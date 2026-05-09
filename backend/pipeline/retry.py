import time
import logging
import functools
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


def retry(max_attempts: int = 3, delay_sec: float = 30.0, exceptions: tuple = (Exception,)):
    """Decorator: retry up to max_attempts times with delay_sec between attempts."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        logger.warning(
                            "[retry] %s attempt %d/%d failed: %s — retrying in %.0fs",
                            func.__name__, attempt, max_attempts, exc, delay_sec,
                        )
                        time.sleep(delay_sec)
                    else:
                        logger.error(
                            "[retry] %s exhausted %d attempts. Last error: %s",
                            func.__name__, max_attempts, exc,
                        )
            raise last_exc  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator
