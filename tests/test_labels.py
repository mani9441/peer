import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.db import Base

from backend.datasets.models import Dataset, DatasetVersion, DatasetLabel
from backend.datasets.dataset_manager import DatasetManager
from backend.experiments.models import Experiment, ExperimentRun, Response, Metric
from backend.experiments.manager import ExperimentManager
from backend.experiments.evaluator import ResponseProcessor


class TestLabelMetadataSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        cls.SessionLocal = sessionmaker(bind=cls.engine)
        
        # Load tables
        import backend.datasets.models
        import backend.prompts.models
        import backend.strategies.models
        import backend.fewshot.models
        import backend.providers.models
        import backend.experiments.models
        Base.metadata.create_all(bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()
        self.dataset_manager = DatasetManager()
        self.experiment_manager = ExperimentManager()
        
        # Add basic provider & strategy for experiment tests
        from backend.providers.models import Provider as DBProvider, Model as DBModel
        from backend.strategies.models import PromptStrategy
        
        # Setup strategy
        strat = PromptStrategy(
            id="strat_zero", name="Zero Shot", structure="Instruction",
            format="Plain Text", instruction_style="Simple", reasoning_style="None",
            prompt_length="Short", example_count=0, selection_strategy="None",
            ordering_strategy="None"
        )
        self.db.add(strat)
        
        # Setup provider
        prov = DBProvider(id="gemini", provider_name="Gemini", enabled=True)
        self.db.add(prov)
        self.db.commit()
        
        model = DBModel(provider_id="gemini", model_name="gemini-2.5-flash", status="active")
        self.db.add(model)
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        # Clean tables
        from backend.providers.models import Provider as DBProvider, Model as DBModel
        from backend.strategies.models import PromptStrategy
        self.db.query(Response).delete()
        self.db.query(Metric).delete()
        self.db.query(ExperimentRun).delete()
        self.db.query(Experiment).delete()
        self.db.query(DatasetLabel).delete()
        self.db.query(DatasetVersion).delete()
        self.db.query(Dataset).delete()
        self.db.query(DBModel).delete()
        self.db.query(DBProvider).delete()
        self.db.query(PromptStrategy).delete()
        self.db.commit()
        self.db.close()

    def test_manual_label_mapping_registration(self):
        # 1. Register a classification dataset with manual mapping
        df_dict = {
            "train": pd.DataFrame({"text": ["happy"], "label": ["joy"]}),
            "test": pd.DataFrame({"text": ["sad"], "label": ["sadness"]})
        }
        manual_mapping = {0: "sadness", 1: "joy"}
        
        dataset = self.dataset_manager.registry.register_dataset(
            db=self.db,
            name="emotion_test",
            task="classification",
            source="custom",
            df_dict=df_dict,
            label_mapping=manual_mapping
        )
        
        # Verify stored label mappings
        mapping = self.dataset_manager.get_label_mapping(self.db, dataset.id)
        self.assertEqual(mapping, {0: "sadness", 1: "joy"})
        
        name_0 = self.dataset_manager.get_label_name(self.db, dataset.id, 0)
        self.assertEqual(name_0, "sadness")
        
        all_lbls = self.dataset_manager.get_all_labels(self.db, dataset.id)
        self.assertEqual(len(all_lbls), 2)
        self.assertEqual(all_lbls[0]["label_name"], "sadness")

    def test_auto_generate_label_mapping(self):
        # 2. Register without mapping -> should auto-generate
        df_dict = {
            "train": pd.DataFrame({"text": ["excellent", "terrible"], "label": ["positive", "negative"]})
        }
        dataset = self.dataset_manager.registry.register_dataset(
            db=self.db,
            name="sst_auto",
            task="classification",
            source="custom",
            df_dict=df_dict
        )
        
        mapping = self.dataset_manager.get_label_mapping(self.db, dataset.id)
        # Should alphabetically sort and map: 0: negative, 1: positive
        self.assertEqual(mapping, {0: "negative", 1: "positive"})

    def test_validate_labels(self):
        # 3. Validation PASS case
        df_dict = {
            "train": pd.DataFrame({"text": ["love"], "label": ["joy"]})
        }
        dataset = self.dataset_manager.registry.register_dataset(
            db=self.db,
            name="validation_test",
            task="classification",
            source="custom",
            df_dict=df_dict,
            label_mapping={0: "joy"}
        )
        
        report = self.dataset_manager.validate_labels(self.db, dataset.id)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(len(report["errors"]), 0)

        # 4. Validation FAIL case (sample contains "sadness" which is not mapped)
        df_dict_fail = {
            "train": pd.DataFrame({"text": ["love", "cry"], "label": ["joy", "sadness"]})
        }
        # Force save a version with unmapped values
        self.dataset_manager.registry.create_dataset_version(
            db=self.db,
            dataset_id=dataset.id,
            version="v2",
            df_dict=df_dict_fail,
            parent_version="v1",
            transformations={"info": "Adding unmapped labels"},
            label_mapping={0: "joy"} # Omit mapping for "sadness"
        )
        
        report_fail = self.dataset_manager.validate_labels(self.db, dataset.id)
        self.assertEqual(report_fail["status"], "FAIL")
        self.assertTrue(any("sadness" in err for err in report_fail["errors"]))

    @patch("backend.datasets.dataset_manager.DatasetManager.get_dataset_version_data")
    @patch("backend.providers.service.ProviderService.generate")
    def test_pipeline_injects_numeric_labels(self, mock_generate, mock_get_dataset_data):
        # Setup mock split data
        mock_get_dataset_data.return_value = {
            "test": pd.DataFrame({"text": ["so good"], "label": ["positive"]}),
            "train": pd.DataFrame({"text": ["bad"], "label": ["negative"]})
        }

        # Mock LLM API response returning the numeric digit "1"
        mock_response = MagicMock()
        mock_response.response_text = "The answer is 1."
        mock_response.latency_ms = 100
        mock_response.input_tokens = 25
        mock_response.output_tokens = 5
        mock_response.total_tokens = 30
        mock_response.estimated_cost = 0.0001
        mock_response.finish_reason = "stop"
        mock_response.request_timestamp = datetime.datetime.utcnow()
        mock_response.response_timestamp = datetime.datetime.utcnow()
        mock_generate.return_value = mock_response

        # Register classification dataset with mapping
        dataset = self.dataset_manager.registry.register_dataset(
            db=self.db,
            name="Pipeline Labels sst",
            task="classification",
            source="custom",
            df_dict={
                "train": pd.DataFrame({"text": ["bad"], "label": ["negative"]}),
                "test": pd.DataFrame({"text": ["so good"], "label": ["positive"]})
            },
            label_mapping={0: "negative", 1: "positive"}
        )


        exp = self.experiment_manager.create_experiment(
            db=self.db,
            name="Numeric Labels Eval",
            description="Testing prompt insertions",
            dataset_id=dataset.id,
            template_id=None,
            strategy_id="strat_zero",
            provider="gemini",
            model="gemini-2.5-flash"
        )

        # Run single run execution
        run = self.experiment_manager.run_single(
            db=self.db,
            experiment_id=exp.id,
            run_number=1,
            max_samples=1
        )

        self.assertEqual(run.status, "Completed")
        
        # Verify stored response prediction is parsed to "1" and correct matches ground truth ID "1"
        db_response = self.db.query(Response).filter(Response.run_id == run.id).first()
        self.assertIsNotNone(db_response)
        
        # Verify the prompt generated and passed to mock_generate contains the label mapping header
        generated_prompt = mock_generate.call_args[0][1].prompt
        self.assertIn("0 = Negative", generated_prompt)
        self.assertIn("1 = Positive", generated_prompt)
        self.assertIn("Return only the numeric label", generated_prompt)
        
        # Ground truth should have been converted to "1"
        self.assertEqual(db_response.ground_truth, "1")
        # LLM answered "1" -> ResponseProcessor parsed to "1"
        self.assertEqual(db_response.prediction, "1")
        self.assertTrue(db_response.is_correct)


if __name__ == "__main__":
    unittest.main()
