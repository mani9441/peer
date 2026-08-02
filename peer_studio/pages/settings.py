import streamlit as st
import sys
import os
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.providers import ProviderService
from peer_studio.utils.ui import apply_custom_theme, render_header, inject_footer_spacer

# Apply page styling
apply_custom_theme()

# Page Header
render_header(
    "Settings", 
    "Inspect local environment metrics, verify SQLite storage parameters, and re-initialize inference catalogs.", 
    "settings"
)

db = SessionLocal()
provider_service = ProviderService()

# DB size calculations
db_path = "config/peer.db"
db_size_kb = 0.0
if os.path.exists(db_path):
    db_size_kb = os.path.getsize(db_path) / 1024.0

st.markdown("### Database Storage Metrics")
col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    st.text_input("Database Path Bind", value=db_path, disabled=True)
with col_s2:
    st.metric("Database File Size", f"{db_size_kb:.2f} KB")
with col_s3:
    if st.button("Seed / Re-initialize DB Defaults", use_container_width=True):
        provider_service._ensure_providers_seeded(db)
        st.success("Default provider configurations successfully re-seeded.")

st.markdown("---")

st.markdown("### System Environment Info")
col_sys1, col_sys2 = st.columns(2)
with col_sys1:
    st.markdown(f"- **Python Version**: `{sys.version.split()[0]}`")
    st.markdown(f"- **Streamlit version**: `{st.__version__}`")
with col_sys2:
    st.markdown(f"- **Workspace path**: `{os.getcwd()}`")
    st.markdown(f"- **Artifacts subdirectory**: `exports/`")

st.markdown("---")

st.markdown("### API Key Environments Guideline")
st.info("""
To interact with models from Gemini, OpenAI, or OpenRouter, ensure you have exported the relevant environment variables in your terminal shell before launching PEER:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
export OPENAI_API_KEY="your-openai-api-key"
export OPENROUTER_API_KEY="your-openrouter-api-key"
```
Or define them inside a `.env` file in the project's root directory.
""")

db.close()
inject_footer_spacer()
