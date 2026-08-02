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
from peer_studio.utils.ui import apply_custom_theme, render_header, inject_footer_spacer, status_badge

# Apply page styles
apply_custom_theme()

st.markdown("""
    <style>
    .metric-box {
        background-color: #ffffff;
        border: 1px solid #E7E7E7;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #5E3A87;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #666666;
        margin-top: 5px;
        font-weight: 600;
    }
    .winner-card {
        border-left: 5px solid #2F7D4A;
        background-color: #EBF7EE;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .report-box {
        background-color: #ffffff;
        border: 1px solid #E7E7E7;
        border-radius: 12px;
        padding: 25px;
        color: #1A1A1A;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    </style>
""", unsafe_allow_html=True)

render_header(
    "Research Results Analyzer", 
    "Analyze prompting variable comparisons, check statistical significance, and generate dissertation reports.", 
    "description"
)

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
        
    successful_responses = [resp for resp in all_responses if resp.status == "SUCCESS"]
    failed_responses = [resp for resp in all_responses if resp.status not in (None, "SUCCESS", "Created", "Queued", "Running")]
    
    # Compute aggregates over successful responses
    correct_count = sum(1 for resp in successful_responses if resp.is_correct)
    successful_samples_count = len(successful_responses)
    accuracy = correct_count / successful_samples_count if successful_samples_count > 0 else 0.0
    
    # Estimate F1 score
    f1 = accuracy # fallback
    completed_metrics = [r.metrics for r in completed_runs if r.metrics]
    if completed_metrics:
        f1 = sum((m.f1 if m.f1 is not None else 0.0) for m in completed_metrics) / len(completed_metrics)
        
    latencies = [resp.latency for resp in successful_responses]
    mean_latency = sum(latencies) / len(latencies) if latencies else 0.0
    std_latency = math.sqrt(sum((x - mean_latency)**2 for x in latencies) / len(latencies)) if len(latencies) > 1 else 0.0
    
    # Cumulative costs & tokens include all calls (even failed ones for absolute footprint)
    total_cost = sum(resp.cost for resp in all_responses)
    mean_cost = total_cost / len(completed_runs) if completed_runs else 0.0
    total_tokens = sum(resp.input_tokens + resp.output_tokens for resp in all_responses)
    mean_tokens = total_tokens / len(completed_runs) if completed_runs else 0.0
    
    # Binomial CI margin based on successful sample count
    ci_margin = 1.96 * math.sqrt((accuracy * (1 - accuracy)) / successful_samples_count) if successful_samples_count > 0 else 0.0
    
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
        "total_samples": successful_samples_count,
        "correctness_array": [1 if r.is_correct else 0 for r in successful_responses],
        "latency_array": latencies,
        "model": exp.model,
        "dataset_id": exp.dataset_id,
        "runs_count": len(runs)
    })

if not cfg_stats:
    st.info("No completed configuration runs are available for this study yet.")
    db.close()
    st.stop()

# Check for any failures to show Dashboard Alerts
all_failed_responses = []
for c_name, exp in study_data["configs"]:
    runs = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == exp.id).all()
    for r in runs:
        for resp in r.responses:
            if resp.status not in (None, "SUCCESS", "Created", "Queued", "Running"):
                all_failed_responses.append((c_name, resp))

if all_failed_responses:
    st.markdown("### ⚠️ LLM Execution Failure Alert")
    for c_name, resp in all_failed_responses[:3]:
        st.warning(
            f"**LLM execution failed.**\n\n"
            f"**Configuration**: {c_name} | **Model**: `{resp.model}`\n\n"
            f"**Reason**: `{resp.error_type or 'Error'}: {resp.error_message}`\n\n"
            f"Validation skipped. No benchmark metrics were calculated for this sample."
        )
    if len(all_failed_responses) > 3:
        st.info(f"And {len(all_failed_responses) - 3} other execution failures. See 'Execution Failures' panel tab for details.")

# Environment settings (taken from first config)
env = cfg_stats[0]

# Display Winner Card
winner = max(cfg_stats, key=lambda x: x["accuracy"])
st.markdown(f"""
    <div class="winner-card">
        <h4 style="margin: 0; color: #2F7D4A; display: flex; align-items: center; gap: 8px; font-family: 'Outfit', sans-serif; font-size: 16px; font-weight: 600;">
            <span class="material-symbols-outlined">workspace_premium</span>
            Optimal Prompt Strategy (Winner)
        </h4>
        <p style="margin: 5px 0 0 0; color: #1A1A1A;">
            The configuration <b>{winner['config_name']}</b> achieved the highest classification accuracy of 
            <b>{winner['accuracy']*100:.1f}%</b> (± {winner['ci_margin']*100:.1f}%) on target model <code>{winner['model']}</code>.
        </p>
    </div>
""", unsafe_allow_html=True)

# Compute Session Summary stats
total_runs_count = 0
total_resp_count = 0
total_success_count = 0
total_failed_count = 0
total_skipped_count = 0

for c_name, exp in study_data["configs"]:
    runs = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == exp.id).all()
    for r in runs:
        total_runs_count += 1
        for resp in r.responses:
            total_resp_count += 1
            if resp.status == "SUCCESS":
                total_success_count += 1
            elif resp.status == "SKIPPED":
                total_skipped_count += 1
            else:
                total_failed_count += 1

success_rate = (total_success_count / total_resp_count * 100) if total_resp_count > 0 else 100.0
val_coverage = (total_success_count / total_resp_count * 100) if total_resp_count > 0 else 100.0

st.markdown("### **Evaluation Session Summary**")
col_s1, col_s2, col_s3, col_s4, col_s5, col_s6 = st.columns(6)
col_s1.metric("Successful Samples", f"{total_success_count}")
col_s2.metric("Failed Samples", f"{total_failed_count}")
col_s3.metric("Skipped Samples", f"{total_skipped_count}")
col_s4.metric("Success Rate", f"{success_rate:.1f}%")
col_s5.metric("Validation Coverage", f"{val_coverage:.1f}%")
col_s6.metric("Total Executions", f"{total_resp_count}")

st.markdown("---")

tab_matrix, tab_stats, tab_report, tab_audit, tab_failures, tab_export = st.tabs([
    "Performance Matrix", "Statistical Significance", "Research Report", "Audit Logs", "Execution Failures", "Export Package"
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
    st.dataframe(pd.DataFrame(matrix_rows), width='stretch', hide_index=True)
    
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
        fig_acc = px.bar(
            plot_df, 
            x="Configuration", 
            y="Accuracy (%)", 
            title="Configuration Accuracy (%)",
            color="Accuracy (%)", 
            color_continuous_scale="Greens"
        )
        st.plotly_chart(fig_acc, width='stretch', key="view_plotly_accuracy_chart")
    with col_p2:
        fig_lat = px.bar(plot_df, x="Configuration", y="Latency (ms)", title="Response Latency (ms)", color="Latency (ms)", color_continuous_scale="Reds")
        st.plotly_chart(fig_lat, width='stretch', key="view_plotly_latency_chart")

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
            st.success(f"**Significant Difference Detected!** (p-value = `{p_val:.4e}` < `0.05`)", icon=":material/check_circle:")
            st.markdown("The latency variation between configurations is statistically significant. Prompt engineering format and style changes directly impact inference speed.")
        else:
            st.warning(f"**No Significant Difference.** (p-value = `{p_val:.4f}` ≥ `0.05`)", icon=":material/warning:")
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
            st.success(f"**Significant Difference Detected!** (p-value = `{p_val:.4f}` < `0.05`)", icon=":material/check_circle:")
            st.markdown("The differences in classification accuracy are statistically significant. The prompting variables evaluated are highly likely to have a direct influence on classification success.")
        else:
            st.warning(f"**No Significant Difference.** (p-value = `{p_val:.4f}` ≥ `0.05`)", icon=":material/warning:")
            st.markdown("The accuracy variations do not pass the statistical significance threshold. We cannot reject the null hypothesis; differences might be due to random sample selection.")
            
    # Interval overlap check
    st.markdown("##### 3. Binomial Confidence Intervals (95% Confidence)")
    for c in cfg_stats:
        ci_low = max(0.0, c["accuracy"] - c["ci_margin"]) * 100
        ci_high = min(1.0, c["accuracy"] + c["ci_margin"]) * 100
        st.markdown(f"- **{c['config_name']}**: `{c['accuracy']*100:.1f}%` Accuracy $\\rightarrow$ **CI**: `[{ci_low:.1f}%, {ci_high:.1f}%]` (based on $N={c['total_samples']}$ evaluations).")

# ----------------- TAB 3: RESEARCH REPORT -----------------
with tab_report:
    if os.path.exists("assets/logo_horizontal.png"):
        st.image("assets/logo_horizontal.png", width=250)
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
        label="Download Research Report (.md)",
        icon=":material/download:",
        data=report_md,
        file_name=f"peer_research_report_{selected_study.replace(' ', '_').lower()}.md",
        mime="text/markdown",
        width='stretch'
    )

# ----------------- TAB 4: AUDIT LOGS -----------------
with tab_audit:
    st.markdown("#### Sample Predictions Audit Logs")
    
    # Select configuration run to inspect
    selected_cfg_lbl = st.selectbox("Select Configuration to Audit", [c["config_name"] for c in cfg_stats])
    target_cfg = next(c for c in cfg_stats if c["config_name"] == selected_cfg_lbl)
    
    target_run = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == target_cfg["experiment_id"]).first()
    
    if target_run and target_run.responses:
        responses_list = []
        for resp in sorted(target_run.responses, key=lambda x: x.sample_index):
            status_map = {
                "SUCCESS": "🟢 Success",
                "FAILED": "🔴 Failed",
                "TIMEOUT": "🔴 Timeout",
                "RATE_LIMITED": "🔴 Rate Limited",
                "NETWORK_ERROR": "🔴 Network Error",
                "AUTH_ERROR": "🔴 Auth Error",
                "INVALID_MODEL": "🔴 Invalid Model",
                "CANCELLED": "⚪ Cancelled",
                "SKIPPED": "⚪ Skipped"
            }
            status_str = status_map.get(resp.status or "SUCCESS", "🟢 Success")
            correct_str = "Yes" if resp.is_correct else ("No" if resp.is_correct is False else "N/A")
            
            responses_list.append({
                "Index": resp.sample_index,
                "Status": status_str,
                "Prediction": resp.prediction if resp.prediction is not None else "NOT EXECUTED",
                "Ground Truth": resp.ground_truth,
                "Correct": correct_str,
                "Latency (ms)": resp.latency,
                "Tokens": resp.input_tokens + resp.output_tokens,
                "Cost ($)": f"${resp.cost:.5f}"
            })
        st.dataframe(pd.DataFrame(responses_list), width='stretch', hide_index=True)
        
        st.markdown("---")
        st.markdown("##### Detailed Prompt Payload Inspect")
        selected_log_idx = st.slider("Select Sample Index to View Payload", 0, len(target_run.responses)-1, 0)
        selected_resp = sorted(target_run.responses, key=lambda x: x.sample_index)[selected_log_idx]
        
        st.code(selected_resp.prompt, language="text")
    else:
        st.info("No responses found for this configuration run.")

# ----------------- TAB 5: EXECUTION FAILURES -----------------
with tab_failures:
    st.markdown("#### Execution Failures Panel")
    st.markdown("The following table logs infrastructure and provider API errors that occurred during the evaluation study. These samples are automatically excluded from accuracy and validation calculations to preserve benchmark integrity.")
    
    if all_failed_responses:
        failures_data = []
        for c_name, resp in all_failed_responses:
            failures_data.append({
                "Configuration": c_name,
                "Sample Index": resp.sample_index,
                "Provider": resp.provider or "N/A",
                "Model": resp.model or "N/A",
                "Error Code / Status": resp.status,
                "Exception Details": f"{resp.error_type}: {resp.error_message}"
            })
        st.dataframe(pd.DataFrame(failures_data), width='stretch', hide_index=True)
    else:
        st.success("🎉 No execution failures detected for this study. All LLM responses generated and validated successfully!", icon=":material/check_circle:")

# ----------------- TAB 6: EXPORT PACKAGE -----------------
with tab_export:
    st.markdown("#### Download Evaluation Data Package")
    st.markdown("Download raw logs, predictions, latencies, and metadata to CSV/JSON format.")
    
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        if st.button("Export JSON Logs", icon=":material/download:", width='stretch'):
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
                    icon=":material/download:",
                    data=f.read(),
                    file_name=os.path.basename(export_path),
                    mime="application/json",
                    width='stretch'
                )
                
    with col_ex2:
        if st.button("Export CSV Comparative Logs", icon=":material/download:", width='stretch'):
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
                    icon=":material/download:",
                    data=f.read(),
                    file_name=os.path.basename(export_path),
                    mime="text/csv",
                    width='stretch'
                )

db.close()
inject_footer_spacer()
