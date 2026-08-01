import streamlit as st
import os
import sys

# Add current workspace to path to allow importing backend module
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Define pages using Streamlit's programmatic navigation (requires Streamlit 1.35+)
home_page = st.Page(
    "peer_studio/home.py", 
    title="Dashboard", 
    icon="🏠", 
    default=True
)

create_exp_page = st.Page(
    "peer_studio/pages/experiments/create.py", 
    title="Create Experiment", 
    icon="🧪"
)

running_exp_page = st.Page(
    "peer_studio/pages/experiments/running.py", 
    title="Running Experiments", 
    icon="⏳"
)

completed_exp_page = st.Page(
    "peer_studio/pages/experiments/completed.py", 
    title="Completed Experiments", 
    icon="✅"
)

results_page = st.Page(
    "peer_studio/pages/results/view.py", 
    title="Experiment Results", 
    icon="📊"
)

compare_page = st.Page(
    "peer_studio/pages/results/compare.py", 
    title="Compare Experiments", 
    icon="⚖️"
)

analytics_page = st.Page(
    "peer_studio/pages/results/analytics.py", 
    title="Analytics", 
    icon="📈"
)

datasets_page = st.Page(
    "peer_studio/pages/resources/datasets.py", 
    title="Datasets", 
    icon="📚"
)

models_page = st.Page(
    "peer_studio/pages/resources/models.py", 
    title="Models", 
    icon="🤖"
)

prompt_templates_page = st.Page(
    "peer_studio/pages/resources/templates.py", 
    title="Prompt Templates", 
    icon="✍️"
)

settings_page = st.Page(
    "peer_studio/pages/settings.py", 
    title="Settings", 
    icon="⚙️"
)

# Render navigation
pg = st.navigation(
    {
        "Dashboard": [home_page],
        "Experiments": [create_exp_page, running_exp_page, completed_exp_page],
        "Results": [results_page, compare_page, analytics_page],
        "Resources": [datasets_page, models_page, prompt_templates_page],
        "Settings": [settings_page]
    }
)

st.set_page_config(
    page_title="PEER Studio", 
    page_icon="🔬", 
    layout="wide"
)

pg.run()
