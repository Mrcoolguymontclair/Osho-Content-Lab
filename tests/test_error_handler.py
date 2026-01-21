"""
Unit tests for error_handler module
"""

import pytest
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from error_handler import (
    retry_with_backoff,
    handle_errors,
    CircuitBreaker,
    ErrorCategory,
    ErrorSeverity,
    CircuitBreakerOpen
)


class TestRetryDecorator:
    """Test retry decorator."""

    def test_retry_succeeds_eventually(self):
        """Test that retry eventually succeeds."""
        attempt_count = [0]

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def flaky_function():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert attempt_count[0] == 2

    def test_retry_fails_after_max_attempts(self):
        """Test that retry fails after max attempts."""
        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            always_fails()

    def test_retry_with_specific_exceptions(self):
        """Test retry only catches specified exceptions."""
        @retry_with_backoff(max_attempts=3, base_delay=0.01, exceptions=(ValueError,))
        def raises_type_error():
            raise TypeError("Different error")

        # Should not retry TypeError
        with pytest.raises(TypeError):
            raises_type_error()


class TestHandleErrorsDecorator:
    """Test handle_errors decorator."""

    def test_handle_errors_raises_by_default(self):
        """Test that errors are raised by default."""
        @handle_errors(category=ErrorCategory.UNKNOWN)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

    def test_handle_errors_suppresses_when_configured(self):
        """Test that errors can be suppressed."""
        @handle_errors(
            category=ErrorCategory.UNKNOWN,
            raise_on_error=False,
            default_return="error handled"
        )
        def failing_function():
            raise ValueError("Test error")

        result = failing_function()
        assert result == "error handled"


class TestCircuitBreaker:
    """Test circuit breaker."""

    def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

        def failing_function():
            raise ValueError("Fails")

        # Fail 3 times
        for _ in range(3):
            with pytest.raises(ValueError):
                breaker.call(failing_function)

        # Circuit should be open now
        with pytest.raises(CircuitBreakerOpen):
            breaker.call(failing_function)

    def test_circuit_breaker_recovers(self):
        """Test that circuit breaker recovers after timeout."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5)

        def failing_function():
            raise ValueError("Fails")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_function)

        # Should be open
        with pytest.raises(CircuitBreakerOpen):
            breaker.call(failing_function)

        # Wait for recovery timeout
        time.sleep(0.6)

        # Should enter half-open state and allow one attempt
        with pytest.raises(ValueError):
            breaker.call(failing_function)

    def test_circuit_breaker_closes_on_success(self):
        """Test that circuit closes after successful call."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5)

        def sometimes_succeeds(should_fail):
            if should_fail:
                raise ValueError("Fails")
            return "success"

        # Fail once
        with pytest.raises(ValueError):
            breaker.call(sometimes_succeeds, True)

        # Succeed
        result = breaker.call(sometimes_succeeds, False)
        assert result == "success"
        assert breaker.failure_count == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
