import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import json

class DatasetStatistics:
    """
    Computes summary metrics and charts data for datasets of type classification or QA.
    """
    
    @staticmethod
    def calculate_entropy(probabilities: np.ndarray) -> float:
        """Computes Shannon entropy."""
        probabilities = probabilities[probabilities > 0]
        return float(-np.sum(probabilities * np.log2(probabilities)))

    @classmethod
    def compute(cls, df: pd.DataFrame, task_type: str, mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Compute statistics for a given DataFrame based on its task type and column mapping.
        """
        stats = {
            "total_samples": len(df),
            "class_distribution": None,
            "avg_length": 0.0,
            "min_length": 0,
            "max_length": 0,
            "imbalance_score": 1.0,
            "metadata_json": {}
        }
        
        if df.empty:
            return stats

        if task_type == "classification":
            text_col = mapping["text"]
            label_col = mapping["label"]
            
            # Text lengths (characters)
            lengths = df[text_col].dropna().astype(str).str.len()
            if not lengths.empty:
                stats["avg_length"] = float(lengths.mean())
                stats["min_length"] = int(lengths.min())
                stats["max_length"] = int(lengths.max())
                
                # Word count approximations
                word_counts = df[text_col].dropna().astype(str).str.split().str.len()
                stats["metadata_json"]["avg_word_count"] = float(word_counts.mean())
                stats["metadata_json"]["min_word_count"] = int(word_counts.min())
                stats["metadata_json"]["max_word_count"] = int(word_counts.max())
                
            # Class distribution
            class_counts = df[label_col].dropna().value_counts()
            dist = {str(k): int(v) for k, v in class_counts.items()}
            stats["class_distribution"] = json.dumps(dist)
            
            # Imbalance Score (Normalized Shannon Entropy)
            num_classes = len(class_counts)
            if num_classes > 1:
                counts = class_counts.values
                probs = counts / counts.sum()
                entropy = cls.calculate_entropy(probs)
                max_entropy = np.log2(num_classes)
                # Normalized between 0 and 1
                stats["imbalance_score"] = float(entropy / max_entropy)
            else:
                stats["imbalance_score"] = 0.0
                
        elif task_type == "qa":
            context_col = mapping["context"]
            question_col = mapping["question"]
            answers_col = mapping["answers"]
            
            # Context length stats
            context_lens = df[context_col].dropna().astype(str).str.len()
            if not context_lens.empty:
                stats["avg_length"] = float(context_lens.mean())
                stats["min_length"] = int(context_lens.min())
                stats["max_length"] = int(context_lens.max())
                
                stats["metadata_json"]["context"] = {
                    "avg_char_len": float(context_lens.mean()),
                    "min_char_len": int(context_lens.min()),
                    "max_char_len": int(context_lens.max())
                }
                
            # Question length stats
            question_lens = df[question_col].dropna().astype(str).str.len()
            if not question_lens.empty:
                stats["metadata_json"]["question"] = {
                    "avg_char_len": float(question_lens.mean()),
                    "min_char_len": int(question_lens.min()),
                    "max_char_len": int(question_lens.max())
                }
                
            # Answer length stats helper
            def extract_answer_text(ans) -> str:
                if isinstance(ans, dict):
                    # SQuAD style dict
                    texts = ans.get("text", [])
                    if isinstance(texts, list) and len(texts) > 0:
                        return str(texts[0])
                    elif isinstance(texts, str):
                        return texts
                elif isinstance(ans, (list, tuple)):
                    if len(ans) > 0:
                        return str(ans[0])
                elif pd.isna(ans):
                    return ""
                return str(ans)

            answers_series = df[answers_col].apply(extract_answer_text)
            answer_lens = answers_series.str.len()
            if not answer_lens.empty:
                stats["metadata_json"]["answer"] = {
                    "avg_char_len": float(answer_lens.mean()),
                    "min_char_len": int(answer_lens.min()),
                    "max_char_len": int(answer_lens.max())
                }
                
            stats["imbalance_score"] = 1.0  # QA task doesn't have class imbalance in the same way
            stats["class_distribution"] = json.dumps({"n_questions": len(df)})
            
        stats["metadata_json"] = json.dumps(stats["metadata_json"])
        return stats
