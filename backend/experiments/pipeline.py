import logging
import datetime
import time
import pandas as pd
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from backend.experiments.models import ExperimentRun, Experiment
from backend.experiments.repository import ExperimentRepository
from backend.experiments.evaluator import ResponseProcessor, EvaluationManager
from backend.experiments.utils import generate_uuid
from backend.datasets.dataset_manager import DatasetManager
from backend.datasets.dataset_validator import DatasetValidator
from backend.prompts.prompt_manager import PromptManager
from backend.fewshot.builder import FewShotBuilder
from backend.providers import ProviderService, LLMRequest, GenerationConfig
from backend.strategies.models import PromptStrategy

logger = logging.getLogger(__name__)

def map_exception_to_status(e: Exception) -> str:
    from backend.providers.exceptions import (
        AuthenticationError,
        InvalidModelError,
        NetworkError,
        TimeoutError,
        ProviderUnavailableError
    )
    if isinstance(e, AuthenticationError):
        return "AUTH_ERROR"
    if isinstance(e, InvalidModelError):
        return "INVALID_MODEL"
    if isinstance(e, TimeoutError):
        return "TIMEOUT"
    if isinstance(e, NetworkError):
        return "NETWORK_ERROR"
    if isinstance(e, ProviderUnavailableError):
        msg = str(e).lower()
        if "429" in msg or "quota" in msg or "rate limit" in msg or "resource" in msg:
            return "RATE_LIMITED"
        return "FAILED"
    
    msg = str(e).lower()
    if "api key" in msg or "auth" in msg or "unauthorized" in msg or "401" in msg or "403" in msg:
        return "AUTH_ERROR"
    if "404" in msg or "model not found" in msg or "invalid model" in msg:
        return "INVALID_MODEL"
    if "429" in msg or "quota" in msg or "rate limit" in msg or "resourceexhausted" in msg:
        return "RATE_LIMITED"
    if "timeout" in msg or "deadline" in msg or "408" in msg:
        return "TIMEOUT"
    if "connection" in msg or "network" in msg or "ssl" in msg:
        return "NETWORK_ERROR"
    return "FAILED"

def check_can_retry(status: str) -> bool:
    return status in ("TIMEOUT", "NETWORK_ERROR")

class ExecutionPipeline:
    def __init__(self):
        self.dataset_manager = DatasetManager()
        self.prompt_manager = PromptManager()
        self.fewshot_builder = FewShotBuilder()
        self.provider_service = ProviderService()
        self.evaluation_manager = EvaluationManager()

    def execute_run(self, db: Session, run_id: str, max_samples: Optional[int] = None) -> None:
        """
        Executes a complete experiment run sample-by-sample, evaluating and persisting results.
        """
        # Load run and experiment details
        run = ExperimentRepository.get_run(db, run_id)
        if not run:
            raise ValueError(f"Experiment run with ID '{run_id}' not found.")
            
        experiment = run.experiment
        if not experiment:
            raise ValueError(f"No experiment associated with run ID '{run_id}'.")
            
        # Update status to Running
        ExperimentRepository.update_run_status(db, run_id, "Running")
        
        # Load run metadata
        metadata = run.metadata_rel
        if not metadata:
            raise ValueError(f"No metadata found for run ID '{run_id}'.")
            
        try:
            # 1. Fetch Dataset & Splits
            dataset = self.dataset_manager.get_dataset(db, experiment.dataset_id)
            if not dataset:
                raise ValueError(f"Dataset '{experiment.dataset_id}' not found.")
                
            df_dict = self.dataset_manager.get_dataset_version_data(db, experiment.dataset_id, dataset.version)
            
            # Determine evaluation split (prefer test, then validation, then train)
            eval_split = "test"
            if eval_split not in df_dict:
                eval_split = "validation" if "validation" in df_dict else list(df_dict.keys())[0]
                
            eval_df = df_dict[eval_split]
            if max_samples:
                eval_df = eval_df.head(max_samples)
                
            # Detect text/label columns mapping
            val_report = DatasetValidator.detect_and_normalize_columns(eval_df, dataset.task)
            mapping = val_report.get("column_mapping", {})
            text_col = mapping.get("text") if dataset.task == "classification" else mapping.get("context")
            label_col = mapping.get("label") if dataset.task == "classification" else mapping.get("answers")
            
            # Retrieve unique labels list (for classification classification matching)
            target_labels = None
            if dataset.task == "classification":
                # Check all classes present in dataset
                train_split = "train" if "train" in df_dict else list(df_dict.keys())[0]
                train_df = df_dict[train_split]
                target_labels = train_df[label_col].dropna().unique().tolist()
                target_labels = [str(lbl).strip() for lbl in target_labels]
            
            # 2. Retrieve Prompt Template Body
            template_body = None
            if experiment.template_id:
                template = self.prompt_manager.get_prompt(db, experiment.template_id)
                if template:
                    template_body = self.prompt_manager.get_prompt_version_body(db, template.id, template.current_version)
                    
            if not template_body:
                # Task specific default template wrappers
                if dataset.task == "classification":
                    template_body = (
                        "Classify the following text into one of the target labels.\n"
                        "Target Labels: {{target_labels}}\n\n"
                        "{% if few_shot_examples %}"
                        "Demonstration Examples:\n"
                        "{% for ex in few_shot_examples %}"
                        "Input: {{ex.input}}\n"
                        "Label: {{ex.label}}\n\n"
                        "{% endfor %}"
                        "{% endif %}"
                        "Now classify the target query.\n"
                        "Input: {{text}}\n"
                        "Label:"
                    )
                else:
                    template_body = (
                        "Answer the question based on the provided context passage.\n\n"
                        "{% if few_shot_examples %}"
                        "Demonstration Examples:\n"
                        "{% for ex in few_shot_examples %}"
                        "Context: {{ex.input}}\n"
                        "Answer: {{ex.label}}\n\n"
                        "{% endfor %}"
                        "{% endif %}"
                        "Context: {{context}}\n"
                        "Question: {{question}}\n"
                        "Answer:"
                    )
            
            # 3. Load strategy parameters
            strategy = db.query(PromptStrategy).filter(PromptStrategy.id == experiment.strategy_id).first()
            if not strategy:
                raise ValueError(f"Strategy '{experiment.strategy_id}' not found.")
                
            strategy_config = {
                "example_count": strategy.example_count,
                "selection_strategy": strategy.selection_strategy,
                "ordering_strategy": strategy.ordering_strategy,
                "embedding_model": "all-MiniLM-L6-v2"
            }
            
            # Fetch label mapping if classification task
            label_mapping = {}
            reverse_mapping = {}
            labels_def_str = ""
            if target_labels is None:
                target_labels = []
            if dataset.task == "classification":
                label_mapping = self.dataset_manager.get_label_mapping(db, experiment.dataset_id)
                if label_mapping:
                    reverse_mapping = {str(name).strip().lower(): str(lbl_id) for lbl_id, name in label_mapping.items()}
                    header_type = "Labels" if "sst" in dataset.name.lower() or "sst2" in dataset.name.lower() else "Categories"
                    labels_def_lines = [f"{dataset.name} {header_type}", ""]
                    for lbl_id in sorted(label_mapping.keys()):
                        class_name = str(label_mapping[lbl_id]).capitalize()
                        labels_def_lines.append(f"{lbl_id} = {class_name}")
                    labels_def_str = "\n".join(labels_def_lines) + "\n\nReturn only the numeric label.\n"
                    target_labels = [str(lbl_id) for lbl_id in sorted(label_mapping.keys())]
            else:
                try:
                    unique_gts = set(str(val).strip().lower() for val in eval_df[label_col].dropna().unique())
                    if unique_gts.issubset({"true", "false", "yes", "no", "1", "0", "yes.", "no."}):
                        target_labels = ["True", "False"]
                except Exception:
                    pass

            # Prepend or insert the labels definition block before few-shot examples
            active_template_body = template_body
            if labels_def_str:
                if "{% if few_shot_examples %}" in active_template_body:
                    active_template_body = active_template_body.replace(
                        "{% if few_shot_examples %}",
                        labels_def_str + "\n{% if few_shot_examples %}"
                    )
                elif "Demonstration Examples:" in active_template_body:
                    active_template_body = active_template_body.replace(
                        "Demonstration Examples:",
                        labels_def_str + "\nDemonstration Examples:"
                    )
                else:
                    active_template_body = f"{labels_def_str}\n{active_template_body}"
            
            # 4. Initialize Generation Configuration
            gen_config = GenerationConfig(
                temperature=metadata.temperature,
                top_p=metadata.top_p,
                max_tokens=500,  # Default limit
                seed=metadata.seed
            )
            
            # Keep track of loop outcomes
            predictions = []
            ground_truths = []
            latencies = []
            costs = []
            tokens = []
            statuses = []
            
            # Loop through dataset samples
            for idx in range(len(eval_df)):
                # Check for cancellation signal
                db.refresh(run)
                if run.status == "Cancelled":
                    logger.warning(f"Experiment run {run_id} was cancelled by user.")
                    return
                    
                row = eval_df.iloc[idx]
                ground_truth = str(row[label_col]).strip()
                if dataset.task == "classification" and reverse_mapping:
                    gt_lower = ground_truth.lower()
                    if gt_lower in reverse_mapping:
                        ground_truth = reverse_mapping[gt_lower]
                ground_truths.append(ground_truth)
                
                # Fetch demonstrations
                fs_set = self.fewshot_builder.build_examples(
                    db=db,
                    dataset_id=experiment.dataset_id,
                    dataset_version=dataset.version,
                    query_index=idx,
                    strategy_config=strategy_config,
                    seed=metadata.seed or 42
                )
                
                processed_examples = []
                for ex in fs_set.examples:
                    lbl = str(ex.label).strip()
                    if dataset.task == "classification" and reverse_mapping:
                        lbl_lower = lbl.lower()
                        if lbl_lower in reverse_mapping:
                            lbl = reverse_mapping[lbl_lower]
                    
                    # Resolve human-readable label name
                    lbl_name = ""
                    if dataset.task == "classification" and label_mapping:
                        try:
                            lbl_name = label_mapping.get(int(lbl), label_mapping.get(lbl, ""))
                        except Exception:
                            lbl_name = ""

                    processed_examples.append({
                        "input": ex.input,
                        "label": lbl,
                        "label_name": lbl_name
                    })
                
                # Render Prompt Payload
                payload = {
                    "few_shot_examples": processed_examples,
                    "strategy": strategy_config
                }
                if dataset.task == "classification":
                    payload["text"] = str(row[text_col])
                    if target_labels:
                        payload["target_labels"] = ", ".join(target_labels)
                else:
                    payload["context"] = str(row[mapping.get("context")])
                    payload["question"] = str(row[mapping.get("question")])
                    
                rendered_prompt = self.prompt_manager.render_prompt(active_template_body, payload)
                
                # Execute LLM API call
                req = LLMRequest(
                    experiment_id=run_id,
                    provider=experiment.provider,
                    model=experiment.model,
                    prompt=rendered_prompt,
                    generation_config=gen_config
                )
                
                try:
                    llm_response = self.provider_service.generate(db, req)
                    
                    # Check for empty response (Validation Preconditions)
                    if llm_response.response_text is None or llm_response.response_text.strip() == "":
                        status = "FAILED"
                        prediction = None
                        is_correct = None
                        error_type = "EmptyResponse"
                        error_message = "Model returned empty text completion."
                    else:
                        status = "SUCCESS"
                        error_type = None
                        error_message = None
                        # Normalize prediction
                        prediction = ResponseProcessor.normalize_response(
                            llm_response.response_text,
                            dataset.task,
                            target_labels,
                            label_mapping=label_mapping
                        )
                        is_correct = (prediction.lower() == ground_truth.lower())
                    
                    predictions.append(prediction)
                    latencies.append(llm_response.latency_ms)
                    costs.append(llm_response.estimated_cost)
                    tokens.append(llm_response.total_tokens)
                    statuses.append(status)
                    
                    # Save Response Row
                    ExperimentRepository.save_response(
                        db=db,
                        run_id=run_id,
                        sample_index=idx,
                        prompt=rendered_prompt,
                        response_text=llm_response.response_text or "",
                        latency=llm_response.latency_ms,
                        input_tokens=llm_response.input_tokens,
                        output_tokens=llm_response.output_tokens,
                        cost=llm_response.estimated_cost,
                        finish_reason=llm_response.finish_reason,
                        ground_truth=ground_truth,
                        prediction=prediction,
                        is_correct=is_correct,
                        status=status,
                        error_type=error_type,
                        error_message=error_message,
                        can_retry=None,
                        provider=experiment.provider,
                        model=experiment.model
                    )
                except Exception as call_err:
                    logger.error(f"Failed execution on sample {idx}: {call_err}")
                    status = map_exception_to_status(call_err)
                    can_retry = check_can_retry(status)
                    
                    predictions.append(None)
                    latencies.append(0.0)
                    costs.append(0.0)
                    tokens.append(0)
                    statuses.append(status)
                    
                    ExperimentRepository.save_response(
                        db=db,
                        run_id=run_id,
                        sample_index=idx,
                        prompt=rendered_prompt,
                        response_text=f"ERROR: {str(call_err)}",
                        latency=0.0,
                        input_tokens=0,
                        output_tokens=0,
                        cost=0.0,
                        finish_reason="error",
                        ground_truth=ground_truth,
                        prediction=None,
                        is_correct=None,
                        status=status,
                        error_type=call_err.__class__.__name__,
                        error_message=str(call_err),
                        can_retry=can_retry,
                        provider=experiment.provider,
                        model=experiment.model
                    )
            
            # 5. Compute and Save Aggregated Metrics
            extra_data = {
                "latencies": latencies,
                "costs": costs,
                "tokens": tokens,
                "statuses": statuses
            }
            
            # Fetch all other runs' predictions to compute consistency
            all_runs = db.query(ExperimentRun).filter(
                ExperimentRun.experiment_id == experiment.id,
                ExperimentRun.status == "Completed"
            ).all()
            
            all_runs_predictions = []
            for r in all_runs:
                r_preds = [resp.prediction for resp in sorted(r.responses, key=lambda x: x.sample_index)]
                if len(r_preds) == len(predictions):
                    all_runs_predictions.append(r_preds)
            # Add current predictions too
            all_runs_predictions.append(predictions)
            extra_data["all_runs_predictions"] = all_runs_predictions
            
            # Calculate metrics
            metrics_results = self.evaluation_manager.evaluate_run(predictions, ground_truths, extra_data)
            
            ExperimentRepository.save_metrics(
                db=db,
                run_id=run_id,
                accuracy=metrics_results.get("accuracy", 0.0),
                precision=metrics_results.get("precision", 0.0),
                recall=metrics_results.get("recall", 0.0),
                f1=metrics_results.get("f1", 0.0),
                latency=metrics_results.get("latency", 0.0),
                cost=metrics_results.get("cost", 0.0),
                consistency=metrics_results.get("consistency", 1.0)
            )
            
            # Recalculate and update consistency across all other completed runs of this experiment
            for r in all_runs:
                r_preds = [resp.prediction for resp in sorted(r.responses, key=lambda x: x.sample_index)]
                r_gts = [resp.ground_truth for resp in sorted(r.responses, key=lambda x: x.sample_index)]
                r_statuses = [resp.status or "SUCCESS" for resp in sorted(r.responses, key=lambda x: x.sample_index)]
                r_extra = {
                    "latencies": [resp.latency for resp in sorted(r.responses, key=lambda x: x.sample_index)],
                    "costs": [resp.cost for resp in sorted(r.responses, key=lambda x: x.sample_index)],
                    "tokens": [resp.input_tokens + resp.output_tokens for resp in sorted(r.responses, key=lambda x: x.sample_index)],
                    "all_runs_predictions": all_runs_predictions,
                    "statuses": r_statuses
                }
                r_metrics_results = self.evaluation_manager.evaluate_run(r_preds, r_gts, r_extra)
                # Save updated metrics
                if r.metrics:
                    r.metrics.consistency = r_metrics_results.get("consistency", 1.0)
            db.commit()
            
            # Update status to Completed
            ExperimentRepository.update_run_status(db, run_id, "Completed")
            
        except Exception as e:
            logger.error(f"Inference pipeline execution error on run {run_id}: {e}")
            ExperimentRepository.update_run_status(db, run_id, "Failed")
            raise e

    def retry_failed_samples(self, db: Session, run_id: str) -> None:
        """
        Reruns only the failed sample generations for a completed/failed experiment run.
        """
        run = ExperimentRepository.get_run(db, run_id)
        if not run:
            raise ValueError(f"Experiment run with ID '{run_id}' not found.")
            
        experiment = run.experiment
        if not experiment:
            raise ValueError(f"No experiment associated with run ID '{run_id}'.")
            
        # Set status to Running
        ExperimentRepository.update_run_status(db, run_id, "Running")
        
        try:
            # 1. Fetch Dataset & Splits to get normalizer parameters
            dataset = self.dataset_manager.get_dataset(db, experiment.dataset_id)
            if not dataset:
                raise ValueError(f"Dataset '{experiment.dataset_id}' not found.")
                
            df_dict = self.dataset_manager.get_dataset_version_data(db, experiment.dataset_id, dataset.version)
            
            # Retrieve unique labels list (for classification classification matching)
            target_labels = None
            if dataset.task == "classification":
                # Check all classes present in dataset
                train_split = "train" if "train" in df_dict else list(df_dict.keys())[0]
                train_df = df_dict[train_split]
                
                # Detect and normalize label columns mapping
                val_report = DatasetValidator.detect_and_normalize_columns(train_df, dataset.task)
                mapping = val_report.get("column_mapping", {})
                label_col = mapping.get("label")
                
                target_labels = train_df[label_col].dropna().unique().tolist()
                target_labels = [str(lbl).strip() for lbl in target_labels]
            
            label_mapping = {}
            if dataset.task == "classification":
                label_mapping = self.dataset_manager.get_label_mapping(db, experiment.dataset_id)
                if label_mapping and target_labels is not None:
                    target_labels = [str(lbl_id) for lbl_id in sorted(label_mapping.keys())]
            
            # Load metadata for the run (generation configs)
            metadata = run.metadata_rel
            gen_config = GenerationConfig(
                temperature=metadata.temperature if metadata else None,
                top_p=metadata.top_p if metadata else None,
                max_tokens=500,
                seed=metadata.seed if metadata else None
            )
            
            # Find failed responses in this run
            failed_resps = [resp for resp in run.responses if resp.status != "SUCCESS"]
            
            for resp in failed_resps:
                req = LLMRequest(
                    experiment_id=run_id,
                    provider=experiment.provider,
                    model=experiment.model,
                    prompt=resp.prompt,
                    generation_config=gen_config
                )
                
                try:
                    llm_response = self.provider_service.generate(db, req)
                    
                    if llm_response.response_text is None or llm_response.response_text.strip() == "":
                        status = "FAILED"
                        prediction = None
                        is_correct = None
                        error_type = "EmptyResponse"
                        error_message = "Model returned empty text completion."
                    else:
                        status = "SUCCESS"
                        error_type = None
                        error_message = None
                        prediction = ResponseProcessor.normalize_response(
                            llm_response.response_text,
                            dataset.task,
                            target_labels,
                            label_mapping=label_mapping
                        )
                        is_correct = (prediction.lower() == resp.ground_truth.lower() if resp.ground_truth else False)
                    
                    # Update fields
                    resp.response = llm_response.response_text or ""
                    resp.latency = llm_response.latency_ms
                    resp.input_tokens = llm_response.input_tokens
                    resp.output_tokens = llm_response.output_tokens
                    resp.cost = llm_response.estimated_cost
                    resp.finish_reason = llm_response.finish_reason
                    resp.prediction = prediction
                    resp.is_correct = is_correct
                    resp.status = status
                    resp.error_type = error_type
                    resp.error_message = error_message
                    resp.can_retry = None
                    
                except Exception as call_err:
                    logger.error(f"Failed retry execution on sample {resp.sample_index}: {call_err}")
                    status = map_exception_to_status(call_err)
                    can_retry = check_can_retry(status)
                    
                    resp.response = f"ERROR: {str(call_err)}"
                    resp.latency = 0.0
                    resp.input_tokens = 0
                    resp.output_tokens = 0
                    resp.cost = 0.0
                    resp.finish_reason = "error"
                    resp.prediction = None
                    resp.is_correct = None
                    resp.status = status
                    resp.error_type = call_err.__class__.__name__
                    resp.error_message = str(call_err)
                    resp.can_retry = can_retry
                
                db.commit()
                
            # Recompute aggregated metrics
            all_resps = sorted(run.responses, key=lambda x: x.sample_index)
            predictions = [r.prediction for r in all_resps]
            ground_truths = [r.ground_truth for r in all_resps]
            latencies = [r.latency for r in all_resps]
            costs = [r.cost for r in all_resps]
            tokens = [r.input_tokens + r.output_tokens for r in all_resps]
            statuses = [r.status or "SUCCESS" for r in all_resps]
            
            extra_data = {
                "latencies": latencies,
                "costs": costs,
                "tokens": tokens,
                "statuses": statuses
            }
            
            # Fetch all other runs' predictions to compute consistency
            all_runs = db.query(ExperimentRun).filter(
                ExperimentRun.experiment_id == experiment.id,
                ExperimentRun.status == "Completed",
                ExperimentRun.id != run_id
            ).all()
            
            all_runs_predictions = []
            for r in all_runs:
                r_preds = [resp.prediction for resp in sorted(r.responses, key=lambda x: x.sample_index)]
                if len(r_preds) == len(predictions):
                    all_runs_predictions.append(r_preds)
            # Add current predictions
            all_runs_predictions.append(predictions)
            extra_data["all_runs_predictions"] = all_runs_predictions
            
            metrics_results = self.evaluation_manager.evaluate_run(predictions, ground_truths, extra_data)
            
            ExperimentRepository.save_metrics(
                db=db,
                run_id=run_id,
                accuracy=metrics_results.get("accuracy", 0.0),
                precision=metrics_results.get("precision", 0.0),
                recall=metrics_results.get("recall", 0.0),
                f1=metrics_results.get("f1", 0.0),
                latency=metrics_results.get("latency", 0.0),
                cost=metrics_results.get("cost", 0.0),
                consistency=metrics_results.get("consistency", 1.0)
            )
            
            db.commit()
            ExperimentRepository.update_run_status(db, run_id, "Completed")
            
        except Exception as e:
            logger.error(f"Failed to retry failed samples for run {run_id}: {e}")
            ExperimentRepository.update_run_status(db, run_id, "Failed")
            raise e

