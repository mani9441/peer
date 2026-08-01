from typing import Dict, Type
from backend.providers.base import BaseProvider
from backend.providers.gemini_provider import GeminiProvider
from backend.providers.openai_provider import OpenAIProvider
from backend.providers.openrouter_provider import OpenRouterProvider
from backend.providers.ollama_provider import OllamaProvider
from backend.providers.exceptions import ConfigurationError

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, Type[BaseProvider]] = {
            "gemini": GeminiProvider,
            "openai": OpenAIProvider,
            "openrouter": OpenRouterProvider,
            "ollama": OllamaProvider
        }

    def register_provider(self, name: str, provider_class: Type[BaseProvider]) -> None:
        """Register a new provider implementation."""
        self._providers[name.lower()] = provider_class

    def get_provider_class(self, name: str) -> Type[BaseProvider]:
        """Look up provider implementation class."""
        name_lower = name.lower()
        if name_lower not in self._providers:
            raise ConfigurationError(f"Unsupported provider: '{name}'. Supported: {list(self._providers.keys())}")
        return self._providers[name_lower]
