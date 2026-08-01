import pandas as pd
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session

from backend.datasets.dataset_loader import DatasetLoader
from backend.datasets.dataset_validator import DatasetValidator
from backend.datasets.dataset_statistics import DatasetStatistics as StatsEngine
from backend.datasets.dataset_sampler import DatasetSampler
from backend.datasets.dataset_splitter import DatasetSplitter
from backend.datasets.dataset_filter import DatasetFilter
from backend.datasets.dataset_exporter import DatasetExporter
from backend.datasets.dataset_registry import DatasetRegistry
from backend.datasets.models import Dataset, DatasetVersion

class DatasetManager:
    """
    The orchestrator class for all dataset operations in the PEER Framework.
    Downstream modules interact primarily with this manager.
    """
    
    def __init__(self, cache_dir: str = "datasets/.cache/huggingface", versions_dir: str = "datasets/versions", export_dir: str = "exports"):
        self.loader = DatasetLoader(cache_dir=cache_dir)
        self.validator = DatasetValidator()
        self.sampler = DatasetSampler()
        self.splitter = DatasetSplitter()
        self.filterer = DatasetFilter()
        self.exporter = DatasetExporter(export_dir=export_dir)
        self.registry = DatasetRegistry(versions_dir=versions_dir)

    def load_dataset(
        self, 
        source: str, 
        path: str, 
        name: Optional[str] = None, 
        split: Optional[str] = None,
        db: Optional[Session] = None,
        save_in_registry: bool = True,
        task: Optional[str] = None,
        description: Optional[str] = None,
        language: str = "English",
        license: str = "Unknown",
        label_mapping: Optional[Dict[int, str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Loads dataset from Hugging Face, CSV, or JSON.
        If db is provided and save_in_registry=True, it registers the dataset in the SQLite DB (v1).
        """
        source = source.lower().strip()
        if source == "huggingface":
            df_dict = self.loader.load_from_hf(path, name=name, split=split)
            if not label_mapping:
                label_mapping = self.loader.last_extracted_labels
        elif source == "csv":
            df_dict = self.loader.load_from_csv(path)
        elif source == "json":
            df_dict = self.loader.load_from_json(path)
        else:
            raise ValueError(f"Unknown dataset source: {source}")

        if save_in_registry and db is not None:
            if not task:
                raise ValueError("Task type ('classification' or 'qa') must be specified when saving to registry.")
            # Use path or name as registration name
            reg_name = name or path.split("/")[-1].replace(".csv", "").replace(".json", "")
            self.registry.register_dataset(
                db=db,
                name=reg_name,
                task=task,
                source=source.capitalize(),
                df_dict=df_dict,
                description=description,
                language=language,
                license=license,
                label_mapping=label_mapping
            )

        return df_dict

    def validate_dataset(self, df: pd.DataFrame, task_type: str, custom_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Validates the dataset schema and reports issues."""
        return self.validator.validate(df, task_type, custom_mapping)

    def preview_dataset(self, df: pd.DataFrame, n: int = 100) -> pd.DataFrame:
        """Returns the first N rows for inspection."""
        return df.head(n)

    def sample_dataset(self, df: pd.DataFrame, strategy: str, params: Dict[str, Any], label_col: Optional[str] = None, seed: int = 42) -> pd.DataFrame:
        """Samples the dataset using the specified strategy and parameters."""
        return self.sampler.sample(df, strategy, params, label_col, seed)

    def split_dataset(
        self, 
        df: pd.DataFrame, 
        val_ratio: float, 
        test_ratio: float, 
        label_col: Optional[str] = None, 
        seed: int = 42, 
        stratify: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """Splits a single dataframe into train, validation, and test splits."""
        return self.splitter.split(df, val_ratio, test_ratio, label_col, seed, stratify)

    def filter_dataset(
        self, 
        df: pd.DataFrame, 
        text_col: Optional[str] = None, 
        label_col: Optional[str] = None,
        labels: Optional[List[Any]] = None,
        min_len: Optional[int] = None,
        max_len: Optional[int] = None,
        query: Optional[str] = None,
        case_sensitive: bool = False
    ) -> pd.DataFrame:
        """Applies query, length, or label filters on the dataset."""
        return self.filterer.apply_filters(
            df=df,
            text_col=text_col,
            label_col=label_col,
            labels=labels,
            min_len=min_len,
            max_len=max_len,
            query=query,
            case_sensitive=case_sensitive
        )

    def get_statistics(self, df: pd.DataFrame, task_type: str, mapping: Dict[str, str]) -> Dict[str, Any]:
        """Generates statistical metrics for the dataset."""
        return StatsEngine.compute(df, task_type, mapping)

    def export_dataset(
        self, 
        data: Union[pd.DataFrame, Dict[str, pd.DataFrame]], 
        filename: str, 
        format: str = "csv"
    ) -> Union[str, Dict[str, str]]:
        """Exports the dataset to local CSV/JSON/Parquet file(s)."""
        return self.exporter.export(data, filename, format)

    def list_datasets(self, db: Session) -> List[Dataset]:
        """Lists all registered datasets from the database."""
        return self.registry.list_datasets(db)

    def get_dataset(self, db: Session, dataset_id: str) -> Optional[Dataset]:
        """Fetches registered dataset info by ID."""
        return self.registry.get_dataset(db, dataset_id)

    def get_dataset_version_data(self, db: Session, dataset_id: str, version: str) -> Dict[str, pd.DataFrame]:
        """Retrieves split dataframes for a specific dataset version."""
        return self.registry.get_dataset_version_data(db, dataset_id, version)

    def save_version(
        self,
        db: Session,
        dataset_id: str,
        version_name: str,
        df_dict: Dict[str, pd.DataFrame],
        parent_version: str,
        transformations: Dict[str, Any],
        label_mapping: Optional[Dict[int, str]] = None
    ) -> DatasetVersion:
        """Saves a new dataset version record and serializes split files."""
        return self.registry.create_dataset_version(
            db=db,
            dataset_id=dataset_id,
            version=version_name,
            df_dict=df_dict,
            parent_version=parent_version,
            transformations=transformations,
            label_mapping=label_mapping
        )

    def get_label_mapping(self, db: Session, dataset_id: str) -> Dict[int, str]:
        from backend.datasets.models import DatasetLabel
        labels = db.query(DatasetLabel).filter(DatasetLabel.dataset_id == dataset_id).all()
        return {lbl.label_id: lbl.label_name for lbl in labels}

    def get_label_name(self, db: Session, dataset_id: str, label_id: int) -> Optional[str]:
        from backend.datasets.models import DatasetLabel
        lbl = db.query(DatasetLabel).filter(
            DatasetLabel.dataset_id == dataset_id,
            DatasetLabel.label_id == label_id
        ).first()
        return lbl.label_name if lbl else None

    def get_all_labels(self, db: Session, dataset_id: str) -> List[Dict[str, Any]]:
        from backend.datasets.models import DatasetLabel
        labels = db.query(DatasetLabel).filter(DatasetLabel.dataset_id == dataset_id).all()
        return [
            {"label_id": lbl.label_id, "label_name": lbl.label_name, "description": lbl.description}
            for lbl in labels
        ]

    def validate_labels(self, db: Session, dataset_id: str) -> Dict[str, Any]:
        """
        Validates the registry labels against the dataset split samples.
        """
        from backend.datasets.models import DatasetLabel
        errors = []
        
        labels = db.query(DatasetLabel).filter(DatasetLabel.dataset_id == dataset_id).all()
        if not labels:
            errors.append("Label Registry is empty for this dataset.")
            return {"status": "FAIL", "errors": errors}
            
        label_ids = [lbl.label_id for lbl in labels]
        label_names = [lbl.label_name for lbl in labels]
        
        if len(label_ids) != len(set(label_ids)):
            errors.append("Duplicate label IDs detected in the registry.")
        if len(label_names) != len(set(label_names)):
            errors.append("Duplicate label names detected in the registry.")
            
        try:
            dataset = self.get_dataset(db, dataset_id)
            if dataset:
                df_dict = self.get_dataset_version_data(db, dataset_id, dataset.version)
                if df_dict:
                    pref_split = "train" if "train" in df_dict else list(df_dict.keys())[0]
                    val_report = DatasetValidator.detect_and_normalize_columns(df_dict[pref_split], dataset.task)
                    mapping = val_report.get("column_mapping", {})
                    label_col = mapping.get("label")
                    
                    if label_col:
                        unique_values = set()
                        for split, df in df_dict.items():
                            if label_col in df.columns:
                                unique_values.update(df[label_col].dropna().unique().tolist())
                                
                        for val in unique_values:
                            val_str = str(val).strip().lower()
                            matched = False
                            for lbl in labels:
                                if val_str == str(lbl.label_id).lower() or val_str == str(lbl.label_name).strip().lower():
                                    matched = True
                                    break
                            if not matched:
                                errors.append(f"Sample label value '{val}' is not mapped in the Label Registry.")
        except Exception as e:
            errors.append(f"Failed loading dataset samples for validation: {str(e)}")
            
        status = "FAIL" if errors else "PASS"
        return {"status": status, "errors": errors}
