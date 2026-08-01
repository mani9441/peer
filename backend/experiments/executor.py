import threading
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.experiments.models import ExperimentRun
from backend.experiments.repository import ExperimentRepository
from backend.experiments.pipeline import ExecutionPipeline
from backend.experiments.utils import generate_uuid

logger = logging.getLogger(__name__)

# Global registry to track running experiment threads
ACTIVE_THREADS: Dict[str, threading.Thread] = {}

class ExperimentExecutor:
    def __init__(self):
        self.pipeline = ExecutionPipeline()

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
        """
        Executes a single experiment run synchronously (blocking).
        """
        # Create unique run ID
        run_id = generate_uuid("run")
        
        # Create Run database record
        run = ExperimentRepository.create_run(
            db=db,
            run_id=run_id,
            experiment_id=experiment_id,
            run_number=run_number,
            status="Created"
        )
        
        # Extract metadata settings from experiment / strategy defaults
        strategy = run.experiment.strategy_id
        # Save run Metadata settings
        # We can extract defaults or use custom values
        ExperimentRepository.save_metadata(
            db=db,
            run_id=run_id,
            temperature=temperature,
            top_p=top_p,
            seed=seed,
            prompt_length=None,
            fewshot_count=None,
            selection_strategy=None,
            ordering_strategy=None
        )
        
        # Execute the pipeline
        self.pipeline.execute_run(db, run_id, max_samples=max_samples)
        db.refresh(run)
        return run

    def run_experiment(
        self,
        db: Session,
        experiment_id: str,
        runs_count: int,
        max_samples: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        seed: Optional[int] = None
    ) -> List[str]:
        """
        Executes multiple experiment runs sequentially in a background thread.
        Returns a list of created run IDs.
        """
        run_ids = []
        
        for r_num in range(1, runs_count + 1):
            run_id = generate_uuid("run")
            run_ids.append(run_id)
            
            # Create Run record
            ExperimentRepository.create_run(
                db=db,
                run_id=run_id,
                experiment_id=experiment_id,
                run_number=r_num,
                status="Queued"
            )
            
            # Save parameters
            ExperimentRepository.save_metadata(
                db=db,
                run_id=run_id,
                temperature=temperature,
                top_p=top_p,
                seed=seed,
                prompt_length=None,
                fewshot_count=None,
                selection_strategy=None,
                ordering_strategy=None
            )

        # Spawn execution in background thread
        thread = threading.Thread(
            target=self._background_executor_target,
            args=(run_ids, max_samples),
            daemon=True
        )
        thread.start()
        
        # Register thread
        for rid in run_ids:
            ACTIVE_THREADS[rid] = thread
            
        return run_ids

    def cancel_experiment(self, db: Session, experiment_id: str) -> None:
        """
        Cancels all active runs for the specified experiment.
        """
        active_runs = db.query(ExperimentRun).filter(
            ExperimentRun.experiment_id == experiment_id,
            ExperimentRun.status.in_(["Queued", "Running"])
        ).all()
        
        for run in active_runs:
            ExperimentRepository.update_run_status(db, run.id, "Cancelled")
            
    def resume_experiment(self, db: Session, experiment_id: str, max_samples: Optional[int] = None) -> List[str]:
        """
        Resumes executions for any runs that are in "Failed" or "Cancelled" state.
        """
        failed_runs = db.query(ExperimentRun).filter(
            ExperimentRun.experiment_id == experiment_id,
            ExperimentRun.status.in_(["Failed", "Cancelled"])
        ).all()
        
        run_ids = []
        for run in failed_runs:
            run_ids.append(run.id)
            ExperimentRepository.update_run_status(db, run.id, "Queued")
            
        if run_ids:
            thread = threading.Thread(
                target=self._background_executor_target,
                args=(run_ids, max_samples),
                daemon=True
            )
            thread.start()
            for rid in run_ids:
                ACTIVE_THREADS[rid] = thread
                
        return run_ids

    def _background_executor_target(self, run_ids: List[str], max_samples: Optional[int]) -> None:
        """
        Target function executed inside the background thread.
        """
        for rid in run_ids:
            db_thread = SessionLocal()
            try:
                run = ExperimentRepository.get_run(db_thread, rid)
                if not run:
                    continue
                    
                # If it was cancelled while in queue, skip it
                if run.status == "Cancelled":
                    continue
                    
                # Execute pipeline for this run
                self.pipeline.execute_run(db_thread, rid, max_samples=max_samples)
                
            except Exception as e:
                logger.error(f"Background thread execution failed on run {rid}: {e}")
            finally:
                db_thread.close()
                if rid in ACTIVE_THREADS:
                    ACTIVE_THREADS.pop(rid, None)
