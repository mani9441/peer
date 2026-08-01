import streamlit as st
import pandas as pd
import plotly.express as px
import math
import json
import os
import scipy.stats as stats
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.experiments.manager import ExperimentManager
from backend.experiments.models import Experiment, ExperimentRun, Response

st.markdown("""
    <style>
    .metric-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a73e8;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #5f6368;
        margin-top: 5px;
        font-weight: 600;
    }
    .winner-card {
        border-left: 5px solid #34a853;
        background-color: #e6f4ea;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .report-box {
        background-color: #ffffff;
        border: 1px solid #dadce0;
        border-radius: 8px;
        padding: 25px;
        font-family: 'Inter', sans-serif;
        color: #202124;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Research Results Analyzer")
st.markdown("Analyze prompting variable comparisons, check statistical significance, and generate dissertation reports.")

db = SessionLocal()
experiment_mgr = ExperimentManager()

# Load all experiments
experiments = experiment_mgr.list_experiments(db)

if not experiments:
    st.info("No experiment logs found in database. Please run an experiment study first.")
    db.close()
    st.stop()

# Group experiments by Study Name
study_groups = {}
for exp in experiments:
    study_name = "Independent Configurations"
    rq = "Compare custom prompting variables."
    cfg_name = exp.name
    
    if exp.description:
        try:
            meta = json.loads(exp.description)
            if isinstance(meta, dict):
                study_name = meta.get("study_name", study_name)
                rq = meta.get("research_question", rq)
                cfg_name = meta.get("config_name", cfg_name)
        except Exception:
            pass
            
    if study_name == "Independent Configurations" and "]" in exp.name:
        study_name = exp.name.split("]")[0].replace("[", "").strip()
        cfg_name = exp.name.split("]")[-1].strip()

    if study_name not in study_groups:
        study_groups[study_name] = {
            "research_question": rq,
            "configs": []
        }
    study_groups[study_name]["configs"].append((cfg_name, exp))

# Selectbox Study
default_study_name = list(study_groups.keys())[0]
if "active_study_name" in st.session_state and st.session_state.active_study_name in study_groups:
    default_study_name = st.session_state.active_study_name

selected_study = st.selectbox("Select Research Study to Analyze", list(study_groups.keys()), index=list(study_groups.keys()).index(default_study_name))
study_data = study_groups[selected_study]

st.markdown(f"### **Hypothesis / Research Question**:")
st.markdown(f"*{study_data['research_question']}*")

st.markdown("---")

# Aggregate config data
cfg_stats = []
all_completed = True

for c_name, exp in study_data["configs"]:
    runs = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == exp.id).all()
    completed_runs = [r for r in runs if r.status == "Completed"]
    
    if not completed_runs:
        all_completed = False
        continue
        
    # Gather sample level details across runs
    all_responses = []
    for r in completed_runs:
        all_responses.extend(r.responses)
        
    if not all_responses:
        continue
        
    # Compute aggregates
    correct_count = sum(1 for resp in all_responses if resp.is_correct)
    total_samples = len(all_responses)
    accuracy = correct_count / total_samples if total_samples > 0 else 0.0
    
    # Estimate F1 score
    f1 = accuracy # fallback
    completed_metrics = [r.metrics for r in completed_runs if r.metrics]
    if completed_metrics:
        f1 = sum((m.f1 if m.f1 is not None else 0.0) for m in completed_metrics) / len(completed_metrics)
        
    latencies = [resp.latency for resp in all_responses]
    mean_latency = sum(latencies) / len(latencies) if latencies else 0.0
    std_latency = math.sqrt(sum((x - mean_latency)**2 for x in latencies) / len(latencies)) if len(latencies) > 1 else 0.0
    
    total_cost = sum(resp.cost for resp in all_responses)
    mean_cost = total_cost / len(completed_runs) if completed_runs else 0.0
    total_tokens = sum(resp.input_tokens + resp.output_tokens for resp in all_responses)
    mean_tokens = total_tokens / len(completed_runs) if completed_runs else 0.0
    
    # Binomial CI margin
    ci_margin = 1.96 * math.sqrt((accuracy * (1 - accuracy)) / total_samples) if total_samples > 0 else 0.0
    
    cfg_stats.append({
        "config_name": c_name,
        "experiment_id": exp.id,
        "accuracy": accuracy,
        "f1": f1,
        "latency_mean": mean_latency,
        "latency_std": std_latency,
        "cost_mean": mean_cost,
        "tokens_mean": mean_tokens,
        "ci_margin": ci_margin,
        "total_samples": total_samples,
        "correctness_array": [1 if r.is_correct else 0 for r in all_responses],
        "latency_array": latencies,
        "model": exp.model,
        "dataset_id": exp.dataset_id,
        "runs_count": len(runs)
    })

if not cfg_stats:
    st.info("No completed configuration runs are available for this study yet.")
    db.close()
    st.stop()

# Environment settings (taken from first config)
env = cfg_stats[0]

# Display Winner Card
winner = max(cfg_stats, key=lambda x: x["accuracy"])
st.markdown(f"""
    <div class="winner-card">
        <h4 style="margin: 0; color: #137333;">🏆 Optimal Prompt Strategy (Winner)</h4>
        <p style="margin: 5px 0 0 0; color: #202124;">
            The configuration <b>{winner['config_name']}</b> achieved the highest classification accuracy of 
            <b>{winner['accuracy']*100:.1f}%</b> (± {winner['ci_margin']*100:.1f}%) on target model <code>{winner['model']}</code>.
        </p>
    </div>
""", unsafe_allow_html=True)

tab_matrix, tab_stats, tab_report, tab_audit, tab_export = st.tabs([
    "📋 Performance Matrix", "📊 Statistical Significance", "📝 Research Report", "🔍 Audit Logs", "📥 Export Package"
])

# ----------------- TAB 1: PERFORMANCE MATRIX -----------------
with tab_matrix:
    st.markdown("#### Configuration Performance Comparison")
    
    matrix_rows = []
    for c in cfg_stats:
        matrix_rows.append({
            "Configuration": c["config_name"],
            "Accuracy": f"{c['accuracy']*100:.1f}%",
            "F1 Score": f"{c['f1']:.3f}",
            "Latency": f"{c['latency_mean']:.0f} ± {c['latency_std']:.0f} ms",
            "Mean Cost": f"${c['cost_mean']:.5f}",
            "Mean Tokens": f"{c['tokens_mean']:.0f}",
            "95% Confidence Interval": f"[{ (c['accuracy'] - c['ci_margin'])*100:.1f}%, { (c['accuracy'] + c['ci_margin'])*100:.1f}%]"
        })
    st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True, hide_index=True)
    
    # Plotly Visuals
    plot_df = pd.DataFrame([
        {
            "Configuration": c["config_name"],
            "Accuracy (%)": c["accuracy"] * 100,
            "Latency (ms)": c["latency_mean"],
            "Cost ($)": c["cost_mean"]
        }
        for c in cfg_stats
    ])
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        fig_acc = px.bar(plot_df, x="Configuration", y="Accuracy (%)", title="Accuracy comparison", range_y=[0, 105], color="Accuracy (%)", color_continuous_scale="Viridis")
        st.plotly_chart(fig_acc, use_container_width=True)
    with col_p2:
        fig_lat = px.bar(plot_df, x="Configuration", y="Latency (ms)", title="Response Latency (ms)", color="Latency (ms)", color_continuous_scale="Reds")
        st.plotly_chart(fig_lat, use_container_width=True)

# ----------------- TAB 2: STATISTICAL SIGNIFICANCE -----------------
with tab_stats:
    st.markdown("#### Scientific Validity & Significance Tests")
    st.markdown("PEER performs hypothesis evaluation calculations using `scipy.stats` to check if differences are statistically meaningful.")
    
    # Latency ANOVA/T-Test
    st.markdown("##### 1. Latency Statistical Analysis")
    if len(cfg_stats) >= 2:
        latency_groups = [c["latency_array"] for c in cfg_stats]
        if len(cfg_stats) == 2:
            t_stat, p_val = stats.ttest_ind(latency_groups[0], latency_groups[1], equal_var=False)
            test_name = "Welch's Independent t-test"
        else:
            f_stat, p_val = stats.f_oneway(*latency_groups)
            test_name = "One-Way ANOVA"
            
        st.markdown(f"**Test Performed**: `{test_name}` across response times.")
        if p_val < 0.05:
            st.success(f"🟢 **Significant Difference Detected!** (p-value = `{p_val:.4e}` < `0.05`)")
            st.markdown("The latency variation between configurations is statistically significant. Prompt engineering format and style changes directly impact inference speed.")
        else:
            st.warning(f"🟡 **No Significant Difference.** (p-value = `{p_val:.4f}` ≥ `0.05`)")
            st.markdown("The latency variations are statistically negligible. Differences are likely due to server response jitter or network noise.")
    else:
        st.info("At least 2 configurations are required to run significance calculations.")
        
    st.markdown("---")
    
    # Accuracy Z-test of Proportions / ANOVA approximation
    st.markdown("##### 2. Accuracy Statistical Analysis")
    if len(cfg_stats) >= 2:
        corr_groups = [c["correctness_array"] for c in cfg_stats]
        if len(cfg_stats) == 2:
            t_stat, p_val = stats.ttest_ind(corr_groups[0], corr_groups[1])
            test_name = "Independent Proportions t-test"
        else:
            f_stat, p_val = stats.f_oneway(*corr_groups)
            test_name = "One-Way ANOVA (Binary Proportions)"
            
        st.markdown(f"**Test Performed**: `{test_name}` across correctness distributions.")
        if p_val < 0.05:
            st.success(f"🟢 **Significant Difference Detected!** (p-value = `{p_val:.4f}` < `0.05`)")
            st.markdown("The differences in classification accuracy are statistically significant. The prompting variables evaluated are highly likely to have a direct influence on classification success.")
        else:
            st.warning(f"🟡 **No Significant Difference.** (p-value = `{p_val:.4f}` ≥ `0.05`)")
            st.markdown("The accuracy variations do not pass the statistical significance threshold. We cannot reject the null hypothesis; differences might be due to random sample selection.")
            
    # Interval overlap check
    st.markdown("##### 3. Binomial Confidence Intervals (95% Confidence)")
    for c in cfg_stats:
        ci_low = max(0.0, c["accuracy"] - c["ci_margin"]) * 100
        ci_high = min(1.0, c["accuracy"] + c["ci_margin"]) * 100
        st.markdown(f"- **{c['config_name']}**: `{c['accuracy']*100:.1f}%` Accuracy $\\rightarrow$ **CI**: `[{ci_low:.1f}%, {ci_high:.1f}%]` (based on $N={c['total_samples']}$ evaluations).")

# ----------------- TAB 3: RESEARCH REPORT -----------------
with tab_report:
    st.markdown("#### Dissertation-Ready Research Report")
    st.markdown("This automated report compiles your evaluation configurations, metrics, and statistical analysis into a formatted draft suitable for research papers.")
    
    # Generate Markdown Report
    report_md = f"""# Prompt Engineering Evaluation Report: {selected_study}

## Abstract
This evaluation study compares the performance and footprints of different prompt engineering configurations under a controlled evaluation environment. The study aims to address the hypothesis: *"{study_data['research_question']}"*. Our results indicate that **{winner['config_name']}** achieves the highest classification accuracy of **{winner['accuracy']*100:.1f}%** on target LLM model **{winner['model']}**.

## 1. Introduction
Prompt engineering plays a critical role in optimizing Large Language Model (LLM) performance for task-specific downstream evaluations. In this controlled session, we tested the research question: *"{study_data['research_question']}"*. We systematically varied prompting strategies and benchmarked them side-by-side to understand the trade-offs between precision, response latency, and token efficiency.

## 2. Experimental Setup
All configurations were benchmarked under a fixed evaluation environment to isolate the prompting variables:
- **Benchmark Dataset**: {env['dataset_id']}
- **Sample size ($N$)**: {env['total_samples']} samples per configuration
- **Target LLM Model**: {env['model']}
- **Execution Configs**: Temperature = {db.query(ExperimentRun).filter(ExperimentRun.experiment_id==env['experiment_id']).first().metadata_rel.temperature if db.query(ExperimentRun).filter(ExperimentRun.experiment_id==env['experiment_id']).first().metadata_rel else '0.0'}, Top P = 1.0, Seed = 42.

### Evaluated Variables
We tested {len(cfg_stats)} prompt engineering configurations:
"""
    for c in cfg_stats:
        report_md += f"- **{c['config_name']}**: Evaluates strategy parameters with a sample-limit of {c['total_samples']} evaluations.\n"
        
    report_md += """
## 3. Results Matrix
The following table summarizes the mean accuracy, latency consistency (mean $\\pm$ standard deviation), and token cost structures:

| Configuration | Accuracy | F1 Score | Mean Latency | Cost (per Run) | Tokens (mean) |
| :--- | :---: | :---: | :---: | :---: | :---: |
"""
    for c in cfg_stats:
        report_md += f"| {c['config_name']} | {c['accuracy']*100:.1f}% | {c['f1']:.3f} | {c['latency_mean']:.0f} ± {c['latency_std']:.0f} ms | ${c['cost_mean']:.5f} | {c['tokens_mean']:.0f} |\n"
        
    report_md += f"""
## 4. Statistical Analysis & Discussion
We performed statistical hypothesis testing using `scipy.stats` to check validity:
- **Accuracy Significance**: The proportions test yielded a p-value of `{p_val:.4e}`. {"This confirms that accuracy gains are statistically significant (p < 0.05)." if p_val < 0.05 else "This suggests accuracy variations are statistically negligible at this sample size (p >= 0.05)."}
- **Latency Significance**: Response speed variation statistical test returned p-value `{t_stat if len(cfg_stats)==2 else f_stat}`.

## 5. Conclusion
Based on the empirical evidence gathered, we recommend using **{winner['config_name']}** for production deployment as it offers optimal performance-cost trade-offs.
"""

    st.markdown('<div class="report-box">', unsafe_allow_html=True)
    st.markdown(report_md)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.download_button(
        label="📥 Download Research Report (.md)",
        data=report_md,
        file_name=f"peer_research_report_{selected_study.replace(' ', '_').lower()}.md",
        mime="text/markdown",
        use_container_width=True
    )

# ----------------- TAB 4: AUDIT LOGS -----------------
with tab_audit:
    st.markdown("#### Sample Predictions Audit Logs")
    
    cfg_options = {c["config_name"]: c["experiment_id"] for c in cfg_stats}
    selected_cfg_lbl = st.selectbox("Select Configuration to Audit", list(cfg_options.keys()))
    selected_cfg_id = cfg_options[selected_cfg_lbl]
    
    runs = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == selected_cfg_id).all()
    selected_run_num = st.selectbox("Select Run Number", [r.run_number for r in runs])
    
    target_run = db.query(ExperimentRun).filter(
        ExperimentRun.experiment_id == selected_cfg_id,
        ExperimentRun.run_number == selected_run_num
    ).first()
    
    if target_run and target_run.responses:
        responses_list = []
        for resp in sorted(target_run.responses, key=lambda x: x.sample_index):
            responses_list.append({
                "Index": resp.sample_index,
                "Prediction": resp.prediction,
                "Ground Truth": resp.ground_truth,
                "Correct": "🟢 Yes" if resp.is_correct else "🔴 No",
                "Latency (ms)": resp.latency,
                "Tokens": resp.input_tokens + resp.output_tokens,
                "Cost ($)": f"${resp.cost:.5f}"
            })
        st.dataframe(pd.DataFrame(responses_list), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("##### Detailed Prompt Payload Inspect")
        selected_log_idx = st.slider("Select Sample Index to View Payload", 0, len(target_run.responses)-1, 0)
        selected_resp = sorted(target_run.responses, key=lambda x: x.sample_index)[selected_log_idx]
        
        st.code(selected_resp.prompt, language="text")
    else:
        st.info("No responses found for this configuration run.")

# ----------------- TAB 5: EXPORT PACKAGE -----------------
with tab_export:
    st.markdown("#### Download Evaluation Data Package")
    st.markdown("Download raw logs, predictions, latencies, and metadata to CSV/JSON format.")
    
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        if st.button("📥 Export JSON Logs", use_container_width=True):
            # Compile all study runs into a JSON file
            export_data = []
            for c in cfg_stats:
                run_obj = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == c["experiment_id"]).first()
                if run_obj:
                    resps = []
                    for r in run_obj.responses:
                        resps.append({
                            "index": r.sample_index,
                            "prompt": r.prompt,
                            "prediction": r.prediction,
                            "ground_truth": r.ground_truth,
                            "correct": r.is_correct,
                            "latency": r.latency,
                            "cost": r.cost
                        })
                    export_data.append({
                        "config_name": c["config_name"],
                        "accuracy": c["accuracy"],
                        "latency_mean": c["latency_mean"],
                        "responses": resps
                    })
            
            os.makedirs("exports", exist_ok=True)
            export_path = f"exports/peer_study_{selected_study.replace(' ', '_').lower()}.json"
            with open(export_path, "w") as f:
                json.dump(export_data, f, indent=2)
                
            st.success(f"JSON data generated: {os.path.basename(export_path)}")
            with open(export_path, "r") as f:
                st.download_button(
                    label="Download JSON File",
                    data=f.read(),
                    file_name=os.path.basename(export_path),
                    mime="application/json",
                    use_container_width=True
                )
                
    with col_ex2:
        if st.button("📥 Export CSV Comparative Logs", use_container_width=True):
            # Build spreadsheet mapping each sample's results across configurations
            csv_rows = []
            for c in cfg_stats:
                run_obj = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == c["experiment_id"]).first()
                if run_obj:
                    for r in run_obj.responses:
                        csv_rows.append({
                            "Study": selected_study,
                            "Configuration": c["config_name"],
                            "Sample Index": r.sample_index,
                            "Prediction": r.prediction,
                            "Ground Truth": r.ground_truth,
                            "Is Correct": r.is_correct,
                            "Latency (ms)": r.latency,
                            "Cost ($)": r.cost
                        })
            
            df_csv = pd.DataFrame(csv_rows)
            export_path = f"exports/peer_study_{selected_study.replace(' ', '_').lower()}.csv"
            df_csv.to_csv(export_path, index=False)
            
            st.success(f"CSV data generated: {os.path.basename(export_path)}")
            with open(export_path, "r") as f:
                st.download_button(
                    label="Download CSV File",
                    data=f.read(),
                    file_name=os.path.basename(export_path),
                    mime="text/csv",
                    use_container_width=True
                )

db.close()
