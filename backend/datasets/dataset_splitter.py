import pandas as pd
from typing import Dict, Optional
import logging
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

class DatasetSplitter:
    """
    Splits a single DataFrame into train, validation, and test subsets.
    """
    
    @classmethod
    def split(
        cls, 
        df: pd.DataFrame, 
        val_ratio: float, 
        test_ratio: float, 
        label_col: Optional[str] = None, 
        seed: int = 42, 
        stratify: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Splits a DataFrame into train, validation, and test sets.
        If val_ratio is 0.0, the validation split is not created.
        If test_ratio is 0.0, the test split is not created.
        """
        if df.empty:
            return {}
            
        train_ratio = 1.0 - val_ratio - test_ratio
        if train_ratio <= 0.0:
            raise ValueError(f"Sum of val_ratio ({val_ratio}) and test_ratio ({test_ratio}) must be less than 1.0.")
            
        # Target stratification column
        stratify_col = None
        if stratify and label_col:
            # Check if we can stratify
            if label_col in df.columns:
                counts = df[label_col].dropna().value_counts()
                # Needs at least 2 classes and all classes must have >= 2 items
                if len(counts) >= 2 and (counts >= 2).all():
                    stratify_col = df[label_col]
                else:
                    logger.warning("Stratification requested but not possible (classes have too few samples). Falling back to random splitting.")
            else:
                logger.warning(f"Label column '{label_col}' not found. Falling back to random splitting.")
                
        # We split in two steps:
        # Step 1: Split off the test set (if test_ratio > 0)
        temp_df = df.copy()
        test_df = pd.DataFrame()
        val_df = pd.DataFrame()
        
        if test_ratio > 0.0:
            strat_temp = temp_df[label_col] if (stratify_col is not None and label_col in temp_df.columns) else None
            try:
                temp_df, test_df = train_test_split(
                    temp_df,
                    test_size=test_ratio,
                    random_state=seed,
                    stratify=strat_temp
                )
            except ValueError as e:
                logger.warning(f"Stratified test split failed: {str(e)}. Retrying without stratification.")
                temp_df, test_df = train_test_split(
                    temp_df,
                    test_size=test_ratio,
                    random_state=seed,
                    stratify=None
                )
            
        # Step 2: Split off validation set from the remaining temp_df (if val_ratio > 0)
        if val_ratio > 0.0:
            # Re-scale val_ratio since the test set has already been removed
            val_ratio_scaled = val_ratio / (val_ratio + train_ratio)
            
            # Bound scaled ratio in case of float precision issues
            val_ratio_scaled = min(0.99, max(0.01, val_ratio_scaled))
            
            strat_temp = temp_df[label_col] if (stratify_col is not None and label_col in temp_df.columns) else None
            
            # Check if stratify classes are still valid in remaining data
            if strat_temp is not None:
                counts = strat_temp.dropna().value_counts()
                if len(counts) < 2 or not (counts >= 2).all():
                    strat_temp = None
                    
            try:
                train_df, val_df = train_test_split(
                    temp_df,
                    test_size=val_ratio_scaled,
                    random_state=seed,
                    stratify=strat_temp
                )
            except ValueError as e:
                logger.warning(f"Stratified validation split failed: {str(e)}. Retrying without stratification.")
                train_df, val_df = train_test_split(
                    temp_df,
                    test_size=val_ratio_scaled,
                    random_state=seed,
                    stratify=None
                )
        else:
            train_df = temp_df
            
        splits = {"train": train_df.reset_index(drop=True)}
        if not val_df.empty:
            splits["validation"] = val_df.reset_index(drop=True)
        if not test_df.empty:
            splits["test"] = test_df.reset_index(drop=True)
            
        return splits
