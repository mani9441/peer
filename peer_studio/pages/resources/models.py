import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.providers import ProviderService
from backend.providers.models import Provider as DBProvider, Model as DBModel
from peer_studio.utils.ui import apply_custom_theme, render_header, inject_footer_spacer

# Apply page styling
apply_custom_theme()

render_header(
    "Provider & Model Registry", 
    "Verify API configurations, sync model lists, and test network connections to backend inference nodes.", 
    "memory"
)

db = SessionLocal()
provider_service = ProviderService()

# Ensure default providers are registered in DB
provider_service._ensure_providers_seeded(db)

# Tabs
tab_providers, tab_models = st.tabs(["LLM Providers", "Model Registry"])

with tab_providers:
    st.markdown("### Registered Inference Providers")
    
    # Query all providers
    providers = db.query(DBProvider).all()
    
    for p in providers:
        st.markdown(f"#### {p.provider_name} (ID: `{p.id}`)")
        
        col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
        with col_p1:
            is_enabled = st.checkbox("Enabled", value=p.enabled, key=f"p_enabled_{p.id}")
            if is_enabled != p.enabled:
                p.enabled = is_enabled
                db.commit()
                st.toast(f"{p.provider_name} state updated.")
                st.rerun()
                
        with col_p2:
            api_base_val = st.text_input("API Base URL (optional)", value=p.api_base or "", placeholder="Using default API route...", key=f"p_base_{p.id}")
            if api_base_val != (p.api_base or ""):
                p.api_base = api_base_val if api_base_val.strip() else None
                db.commit()
                st.toast(f"{p.provider_name} API Base updated.")
                st.rerun()
                
        with col_p3:
            # Health check test button
            if st.button("Health Check", icon=":material/network_ping:", key=f"p_test_{p.id}", use_container_width=True):
                with st.spinner("Testing connectivity..."):
                    connected = provider_service.health_check(db, p.id)
                    if connected:
                        st.success("Connection Successful!")
                    else:
                        st.error("Connection Failed. Check API keys or local server.")
                        
        st.markdown("---")

with tab_models:
    st.markdown("### Synced Model Registries")
    st.markdown("Sync active models from enabled providers to register them as targets for experiments.")
    
    if st.button("Sync Available Models", icon=":material/sync:", use_container_width=True):
        with st.spinner("Syncing models from active provider endpoints..."):
            try:
                # Trigger sync
                provider_service.list_models(db)
                st.success("Successfully synchronized models catalog!")
                st.rerun()
            except Exception as sync_err:
                st.error(f"Sync failed: {str(sync_err)}")
                
    # List models in DB
    models = db.query(DBModel).join(DBProvider).filter(DBProvider.enabled == True).all()
    
    if not models:
        st.info("No models registered in database catalog yet. Click the Sync button above to load them.")
    else:
        model_list = []
        for m in models:
            model_list.append({
                "Model Name": m.model_name,
                "Provider": m.provider_id.upper(),
                "Context Window": f"{m.context_window:,}" if m.context_window else "Unknown",
                "Temperature": "Yes" if m.supports_temperature else "No",
                "Seed Tuning": "Yes" if m.supports_seed else "No",
                "JSON Mode": "Yes" if m.supports_json_mode else "No",
                "Status": m.status.capitalize()
            })
            
        st.dataframe(pd.DataFrame(model_list), use_container_width=True, hide_index=True)

db.close()
inject_footer_spacer()
