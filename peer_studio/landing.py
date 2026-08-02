import streamlit as st
import os
from peer_studio.utils.ui import apply_custom_theme, inject_footer_spacer

# Apply page styling
apply_custom_theme()

# Center alignment layout using columns
col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
with col_l2:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    if os.path.exists("assets/logo_primary.png"):
        st.image("assets/logo_primary.png", width='stretch')
    else:
        st.title("PEER Framework Studio")
        
    st.markdown("""
        <div style="text-align: center; margin-top: 20px; margin-bottom: 30px;">
            <h3 style="margin: 0; font-family: 'Outfit', sans-serif; font-size: 20px; font-weight: 600; color: #1A1A1A;">
                Prompt Engineering Evaluation & Research Platform
            </h3>
            <p style="margin: 8px 0 0 0; color: #666666; font-size: 14.5px;">
                A scientific workbench tailored for prompt engineers and researchers to run empirical evaluations.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Center-aligned button using Streamlit columns
    btn_col_1, btn_col_2, btn_col_3 = st.columns([1, 2, 1])
    with btn_col_2:
        if st.button("Get Started", type="primary", width='stretch'):
            st.switch_page("peer_studio/home.py")

inject_footer_spacer()
