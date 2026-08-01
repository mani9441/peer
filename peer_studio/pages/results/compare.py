import streamlit as st
import pandas as pd
import json
import plotly.express as px
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.experiments.manager import ExperimentManager
from backend.experiments.models import Experiment, ExperimentRun, Response

st.markdown("""
    <style>
    .comparison-summary {
        background-color: #f7faff;
        border: 1px solid #cce5ff;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚖️ Cross-Study Comparator")
st.markdown("Perform side-by-side comparisons of prompt configurations across multiple research studies.")

db = SessionLocal()
experiment_mgr = ExperimentManager()

experiments = experiment_mgr.list_experiments(db)

# Group experiments by Study Name
study_groups = {}
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

# Select studies to compare
selected_studies = st.multiselect(
    "Select Studies to Compare (Choose 1 or more)",
    list(study_groups.keys()),
    default=list(study_groups.keys())[:1] if study_groups else []
)

if not selected_studies:
    st.warning("Please select at least one study to begin comparative analysis.")
    db.close()
    st.stop()

# Gather completed configurations across selected studies
cfg_rows = []
for s_name in selected_studies:
    for exp in study_groups[s_name]:
        runs = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == exp.id).all()
        completed_runs = [r for r in runs if r.status == "Completed"]
        
        if not completed_runs:
            continue
            
        all_responses = []
        for r in completed_runs:
            all_responses.extend(r.responses)
            
        if not all_responses:
            continue
            
        # Get metrics
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
        total_tokens = sum(resp.input_tokens + resp.output_tokens for resp in all_responses)
        mean_tokens = total_tokens / len(completed_runs) if completed_runs else 0.0
        
        cfg_label = exp.name.split("]")[-1].strip() if "]" in exp.name else exp.name
        
        cfg_rows.append({
            "Study": s_name,
            "Configuration": cfg_label,
            "Accuracy": accuracy,
            "F1 Score": f1,
            "Latency (ms)": mean_latency,
            "Mean Cost": mean_cost,
            "Mean Tokens": mean_tokens,
            "Model": exp.model
        })

if not cfg_rows:
    st.info("No completed configurations found for the selected studies.")
    db.close()
    st.stop()

df_matrix = pd.DataFrame(cfg_rows)

st.subheader("📋 Cross-Configuration Matrix")
display_df = df_matrix.copy()
display_df["Accuracy"] = display_df["Accuracy"].map(lambda x: f"{x*100:.1f}%")
display_df["F1 Score"] = display_df["F1 Score"].map(lambda x: f"{x:.3f}")
display_df["Latency (ms)"] = display_df["Latency (ms)"].map(lambda x: f"{x:.0f} ms")
display_df["Mean Cost"] = display_df["Mean Cost"].map(lambda x: f"${x:.5f}")
display_df["Mean Tokens"] = display_df["Mean Tokens"].map(lambda x: f"{x:.0f}")

st.dataframe(display_df, use_container_width=True, hide_index=True)

# Recommendation
st.markdown("### 🔬 Strategic Recommendation Summary")
best_acc_row = df_matrix.loc[df_matrix["Accuracy"].idxmax()]
cheapest_row = df_matrix.loc[df_matrix["Mean Cost"].idxmin()]
fastest_row = df_matrix.loc[df_matrix["Latency (ms)"].idxmin()]

st.markdown(f"""
    <div class="comparison-summary">
        <strong>💡 Automated Dissertation Insight Synthesis:</strong>
        <ul>
            <li>The highest accuracy was achieved by configuration <strong>{best_acc_row['Configuration']}</strong> (under Study: <em>{best_acc_row['Study']}</em>) with <strong>{best_acc_row['Accuracy']*100:.1f}%</strong>.</li>
            <li>The most cost-efficient execution was by configuration <strong>{cheapest_row['Configuration']}</strong>, costing <strong>${cheapest_row['Mean_Cost']*1000 if 'Mean_Cost' in cheapest_row else cheapest_row['Mean Cost']*1000:.4f} per 1k runs</strong>.</li>
            <li>The fastest response footprint was by configuration <strong>{fastest_row['Configuration']}</strong>, with a mean latency of <strong>{fastest_row['Latency (ms)']:.0f} ms</strong>.</li>
        </ul>
        <em>Recommendation</em>: If accuracy is paramount, prioritize <strong>{best_acc_row['Configuration']}</strong>. If deploying under strict real-time speed budgets, <strong>{fastest_row['Configuration']}</strong> represents the optimal trade-off.
    </div>
""", unsafe_allow_html=True)

# Charts row
st.markdown("### 📊 Metrics Visualization Charts")

df_matrix_chart = df_matrix.copy()
df_matrix_chart["Accuracy (%)"] = df_matrix_chart["Accuracy"] * 100
df_matrix_chart["Cost per 1k ($)"] = df_matrix_chart["Mean Cost"] * 1000
df_matrix_chart["Config Label"] = df_matrix_chart["Study"] + " | " + df_matrix_chart["Configuration"]

col_ch1, col_ch2 = st.columns(2)
with col_ch1:
    fig_acc = px.bar(df_matrix_chart, x="Config Label", y="Accuracy (%)", title="Accuracy Comparison", range_y=[0.0, 105.0], color="Study")
    st.plotly_chart(fig_acc, use_container_width=True)
    
    fig_cost = px.bar(df_matrix_chart, x="Config Label", y="Cost per 1k ($)", title="Cost per 1k Queries Comparison", color="Study")
    st.plotly_chart(fig_cost, use_container_width=True)
    
with col_ch2:
    fig_lat = px.bar(df_matrix_chart, x="Config Label", y="Latency (ms)", title="Response Latency Comparison", color="Study")
    st.plotly_chart(fig_lat, use_container_width=True)

# Markdown Research Tables for Copy-Paste
st.markdown("---")
st.markdown("### 📝 LaTeX / GFM Markdown Table for Dissertations")
st.markdown("Copy the markdown layout directly to include in reports or research logs.")

markdown_table = display_df.to_markdown(index=False)
st.code(markdown_table, language="markdown")

db.close()
