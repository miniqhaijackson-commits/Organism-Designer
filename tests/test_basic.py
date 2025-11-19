import time

from jarvis.security import sanitize_input, EnterpriseSecurity
from jarvis.resource_manager import ResourceManager
from jarvis.resilience import RetryMechanism, circuit_breaker, CircuitBreakerError


def test_sanitize_input_blocks_rm():
    s = sanitize_input('please run rm -rf /')
    assert 'rm -rf' not in s.lower()


def test_validate_command_safety_whitelist():
    es = EnterpriseSecurity()
    ok, msg = es.validate_command_safety('hello')
    assert ok is True


def test_resource_manager_context():
    rm = ResourceManager()

    class Dummy:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    with rm.managed_resource('d', Dummy) as d:
        assert hasattr(d, 'close')

    # After exit the resource id should not be present
    assert 'd' not in rm._resources


def test_retry_and_circuit_breaker():
    calls = []

    @RetryMechanism(max_retries=2, base_delay=0.01)
    @circuit_breaker(max_failures=2, timeout=1)
    def flaky():
        calls.append(1)
        raise ValueError('fail')

    try:
        flaky()
    except Exception:
        pass

    # second call should either raise CircuitBreakerError or still raise ValueError
    try:
        flaky()
        assert False, "Should have raised"
    except Exception as e:
        assert isinstance(e, (CircuitBreakerError, ValueError))
