"""
Standardized Error Handling

Provides consistent error handling patterns across the application.

Features:
- Retry logic with exponential backoff
- Circuit breaker pattern
- Error categorization
- Structured error logging
- Recovery strategies
"""

import time
import functools
from typing import Callable, Optional, Any, Type, Tuple
from enum import Enum
from logger import get_logger
from constants import (
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BASE_DELAY,
    MAX_RETRY_DELAY,
    MAX_CONSECUTIVE_ERRORS
)

logger = get_logger(__name__)


class ErrorCategory(Enum):
    """Error categories for classification."""
    NETWORK = "network"
    API = "api"
    FILE_IO = "file_io"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RetryableError(Exception):
    """Base class for errors that should trigger retry."""
    pass


class NonRetryableError(Exception):
    """Base class for errors that should not trigger retry."""
    pass


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents repeated calls to failing operations.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting to close circuit
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'half_open'
                logger.info("Circuit breaker entering half-open state")
            else:
                raise CircuitBreakerOpen("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        if self.state == 'half_open':
            self.state = 'closed'
            logger.info("Circuit breaker closed")
        self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


def retry_with_backoff(
    max_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    max_delay: float = MAX_RETRY_DELAY,
    exponential: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential: If True, use exponential backoff
        exceptions: Tuple of exception types to catch
        on_retry: Optional callback function called on each retry

    Example:
        @retry_with_backoff(max_attempts=3, base_delay=1)
        def unreliable_function():
            # Code that might fail
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}",
                            exc_info=True
                        )
                        raise

                    # Calculate delay
                    if exponential:
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    else:
                        delay = base_delay

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {delay}s..."
                    )

                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt, e)
                        except Exception as callback_error:
                            logger.error(f"Retry callback failed: {callback_error}")

                    time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


def handle_errors(
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    raise_on_error: bool = True,
    default_return: Any = None,
    log_errors: bool = True
):
    """
    Decorator for standardized error handling.

    Args:
        category: Error category for classification
        severity: Error severity level
        raise_on_error: If False, return default_return instead of raising
        default_return: Value to return when error is suppressed
        log_errors: Whether to log errors

    Example:
        @handle_errors(category=ErrorCategory.API, severity=ErrorSeverity.HIGH)
        def api_call():
            # Code that might fail
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    log_level = {
                        ErrorSeverity.LOW: logger.info,
                        ErrorSeverity.MEDIUM: logger.warning,
                        ErrorSeverity.HIGH: logger.error,
                        ErrorSeverity.CRITICAL: logger.critical
                    }.get(severity, logger.error)

                    log_level(
                        f"Error in {func.__name__} "
                        f"[{category.value}/{severity.value}]: {e}",
                        exc_info=True
                    )

                if raise_on_error:
                    raise
                else:
                    return default_return

        return wrapper
    return decorator


class ErrorRecovery:
    """Helper class for error recovery strategies."""

    @staticmethod
    def with_fallback(
        primary_func: Callable,
        fallback_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Try primary function, use fallback on error.

        Args:
            primary_func: Primary function to try
            fallback_func: Fallback function if primary fails
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Result from primary or fallback function
        """
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(
                f"Primary function {primary_func.__name__} failed: {e}. "
                f"Using fallback {fallback_func.__name__}"
            )
            return fallback_func(*args, **kwargs)

    @staticmethod
    def retry_with_recovery(
        func: Callable,
        recovery_func: Optional[Callable] = None,
        max_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        *args,
        **kwargs
    ) -> Any:
        """
        Retry function with recovery between attempts.

        Args:
            func: Function to retry
            recovery_func: Optional recovery function to run between retries
            max_attempts: Maximum retry attempts
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt}/{max_attempts} failed: {e}"
                )

                if attempt < max_attempts:
                    if recovery_func:
                        try:
                            logger.info("Running recovery function")
                            recovery_func()
                        except Exception as recovery_error:
                            logger.error(
                                f"Recovery function failed: {recovery_error}"
                            )

                    time.sleep(2 ** attempt)

        raise last_error


class ErrorContext:
    """Context manager for error handling with cleanup."""

    def __init__(
        self,
        operation_name: str,
        cleanup_func: Optional[Callable] = None,
        raise_on_error: bool = True
    ):
        """
        Initialize error context.

        Args:
            operation_name: Name of the operation
            cleanup_func: Optional cleanup function
            raise_on_error: Whether to raise errors
        """
        self.operation_name = operation_name
        self.cleanup_func = cleanup_func
        self.raise_on_error = raise_on_error
        self.error = None

    def __enter__(self):
        """Enter context."""
        logger.debug(f"Starting operation: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context with error handling."""
        if exc_type is not None:
            self.error = exc_val
            logger.error(
                f"Operation '{self.operation_name}' failed: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb)
            )

            # Run cleanup
            if self.cleanup_func:
                try:
                    logger.debug("Running cleanup function")
                    self.cleanup_func()
                except Exception as cleanup_error:
                    logger.error(f"Cleanup failed: {cleanup_error}")

            # Suppress error if configured
            return not self.raise_on_error

        logger.debug(f"Operation '{self.operation_name}' completed successfully")
        return False


if __name__ == '__main__':
    # Test error handling
    print("Testing Error Handling Module")
    print("=" * 70)

    # Test retry decorator
    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def flaky_function(succeed_on: int = 2):
        """Function that fails a few times then succeeds."""
        if not hasattr(flaky_function, 'attempt'):
            flaky_function.attempt = 0
        flaky_function.attempt += 1

        if flaky_function.attempt < succeed_on:
            raise ValueError(f"Attempt {flaky_function.attempt} failed")

        return "Success!"

    # Test handle_errors decorator
    @handle_errors(
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.LOW,
        raise_on_error=False,
        default_return="Error handled"
    )
    def error_function():
        """Function that always raises an error."""
        raise ValueError("This always fails")

    # Run tests
    print("\n1. Testing retry decorator:")
    try:
        result = flaky_function(succeed_on=2)
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Failed: {e}")

    print("\n2. Testing error handler decorator:")
    result = error_function()
    print(f"   Result: {result}")

    print("\n3. Testing circuit breaker:")
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

    def failing_function():
        raise ValueError("Always fails")

    for i in range(5):
        try:
            breaker.call(failing_function)
        except CircuitBreakerOpen:
            print(f"   Attempt {i+1}: Circuit breaker is open")
        except ValueError:
            print(f"   Attempt {i+1}: Function failed")

    print("\n[OK] Error handling module test completed")
