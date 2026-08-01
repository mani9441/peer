from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from backend.experiments.models import Experiment, ExperimentRun, Response, Metric, Metadata
import datetime

class ExperimentRepository:
    @staticmethod
    def create_experiment(
        db: Session,
        experiment_id: str,
        name: str,
        description: Optional[str],
        dataset_id: str,
        template_id: Optional[str],
        strategy_id: str,
        provider: str,
        model: str
    ) -> Experiment:
        exp = Experiment(
            id=experiment_id,
            name=name,
            description=description,
            dataset_id=dataset_id,
            template_id=template_id,
            strategy_id=strategy_id,
            provider=provider,
            model=model
        )
        db.add(exp)
        db.commit()
        db.refresh(exp)
        return exp

    @staticmethod
    def get_experiment(db: Session, experiment_id: str) -> Optional[Experiment]:
        return db.query(Experiment).filter(Experiment.id == experiment_id).first()

    @staticmethod
    def list_experiments(db: Session) -> List[Experiment]:
        return db.query(Experiment).order_by(Experiment.created_at.desc()).all()

    @staticmethod
    def delete_experiment(db: Session, experiment_id: str) -> bool:
        exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        if exp:
            db.delete(exp)
            db.commit()
            return True
        return False

    @staticmethod
    def create_run(
        db: Session,
        run_id: str,
        experiment_id: str,
        run_number: int,
        status: str = "Created"
    ) -> ExperimentRun:
        run = ExperimentRun(
            id=run_id,
            experiment_id=experiment_id,
            run_number=run_number,
            status=status,
            started_at=datetime.datetime.utcnow()
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def get_run(db: Session, run_id: str) -> Optional[ExperimentRun]:
        return db.query(ExperimentRun).filter(ExperimentRun.id == run_id).first()

    @staticmethod
    def get_runs_for_experiment(db: Session, experiment_id: str) -> List[ExperimentRun]:
        return db.query(ExperimentRun).filter(ExperimentRun.experiment_id == experiment_id).order_by(ExperimentRun.run_number.asc()).all()

    @staticmethod
    def update_run_status(db: Session, run_id: str, status: str) -> Optional[ExperimentRun]:
        run = db.query(ExperimentRun).filter(ExperimentRun.id == run_id).first()
        if run:
            run.status = status
            if status in ("Completed", "Failed", "Cancelled"):
                run.finished_at = datetime.datetime.utcnow()
            db.commit()
            db.refresh(run)
        return run

    @staticmethod
    def save_response(
        db: Session,
        run_id: str,
        sample_index: int,
        prompt: str,
        response_text: str,
        latency: float,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        finish_reason: Optional[str],
        ground_truth: Optional[str],
        prediction: Optional[str],
        is_correct: Optional[bool]
    ) -> Response:
        resp = Response(
            run_id=run_id,
            sample_index=sample_index,
            prompt=prompt,
            response=response_text,
            latency=latency,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            finish_reason=finish_reason,
            ground_truth=ground_truth,
            prediction=prediction,
            is_correct=is_correct
        )
        db.add(resp)
        db.commit()
        db.refresh(resp)
        return resp

    @staticmethod
    def save_metrics(
        db: Session,
        run_id: str,
        accuracy: float,
        precision: float,
        recall: float,
        f1: float,
        latency: float,
        cost: float,
        consistency: float
    ) -> Metric:
        # Delete existing metric record for this run if any
        db.query(Metric).filter(Metric.run_id == run_id).delete()
        
        metric = Metric(
            run_id=run_id,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            latency=latency,
            cost=cost,
            consistency=consistency
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return metric

    @staticmethod
    def save_metadata(
        db: Session,
        run_id: str,
        temperature: Optional[float],
        top_p: Optional[float],
        seed: Optional[int],
        prompt_length: Optional[str],
        fewshot_count: Optional[int],
        selection_strategy: Optional[str],
        ordering_strategy: Optional[str]
    ) -> Metadata:
        db.query(Metadata).filter(Metadata.run_id == run_id).delete()
        
        meta = Metadata(
            run_id=run_id,
            temperature=temperature,
            top_p=top_p,
            seed=seed,
            prompt_length=prompt_length,
            fewshot_count=fewshot_count,
            selection_strategy=selection_strategy,
            ordering_strategy=ordering_strategy
        )
        db.add(meta)
        db.commit()
        db.refresh(meta)
        return meta
