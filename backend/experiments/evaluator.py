import re
from typing import List, Any, Optional, Dict
from backend.experiments.metrics import (
    AccuracyMetric,
    PrecisionMetric,
    RecallMetric,
    F1Metric,
    LatencyMetric,
    CostMetric,
    TokenUsageMetric,
    ConsistencyMetric
)

from backend.experiments.interpretation import PredictionInterpretationEngine

class ResponseProcessor:
    @staticmethod
    def normalize_response(
        response_text: str,
        task_type: str,
        target_labels: Optional[List[str]] = None,
        label_mapping: Optional[Dict[Any, str]] = None
    ) -> str:
        """
        Extracts and normalizes raw model completion text into standard predictions.
        Delegates interpretation logic to the PredictionInterpretationEngine.
        """
        return PredictionInterpretationEngine.interpret(
            response_text=response_text,
            task_type=task_type,
            target_labels=target_labels,
            label_mapping=label_mapping
        )


class EvaluationManager:
    def __init__(self):
        self.metrics = {
            "accuracy": AccuracyMetric(),
            "precision": PrecisionMetric(),
            "recall": RecallMetric(),
            "f1": F1Metric(),
            "latency": LatencyMetric(),
            "cost": CostMetric(),
            "token_usage": TokenUsageMetric(),
            "consistency": ConsistencyMetric()
        }

    def evaluate_run(
        self,
        predictions: List[Any],
        ground_truths: List[Any],
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Orchestrates evaluation by running the list of registered metrics.
        """
        results = {}
        for name, metric in self.metrics.items():
            try:
                results[name] = metric.evaluate(predictions, ground_truths, extra_data)
            except Exception as e:
                # Log error and set to 0.0
                results[name] = 0.0
        return results
