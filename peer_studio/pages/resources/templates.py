import streamlit as st
import pandas as pd
import json
from backend.database.db import SessionLocal
from backend.prompts.prompt_manager import PromptManager
from backend.datasets.dataset_manager import DatasetManager

# Page CSS Styling
st.markdown("""
    <style>
    .sub-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #202124;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .card {
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #dadce0;
        background-color: #ffffff;
        margin-bottom: 10px;
    }
    .badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .badge-pass { background-color: #e6f4ea; color: #137333; }
    .badge-fail { background-color: #fce8e6; color: #c5221f; }
    .badge-info { background-color: #e8f0fe; color: #1a73e8; }
    .diff-added { color: green; background-color: #e6f4ea; }
    .diff-removed { color: red; background-color: #fce8e6; }
    </style>
""", unsafe_allow_html=True)

# Initialize Managers
prompt_mgr = PromptManager()
dataset_mgr = DatasetManager()

st.title("✍️ Prompt Templates Library")
st.markdown("Design, validate, preview, and version prompt templates as experimental research variables.")

# DB session initialization
db = SessionLocal()

# Load prompts list for sidebar selection
prompts = prompt_mgr.list_prompts(db)

# --- SIDEBAR: CHOOSE TEMPLATE ---
st.sidebar.markdown("### Select Prompt Template")
active_prompt = None

if prompts:
    prompt_options = {p.name: p.id for p in prompts}
    selected_p_name = st.sidebar.selectbox("Active Template", list(prompt_options.keys()))
    active_prompt_id = prompt_options[selected_p_name]
    active_prompt = prompt_mgr.get_prompt(db, active_prompt_id)
else:
    st.sidebar.info("No prompt templates registered yet. Go to the 'Create / Edit' tab to write one.")

# Active template detail elements in sidebar
if active_prompt:
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Selected ID**: `{active_prompt.id}`")
    st.sidebar.markdown(f"**Task Category**: `{active_prompt.task_type}`")
    st.sidebar.markdown(f"**Strategy**: `{active_prompt.strategy}`")
    st.sidebar.markdown(f"**Current Version**: `{active_prompt.current_version}`")
    
    # Active Version Selector
    versions = active_prompt.versions
    ver_names = [v.version for v in versions]
    selected_ver = st.sidebar.selectbox("Selected Version", ver_names, index=ver_names.index(active_prompt.current_version))
    active_body = prompt_mgr.get_prompt_version_body(db, active_prompt.id, selected_ver)
    
    # Delete Button
    if st.sidebar.button("🗑️ Delete Template", help="Permanently deletes the template, all its versions, and tags"):
        prompt_mgr.delete_prompt(db, active_prompt.id)
        st.sidebar.success(f"Deleted template '{active_prompt.name}'")
        st.rerun()

# Tabs Layout
tab_library, tab_editor, tab_preview, tab_diff, tab_exports = st.tabs([
    "📚 Prompt Library", "📝 Create / Edit", "👁️ Live Preview", "🔄 Version Diff", "💾 Exports"
])

# 1. LIBRARY TAB
with tab_library:
    # --- QUICK TEMPLATES IMPORT ---
    with st.expander("📥 Load Reference Prompt Templates", expanded=False):
        st.markdown("Instantly import professional prompt templates into your catalog.")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("""
                <div class="card">
                    <h4 style="margin:0 0 5px 0;">🎭 Emotion Classification (Markdown)</h4>
                    <p style="font-size:0.8rem; color:#5f6368; margin:0; line-height:1.25;">
                        Formats demonstration examples with category text descriptions and numeric labels.
                    </p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Import Emotion Template", key="imp_ref_emotion"):
                body = (
                    "# Instruction\n"
                    "Classify the text input into one of the categories.\n\n"
                    "**Target Labels**: {{target_labels}}\n\n"
                    "{% if few_shot_examples %}\n# Examples\n"
                    "{% for ex in few_shot_examples %}\n### Example {{loop.index}}\n- **Input**: {{ex.input}}\n"
                    "{% if ex.label_name %}- **Category**: {{ex.label_name}}\n{% endif %}- **Label**: {{ex.label}}\n\n"
                    "{% endfor %}\n{% endif %}\n"
                    "# Query\n- **Input**: {{text}}\n- **Label**:"
                )
                try:
                    prompt_mgr.create_prompt(
                        db=db,
                        name="Emotion Reference Template",
                        template_body=body,
                        task_type="classification",
                        strategy="Mixed",
                        format="Markdown",
                        instruction_style="Detailed",
                        reasoning_style="None",
                        description="Markdown formatting layout for multiclass emotion detection.",
                        language="English",
                        tags=["reference", "emotion"]
                    )
                    st.success("Emotion template imported!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Import failed: {e}")

            st.markdown("""
                <div class="card" style="margin-top:10px;">
                    <h4 style="margin:0 0 5px 0;">🎬 Sentiment Analysis (XML Layout)</h4>
                    <p style="font-size:0.8rem; color:#5f6368; margin:0; line-height:1.25;">
                        Structured XML tag wrapping for binary sentiment evaluations.
                    </p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Import Sentiment Template", key="imp_ref_sentiment"):
                body = (
                    "<prompt>\n<instruction>Identify movie review sentiment.</instruction>\n"
                    "<target_labels>{{target_labels}}</target_labels>\n"
                    "<examples>\n{% if few_shot_examples %}{% for ex in few_shot_examples %}\n"
                    "  <example>\n    <input>{ex.input}</input>\n"
                    "    {% if ex.label_name %}<category>{ex.label_name}</category>\n{% endif %}"
                    "    <label>{ex.label}</label>\n  </example>\n"
                    "{% endfor %}{% endif %}\n</examples>\n"
                    "<query>\n  <input>{{text}}</input>\n  <label></label>\n</query>\n</prompt>"
                )
                try:
                    prompt_mgr.create_prompt(
                        db=db,
                        name="Sentiment Reference Template",
                        template_body=body,
                        task_type="classification",
                        strategy="Mixed",
                        format="XML",
                        instruction_style="Simple",
                        reasoning_style="None",
                        description="XML-formatted sentiment template with categorical mappings.",
                        language="English",
                        tags=["reference", "sentiment"]
                    )
                    st.success("Sentiment template imported!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Import failed: {e}")

        with col_t2:
            st.markdown("""
                <div class="card">
                    <h4 style="margin:0 0 5px 0;">❓ Contextual QA (CoT / Markdown)</h4>
                    <p style="font-size:0.8rem; color:#5f6368; margin:0; line-height:1.25;">
                        Prompts LLM to think step-by-step before answering context questions.
                    </p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Import QA Template", key="imp_ref_qa"):
                body = (
                    "# Instruction\n"
                    "Answer the question using the context. Output your step-by-step reasoning first, then write the final answer.\n\n"
                    "{% if few_shot_examples %}\n# Examples\n"
                    "{% for ex in few_shot_examples %}\n### Example {{loop.index}}\n- **Context**: {{ex.input}}\n"
                    "- **Question**: {{ex.question if ex.question else 'Question'}}\n- **Answer**: {{ex.label}}\n\n"
                    "{% endfor %}\n{% endif %}\n"
                    "# Query\n- **Context**: {{context}}\n- **Question**: {{question}}\n- **Answer**:"
                )
                try:
                    prompt_mgr.create_prompt(
                        db=db,
                        name="Contextual QA Reference Template",
                        template_body=body,
                        task_type="qa",
                        strategy="Mixed",
                        format="Markdown",
                        instruction_style="Step-by-Step",
                        reasoning_style="Chain-of-Thought",
                        description="Markdown formatting layout with Chain-of-Thought question-answering examples.",
                        language="English",
                        tags=["reference", "qa"]
                    )
                    st.success("QA template imported!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Import failed: {e}")

            st.markdown("""
                <div class="card" style="margin-top:10px;">
                    <h4 style="margin:0 0 5px 0;">📝 Generic Text Summarization (Plain)</h4>
                    <p style="font-size:0.8rem; color:#5f6368; margin:0; line-height:1.25;">
                        Zero-shot concise instruction summarizer template.
                    </p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Import Summarization Template", key="imp_ref_sum"):
                body = (
                    "Instruction:\n"
                    "Summarize the following context passage in one concise sentence.\n\n"
                    "Context:\n{{context}}\n\n"
                    "Summary:"
                )
                try:
                    prompt_mgr.create_prompt(
                        db=db,
                        name="Text Summarization Reference Template",
                        template_body=body,
                        task_type="qa",
                        strategy="Instruction",
                        format="Plain Text",
                        instruction_style="Simple",
                        reasoning_style="None",
                        description="Zero-shot text compression template.",
                        language="English",
                        tags=["reference", "summarization"]
                    )
                    st.success("Summarization template imported!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Import failed: {e}")

    st.markdown("### Registered Prompt Templates")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        f_task = st.selectbox("Filter Task", ["All", "classification", "qa", "summarization", "reasoning", "translation", "extraction", "custom"])
    with col_f2:
        f_strat = st.selectbox("Filter Strategy", ["All", "Instruction", "Example", "Mixed", "JSON", "Markdown", "XML", "CoT", "Custom"])
    with col_f3:
        f_search = st.text_input("Search Name/Description", "")

    filtered_prompts = prompt_mgr.list_prompts(
        db,
        task_type=None if f_task == "All" else f_task,
        strategy=None if f_strat == "All" else f_strat,
        search_query=None if f_search == "" else f_search
    )

    if not filtered_prompts:
        st.info("No prompt templates match the filter criteria.")
    else:
        lib_data = []
        for p in filtered_prompts:
            tags = ", ".join([t.tag for t in p.tags])
            lib_data.append({
                "ID": p.id,
                "Name": p.name,
                "Task": p.task_type,
                "Strategy": p.strategy,
                "Format": p.format,
                "Active Version": p.current_version,
                "Tags": tags,
                "Last Updated": p.updated_at.strftime("%Y-%m-%d %H:%M")
            })
        st.dataframe(pd.DataFrame(lib_data), use_container_width=True, hide_index=True)

    st.markdown("---")
    
    if active_prompt:
        st.markdown(f"#### Active Template Details: {active_prompt.name}")
        st.markdown(f"*{active_prompt.description or 'No description provided.'}*")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown(f"**Instruction Style**: `{active_prompt.instruction_style}`")
            st.markdown(f"**Reasoning Style**: `{active_prompt.reasoning_style}`")
            st.markdown(f"**Language**: `{active_prompt.language}`")
        with col_d2:
            tags_list = [t.tag for t in active_prompt.tags]
            st.markdown(f"**Tags**: {', '.join(tags_list) if tags_list else 'None'}")
            st.markdown(f"**Created At**: `{active_prompt.created_at.strftime('%Y-%m-%d %H:%M:%S')}`")

        st.markdown(f"**Template Body ({selected_ver})**")
        st.code(active_body, language="jinja2")
        
        metrics = prompt_mgr.get_prompt_metrics(active_body)
        st.markdown(f"**Complexity Profile**: Chars: `{metrics['char_count']}` | Words: `{metrics['word_count']}` | Estimated Tokens: `{metrics['token_estimate']}`")

# 2. CREATE / EDIT TAB
with tab_editor:
    editor_mode = st.radio("Editor Mode", ["Create New Template", "Edit Selected Template"], horizontal=True)
    
    if editor_mode == "Edit Selected Template" and not active_prompt:
        st.warning("Please select an active prompt template in the sidebar to edit it.")
        st.stop()

    st.markdown("### Template Details")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        e_name = st.text_input(
            "Template Name", 
            value=active_prompt.name if (editor_mode == "Edit Selected Template" and active_prompt) else "",
            disabled=(editor_mode == "Edit Selected Template")
        )
        e_task = st.selectbox(
            "Task Category", 
            ["classification", "qa", "summarization", "reasoning", "translation", "extraction", "custom"],
            index=["classification", "qa", "summarization", "reasoning", "translation", "extraction", "custom"].index(active_prompt.task_type) if (editor_mode == "Edit Selected Template" and active_prompt) else 0
        )
        e_strat = st.selectbox(
            "Strategy Type", 
            ["Instruction", "Example", "Mixed", "JSON", "Markdown", "XML", "CoT", "Custom"],
            index=["Instruction", "Example", "Mixed", "JSON", "Markdown", "XML", "CoT", "Custom"].index(active_prompt.strategy) if (editor_mode == "Edit Selected Template" and active_prompt) else 0
        )
        e_format = st.selectbox(
            "Formatting Strategy", 
            ["Plain Text", "Markdown", "JSON", "XML"],
            index=["Plain Text", "Markdown", "JSON", "XML"].index(active_prompt.format) if (editor_mode == "Edit Selected Template" and active_prompt) else 0
        )
        
    with col_e2:
        e_style = st.selectbox(
            "Instruction Style", 
            ["Simple", "Detailed", "Step-by-Step", "None"],
            index=["Simple", "Detailed", "Step-by-Step", "None"].index(active_prompt.instruction_style) if (editor_mode == "Edit Selected Template" and active_prompt) else 0
        )
        e_reason = st.selectbox(
            "Reasoning Style", 
            ["None", "Chain-of-Thought"],
            index=["None", "Chain-of-Thought"].index(active_prompt.reasoning_style) if (editor_mode == "Edit Selected Template" and active_prompt) else 0
        )
        e_lang = st.text_input(
            "Language", 
            value=active_prompt.language if (editor_mode == "Edit Selected Template" and active_prompt) else "English"
        )
        e_tags = st.text_input(
            "Tags (comma-separated)", 
            value=", ".join([t.tag for t in active_prompt.tags]) if (editor_mode == "Edit Selected Template" and active_prompt) else ""
        )

    e_desc = st.text_area(
        "Description", 
        value=active_prompt.description if (editor_mode == "Edit Selected Template" and active_prompt) else ""
    )

    st.markdown("---")
    st.markdown("### Template Compiler")
    
    initial_body = ""
    if editor_mode == "Edit Selected Template" and active_prompt:
        initial_body = active_body

    e_body = st.text_area(
        "Template Body (Jinja2 Syntax)", 
        value=initial_body, 
        height=300,
        placeholder="Write your template. Use placeholders like {{input}} or {{examples}}."
    )

    if st.button("🔬 Validate Template Syntax"):
        val_report = prompt_mgr.validate_prompt(e_body, e_task)
        if val_report["status"] == "PASS":
            st.markdown('<span class="badge badge-pass">PASS</span> Jinja2 syntax compile checks out.', unsafe_allow_html=True)
            st.info(f"**Detected Placeholders**: {val_report['placeholders']}")
        else:
            st.markdown('<span class="badge badge-fail">FAIL</span> Syntax errors detected.', unsafe_allow_html=True)
            for err in val_report["errors"]:
                st.error(f"🛑 {err}")
        
        if val_report["warnings"]:
            for warn in val_report["warnings"]:
                st.warning(f"⚠️ {warn}")

    st.markdown("---")
    
    if editor_mode == "Create New Template":
        if st.button("🚀 Save and Publish Template"):
            if not e_name or not e_body:
                st.error("Name and Template Body are required.")
            else:
                try:
                    parsed_tags = [t.strip() for t in e_tags.split(",") if t.strip()]
                    prompt_mgr.create_prompt(
                        db=db,
                        name=e_name,
                        template_body=e_body,
                        task_type=e_task,
                        strategy=e_strat,
                        format=e_format,
                        instruction_style=e_style,
                        reasoning_style=e_reason,
                        description=e_desc,
                        language=e_lang,
                        tags=parsed_tags
                    )
                    st.success(f"Published template '{e_name}' successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error publishing template: {str(e)}")
                    
    else:
        st.markdown("#### Version Control details")
        next_ver = prompt_mgr.get_next_version_name(active_prompt.current_version)
        v_name = st.text_input("New Version Name", value=next_ver)
        v_notes = st.text_area("Change Notes", placeholder="What changed in this template prompt design...")
        
        if st.button("💾 Save New Version"):
            if not v_name or not e_body:
                st.error("Version Name and Template Body are required.")
            else:
                try:
                    prompt_mgr.create_new_version(
                        db=db,
                        prompt_id=active_prompt.id,
                        version_name=v_name,
                        template_body=e_body,
                        change_notes=v_notes
                    )
                    st.success(f"Version '{v_name}' successfully published for template '{active_prompt.name}'!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save version: {str(e)}")

# 3. LIVE PREVIEW TAB
with tab_preview:
    if not active_prompt:
        st.warning("Please select an active prompt template in the sidebar first.")
        st.stop()

    st.markdown("### Interactive Rendering Preview")
    
    val_report = prompt_mgr.validate_prompt(active_body, active_prompt.task_type)
    placeholders = val_report["placeholders"]
    
    datasets = dataset_mgr.list_datasets(db)
    selected_dataset = None
    dataset_df = None
    
    st.markdown("#### 1. Context Source (Optional)")
    if datasets:
        ds_names = ["None"] + [d.name for d in datasets]
        selected_ds_name = st.selectbox("Load sample data row from registered dataset:", ds_names)
        
        if selected_ds_name != "None":
            selected_dataset = next(d for d in datasets if d.name == selected_ds_name)
            
            ds_versions = [v.version for v in selected_dataset.versions]
            selected_ds_ver = st.selectbox("Dataset Version select", ds_versions)
            
            ds_splits_data = dataset_mgr.get_dataset_version_data(db, selected_dataset.id, selected_ds_ver)
            active_ds_split = st.selectbox("Dataset Split select", list(ds_splits_data.keys()))
            dataset_df = ds_splits_data[active_ds_split]
            
            row_idx = st.slider("Dataset row index", 0, len(dataset_df)-1, 0)
            target_row = dataset_df.iloc[row_idx]
            
            st.json(target_row.to_dict())
    else:
        st.info("No datasets registered yet. Fill in placeholders manually below.")

    st.markdown("#### 2. Placeholder Values Configuration")
    
    filled_placeholders = {}
    
    ds_mapping = {}
    if dataset_df is not None and selected_dataset is not None:
        ds_val_rep = dataset_mgr.validate_dataset(dataset_df, selected_dataset.task)
        ds_mapping = ds_val_rep.get("column_mapping", {})
    
    for p in placeholders:
        default_val = ""
        
        if dataset_df is not None:
            if p == "input" and "text" in ds_mapping and ds_mapping["text"] in dataset_df.columns:
                default_val = str(target_row[ds_mapping["text"]])
            elif p == "context" and "context" in ds_mapping and ds_mapping["context"] in dataset_df.columns:
                default_val = str(target_row[ds_mapping["context"]])
            elif p == "question" and "question" in ds_mapping and ds_mapping["question"] in dataset_df.columns:
                default_val = str(target_row[ds_mapping["question"]])
            elif p == "label" and "label" in ds_mapping and ds_mapping["label"] in dataset_df.columns:
                default_val = str(target_row[ds_mapping["label"]])
            elif p in dataset_df.columns:
                default_val = str(target_row[p])
        
        if len(default_val) > 100 or p in ["examples", "context", "template_body"]:
            filled_placeholders[p] = st.text_area(f"Placeholder: `{{{{{p}}}}}`", value=default_val, key=f"preview_val_{p}")
        else:
            filled_placeholders[p] = st.text_input(f"Placeholder: `{{{{{p}}}}}`", value=default_val, key=f"preview_val_{p}")

    st.markdown("#### 3. Render Output")
    if st.button("⚡ Render Preview"):
        try:
            rendered_prompt = prompt_mgr.render_prompt(active_body, filled_placeholders)
            st.code(rendered_prompt, language="text")
            
            p_metrics = prompt_mgr.get_prompt_metrics(rendered_prompt)
            st.info(f"**Rendered Complexity**: Characters: `{p_metrics['char_count']}` | Words: `{p_metrics['word_count']}` | Estimated Tokens: `{p_metrics['token_estimate']}`")
        except Exception as e:
            st.error(f"Render failed: {str(e)}")

# 4. DIFF TAB
with tab_diff:
    if not active_prompt:
        st.warning("Please select an active prompt template in the sidebar first.")
        st.stop()

    st.markdown("### Version Comparisons")
    st.markdown("Select two prompt versions to check changes in templates.")

    col_diff_1, col_diff_2 = st.columns(2)
    with col_diff_1:
        ver_a = st.selectbox("Version A (Base)", ver_names, index=0)
    with col_diff_2:
        ver_b = st.selectbox("Version B (Target)", ver_names, index=min(1, len(ver_names)-1))

    if st.button("🔍 Generate Diff"):
        body_a = prompt_mgr.get_prompt_version_body(db, active_prompt.id, ver_a)
        body_b = prompt_mgr.get_prompt_version_body(db, active_prompt.id, ver_b)
        
        diff_text = prompt_mgr.get_diff(body_a, body_b, f"Version {ver_a}", f"Version {ver_b}")
        
        if not diff_text:
            st.info("No differences detected between these two versions.")
        else:
            st.markdown("**Unified Diff Output**")
            st.code(diff_text, language="diff")

# 5. EXPORTS TAB
with tab_exports:
    if not active_prompt:
        st.warning("Please select an active prompt template in the sidebar first.")
        st.stop()

    st.markdown("### Export Prompt Template Configuration")
    
    export_format = st.selectbox("Export Format option", ["txt", "md", "json", "yaml"])
    export_filename = st.text_input("Export Filename Prefix", f"{active_prompt.id}_v{selected_ver}")
    
    if st.button("💾 Export Template"):
        with st.spinner("Writing export files..."):
            try:
                filepath = prompt_mgr.export_prompt(
                    db=db,
                    prompt_id=active_prompt.id,
                    version=selected_ver,
                    filename=export_filename,
                    format=export_format
                )
                st.success(f"Prompt template version successfully exported to file: `{filepath}`")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")

db.close()
