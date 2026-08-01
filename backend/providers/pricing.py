import os
import json
from typing import Dict, Any, Optional

class PricingManager:
    def __init__(self, pricing_cache_path: Optional[str] = None):
        if pricing_cache_path is None:
            pricing_cache_path = os.path.join(os.path.dirname(__file__), "pricing.json")
        self.pricing_cache_path = pricing_cache_path
        self.pricing_data = self._load_pricing()

    def _load_pricing(self) -> Dict[str, Any]:
        if os.path.exists(self.pricing_cache_path):
            try:
                with open(self.pricing_cache_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default fallback pricing if config is missing or corrupted
        default_pricing = {
            "gemini": {
                "gemini-2.5-flash": {
                    "input_price": 0.075 / 1_000_000,
                    "output_price": 0.30 / 1_000_000
                },
                "gemini-2.5-pro": {
                    "input_price": 1.25 / 1_000_000,
                    "output_price": 5.00 / 1_000_000
                },
                "default": {
                    "input_price": 0.075 / 1_000_000,
                    "output_price": 0.30 / 1_000_000
                }
            },
            "openai": {
                "gpt-5": {
                    "input_price": 5.00 / 1_000_000,
                    "output_price": 15.00 / 1_000_000
                },
                "gpt-5-mini": {
                    "input_price": 0.15 / 1_000_000,
                    "output_price": 0.60 / 1_000_000
                },
                "default": {
                    "input_price": 0.15 / 1_000_000,
                    "output_price": 0.60 / 1_000_000
                }
            },
            "openrouter": {
                "default": {
                    "input_price": 1.00 / 1_000_000,
                    "output_price": 3.00 / 1_000_000
                }
            },
            "ollama": {
                "default": {
                    "input_price": 0.0,
                    "output_price": 0.0
                }
            }
        }
        self._save_pricing(default_pricing)
        return default_pricing

    def _save_pricing(self, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.pricing_cache_path), exist_ok=True)
        try:
            with open(self.pricing_cache_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def get_pricing(self, provider: str, model: str) -> Dict[str, float]:
        """Returns input_price and output_price per token."""
        provider = provider.lower()
        model = model.lower()
        
        p_pricing = self.pricing_data.get(provider, {})
        
        # Check for model match
        if model in p_pricing:
            return p_pricing[model]
            
        # Check if there is a generic match where the model matches a key partially
        for k, v in p_pricing.items():
            if k != "default" and k in model:
                return v

        # Check for provider default fallback
        if "default" in p_pricing:
            return p_pricing["default"]
            
        # Global fallback
        return {"input_price": 0.0, "output_price": 0.0}

    def calculate_price(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = self.get_pricing(provider, model)
        cost = (input_tokens * pricing.get("input_price", 0.0)) + (output_tokens * pricing.get("output_price", 0.0))
        return float(cost)
