import os
import json
import csv
import zipfile
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.experiments.models import Experiment, ExperimentRun, Response

class ExperimentExporter:
    def __init__(self, export_dir: str = "exports"):
        self.export_dir = export_dir
        os.makedirs(self.export_dir, exist_ok=True)

    def export_experiment(self, db: Session, experiment_id: str, format: str = "json") -> str:
        """
        Exports experiment data to JSON, CSV, or a zip Experiment Package.
        Returns the absolute path to the generated file.
        """
        exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found.")

        format = format.lower().strip()
        
        if format == "json":
            return self._export_to_json(exp)
        elif format == "csv":
            return self._export_to_csv(exp)
        elif format == "package":
            return self._export_to_package(exp)
        else:
            raise ValueError(f"Unsupported export format: {format}. Use 'json', 'csv', or 'package'.")

    def _export_to_json(self, exp: Experiment) -> str:
        data = self._gather_experiment_data(exp)
        filename = f"experiment_{exp.id}.json"
        filepath = os.path.join(self.export_dir, filename)
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
            
        return os.path.abspath(filepath)

    def _export_to_csv(self, exp: Experiment) -> str:
        filename = f"experiment_{exp.id}.csv"
        filepath = os.path.join(self.export_dir, filename)
        
        with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            # Write Header
            writer.writerow([
                "experiment_id", "experiment_name", "run_number", "sample_id", 
                "provider", "model", "status", "error_type", "error_message", 
                "latency", "prediction", "reference", "validator_score",
                "prompt", "response", "input_tokens", "output_tokens", "cost_usd", "finish_reason"
            ])
            
            for run in exp.runs:
                for resp in run.responses:
                    pred = resp.prediction if resp.status == "SUCCESS" else None
                    score = resp.is_correct if resp.status == "SUCCESS" else None
                    writer.writerow([
                        exp.id, exp.name, run.run_number, resp.sample_index,
                        resp.provider or exp.provider, resp.model or exp.model, resp.status or "SUCCESS",
                        resp.error_type, resp.error_message, resp.latency,
                        pred, resp.ground_truth, score,
                        resp.prompt, resp.response, resp.input_tokens, resp.output_tokens, resp.cost,
                        resp.finish_reason
                    ])
                    
        return os.path.abspath(filepath)

    def _export_to_package(self, exp: Experiment) -> str:
        """
        Generates a Zip package containing both JSON configuration and CSV logs.
        """
        json_path = self._export_to_json(exp)
        csv_path = self._export_to_csv(exp)
        
        zip_filename = f"experiment_package_{exp.id}.zip"
        zip_filepath = os.path.join(self.export_dir, zip_filename)
        
        with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(json_path, arcname=os.path.basename(json_path))
            zipf.write(csv_path, arcname=os.path.basename(csv_path))
            
        # Clean up temporary JSON/CSV files generated for the zip
        try:
            os.remove(json_path)
            os.remove(csv_path)
        except Exception:
            pass
            
        return os.path.abspath(zip_filepath)

    def _gather_experiment_data(self, exp: Experiment) -> Dict[str, Any]:
        """Gathers complete hierarchical data representation of an experiment."""
        runs_list = []
        
        for run in exp.runs:
            m_dict = {}
            if run.metrics:
                m_dict = {
                    "accuracy": run.metrics.accuracy,
                    "precision": run.metrics.precision,
                    "recall": run.metrics.recall,
                    "f1": run.metrics.f1,
                    "latency": run.metrics.latency,
                    "cost": run.metrics.cost,
                    "consistency": run.metrics.consistency
                }
                
            meta_dict = {}
            if run.metadata_rel:
                meta_dict = {
                    "temperature": run.metadata_rel.temperature,
                    "top_p": run.metadata_rel.top_p,
                    "seed": run.metadata_rel.seed,
                    "prompt_length": run.metadata_rel.prompt_length,
                    "fewshot_count": run.metadata_rel.fewshot_count,
                    "selection_strategy": run.metadata_rel.selection_strategy,
                    "ordering_strategy": run.metadata_rel.ordering_strategy
                }
                
            responses_list = []
            for resp in run.responses:
                pred = resp.prediction if resp.status == "SUCCESS" else None
                score = resp.is_correct if resp.status == "SUCCESS" else None
                responses_list.append({
                    "sample_id": resp.sample_index,
                    "provider": resp.provider or exp.provider,
                    "model": resp.model or exp.model,
                    "status": resp.status or "SUCCESS",
                    "error_type": resp.error_type,
                    "error_message": resp.error_message,
                    "latency": resp.latency,
                    "prediction": pred,
                    "reference": resp.ground_truth,
                    "validator_score": score,
                    "prompt": resp.prompt,
                    "response": resp.response,
                    "input_tokens": resp.input_tokens,
                    "output_tokens": resp.output_tokens,
                    "cost": resp.cost,
                    "finish_reason": resp.finish_reason
                })
                
            runs_list.append({
                "run_id": run.id,
                "run_number": run.run_number,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "metadata": meta_dict,
                "metrics": m_dict,
                "responses": responses_list
            })

        return {
            "experiment_id": exp.id,
            "name": exp.name,
            "description": exp.description,
            "dataset_id": exp.dataset_id,
            "template_id": exp.template_id,
            "strategy_id": exp.strategy_id,
            "provider": exp.provider,
            "model": exp.model,
            "created_at": exp.created_at.isoformat() if exp.created_at else None,
            "runs": runs_list
        }
