class ProviderError(Exception):
    """Base exception for all provider operations."""
    pass

class AuthenticationError(ProviderError):
    """Raised when authentication (API key, token, etc.) fails."""
    pass

class InvalidModelError(ProviderError):
    """Raised when a model is not found or unsupported by the provider."""
    pass

class NetworkError(ProviderError):
    """Raised when network failures or remote servers are unreachable."""
    pass

class TimeoutError(ProviderError):
    """Raised when a request to the provider times out."""
    pass

class ProviderUnavailableError(ProviderError):
    """Raised when the provider service is unavailable (e.g. 503, rate limited)."""
    pass

class ContextLengthExceededError(ProviderError):
    """Raised when the input context exceeds the model's limits."""
    pass

class ConfigurationError(ProviderError):
    """Raised when there is a configuration error (e.g. missing API keys)."""
    pass
