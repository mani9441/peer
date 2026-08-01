import time
import logging
from typing import Callable, Any, Type, Tuple
from backend.providers.exceptions import (
    TimeoutError,
    NetworkError,
    ProviderUnavailableError
)

logger = logging.getLogger(__name__)

class RetryHandler:
    @staticmethod
    def execute_with_retry(
        func: Callable[..., Any],
        max_retries: int = 3,
        initial_backoff: float = 2.0,
        backoff_factor: float = 2.0,
        retryable_exceptions: Tuple[Type[Exception], ...] = (
            TimeoutError,
            NetworkError,
            ProviderUnavailableError
        ),
        *args,
        **kwargs
    ) -> Any:
        """
        Executes a callable, retrying on transient errors with exponential backoff.
        Retries up to max_retries times.
        Example backoff: 2s, 4s, 8s.
        """
        backoff = initial_backoff
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                is_retryable = False
                for ex_type in retryable_exceptions:
                    if isinstance(e, ex_type):
                        is_retryable = True
                        break
                        
                if not is_retryable:
                    raise e
                    
                last_exception = e
                if attempt == max_retries:
                    logger.error(f"Request failed after {max_retries} retries. Raising: {e}")
                    raise e
                    
                logger.warning(
                    f"Transient error encountered (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {backoff} seconds..."
                )
                time.sleep(backoff)
                backoff *= backoff_factor
                
        if last_exception:
            raise last_exception
