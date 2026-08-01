from abc import ABC, abstractmethod
from typing import List, Any, Optional, Dict
import numpy as np

class BaseMetric(ABC):
    @abstractmethod
    def evaluate(self, predictions: List[Any], ground_truths: List[Any], extra_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Computes metric score based on predictions and ground truths.
        """
        pass

class AccuracyMetric(BaseMetric):
    def evaluate(self, predictions: List[Any], ground_truths: List[Any], extra_data: Optional[Dict[str, Any]] = None) -> float:
        if not predictions or not ground_truths or len(predictions) != len(ground_truths):
            return 0.0
        try:
            from sklearn.metrics import accuracy_score
            return float(accuracy_score(ground_truths, predictions))
        except ImportError:
            correct = sum(1 for p, g in zip(predictions, ground_truths) if str(p).strip().lower() == str(g).strip().lower())
            return float(correct / len(predictions))

class PrecisionMetric(BaseMetric):
    def evaluate(self, predictions: List[Any], ground_truths: List[Any], extra_data: Optional[Dict[str, Any]] = None) -> float:
        if not predictions or not ground_truths or len(predictions) != len(ground_truths):
            return 0.0
        try:
            from sklearn.metrics import precision_score
            # Using macro average for multi-class classification
            return float(precision_score(ground_truths, predictions, average='macro', zero_division=0))
        except Exception:
            return 0.0

class RecallMetric(BaseMetric):
    def evaluate(self, predictions: List[Any], ground_truths: List[Any], extra_data: Optional[Dict[str, Any]] = None) -> float:
        if not predictions or not ground_truths or len(predictions) != len(ground_truths):
            return 0.0
        try:
            from sklearn.metrics import recall_score
            return float(recall_score(ground_truths, predictions, average='macro', zero_division=0))
        except Exception:
            return 0.0

class F1Metric(BaseMetric):
    def evaluate(self, predictions: List[Any], ground_truths: List[Any], extra_data: Optional[Dict[str, Any]] = None) -> float:
        if not predictions or not ground_truths or len(predictions) != len(ground_truths):
            return 0.0
        try:
            from sklearn.metrics import f1_score
            return float(f1_score(ground_truths, predictions, average='macro', zero_division=0))
        except Exception:
            return 0.0

class LatencyMetric(BaseMetric):
    def evaluate(self, predictions: List[Any], ground_truths: List[Any], extra_data: Optional[Dict[str, Any]] = None) -> float:
        # Expects latencies in extra_data
        if not extra_data or "latencies" not in extra_data:
            return 0.0
        latencies = extra_data["latencies"]
        if not latencies:
            return 0.0
        return float(np.mean(latencies))

class CostMetric(BaseMetric):
    def evaluate(self, predictions: List[Any], ground_truths: List[Any], extra_data: Optional[Dict[str, Any]] = None) -> float:
        # Expects costs in extra_data
        if not extra_data or "costs" not in extra_data:
            return 0.0
        costs = extra_data["costs"]
        if not costs:
            return 0.0
        return float(np.sum(costs))

class TokenUsageMetric(BaseMetric):
    def evaluate(self, predictions: List[Any], ground_truths: List[Any], extra_data: Optional[Dict[str, Any]] = None) -> float:
        if not extra_data or "tokens" not in extra_data:
            return 0.0
        tokens = extra_data["tokens"]
        if not tokens:
            return 0.0
        return float(np.sum(tokens))

class ConsistencyMetric(BaseMetric):
    def evaluate(self, predictions: List[Any], ground_truths: List[Any], extra_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Computes the consistency of prediction strings across repeated runs.
        """
        if not extra_data or "all_runs_predictions" not in extra_data:
            return 1.0
            
        all_runs_predictions = extra_data["all_runs_predictions"]
        if not all_runs_predictions or len(all_runs_predictions) <= 1:
            return 1.0
            
        num_samples = len(predictions)
        if num_samples == 0:
            return 0.0
            
        consistency_sum = 0.0
        for idx in range(num_samples):
            sample_preds = []
            for r_preds in all_runs_predictions:
                if idx < len(r_preds):
                    sample_preds.append(str(r_preds[idx]).strip().lower())
            
            if not sample_preds:
                continue
                
            from collections import Counter
            counts = Counter(sample_preds)
            mode_count = counts.most_common(1)[0][1]
            consistency_sum += mode_count / len(sample_preds)
            
        return float(consistency_sum / num_samples)
