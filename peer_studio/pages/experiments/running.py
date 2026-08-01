import streamlit as st
import time
import json
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.experiments.manager import ExperimentManager
from backend.experiments.models import Experiment, ExperimentRun, Response

st.markdown("""
    <style>
    .running-card {
        background-color: #ffffff;
        border: 1px solid #dadce0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
    }
    .metric-row {
        display: flex;
        gap: 15px;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .mini-box {
        flex: 1;
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .mini-value {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1a73e8;
    }
    .mini-label {
        font-size: 0.75rem;
        color: #5f6368;
        margin-top: 3px;
    }
    .badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
    }
    .badge-correct { background-color: #e6f4ea; color: #137333; }
    .badge-incorrect { background-color: #fce8e6; color: #c5221f; }
    .badge-running { background-color: #e8f0fe; color: #1a73e8; }
    .badge-queued { background-color: #f1f3f4; color: #5f6368; }
    </style>
""", unsafe_allow_html=True)

st.title("⏳ Running Experiments Monitor")
st.markdown("Live streaming predictions and evaluation metrics from active background configurations.")

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
    st.subheader(f"Monitoring Study: {selected_study}")
with col_act2:
    if st.button("🛑 Cancel Study", use_container_width=True, help="Stop all configurations under this study"):
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
            
        status_badge_class = "badge-queued" if run.status == "Queued" else "badge-running" if run.status == "Running" else "badge-correct"
        
        r_col1, r_col2 = st.columns([3, 1])
        r_col1.markdown(f"### {cfg_label} (Run #{run.run_number}) <span class='badge {status_badge_class}'>{run.status}</span>", unsafe_allow_html=True)
        
        # Count progress
        completed_responses = db.query(Response).filter(Response.run_id == run.id).all()
        completed_count = len(completed_responses)
        
        # Default sample size limit
        total_samples = 20
        if run.metadata_rel and run.responses:
            total_samples = len(run.responses)
            
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
            badge_style = "badge-correct" if latest_resp.is_correct else "badge-incorrect"
            badge_label = "🟢 Correct" if latest_resp.is_correct else "🔴 Incorrect"
            
            col_s_1, col_s_2 = st.columns([1, 4])
            col_s_1.markdown(f"**Index**: `Row {latest_resp.sample_index}`")
            col_s_2.markdown(f"**Evaluation**: <span class='badge {badge_style}'>{badge_label}</span>", unsafe_allow_html=True)
            
            col_res1, col_res2 = st.columns(2)
            col_res1.markdown(f"**Prediction**: `{latest_resp.prediction}`")
            col_res2.markdown(f"**Expected**: `{latest_resp.ground_truth}`")
            
            with st.expander("Show Prompt Payload"):
                st.code(latest_resp.prompt, language="text")
                
        st.markdown("</div>", unsafe_allow_html=True)

# Auto refresh loop (1.5 seconds)
db.close()
time.sleep(1.5)
st.rerun()
