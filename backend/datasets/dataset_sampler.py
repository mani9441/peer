import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DatasetSampler:
    """
    Samples a subset of data from a DataFrame.
    """
    
    @staticmethod
    def sample_first_n(df: pd.DataFrame, n: int) -> pd.DataFrame:
        """Returns the first N rows."""
        return df.head(n)

    @staticmethod
    def sample_random(df: pd.DataFrame, n: Optional[int] = None, frac: Optional[float] = None, seed: int = 42) -> pd.DataFrame:
        """Returns N random rows or a fraction of rows."""
        return df.sample(n=n, frac=frac, random_state=seed).reset_index(drop=True)

    @classmethod
    def sample_balanced(cls, df: pd.DataFrame, label_col: str, n_per_class: int, seed: int = 42) -> pd.DataFrame:
        """
        Samples exactly n_per_class items for each unique class in label_col.
        If a class has fewer than n_per_class items, we take all of them.
        """
        classes = df[label_col].dropna().unique()
        sampled_dfs = []
        
        for c in classes:
            class_df = df[df[label_col] == c]
            available = len(class_df)
            take = min(available, n_per_class)
            
            if take < n_per_class:
                logger.warning(f"Class '{c}' only has {available} samples. Requested {n_per_class}. Taking all available.")
                
            sampled_dfs.append(class_df.sample(n=take, random_state=seed))
            
        return pd.concat(sampled_dfs).sample(frac=1.0, random_state=seed).reset_index(drop=True)

    @classmethod
    def sample_stratified(cls, df: pd.DataFrame, label_col: str, frac: float, seed: int = 42) -> pd.DataFrame:
        """
        Samples a fraction of the dataset maintaining class distribution.
        Uses train_test_split from scikit-learn.
        """
        from sklearn.model_selection import train_test_split
        
        # Filter rows with null labels first
        clean_df = df.dropna(subset=[label_col])
        if len(clean_df) < 2:
            return clean_df.copy()
            
        try:
            sampled_df, _ = train_test_split(
                clean_df, 
                train_size=frac, 
                stratify=clean_df[label_col], 
                random_state=seed
            )
            return sampled_df.reset_index(drop=True)
        except Exception as e:
            logger.warning(f"Stratification failed: {str(e)}. Falling back to random sampling.")
            return cls.sample_random(df, frac=frac, seed=seed)

    @classmethod
    def sample(cls, df: pd.DataFrame, strategy: str, params: Dict[str, Any], label_col: Optional[str] = None, seed: int = 42) -> pd.DataFrame:
        """
        Main entry point for sampling.
        """
        strategy = strategy.lower().strip()
        if df.empty:
            return df
            
        if strategy == "first_n":
            n = int(params.get("n", 100))
            return cls.sample_first_n(df, n)
            
        elif strategy == "random":
            n = params.get("n")
            frac = params.get("frac")
            if n is not None:
                n = int(n)
                # Cap n to dataframe length
                n = min(n, len(df))
            if frac is not None:
                frac = float(frac)
            return cls.sample_random(df, n=n, frac=frac, seed=seed)
            
        elif strategy == "balanced":
            if not label_col:
                raise ValueError("Label column must be specified for balanced sampling.")
            n_per_class = int(params.get("n_per_class", 10))
            return cls.sample_balanced(df, label_col, n_per_class, seed=seed)
            
        elif strategy == "stratified":
            if not label_col:
                raise ValueError("Label column must be specified for stratified sampling.")
            frac = float(params.get("frac", 0.1))
            return cls.sample_stratified(df, label_col, frac, seed=seed)
            
        else:
            raise ValueError(f"Unknown sampling strategy: {strategy}")
