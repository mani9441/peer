import json
import os
from sqlalchemy import func
import streamlit as st

from backend.database.db import get_db, init_db
from backend.datasets.models import Dataset
from backend.experiments.models import ExperimentRun, Response
from peer_studio.utils.ui import (
    apply_custom_theme,
    inject_footer_spacer,
    render_header,
)

# Make sure database is initialized
init_db()

# Apply page styles
apply_custom_theme()

# Injected CSS enhancements to guarantee high contrast between headings and text
st.markdown(
    """
<style>
    /* Section Headings Styling */
    .h2-style {
        color: #1A202C !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
        margin-top: 10px !important;
        margin-bottom: 6px !important;
        padding-bottom: 6px;
        border-bottom: 2px solid #E2E8F0;
    }

    /* Subtitle styling */
    .sub-caption {
        color: #4A5568 !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        margin-top: -6px !important;
        margin-bottom: 20px !important;
    }

    /* Metric Cards Improvement */
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-title {
        color: #4A5568 !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .metric-value {
        color: #0F172A !important;
        font-size: 1.45rem !important;
        font-weight: 800 !important;
        font-family: 'Outfit', sans-serif;
    }

    /* Step Cards Visual Separation */
    .journey-card {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 18px;
        border-top: 4px solid;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.06);
        height: 100%;
    }
    .journey-card-header {
        font-family: 'Outfit', sans-serif;
        font-size: 1.15rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #EDF2F7;
    }
    .journey-card p {
        font-size: 0.88rem;
        line-height: 1.55;
        color: #4A5568;
        margin: 0;
    }
    .highlight-label {
        font-weight: 700;
        color: #1A202C;
    }
</style>
""",
    unsafe_allow_html=True,
)

# App Header
render_header(
    "PEER Framework Studio",
    "Prompt Engineering Evaluation and Experimentation Research Framework",
    "speed",
)

st.markdown("""
Welcome to **PEER Studio**, a scientific workbench tailored for prompt engineers and researchers to run rigorous, empirical evaluations. 
Here, prompt variations are designed as experimental parameters, run across language models, and evaluated against standardized ground-truth benchmarks.
""")

# Database queries for stats
dataset_count = 0
total_samples = 0
db_size_kb = 0.0
completed_runs = 0
active_runs = 0

db_path = "config/peer.db"
if os.path.exists(db_path):
    db_size_kb = os.path.getsize(db_path) / 1024.0

with get_db() as db:
    datasets = db.query(Dataset).all()
    dataset_count = len(datasets)

    # 1. Total Studies and Configurations
    from backend.experiments.models import Experiment

    db_exps = db.query(Experiment).all()
    study_names = set()
    for e in db_exps:
        study_name = "Independent Configurations"
        if e.description:
            try:
                meta = json.loads(e.description)
                if isinstance(meta, dict) and "study_name" in meta:
                    study_name = meta["study_name"]
            except Exception:
                pass
        if study_name == "Independent Configurations" and "]" in e.name:
            study_name = e.name.split("]")[0].replace("[", "").strip()
        study_names.add(study_name)
    study_count = len(study_names) if db_exps else 0
    config_count = len(db_exps)

    # 2. Total Evaluated Responses
    total_evals = db.query(Response).count()

    # 3. Target Models
    unique_models = [
        m[0] for m in db.query(Experiment.model).distinct().all()
    ]
    models_str = ", ".join(unique_models) if unique_models else "None"

    # 4. Total Tokens
    total_tokens = (
        db.query(
            func.sum(Response.input_tokens + Response.output_tokens)
        ).scalar()
        or 0
    )

    # 5. Average Accuracy
    correct_evals = (
        db.query(Response).filter(Response.is_correct == True).count()
    )
    avg_accuracy = (
        (correct_evals / total_evals * 100) if total_evals > 0 else 0.0
    )

    # 6. Most accurate & fastest prompt styles
    from backend.strategies.models import PromptStrategy

    style_stats = {}
    for exp in db_exps:
        strat = (
            db.query(PromptStrategy)
            .filter(PromptStrategy.id == exp.strategy_id)
            .first()
        )
        style = strat.structure if strat else "Mixed"
        runs = (
            db.query(ExperimentRun)
            .filter(ExperimentRun.experiment_id == exp.id)
            .all()
        )
        resps = []
        for r in runs:
            resps.extend(r.responses)
        if not resps:
            continue
        correct = sum(1 for rp in resps if rp.is_correct)
        acc = correct / len(resps)
        lat = sum(rp.latency for rp in resps) / len(resps)

        if style not in style_stats:
            style_stats[style] = {"accs": [], "lats": []}
        style_stats[style]["accs"].append(acc)
        style_stats[style]["lats"].append(lat)

    best_style = "N/A"
    fastest_style = "N/A"
    if style_stats:
        best_style = max(
            style_stats.keys(),
            key=lambda k: sum(style_stats[k]["accs"])
            / len(style_stats[k]["accs"]),
        )
        fastest_style = min(
            style_stats.keys(),
            key=lambda k: sum(style_stats[k]["lats"])
            / len(style_stats[k]["lats"]),
        )

    completed_runs = (
        db.query(ExperimentRun)
        .filter(ExperimentRun.status == "Completed")
        .count()
    )
    active_runs = (
        db.query(ExperimentRun)
        .filter(ExperimentRun.status.in_(["Queued", "Running"]))
        .count()
    )

# Active alert if background executions are running
if active_runs > 0:
    st.info(
        f"**Live Activity Alert**: There are currently **{active_runs} runs** executing in the background. [Click here to monitor them](experiments/Running_Experiments)",
        icon=":material/warning:",
    )
    st.markdown("---")

# Key Metrics section with high-contrast heading
st.markdown(
    '<h2 class="h2-style">Research Laboratory Status</h2>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p class="sub-caption">Active Models benchmarked: <code style="color: #2F7D4A; font-weight: 600;">{models_str}</code></p>',
    unsafe_allow_html=True,
)

col_r1, col_r2, col_r3, col_r4 = st.columns(4)

with col_r1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Research Studies</div>
            <div class="metric-value">{study_count}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

with col_r2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Configurations Tested</div>
            <div class="metric-value">{config_count}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

with col_r3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Total Samples Evaluated</div>
            <div class="metric-value">{total_evals:,}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

with col_r4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Total Tokens Footprint</div>
            <div class="metric-value">{total_tokens / 1e6:.2f} M</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

st.markdown("<br/>", unsafe_allow_html=True)

col_r5, col_r6, col_r7, col_r8 = st.columns(4)

with col_r5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Average Evaluation Accuracy</div>
            <div class="metric-value">{avg_accuracy:.1f}%</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

with col_r6:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Optimal Prompt Style</div>
            <div class="metric-value">{best_style}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

with col_r7:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Fastest Prompt Style</div>
            <div class="metric-value">{fastest_style}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

with col_r8:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">SQLite Database Size</div>
            <div class="metric-value">{db_size_kb:.1f} KB</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

st.markdown("<br/>", unsafe_allow_html=True)

# Overview sections with prominent cards and bullet emphasis
st.markdown(
    '<h2 class="h2-style">Guided Scientific Research Journey</h2>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-caption">A structured step-by-step pipeline from formulation to comparative evaluation.</p>',
    unsafe_allow_html=True,
)

col_g1, col_g2, col_g3 = st.columns(3)

with col_g1:
    st.markdown(
        """
    <div class="journey-card" style="border-top-color: #2F7D4A;">
        <div class="journey-card-header" style="color: #2F7D4A;">
            <span class="material-symbols-outlined">science</span>
            1. Design Experiments
        </div>
        <p>
            <span class="highlight-label">Formulate hypotheses directly:</span><br/>
            • <b>Prompt Structures:</b> Markdown, XML, JSON<br/>
            • <b>Parameters:</b> Instruction length & reasoning flags<br/>
            • <b>Context:</b> Few-shot counts & retrieval methods<br/>
            • <b>Target Models:</b> Multi-LLM sync backend
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col_g2:
    st.markdown(
        """
    <div class="journey-card" style="border-top-color: #5E3A87;">
        <div class="journey-card-header" style="color: #5E3A87;">
            <span class="material-symbols-outlined">pending</span>
            2. Execute Evaluations
        </div>
        <p>
            <span class="highlight-label">Monitor performance runs live:</span><br/>
            • <b>Background Spawning:</b> Async multi-run execution<br/>
            • <b>Streaming Capture:</b> Inputs, prompts, latencies<br/>
            • <b>Automated Scoring:</b> Correctness, precision, recall<br/>
            • <b>Cost Tracking:</b> Token expenditure analysis
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col_g3:
    st.markdown(
        """
    <div class="journey-card" style="border-top-color: #C48A1D;">
        <div class="journey-card-header" style="color: #C48A1D;">
            <span class="material-symbols-outlined">compare</span>
            3. Compare Strategies
        </div>
        <p>
            <span class="highlight-label">Evaluate and export analytics:</span><br/>
            • <b>Matrices:</b> Side-by-side Accuracy vs. Latency<br/>
            • <b>Visualizations:</b> Multi-experiment Plotly charts<br/>
            • <b>Research Logs:</b> Direct LaTeX & Markdown table export<br/>
            • <b>Optimal Discovery:</b> Best performing prompt styles
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

inject_footer_spacer()