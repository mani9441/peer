import uuid
import time
from typing import Callable, Tuple, Any

def generate_uuid(prefix: str = "") -> str:
    """Generates a standard UUID string, optionally prefixed."""
    suffix = str(uuid.uuid4())[:8]
    if prefix:
        return f"{prefix}_{suffix}"
    return suffix

def measure_execution_time(func: Callable[..., Any], *args, **kwargs) -> Tuple[Any, float]:
    """
    Executes a callable, measuring the execution time in milliseconds.
    Returns (result, duration_ms).
    """
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    duration_ms = (time.perf_counter() - start_time) * 1000
    return result, duration_ms
