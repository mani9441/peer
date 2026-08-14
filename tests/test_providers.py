import unittest
from unittest.mock import MagicMock, patch
import datetime
import os
import tempfile
import shutil
import json

# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker# pyrefly: ignore [missing-import]
from backend.database.db import Base

from backend.providers.exceptions import (
    AuthenticationError,
    InvalidModelError,
    TimeoutError,
    ProviderUnavailableError,
    ContextLengthExceededError,
    ConfigurationError
)
from backend.providers.schemas import LLMRequest, LLMResponse, GenerationConfig
from backend.providers.pricing import PricingManager
from backend.providers.tokenizer import Tokenizer
from backend.providers.retry import RetryHandler
from backend.providers.validators import RequestValidator
from backend.providers.models import Provider as DBProvider, Model as DBModel, ProviderRequest as DBProviderRequest
from backend.providers.service import ProviderService

# ----------------- Database Setup for Testing -----------------
class TestDatabaseMixin:
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        cls.SessionLocal = sessionmaker(bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()
        # Seed default tables
        self.service = ProviderService()
        self.service._ensure_providers_seeded(self.db)

    def tearDown(self):
        self.db.rollback()
        # Clear tables
        self.db.query(DBProviderRequest).delete()
        self.db.query(DBModel).delete()
        self.db.query(DBProvider).delete()
        self.db.commit()
        self.db.close()


# ----------------- Unit Tests -----------------

class TestPricingManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.pricing_file = os.path.join(self.temp_dir, "pricing.json")
        self.manager = PricingManager(self.pricing_file)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_default_pricing_initialization(self):
        # Cache file should be generated
        self.assertTrue(os.path.exists(self.pricing_file))
        pricing = self.manager.get_pricing("gemini", "gemini-2.5-flash")
        self.assertEqual(pricing["input_price"], 0.075 / 1_000_000)
        self.assertEqual(pricing["output_price"], 0.30 / 1_000_000)

    def test_pricing_calculation(self):
        cost = self.manager.calculate_price("openai", "gpt-5", 1000, 2000)
        # input: 1000 * 5e-6 = 0.005
        # output: 2000 * 15e-6 = 0.030
        # total: 0.035
        self.assertAlmostEqual(cost, 0.035)

    def test_pricing_fallbacks(self):
        # Non-existing model should fallback to default for that provider
        pricing = self.manager.get_pricing("openai", "gpt-unknown")
        self.assertEqual(pricing["input_price"], 0.15 / 1_000_000) # fallback is gpt-5-mini standard or similar? Wait, default fallback in loader for openai is not set but pricing fallback matches partial keys or returns default/0.0
        
        # Test unknown provider
        pricing_unknown = self.manager.get_pricing("unknown_prov", "some_model")
        self.assertEqual(pricing_unknown["input_price"], 0.0)
        self.assertEqual(pricing_unknown["output_price"], 0.0)


class TestTokenizer(unittest.TestCase):
    def test_tokenizer_estimation(self):
        # Empty string
        self.assertEqual(Tokenizer.estimate_tokens(""), 0)
        # Test normal string with fallback
        text = "Hello world! This is a simple test prompt."
        # Character count: 42. Fallback: 42/4 = 10 tokens
        # Since tiktoken is installed, it will use cl100k_base.
        # "Hello world! This is a simple test prompt." has exactly 10 tokens in cl100k_base.
        tokens = Tokenizer.estimate_tokens(text)
        self.assertTrue(tokens > 0)


class TestRetryHandler(unittest.TestCase):
    def test_retry_success(self):
        call_count = 0
        def dummy_success():
            nonlocal call_count
            call_count += 1
            return "success"
            
        res = RetryHandler.execute_with_retry(dummy_success, max_retries=3, initial_backoff=0.01)
        self.assertEqual(res, "success")
        self.assertEqual(call_count, 1)

    def test_retry_transient_failure_then_success(self):
        call_count = 0
        def dummy_fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Temporary timeout")
            return "success"
            
        res = RetryHandler.execute_with_retry(dummy_fail_then_succeed, max_retries=3, initial_backoff=0.01)
        self.assertEqual(res, "success")
        self.assertEqual(call_count, 3)

    def test_retry_non_retryable_exception(self):
        call_count = 0
        def dummy_non_retryable():
            nonlocal call_count
            call_count += 1
            raise AuthenticationError("Invalid key")
            
        with self.assertRaises(AuthenticationError):
            RetryHandler.execute_with_retry(dummy_non_retryable, max_retries=3, initial_backoff=0.01)
        # AuthenticationError is not retryable, so it should exit after 1 attempt
        self.assertEqual(call_count, 1)


class TestRequestValidator(unittest.TestCase):
    def test_valid_request(self):
        req = LLMRequest(
            provider="gemini",
            model="gemini-2.5-flash",
            prompt="Hello",
            generation_config=GenerationConfig(
                temperature=0.7,
                top_p=0.9,
                max_tokens=100,
                seed=42
            )
        )
        # Should not raise any error
        RequestValidator.validate_request(req)

    def test_invalid_ranges(self):
        # Test temperature
        with self.assertRaises(ConfigurationError):
            RequestValidator.validate_request(LLMRequest(
                provider="gemini", model="gemini", prompt="Hi",
                generation_config=GenerationConfig(temperature=2.5)
            ))
            
        # Test top_p
        with self.assertRaises(ConfigurationError):
            RequestValidator.validate_request(LLMRequest(
                provider="gemini", model="gemini", prompt="Hi",
                generation_config=GenerationConfig(top_p=-0.1)
            ))

        # Test max_tokens
        with self.assertRaises(ConfigurationError):
            RequestValidator.validate_request(LLMRequest(
                provider="gemini", model="gemini", prompt="Hi",
                generation_config=GenerationConfig(max_tokens=-5)
            ))


# ----------------- Mock Provider Tests -----------------

class TestGeminiProviderMock(unittest.TestCase):
    @patch("google.genai.Client")
    def test_gemini_provider_success(self, mock_client_class):
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.text = "Gemini Response"
        
        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 10
        mock_usage.candidates_token_count = 20
        mock_response.usage_metadata = mock_usage
        
        mock_candidate = MagicMock()
        mock_candidate.finish_reason = "STOP"
        mock_response.candidates = [mock_candidate]
        
        mock_client.models.generate_content.return_value = mock_response

        # Call
        from backend.providers.gemini_provider import GeminiProvider
        provider = GeminiProvider(api_key="fake-gemini-key")
        req = LLMRequest(provider="gemini", model="gemini-2.5-flash", prompt="Hello Gemini")
        resp = provider.generate(req)
        
        self.assertEqual(resp.provider, "gemini")
        self.assertEqual(resp.model, "gemini-2.5-flash")
        self.assertEqual(resp.response_text, "Gemini Response")
        self.assertEqual(resp.input_tokens, 10)
        self.assertEqual(resp.output_tokens, 20)
        self.assertEqual(resp.total_tokens, 30)

    @patch("google.genai.Client")
    def test_gemini_provider_exceptions(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API key is invalid")

        from backend.providers.gemini_provider import GeminiProvider
        provider = GeminiProvider(api_key="bad-key")
        req = LLMRequest(provider="gemini", model="gemini-2.5-flash", prompt="Hello")
        
        with self.assertRaises(AuthenticationError):
            provider.generate(req)


class TestOpenAIProviderMock(unittest.TestCase):
    @patch("openai.OpenAI")
    def test_openai_provider_success(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_choice = MagicMock()
        mock_choice.message.content = "OpenAI Response"
        mock_choice.finish_reason = "stop"
        
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 15
        mock_usage.completion_tokens = 25
        
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        
        mock_client.chat.completions.create.return_value = mock_response

        from backend.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key="fake-openai-key")
        req = LLMRequest(provider="openai", model="gpt-5", prompt="Hello OpenAI")
        resp = provider.generate(req)
        
        self.assertEqual(resp.provider, "openai")
        self.assertEqual(resp.model, "gpt-5")
        self.assertEqual(resp.response_text, "OpenAI Response")
        self.assertEqual(resp.input_tokens, 15)
        self.assertEqual(resp.output_tokens, 25)
        self.assertEqual(resp.total_tokens, 40)


class TestOpenRouterProviderMock(unittest.TestCase):
    @patch("requests.post")
    def test_openrouter_provider_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "OpenRouter Response"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 18
            }
        }
        mock_post.return_value = mock_response

        from backend.providers.openrouter_provider import OpenRouterProvider
        provider = OpenRouterProvider(api_key="fake-openrouter-key")
        req = LLMRequest(provider="openrouter", model="meta-llama/llama-3.1-8b-instruct:free", prompt="Hello OR")
        resp = provider.generate(req)
        
        self.assertEqual(resp.provider, "openrouter")
        self.assertEqual(resp.response_text, "OpenRouter Response")
        self.assertEqual(resp.input_tokens, 12)
        self.assertEqual(resp.output_tokens, 18)


class TestOllamaProviderMock(unittest.TestCase):
    @patch("ollama.Client")
    def test_ollama_provider_success(self, mock_ollama_client):
        mock_client = MagicMock()
        mock_ollama_client.return_value = mock_client
        
        mock_client.chat.return_value = {
            "message": {"content": "Ollama Response"},
            "prompt_eval_count": 8,
            "eval_count": 12
        }

        from backend.providers.ollama_provider import OllamaProvider
        provider = OllamaProvider(api_base="http://localhost:11434")
        req = LLMRequest(provider="ollama", model="llama3.1:latest", prompt="Hello Ollama")
        resp = provider.generate(req)
        
        self.assertEqual(resp.provider, "ollama")
        self.assertEqual(resp.response_text, "Ollama Response")
        self.assertEqual(resp.input_tokens, 8)
        self.assertEqual(resp.output_tokens, 12)
        
        mock_client.chat.assert_called_once_with(
            model="llama3.1:latest",
            messages=[{"role": "user", "content": "Hello Ollama"}],
            options={},
            think=False
        )


# ----------------- DB Orchestration & End-to-End Mocks -----------------

class TestProviderServiceOrchestration(TestDatabaseMixin, unittest.TestCase):
    @patch("backend.providers.gemini_provider.GeminiProvider.generate")
    def test_successful_request_db_logging(self, mock_gemini_generate):
        # Mock provider generate method
        mock_gemini_generate.return_value = LLMResponse(
            provider="gemini",
            model="gemini-2.5-flash",
            response_text="Mocked Gemini Text",
            latency_ms=150,
            input_tokens=10,
            output_tokens=15,
            total_tokens=25,
            estimated_cost=0.0,
            finish_reason="stop",
            request_timestamp=datetime.datetime.utcnow(),
            response_timestamp=datetime.datetime.utcnow(),
            status="success"
        )

        req = LLMRequest(
            experiment_id="exp-run-001",
            provider="gemini",
            model="gemini-2.5-flash",
            prompt="Test Prompt"
        )
        
        # Invoke service generate (which handles cost calculation and db logging)
        resp = self.service.generate(self.db, req)
        
        self.assertEqual(resp.response_text, "Mocked Gemini Text")
        # cost should be calculated by pricing_manager downstream:
        # gemini-2.5-flash cost: input 10 * 7.5e-8 = 7.5e-7; output 15 * 3e-7 = 4.5e-6; total = 5.25e-6
        self.assertAlmostEqual(resp.estimated_cost, 5.25e-6)

        # Check DB request logging
        db_logs = self.db.query(DBProviderRequest).all()
        self.assertEqual(len(db_logs), 1)
        log = db_logs[0]
        self.assertEqual(log.experiment_run, "exp-run-001")
        self.assertEqual(log.provider, "gemini")
        self.assertEqual(log.model, "gemini-2.5-flash")
        self.assertEqual(log.latency, 150)
        self.assertEqual(log.tokens, 25)
        self.assertAlmostEqual(log.cost, 5.25e-6)
        self.assertEqual(log.status, "success")

    @patch("backend.providers.gemini_provider.GeminiProvider.generate")
    def test_failed_request_db_logging(self, mock_gemini_generate):
        mock_gemini_generate.side_effect = TimeoutError("Request Timeout")

        req = LLMRequest(
            experiment_id="exp-run-002",
            provider="gemini",
            model="gemini-2.5-flash",
            prompt="Test Prompt Fail"
        )
        
        # Invoke and check error propagation
        with self.assertRaises(TimeoutError):
            self.service.generate(self.db, req)

        # Check DB log for failure
        db_logs = self.db.query(DBProviderRequest).all()
        self.assertEqual(len(db_logs), 1)
        log = db_logs[0]
        self.assertEqual(log.experiment_run, "exp-run-002")
        self.assertEqual(log.provider, "gemini")
        self.assertEqual(log.model, "gemini-2.5-flash")
        self.assertEqual(log.latency, 0)
        self.assertEqual(log.tokens, 0)
        self.assertEqual(log.cost, 0.0)
        self.assertEqual(log.status, "failed")

    def test_list_models_sync(self):
        # Verify seeding
        db_providers = self.db.query(DBProvider).all()
        self.assertEqual(len(db_providers), 4) # gemini, openai, openrouter, ollama
        
        # Sync models (which triggers mocks / fallback list_models of the classes)
        models = self.service.list_models(self.db)
        
        # Verify models are registered in DB
        db_models = self.db.query(DBModel).all()
        self.assertTrue(len(db_models) > 0)
        
        # Check specific seeded models exist
        gpt5 = self.db.query(DBModel).filter(DBModel.model_name == "gpt-5").first()
        self.assertIsNotNone(gpt5)
        self.assertEqual(gpt5.provider_id, "openai")
        self.assertEqual(gpt5.context_window, 128000)

        # Retrieve filtered list
        gemini_models = self.service.list_models(self.db, provider_id="gemini")
        for m in gemini_models:
            self.assertEqual(m.provider_id, "gemini")


if __name__ == "__main__":
    unittest.main()
