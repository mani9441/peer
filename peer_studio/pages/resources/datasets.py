from backend.datasets.dataset_statistics import DatasetStatistics as StatsEngine
import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
from backend.database.db import SessionLocal
from backend.datasets.dataset_manager import DatasetManager
from backend.datasets.models import Dataset, DatasetVersion, DatasetStatistics

# Page styling
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
    </style>
""", unsafe_allow_html=True)

# Initialize Manager
manager = DatasetManager()

st.title("📊 Dataset Manager")
st.markdown("Load, validate, sample, split, and profile benchmark datasets.")

# Initialize DB connection
db = SessionLocal()

# --- QUICK IMPORT LIBRARY ---
st.markdown("### 📥 Quick Import Popular Benchmarks")
st.markdown("Get started instantly by importing standard NLP benchmark datasets into your workspace.")

col_b1, col_b2, col_b3, col_b4 = st.columns(4)

with col_b1:
    st.markdown("""
        <div class="card">
            <h4 style="margin:0 0 5px 0;">🎭 Emotion</h4>
            <p style="font-size:0.8rem; color:#5f6368; height:85px; margin:0 0 5px 0; line-height:1.25;">
                dair-ai/emotion<br/>
                6 classes (sadness, joy, etc.)<br/>
                Classification task
            </p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Import Emotion", key="imp_bench_emotion", use_container_width=True):
        with st.spinner("Downloading and registering dair-ai/emotion from HF..."):
            try:
                manager.load_dataset(
                    source="huggingface",
                    path="dair-ai/emotion",
                    db=db,
                    save_in_registry=True,
                    task="classification",
                    description="Standard 6-class emotion classification benchmark dataset.",
                    language="English",
                    license="Apache 2.0"
                )
                from backend.database.db import self_heal_dataset_labels
                self_heal_dataset_labels()
                st.success("Emotion dataset imported successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Import failed: {e}")

with col_b2:
    st.markdown("""
        <div class="card">
            <h4 style="margin:0 0 5px 0;">🎬 SST-2</h4>
            <p style="font-size:0.8rem; color:#5f6368; height:85px; margin:0 0 5px 0; line-height:1.25;">
                glue/sst2<br/>
                Binary Sentiment Analysis<br/>
                Classification task
            </p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Import SST-2", key="imp_bench_sst2", use_container_width=True):
        with st.spinner("Downloading and registering glue/sst2 from HF..."):
            try:
                manager.load_dataset(
                    source="huggingface",
                    path="glue",
                    name="sst2",
                    db=db,
                    save_in_registry=True,
                    task="classification",
                    description="Binary movie review sentiment analysis benchmark.",
                    language="English",
                    license="GLUE License"
                )
                from backend.database.db import self_heal_dataset_labels
                self_heal_dataset_labels()
                st.success("SST-2 dataset imported successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Import failed: {e}")

with col_b3:
    st.markdown("""
        <div class="card">
            <h4 style="margin:0 0 5px 0;">📰 AG News</h4>
            <p style="font-size:0.8rem; color:#5f6368; height:85px; margin:0 0 5px 0; line-height:1.25;">
                ag_news<br/>
                4 News Categories<br/>
                Classification task
            </p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Import AG News", key="imp_bench_ag_news", use_container_width=True):
        with st.spinner("Downloading and registering ag_news from HF..."):
            try:
                manager.load_dataset(
                    source="huggingface",
                    path="ag_news",
                    db=db,
                    save_in_registry=True,
                    task="classification",
                    description="4-class topic classification news dataset (World, Sports, Business, Sci/Tech).",
                    language="English",
                    license="MIT"
                )
                from backend.database.db import self_heal_dataset_labels
                self_heal_dataset_labels()
                st.success("AG News dataset imported successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Import failed: {e}")

with col_b4:
    st.markdown("""
        <div class="card">
            <h4 style="margin:0 0 5px 0;">❓ BoolQ</h4>
            <p style="font-size:0.8rem; color:#5f6368; height:85px; margin:0 0 5px 0; line-height:1.25;">
                google/boolq<br/>
                Yes/No Question Answering<br/>
                QA task
            </p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Import BoolQ", key="imp_bench_boolq", use_container_width=True):
        with st.spinner("Downloading and registering google/boolq from HF..."):
            try:
                manager.load_dataset(
                    source="huggingface",
                    path="google/boolq",
                    db=db,
                    save_in_registry=True,
                    task="qa",
                    description="BoolQ: Yes/No Reading comprehension QA benchmark dataset.",
                    language="English",
                    license="CC BY-SA 3.0"
                )
                st.success("BoolQ dataset imported successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Import failed: {e}")

st.markdown("---")

# --- IMPORT EXPANDER ---
with st.expander("📥 Import New Dataset", expanded=False):
    st.markdown("### Import options")
    import_type = st.radio("Source Type", ["Hugging Face Datasets", "Local CSV", "Local JSON"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        dataset_name = st.text_input("Dataset Name (friendly label)", placeholder="e.g., sst2")
        task_type = st.selectbox("Task Type", ["classification", "qa"])
    
    with col2:
        language = st.text_input("Language", "English")
        license_type = st.text_input("License", "Unknown")

    description = st.text_area("Description / Research Context", placeholder="Describe the origin and target utility...")

    if import_type == "Hugging Face Datasets":
        st.markdown("**HF Config**")
        hf_path = st.text_input("HF Repo Path", placeholder="e.g., glue or dair-ai/emotion")
        hf_config = st.text_input("HF Sub-config (optional)", placeholder="e.g., sst2")
        hf_split = st.text_input("Split to load (optional)", placeholder="e.g., train")
        
        if st.button("Download & Register from HF"):
            if not dataset_name or not hf_path:
                st.error("Please provide both Dataset Name and HF Repo Path.")
            else:
                with st.spinner("Downloading from Hugging Face..."):
                    try:
                        manager.load_dataset(
                            source="huggingface",
                            path=hf_path,
                            name=hf_config or None,
                            split=hf_split or None,
                            db=db,
                            save_in_registry=True,
                            task=task_type,
                            description=description,
                            language=language,
                            license=license_type
                        )
                        st.success(f"Successfully loaded and registered dataset '{dataset_name}'!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error loading dataset: {str(e)}")
                        
    elif import_type in ["Local CSV", "Local JSON"]:
        uploaded_file = st.file_uploader(f"Choose a {import_type.split()[-1]} file", type=["csv", "json"])
        
        # Mapping column definitions
        st.markdown("**Column Schema Mapping**")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            if task_type == "classification":
                col_text = st.text_input("Input/Text Column Name (auto-detect if empty)", "")
                col_label = st.text_input("Output/Label Column Name (auto-detect if empty)", "")
            else:
                col_context = st.text_input("Context Column Name (auto-detect if empty)", "")
                col_question = st.text_input("Question Column Name (auto-detect if empty)", "")
        with col_m2:
            if task_type == "qa":
                col_answers = st.text_input("Answers Column Name (auto-detect if empty)", "")

        if uploaded_file is not None:
            if st.button("Upload & Register"):
                if not dataset_name:
                    st.error("Please supply a Dataset Name.")
                else:
                    # Save local file
                    os.makedirs("datasets/uploads", exist_ok=True)
                    local_path = os.path.join("datasets/uploads", uploaded_file.name)
                    with open(local_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                        
                    with st.spinner("Processing file..."):
                        try:
                            source_key = "csv" if import_type == "Local CSV" else "json"
                            
                            # Build manual mapping if any fields filled
                            custom_mapping = {}
                            if task_type == "classification":
                                if col_text: custom_mapping["text"] = col_text
                                if col_label: custom_mapping["label"] = col_label
                            else:
                                if col_context: custom_mapping["context"] = col_context
                                if col_question: custom_mapping["question"] = col_question
                                if col_answers: custom_mapping["answers"] = col_answers
                                
                            temp_dict = manager.load_dataset(source=source_key, path=local_path, save_in_registry=False)
                            first_split_df = list(temp_dict.values())[0]
                            val_report = manager.validate_dataset(first_split_df, task_type, custom_mapping or None)
                            
                            if val_report["status"] == "FAIL":
                                st.error(f"Validation failed: {val_report['errors']}")
                            else:
                                manager.load_dataset(
                                    source=source_key,
                                    path=local_path,
                                    name=dataset_name,
                                    db=db,
                                    save_in_registry=True,
                                    task=task_type,
                                    description=description,
                                    language=language,
                                    license=license_type
                                )
                                st.success("Local dataset registered successfully!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Failed to register local dataset: {str(e)}")

# --- SIDEBAR: CHOOSE DATASET ---
st.sidebar.markdown("### Select Dataset")
registered_datasets = manager.list_datasets(db)

if not registered_datasets:
    st.info("No datasets registered yet. Please import a dataset using the form above.")
    db.close()
    st.stop()

ds_options = {d.name: d.id for d in registered_datasets}
selected_ds_name = st.sidebar.selectbox("Active Dataset", list(ds_options.keys()))
selected_ds_id = ds_options[selected_ds_name]

# Fetch selected dataset model
dataset = manager.get_dataset(db, selected_ds_id)

# Fetch available versions
versions = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == selected_ds_id).all()
ver_names = [v.version for v in versions]
selected_ver = st.sidebar.selectbox("Dataset Version", ver_names, index=ver_names.index(dataset.version) if dataset.version in ver_names else 0)

# Fetch data for active dataset version
with st.spinner("Loading dataset version data..."):
    try:
        data_dict = manager.get_dataset_version_data(db, selected_ds_id, selected_ver)
    except Exception as e:
        st.error(f"Failed to load dataset files: {str(e)}")
        db.close()
        st.stop()

# Detect normalized columns mapping using the first split
splits = list(data_dict.keys())
pref_split = "train" if "train" in data_dict else splits[0]
first_df = data_dict[pref_split]
val_report = manager.validate_dataset(first_df, dataset.task)
mapping = val_report.get("column_mapping", {})

# Main Tabs layout
tab_overview, tab_preview, tab_stats, tab_validation, tab_vector, tab_transform, tab_exports = st.tabs([
    "🔍 Overview", "📋 Preview", "📈 Statistics", "✔️ Schema Validation", "⚡ Vector Indexing", "⚙️ Transform & Version", "💾 Exports"
])

# 1. OVERVIEW TAB
with tab_overview:
    st.markdown(f"### {dataset.name} ({selected_ver})")
    st.markdown(f"*{dataset.description or 'No description provided.'}*")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**Task Type**: `{dataset.task}`")
        st.markdown(f"**Source**: `{dataset.source}`")
        st.markdown(f"**Total Samples**: `{dataset.samples:,}`")
        st.markdown(f"**Available Splits**: `{dataset.splits}`")
    with col_b:
        st.markdown(f"**Language**: `{dataset.language}`")
        st.markdown(f"**License**: `{dataset.license}`")
        st.markdown(f"**Stable Hash**: `{dataset.hash}`")
        st.markdown(f"**Registered At**: `{dataset.created_at.strftime('%Y-%m-%d %H:%M:%S')}`")

    st.markdown("---")
    st.markdown("#### Database Trace & Lineage")
    ver_recs = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == selected_ds_id).order_by(DatasetVersion.id.asc()).all()
    for v in ver_recs:
        parent_info = f"parent={v.parent_version}" if v.parent_version else "root"
        st.markdown(f"- **Version `{v.version}`** ({parent_info}):  \n  `Transformations`: {v.transformations}")

# 2. PREVIEW TAB
with tab_preview:
    st.markdown("### Data Inspector")
    active_split = st.selectbox("Select Split to Preview", splits)
    df_to_preview = data_dict[active_split]
    
    # Simple search bar
    search_col = mapping.get("text") or mapping.get("question") or df_to_preview.columns[0]
    search_query = st.text_input("Filter rows by substring search:", "")
    
    if search_query:
        df_filtered = df_to_preview[df_to_preview[search_col].astype(str).str.contains(search_query, case=False, na=False)]
    else:
        df_filtered = df_to_preview

    st.write(f"Showing {min(100, len(df_filtered))} of {len(df_filtered)} rows.")
    
    # Handle rendering based on task
    if dataset.task == "classification":
        preview_cols = [mapping.get("text"), mapping.get("label")]
        preview_cols = [c for c in preview_cols if c in df_filtered.columns]
        st.dataframe(df_filtered[preview_cols].head(100), use_container_width=True)
    elif dataset.task == "qa":
        preview_cols = [mapping.get("context"), mapping.get("question"), mapping.get("answers")]
        preview_cols = [c for c in preview_cols if c in df_filtered.columns]
        st.dataframe(df_filtered[preview_cols].head(100), use_container_width=True)
    else:
        st.dataframe(df_filtered.head(100), use_container_width=True)

# 3. STATISTICS TAB
with tab_stats:
    st.markdown("### Profile Summary")
    
    # Recompute statistics on selected version (concatenating splits for complete overview)
    combined_ver_df = pd.concat(data_dict.values(), ignore_index=True)
    stats = StatsEngine.compute(combined_ver_df, dataset.task, mapping)
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    col_s1.metric("Total Records", f"{stats['total_samples']:,}")
    
    if dataset.task == "classification":
        col_s2.metric("Imbalance Entropy (0-1)", f"{stats['imbalance_score']:.2f}")
        col_s3.metric("Avg Character Length", f"{stats['avg_length']:.1f}")
        col_s4.metric("Max Character Length", f"{stats['max_length']}")
    else:
        col_s2.metric("Avg Context Length", f"{stats['avg_length']:.1f}")
        col_s3.metric("Max Context Length", f"{stats['max_length']}")
        col_s4.metric("QA Pairs Count", f"{len(combined_ver_df):,}")

    st.markdown("---")
    
    # Render Plots
    plot_left, plot_right = st.columns(2)
    
    with plot_left:
        st.markdown("#### Split Distribution")
        split_counts = {s: len(df) for s, df in data_dict.items()}
        split_df = pd.DataFrame(list(split_counts.items()), columns=["Split", "Count"])
        fig_splits = px.pie(split_df, values="Count", names="Split", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_splits.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
        st.plotly_chart(fig_splits, use_container_width=True)

    with plot_right:
        if dataset.task == "classification":
            st.markdown("#### Class Balance")
            if stats["class_distribution"]:
                dist_dict = json.loads(stats["class_distribution"])
                dist_df = pd.DataFrame(list(dist_dict.items()), columns=["Class", "Count"])
                fig_class = px.bar(dist_df, x="Class", y="Count", color="Class", color_discrete_sequence=px.colors.qualitative.Safe)
                fig_class.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300, showlegend=False)
                st.plotly_chart(fig_class, use_container_width=True)
        else:
            st.markdown("#### Context / Question Lengths")
            meta = json.loads(stats["metadata_json"])
            if "question" in meta and "context" in meta:
                meta_df = pd.DataFrame([
                    {"Field": "Question", "Avg Char Length": meta["question"]["avg_char_len"]},
                    {"Field": "Context", "Avg Char Length": meta["context"]["avg_char_len"]},
                    {"Field": "Answer", "Avg Char Length": meta.get("answer", {}).get("avg_char_len", 0.0)}
                ])
                fig_qa_lens = px.bar(meta_df, x="Field", y="Avg Char Length", color="Field", color_discrete_sequence=px.colors.qualitative.Safe)
                fig_qa_lens.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300, showlegend=False)
                st.plotly_chart(fig_qa_lens, use_container_width=True)

    # Length Histograms
    st.markdown("#### Sample Length Distribution")
    hist_split = st.selectbox("Histogram Split Source", splits, key="hist_split_sel")
    hist_df = data_dict[hist_split]
    hist_col = mapping.get("text") if dataset.task == "classification" else mapping.get("context")
    
    if hist_col in hist_df.columns:
        lengths_series = hist_df[hist_col].dropna().astype(str).str.len()
        fig_hist = px.histogram(lengths_series, nbins=50, labels={"value": "Character Length", "count": "Frequency"}, color_discrete_sequence=["#1A73E8"])
        fig_hist.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320, showlegend=False)
        st.plotly_chart(fig_hist, use_container_width=True)

# 4. SCHEMA VALIDATION TAB
with tab_validation:
    st.markdown("### Standard Validation Report")
    val_split = st.selectbox("Validation Target Split", splits, key="val_split_sel")
    target_val_df = data_dict[val_split]
    
    report = manager.validate_dataset(target_val_df, dataset.task)
    
    if report["status"] == "PASS":
        st.markdown('<span class="badge badge-pass">PASS</span> Schema is valid and matches expectation.', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-fail">FAIL</span> Schema check failed. Fix errors to proceed.', unsafe_allow_html=True)

    st.markdown("#### Mapping details")
    st.json(report["column_mapping"])

    if report["errors"]:
        st.error("Errors Detected:")
        for err in report["errors"]:
            st.write(f"🛑 {err}")
            
    if report["warnings"]:
        st.warning("Warnings Detected:")
        for warn in report["warnings"]:
            st.write(f"⚠️ {warn}")

# 5. VECTOR INDEXING TAB
with tab_vector:
    st.markdown("### Vector Embeddings & FAISS Vector Index")
    st.markdown("PEER semantic few-shot selection retrieves demonstration examples using FAISS vector indexing.")

    # Lazy-load builder models when inside tab
    from backend.fewshot.builder import FewShotBuilder
    builder = FewShotBuilder()
    emb_model = "all-MiniLM-L6-v2"

    cache_exists = builder.service.cache.cache_exists(selected_ds_id, selected_ver, emb_model)
    npy_path = builder.service.cache.get_embedding_path(selected_ds_id, selected_ver, emb_model)
    faiss_path = builder.service.cache.get_faiss_path(selected_ds_id, selected_ver, emb_model)

    db_idx = builder.service.get_index(db, selected_ds_id, selected_ver, emb_model)

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.markdown("**Index Status Summary**")
        st.markdown(f"**Embedding Model**: `{emb_model}`")
        st.markdown(f"**Vector Dimension**: `384`")
        
        if cache_exists and db_idx:
            st.markdown('**Status**: <span class="badge badge-pass">INDEXED</span> Vector files are cached on disk.', unsafe_allow_html=True)
            npy_size_mb = os.path.getsize(npy_path) / (1024.0 * 1024.0)
            faiss_size_mb = os.path.getsize(faiss_path) / (1024.0 * 1024.0)
            st.markdown(f"**Embeddings Cache Size**: `{npy_size_mb:.2f} MB`")
            st.markdown(f"**FAISS Index Size**: `{faiss_size_mb:.2f} MB`")
            st.markdown(f"**Index Path**: `{faiss_path}`")
            st.markdown(f"**Index Created At**: `{db_idx.created_at.strftime('%Y-%m-%d %H:%M:%S')}`")
        else:
            st.markdown('**Status**: <span class="badge badge-fail">NOT INDEXED</span> Semantic few-shot search cannot run for this version.', unsafe_allow_html=True)
            
    with col_v2:
        st.markdown("**Index Build Controls**")
        if st.button("🚀 Build Vector Index", help="Generates sentence transformer embeddings and compiles the FAISS vector database"):
            with st.spinner("Lazy loading SentenceTransformers model and generating vector embeddings on train split..."):
                try:
                    builder.service.build_dataset_index(db, selected_ds_id, selected_ver, emb_model)
                    st.success("Successfully generated embeddings cache and built FAISS index!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to build vector index: {str(e)}")

        if cache_exists:
            if st.button("🗑️ Delete Cache Files", help="Permanently deletes the npy embedding array and faiss index files from storage"):
                try:
                    if os.path.exists(npy_path): os.remove(npy_path)
                    if os.path.exists(faiss_path): os.remove(faiss_path)
                    db_idx = builder.service.get_index(db, selected_ds_id, selected_ver, emb_model)
                    if db_idx:
                        db.delete(db_idx)
                        db.commit()
                    st.success("Embedding cache files successfully deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete files: {str(e)}")

# 6. TRANSFORM TAB
with tab_transform:
    st.markdown("### Transform & Create New Dataset Version")
    st.markdown("Apply filters, sampling, or custom train/val/test splits to form a reproducible subset.")

    transform_src_split = st.selectbox("Source Split to Transform", splits, key="trans_split_sel")
    src_df = data_dict[transform_src_split]

    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown("**1. Sampling Strategy**")
        sample_strategy = st.selectbox("Strategy", ["None", "Random (N Rows)", "Random (Fraction)", "Balanced", "First N"])
        
        sample_params = {}
        if sample_strategy == "Random (N Rows)":
            sample_params["n"] = st.number_input("Number of samples (N)", min_value=1, max_value=len(src_df), value=min(100, len(src_df)))
        elif sample_strategy == "Random (Fraction)":
            sample_params["frac"] = st.slider("Fraction size", 0.01, 1.0, 0.1, step=0.01)
        elif sample_strategy == "Balanced":
            sample_params["n_per_class"] = st.number_input("Samples per class", min_value=1, max_value=len(src_df), value=10)
        elif sample_strategy == "First N":
            sample_params["n"] = st.number_input("First N rows", min_value=1, max_value=len(src_df), value=min(100, len(src_df)))

    with col_t2:
        st.markdown("**2. Filter Criteria**")
        apply_len_filter = st.checkbox("Filter by Length")
        min_char_len = None
        max_char_len = None
        if apply_len_filter:
            min_char_len = st.number_input("Min character length", min_value=0, value=0)
            max_char_len = st.number_input("Max character length", min_value=1, value=1000)
            
        apply_query_filter = st.checkbox("Filter by Query Substring")
        query_str = ""
        if apply_query_filter:
            query_str = st.text_input("Contains substring", "")

        apply_label_filter = st.checkbox("Filter by Specific Labels")
        label_list = []
        if apply_label_filter and dataset.task == "classification":
            available_labels = src_df[mapping["label"]].dropna().unique().tolist()
            label_list = st.multiselect("Include only labels", available_labels, default=available_labels)

    st.markdown("**3. Re-Splitting**")
    re_split = st.checkbox("Generate custom splits (train, validation, test) from the transformed result")
    
    val_ratio = 0.0
    test_ratio = 0.0
    stratify_split = False
    
    if re_split:
        col_s_a, col_s_b = st.columns(2)
        with col_s_a:
            val_ratio = st.slider("Validation Split Ratio", 0.0, 0.4, 0.1, step=0.05)
            test_ratio = st.slider("Test Split Ratio", 0.0, 0.4, 0.2, step=0.05)
        with col_s_b:
            stratify_split = st.checkbox("Stratify Split (Classification only)", value=True)

    st.markdown("**4. Save Version Metadata**")
    new_ver_name = st.text_input("New Version Name", placeholder="e.g., v2, 500_balanced, test_split")
    trans_comments = st.text_area("Change comments", placeholder="Explain the rationale for this version subset...")

    if st.button("Apply Transformations & Save"):
        if not new_ver_name:
            st.error("Version Name is required.")
        elif new_ver_name in ver_names:
            st.error(f"Version '{new_ver_name}' already exists.")
        else:
            with st.spinner("Processing transformation..."):
                try:
                    text_col = mapping.get("text") or mapping.get("context")
                    label_col = mapping.get("label")
                    
                    df_proc = src_df.copy()
                    if apply_len_filter or apply_query_filter or (apply_label_filter and label_list):
                        df_proc = manager.filter_dataset(
                            df=df_proc,
                            text_col=text_col,
                            label_col=label_col,
                            labels=label_list if apply_label_filter else None,
                            min_len=min_char_len,
                            max_len=max_char_len,
                            query=query_str if apply_query_filter else None
                        )
                    
                    if sample_strategy != "None":
                        strat_key = {
                            "Random (N Rows)": "random",
                            "Random (Fraction)": "random",
                            "Balanced": "balanced",
                            "First N": "first_n"
                        }[sample_strategy]
                        df_proc = manager.sample_dataset(
                            df=df_proc,
                            strategy=strat_key,
                            params=sample_params,
                            label_col=label_col
                        )
                        
                    if re_split:
                        new_splits_dict = manager.split_dataset(
                            df=df_proc,
                            val_ratio=val_ratio,
                            test_ratio=test_ratio,
                            label_col=label_col,
                            stratify=stratify_split
                        )
                    else:
                        new_splits_dict = {transform_src_split: df_proc}
                        for s in splits:
                            if s != transform_src_split:
                                new_splits_dict[s] = data_dict[s]

                    transform_info = {
                        "source_split": transform_src_split,
                        "sampling_strategy": sample_strategy,
                        "sampling_params": sample_params,
                        "filters": {
                            "length": {"min": min_char_len, "max": max_char_len} if apply_len_filter else None,
                            "query": query_str if apply_query_filter else None,
                            "labels": label_list if apply_label_filter else None
                        },
                        "resplit": {
                            "enabled": re_split,
                            "val_ratio": val_ratio,
                            "test_ratio": test_ratio,
                            "stratified": stratify_split
                        } if re_split else None,
                        "comments": trans_comments
                    }
                    
                    manager.save_version(
                        db=db,
                        dataset_id=selected_ds_id,
                        version_name=new_ver_name,
                        df_dict=new_splits_dict,
                        parent_version=selected_ver,
                        transformations=transform_info
                    )
                    st.success(f"Successfully created version '{new_ver_name}'!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Transformation failed: {str(e)}")

# 7. EXPORTS TAB
with tab_exports:
    st.markdown("### Export Dataset Version")
    st.markdown("Save this version subset to disk for offline workflows or publication.")
    
    export_format = st.selectbox("Export Format", ["csv", "json", "parquet"])
    export_filename = st.text_input("Export Filename Prefix", f"{dataset.name}_{selected_ver}")
    
    if st.button("Export Files"):
        with st.spinner("Writing export files..."):
            try:
                paths = manager.export_dataset(data_dict, export_filename, export_format)
                st.success("Successfully exported dataset splits:")
                if isinstance(paths, dict):
                    for split, path in paths.items():
                        st.markdown(f"- **{split}**: `{path}`")
                else:
                    st.markdown(f"- **File**: `{paths}`")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")

db.close()
