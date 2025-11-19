import time
import random
from functools import wraps


class CircuitBreakerError(Exception):
    pass


def circuit_breaker(max_failures: int = 5, timeout: int = 60):
    """Circuit breaker pattern for resilient operations (sync only)."""

    def decorator(func):
        failures = 0
        last_failure_time = 0
        state = "CLOSED"

        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal failures, last_failure_time, state

            if state == "OPEN":
                if time.time() - last_failure_time > timeout:
                    state = "HALF_OPEN"
                else:
                    raise CircuitBreakerError("Service unavailable")

            try:
                result = func(*args, **kwargs)
                if state == "HALF_OPEN":
                    state = "CLOSED"
                    failures = 0
                return result
            except Exception:
                failures += 1
                last_failure_time = time.time()

                if failures >= max_failures:
                    state = "OPEN"

                raise

        return wrapper

    return decorator


class RetryMechanism:
    """Retry decorator with exponential backoff (sync)."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(self.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == self.max_retries:
                        break

                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    time.sleep(delay)

            raise last_exception

        return wrapper
