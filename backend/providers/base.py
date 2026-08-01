from abc import ABC, abstractmethod
from typing import List, Dict, Any
from backend.providers.schemas import LLMRequest, LLMResponse

class BaseProvider(ABC):
    
    @abstractmethod
    def generate(self, request: LLMRequest, timeout: int = 120) -> LLMResponse:
        """
        Executes a prompt generation request synchronously.
        Must raise a subclass of ProviderError on failure.
        """
        pass

    @abstractmethod
    def list_models(self) -> List[Dict[str, Any]]:
        """
        Retrieves available models and metadata for this provider.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Verifies if the provider credentials and endpoint are working.
        """
        pass
