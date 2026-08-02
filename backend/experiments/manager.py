from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from backend.experiments.models import Experiment, ExperimentRun
from backend.experiments.repository import ExperimentRepository
from backend.experiments.executor import ExperimentExecutor
from backend.experiments.validators import ExperimentValidator
from backend.experiments.utils import generate_uuid
from backend.experiments.history import RunHistoryManager
from backend.experiments.exporter import ExperimentExporter

class ExperimentManager:
    def __init__(self, export_dir: str = "exports"):
        self.executor = ExperimentExecutor()
        self.history = RunHistoryManager()
        self.exporter = ExperimentExporter(export_dir=export_dir)

    def create_experiment(
        self,
        db: Session,
        name: str,
        description: Optional[str],
        dataset_id: str,
        template_id: Optional[str],
        strategy_id: str,
        provider: str,
        model: str
    ) -> Experiment:
        """
        Creates and registers a new experiment configuration after validation.
        """
        # Validate configuration assets
        ExperimentValidator.validate_config(
            db=db,
            dataset_id=dataset_id,
            template_id=template_id,
            strategy_id=strategy_id,
            provider=provider,
            model=model
        )
        
        # Create ID
        experiment_id = generate_uuid("exp")
        
        return ExperimentRepository.create_experiment(
            db=db,
            experiment_id=experiment_id,
            name=name,
            description=description,
            dataset_id=dataset_id,
            template_id=template_id,
            strategy_id=strategy_id,
            provider=provider,
            model=model
        )

    def run_experiment(
        self,
        db: Session,
        experiment_id: str,
        runs: int,
        max_samples: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        seed: Optional[int] = None
    ) -> List[str]:
        """Runs the complete multi-run experiment in the background."""
        return self.executor.run_experiment(
            db=db,
            experiment_id=experiment_id,
            runs_count=runs,
            max_samples=max_samples,
            temperature=temperature,
            top_p=top_p,
            seed=seed
        )

    def run_single(
        self,
        db: Session,
        experiment_id: str,
        run_number: int,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        seed: Optional[int] = None,
        max_samples: Optional[int] = None
    ) -> ExperimentRun:
        """Runs a single run of the experiment synchronously."""
        return self.executor.run_single(
            db=db,
            experiment_id=experiment_id,
            run_number=run_number,
            temperature=temperature,
            top_p=top_p,
            seed=seed,
            max_samples=max_samples
        )

    def cancel_experiment(self, db: Session, experiment_id: str) -> None:
        """Cancels all active runs for the experiment."""
        self.executor.cancel_experiment(db, experiment_id)

    def resume_experiment(self, db: Session, experiment_id: str, max_samples: Optional[int] = None) -> List[str]:
        """Resumes failed or cancelled runs for the experiment in the background."""
        return self.executor.resume_experiment(db, experiment_id, max_samples=max_samples)

    def get_experiment(self, db: Session, experiment_id: str) -> Optional[Experiment]:
        """Retrieves experiment configuration by ID."""
        return ExperimentRepository.get_experiment(db, experiment_id)

    def list_experiments(self, db: Session) -> List[Experiment]:
        """Lists all experiments in reverse chronological order."""
        return ExperimentRepository.list_experiments(db)

    def delete_experiment(self, db: Session, experiment_id: str) -> bool:
        """Deletes experiment and all its runs, metrics, and responses."""
        return ExperimentRepository.delete_experiment(db, experiment_id)

    def evaluate_run(self, db: Session, run_id: str) -> Dict[str, float]:
        """
        Manually triggers evaluation on existing run responses.
        """
        run = ExperimentRepository.get_run(db, run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found.")
            
        predictions = [resp.prediction for resp in sorted(run.responses, key=lambda x: x.sample_index)]
        ground_truths = [resp.ground_truth for resp in sorted(run.responses, key=lambda x: x.sample_index)]
        
        extra_data = {
            "latencies": [resp.latency for resp in sorted(run.responses, key=lambda x: x.sample_index)],
            "costs": [resp.cost for resp in sorted(run.responses, key=lambda x: x.sample_index)],
            "tokens": [resp.input_tokens + resp.output_tokens for resp in sorted(run.responses, key=lambda x: x.sample_index)],
            "statuses": [resp.status or "SUCCESS" for resp in sorted(run.responses, key=lambda x: x.sample_index)]
        }
        
        # Add all runs' predictions for consistency calculation
        all_runs = db.query(ExperimentRun).filter(
            ExperimentRun.experiment_id == run.experiment_id,
            ExperimentRun.status == "Completed"
        ).all()
        
        all_runs_predictions = []
        for r in all_runs:
            r_preds = [resp.prediction for resp in sorted(r.responses, key=lambda x: x.sample_index)]
            if len(r_preds) == len(predictions):
                all_runs_predictions.append(r_preds)
                
        extra_data["all_runs_predictions"] = all_runs_predictions
        
        results = self.executor.pipeline.evaluation_manager.evaluate_run(predictions, ground_truths, extra_data)
        
        # Save updated metrics
        ExperimentRepository.save_metrics(
            db=db,
            run_id=run_id,
            accuracy=results.get("accuracy", 0.0),
            precision=results.get("precision", 0.0),
            recall=results.get("recall", 0.0),
            f1=results.get("f1", 0.0),
            latency=results.get("latency", 0.0),
            cost=results.get("cost", 0.0),
            consistency=results.get("consistency", 1.0)
        )
        return results

    def retry_failed_samples(self, db: Session, run_id: str) -> None:
        """Manually triggers retries for failed samples in a run."""
        self.executor.pipeline.retry_failed_samples(db, run_id)

    def export_results(self, db: Session, experiment_id: str, format: str = "json") -> str:
        """Exports experiment results and metrics to a local file."""
        return self.exporter.export_experiment(db, experiment_id, format)

    def load_history(self, db: Session, experiment_id: str) -> Dict[str, Any]:
        """Loads and formats the run history for an experiment."""
        return self.history.load_experiment_history(db, experiment_id)

    def compare_experiments(self, db: Session, experiment_ids: List[str]) -> Dict[str, Any]:
        """Compares multiple experiments and returns comparative metrics."""
        return self.history.compare_runs(db, experiment_ids)
