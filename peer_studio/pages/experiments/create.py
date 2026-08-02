import streamlit as st
import pandas as pd
import time
import json
import itertools
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.datasets.dataset_manager import DatasetManager
from backend.datasets.dataset_validator import DatasetValidator
from backend.prompts.prompt_manager import PromptManager
from backend.fewshot.builder import FewShotBuilder
from backend.strategies.strategy_manager import StrategyManager
from backend.experiments.manager import ExperimentManager
from backend.providers import ProviderService
from backend.providers.models import Provider as DBProvider, Model as DBModel
from backend.strategies.models import PromptStrategy
from peer_studio.utils.ui import apply_custom_theme, render_header, render_step_header, inject_footer_spacer

# Apply page styling
apply_custom_theme()

# Initialize backend instances
dataset_mgr = DatasetManager()
prompt_mgr = PromptManager()
fewshot_builder = FewShotBuilder()
strat_mgr = StrategyManager()
experiment_mgr = ExperimentManager()
provider_service = ProviderService()

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
                template += "{% for ex in few_shot_examples %}\n### Example {{loop.index}}\n- **Input**: {{ex.input}}\n{% if ex.label_name %}- **Category**: {{ex.label_name}}\n{% endif %}- **Label**: {{ex.label}}\n\n{% endfor %}"
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
            template += '      {% if ex.label_name %}"category": "{{ex.label_name}}",\n{% endif %}'
            template += '      "label": "{{ex.label}}"\n'
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
            template += "    <input>{ex.input}</input>\n"
            template += "    {% if ex.label_name %}<category>{ex.label_name}</category>\n{% endif %}"
            template += "    <label>{ex.label}</label>\n"
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
                template += "{% for ex in few_shot_examples %}\nInput: {{ex.input}}\n{% if ex.label_name %}Category: {{ex.label_name}}\n{% endif %}Label: {{ex.label}}\n\n{% endfor %}"
            else:
                template += "{% for ex in few_shot_examples %}\nContext: {{ex.input}}\nQuestion: {{ex.question if ex.question else 'Question'}}\nAnswer: {{ex.label}}\n\n{% endfor %}"
            template += "{% endif %}\n"
            
        template += "Query:\n"
        if task == "classification":
            template += "Input: {{text}}\nLabel:"
        else:
            template += "Context: {{context}}\nQuestion: {{question}}\nAnswer:"
            
    return template

render_header(
    "Design Research Experiment", 
    "Set up a study with a fixed environment and generate configurations of prompting variables to test a research hypothesis.", 
    "science"
)

db = SessionLocal()

# Load datasets
datasets = dataset_mgr.list_datasets(db)

if not datasets:
    st.info("No datasets registered yet. Please go to **Resources > Datasets** to import a dataset first.")
    db.close()
    st.stop()

# Define parameter lists
STRUCTURES = ["Instruction", "Example-Based", "Mixed"]
FORMATS = ["Plain Text", "Markdown", "JSON", "XML"]
INST_STYLES = ["Simple", "Detailed", "Step-by-Step", "None"]
REASONINGS = ["None", "Chain-of-Thought"]
FEWSHOT_COUNTS = [0, 1, 3, 5]
SELECTIONS = ["Random", "Balanced", "Semantic", "Sequential"]
ORDERINGS = ["Original", "Random", "Similarity", "Reverse Similarity", "Alternating"]

# ----------------- STEP 1: HYPOTHESIS & FIXED ENVIRONMENT -----------------
render_step_header(1, "Setup Study & Fixed Environment", "Define study metadata and configure common benchmark environment constants.")

col_s1, col_s2 = st.columns(2)
with col_s1:
    study_name = st.text_input("Study Name", placeholder="e.g., Emotion Prompt Structure Study")
with col_s2:
    research_question = st.text_input("Research Question / Hypothesis", placeholder="e.g., Does prompt structure influence emotion classification accuracy?")

st.markdown("##### Environment Parameters (Constant)")
col_e1, col_e2, col_e3 = st.columns(3)
with col_e1:
    ds_options = {d.name: d.id for d in datasets}
    selected_ds_name = st.selectbox("Benchmark Dataset", list(ds_options.keys()))
    selected_ds_id = ds_options[selected_ds_name]
    dataset = dataset_mgr.get_dataset(db, selected_ds_id)
    
    versions = [v.version for v in dataset.versions]
    selected_ver = st.selectbox("Version", versions)
    df_dict = dataset_mgr.get_dataset_version_data(db, selected_ds_id, selected_ver)
    splits = list(df_dict.keys())
    active_split = st.selectbox("Evaluation Split", splits, index=splits.index("test") if "test" in splits else 0)
    active_df = df_dict[active_split]
    
    # Extract column mappings
    val_report = dataset_mgr.validate_dataset(active_df, dataset.task)
    mapping = val_report.get("column_mapping", {})
    text_col = mapping.get("text")
    label_col = mapping.get("label")
    top_p = 1.0

with col_e2:
    # Sync Providers
    db_providers = db.query(DBProvider).filter(DBProvider.enabled == True).all()
    
    # Run pre-flight checks on start to determine connection health
    provider_health = {}
    for p in db_providers:
        provider_health[p.id] = provider_service.health_check(db, p.id)
        
    provider_options = {}
    for p in db_providers:
        is_ok = provider_health.get(p.id, False)
        label = p.provider_name
        if not is_ok:
            if p.id == "ollama":
                label += " (🔴 Offline)"
            else:
                label += " (🔴 Unconfigured)"
        provider_options[label] = p.id
        
    selected_provider_name = st.selectbox("LLM Provider", list(provider_options.keys()))
    selected_provider_id = provider_options[selected_provider_name]
    is_selected_provider_healthy = provider_health.get(selected_provider_id, False)
    
    db_models = provider_service.list_models(db, provider_id=selected_provider_id)
    model_names = [m.model_name for m in db_models]
    if not model_names:
        if selected_provider_id == "gemini":
            model_names = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        elif selected_provider_id == "openai":
            model_names = ["gpt-4o-mini", "gpt-4o"]
        else:
            model_names = ["llama3.1:latest"]
            
    # Format model names in selectbox based on health status
    model_display_options = {}
    for m_name in model_names:
        label = m_name
        if not is_selected_provider_healthy:
            label += " (🔴 Unconfigured)"
        model_display_options[label] = m_name
        
    selected_model_display = st.selectbox("Model", list(model_display_options.keys()))
    selected_model = model_display_options[selected_model_display]
    
    if not is_selected_provider_healthy:
        if selected_provider_id == "ollama":
            st.error("🛑 **Ollama service is offline**. Please start Ollama locally before running.")
        else:
            st.error(f"🛑 **API Key Missing**: Gemini/OpenAI key is not set. Please add it to the `.env` file in the project root.")

with col_e3:
    col_ep1, col_ep2 = st.columns(2)
    with col_ep1:
        temperature = st.slider("Temperature", 0.0, 2.0, 0.0, 0.1)
        runs_per_config = st.number_input("Runs per Config", min_value=1, max_value=10, value=1, help="Runs count for stochastic variance evaluation.")
    with col_ep2:
        replication_seed = st.number_input("Replication Seed", value=42)
        sample_limit = st.number_input("Limit Sample Size", min_value=1, max_value=len(active_df), value=min(20, len(active_df)))

# ----------------- STEP 2: CHOOSE VARIABLES & CONFIGS -----------------
render_step_header(2, "Choose Comparison Mode & Variables", "Select prompt variables comparison strategy and populate test configurations.")

comp_mode = st.selectbox("Comparison Mode", ["Single Variable", "Two Variables (Grid)", "Manual Configurations", "Full Factorial"])

configs = []

if comp_mode == "Single Variable":
    col_v1, col_v2 = st.columns([1, 2])
    with col_v1:
        var_to_vary = st.selectbox("Variable to Vary", [
            "Prompt Structure", "Prompt Format", "Instruction Style", "Reasoning Style", 
            "Examples Count", "Example Selection Method", "Example Ordering Method"
        ])
    
    # Render value selectors
    with col_v2:
        if var_to_vary == "Prompt Structure":
            varied_vals = st.multiselect("Select structures to compare", STRUCTURES, default=STRUCTURES[:2])
        elif var_to_vary == "Prompt Format":
            varied_vals = st.multiselect("Select formats to compare", FORMATS, default=FORMATS[:2])
        elif var_to_vary == "Instruction Style":
            varied_vals = st.multiselect("Select instruction styles to compare", INST_STYLES, default=INST_STYLES[:2])
        elif var_to_vary == "Reasoning Style":
            varied_vals = st.multiselect("Select reasoning styles to compare", REASONINGS, default=REASONINGS)
        elif var_to_vary == "Examples Count":
            varied_vals = st.multiselect("Select example counts to compare", FEWSHOT_COUNTS, default=[0, 3])
        elif var_to_vary == "Example Selection Method":
            varied_vals = st.multiselect("Select example selection methods to compare", SELECTIONS, default=SELECTIONS[:2])
        else: # Ordering
            varied_vals = st.multiselect("Select example ordering methods to compare", ORDERINGS, default=ORDERINGS[:2])
            
    # Fixed parameters block
    st.markdown("##### Fixed Parameters values for other variables")
    col_fix1, col_fix2, col_fix3 = st.columns(3)
    with col_fix1:
        fix_struct = st.selectbox("Fixed Structure", STRUCTURES, index=2, disabled=(var_to_vary == "Prompt Structure"))
        fix_fmt = st.selectbox("Fixed Format", FORMATS, index=1, disabled=(var_to_vary == "Prompt Format"))
    with col_fix2:
        fix_style = st.selectbox("Fixed Instruction Style", INST_STYLES, index=1, disabled=(var_to_vary == "Instruction Style"))
        fix_reason = st.selectbox("Fixed Reasoning Style", REASONINGS, index=0, disabled=(var_to_vary == "Reasoning Style"))
    with col_fix3:
        fix_count = st.selectbox("Fixed Examples Count", FEWSHOT_COUNTS, index=2, disabled=(var_to_vary == "Examples Count"))
        fix_select = st.selectbox("Fixed Example Selection Method", SELECTIONS, index=0, disabled=(var_to_vary == "Example Selection Method"))
        fix_order = st.selectbox("Fixed Example Ordering Method", ORDERINGS, index=0, disabled=(var_to_vary == "Example Ordering Method"))

    # Generate Configurations list
    for val in varied_vals:
        cfg = {
            "structure": val if var_to_vary == "Prompt Structure" else fix_struct,
            "format": val if var_to_vary == "Prompt Format" else fix_fmt,
            "instruction_style": val if var_to_vary == "Instruction Style" else fix_style,
            "reasoning_style": val if var_to_vary == "Reasoning Style" else fix_reason,
            "example_count": val if var_to_vary == "Examples Count" else fix_count,
            "selection_strategy": val if var_to_vary == "Example Selection Method" else fix_select,
            "ordering_strategy": val if var_to_vary == "Example Ordering Method" else fix_order
        }
        configs.append(cfg)

elif comp_mode == "Two Variables (Grid)":
    col_g1, col_g2 = st.columns(2)
    variables = [
        "Prompt Structure", "Prompt Format", "Instruction Style", "Reasoning Style", 
        "Examples Count", "Example Selection Method", "Example Ordering Method"
    ]
    with col_g1:
        v1 = st.selectbox("Variable 1", variables, index=0)
        if v1 == "Prompt Structure": v1_vals = st.multiselect("V1 Values", STRUCTURES, default=STRUCTURES[:2])
        elif v1 == "Prompt Format": v1_vals = st.multiselect("V1 Values", FORMATS, default=FORMATS[:2])
        elif v1 == "Instruction Style": v1_vals = st.multiselect("V1 Values", INST_STYLES, default=INST_STYLES[:2])
        elif v1 == "Reasoning Style": v1_vals = st.multiselect("V1 Values", REASONINGS, default=REASONINGS)
        elif v1 == "Examples Count": v1_vals = st.multiselect("V1 Values", FEWSHOT_COUNTS, default=[0, 3])
        elif v1 == "Example Selection Method": v1_vals = st.multiselect("V1 Values", SELECTIONS, default=SELECTIONS[:2])
        else: v1_vals = st.multiselect("V1 Values", ORDERINGS, default=ORDERINGS[:2])
        
    with col_g2:
        v2 = st.selectbox("Variable 2", [v for v in variables if v != v1], index=3)
        if v2 == "Prompt Structure": v2_vals = st.multiselect("V2 Values", STRUCTURES, default=STRUCTURES[:2])
        elif v2 == "Prompt Format": v2_vals = st.multiselect("V2 Values", FORMATS, default=FORMATS[:2])
        elif v2 == "Instruction Style": v2_vals = st.multiselect("V2 Values", INST_STYLES, default=INST_STYLES[:2])
        elif v2 == "Reasoning Style": v2_vals = st.multiselect("V2 Values", REASONINGS, default=REASONINGS)
        elif v2 == "Examples Count": v2_vals = st.multiselect("V2 Values", FEWSHOT_COUNTS, default=[0, 3])
        elif v2 == "Example Selection Method": v2_vals = st.multiselect("V2 Values", SELECTIONS, default=SELECTIONS[:2])
        else: v2_vals = st.multiselect("V2 Values", ORDERINGS, default=ORDERINGS[:2])

    st.markdown("##### Fixed Parameters values for other variables")
    col_fix1, col_fix2, col_fix3 = st.columns(3)
    with col_fix1:
        fix_struct = st.selectbox("Fixed Structure", STRUCTURES, index=2, disabled=(v1 == "Prompt Structure" or v2 == "Prompt Structure"))
        fix_fmt = st.selectbox("Fixed Format", FORMATS, index=1, disabled=(v1 == "Prompt Format" or v2 == "Prompt Format"))
    with col_fix2:
        fix_style = st.selectbox("Fixed Instruction Style", INST_STYLES, index=1, disabled=(v1 == "Instruction Style" or v2 == "Instruction Style"))
        fix_reason = st.selectbox("Fixed Reasoning Style", REASONINGS, index=0, disabled=(v1 == "Reasoning Style" or v2 == "Reasoning Style"))
    with col_fix3:
        fix_count = st.selectbox("Fixed Examples Count", FEWSHOT_COUNTS, index=2, disabled=(v1 == "Examples Count" or v2 == "Examples Count"))
        fix_select = st.selectbox("Fixed Example Selection Method", SELECTIONS, index=0, disabled=(v1 == "Example Selection Method" or v2 == "Example Selection Method"))
        fix_order = st.selectbox("Fixed Example Ordering Method", ORDERINGS, index=0, disabled=(v1 == "Example Ordering Method" or v2 == "Example Ordering Method"))

    # Generate grid
    for val1, val2 in itertools.product(v1_vals, v2_vals):
        cfg = {
            "structure": val1 if v1 == "Prompt Structure" else (val2 if v2 == "Prompt Structure" else fix_struct),
            "format": val1 if v1 == "Prompt Format" else (val2 if v2 == "Prompt Format" else fix_fmt),
            "instruction_style": val1 if v1 == "Instruction Style" else (val2 if v2 == "Instruction Style" else fix_style),
            "reasoning_style": val1 if v1 == "Reasoning Style" else (val2 if v2 == "Reasoning Style" else fix_reason),
            "example_count": val1 if v1 == "Examples Count" else (val2 if v2 == "Examples Count" else fix_count),
            "selection_strategy": val1 if v1 == "Example Selection Method" else (val2 if v2 == "Example Selection Method" else fix_select),
            "ordering_strategy": val1 if v1 == "Example Ordering Method" else (val2 if v2 == "Example Ordering Method" else fix_order)
        }
        configs.append(cfg)

elif comp_mode == "Manual Configurations":
    if "manual_configs" not in st.session_state:
        st.session_state.manual_configs = [
            {"structure": "Instruction", "format": "Plain Text", "instruction_style": "Simple", "reasoning_style": "None", "example_count": 0, "selection_strategy": "Random", "ordering_strategy": "Original"}
        ]
        
    st.markdown("##### Configure individual configurations:")
    
    # Table list of current configurations
    df_man = pd.DataFrame(st.session_state.manual_configs)
    st.dataframe(df_man, use_container_width=True)
    
    col_add1, col_add2, col_add3 = st.columns(3)
    with col_add1:
        m_struct = st.selectbox("Structure", STRUCTURES, index=2)
        m_fmt = st.selectbox("Format", FORMATS, index=1)
    with col_add2:
        m_style = st.selectbox("Instruction Style", INST_STYLES, index=1)
        m_reason = st.selectbox("Reasoning Style", REASONINGS, index=0)
    with col_add3:
        m_count = st.selectbox("Few-shot Count", FEWSHOT_COUNTS, index=2)
        m_select = st.selectbox("Selection Strategy", SELECTIONS, index=0)
        m_order = st.selectbox("Ordering Strategy", ORDERINGS, index=0)
        
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Add Configuration", icon=":material/add:", use_container_width=True):
            st.session_state.manual_configs.append({
                "structure": m_struct,
                "format": m_fmt,
                "instruction_style": m_style,
                "reasoning_style": m_reason,
                "example_count": m_count,
                "selection_strategy": m_select,
                "ordering_strategy": m_order
            })
            st.rerun()
    with col_btn2:
        if st.button("Clear All", icon=":material/delete_sweep:", use_container_width=True):
            st.session_state.manual_configs = []
            st.rerun()
            
    configs = st.session_state.manual_configs

else: # Full Factorial
    st.markdown("##### Varied Parameters (Grid is generated across all selected combinations)")
    col_ff1, col_ff2 = st.columns(2)
    with col_ff1:
        v_struct = st.multiselect("Vary Structures", STRUCTURES, default=[STRUCTURES[0]])
        v_fmt = st.multiselect("Vary Formats", FORMATS, default=[FORMATS[0]])
        v_style = st.multiselect("Vary Instruction Styles", INST_STYLES, default=[INST_STYLES[0]])
        v_reason = st.multiselect("Vary Reasoning Styles", REASONINGS, default=[REASONINGS[0]])
    with col_ff2:
        v_count = st.multiselect("Vary Examples Counts", FEWSHOT_COUNTS, default=[FEWSHOT_COUNTS[0]])
        v_select = st.multiselect("Vary Example Selection Methods", SELECTIONS, default=[SELECTIONS[0]])
        v_order = st.multiselect("Vary Example Ordering Methods", ORDERINGS, default=[ORDERINGS[0]])
        
    for struct, fmt, style, reason, count, select, order in itertools.product(v_struct, v_fmt, v_style, v_reason, v_count, v_select, v_order):
        configs.append({
            "structure": struct,
            "format": fmt,
            "instruction_style": style,
            "reasoning_style": reason,
            "example_count": count,
            "selection_strategy": select,
            "ordering_strategy": order
        })

# Check semantic vector index if Semantic strategy selected in any config
for cfg in configs:
    if cfg["selection_strategy"] == "Semantic":
        from backend.fewshot.cache import FewShotCache
        cache = FewShotCache()
        if not cache.cache_exists(selected_ds_id, selected_ver, "all-MiniLM-L6-v2"):
            st.error("One or more configurations use 'Semantic' selection, which requires a compiled FAISS vector index. Please go to **Resources > Datasets > Vector Indexing** to build it first.", icon=":material/warning:")
            db.close()
            st.stop()

# ----------------- STEP 3: PREVIEW & INTERACTIVE Payloads -----------------
render_step_header(3, "Preview Configurations & Prompt Payloads", "Review auto-generated variables settings and evaluate rendered model prompts.")

if not configs:
    st.warning("No configurations generated. Adjust variable parameters above.")
else:
    # Display table of configurations
    cfg_display = []
    for idx, c in enumerate(configs):
        cfg_display.append({
            "Config Index": idx + 1,
            "Style (Structure)": c["structure"],
            "Format": c["format"],
            "Instruction": c["instruction_style"],
            "Reasoning": c["reasoning_style"],
            "Few-shot": c["example_count"],
            "Selection": c["selection_strategy"],
            "Ordering": c["ordering_strategy"]
        })
    st.dataframe(pd.DataFrame(cfg_display), use_container_width=True, hide_index=True)
    
    # Prompt preview selector
    st.markdown("##### Render Sample Prompt Preview")
    selected_cfg_idx = st.selectbox("Select Configuration to Preview", [i+1 for i in range(len(configs))]) - 1
    selected_cfg = configs[selected_cfg_idx]
    
    # Generate Jinja2 Template body
    tmp_template_body = generate_jinja_template(
        task=dataset.task,
        format_type=selected_cfg["format"],
        inst_style=selected_cfg["instruction_style"],
        reasoning=selected_cfg["reasoning_style"],
        count=selected_cfg["example_count"]
    )
    
    try:
        # Get details for first row in split to simulate render
        query_idx = st.slider("Select sample row to preview render payload", 0, len(active_df)-1, 0)
        row = active_df.iloc[query_idx]
        
        # Compile label mappings
        reverse_mapping = {}
        target_labels = None
        label_mapping = dataset_mgr.get_label_mapping(db, selected_ds_id)
        if dataset.task == "classification":
            if label_mapping:
                reverse_mapping = {str(name).strip().lower(): str(lbl_id) for lbl_id, name in label_mapping.items()}
                target_labels = [str(lbl_id) for lbl_id in sorted(label_mapping.keys())]
            else:
                target_labels = [str(lbl) for lbl in active_df[label_col].dropna().unique().tolist()]

        strategy_config = {
            "example_count": selected_cfg["example_count"],
            "selection_strategy": selected_cfg["selection_strategy"],
            "ordering_strategy": selected_cfg["ordering_strategy"],
            "embedding_model": "all-MiniLM-L6-v2"
        }

        # Fetch dynamic few-shot examples
        examples_list = []
        if selected_cfg["example_count"] > 0:
            fs_set = fewshot_builder.build_examples(
                db=db,
                dataset_id=selected_ds_id,
                dataset_version=selected_ver,
                query_index=query_idx,
                strategy_config=strategy_config,
                seed=replication_seed
            )
            for ex in fs_set.examples:
                lbl = str(ex.label).strip()
                if dataset.task == "classification" and reverse_mapping:
                    lbl_lower = lbl.lower()
                    if lbl_lower in reverse_mapping:
                        lbl = reverse_mapping[lbl_lower]
                
                # Resolve human-readable label name for preview
                lbl_name = ""
                if dataset.task == "classification" and label_mapping:
                    try:
                        lbl_name = label_mapping.get(int(lbl), label_mapping.get(lbl, ""))
                    except Exception:
                        lbl_name = ""

                examples_list.append({
                    "input": ex.input,
                    "label": lbl,
                    "label_name": lbl_name
                })

        # Prepare Jinja render dictionary
        payload = {
            "few_shot_examples": examples_list,
            "strategy": strategy_config
        }
        
        if dataset.task == "classification":
            payload["text"] = str(row[text_col])
            if target_labels:
                payload["target_labels"] = ", ".join(target_labels)
        else:
            payload["context"] = str(row[mapping.get("context")])
            payload["question"] = str(row[mapping.get("question")])

        # Prepend categories header (same as pipeline logic)
        labels_def_str = ""
        if dataset.task == "classification" and label_mapping:
            header_type = "Labels" if "sst" in dataset.name.lower() or "sst2" in dataset.name.lower() else "Categories"
            labels_def_lines = [f"{dataset.name} {header_type}", ""]
            for lbl_id in sorted(label_mapping.keys()):
                class_name = str(label_mapping[lbl_id]).capitalize()
                labels_def_lines.append(f"{lbl_id} = {class_name}")
            labels_def_str = "\n".join(labels_def_lines) + "\n\nReturn only the numeric label.\n"

        active_template_body = tmp_template_body
        if labels_def_str:
            if "{% if few_shot_examples %}" in active_template_body:
                active_template_body = active_template_body.replace(
                    "{% if few_shot_examples %}",
                    labels_def_str + "\n{% if few_shot_examples %}"
                )
            elif "Demonstration Examples:" in active_template_body:
                active_template_body = active_template_body.replace(
                    "Demonstration Examples:",
                    labels_def_str + "\nDemonstration Examples:"
                )
            else:
                active_template_body = f"{labels_def_str}\n{active_template_body}"

        # Render template body
        rendered_prompt = prompt_mgr.render_prompt(active_template_body, payload)
        
        st.markdown("**Rendered Prompt Preview**:")
        st.code(rendered_prompt, language="text" if selected_cfg["format"] == "Plain Text" else selected_cfg["format"].lower())
        
    except Exception as preview_err:
        st.warning(f"Unable to render prompt preview: {str(preview_err)}")

# ----------------- STEP 4: EXECUTE STUDY -----------------
render_step_header(4, "Launch Research Experiment", "Register prompting combinations and trigger asynchronous evaluation executions.")

run_disabled = not is_selected_provider_healthy
if st.button("Run Experiment", icon=":material/play_arrow:", type="primary", use_container_width=True, disabled=run_disabled):
    if not study_name:
        st.error("Please specify a Study Name.")
    elif not configs:
        st.error("You need at least 1 configuration to execute a study.")
    else:
        # Check provider health
        with st.spinner("Checking model provider connectivity..."):
            is_healthy = provider_service.health_check(db, selected_provider_id)
        if not is_healthy:
            st.error(f"🛑 **Model Provider Connection Failed**: Health check failed for '{selected_provider_id}'. "
                     f"Please make sure your API key (e.g. `GEMINI_API_KEY` for Google Gemini, or `OPENAI_API_KEY` for OpenAI) "
                     f"is set in the `.env` file in the project root, and that you have internet connectivity.")
        else:
            status_placeholder = st.empty()
            status_placeholder.info("Registering configurations and launching background runs...")
            # Map Study details
            # A PEER study is composed of multiple DB experiments, each representing one configuration.
            # We prefix the DB experiment name with `[Study Name]` to group them logically.
            first_exp_id = None
            
            for idx, cfg in enumerate(configs):
                cfg_label = f"{cfg['structure']}-{cfg['format']}-{cfg['example_count']}shot"
                db_exp_name = f"[{study_name}] {cfg_label}"
                
                # 1. Save Strategy record to database
                strat_id = f"strat_{cfg['structure'].lower()}_{cfg['selection_strategy'].lower()}_{cfg['example_count']}"
                db_strat = db.query(PromptStrategy).filter(PromptStrategy.id == strat_id).first()
                if not db_strat:
                    db_strat = PromptStrategy(
                        id=strat_id,
                        name=f"{cfg['structure']} {cfg['selection_strategy']} ({cfg['example_count']} shot)",
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
                    
                # 2. Save Dynamic template to database
                cfg_template_body = generate_jinja_template(
                    task=dataset.task,
                    format_type=cfg["format"],
                    inst_style=cfg["instruction_style"],
                    reasoning=cfg["reasoning_style"],
                    count=cfg["example_count"]
                )
                
                created_prompt = prompt_mgr.create_prompt(
                    db=db,
                    name=f"Auto-generated: {study_name} Config {idx+1} {int(time.time())}",
                    template_body=cfg_template_body,
                    task_type=dataset.task,
                    strategy=cfg["structure"],
                    format=cfg["format"],
                    instruction_style=cfg["instruction_style"],
                    reasoning_style=cfg["reasoning_style"],
                    description=f"Auto-compiled configuration '{cfg_label}' for study '{study_name}'",
                    tags=["auto-generated", "study-config"]
                )
                
                metadata_json = {
                    "study_name": study_name,
                    "research_question": research_question,
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
                
                # 4. Create DB Experiment representing this Configuration
                exp = experiment_mgr.create_experiment(
                    db=db,
                    name=db_exp_name,
                    description=description_str,
                    dataset_id=selected_ds_id,
                    template_id=created_prompt.id,
                    strategy_id=strat_id,
                    provider=selected_provider_id,
                    model=selected_model
                )
                
                if first_exp_id is None:
                    first_exp_id = exp.id
                
                # 5. Trigger runs in background
                experiment_mgr.run_experiment(
                    db=db,
                    experiment_id=exp.id,
                    runs=runs_per_config,
                    max_samples=sample_limit,
                    temperature=temperature,
                    top_p=top_p,
                    seed=replication_seed
                )
                
            st.toast(f"Successfully registered study and spawned executions for {len(configs)} configurations!")
            st.session_state.active_study_name = study_name
            st.session_state.active_experiment_id = first_exp_id
            
            status_placeholder.empty()
            # Redirect to Running page
            st.switch_page("peer_studio/pages/experiments/running.py")

inject_footer_spacer()

db.close()
