import pandas as pd
import random
from typing import Dict, Any, List, Optional
from backend.fewshot.schemas import FewShotExample
import logging

logger = logging.getLogger(__name__)

class FewShotSelector:
    """
    Implements random, sequential, and balanced label few-shot selection strategies.
    """

    @staticmethod
    def select_random(candidates_df: pd.DataFrame, k: int, seed: int = 42) -> pd.DataFrame:
        """Randomly samples k records from candidate pool."""
        take = min(len(candidates_df), k)
        return candidates_df.sample(n=take, random_state=seed).reset_index(drop=True)

    @staticmethod
    def select_sequential(candidates_df: pd.DataFrame, query_idx: int, k: int) -> pd.DataFrame:
        """
        Selects up to k examples immediately preceding the query index (relative to original dataset order).
        Helps evaluate context leakage/ordering properties.
        """
        # Filter for candidates with original dataset index preceding the query index
        # using the __df_index tracker column
        preceding = candidates_df[candidates_df["__df_index"] < query_idx]
        
        # Sort by original index descending (closest preceding first)
        preceding_sorted = preceding.sort_values(by="__df_index", ascending=False)
        
        # Take closest K
        selected = preceding_sorted.head(k)
        
        # Re-sort to original order ascending
        return selected.sort_values(by="__df_index", ascending=True).reset_index(drop=True)

    @classmethod
    def select_balanced(
        cls, 
        candidates_df: pd.DataFrame, 
        label_col: str, 
        k: int, 
        seed: int = 42
    ) -> pd.DataFrame:
        """
        Selects examples maintaining balanced representation of labels.
        The difference in representation counts between any two classes will not exceed 1.
        """
        classes = candidates_df[label_col].dropna().unique().tolist()
        num_classes = len(classes)
        
        if num_classes == 0:
            return cls.select_random(candidates_df, k, seed)

        # Distribute count k across classes
        base_per_class = k // num_classes
        remainder = k % num_classes
        
        # Assign allocation sizes per class
        allocations = {c: base_per_class for c in classes}
        # Seed random choice of which classes get the remainder allocations to ensure reproducibility
        rng = random.Random(seed)
        extra_classes = rng.sample(classes, remainder)
        for c in extra_classes:
            allocations[c] += 1
            
        sampled_dfs = []
        for c, count in allocations.items():
            if count == 0:
                continue
            class_df = candidates_df[candidates_df[label_col] == c]
            take = min(len(class_df), count)
            if take > 0:
                sampled_dfs.append(class_df.sample(n=take, random_state=seed))
                
        if not sampled_dfs:
            return pd.DataFrame()
            
        # Combine and shuffle
        combined = pd.concat(sampled_dfs)
        return combined.sample(frac=1.0, random_state=seed).reset_index(drop=True)
