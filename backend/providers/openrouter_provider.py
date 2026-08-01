import os
import time
import datetime
from typing import List, Dict, Any, Optional
import requests
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

class OpenRouterProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.api_base = "https://openrouter.ai/api/v1"

    def generate(self, request: LLMRequest, timeout: int = 120) -> LLMResponse:
        if not self.api_key:
            raise AuthenticationError("OPENROUTER_API_KEY environment variable is not set.")
            
        cfg = request.generation_config or GenerationConfig()
        
        payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}]
        }
        
        if cfg.temperature is not None:
            payload["temperature"] = cfg.temperature
        if cfg.top_p is not None:
            payload["top_p"] = cfg.top_p
        if cfg.max_tokens is not None:
            payload["max_tokens"] = cfg.max_tokens
        if cfg.seed is not None:
            payload["seed"] = cfg.seed

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://peer-framework.ai",
            "X-Title": "PEER Framework"
        }
        
        request_timestamp = datetime.datetime.utcnow()
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            response_timestamp = datetime.datetime.utcnow()
            
            if response.status_code == 401:
                raise AuthenticationError(f"OpenRouter authentication failed: {response.text}")
            elif response.status_code == 404:
                raise InvalidModelError(f"OpenRouter model '{request.model}' not found: {response.text}")
            elif response.status_code == 429:
                raise ProviderUnavailableError(f"OpenRouter rate limit exceeded: {response.text}")
            elif response.status_code in (408, 504):
                raise TimeoutError(f"OpenRouter request timed out: {response.text}")
            elif response.status_code >= 500:
                raise ProviderUnavailableError(f"OpenRouter temporary server error: {response.text}")
            elif response.status_code != 200:
                raise ProviderError(f"OpenRouter API error {response.status_code}: {response.text}")
                
            res_json = response.json()
            if "error" in res_json:
                err_data = res_json["error"]
                err_code = err_data.get("code")
                err_msg = err_data.get("message", "")
                if err_code == 401:
                    raise AuthenticationError(f"OpenRouter authentication failed: {err_msg}")
                elif err_code == 404:
                    raise InvalidModelError(f"OpenRouter model '{request.model}' not found: {err_msg}")
                elif "context" in err_msg.lower() or "length" in err_msg.lower():
                    raise ContextLengthExceededError(f"OpenRouter context length exceeded: {err_msg}")
                else:
                    raise ProviderError(f"OpenRouter API returned error: {err_msg}")

            choices = res_json.get("choices", [])
            if not choices:
                raise ProviderError(f"OpenRouter response contained no choices: {res_json}")
                
            response_text = choices[0].get("message", {}).get("content", "") or ""
            finish_reason = choices[0].get("finish_reason")
            
            usage = res_json.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            if input_tokens == 0 or output_tokens == 0:
                input_tokens = Tokenizer.estimate_tokens(request.prompt, request.model)
                output_tokens = Tokenizer.estimate_tokens(response_text, request.model)
                
            total_tokens = input_tokens + output_tokens
            
            return LLMResponse(
                provider="openrouter",
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
            
        except requests.exceptions.Timeout:
            raise TimeoutError("OpenRouter request timed out.")
        except requests.exceptions.ConnectionError:
            raise NetworkError("OpenRouter connection failure.")
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"OpenRouter unexpected exception: {e}")

    def list_models(self) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.api_base}/models", timeout=5)
            if response.status_code == 200:
                res_data = response.json()
                models = res_data.get("data", [])
                result = []
                for m in models:
                    result.append({
                        "model_name": m.get("id"),
                        "context_window": m.get("context_length", 4096),
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
            
        # Static fallback list
        return [
            {
                "model_name": "meta-llama/llama-3.1-8b-instruct:free",
                "context_window": 128000,
                "supports_seed": True,
                "supports_temperature": True,
                "supports_top_p": True,
                "supports_json_mode": True,
                "status": "active"
            },
            {
                "model_name": "google/gemini-2.5-flash",
                "context_window": 1000000,
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
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.api_base}/auth/key", headers=headers, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
