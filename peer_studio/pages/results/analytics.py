import streamlit as st
import pandas as pd
import json
import plotly.express as px
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.experiments.manager import ExperimentManager
from backend.experiments.models import Experiment, ExperimentRun
from peer_studio.utils.ui import apply_custom_theme, render_header, inject_footer_spacer

# Apply page styles
apply_custom_theme()

render_header(
    "Advanced Research Analytics", 
    "Diagnose Pareto Frontier optimizations, analyzing accuracy-to-latency limits and parameter sensitivity.", 
    "trending_up"
)

db = SessionLocal()
experiment_mgr = ExperimentManager()

experiments = experiment_mgr.list_experiments(db)

# Group experiments by Study Name
study_groups = {"All Studies Combined": []}
for exp in experiments:
    study_name = "Independent Configurations"
    if exp.description:
        try:
            meta = json.loads(exp.description)
            if isinstance(meta, dict) and "study_name" in meta:
                study_name = meta["study_name"]
        except Exception:
            pass
    if study_name == "Independent Configurations" and "]" in exp.name:
        study_name = exp.name.split("]")[0].replace("[", "").strip()

    if study_name not in study_groups:
        study_groups[study_name] = []
    study_groups[study_name].append(exp)
    study_groups["All Studies Combined"].append(exp)

selected_study = st.selectbox("Select Study to Analyze", list(study_groups.keys()))
selected_exps = study_groups[selected_study]

# Filter out active runs
completed_exps = []
for e in selected_exps:
    active_count = db.query(ExperimentRun).filter(
        ExperimentRun.experiment_id == e.id,
        ExperimentRun.status.in_(["Queued", "Running"])
    ).count()
    if active_count == 0:
        completed_exps.append(e)

if len(completed_exps) < 2:
    st.info("At least 2 completed configurations are required to unlock comparative metrics charts.")
    db.close()
    st.stop()

# Compile details
records = []
for exp in completed_exps:
    runs = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == exp.id).all()
    completed_runs = [r for r in runs if r.status == "Completed"]
    if not completed_runs:
        continue
        
    all_responses = []
    for r in completed_runs:
        all_responses.extend(r.responses)
        
    if not all_responses:
        continue
        
    correct_count = sum(1 for resp in all_responses if resp.is_correct)
    total_samples = len(all_responses)
    accuracy = correct_count / total_samples if total_samples > 0 else 0.0
    
    # Estimate F1 score
    f1 = accuracy
    completed_metrics = [r.metrics for r in completed_runs if r.metrics]
    if completed_metrics:
        f1 = sum((m.f1 if m.f1 is not None else 0.0) for m in completed_metrics) / len(completed_metrics)
        
    latencies = [resp.latency for resp in all_responses]
    mean_latency = sum(latencies) / len(latencies) if latencies else 0.0
    total_cost = sum(resp.cost for resp in all_responses)
    mean_cost = total_cost / len(completed_runs) if completed_runs else 0.0
    
    # Get strategy attributes
    strategy_id = exp.strategy_id
    strategy_format = "Plain Text"
    fewshot_count = 0
    strategy_struct = "Mixed"
    
    from backend.strategies.models import PromptStrategy
    db_strat = db.query(PromptStrategy).filter(PromptStrategy.id == strategy_id).first()
    if db_strat:
        strategy_format = db_strat.format
        fewshot_count = db_strat.example_count
        strategy_struct = db_strat.structure
        
    cfg_label = exp.name.split("]")[-1].strip() if "]" in exp.name else exp.name
        
    records.append({
        "Configuration": cfg_label,
        "Model": exp.model,
        "Prompt Format": strategy_format,
        "Prompt Style": strategy_struct,
        "Few-shot Count": fewshot_count,
        "Accuracy (%)": accuracy * 100,
        "F1 Score": f1,
        "Latency (ms)": mean_latency,
        "Cost per 1k ($)": mean_cost * 1000
    })

df = pd.DataFrame(records)

st.markdown('<h3 class="h3-style">Pareto Frontier Optimization Diagnostics</h3>', unsafe_allow_html=True)
st.markdown("Ideal prompting methods reside in the top-left section (high accuracy, low latency) or top-right quadrant.")

fig_scatter = px.scatter(
    df,
    x="Latency (ms)",
    y="Accuracy (%)",
    size="Cost per 1k ($)",
    color="Prompt Format" if len(df["Prompt Format"].unique()) > 1 else "Model",
    color_discrete_sequence=["#2F7D4A", "#5E3A87", "#C48A1D", "#666666"],
    hover_name="Configuration",
    text="Prompt Style" if len(df["Prompt Style"].unique()) > 1 else "Configuration",
    title="<b>Pareto Curve: Accuracy (%) vs Latency (ms)</b>",
    labels={"Accuracy (%)": "Accuracy (%)", "Latency (ms)": "Latency (ms)"}
)
fig_scatter.update_traces(textposition='top center')
fig_scatter.update_layout(
    height=500, 
    plot_bgcolor="rgba(0,0,0,0)", 
    paper_bgcolor="rgba(0,0,0,0)",
    title=dict(font=dict(family="Outfit", size=15, color="#1A1A1A")),
    margin=dict(t=50, b=40, l=40, r=20),
    legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
)
st.plotly_chart(fig_scatter, use_container_width=True)

col_an1, col_an2 = st.columns(2)
with col_an1:
    st.markdown("#### Accuracy vs Cost footprint")
    fig_cost_acc = px.scatter(
        df,
        x="Cost per 1k ($)",
        y="Accuracy (%)",
        color="Prompt Format",
        color_discrete_sequence=["#2F7D4A", "#C48A1D", "#5E3A87", "#666666"],
        hover_name="Configuration",
        title="<b>Accuracy (%) vs Cost per 1k ($)</b>",
    )
    fig_cost_acc.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", 
        paper_bgcolor="rgba(0,0,0,0)",
        title=dict(font=dict(family="Outfit", size=15, color="#1A1A1A")),
        margin=dict(t=50, b=40, l=40, r=20),
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_cost_acc, use_container_width=True)
    
with col_an2:
    st.markdown("#### Latency footprint by Prompt Format")
    fig_format_lat = px.box(
        df,
        x="Prompt Format",
        y="Latency (ms)",
        points="all",
        title="<b>Latency footprints by formatting layout</b>",
        color="Prompt Format",
        color_discrete_sequence=["#5E3A87", "#7E58AA", "#A283C7"]
    )
    fig_format_lat.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", 
        paper_bgcolor="rgba(0,0,0,0)",
        title=dict(font=dict(family="Outfit", size=15, color="#1A1A1A")),
        margin=dict(t=50, b=40, l=40, r=20),
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_format_lat, use_container_width=True)

# Parameter Analysis Tables
st.markdown("---")
st.markdown('<h3 class="h3-style">Parameter Sensitivity Diagnostics</h3>', unsafe_allow_html=True)

col_t1, col_t2 = st.columns(2)
with col_t1:
    st.markdown("**Few-shot Count Influence**")
    fewshot_influence = df.groupby("Few-shot Count").agg({
        "Accuracy (%)": "mean",
        "Latency (ms)": "mean",
        "Cost per 1k ($)": "mean"
    }).reset_index()
    st.dataframe(fewshot_influence, use_container_width=True, hide_index=True)
    
with col_t2:
    st.markdown("**Prompt Style Influence**")
    style_influence = df.groupby("Prompt Style").agg({
        "Accuracy (%)": "mean",
        "Latency (ms)": "mean",
        "Cost per 1k ($)": "mean"
    }).reset_index()
    st.dataframe(style_influence, use_container_width=True, hide_index=True)

db.close()
inject_footer_spacer()
