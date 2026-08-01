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
    ProviderError,
    ProviderUnavailableError,
    ContextLengthExceededError
)
from backend.providers.tokenizer import Tokenizer

class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def _get_client(self):
        if not self.api_key:
            raise AuthenticationError("OPENAI_API_KEY environment variable is not set.")
        try:
            from openai import OpenAI
            return OpenAI(api_key=self.api_key)
        except ImportError:
            raise ProviderError("openai SDK is not installed. Run `pip install openai`.")
        except Exception as e:
            raise ProviderError(f"Failed to initialize OpenAI Client: {e}")

    def generate(self, request: LLMRequest, timeout: int = 120) -> LLMResponse:
        client = self._get_client()
        
        cfg = request.generation_config or GenerationConfig()
        config_kwargs = {}
        if cfg.temperature is not None:
            config_kwargs["temperature"] = cfg.temperature
        if cfg.top_p is not None:
            config_kwargs["top_p"] = cfg.top_p
        if cfg.max_tokens is not None:
            config_kwargs["max_tokens"] = cfg.max_tokens
        if cfg.seed is not None:
            config_kwargs["seed"] = cfg.seed

        request_timestamp = datetime.datetime.utcnow()
        start_time = time.time()
        
        try:
            response = client.chat.completions.create(
                model=request.model,
                messages=[{"role": "user", "content": request.prompt}],
                timeout=timeout,
                **config_kwargs
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            response_timestamp = datetime.datetime.utcnow()
            
            response_text = response.choices[0].message.content or ""
            
            # Extract tokens
            input_tokens = 0
            output_tokens = 0
            if response.usage:
                input_tokens = response.usage.prompt_tokens or 0
                output_tokens = response.usage.completion_tokens or 0
                
            if input_tokens == 0 or output_tokens == 0:
                input_tokens = Tokenizer.estimate_tokens(request.prompt, request.model)
                output_tokens = Tokenizer.estimate_tokens(response_text, request.model)
                
            total_tokens = input_tokens + output_tokens
            finish_reason = response.choices[0].finish_reason
            
            return LLMResponse(
                provider="openai",
                model=request.model,
                response_text=response_text,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost=0.0,
                finish_reason=finish_reason,
                request_timestamp=request_timestamp,
                response_timestamp=response_timestamp,
                status="success"
            )
            
        except Exception as e:
            err_msg = str(e)
            import openai
            if isinstance(e, openai.AuthenticationError):
                raise AuthenticationError(f"OpenAI authentication failed: {e}")
            elif isinstance(e, openai.NotFoundError) or "model_not_found" in err_msg:
                raise InvalidModelError(f"OpenAI model '{request.model}' not found: {e}")
            elif isinstance(e, openai.APITimeoutError):
                raise TimeoutError(f"OpenAI request timed out: {e}")
            elif isinstance(e, openai.RateLimitError):
                raise ProviderUnavailableError(f"OpenAI rate limit exceeded: {e}")
            elif "context_length_exceeded" in err_msg or "maximum context length" in err_msg.lower():
                raise ContextLengthExceededError(f"OpenAI context length exceeded: {e}")
            elif isinstance(e, openai.APIConnectionError):
                raise NetworkError(f"OpenAI connection error: {e}")
            else:
                raise ProviderError(f"OpenAI execution error: {e}")

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "model_name": "gpt-5",
                "context_window": 128000,
                "supports_seed": True,
                "supports_temperature": True,
                "supports_top_p": True,
                "supports_json_mode": True,
                "status": "active"
            },
            {
                "model_name": "gpt-5-mini",
                "context_window": 128000,
                "supports_seed": True,
                "supports_temperature": True,
                "supports_top_p": True,
                "supports_json_mode": True,
                "status": "active"
            }
        ]

    def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            client = self._get_client()
            client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                timeout=5
            )
            return True
        except Exception:
            return False
