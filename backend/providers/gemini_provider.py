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
    ProviderUnavailableError
)
from backend.providers.tokenizer import Tokenizer

class GeminiProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def _get_client(self):
        if not self.api_key:
            raise AuthenticationError("GEMINI_API_KEY environment variable is not set.")
        try:
            from google import genai
            return genai.Client(api_key=self.api_key)
        except ImportError:
            raise ProviderError("google-genai SDK is not installed. Run `pip install google-genai`.")
        except Exception as e:
            raise ProviderError(f"Failed to initialize Gemini Client: {e}")

    def generate(self, request: LLMRequest, timeout: int = 120) -> LLMResponse:
        client = self._get_client()
        from google.genai import types
        
        cfg = request.generation_config or GenerationConfig()
        config_kwargs = {}
        if cfg.temperature is not None:
            config_kwargs["temperature"] = cfg.temperature
        if cfg.top_p is not None:
            config_kwargs["top_p"] = cfg.top_p
        if cfg.max_tokens is not None:
            config_kwargs["max_output_tokens"] = cfg.max_tokens
        if cfg.seed is not None:
            # Note: google-genai sdk supports seed parameter under types.GenerateContentConfig
            config_kwargs["seed"] = cfg.seed

        gen_config = types.GenerateContentConfig(**config_kwargs)
        
        request_timestamp = datetime.datetime.utcnow()
        start_time = time.time()
        
        try:
            # Apply request options timeout if class types.HttpOptions exists
            request_options = None
            if hasattr(types, "HttpOptions"):
                request_options = types.HttpOptions(timeout=timeout)
            elif hasattr(types, "HttpRequestOptions"):
                request_options = types.HttpRequestOptions(timeout=f"{timeout}s")
                
            response = client.models.generate_content(
                model=request.model,
                contents=request.prompt,
                config=gen_config,
                request_options=request_options
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            response_timestamp = datetime.datetime.utcnow()
            
            response_text = response.text or ""
            
            # Extract token counts
            input_tokens = 0
            output_tokens = 0
            if response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0
                
            if input_tokens == 0 or output_tokens == 0:
                input_tokens = Tokenizer.estimate_tokens(request.prompt, request.model)
                output_tokens = Tokenizer.estimate_tokens(response_text, request.model)
                
            total_tokens = input_tokens + output_tokens
            
            # Finish reason
            finish_reason = None
            if response.candidates and len(response.candidates) > 0:
                finish_reason = str(response.candidates[0].finish_reason)
                
            return LLMResponse(
                provider="gemini",
                model=request.model,
                response_text=response_text,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost=0.0,  # calculated downstream
                finish_reason=finish_reason,
                request_timestamp=request_timestamp,
                response_timestamp=response_timestamp,
                status="success"
            )
            
        except Exception as e:
            err_msg = str(e)
            if "API key" in err_msg or "401" in err_msg or "UNAUTHENTICATED" in err_msg:
                raise AuthenticationError(f"Gemini authentication failed: {e}")
            elif "404" in err_msg or "not found" in err_msg.lower():
                raise InvalidModelError(f"Gemini model '{request.model}' not found: {e}")
            elif "429" in err_msg or "quota" in err_msg.lower() or "ResourceExhausted" in err_msg:
                raise ProviderUnavailableError(f"Gemini quota/rate limit exceeded: {e}")
            elif "deadline" in err_msg.lower() or "timeout" in err_msg.lower():
                raise TimeoutError(f"Gemini request timed out: {e}")
            else:
                raise NetworkError(f"Gemini connection error: {e}")

    def list_models(self) -> List[Dict[str, Any]]:
        # Fallback static list
        fallback = [
            {
                "model_name": "gemini-2.0-flash",
                "context_window": 1048576,
                "supports_seed": True,
                "supports_temperature": True,
                "supports_top_p": True,
                "supports_json_mode": True,
                "status": "active"
            },
            {
                "model_name": "gemini-1.5-flash",
                "context_window": 1048576,
                "supports_seed": True,
                "supports_temperature": True,
                "supports_top_p": True,
                "supports_json_mode": True,
                "status": "active"
            },
            {
                "model_name": "gemini-1.5-pro",
                "context_window": 2097152,
                "supports_seed": True,
                "supports_temperature": True,
                "supports_top_p": True,
                "supports_json_mode": True,
                "status": "active"
            }
        ]
        if not self.api_key:
            return fallback
        try:
            client = self._get_client()
            models_list = list(client.models.list())
            result = []
            for m in models_list:
                # Include models supporting text generation
                actions = getattr(m, "supported_actions", []) or []
                if "generateContent" in actions or "generate_content" in actions:
                    name = m.name.replace("models/", "")
                    # Skip retired/unavailable models to keep selection clean
                    if "gemini-2.5-flash" in name:
                        continue
                    result.append({
                        "model_name": name,
                        "context_window": getattr(m, "input_token_limit", 1048576) or 1048576,
                        "supports_seed": True,
                        "supports_temperature": True,
                        "supports_top_p": True,
                        "supports_json_mode": True,
                        "status": "active"
                    })
            if result:
                return result
        except Exception:
            pass
        return fallback

    def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            client = self._get_client()
            # Calling models.list() validates the API key without depleting generation quota
            list(client.models.list())
            return True
        except Exception:
            return False
