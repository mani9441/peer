import unittest
from unittest.mock import MagicMock, patch
import datetime
import os
import tempfile
import shutil
import json
import zipfile
import pandas as pd

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.db import Base

from backend.datasets.models import Dataset, DatasetVersion
from backend.prompts.models import PromptTemplate, PromptVersion
from backend.strategies.models import PromptStrategy, StrategyVersion
from backend.providers.models import Provider as DBProvider, Model as DBModel

from backend.experiments.models import Experiment, ExperimentRun, Response, Metric, Metadata
from backend.experiments.evaluator import ResponseProcessor, EvaluationManager
from backend.experiments.repository import ExperimentRepository
from backend.experiments.utils import generate_uuid
from backend.experiments.manager import ExperimentManager
from backend.providers.exceptions import ConfigurationError


class TestExperimentsSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize in-memory SQLite database
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        cls.SessionLocal = sessionmaker(bind=cls.engine)
        
        # Register all models with metadata
        import backend.datasets.models
        import backend.prompts.models
        import backend.strategies.models
        import backend.fewshot.models
        import backend.providers.models
        import backend.experiments.models
        Base.metadata.create_all(bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ExperimentManager(export_dir=self.temp_dir)
        
        # Seed mock data for validation checks
        # 1. Dataset
        ds = Dataset(
            id="ds_sst2", name="SST-2", version="v1", task="classification",
            source="HuggingFace", hash="sst2-hash"
        )
        self.db.add(ds)
        self.db.commit()
        
        # Dataset Version
        # We write dummy parquet/data path
        ds_ver = DatasetVersion(
            dataset_id="ds_sst2", version="v1", hash="sst2-hash", path="dummy_path"
        )
        self.db.add(ds_ver)
        
        # 2. Template
        tpl = PromptTemplate(
            id="tpl_sentiment", name="Sentiment Template", task_type="classification",
            strategy="Instruction", format="Plain Text", instruction_style="Simple",
            reasoning_style="None"
        )
        self.db.add(tpl)
        self.db.commit()
        
        tpl_ver = PromptVersion(
            prompt_id="tpl_sentiment", version="1", template_body="Classify text: {{text}}"
        )
        self.db.add(tpl_ver)
        
        # 3. Strategy
        strat = PromptStrategy(
            id="strat_zero_shot", name="Zero Shot Strategy", structure="Instruction",
            format="Plain Text", instruction_style="Simple", reasoning_style="None",
            prompt_length="Short", example_count=0, selection_strategy="None",
            ordering_strategy="None"
        )
        self.db.add(strat)
        
        # 4. Providers & Models
        prov = DBProvider(id="gemini", provider_name="Gemini", enabled=True)
        self.db.add(prov)
        self.db.commit()
        
        model = DBModel(provider_id="gemini", model_name="gemini-2.5-flash", status="active")
        self.db.add(model)
        
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        # Clean tables
        self.db.query(Response).delete()
        self.db.query(Metric).delete()
        self.db.query(Metadata).delete()
        self.db.query(ExperimentRun).delete()
        self.db.query(Experiment).delete()
        self.db.query(DBModel).delete()
        self.db.query(DBProvider).delete()
        self.db.query(PromptVersion).delete()
        self.db.query(PromptTemplate).delete()
        self.db.query(PromptStrategy).delete()
        self.db.query(DatasetVersion).delete()
        self.db.query(Dataset).delete()
        self.db.commit()
        self.db.close()
        shutil.rmtree(self.temp_dir)

    # ----------------- 1. Test Response Normalization -----------------
    def test_response_normalization(self):
        labels = ["Positive", "Negative", "Neutral"]
        
        # Exact Match
        self.assertEqual(ResponseProcessor.normalize_response("Positive", "classification", labels), "Positive")
        
        # Case Insensitive
        self.assertEqual(ResponseProcessor.normalize_response("  negative  ", "classification", labels), "Negative")
        
        # Standalone Substring in text
        self.assertEqual(ResponseProcessor.normalize_response("The predicted sentiment is Neutral.", "classification", labels), "Neutral")
        
        # Markdown cleanup
        self.assertEqual(ResponseProcessor.normalize_response("```\nPositive\n```", "classification", labels), "Positive")
        
        # Non-matching fallback
        self.assertEqual(ResponseProcessor.normalize_response("Unexpected Completion Text", "classification", labels), "Unexpected Completion Text")
        
        # QA direct return (no targets specified)
        self.assertEqual(ResponseProcessor.normalize_response("Detailed answer text here.", "qa", None), "Detailed answer text here.")

        # --- ADVANCED EXTRACTION TESTS ---
        # 1. Answer Patterns Extraction
        self.assertEqual(
            ResponseProcessor.normalize_response("**Answer**: False (due to ethanol structure)", "qa", ["True", "False"]),
            "False"
        )
        self.assertEqual(
            ResponseProcessor.normalize_response("The answer is True.", "qa", ["True", "False"]),
            "True"
        )
        self.assertEqual(
            ResponseProcessor.normalize_response("prediction: Negative", "classification", labels),
            "Negative"
        )

        # 2. Boolean Synonym Mapping
        self.assertEqual(
            ResponseProcessor.normalize_response("Yes, the sugarcane ethanol is...", "qa", ["True", "False"]),
            "True"
        )
        self.assertEqual(
            ResponseProcessor.normalize_response("No. It is incorrect.", "qa", ["True", "False"]),
            "False"
        )

        # 3. Label Mapping translation (Class name to Class ID)
        class_mapping = {0: "sadness", 1: "joy", 2: "love"}
        class_ids = ["0", "1", "2"]
        self.assertEqual(
            ResponseProcessor.normalize_response("The emotion of the customer is sadness.", "classification", class_ids, label_mapping=class_mapping),
            "0"
        )
        self.assertEqual(
            ResponseProcessor.normalize_response("joy", "classification", class_ids, label_mapping=class_mapping),
            "1"
        )

    # ----------------- 2. Test Metric Evaluations -----------------
    def test_evaluation_metrics(self):
        eval_mgr = EvaluationManager()
        predictions = ["positive", "negative", "positive", "positive"]
        ground_truths = ["positive", "negative", "negative", "positive"]
        
        # Accuracy: 3 correct / 4 total = 0.75
        extra_data = {
            "latencies": [100.0, 200.0, 150.0, 150.0],
            "costs": [0.001, 0.002, 0.001, 0.001],
            "tokens": [100, 200, 150, 150]
        }
        
        results = eval_mgr.evaluate_run(predictions, ground_truths, extra_data)
        self.assertEqual(results["accuracy"], 0.75)
        self.assertEqual(results["latency"], 150.0) # Mean latency
        self.assertEqual(results["cost"], 0.005)    # Total cost
        self.assertEqual(results["token_usage"], 600.0) # Total tokens

    def test_consistency_metric(self):
        eval_mgr = EvaluationManager()
        predictions = ["positive", "negative", "positive"]
        ground_truths = ["positive", "negative", "negative"]
        
        # Add predictions from multiple runs to compute mode frequency agreement
        extra_data = {
            "all_runs_predictions": [
                ["positive", "negative", "positive"],  # Run 1
                ["positive", "neutral", "positive"],   # Run 2
                ["positive", "negative", "negative"]   # Run 3 (current)
            ]
        }
        # Sample 0: ["positive", "positive", "positive"] -> Mode freq: 3/3 = 1.0
        # Sample 1: ["negative", "neutral", "negative"] -> Mode freq: 2/3 = 0.666
        # Sample 2: ["positive", "positive", "negative"] -> Mode freq: 2/3 = 0.666
        # Avg Consistency = (1.0 + 0.666 + 0.666) / 3 = 0.777
        results = eval_mgr.evaluate_run(predictions, ground_truths, extra_data)
        self.assertAlmostEqual(results["consistency"], 0.7777777777777778)

    # ----------------- 3. Test Config Validation -----------------
    def test_invalid_experiment_configuration(self):
        # Try to create experiment with non-existing dataset
        with self.assertRaises(ConfigurationError):
            self.manager.create_experiment(
                db=self.db,
                name="Invalid Exp",
                description="Test",
                dataset_id="unknown_ds",
                template_id="tpl_sentiment",
                strategy_id="strat_zero_shot",
                provider="gemini",
                model="gemini-2.5-flash"
            )

    def test_valid_experiment_creation(self):
        exp = self.manager.create_experiment(
            db=self.db,
            name="Valid Sentiment Experiment",
            description="Testing SST-2 Classification",
            dataset_id="ds_sst2",
            template_id="tpl_sentiment",
            strategy_id="strat_zero_shot",
            provider="gemini",
            model="gemini-2.5-flash"
        )
        self.assertEqual(exp.name, "Valid Sentiment Experiment")
        self.assertEqual(exp.provider, "gemini")
        self.assertEqual(exp.model, "gemini-2.5-flash")

    # ----------------- 4. Test Single Run Pipeline Execution -----------------
    @patch("backend.datasets.dataset_manager.DatasetManager.get_dataset_version_data")
    @patch("backend.providers.service.ProviderService.generate")
    def test_single_run_pipeline_execution(self, mock_generate, mock_get_dataset_data):
        # Mock dataset version split data: we return a small 2-row classification dataframe split
        mock_get_dataset_data.return_value = {
            "test": pd.DataFrame({
                "sentence": ["extremely good movie", "terrible script and acting"],
                "label": ["positive", "negative"]
            }),
            "train": pd.DataFrame({
                "sentence": ["great story", "bad film"],
                "label": ["positive", "negative"]
            })
        }
        
        # Mock LLM API Responses
        mock_response_1 = MagicMock()
        mock_response_1.response_text = "positive"
        mock_response_1.latency_ms = 120
        mock_response_1.input_tokens = 10
        mock_response_1.output_tokens = 2
        mock_response_1.total_tokens = 12
        mock_response_1.estimated_cost = 0.0001
        mock_response_1.finish_reason = "stop"
        mock_response_1.request_timestamp = datetime.datetime.utcnow()
        mock_response_1.response_timestamp = datetime.datetime.utcnow()
        
        mock_response_2 = MagicMock()
        mock_response_2.response_text = "The prediction is negative."
        mock_response_2.latency_ms = 180
        mock_response_2.input_tokens = 12
        mock_response_2.output_tokens = 4
        mock_response_2.total_tokens = 16
        mock_response_2.estimated_cost = 0.0002
        mock_response_2.finish_reason = "stop"
        mock_response_2.request_timestamp = datetime.datetime.utcnow()
        mock_response_2.response_timestamp = datetime.datetime.utcnow()

        mock_generate.side_effect = [mock_response_1, mock_response_2]

        # Create experiment
        exp = self.manager.create_experiment(
            db=self.db,
            name="Valid SST-2 Exp",
            description="Testing Classification",
            dataset_id="ds_sst2",
            template_id="tpl_sentiment",
            strategy_id="strat_zero_shot",
            provider="gemini",
            model="gemini-2.5-flash"
        )
        
        # Run execution run synchronously
        run = self.manager.run_single(
            db=self.db,
            experiment_id=exp.id,
            run_number=1,
            temperature=0.7,
            top_p=0.9,
            seed=42,
            max_samples=2
        )
        
        self.assertEqual(run.status, "Completed")
        self.assertEqual(run.run_number, 1)
        
        # Verify Responses logged in DB
        db_responses = self.db.query(Response).filter(Response.run_id == run.id).all()
        self.assertEqual(len(db_responses), 2)
        
        # Sample 0
        self.assertEqual(db_responses[0].prediction, "positive")
        self.assertEqual(db_responses[0].ground_truth, "positive")
        self.assertTrue(db_responses[0].is_correct)
        self.assertEqual(db_responses[0].latency, 120.0)
        
        # Sample 1
        self.assertEqual(db_responses[1].prediction, "negative")
        self.assertEqual(db_responses[1].ground_truth, "negative")
        self.assertTrue(db_responses[1].is_correct)
        
        # Verify Metrics logged in DB (both correct -> accuracy 1.0)
        db_metrics = self.db.query(Metric).filter(Metric.run_id == run.id).first()
        self.assertIsNotNone(db_metrics)
        self.assertEqual(db_metrics.accuracy, 1.0)
        self.assertEqual(db_metrics.latency, 150.0) # Mean: (120+180)/2
        self.assertAlmostEqual(db_metrics.cost, 0.0003) # Total: 0.0001 + 0.0002
        
        # Verify Metadata logged in DB
        db_metadata = self.db.query(Metadata).filter(Metadata.run_id == run.id).first()
        self.assertIsNotNone(db_metadata)
        self.assertEqual(db_metadata.temperature, 0.7)
        self.assertEqual(db_metadata.top_p, 0.9)
        self.assertEqual(db_metadata.seed, 42)

    # ----------------- 5. Test Exporting -----------------
    @patch("backend.datasets.dataset_manager.DatasetManager.get_dataset_version_data")
    @patch("backend.providers.service.ProviderService.generate")
    def test_exporter_validation(self, mock_generate, mock_get_dataset_data):
        mock_get_dataset_data.return_value = {
            "test": pd.DataFrame({"sentence": ["good movie"], "label": ["positive"]}),
            "train": pd.DataFrame({"sentence": ["great story"], "label": ["positive"]})
        }
        mock_response = MagicMock()
        mock_response.response_text = "positive"
        mock_response.latency_ms = 100
        mock_response.input_tokens = 5
        mock_response.output_tokens = 1
        mock_response.total_tokens = 6
        mock_response.estimated_cost = 0.00001
        mock_response.finish_reason = "stop"
        mock_response.request_timestamp = datetime.datetime.utcnow()
        mock_response.response_timestamp = datetime.datetime.utcnow()
        mock_generate.return_value = mock_response

        exp = self.manager.create_experiment(
            db=self.db,
            name="SST-2 Export Exp",
            description="Testing Export",
            dataset_id="ds_sst2",
            template_id="tpl_sentiment",
            strategy_id="strat_zero_shot",
            provider="gemini",
            model="gemini-2.5-flash"
        )
        
        self.manager.run_single(db=self.db, experiment_id=exp.id, run_number=1, max_samples=1)
        
        # Test JSON Export
        json_path = self.manager.export_results(self.db, exp.id, format="json")
        self.assertTrue(os.path.exists(json_path))
        with open(json_path, "r") as f:
            data = json.load(f)
            self.assertEqual(data["name"], "SST-2 Export Exp")
            self.assertEqual(len(data["runs"]), 1)
            self.assertEqual(data["runs"][0]["status"], "Completed")

        # Test CSV Export
        csv_path = self.manager.export_results(self.db, exp.id, format="csv")
        self.assertTrue(os.path.exists(csv_path))

        # Test Package Export (zip package)
        zip_path = self.manager.export_results(self.db, exp.id, format="package")
        self.assertTrue(os.path.exists(zip_path))
        self.assertTrue(zipfile.is_zipfile(zip_path))
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            filenames = zip_ref.namelist()
            self.assertTrue(any(f.endswith(".json") for f in filenames))
            self.assertTrue(any(f.endswith(".csv") for f in filenames))

    # ----------------- 6. Test History Loader & Comparisons -----------------
    @patch("backend.datasets.dataset_manager.DatasetManager.get_dataset_version_data")
    @patch("backend.providers.service.ProviderService.generate")
    def test_run_history_and_comparisons(self, mock_generate, mock_get_dataset_data):
        mock_get_dataset_data.return_value = {
            "test": pd.DataFrame({"sentence": ["good"], "label": ["positive"]}),
            "train": pd.DataFrame({"sentence": ["great"], "label": ["positive"]})
        }
        
        mock_response_1 = MagicMock(response_text="positive", latency_ms=100, input_tokens=5, output_tokens=1, total_tokens=6, estimated_cost=0.00001, finish_reason="stop", request_timestamp=datetime.datetime.utcnow(), response_timestamp=datetime.datetime.utcnow())
        mock_response_2 = MagicMock(response_text="negative", latency_ms=150, input_tokens=5, output_tokens=1, total_tokens=6, estimated_cost=0.00001, finish_reason="stop", request_timestamp=datetime.datetime.utcnow(), response_timestamp=datetime.datetime.utcnow())
        mock_generate.side_effect = [mock_response_1, mock_response_2]

        exp = self.manager.create_experiment(
            db=self.db,
            name="History Exp",
            description="Testing stats",
            dataset_id="ds_sst2",
            template_id="tpl_sentiment",
            strategy_id="strat_zero_shot",
            provider="gemini",
            model="gemini-2.5-flash"
        )
        
        # Run 2 runs to verify Mean/Variance calculation
        self.manager.run_single(db=self.db, experiment_id=exp.id, run_number=1, max_samples=1)
        self.manager.run_single(db=self.db, experiment_id=exp.id, run_number=2, max_samples=1)
        
        history = self.manager.load_history(self.db, exp.id)
        
        self.assertEqual(history["summary"]["total_runs_count"], 2)
        # Run 1 prediction: "positive" (correct -> acc 1.0)
        # Run 2 prediction: "negative" (incorrect -> acc 0.0)
        # Mean Accuracy should be 0.5
        self.assertEqual(history["summary"]["accuracy_mean"], 0.5)
        # Mean Latency: (100 + 150) / 2 = 125.0
        self.assertEqual(history["summary"]["latency_mean"], 125.0)

        # Test compare experiments
        comparisons = self.manager.compare_experiments(self.db, [exp.id])
        self.assertIn(exp.id, comparisons)
        self.assertEqual(comparisons[exp.id]["name"], "History Exp")
        self.assertEqual(comparisons[exp.id]["accuracy_mean"], 0.5)


    # ----------------- 7. Test Reliability & Failure Handling -----------------
    @patch("backend.datasets.dataset_manager.DatasetManager.get_dataset_version_data")
    @patch("backend.providers.service.ProviderService.generate")
    def test_llm_execution_reliability(self, mock_generate, mock_get_dataset_data):
        mock_get_dataset_data.return_value = {
            "test": pd.DataFrame({"sentence": ["good", "bad", "okay"], "label": ["positive", "negative", "neutral"]}),
            "train": pd.DataFrame({"sentence": ["great"], "label": ["positive"]})
        }
        
        # 1st call: Success, 2nd call: TimeoutError, 3rd call: Success
        from backend.providers.exceptions import TimeoutError
        mock_resp_1 = MagicMock(response_text="positive", latency_ms=100, input_tokens=5, output_tokens=1, total_tokens=6, estimated_cost=0.00001, finish_reason="stop", request_timestamp=datetime.datetime.utcnow(), response_timestamp=datetime.datetime.utcnow())
        mock_resp_3 = MagicMock(response_text="neutral", latency_ms=120, input_tokens=5, output_tokens=1, total_tokens=6, estimated_cost=0.00001, finish_reason="stop", request_timestamp=datetime.datetime.utcnow(), response_timestamp=datetime.datetime.utcnow())
        
        mock_generate.side_effect = [mock_resp_1, TimeoutError("Gemini request timed out"), mock_resp_3]

        exp = self.manager.create_experiment(
            db=self.db,
            name="Reliability Exp",
            description="Testing reliability",
            dataset_id="ds_sst2",
            template_id="tpl_sentiment",
            strategy_id="strat_zero_shot",
            provider="gemini",
            model="gemini-2.5-flash"
        )
        
        # Run study with 3 samples
        run = self.manager.run_single(db=self.db, experiment_id=exp.id, run_number=1, max_samples=3)
        
        # Reload responses from database
        resps = sorted(run.responses, key=lambda x: x.sample_index)
        self.assertEqual(len(resps), 3)
        
        # 1st response: SUCCESS
        self.assertEqual(resps[0].status, "SUCCESS")
        self.assertEqual(resps[0].prediction, "positive")
        self.assertEqual(resps[0].is_correct, True)
        
        # 2nd response: TIMEOUT
        self.assertEqual(resps[1].status, "TIMEOUT")
        self.assertIsNone(resps[1].prediction)
        self.assertIsNone(resps[1].is_correct)
        self.assertEqual(resps[1].error_type, "TimeoutError")
        self.assertIn("timed out", resps[1].error_message)
        
        # 3rd response: SUCCESS
        self.assertEqual(resps[2].status, "SUCCESS")
        self.assertEqual(resps[2].prediction, "neutral")
        self.assertEqual(resps[2].is_correct, True)

        # Accuracy should be calculated over SUCCESS samples only: 2 correct / 2 successful = 1.0 (100%)
        # Not 2/3 (66.6%)
        self.assertEqual(run.metrics.accuracy, 1.0)
        
        # Test retry failed samples
        # Next generation mock (when retrying sample index 1)
        mock_resp_retry = MagicMock(response_text="negative", latency_ms=110, input_tokens=5, output_tokens=1, total_tokens=6, estimated_cost=0.00001, finish_reason="stop", request_timestamp=datetime.datetime.utcnow(), response_timestamp=datetime.datetime.utcnow())
        mock_generate.side_effect = [mock_resp_retry]
        
        self.manager.retry_failed_samples(self.db, run.id)
        
        # Reload responses
        self.db.refresh(run)
        resps_updated = sorted(run.responses, key=lambda x: x.sample_index)
        
        self.assertEqual(resps_updated[1].status, "SUCCESS")
        self.assertEqual(resps_updated[1].prediction, "negative")
        self.assertEqual(resps_updated[1].is_correct, True)
        
        # Metrics should be updated: 3 successful, all 3 correct -> accuracy 1.0
        self.assertEqual(run.metrics.accuracy, 1.0)


if __name__ == "__main__":
    unittest.main()
