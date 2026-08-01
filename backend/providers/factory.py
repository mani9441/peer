from typing import Optional
from backend.providers.registry import ProviderRegistry
from backend.providers.base import BaseProvider

class ProviderFactory:
    def __init__(self, registry: Optional[ProviderRegistry] = None):
        self.registry = registry or ProviderRegistry()

    def get_provider(self, provider_name: str, api_key: Optional[str] = None, api_base: Optional[str] = None) -> BaseProvider:
        """
        Instantiates and returns the appropriate BaseProvider instance.
        """
        provider_class = self.registry.get_provider_class(provider_name)
        
        # Instantiate with provider-specific parameters
        if provider_name.lower() == "ollama":
            return provider_class(api_base=api_base)
        else:
            return provider_class(api_key=api_key)
