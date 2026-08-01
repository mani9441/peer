from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import numpy as np
from backend.experiments.models import Experiment, ExperimentRun

class RunHistoryManager:
    @staticmethod
    def load_experiment_history(db: Session, experiment_id: str) -> Dict[str, Any]:
        """
        Loads the runs for an experiment and calculates summary stats (Mean, Variance, Consistency).
        """
        exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found.")

        completed_runs = [r for r in exp.runs if r.status == "Completed" and r.metrics]
        
        runs_data = []
        accuracies = []
        latencies = []
        costs = []
        consistencies = []

        for run in exp.runs:
            m = run.metrics
            metrics_dict = {}
            if m:
                metrics_dict = {
                    "accuracy": m.accuracy,
                    "precision": m.precision,
                    "recall": m.recall,
                    "f1": m.f1,
                    "latency": m.latency,
                    "cost": m.cost,
                    "consistency": m.consistency
                }
                
                if run.status == "Completed":
                    if m.accuracy is not None: accuracies.append(m.accuracy)
                    if m.latency is not None: latencies.append(m.latency)
                    if m.cost is not None: costs.append(m.cost)
                    if m.consistency is not None: consistencies.append(m.consistency)

            runs_data.append({
                "run_id": run.id,
                "run_number": run.run_number,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "metrics": metrics_dict
            })

        # Calculate Mean and Variance
        summary = {
            "completed_runs_count": len(completed_runs),
            "total_runs_count": len(exp.runs),
            "accuracy_mean": float(np.mean(accuracies)) if accuracies else 0.0,
            "accuracy_variance": float(np.var(accuracies)) if accuracies else 0.0,
            "latency_mean": float(np.mean(latencies)) if latencies else 0.0,
            "latency_variance": float(np.var(latencies)) if latencies else 0.0,
            "cost_mean": float(np.mean(costs)) if costs else 0.0,
            "cost_variance": float(np.var(costs)) if costs else 0.0,
            "consistency_avg": float(np.mean(consistencies)) if consistencies else 1.0
        }

        return {
            "experiment_id": exp.id,
            "name": exp.name,
            "description": exp.description,
            "dataset_id": exp.dataset_id,
            "provider": exp.provider,
            "model": exp.model,
            "runs": runs_data,
            "summary": summary
        }

    @classmethod
    def compare_runs(cls, db: Session, experiment_ids: List[str]) -> Dict[str, Any]:
        """
        Compares multiple experiments.
        """
        comparisons = {}
        for exp_id in experiment_ids:
            try:
                hist = cls.load_experiment_history(db, exp_id)
                comparisons[exp_id] = {
                    "name": hist["name"],
                    "provider": hist["provider"],
                    "model": hist["model"],
                    "dataset_id": hist["dataset_id"],
                    "accuracy_mean": hist["summary"]["accuracy_mean"],
                    "latency_mean": hist["summary"]["latency_mean"],
                    "cost_mean": hist["summary"]["cost_mean"],
                    "consistency_avg": hist["summary"]["consistency_avg"],
                    "completed_runs": hist["summary"]["completed_runs_count"]
                }
            except Exception as e:
                comparisons[exp_id] = {"error": str(e)}
        return comparisons
