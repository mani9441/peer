import os
import pandas as pd
from typing import Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)

class DatasetLoader:
    def __init__(self, cache_dir: Optional[str] = "datasets/.cache/huggingface"):
        self.cache_dir = cache_dir
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
        self.last_extracted_labels = {}

    def load_from_hf(self, path: str, name: Optional[str] = None, split: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Load a dataset from Hugging Face.
        Returns a dictionary mapping split names to pandas DataFrames.
        """
        from datasets import load_dataset, DatasetDict
        try:
            logger.info(f"Loading HF dataset {path} (name={name}, split={split}) with cache={self.cache_dir}")
            
            # Load dataset from Hugging Face
            kwargs = {}
            if name:
                kwargs["name"] = name
            if self.cache_dir:
                kwargs["cache_dir"] = self.cache_dir
                
            ds = load_dataset(path, **kwargs)
            
            # Extract ClassLabel features if present
            self.last_extracted_labels = {}
            try:
                from datasets import DatasetDict
                first_split = list(ds.keys())[0] if isinstance(ds, DatasetDict) else None
                split_ds = ds[first_split] if first_split else ds
                for col_name, feature in split_ds.features.items():
                    if hasattr(feature, "names") and isinstance(feature.names, list):
                        self.last_extracted_labels = {int(i): str(name) for i, name in enumerate(feature.names)}
                        break
            except Exception as hf_err:
                logger.warning(f"Could not extract HF ClassLabel features: {hf_err}")
            
            # Convert to DataFrames
            if isinstance(ds, DatasetDict):
                if split:
                    if split in ds:
                        return {split: ds[split].to_pandas()}
                    else:
                        raise ValueError(f"Split '{split}' not found in Hugging Face dataset. Available: {list(ds.keys())}")
                else:
                    return {s: ds[s].to_pandas() for s in ds.keys()}
            else:
                # It's a single Dataset
                split_name = split or "train"
                return {split_name: ds.to_pandas()}
        except Exception as e:
            logger.error(f"Failed to load Hugging Face dataset {path}: {str(e)}")
            raise RuntimeError(f"Hugging Face dataset load error: {str(e)}")

    def load_from_csv(self, filepath: str) -> Dict[str, pd.DataFrame]:
        """
        Load a dataset from a local CSV file.
        Returns a dictionary containing a single 'train' split.
        """
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"CSV file not found: {filepath}")
            df = pd.read_csv(filepath)
            return {"train": df}
        except Exception as e:
            logger.error(f"Failed to load CSV from {filepath}: {str(e)}")
            raise RuntimeError(f"CSV load error: {str(e)}")

    def load_from_json(self, filepath: str, orient: str = "records") -> Dict[str, pd.DataFrame]:
        """
        Load a dataset from a local JSON file.
        Returns a dictionary containing a single 'train' split.
        """
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"JSON file not found: {filepath}")
            # Try records first, if fails try default
            try:
                df = pd.read_json(filepath, orient=orient)
            except Exception:
                df = pd.read_json(filepath)
            return {"train": df}
        except Exception as e:
            logger.error(f"Failed to load JSON from {filepath}: {str(e)}")
            raise RuntimeError(f"JSON load error: {str(e)}")
