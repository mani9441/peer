import os
import time
import datetime
from typing import List, Dict, Any, Optional
from backend.providers.base import BaseProvider
from backend.providers.schemas import LLMRequest, LLMResponse, GenerationConfig
from backend.providers.exceptions import (
    AuthenticationError,
    InvalidModelError,
    NetworkError,
    TimeoutError,
    ProviderError
)
from backend.providers.tokenizer import Tokenizer

class OllamaProvider(BaseProvider):
    def __init__(self, api_base: Optional[str] = None):
        self.api_base = api_base or os.environ.get("OLLAMA_HOST") or "http://localhost:11434"

    def _get_client(self):
        try:
            import ollama
            return ollama.Client(host=self.api_base)
        except ImportError:
            raise ProviderError("ollama package is not installed. Run `pip install ollama`.")
        except Exception as e:
            raise ProviderError(f"Failed to initialize Ollama Client: {e}")

    def generate(self, request: LLMRequest, timeout: int = 120) -> LLMResponse:
        client = self._get_client()
        
        cfg = request.generation_config or GenerationConfig()
        options = {}
        if cfg.temperature is not None:
            options["temperature"] = cfg.temperature
        if cfg.top_p is not None:
            options["top_p"] = cfg.top_p
        if cfg.max_tokens is not None:
            options["num_predict"] = cfg.max_tokens
        if cfg.seed is not None:
            options["seed"] = cfg.seed

        request_timestamp = datetime.datetime.utcnow()
        start_time = time.time()
        
        try:
            # Execute chat completion
            response = client.chat(
                model=request.model,
                messages=[{"role": "user", "content": request.prompt}],
                options=options,
                think=False
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            response_timestamp = datetime.datetime.utcnow()
            
            response_text = response.get("message", {}).get("content", "") or ""
            
            # Extract tokens
            input_tokens = response.get("prompt_eval_count", 0)
            output_tokens = response.get("eval_count", 0)
            
            if input_tokens == 0 or output_tokens == 0:
                input_tokens = Tokenizer.estimate_tokens(request.prompt, request.model)
                output_tokens = Tokenizer.estimate_tokens(response_text, request.model)
                
            total_tokens = input_tokens + output_tokens
            
            return LLMResponse(
                provider="ollama",
                model=request.model,
                response_text=response_text,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost=0.0,
                finish_reason="stop",
                request_timestamp=request_timestamp,
                response_timestamp=response_timestamp,
                status="success"
            )
            
        except Exception as e:
            err_msg = str(e)
            import ollama
            if isinstance(e, ollama.ResponseError):
                if e.status_code == 404:
                    raise InvalidModelError(f"Ollama model '{request.model}' not found: {e}")
                else:
                    raise ProviderError(f"Ollama response error: {e}")
            elif "connection" in err_msg.lower() or "conn" in err_msg.lower():
                raise NetworkError(f"Failed to connect to Ollama service at {self.api_base}: {e}")
            else:
                raise ProviderError(f"Ollama unexpected error: {e}")

    def list_models(self) -> List[Dict[str, Any]]:
        try:
            client = self._get_client()
            models_response = client.list()
            
            models = []
            models_list = []
            if isinstance(models_response, dict):
                models_list = models_response.get("models", [])
            elif hasattr(models_response, "models"):
                models_list = models_response.models
                
            for m in models_list:
                m_name = None
                if isinstance(m, dict):
                    m_name = m.get("name")
                elif hasattr(m, "name"):
                    m_name = m.name
                elif hasattr(m, "model"):
                    m_name = m.model
                    
                if m_name:
                    models.append({
                        "model_name": m_name,
                        "context_window": 4096,
                        "supports_seed": True,
                        "supports_temperature": True,
                        "supports_top_p": True,
                        "supports_json_mode": True,
                        "status": "active"
                    })
            return models
        except Exception:
            return [
                {
                    "model_name": "llama3.1:latest",
                    "context_window": 8192,
                    "supports_seed": True,
                    "supports_temperature": True,
                    "supports_top_p": True,
                    "supports_json_mode": True,
                    "status": "active"
                }
            ]

    def health_check(self) -> bool:
        try:
            client = self._get_client()
            client.list()
            return True
        except Exception:
            return False
