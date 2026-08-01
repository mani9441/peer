import pandas as pd
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class OrderingEngine:
    """
    Applies original, random, similarity, or alternating label ordering to few-shot selections.
    """

    @staticmethod
    def order_by_original(df: pd.DataFrame) -> pd.DataFrame:
        """Restores original dataset file ordering using '__df_index'."""
        if "__df_index" in df.columns:
            return df.sort_values(by="__df_index", ascending=True).reset_index(drop=True)
        return df

    @staticmethod
    def order_by_random(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
        """Shuffles examples randomly using seed."""
        return df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    @staticmethod
    def order_by_similarity(df: pd.DataFrame, ascending: bool = False) -> pd.DataFrame:
        """Sorts by similarity score column (descending = highest first, ascending = lowest first)."""
        if "similarity" in df.columns:
            return df.sort_values(by="similarity", ascending=ascending).reset_index(drop=True)
        return df

    @staticmethod
    def order_by_label_alternating(df: pd.DataFrame, label_col: str) -> pd.DataFrame:
        """
        Interleaves records so that their class labels alternate in sequence.
        Assumes classification task.
        """
        if label_col not in df.columns:
            return df
            
        # Group by labels
        classes = df[label_col].dropna().unique().tolist()
        if len(classes) <= 1:
            return df
            
        groups = {c: df[df[label_col] == c].to_dict("records") for c in classes}
        ordered_records = []
        
        # Interleave elements in round-robin fashion
        max_len = max(len(lst) for lst in groups.values())
        for idx in range(max_len):
            for c in classes:
                if idx < len(groups[c]):
                    ordered_records.append(groups[c][idx])
                    
        return pd.DataFrame(ordered_records)

    @classmethod
    def apply_ordering(
        cls, 
        df: pd.DataFrame, 
        strategy: str, 
        label_col: Optional[str] = None, 
        seed: int = 42
    ) -> pd.DataFrame:
        """
        Applies target ordering strategy.
        """
        strategy = strategy.lower().strip()
        if df.empty:
            return df
            
        if strategy == "original":
            return cls.order_by_original(df)
        elif strategy == "random":
            return cls.order_by_random(df, seed=seed)
        elif strategy == "similarity":
            return cls.order_by_similarity(df, ascending=False)
        elif strategy == "reverse similarity":
            return cls.order_by_similarity(df, ascending=True)
        elif strategy == "alternating":
            if not label_col:
                raise ValueError("Label column is required for alternating labels ordering.")
            return cls.order_by_label_alternating(df, label_col)
        else:
            raise ValueError(f"Unknown ordering strategy: {strategy}")
