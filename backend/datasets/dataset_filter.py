import pandas as pd
from typing import List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)

class DatasetFilter:
    """
    Applies filters to a dataset DataFrame without modifying the original.
    """
    
    @staticmethod
    def filter_by_label(df: pd.DataFrame, label_col: str, labels: List[Any]) -> pd.DataFrame:
        """Filters rows to only include specified label values."""
        if not labels:
            return df
        # Convert list elements to match series type as closely as possible
        # Check type of first element in series to avoid type mismatch
        sample_val = df[label_col].dropna().iloc[0] if not df[label_col].dropna().empty else None
        if sample_val is not None:
            typed_labels = []
            for l in labels:
                try:
                    typed_labels.append(type(sample_val)(l))
                except (ValueError, TypeError):
                    typed_labels.append(l)
            labels = typed_labels
            
        return df[df[label_col].isin(labels)].reset_index(drop=True)

    @staticmethod
    def filter_by_length(
        df: pd.DataFrame, 
        text_col: str, 
        min_len: Optional[int] = None, 
        max_len: Optional[int] = None
    ) -> pd.DataFrame:
        """Filters rows based on character length of the specified text column."""
        lengths = df[text_col].dropna().astype(str).str.len()
        mask = pd.Series(True, index=df.index)
        
        if min_len is not None:
            mask = mask & (lengths >= min_len)
        if max_len is not None:
            mask = mask & (lengths <= max_len)
            
        # Handle cases where the text column was NaN (treat as excluded)
        mask = mask & df[text_col].notna()
        
        return df[mask].reset_index(drop=True)

    @staticmethod
    def filter_by_query(df: pd.DataFrame, text_col: str, query: str, case_sensitive: bool = False) -> pd.DataFrame:
        """Filters rows that contain the search query in the specified text column."""
        if not query:
            return df
        # Force string conversion and use str.contains
        mask = df[text_col].dropna().astype(str).str.contains(query, case=case_sensitive, regex=False)
        # Reindex to match dataframe indices
        mask = mask.reindex(df.index, fill_value=False)
        return df[mask].reset_index(drop=True)

    @classmethod
    def apply_filters(
        cls, 
        df: pd.DataFrame, 
        text_col: Optional[str] = None, 
        label_col: Optional[str] = None,
        labels: Optional[List[Any]] = None,
        min_len: Optional[int] = None,
        max_len: Optional[int] = None,
        query: Optional[str] = None,
        case_sensitive: bool = False
    ) -> pd.DataFrame:
        """
        Applies multiple filters in sequence.
        """
        filtered_df = df.copy()
        
        if label_col and labels:
            filtered_df = cls.filter_by_label(filtered_df, label_col, labels)
            
        if text_col:
            if min_len is not None or max_len is not None:
                filtered_df = cls.filter_by_length(filtered_df, text_col, min_len, max_len)
            if query:
                filtered_df = cls.filter_by_query(filtered_df, text_col, query, case_sensitive)
                
        return filtered_df
