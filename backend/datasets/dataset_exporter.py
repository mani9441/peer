import os
import pandas as pd
from typing import Dict, Union, Optional
import logging

logger = logging.getLogger(__name__)

class DatasetExporter:
    """
    Exports a single DataFrame or a dictionary of split DataFrames to local storage.
    """
    
    def __init__(self, export_dir: str = "exports"):
        self.export_dir = export_dir
        os.makedirs(self.export_dir, exist_ok=True)

    def export(
        self, 
        data: Union[pd.DataFrame, Dict[str, pd.DataFrame]], 
        filename: str, 
        format: str = "csv"
    ) -> Union[str, Dict[str, str]]:
        """
        Exports DataFrame(s) to the specified format ('csv', 'json', 'parquet').
        If data is a dictionary of splits, it will create separate files for each split
        (e.g., filename_train.csv, filename_test.csv) and return a dictionary of paths.
        """
        format = format.lower().strip()
        if format not in ["csv", "json", "parquet"]:
            raise ValueError(f"Unsupported export format: {format}")

        if isinstance(data, pd.DataFrame):
            # Single dataframe export
            ext = f".{format}"
            if not filename.endswith(ext):
                filename += ext
            filepath = os.path.join(self.export_dir, filename)
            
            self._write_df(data, filepath, format)
            logger.info(f"Successfully exported DataFrame to {filepath}")
            return filepath
            
        elif isinstance(data, dict):
            # Multiple splits export
            paths = {}
            base, ext = os.path.splitext(filename)
            if not ext:
                ext = f".{format}"
            else:
                # If format is provided, make sure it matches the ext
                ext = f".{format}"
                
            for split, df in data.items():
                split_filename = f"{base}_{split}{ext}"
                filepath = os.path.join(self.export_dir, split_filename)
                self._write_df(df, filepath, format)
                paths[split] = filepath
                
            logger.info(f"Successfully exported split DataFrames: {paths}")
            return paths
        else:
            raise TypeError("Data must be a pandas DataFrame or a dictionary of pandas DataFrames.")

    def _write_df(self, df: pd.DataFrame, filepath: str, format: str):
        if format == "csv":
            df.to_csv(filepath, index=False)
        elif format == "json":
            df.to_json(filepath, orient="records", indent=2)
        elif format == "parquet":
            df.to_parquet(filepath, index=False)
