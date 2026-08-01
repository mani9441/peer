import time
import json
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.experiments.manager import ExperimentManager
from backend.experiments.models import Experiment, ExperimentRun

st.markdown("""
    <style>
    .completed-card {
        background-color: #ffffff;
        border: 1px solid #dadce0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
        transition: border-color 0.2s;
    }
    .completed-card:hover {
        border-color: #1a73e8;
    }
    .comp-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1a73e8;
    }
    .comp-question {
        font-size: 0.95rem;
        font-style: italic;
        color: #3c4043;
        margin-top: 5px;
        margin-bottom: 15px;
    }
    .badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
    }
    .badge-comp { background-color: #e6f4ea; color: #137333; }
    </style>
""", unsafe_allow_html=True)

st.title("✅ Completed Research Studies")
st.markdown("Inspect and manage completed hypothesis-driven evaluation studies.")

db = SessionLocal()
experiment_mgr = ExperimentManager()

experiments = experiment_mgr.list_experiments(db)

# Group completed experiments by Study Name
# We consider an experiment "completed" if it has 0 active (Queued/Running) runs
active_run_counts = {}
for e in experiments:
    active_count = db.query(ExperimentRun).filter(
        ExperimentRun.experiment_id == e.id,
        ExperimentRun.status.in_(["Queued", "Running"])
    ).count()
    active_run_counts[e.id] = active_count

completed_exps = [e for e in experiments if active_run_counts[e.id] == 0]

if not completed_exps:
    st.info("No completed research studies found in database history.")
    st.markdown("Go to the **Create Experiment** wizard to execute a new prompting study.")
    db.close()
    st.stop()

study_groups = {}
for exp in completed_exps:
    study_name = "Independent Configurations"
    rq = "No hypothesis provided."
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
        rq = "Compare custom prompting variables."
        cfg_name = exp.name.split("]")[-1].strip()

    if study_name not in study_groups:
        study_groups[study_name] = {
            "research_question": rq,
            "model": exp.model,
            "created_at": exp.created_at,
            "configs": []
        }
    study_groups[study_name]["configs"].append((cfg_name, exp))

# Search filter
f_search = st.text_input("🔍 Search studies by name, hypothesis, or model...", "")

for s_name, data in study_groups.items():
    if f_search and f_search.lower() not in s_name.lower() and f_search.lower() not in data["research_question"].lower() and f_search.lower() not in data["model"].lower():
        continue
        
    st.markdown(f"""
        <div class="completed-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div class="comp-title">{s_name}</div>
                <span class="badge badge-comp">Completed</span>
            </div>
            <div class="comp-question"><b>Hypothesis</b>: {data["research_question"]}</div>
    """, unsafe_allow_html=True)
    
    col_d1, col_d2, col_d3 = st.columns(3)
    col_d1.markdown(f"**Model Target**: `{data['model']}`")
    col_d2.markdown(f"**Configurations**: `{len(data['configs'])}`")
    col_d3.markdown(f"**Created Date**: `{data['created_at'].strftime('%Y-%m-%d %H:%M')}`")
    
    # List configurations inside expander
    with st.expander("📋 View Configurations List"):
        cfg_rows = []
        for c_name, exp_obj in data["configs"]:
            runs = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == exp_obj.id).all()
            completed_runs = sum(1 for r in runs if r.status == "Completed")
            cfg_rows.append({
                "Configuration": c_name,
                "Runs Evaluated": f"{completed_runs} / {len(runs)}",
                "Experiment ID": exp_obj.id
            })
        st.dataframe(pd.DataFrame(cfg_rows), use_container_width=True, hide_index=True)
        
    st.markdown("<br/>", unsafe_allow_html=True)
    
    col_act1, col_act2 = st.columns([1, 1])
    with col_act1:
        if st.button("📊 View Results & Analytics", key=f"view_study_{s_name}", use_container_width=True):
            st.session_state.active_study_name = s_name
            # Set the first config's experiment ID as active fallback
            st.session_state.active_experiment_id = data["configs"][0][1].id
            st.switch_page("peer_studio/pages/results/view.py")
            
    with col_act2:
        if st.button("🗑️ Delete Study Record", key=f"delete_study_{s_name}", use_container_width=True, help="Permanently delete all configuration logs for this study"):
            with st.spinner("Deleting database logs..."):
                for _, exp_obj in data["configs"]:
                    experiment_mgr.delete_experiment(db, exp_obj.id)
            st.toast(f"Study '{s_name}' deleted successfully.")
            time.sleep(0.5)
            st.rerun()
            
    st.markdown("</div>", unsafe_allow_html=True)

db.close()
