import streamlit as st
import pandas as pd
import json
from backend.database.db import SessionLocal
from backend.prompts.prompt_manager import PromptManager
from backend.datasets.dataset_manager import DatasetManager
from peer_studio.utils.ui import apply_custom_theme, render_header, inject_footer_spacer, status_badge

# Apply page styling
apply_custom_theme()

st.markdown("""
    <style>
    .diff-added { color: #2F7D4A; background-color: #EBF7EE; }
    .diff-removed { color: #D12424; background-color: #FDF2F2; }
    </style>
""", unsafe_allow_html=True)

# Initialize Managers
prompt_mgr = PromptManager()
dataset_mgr = DatasetManager()

render_header(
    "Prompt Templates Library", 
    "Design, validate, preview, and version prompt templates as experimental research variables.", 
    "library_books"
)

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
    if st.sidebar.button("Delete Template", icon=":material/delete:", help="Permanently deletes the template, all its versions, and tags"):
        prompt_mgr.delete_prompt(db, active_prompt.id)
        st.sidebar.success(f"Deleted template '{active_prompt.name}'")
        st.rerun()

# Tabs Layout
tab_library, tab_editor, tab_preview, tab_diff, tab_exports = st.tabs([
    "Prompt Library", "Create / Edit", "Live Preview", "Version Diff", "Exports"
])

# 1. LIBRARY TAB
with tab_library:
    # --- QUICK TEMPLATES IMPORT ---
    with st.expander("Load Reference Prompt Templates", expanded=False):
        st.markdown("Instantly import professional prompt templates into your catalog.")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("""
                <div class="card">
                    <h4 style="margin:0 0 5px 0; font-family:'Outfit',sans-serif; color:#1A1A1A;">Emotion Classification (Markdown)</h4>
                    <p style="font-size:13px; color:#666666; margin:0; line-height:1.25;">
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
                    "{% if ex.label_name %}- **Category**: {{ex.label_name}}\n{% endif %}- **Label**: {{ex.label}}\n\n{% endfor %}"
                    "{% endif %}\n"
                    "**Query**:\n- **Input**: {{text}}\n- **Label**:"
                )
                try:
                    prompt_mgr.create_prompt(
                        db=db,
                        name="Emotion Classification Template",
                        task_type="classification",
                        strategy="Example-Based",
                        template_body=body,
                        description="Professional markdown formatted template for dair-ai/emotion evaluations."
                    )
                    st.success("Emotion template imported!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Import failed: {e}")

            st.markdown("""
                <div class="card" style="margin-top:10px;">
                    <h4 style="margin:0 0 5px 0; font-family:'Outfit',sans-serif; color:#1A1A1A;">Sentiment Analysis (XML Layout)</h4>
                    <p style="font-size:13px; color:#666666; margin:0; line-height:1.25;">
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
                    <h4 style="margin:0 0 5px 0; font-family:'Outfit',sans-serif; color:#1A1A1A;">Contextual QA (CoT / Markdown)</h4>
                    <p style="font-size:13px; color:#666666; margin:0; line-height:1.25;">
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
                    "- **Question**: {{ex.question}}\n- **Reasoning**: {{ex.reasoning if ex.reasoning else 'N/A'}}\n- **Answer**: {{ex.label}}\n\n{% endfor %}"
                    "{% endif %}\n"
                    "**Query**:\n- **Context**: {{context}}\n- **Question**: {{question}}\n- **Reasoning**: Think step-by-step.\n- **Answer**:"
                )
                try:
                    prompt_mgr.create_prompt(
                        db=db,
                        name="Contextual QA CoT Template",
                        task_type="qa",
                        strategy="Example-Based",
                        template_body=body,
                        description="Chain-of-Thought markdown template optimized for Yes/No QA benchmark tasks."
                    )
                    st.success("QA template imported!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Import failed: {e}")

            st.markdown("""
                <div class="card" style="margin-top:10px;">
                    <h4 style="margin:0 0 5px 0; font-family:'Outfit',sans-serif; color:#1A1A1A;">Generic Text Summarization (Plain)</h4>
                    <p style="font-size:13px; color:#666666; margin:0; line-height:1.25;">
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
        st.dataframe(pd.DataFrame(lib_data), width='stretch', hide_index=True)

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
    is_new_template = (editor_mode == "Create New Template")

    if not is_new_template and not active_prompt:
        st.warning("Please select an active prompt template in the sidebar to edit it.")
        st.stop()

    st.markdown("### Template Details")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        edit_name = st.text_input("Template Name", value=active_prompt.name if not is_new_template else "")
        edit_task = st.selectbox("Task Category", ["classification", "qa", "summarization", "reasoning", "translation", "extraction", "custom"], index=0)
        edit_strat = st.selectbox("Strategy Type", ["Instruction", "Example", "Mixed", "JSON", "Markdown", "XML", "CoT", "Custom"], index=0)
    with col_e2:
        edit_desc = st.text_input("Description", value=active_prompt.description if not is_new_template else "")

    edit_body = st.text_area("Template Body (Jinja2 Syntax)", value=active_body if not is_new_template else "", height=300)

    if st.button("Validate Template Syntax", icon=":material/fact_check:"):
        errs, warns = prompt_mgr.validate_template(edit_body)
        if not errs:
            badge_html = status_badge("PASS")
            st.markdown(f'{badge_html} Jinja2 syntax compile checks out.', unsafe_allow_html=True)
        else:
            badge_html = status_badge("FAIL")
            st.markdown(f'{badge_html} Syntax errors detected.', unsafe_allow_html=True)
            for err in errs:
                st.error(f"{err}")
        if warns:
            for warn in warns:
                st.warning(f"{warn}")

    st.markdown("---")
    
    if is_new_template:
        if st.button("Save and Publish Template", icon=":material/publish:", type="primary"):
            if not edit_name.strip():
                st.error("Template name cannot be empty.")
            else:
                try:
                    prompt_mgr.create_prompt(db, edit_name, edit_task, edit_strat, edit_body, edit_desc)
                    st.success(f"Template '{edit_name}' successfully created!")
                    st.rerun()
                except Exception as create_err:
                    st.error(f"Creation failed: {str(create_err)}")
    else:
        if st.button("Save New Version", icon=":material/save:", type="primary"):
            try:
                prompt_mgr.create_new_version(db, active_prompt.id, edit_body)
                st.success("New version saved!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save version: {str(e)}")

# 3. LIVE PREVIEW TAB
with tab_preview:
    if not active_prompt:
        st.warning("Please select an active prompt template in the sidebar first.")
        st.stop()

    st.markdown("### Interactive Rendering Preview")
    
    if st.button("Render Preview", icon=":material/preview:"):
        with st.spinner("Compiling Jinja layout contexts..."):
            try:
                rendered = prompt_mgr.render_preview(db, active_prompt.id, selected_ver)
                st.success("Successfully compiled and rendered prompt context payload!")
                st.code(rendered, language="text")
            except Exception as render_err:
                st.error(f"Render failed: {str(render_err)}")

# 4. DIFF TAB
with tab_diff:
    st.markdown("### Compare Template Revisions")
    st.markdown("Contrasting lines diff across different prompt template iterations.")
    
    ver_options = [v.version for v in active_prompt.versions]
    col_df1, col_df2 = st.columns(2)
    with col_df1:
        ver_a = st.selectbox("Version A (Reference)", ver_options, index=max(0, len(ver_options)-2))
    with col_df2:
        ver_b = st.selectbox("Version B (Compare)", ver_options, index=len(ver_options)-1)
        
    if st.button("Generate Diff", icon=":material/difference:"):
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
    
    export_fmt = st.selectbox("Export Format option", ["txt", "md", "json", "yaml"])
    
    if st.button("Export Template", icon=":material/download:"):
        with st.spinner("Compiling prompt metadata splits..."):
            try:
                export_body = prompt_mgr.get_prompt_version_body(db, active_prompt.id, selected_ver)
                st.success("Prompt version compiled successfully!")
                st.download_button(
                    label="Download Export File",
                    icon=":material/download:",
                    data=export_body,
                    file_name=f"{active_prompt.name.replace(' ', '_').lower()}_{selected_ver}.{export_fmt}",
                    mime="text/plain",
                    width='stretch'
                )
            except Exception as exp_err:
                st.error(f"Export failed: {str(exp_err)}")

db.close()
inject_footer_spacer()
