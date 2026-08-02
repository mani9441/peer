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
        Filters out samples that did not generate successfully.
        """
        statuses = extra_data.get("statuses") if extra_data else None
        
        filtered_preds = []
        filtered_gts = []
        filtered_latencies = []
        filtered_costs = []
        filtered_tokens = []
        
        if statuses:
            latencies = extra_data.get("latencies", [])
            costs = extra_data.get("costs", [])
            tokens = extra_data.get("tokens", [])
            
            for i, status in enumerate(statuses):
                if status == "SUCCESS":
                    if i < len(predictions):
                        filtered_preds.append(predictions[i])
                    if i < len(ground_truths):
                        filtered_gts.append(ground_truths[i])
                    if i < len(latencies):
                        filtered_latencies.append(latencies[i])
                    if i < len(costs):
                        filtered_costs.append(costs[i])
                    if i < len(tokens):
                        filtered_tokens.append(tokens[i])
        else:
            filtered_preds = predictions
            filtered_gts = ground_truths
            filtered_latencies = extra_data.get("latencies", []) if extra_data else []
            filtered_costs = extra_data.get("costs", []) if extra_data else []
            filtered_tokens = extra_data.get("tokens", []) if extra_data else []
            
        filtered_extra = {
            "latencies": filtered_latencies,
            "costs": filtered_costs,
            "tokens": filtered_tokens
        }
        
        if extra_data and "all_runs_predictions" in extra_data:
            filtered_all_runs = []
            for r_preds in extra_data["all_runs_predictions"]:
                filtered_r_preds = []
                for i, status in enumerate(statuses or []):
                    if status == "SUCCESS" and i < len(r_preds):
                        filtered_r_preds.append(r_preds[i])
                filtered_all_runs.append(filtered_r_preds if statuses else r_preds)
            filtered_extra["all_runs_predictions"] = filtered_all_runs
            
        results = {}
        for name, metric in self.metrics.items():
            try:
                results[name] = metric.evaluate(filtered_preds, filtered_gts, filtered_extra)
            except Exception as e:
                # Log error and set to 0.0
                results[name] = 0.0
        return results
