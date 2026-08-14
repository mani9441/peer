from altair.utils import Optional
import streamlit as st
import time
import json
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.datasets.dataset_manager import DatasetManager
from backend.prompts.prompt_manager import PromptManager
from backend.strategies.strategy_manager import StrategyManager
from backend.experiments.manager import ExperimentManager
from backend.providers import ProviderService
from backend.strategies.models import PromptStrategy
from backend.experiments.models import Experiment, ExperimentRun, Response
from backend.datasets.models import Dataset
from peer_studio.utils.ui import apply_custom_theme, render_header, status_badge, inject_footer_spacer

# Apply page styling
apply_custom_theme()

# Initialize backend instances
dataset_mgr = DatasetManager()
prompt_mgr = PromptManager()
strat_mgr = StrategyManager()
experiment_mgr = ExperimentManager()
provider_service = ProviderService()

render_header(
    "Study Matrix Manager", 
    "Automate and manage the complete 36-study prompting evaluation matrix in controlled batches.", 
    "grid_on"
)

# Helper function to compile Jinja2 template body dynamically
def generate_jinja_template(task: str, format_type: str, inst_style: str, reasoning: str, count: int) -> str:
    if task == "classification":
        if inst_style == "Simple":
            inst = "Classify the input text into one of the target labels."
        elif inst_style == "Detailed":
            inst = "Analyze the input text carefully to identify the underlying emotional state or class. Choose the most appropriate class from the target labels list."
        elif inst_style == "Step-by-Step":
            inst = "Carefully analyze the input text step-by-step. Break down the key phrases and tone before selecting the correct label."
        else:
            inst = "Classify the text."
            
        if reasoning == "Chain-of-Thought":
            inst += " Output your step-by-step reasoning before providing the final classification label."
    else: # QA task
        if inst_style == "Simple":
            inst = "Answer the question based on the provided context passage."
        elif inst_style == "Detailed":
            inst = "Read the context passage thoroughly and answer the question. Ensure the answer is factual and directly supported by the text."
        elif inst_style == "Step-by-Step":
            inst = "Analyze the question and context step-by-step. Locate the evidence in the text first, then formulate the final answer."
        else:
            inst = "Answer the question using the context."
            
        if reasoning == "Chain-of-Thought":
            inst += " Output your step-by-step reasoning first, then write the final answer."

    if format_type == "Markdown":
        template = f"# Instruction\n{inst}\n\n"
        if task == "classification":
            template += "**Target Labels**: {{target_labels}}\n\n"
            
        if count > 0:
            template += "{% if few_shot_examples %}\n# Examples\n"
            if task == "classification":
                template += "{% for ex in few_shot_examples %}\n### Example {{loop.index}}\n- **Input**: {{ex.input}}\n- **Label**: {{ex.label_name if ex.label_name else ex.label}}\n\n{% endfor %}"
            else:
                template += "{% for ex in few_shot_examples %}\n### Example {{loop.index}}\n- **Context**: {{ex.input}}\n- **Question**: {{ex.question if ex.question else 'Question'}}\n- **Answer**: {{ex.label}}\n\n{% endfor %}"
            template += "{% endif %}\n"
            
        template += "# Query\n"
        if task == "classification":
            template += "- **Input**: {{text}}\n- **Label**:"
        else:
            template += "- **Context**: {{context}}\n- **Question**: {{question}}\n- **Answer**:"
            
    elif format_type == "JSON":
        template = "{\n"
        template += f'  "instruction": "{inst}",\n'
        if task == "classification":
            template += '  "target_labels": [{{target_labels}}],\n'
            
        if count > 0:
            template += '  "examples": [\n'
            template += '    {% if few_shot_examples %}{% for ex in few_shot_examples %}{\n'
            template += '      "input": "{{ex.input}}",\n'
            template += '      "label": "{{ex.label_name if ex.label_name else ex.label}}"\n'
            template += '    }{% if not loop.last %},{% endif %}{% endfor %}{% endif %}\n'
            template += '  ],\n'
            
        template += '  "query": {\n'
        if task == "classification":
            template += '    "input": "{{text}}"\n'
        else:
            template += '    "context": "{{context}}",\n'
            template += '    "question": "{{question}}"\n'
        template += '  }\n'
        template += "}"
        
    elif format_type == "XML":
        template = f"<prompt>\n<instruction>{inst}</instruction>\n"
        if task == "classification":
            template += "<target_labels>{{target_labels}}</target_labels>\n"
            
        if count > 0:
            template += "<examples>\n"
            template += "{% if few_shot_examples %}{% for ex in few_shot_examples %}\n"
            template += "  <example>\n"
            template += "    <input>{{ex.input}}</input>\n"
            template += "    <label>{{ex.label_name if ex.label_name else ex.label}}</label>\n"
            template += "  </example>\n"
            template += "{% endfor %}{% endif %}\n"
            template += "</examples>\n"
            
        template += "<query>\n"
        if task == "classification":
            template += "  <input>{{text}}</input>\n"
            template += "  <label></label>\n"
        else:
            template += "  <context>{{context}}</context>\n"
            template += "  <question>{{question}}</question>\n"
            template += "  <answer></answer>\n"
        template += "</query>\n</prompt>"
        
    else: # Plain Text
        template = f"Instruction:\n{inst}\n\n"
        if task == "classification":
            template += "Target Labels: {{target_labels}}\n\n"
            
        if count > 0:
            template += "{% if few_shot_examples %}\nDemonstration Examples:\n"
            if task == "classification":
                template += "{% for ex in few_shot_examples %}\nInput: {{ex.input}}\nLabel: {{ex.label_name if ex.label_name else ex.label}}\n\n{% endfor %}"
            else:
                template += "{% for ex in few_shot_examples %}\nContext: {{ex.input}}\nQuestion: {{ex.question if ex.question else 'Question'}}\nAnswer: {{ex.label}}\n\n{% endfor %}"
            template += "{% endif %}\n"
            
        template += "Query:\n"
        if task == "classification":
            template += "Input: {{text}}\nLabel:"
        else:
            template += "Context: {{context}}\nQuestion: {{question}}\nAnswer:"
            
    return template

db = SessionLocal()

# Verify datasets in the registry
datasets = dataset_mgr.list_datasets(db)
ag_news_ds = next((d for d in datasets if d.name.lower() in ["ag_news", "ag news"]), None)
boolq_ds = next((d for d in datasets if d.name.lower() in ["boolq"]), None)
sst2_ds = next((d for d in datasets if d.name.lower() in ["sst2", "sst-2"]), None)

missing_datasets = []
if not ag_news_ds: missing_datasets.append("AG News")
if not boolq_ds: missing_datasets.append("BoolQ")
if not sst2_ds: missing_datasets.append("SST-2")

# If datasets are missing, offer auto-import
if missing_datasets:
    st.warning(f"⚠️ **Missing Benchmark Datasets**: The following datasets are not registered in the system: {', '.join(missing_datasets)}.")
    st.markdown("You must import these benchmark datasets before generating the study matrix.")
    
    if st.button("🚀 Import Missing Datasets (Hugging Face)", type="primary"):
        with st.spinner("Downloading and importing missing benchmark datasets..."):
            try:
                from backend.database.db import self_heal_dataset_labels
                if not ag_news_ds:
                    dataset_mgr.load_dataset(
                        source="huggingface",
                        path="wangrongsheng/ag_news",
                        db=db,
                        save_in_registry=True,
                        task="classification",
                        description="4-class topic classification news dataset.",
                        language="English",
                        license="MIT"
                    )
                if not boolq_ds:
                    dataset_mgr.load_dataset(
                        source="huggingface",
                        path="google/boolq",
                        db=db,
                        save_in_registry=True,
                        task="qa",
                        description="BoolQ: Yes/No Reading comprehension QA benchmark dataset.",
                        language="English",
                        license="CC BY-SA 3.0"
                    )
                if not sst2_ds:
                    dataset_mgr.load_dataset(
                        source="huggingface",
                        path="stanfordnlp/sst2",
                        db=db,
                        save_in_registry=True,
                        task="classification",
                        description="Binary movie review sentiment analysis benchmark.",
                        language="English",
                        license="GLUE License"
                    )
                self_heal_dataset_labels()
                st.success("All missing datasets imported successfully! Reloading...")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Import failed: {e}")
    db.close()
    st.stop()

# Define the models and splits mapping
MODELS = ["llama3.1:latest", "mistral:7b", "qwen3:8b"]
DATASETS_MAPPING = {
    "AG News": {"obj": ag_news_ds, "split": "test"},
    "BoolQ": {"obj": boolq_ds, "split": "validation"},
    "SST-2": {"obj": sst2_ds, "split": "validation"}
}

# Define the 4 study types configuration templates
STUDY_TYPES = {
    "Prompt Structure": {
        "description": "Evaluate prompt structure variations (Instruction vs Example-Based vs Mixed)",
        "configs": [
            {"structure": "Instruction", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 3, "selection_strategy": "Random", "ordering_strategy": "Original"},
            {"structure": "Example-Based", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 3, "selection_strategy": "Random", "ordering_strategy": "Original"},
            {"structure": "Mixed", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 3, "selection_strategy": "Random", "ordering_strategy": "Original"}
        ]
    },
    "Example Count": {
        "description": "Evaluate few-shot example counts (0 vs 1 vs 3 vs 5 examples)",
        "configs": [
            {"structure": "Mixed", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 0, "selection_strategy": "Random", "ordering_strategy": "Original"},
            {"structure": "Mixed", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 1, "selection_strategy": "Random", "ordering_strategy": "Original"},
            {"structure": "Mixed", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 3, "selection_strategy": "Random", "ordering_strategy": "Original"},
            {"structure": "Mixed", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 5, "selection_strategy": "Random", "ordering_strategy": "Original"}
        ]
    },
    "Example Selection": {
        "description": "Evaluate example selection algorithms (Random vs Balanced vs Sequential)",
        "configs": [
            {"structure": "Mixed", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 3, "selection_strategy": "Random", "ordering_strategy": "Original"},
            {"structure": "Mixed", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 3, "selection_strategy": "Balanced", "ordering_strategy": "Original"},
            {"structure": "Mixed", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 3, "selection_strategy": "Sequential", "ordering_strategy": "Original"}
        ]
    },
    "Example Ordering": {
        "description": "Evaluate few-shot example ordering methods (Original vs Random vs Similarity)",
        "configs": [
            {"structure": "Mixed", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 3, "selection_strategy": "Random", "ordering_strategy": "Original"},
            {"structure": "Mixed", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 3, "selection_strategy": "Random", "ordering_strategy": "Random"},
            {"structure": "Mixed", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 3, "selection_strategy": "Random", "ordering_strategy": "Similarity"}
        ]
    }
}

# Settings section
st.markdown("### ⚙️ Matrix Settings")
col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
with col_cfg1:
    sample_limit = st.selectbox("Sample Limit per Configuration (evaluation subset)", [10, 20, 50, 100, 200, None], index=2, help="Determines how many records to pull from the target split for verification. Prevents long runs.")
with col_cfg2:
    replication_seed = st.number_input("Replication Seed", value=42, min_value=0, help="Fixed random seed for example selection repeatability.")
with col_cfg3:
    runs_per_config = st.number_input("Runs per Configuration", value=2, min_value=1, help="Number of times to run evaluation for statistical significance.")

st.markdown("---")

# Generate Study Matrix
st.markdown("### 📂 Initialization")
st.markdown("Generate all 36 studies and their configurations in the DB database. This action does **not** trigger executions immediately; it registers the experiment definitions so they can be inspected, and runs can be launched in controlled batches.")

# Fetch currently defined studies from the DB
def get_matrix_studies():
    exps = experiment_mgr.list_experiments(db)
    studies = {}
    for exp in exps:
        if exp.description:
            try:
                meta = json.loads(exp.description)
                if isinstance(meta, dict) and "study_name" in meta:
                    study_name = meta["study_name"]
                    if study_name not in studies:
                        studies[study_name] = []
                    studies[study_name].append(exp)
            except Exception:
                pass
    return studies

current_studies = get_matrix_studies()

# Helper to launch all studies in a single sequential background thread
def launch_sequential_matrix_campaign(db_session: Session, studies_dict: dict, runs_per_cfg: int, limit: Optional[int], seed: int):
    import threading
    from backend.experiments.utils import generate_uuid
    from backend.experiments.repository import ExperimentRepository
    from backend.experiments.executor import ExecutionPipeline, ACTIVE_THREADS
    
    run_ids = []
    for s_name, configs in studies_dict.items():
        for exp in configs:
            for r_num in range(1, runs_per_cfg + 1):
                run_id = generate_uuid("run")
                run_ids.append(run_id)
                
                ExperimentRepository.create_run(
                    db=db_session,
                    run_id=run_id,
                    experiment_id=exp.id,
                    run_number=r_num,
                    status="Queued"
                )
                
                ExperimentRepository.save_metadata(
                    db=db_session,
                    run_id=run_id,
                    temperature=0.00,
                    top_p=1.0,
                    seed=seed,
                    prompt_length=None,
                    fewshot_count=None,
                    selection_strategy=None,
                    ordering_strategy=None
                )
                
    def _sequential_worker(r_list, s_limit):
        pipeline = ExecutionPipeline()
        for rid in r_list:
            db_thread = SessionLocal()
            try:
                run = ExperimentRepository.get_run(db_thread, rid)
                if not run or run.status == "Cancelled":
                    continue
                pipeline.execute_run(db_thread, rid, max_samples=s_limit)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Sequential campaign error on run {rid}: {e}")
            finally:
                db_thread.close()
                if rid in ACTIVE_THREADS:
                    ACTIVE_THREADS.pop(rid, None)
                    
    t = threading.Thread(target=_sequential_worker, args=(run_ids, limit), daemon=True)
    t.start()
    for rid in run_ids:
        ACTIVE_THREADS[rid] = t
        
    return len(run_ids)

col_btn1, col_btn2 = st.columns([1, 3])
with col_btn1:
    if st.button("🏗️ Generate Study Matrix", type="primary", help="Pre-register all 36 studies and their configurations"):
        status_box = st.empty()
        status_box.info("Generating and registering experiment configurations in DB...")
        
        created_count = 0
        duplicate_count = 0
        
        for ds_name, ds_info in DATASETS_MAPPING.items():
            dataset = ds_info["obj"]
            split = ds_info["split"]
            
            for model in MODELS:
                for study_type, study_data in STUDY_TYPES.items():
                    study_name = f"{ds_name} - {model} - {study_type}"
                    
                    # Verify if this study is already registered
                    if study_name in current_studies:
                        duplicate_count += 1
                        continue
                        
                    for idx, cfg in enumerate(study_data["configs"]):
                        cfg_label = f"{cfg['structure']}-{cfg['example_count']}shot-{cfg['selection_strategy']}-{cfg['ordering_strategy']}"
                        db_exp_name = f"[{study_name}] {cfg_label}"
                        
                        # 1. Register strategy
                        strat_id = f"strat_{cfg['structure'].lower()}_{cfg['selection_strategy'].lower()}_{cfg['example_count']}_{cfg['ordering_strategy'].lower()}"
                        db_strat = db.query(PromptStrategy).filter(PromptStrategy.id == strat_id).first()
                        if not db_strat:
                            db_strat = PromptStrategy(
                                id=strat_id,
                                name=f"{cfg['structure']} {cfg['selection_strategy']} {cfg['ordering_strategy']} ({cfg['example_count']} shot)",
                                structure=cfg["structure"],
                                format=cfg["format"],
                                instruction_style=cfg["instruction_style"],
                                reasoning_style=cfg["reasoning_style"],
                                prompt_length="Medium",
                                example_count=cfg["example_count"],
                                selection_strategy=cfg["selection_strategy"],
                                ordering_strategy=cfg["ordering_strategy"]
                            )
                            db.add(db_strat)
                            db.commit()
                            
                        # 2. Compile prompt template
                        cfg_template_body = generate_jinja_template(
                            task=dataset.task,
                            format_type=cfg["format"],
                            inst_style=cfg["instruction_style"],
                            reasoning=cfg["reasoning_style"],
                            count=cfg["example_count"]
                        )
                        
                        created_prompt = prompt_mgr.create_prompt(
                            db=db,
                            name=f"Auto-generated: {study_name} Config {idx+1}",
                            template_body=cfg_template_body,
                            task_type=dataset.task,
                            strategy=cfg["structure"],
                            format=cfg["format"],
                            instruction_style=cfg["instruction_style"],
                            reasoning_style=cfg["reasoning_style"],
                            description=f"Auto-compiled prompting config '{cfg_label}' for study matrix.",
                            tags=["auto-generated", "study-matrix"]
                        )
                        
                        # 3. Create metadata JSON
                        metadata_json = {
                            "study_name": study_name,
                            "research_question": f"Evaluate the impact of {study_type} on dataset {ds_name} using model {model}.",
                            "config_name": cfg_label,
                            "sample_limit": sample_limit,
                            "variables": {
                                "structure": cfg["structure"],
                                "format": cfg["format"],
                                "instruction_style": cfg["instruction_style"],
                                "reasoning_style": cfg["reasoning_style"],
                                "example_count": cfg["example_count"],
                                "selection_strategy": cfg["selection_strategy"],
                                "ordering_strategy": cfg["ordering_strategy"]
                            }
                        }
                        description_str = json.dumps(metadata_json)
                        
                        # 4. Create the Experiment configuration (DB Experiment record)
                        exp = experiment_mgr.create_experiment(
                            db=db,
                            name=db_exp_name,
                            description=description_str,
                            dataset_id=dataset.id,
                            template_id=created_prompt.id,
                            strategy_id=strat_id,
                            provider="ollama",
                            model=model
                        )
                        created_count += 1
        
        status_box.empty()
        st.success(f"Matrix generation completed! Registered {created_count} configurations across new studies. (Skipped {duplicate_count} existing studies).")
        time.sleep(1)
        st.rerun()

with col_btn2:
    if current_studies:
        if st.button("🗑️ Reset Matrix Configurations", help="Deletes all registered study matrix experiments"):
            with st.spinner("Deleting registered matrix configuration records..."):
                delete_count = 0
                for s_name, exps in current_studies.items():
                    for exp in exps:
                        experiment_mgr.delete_experiment(db, exp.id)
                        delete_count += 1
            st.success(f"Successfully deleted {delete_count} configurations.")
            time.sleep(1)
            st.rerun()

st.markdown("---")

# ----------------- FULL MATRIX SEQUENTIAL CAMPAIGN SECTION -----------------
st.markdown("### 🔄 Full Matrix Sequential Execution Campaign")
st.markdown("Run all 36 studies (117 configurations) **one after another (strictly serially)** in a single background worker queue. This avoids simultaneous GPU/CPU resource overload.")

total_matrix_configs = sum(len(cfgs) for cfgs in current_studies.values()) if current_studies else 0
total_matrix_runs_target = total_matrix_configs * runs_per_config

global_queued = 0
global_running = 0
global_completed = 0
global_failed = 0
global_total = 0

if current_studies:
    for s_name, exps in current_studies.items():
        for exp in exps:
            runs_rec = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == exp.id).all()
            for r in runs_rec:
                global_total += 1
                if r.status == "Completed": global_completed += 1
                elif r.status == "Running": global_running += 1
                elif r.status == "Queued": global_queued += 1
                elif r.status in ["Failed", "Cancelled"]: global_failed += 1

col_camp1, col_camp2, col_camp3 = st.columns(3)
col_camp1.metric("Registered Studies", f"{len(current_studies)} / 36")
col_camp2.metric("Total Configurations", f"{total_matrix_configs} / 117")
col_camp3.metric("Execution Progress", f"{global_completed} / {global_total if global_total > 0 else total_matrix_runs_target} runs")

col_c_btn1, col_c_btn2 = st.columns([2, 2])
with col_c_btn1:
    if global_running > 0 or global_queued > 0:
        if st.button("⏹️ Cancel Sequential Campaign", type="secondary", width="stretch", help="Cancel all active queued and running runs"):
            with st.spinner("Cancelling background execution..."):
                for s_name, exps in current_studies.items():
                    for exp in exps:
                        experiment_mgr.cancel_experiment(db, exp.id)
            st.toast("Sequential campaign cancelled.")
            time.sleep(0.5)
            st.rerun()
    else:
        if st.button("🚀 Launch Full Sequential Campaign (Serially Run All 36 Studies)", type="primary", width="stretch", disabled=not current_studies, help="Runs all 36 studies sequentially one after another in a single background queue."):
            with st.spinner("Queueing 36 studies for sequential background execution..."):
                queued_count = launch_sequential_matrix_campaign(db, current_studies, runs_per_config, sample_limit, replication_seed)
            st.success(f"Successfully queued full campaign with {queued_count} runs sequentially!")
            time.sleep(1)
            st.rerun()

with col_c_btn2:
    if global_completed > 0 and current_studies:
        if st.button("📊 View Full Campaign Analytics", width="stretch"):
            first_study_exp = list(current_studies.values())[0][0]
            st.session_state.active_experiment_id = first_study_exp.id
            st.switch_page("peer_studio/pages/results/analytics.py")

st.markdown("---")

# 4. Interactive Matrix Viewer & Batch Launcher
st.markdown("### 📊 Interactive Study Matrix & Individual Batch Launchers")

if not current_studies:
    st.info("Study matrix has not been generated yet. Please click the button above to register the matrix in your database.")
else:
    # Organize studies by Dataset and Model
    matrix_groups = {}
    for ds_name in DATASETS_MAPPING.keys():
        matrix_groups[ds_name] = {}
        for model in MODELS:
            matrix_groups[ds_name][model] = {}
            for study_type in STUDY_TYPES.keys():
                study_name = f"{ds_name} - {model} - {study_type}"
                if study_name in current_studies:
                    matrix_groups[ds_name][model][study_type] = current_studies[study_name]
                    
    # Render selectors
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        view_dataset = st.selectbox("Filter by Dataset", list(DATASETS_MAPPING.keys()))
    with col_v2:
        view_model = st.selectbox("Filter by Model", MODELS)
        
    st.markdown(f"#### Dataset: `{view_dataset}` | Model: `{view_model}`")
    
    # Render studies for this dataset x model pair
    ds_model_studies = matrix_groups.get(view_dataset, {}).get(view_model, {})
    
    if not ds_model_studies:
        st.warning("No studies generated for this specific Dataset & Model combination.")
    else:
        for study_type, configs in ds_model_studies.items():
            study_name = f"{view_dataset} - {view_model} - {study_type}"
            
            # Check runs status for this study's configurations
            all_runs = []
            completed_runs = 0
            running_runs = 0
            queued_runs = 0
            failed_runs = 0
            total_runs = 0
            
            for exp in configs:
                runs = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == exp.id).all()
                all_runs.extend(runs)
                for r in runs:
                    total_runs += 1
                    if r.status == "Completed":
                        completed_runs += 1
                    elif r.status == "Running":
                        running_runs += 1
                    elif r.status == "Queued":
                        queued_runs += 1
                    elif r.status in ["Failed", "Cancelled"]:
                        failed_runs += 1
                        
            status_summary = "Not Started"
            
            if total_runs > 0:
                target_count = len(configs) * runs_per_config
                if completed_runs >= target_count and failed_runs == 0:
                    status_summary = "Completed"
                elif running_runs > 0:
                    status_summary = "Running"
                elif queued_runs > 0:
                    status_summary = "Queued"
                elif failed_runs > 0:
                    status_summary = "Failed"
                elif completed_runs > 0:
                    status_summary = "Completed"
            
            # Render card
            badge_html = status_badge(status_summary)
            st.markdown(f"""
                <div class="completed-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-family:'Outfit',sans-serif; font-size:16px; font-weight:600; color:#1A1A1A;">{study_type} Study</span>
                        {badge_html}
                    </div>
                    <p style="font-size:13px; color:#666666; margin-bottom:12px;">{STUDY_TYPES[study_type]['description']}</p>
            """, unsafe_allow_html=True)
            
            target_display_runs = len(configs) * runs_per_config
            col_st1, col_st2, col_st3 = st.columns([1, 1, 1])
            col_st1.markdown(f"**Configurations**: `{len(configs)}`")
            col_st2.markdown(f"**Execution Runs**: `{completed_runs} / {total_runs if total_runs > 0 else target_display_runs} completed`")
            
            with col_st3:
                # Add action controls
                if status_summary in ["Not Started", "Failed"]:
                    btn_label = "🚀 Launch Batch" if status_summary == "Not Started" else "🔄 Relaunch Batch"
                    help_txt = f"Queues {runs_per_config} runs per configuration in the background thread."
                    if st.button(btn_label, key=f"launch_{study_name}", help=help_txt, width='stretch'):
                        with st.spinner("Queueing batch runs..."):
                            for exp in configs:
                                try:
                                    meta = json.loads(exp.description)
                                    s_limit = meta.get("sample_limit", sample_limit)
                                except Exception:
                                    s_limit = sample_limit
                                    
                                experiment_mgr.run_experiment(
                                    db=db,
                                    experiment_id=exp.id,
                                    runs=runs_per_config,
                                    max_samples=s_limit,
                                    temperature=0.00,
                                    top_p=1.0,
                                    seed=replication_seed
                                )
                        st.toast(f"Study '{study_name}' queued successfully!")
                        time.sleep(0.5)
                        st.rerun()
                elif status_summary in ["Queued", "Running"]:
                    if st.button("⏹️ Cancel Runs", key=f"cancel_{study_name}", width='stretch'):
                        with st.spinner("Cancelling active runs..."):
                            for exp in configs:
                                experiment_mgr.cancel_experiment(db, exp.id)
                        st.toast(f"Cancelled runs for '{study_name}'.")
                        time.sleep(0.5)
                        st.rerun()
                elif status_summary == "Completed":
                    if st.button("📊 View Analytics", key=f"view_{study_name}", width='stretch'):
                        st.session_state.active_study_name = study_name
                        st.session_state.active_experiment_id = configs[0].id
                        st.switch_page("peer_studio/pages/results/view.py")
                        
            # Expander for inspecting detailed configuration list
            with st.expander("Show Configurations Detail"):
                cfg_list = []
                for exp in configs:
                    try:
                        meta = json.loads(exp.description)
                        vars_dict = meta.get("variables", {})
                    except Exception:
                        vars_dict = {}
                    runs_rec = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == exp.id).all()
                    run_statuses = ", ".join([f"Run #{r.run_number}: {r.status}" for r in runs_rec]) or "No runs created"
                    cfg_list.append({
                        "Config Name": exp.name.split("]")[-1].strip(),
                        "Structure": vars_dict.get("structure"),
                        "Examples": vars_dict.get("example_count"),
                        "Selection": vars_dict.get("selection_strategy"),
                        "Ordering": vars_dict.get("ordering_strategy"),
                        "Run Statuses": run_statuses
                    })
                st.dataframe(cfg_list, use_container_width=True)
                
            st.markdown("</div>", unsafe_allow_html=True)

db.close()
inject_footer_spacer()
