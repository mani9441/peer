from backend.providers.schemas import LLMRequest
from backend.providers.exceptions import ConfigurationError

class RequestValidator:
    @staticmethod
    def validate_request(request: LLMRequest) -> None:
        if not request.provider or not request.provider.strip():
            raise ConfigurationError("Provider must be specified.")
        if not request.model or not request.model.strip():
            raise ConfigurationError("Model name must be specified.")
        if not request.prompt or not request.prompt.strip():
            raise ConfigurationError("Prompt content must be specified and not empty.")
            
        config = request.generation_config
        if config:
            if config.temperature is not None:
                if not (0.0 <= config.temperature <= 2.0):
                    raise ConfigurationError("temperature must be between 0.0 and 2.0.")
            if config.top_p is not None:
                if not (0.0 <= config.top_p <= 1.0):
                    raise ConfigurationError("top_p must be between 0.0 and 1.0.")
            if config.max_tokens is not None:
                if config.max_tokens <= 0:
                    raise ConfigurationError("max_tokens must be a positive integer.")
            if config.seed is not None:
                if not isinstance(config.seed, int):
                    raise ConfigurationError("seed must be an integer.")
