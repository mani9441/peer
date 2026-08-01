import os
import hashlib
import json
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from backend.datasets.models import Dataset, DatasetVersion, DatasetStatistics, DatasetLabel
from backend.datasets.dataset_statistics import DatasetStatistics as StatsEngine
import logging

logger = logging.getLogger(__name__)

class DatasetRegistry:
    """
    Manages database transactions and local file storage for datasets and versions.
    """
    
    def __init__(self, versions_dir: str = "datasets/versions"):
        self.versions_dir = versions_dir
        os.makedirs(self.versions_dir, exist_ok=True)

    @staticmethod
    def compute_hash(df_dict: Dict[str, pd.DataFrame]) -> str:
        """
        Computes a stable hash for a dictionary of DataFrames.
        We do this by sorting the splits, converting each to a CSV byte string,
        and computing a cumulative SHA256.
        """
        hasher = hashlib.sha256()
        for split in sorted(df_dict.keys()):
            df = df_dict[split]
            # Convert to CSV format without index
            csv_str = df.to_csv(index=False)
            hasher.update(split.encode('utf-8'))
            hasher.update(csv_str.encode('utf-8'))
        return hasher.hexdigest()

    def save_version_files(self, dataset_id: str, version: str, df_dict: Dict[str, pd.DataFrame]) -> Dict[str, str]:
        """
        Saves splits of a dataset version to Parquet format.
        Returns a dictionary of split names to file paths.
        """
        paths = {}
        for split, df in df_dict.items():
            filename = f"{dataset_id}_{version}_{split}.parquet"
            filepath = os.path.join(self.versions_dir, filename)
            df.to_parquet(filepath, index=False)
            paths[split] = filepath
        return paths

    def load_version_files(self, paths_json: str) -> Dict[str, pd.DataFrame]:
        """
        Loads splits of a dataset version from Parquet format.
        """
        paths = json.loads(paths_json)
        df_dict = {}
        for split, path in paths.items():
            if not os.path.exists(path):
                raise FileNotFoundError(f"Parquet file for split '{split}' not found at {path}")
            df_dict[split] = pd.read_parquet(path)
        return df_dict

    def register_dataset(
        self, 
        db: Session, 
        name: str, 
        task: str, 
        source: str, 
        df_dict: Dict[str, pd.DataFrame], 
        description: Optional[str] = None,
        language: str = "English",
        license: str = "Unknown",
        label_mapping: Optional[Dict[int, str]] = None
    ) -> Dataset:
        """
        Registers a new dataset (v1) and stores its files and statistics.
        """
        # Generate stable dataset ID from name
        clean_name = "".join(c for c in name if c.isalnum() or c in ("_", "-")).lower()
        dataset_id = f"{clean_name}_{int(pd.Timestamp.now().timestamp())}"
        
        # Compute hashes
        hash_val = self.compute_hash(df_dict)
        
        # Check if hash already exists in DB to prevent duplicates
        existing = db.query(Dataset).filter(Dataset.hash == hash_val).first()
        if existing:
            logger.info(f"Dataset already registered with ID {existing.id}")
            return existing

        # Create local Parquet files
        paths = self.save_version_files(dataset_id, "v1", df_dict)
        
        # Count total samples
        total_samples = sum(len(df) for df in df_dict.values())
        splits_str = ",".join(df_dict.keys())
        
        # 1. Create Dataset model
        dataset = Dataset(
            id=dataset_id,
            name=name,
            version="v1",
            task=task,
            source=source,
            language=language,
            samples=total_samples,
            splits=splits_str,
            license=license,
            hash=hash_val,
            description=description
        )
        db.add(dataset)
        db.flush()  # Retrieve dataset.id for relationships
        
        # 2. Create DatasetVersion model
        version_rec = DatasetVersion(
            dataset_id=dataset.id,
            version="v1",
            parent_version=None,
            transformations=json.dumps({"info": "Initial registration"}),
            hash=hash_val,
            path=json.dumps(paths)
        )
        db.add(version_rec)
        
        # 3. Compute and store Statistics (combining splits for overall analysis or using mapping)
        # We need a column mapping. We'll attempt auto-detection for stats.
        from backend.datasets.dataset_validator import DatasetValidator
        # Pick the largest split or train split for columns mapping
        pref_split = "train" if "train" in df_dict else list(df_dict.keys())[0]
        val_report = DatasetValidator.detect_and_normalize_columns(df_dict[pref_split], task)
        mapping = val_report.get("column_mapping", {})
        
        # Combine all splits for overall stats computing
        combined_df = pd.concat(df_dict.values(), ignore_index=True)
        stats_data = StatsEngine.compute(combined_df, task, mapping)
        
        stats_rec = DatasetStatistics(
            dataset_id=dataset.id,
            total_samples=stats_data["total_samples"],
            class_distribution=stats_data["class_distribution"],
            avg_length=stats_data["avg_length"],
            min_length=stats_data["min_length"],
            max_length=stats_data["max_length"],
            imbalance_score=stats_data["imbalance_score"],
            metadata_json=stats_data["metadata_json"]
        )
        db.add(stats_rec)
        
        # 4. Save Label definitions
        if task == "classification":
            if not label_mapping:
                label_mapping = {}
                pref_split = "train" if "train" in df_dict else list(df_dict.keys())[0]
                val_report = DatasetValidator.detect_and_normalize_columns(df_dict[pref_split], task)
                mapping = val_report.get("column_mapping", {})
                label_col = mapping.get("label")
                if label_col and label_col in df_dict[pref_split].columns:
                    unique_labels = df_dict[pref_split][label_col].dropna().unique().tolist()
                    try:
                        numeric_vals = sorted([int(val) for val in unique_labels])
                        label_mapping = {val: str(val) for val in numeric_vals}
                    except ValueError:
                        string_vals = sorted([str(val).strip() for val in unique_labels])
                        label_mapping = {i: val for i, val in enumerate(string_vals)}
            
            if label_mapping:
                for lbl_id, lbl_name in label_mapping.items():
                    db_lbl = DatasetLabel(
                        dataset_id=dataset.id,
                        label_id=int(lbl_id),
                        label_name=str(lbl_name)
                    )
                    db.add(db_lbl)
        
        db.commit()
        logger.info(f"Registered new dataset: {dataset.id}")
        return dataset

    def create_dataset_version(
        self,
        db: Session,
        dataset_id: str,
        version: str,
        df_dict: Dict[str, pd.DataFrame],
        parent_version: str,
        transformations: Dict[str, Any],
        label_mapping: Optional[Dict[int, str]] = None
    ) -> DatasetVersion:
        """
        Creates a new version for an existing dataset.
        Updates the dataset's current active version name and counts.
        """
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} not found.")
            
        # Verify version name doesn't exist already
        existing_ver = db.query(DatasetVersion).filter(
            DatasetVersion.dataset_id == dataset_id,
            DatasetVersion.version == version
        ).first()
        if existing_ver:
            raise ValueError(f"Version '{version}' already exists for dataset '{dataset_id}'.")

        # Compute hash
        hash_val = self.compute_hash(df_dict)
        
        # Save Parquet files
        paths = self.save_version_files(dataset_id, version, df_dict)
        
        # Save DB record
        version_rec = DatasetVersion(
            dataset_id=dataset_id,
            version=version,
            parent_version=parent_version,
            transformations=json.dumps(transformations),
            hash=hash_val,
            path=json.dumps(paths)
        )
        db.add(version_rec)
        
        # Update main Dataset properties
        dataset.version = version
        dataset.samples = sum(len(df) for df in df_dict.values())
        dataset.splits = ",".join(df_dict.keys())
        dataset.hash = hash_val
        
        # Update Statistics for the new version
        from backend.datasets.dataset_validator import DatasetValidator
        pref_split = "train" if "train" in df_dict else list(df_dict.keys())[0]
        val_report = DatasetValidator.detect_and_normalize_columns(df_dict[pref_split], dataset.task)
        mapping = val_report.get("column_mapping", {})
        
        combined_df = pd.concat(df_dict.values(), ignore_index=True)
        stats_data = StatsEngine.compute(combined_df, dataset.task, mapping)
        
        # Fetch or create statistics record
        stats_rec = db.query(DatasetStatistics).filter(DatasetStatistics.dataset_id == dataset_id).first()
        if not stats_rec:
            stats_rec = DatasetStatistics(dataset_id=dataset_id)
            db.add(stats_rec)
            
        stats_rec.total_samples = stats_data["total_samples"]
        stats_rec.class_distribution = stats_data["class_distribution"]
        stats_rec.avg_length = stats_data["avg_length"]
        stats_rec.min_length = stats_data["min_length"]
        stats_rec.max_length = stats_data["max_length"]
        stats_rec.imbalance_score = stats_data["imbalance_score"]
        stats_rec.metadata_json = stats_data["metadata_json"]
        
        # Save updated labels
        if label_mapping:
            db.query(DatasetLabel).filter(DatasetLabel.dataset_id == dataset_id).delete()
            for lbl_id, lbl_name in label_mapping.items():
                db_lbl = DatasetLabel(
                    dataset_id=dataset_id,
                    label_id=int(lbl_id),
                    label_name=str(lbl_name)
                )
                db.add(db_lbl)
        
        db.commit()
        logger.info(f"Created version '{version}' for dataset '{dataset_id}'")
        return version_rec

    def get_dataset(self, db: Session, dataset_id: str) -> Optional[Dataset]:
        return db.query(Dataset).filter(Dataset.id == dataset_id).first()

    def list_datasets(self, db: Session) -> List[Dataset]:
        return db.query(Dataset).order_by(Dataset.created_at.desc()).all()

    def get_dataset_version_data(self, db: Session, dataset_id: str, version: str) -> Dict[str, pd.DataFrame]:
        """
        Loads and returns the dictionary of DataFrames for a specific dataset and version.
        """
        ver_rec = db.query(DatasetVersion).filter(
            DatasetVersion.dataset_id == dataset_id,
            DatasetVersion.version == version
        ).first()
        if not ver_rec:
            raise ValueError(f"Version '{version}' not found for dataset '{dataset_id}'.")
        return self.load_version_files(ver_rec.path)
