from backend.datasets.models import Dataset
import streamlit as st
import time
import json
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.experiments.manager import ExperimentManager
from backend.experiments.models import Experiment, ExperimentRun, Response

from peer_studio.utils.ui import apply_custom_theme, render_header, inject_footer_spacer, status_badge

# Apply page styles
apply_custom_theme()

st.markdown("""
    <style>
    .metric-row {
        display: flex;
        gap: 15px;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .mini-box {
        flex: 1;
        background-color: #FAFAFA;
        border: 1px solid #E7E7E7;
        border-radius: 10px;
        padding: 12px;
        text-align: center;
    }
    .mini-value {
        font-size: 1.3rem;
        font-weight: 700;
        color: #5E3A87;
    }
    .mini-label {
        font-size: 0.75rem;
        color: #666666;
        margin-top: 3px;
    }
    </style>
""", unsafe_allow_html=True)

render_header(
    "Running Experiments Monitor", 
    "Live streaming predictions and evaluation metrics from active background configurations.", 
    "hourglass_empty"
)

db = SessionLocal()
experiment_mgr = ExperimentManager()

# Find active runs
active_runs = db.query(ExperimentRun).filter(ExperimentRun.status.in_(["Queued", "Running"])).all()

if not active_runs:
    st.info("No active experiments are currently executing in the background.")
    st.markdown("Go to **Create Experiment** to launch a new evaluation study.")
    
    if "active_experiment_id" in st.session_state:
        recent_exp = experiment_mgr.get_experiment(db, st.session_state.active_experiment_id)
        if recent_exp:
            st.markdown("---")
            st.markdown(f"### Latest Study Registered: **{recent_exp.name.split(']')[0].replace('[', '') if ']' in recent_exp.name else recent_exp.name}**")
            if st.button("📊 View Study Results"):
                st.switch_page("peer_studio/pages/results/view.py")
    
    db.close()
    st.stop()

# Group active runs by Study Name
study_groups = {}
for r in active_runs:
    exp = r.experiment
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
    study_groups[study_name].append(r)

# Study selectbox
selected_study = st.selectbox("Active Study / Hypothesis", list(study_groups.keys()))
active_study_runs = study_groups[selected_study]

# Cancel controls
col_act1, col_act2 = st.columns([3, 1])
with col_act1:
    st.markdown(f'<h3 class="h3-style" style="margin-top: 0;">Monitoring Study: {selected_study}</h3>', unsafe_allow_html=True)
with col_act2:
    if st.button("Cancel Study", icon=":material/cancel:", use_container_width=True, help="Stop all configurations under this study"):
        for r in active_study_runs:
            experiment_mgr.cancel_experiment(db, r.experiment_id)
        st.toast("Cancellation command broadcasted to all configurations.")
        time.sleep(1)
        st.rerun()

st.markdown("---")

# Render each configuration run
# We group active runs by their configuration experiment
exp_ids = list(set([r.experiment_id for r in active_study_runs]))
db_exps = db.query(Experiment).filter(Experiment.id.in_(exp_ids)).all()

for exp in db_exps:
    cfg_runs = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == exp.id).all()
    
    # Render each run under this configuration
    for run in cfg_runs:
        st.markdown(f'<div class="running-card">', unsafe_allow_html=True)
        
        # Get configuration label
        cfg_label = exp.name
        if "]" in exp.name:
            cfg_label = exp.name.split("]")[-1].strip()
            
        badge_html = status_badge(run.status)
        
        r_col1, r_col2 = st.columns([3, 1])
        r_col1.markdown(f'<h3 class="h3-style" style="margin-top: 0; display: inline-flex; align-items: center; gap: 8px;">{cfg_label} (Run #{run.run_number}) {badge_html}</h3>', unsafe_allow_html=True)
        
        # Count progress
        completed_responses = db.query(Response).filter(Response.run_id == run.id).all()
        completed_count = len(completed_responses)
        
        # Get total sample limit from experiment description JSON
        total_samples = 20
        if exp.description:
            try:
                meta = json.loads(exp.description)
                if isinstance(meta, dict) and "sample_limit" in meta and meta["sample_limit"]:
                    total_samples = int(meta["sample_limit"])
                else:
                    dataset = db.query(Dataset).filter(Dataset.id == exp.dataset_id).first()
                    if dataset:
                        total_samples = dataset.samples
            except Exception:
                pass
            
        prog_ratio = 0.0
        if total_samples > 0:
            prog_ratio = min(1.0, completed_count / total_samples)
            
        r_col2.markdown(f"<div style='text-align: right; font-weight: bold;'>Progress: {completed_count} / {total_samples}</div>", unsafe_allow_html=True)
        st.progress(prog_ratio)
        
        # Stats row
        if completed_count > 0:
            correct_count = sum(1 for resp in completed_responses if resp.is_correct)
            running_acc = (correct_count / completed_count) * 100
            avg_latency = sum(resp.latency for resp in completed_responses) / completed_count
            total_cost = sum(resp.cost for resp in completed_responses)
            total_tokens = sum(resp.input_tokens + resp.output_tokens for resp in completed_responses)
            
            st.markdown(f"""
                <div class="metric-row">
                    <div class="mini-box">
                        <div class="mini-value">{running_acc:.1f}%</div>
                        <div class="mini-label">Running Accuracy</div>
                    </div>
                    <div class="mini-box">
                        <div class="mini-value">{avg_latency:.0f} ms</div>
                        <div class="mini-label">Avg Latency</div>
                    </div>
                    <div class="mini-box">
                        <div class="mini-value">${total_cost:.4f}</div>
                        <div class="mini-label">Total Cost</div>
                    </div>
                    <div class="mini-box">
                        <div class="mini-value">{total_tokens:,}</div>
                        <div class="mini-label">Accumulated Tokens</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Configuration run in queue. Waiting to pull sample evaluations...")
            
        # streaming logs
        latest_resp = db.query(Response).filter(Response.run_id == run.id).order_by(Response.sample_index.desc()).first()
        if latest_resp:
            st.markdown("**Latest Sample Activity**:")
            eval_status = "Correct" if latest_resp.is_correct else "Incorrect"
            badge_html = status_badge(eval_status)
            
            col_s_1, col_s_2 = st.columns([1, 4])
            col_s_1.markdown(f"**Index**: `Row {latest_resp.sample_index}`")
            col_s_2.markdown(f"**Evaluation**: {badge_html}", unsafe_allow_html=True)
            
            col_res1, col_res2 = st.columns(2)
            col_res1.markdown(f"**Prediction**: `{latest_resp.prediction}`")
            col_res2.markdown(f"**Expected**: `{latest_resp.ground_truth}`")
            
            with st.expander("Show Prompt Payload"):
                st.code(latest_resp.prompt, language="text")
                
        st.markdown("</div>", unsafe_allow_html=True)

inject_footer_spacer()

# Auto refresh loop (1.5 seconds)
db.close()
time.sleep(1.5)
st.rerun()
