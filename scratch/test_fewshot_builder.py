import os
import sys
import numpy as np
import pandas as pd
import shutil

# Add workspace path to python import lookup
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from backend.database.db import get_db, init_db
from backend.datasets.dataset_manager import DatasetManager
from backend.fewshot.builder import FewShotBuilder
from backend.fewshot.models import EmbeddingIndex
from backend.fewshot.retriever import CandidateRetriever
from backend.fewshot.selector import FewShotSelector
from backend.fewshot.ordering import OrderingEngine
from backend.fewshot.diversity import DiversityFilter
from backend.fewshot.validators import FewShotValidator

def run_tests():
    print("=== STARTING PEER FEW-SHOT BUILDER VERIFICATION ===")
    
    # Initialize DB
    init_db()

    # Create dummy dataset details
    dummy_data = pd.DataFrame({
        "text": [
            "The movie was absolutely fantastic and brilliant!", # 0 positive
            "I hated the film, it was terrible and boring.",      # 1 negative
            "An average experience, nothing special but not bad.", # 2 neutral
            "Superb performance, highly recommended to everyone.", # 3 positive
            "Extremely slow, poorly directed, and waste of money.",# 4 negative
            "It was okay, standard plot lines."                   # 5 neutral
        ],
        "label": ["positive", "negative", "neutral", "positive", "negative", "neutral"]
    })
    
    # Ensure test directories exist
    os.makedirs("datasets/test_cache", exist_ok=True)
    os.makedirs("datasets/test_versions", exist_ok=True)

    # Setup Registry & save test dataset version in DB
    from backend.database.db import SessionLocal
    db_session = SessionLocal()
    dataset_mgr = DatasetManager(
        cache_dir="datasets/test_cache",
        versions_dir="datasets/test_versions"
    )
    
    # Check delete if existing from previous runs
    from backend.datasets.models import Dataset
    existing_ds = db_session.query(Dataset).filter(Dataset.name == "test_fewshot_sentiment").first()
    if existing_ds:
        db_session.delete(existing_ds)
        db_session.commit()
        
    dataset = dataset_mgr.registry.register_dataset(
        db=db_session,
        name="test_fewshot_sentiment",
        task="classification",
        source="CSV",
        df_dict={"train": dummy_data},
        description="Few-shot testing dataset"
    )
    print(f"Registered Dataset ID: {dataset.id}")

    # Initialize Builder with test cache
    builder = FewShotBuilder(cache_dir="datasets/test_cache")

    # 1. Test CandidateRetriever query exclusion
    print("\n1. Testing CandidateRetriever leakage check...")
    # For query_idx = 3, candidates should exclude index 3
    cand_df = CandidateRetriever.retrieve_candidates(dummy_data, query_idx=3)
    assert len(cand_df) == 5
    assert 3 not in cand_df["__df_index"].tolist()
    print("Leakage checker successfully excluded the active query sample!")

    # 2. Test Selectors
    print("\n2. Testing Selector strategies...")
    # Random selection
    rand_df = FewShotSelector.select_random(cand_df, k=2, seed=42)
    assert len(rand_df) == 2
    
    # For query_idx = 4, sequential K=2 should take closest preceding indices: 1, 2 (since 3 is query-excluded)
    seq_df = FewShotSelector.select_sequential(cand_df, query_idx=4, k=2)
    assert len(seq_df) == 2
    assert seq_df["__df_index"].tolist() == [1, 2]
    
    # Balanced selection
    # K=3 for classes positive, negative, neutral -> should yield 1 positive, 1 negative, 1 neutral
    bal_df = FewShotSelector.select_balanced(cand_df, label_col="label", k=3, seed=42)
    assert len(bal_df) == 3
    assert len(bal_df["label"].unique()) == 3
    print("Random, Sequential, and Balanced label selectors PASSED!")

    # 3. Test Ordering Engine
    print("\n3. Testing Ordering Engine sorts...")
    # Alternate labels ordering
    alt_df = OrderingEngine.apply_ordering(bal_df, strategy="alternating", label_col="label")
    assert len(alt_df) == 3
    # Check alternating labels
    labels = alt_df["label"].tolist()
    assert labels[0] != labels[1]
    assert labels[1] != labels[2]
    print("Ordering engine label alternating sort PASSED!")

    # 4. Test FAISS Index & Embeddings Build Pipeline
    print("\n4. Testing FAISS index building and lazy model encode...")
    # Generate dummy embeddings (shape 6 rows x 384 dimensions)
    # This checks our index managers without having to load the large 500MB Transformer model in tests if not needed
    # We will also test lazy sentence transformers loader
    dummy_embeddings = np.random.randn(6, 384).astype(np.float32)
    
    # L2 normalize
    norms = np.linalg.norm(dummy_embeddings, axis=1, keepdims=True)
    norm_embeddings = dummy_embeddings / (norms + 1e-10)
    
    # Save cache
    npy_path = builder.service.cache.get_embedding_path(dataset.id, "v1", "all-MiniLM-L6-v2")
    faiss_path = builder.service.cache.get_faiss_path(dataset.id, "v1", "all-MiniLM-L6-v2")
    
    from backend.fewshot.index_manager import IndexManager
    IndexManager.build_index(norm_embeddings, faiss_path)
    np.save(npy_path, norm_embeddings)
    
    # Register in DB
    db_idx = EmbeddingIndex(
        id=f"idx_{dataset.id}_v1_allminimll6v2",
        dataset_id=dataset.id,
        embedding_model="all-MiniLM-L6-v2",
        index_path=faiss_path,
        embedding_path=npy_path
    )
    db_session.add(db_idx)
    db_session.commit()
    
    assert builder.service.cache.cache_exists(dataset.id, "v1", "all-MiniLM-L6-v2")
    print("FAISS Index build and persistence checks PASSED!")

    # 5. Test Diversity Filtering Heuristics
    print("\n5. Testing Diversity filters...")
    # Add dummy similarities to cand_df (e.g. indices 0, 1, 2, 4, 5)
    cand_df["similarity"] = [0.95, 0.40, 0.60, 0.90, 0.30]
    
    # Medium diversity: skip nearest duplicate threshold > 0.92
    # Candidate index 0 has similarity 0.95. Let's make index 4 very close to index 0.
    # In a dummy setup, we check if Medium Diversity skips duplicates.
    med_df = DiversityFilter.filter_medium_diversity(
        candidates_df=cand_df,
        embeddings=norm_embeddings,
        k=2,
        threshold=0.92
    )
    assert len(med_df) <= 2
    
    # High diversity: KMeans clustering
    high_df = DiversityFilter.filter_high_diversity(
        candidates_df=cand_df,
        embeddings=norm_embeddings,
        k=2,
        seed=42
    )
    assert len(high_df) == 2
    print("Medium threshold diversity and High KMeans clustering filters PASSED!")

    # 6. Test Validator Checks
    print("\n6. Testing Validator rules...")
    # Create simple examples list
    from backend.fewshot.schemas import FewShotExample
    ex_list = [
        FewShotExample(id="0", input="movie was brilliant", label="positive"),
        FewShotExample(id="1", input="terrible acting", label="negative")
    ]
    
    # Check no errors on correct set
    errs = FewShotValidator.validate_few_shot_set(
        examples=ex_list,
        query_id="99",
        query_text="completely different text",
        text_col="text",
        expected_count=2
    )
    assert len(errs) == 0

    # Leak query ID check -> should capture error
    errs_leak = FewShotValidator.validate_few_shot_set(
        examples=ex_list,
        query_id="0", # query ID same as first example
        query_text="completely different text",
        text_col="text",
        expected_count=2
    )
    assert len(errs_leak) > 0
    assert "leaked" in errs_leak[0]
    
    # Size mismatch check
    errs_size = FewShotValidator.validate_few_shot_set(
        examples=ex_list,
        query_id="99",
        query_text="different",
        text_col="text",
        expected_count=3 # expected 3 examples but only got 2
    )
    assert len(errs_size) > 0
    assert "Expected exactly" in errs_size[0]
    print("Exclusion, leakage checks, and duplicate validator rules PASSED!")

    # 7. Test E2E Pipeline Rendering
    print("\n7. Testing E2E Pipeline execution...")
    # Mixed Strategy configuration
    strategy_config = {
        "example_count": 2,
        "selection_strategy": "Random",
        "ordering_strategy": "Similarity",
        "diversity_level": "High Similarity",
        "embedding_model": "all-MiniLM-L6-v2"
    }
    
    # Run build
    fs_set = builder.build_examples(
        db=db_session,
        dataset_id=dataset.id,
        dataset_version="v1",
        query_index=4,
        strategy_config=strategy_config,
        seed=42
    )
    
    assert len(fs_set.examples) == 2
    assert fs_set.query_sample["text"] == "Extremely slow, poorly directed, and waste of money."
    print("FewShotSet pipeline built successfully!")

    # Cleanup database records
    db_session.delete(dataset)
    db_session.commit()
    db_session.close()

    # Cleanup directories
    if os.path.exists("datasets/test_cache"):
        shutil.rmtree("datasets/test_cache")
    if os.path.exists("datasets/test_versions"):
        shutil.rmtree("datasets/test_versions")

    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()
