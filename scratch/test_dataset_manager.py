import os
import pandas as pd
import numpy as np
import sys

# Ensure backend can be imported
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from backend.database.db import get_db, init_db
from backend.datasets.dataset_manager import DatasetManager
from backend.datasets.models import Dataset, DatasetVersion, DatasetStatistics

def run_tests():
    print("=== STARTING PEER DATASET MANAGER VERIFICATION ===")
    
    # Initialize DB schema
    init_db()
    
    # Initialize manager
    manager = DatasetManager(
        cache_dir="datasets/.cache/test_hf",
        versions_dir="datasets/test_versions",
        export_dir="exports/test_exports"
    )
    
    # 1. Create dummy Classification dataset
    dummy_data = pd.DataFrame({
        "text": [
            "The movie was absolutely fantastic and brilliant!",
            "I hated the film, it was terrible and boring.",
            "An average experience, nothing special but not bad.",
            "Superb performance, highly recommended to everyone.",
            "Extremely slow, poorly directed, and waste of money.",
            "It was okay, standard plot lines."
        ],
        "label": ["positive", "negative", "neutral", "positive", "negative", "neutral"]
    })
    
    df_dict = {"train": dummy_data}
    
    # 2. Register Dataset
    print("\n1. Testing dataset registration...")
    with get_db() as db:
        # Check if already registered
        dataset = manager.registry.register_dataset(
            db=db,
            name="test_dummy_sentiment",
            task="classification",
            source="CSV",
            df_dict=df_dict,
            description="Testing dataset",
            language="English",
            license="MIT"
        )
        print(f"Registered Dataset ID: {dataset.id}")
        assert dataset.name == "test_dummy_sentiment"
        assert dataset.version == "v1"
        assert dataset.samples == 6
        assert dataset.splits == "train"
        
        # Verify stats generated
        stats = db.query(DatasetStatistics).filter(DatasetStatistics.dataset_id == dataset.id).first()
        assert stats is not None
        assert stats.total_samples == 6
        print("Dataset registered and statistics verified!")

    # 3. Test Loading version files
    print("\n2. Testing loading version files back...")
    with get_db() as db:
        loaded_dict = manager.get_dataset_version_data(db, dataset.id, "v1")
        assert "train" in loaded_dict
        assert len(loaded_dict["train"]) == 6
        print("Data loaded back from Parquet matches source size!")

    # 4. Test Validation rules
    print("\n3. Testing schema validator...")
    val_report = manager.validate_dataset(dummy_data, "classification")
    assert val_report["status"] == "PASS"
    assert val_report["column_mapping"]["text"] == "text"
    assert val_report["column_mapping"]["label"] == "label"
    print("Schema validator report: PASS")

    # 5. Test Sampler (Balanced)
    print("\n4. Testing Balanced sampler...")
    # Sample 1 per class (positive, negative, neutral) -> should yield 3 samples
    sampled_df = manager.sample_dataset(dummy_data, "balanced", {"n_per_class": 1}, label_col="label")
    assert len(sampled_df) == 3
    # Check that labels are unique and balanced
    assert len(sampled_df["label"].unique()) == 3
    print("Balanced sampler returned correct number of balanced records!")

    # 6. Test Splitter
    print("\n5. Testing Splitter...")
    # Split 6 rows with 1 val and 1 test roughly (e.g. 1/3 and 1/3)
    splits_dict = manager.split_dataset(dummy_data, val_ratio=0.33, test_ratio=0.33, label_col="label", stratify=True)
    assert "train" in splits_dict
    assert "validation" in splits_dict
    assert "test" in splits_dict
    print(f"Splits generated: train={len(splits_dict['train'])}, val={len(splits_dict['validation'])}, test={len(splits_dict['test'])}")

    # 7. Test Filter
    print("\n6. Testing Filter...")
    # Filter for texts containing 'movie' (only 1 row matches)
    filtered_df = manager.filter_dataset(dummy_data, text_col="text", query="movie")
    assert len(filtered_df) == 1
    # Filter by label
    filtered_df_label = manager.filter_dataset(dummy_data, label_col="label", labels=["positive"])
    assert len(filtered_df_label) == 2
    print("Query and label filtering working correctly!")

    # 8. Test Version Saving
    print("\n7. Testing version creation...")
    with get_db() as db:
        new_splits = {"train": sampled_df}
        ver_rec = manager.save_version(
            db=db,
            dataset_id=dataset.id,
            version_name="v2_sampled",
            df_dict=new_splits,
            parent_version="v1",
            transformations={"strategy": "balanced_1_per_class"}
        )
        print(f"Created version: {ver_rec.version} with samples count: {ver_rec.dataset.samples}")
        assert ver_rec.version == "v2_sampled"
        assert ver_rec.dataset.version == "v2_sampled"
        assert ver_rec.dataset.samples == 3
        
        # Verify stats updated
        stats2 = db.query(DatasetStatistics).filter(DatasetStatistics.dataset_id == dataset.id).first()
        assert stats2.total_samples == 3
        print("Version metadata and statistics successfully updated!")

    # 9. Test Exporting
    print("\n8. Testing exporter...")
    export_paths = manager.export_dataset(df_dict, "test_dummy_sentiment", "csv")
    assert "train" in export_paths
    assert os.path.exists(export_paths["train"])
    print(f"Exported files written to: {export_paths}")

    # Cleanup test files
    print("\nCleaning up test files...")
    import shutil
    if os.path.exists("datasets/test_versions"):
        shutil.rmtree("datasets/test_versions")
    if os.path.exists("exports/test_exports"):
        shutil.rmtree("exports/test_exports")
    
    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()
