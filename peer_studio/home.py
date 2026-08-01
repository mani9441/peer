import streamlit as st
import os
from backend.database.db import get_db, init_db
from backend.datasets.models import Dataset
from backend.experiments.models import ExperimentRun, Response

# Make sure database is initialized
init_db()

# Page Styling
st.markdown("""
    <style>
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1A73E8 0%, #34A853 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #5f6368;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #dadce0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.04);
        border-color: #1a73e8;
    }
    .metric-title {
        font-size: 0.95rem;
        color: #5f6368;
        font-weight: 600;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #202124;
        margin-top: 5px;
    }
    .section-title {
        font-size: 1.5rem;
        font-weight: 700;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: #202124;
    }
    </style>
""", unsafe_allow_html=True)

# App Header
st.markdown('<div class="main-title">PEER Framework Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Prompt Engineering Evaluation and Experimentation Research Framework</div>', unsafe_allow_html=True)

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

from sqlalchemy import func
import json

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
    unique_models = [m[0] for m in db.query(Experiment.model).distinct().all()]
    models_str = ", ".join(unique_models) if unique_models else "None"
    
    # 4. Total Tokens
    total_tokens = db.query(func.sum(Response.input_tokens + Response.output_tokens)).scalar() or 0
    
    # 5. Average Accuracy
    correct_evals = db.query(Response).filter(Response.is_correct == True).count()
    avg_accuracy = (correct_evals / total_evals * 100) if total_evals > 0 else 0.0
    
    # 6. Most accurate & fastest prompt styles
    from backend.strategies.models import PromptStrategy
    style_stats = {}
    for exp in db_exps:
        strat = db.query(PromptStrategy).filter(PromptStrategy.id == exp.strategy_id).first()
        style = strat.structure if strat else "Mixed"
        runs = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == exp.id).all()
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
        best_style = max(style_stats.keys(), key=lambda k: sum(style_stats[k]["accs"]) / len(style_stats[k]["accs"]))
        fastest_style = min(style_stats.keys(), key=lambda k: sum(style_stats[k]["lats"]) / len(style_stats[k]["lats"]))
        
    completed_runs = db.query(ExperimentRun).filter(ExperimentRun.status == "Completed").count()
    active_runs = db.query(ExperimentRun).filter(ExperimentRun.status.in_(["Queued", "Running"])).count()

# Active alert if background executions are running
if active_runs > 0:
    st.info(f"⚡ **Live Activity Alert**: There are currently **{active_runs} runs** executing in the background. [Click here to monitor them](experiments/Running_Experiments)")
    st.markdown("---")

# Key Metrics row
st.markdown('<div class="section-title">Research Laboratory Status</div>', unsafe_allow_html=True)
st.markdown(f"<p style='color:#5f6368; font-size:0.9rem; margin-top:-10px; margin-bottom:15px;'>Active Models benchmarked: <code>{models_str}</code></p>", unsafe_allow_html=True)

col_r1, col_r2, col_r3, col_r4 = st.columns(4)

with col_r1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Research Studies</div>
            <div class="metric-value">{study_count}</div>
        </div>
    """, unsafe_allow_html=True)

with col_r2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Configurations Tested</div>
            <div class="metric-value">{config_count}</div>
        </div>
    """, unsafe_allow_html=True)

with col_r3:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Samples Evaluated</div>
            <div class="metric-value">{total_evals:,}</div>
        </div>
    """, unsafe_allow_html=True)

with col_r4:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Tokens Footprint</div>
            <div class="metric-value">{total_tokens / 1e6:.2f} M</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

col_r5, col_r6, col_r7, col_r8 = st.columns(4)

with col_r5:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Average Evaluation Accuracy</div>
            <div class="metric-value">{avg_accuracy:.1f}%</div>
        </div>
    """, unsafe_allow_html=True)

with col_r6:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Optimal Prompt Style</div>
            <div class="metric-value">{best_style}</div>
        </div>
    """, unsafe_allow_html=True)

with col_r7:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Fastest Prompt Style</div>
            <div class="metric-value">{fastest_style}</div>
        </div>
    """, unsafe_allow_html=True)

with col_r8:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">SQLite Database size</div>
            <div class="metric-value">{db_size_kb:.1f} KB</div>
        </div>
    """, unsafe_allow_html=True)

# Overview sections
st.markdown('<div class="section-title">Guided Scientific Research Journey</div>', unsafe_allow_html=True)

col_g1, col_g2, col_g3 = st.columns(3)

with col_g1:
    st.success("""
    ### 🧪 1. Design Experiments
    Formulate hypotheses directly:
    - Specify prompt format structure (Markdown, XML, JSON).
    - Toggle instruction lengths and step-by-step reasoning flags.
    - Set up few-shot examples count ($K$) and retrieval methods (Random, Semantic).
    - Sync backend model targets.
    """)

with col_g2:
    st.info("""
    ### ⏳ 2. Execute Evaluations
    Monitor performance runs live:
    - Spawns multi-run experiments in the background.
    - TensorBoard-style streaming captures inputs, prompts, outputs, and latencies.
    - Auto-calculates correctness, precision, recall, and cost models.
    """)

with col_g3:
    st.warning("""
    ### 📊 3. Compare Strategies
    Evaluate and copy analytics:
    - Side-by-side matrices contrasting accuracy vs. latency frontiers.
    - Multi-experiment Plotly charting.
    - Auto-generated LaTeX and Markdown tables to drag directly into thesis logs.
    """)
