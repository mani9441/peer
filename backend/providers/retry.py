import time
import logging
import re
from typing import Callable, Any, Type, Tuple, Optional
from backend.providers.exceptions import (
    TimeoutError,
    NetworkError,
    ProviderUnavailableError
)

logger = logging.getLogger(__name__)

def parse_retry_delay(e: Exception) -> Optional[float]:
    """
    Parses retry delay (in seconds) from headers or message of an exception.
    """
    try:
        if hasattr(e, "headers") and e.headers and "retry-after" in e.headers:
            return float(e.headers["retry-after"])
        if hasattr(e, "response") and e.response and hasattr(e.response, "headers") and e.response.headers:
            if "retry-after" in e.response.headers:
                return float(e.response.headers["retry-after"])
    except Exception:
        pass
    
    try:
        if hasattr(e, "retry_after") and e.retry_after is not None:
            return float(e.retry_after)
    except Exception:
        pass

    msg = str(e).lower()
    # Look for patterns like "retry after 32 seconds", "retry in 32s", "try again in 32 seconds"
    patterns = [
        r"retry after (\d+)\s*seconds",
        r"retry after (\d+)\s*s",
        r"retry in (\d+)\s*seconds",
        r"retry in (\d+)\s*s",
        r"try again in (\d+)\s*seconds",
        r"try again in (\d+)\s*s",
        r"limit.*try again in (\d+)",
        r"limit.*after (\d+)"
    ]
    for pattern in patterns:
        m = re.search(pattern, msg)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None

def is_transient_error(e: Exception) -> bool:
    """
    Returns True if the exception represents a transient failure that should be retried.
    """
    if isinstance(e, (TimeoutError, NetworkError)):
        return True
        
    msg = str(e).lower()
    # Check for transient codes and messages
    if "503" in msg or "502" in msg or "504" in msg or "connection reset" in msg or "connection refused" in msg or "read timeout" in msg:
        return True
        
    return False

class RetryHandler:
    @staticmethod
    def execute_with_retry(
        func: Callable[..., Any],
        max_retries: int = 3,
        initial_backoff: float = 2.0,
        backoff_factor: float = 2.0,
        *args,
        **kwargs
    ) -> Any:
        """
        Executes a callable, retrying on transient errors with exponential backoff.
        Non-transient errors are raised immediately.
        Rate limits (429) are retried ONLY if a retry delay is provided by the server.
        """
        backoff = initial_backoff
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                msg = str(e).lower()
                retry_delay = parse_retry_delay(e)
                is_rate_limit = "429" in msg or "quota" in msg or "resourceexhausted" in msg or "rate limit" in msg or "resource_exhausted" in msg
                
                # Check retry eligibility
                should_retry = False
                backoff_time = backoff
                
                if is_transient_error(e):
                    should_retry = True
                elif is_rate_limit and retry_delay is not None:
                    should_retry = True
                    backoff_time = retry_delay
                    
                if not should_retry:
                    raise e
                    
                last_exception = e
                if attempt == max_retries:
                    logger.error(f"Request failed after {max_retries} retries. Raising: {e}")
                    raise e
                    
                logger.warning(
                    f"Retryable error encountered (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {backoff_time} seconds..."
                )
                time.sleep(backoff_time)
                
                # Only scale the backoff if we didn't use a specific server-provided delay
                if retry_delay is None:
                    backoff *= backoff_factor
                
        if last_exception:
            raise last_exception
