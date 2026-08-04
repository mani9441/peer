import streamlit as st

st.set_page_config(
    page_title="PEER Studio", 
    page_icon="assets/favicon.png", 
    layout="wide"
)

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current workspace to path to allow importing backend module
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

def hide_streamlit_header_footer():
    """Hides the top-right Deploy button, 3-dot menu, and bottom Streamlit footer."""
    hide_css = """
        <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppDeployButton {display:none;}
        </style>
    """
    st.markdown(hide_css, unsafe_allow_html=True)


# Hide Streamlit's default header elements (Deploy button & 3 dots)
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display:none;}
    </style>
    """,
    unsafe_allow_html=True,
)



landing_page = st.Page(
    "peer_studio/landing.py", 
    title="Welcome", 
    icon=":material/home:", 
    default=True
)

home_page = st.Page(
    "peer_studio/home.py", 
    title="Dashboard", 
    icon=":material/speed:"
)

create_exp_page = st.Page(
    "peer_studio/pages/experiments/create.py", 
    title="Create Experiment", 
    icon=":material/science:"
)

running_exp_page = st.Page(
    "peer_studio/pages/experiments/running.py", 
    title="Running Experiments", 
    icon=":material/hourglass_empty:"
)

completed_exp_page = st.Page(
    "peer_studio/pages/experiments/completed.py", 
    title="Completed Experiments", 
    icon=":material/check_circle:"
)

results_page = st.Page(
    "peer_studio/pages/results/view.py", 
    title="Experiment Results", 
    icon=":material/analytics:"
)

compare_page = st.Page(
    "peer_studio/pages/results/compare.py", 
    title="Compare Experiments", 
    icon=":material/compare:"
)

analytics_page = st.Page(
    "peer_studio/pages/results/analytics.py", 
    title="Analytics", 
    icon=":material/trending_up:"
)

datasets_page = st.Page(
    "peer_studio/pages/resources/datasets.py", 
    title="Datasets", 
    icon=":material/database:"
)

models_page = st.Page(
    "peer_studio/pages/resources/models.py", 
    title="Models", 
    icon=":material/memory:"
)

prompt_templates_page = st.Page(
    "peer_studio/pages/resources/templates.py", 
    title="Prompt Templates", 
    icon=":material/library_books:"
)

settings_page = st.Page(
    "peer_studio/pages/settings.py", 
    title="Settings", 
    icon=":material/settings:"
)

# Render navigation
pg = st.navigation(
    {
        "Welcome": [landing_page],
        "Dashboard": [home_page],
        "Experiments": [create_exp_page, running_exp_page, completed_exp_page],
        "Results": [results_page, compare_page, analytics_page],
        "Resources": [datasets_page, models_page, prompt_templates_page],
        "Settings": [settings_page]
    }
)

pg.run()

