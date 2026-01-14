#!/usr/bin/env python3
"""
UNIFIED ERROR RECOVERY SYSTEM
Intelligent retry logic with exponential backoff and automatic issue resolution.
"""

import time
from typing import Callable, Any, Optional, Dict
from functools import wraps
import traceback


class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retriable_errors: list = None
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retriable_errors = retriable_errors or [
            'quota', 'rate limit', '429', '503', 'timeout',
            'connection', 'temporary', 'transient'
        ]


def is_retriable_error(error: Exception, config: RetryConfig) -> bool:
    """
    Determine if an error is retriable.

    Args:
        error: The exception that occurred
        config: Retry configuration

    Returns: True if error should be retried
    """
    error_str = str(error).lower()

    # Check if error matches any retriable patterns
    for pattern in config.retriable_errors:
        if pattern in error_str:
            return True

    # Non-retriable errors (fail fast)
    non_retriable = [
        'authentication failed',
        'invalid credentials',
        'permission denied',
        'not found',
        'invalid request',
        'bad request'
    ]

    for pattern in non_retriable:
        if pattern in error_str:
            return False

    # Default: retry if it's a common transient error type
    return isinstance(error, (ConnectionError, TimeoutError, IOError))


def retry_with_backoff(config: RetryConfig = None):
    """
    Decorator for automatic retry with exponential backoff.

    Usage:
        @retry_with_backoff(RetryConfig(max_attempts=5))
        def unstable_function():
            # This will automatically retry on transient errors
            pass
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Check if we should retry
                    if not is_retriable_error(e, config):
                        # Non-retriable error, fail immediately
                        raise

                    if attempt == config.max_attempts:
                        # Last attempt, give up
                        raise

                    # Calculate backoff delay
                    delay = min(
                        config.initial_delay * (config.exponential_base ** (attempt - 1)),
                        config.max_delay
                    )

                    print(f"⚠️  Attempt {attempt}/{config.max_attempts} failed: {str(e)[:100]}")
                    print(f"   Retrying in {delay:.1f}s...")
                    time.sleep(delay)

            # Should never reach here, but just in case
            raise last_exception

        return wrapper
    return decorator


class ErrorRecoveryManager:
    """
    Manages error recovery strategies for different failure types.
    """

    def __init__(self):
        self.recovery_strategies = {
            'authentication': self._recover_authentication,
            'quota': self._recover_quota,
            'ffmpeg': self._recover_ffmpeg,
            'groq_api': self._recover_groq_api,
            'duplicate': self._recover_duplicate,
        }

    def categorize_error(self, error: str) -> str:
        """
        Categorize error into recovery type.

        Args:
            error: Error message

        Returns: Error category
        """
        error_lower = error.lower()

        if 'not authenticated' in error_lower or 'authentication' in error_lower:
            return 'authentication'
        elif 'quota' in error_lower or '403' in error_lower:
            return 'quota'
        elif 'ffmpeg' in error_lower or 'ffprobe' in error_lower:
            return 'ffmpeg'
        elif 'groq' in error_lower or 'error code:' in error_lower:
            return 'groq_api'
        elif 'duplicate' in error_lower:
            return 'duplicate'
        else:
            return 'unknown'

    def attempt_recovery(self, error: str, channel_id: int) -> Dict:
        """
        Attempt to recover from an error.

        Args:
            error: Error message
            channel_id: Channel that experienced the error

        Returns: Recovery result dict
        """
        category = self.categorize_error(error)

        if category in self.recovery_strategies:
            return self.recovery_strategies[category](error, channel_id)
        else:
            return {
                'success': False,
                'category': category,
                'action': 'No recovery strategy available',
                'recommendation': 'Manual intervention required'
            }

    def _recover_authentication(self, error: str, channel_id: int) -> Dict:
        """Recover from authentication errors"""
        from channel_manager import get_channel, add_log

        channel = get_channel(channel_id)

        add_log(
            channel_id,
            'warning',
            'recovery',
            '🔧 Authentication error detected. Please re-authenticate in UI Settings tab.'
        )

        return {
            'success': False,
            'category': 'authentication',
            'action': 'User re-authentication required',
            'recommendation': 'Go to Settings tab → YouTube Authentication section',
            'auto_recoverable': False
        }

    def _recover_quota(self, error: str, channel_id: int) -> Dict:
        """Recover from quota errors"""
        from channel_manager import add_log
        from quota_manager import mark_quota_exhausted, get_quota_reset_time

        add_log(
            channel_id,
            'warning',
            'recovery',
            '⏳ YouTube quota exhausted. Channel will auto-resume at midnight PST.'
        )

        mark_quota_exhausted()
        reset_time = get_quota_reset_time()

        return {
            'success': True,
            'category': 'quota',
            'action': 'Marked quota as exhausted',
            'recommendation': f'Will auto-resume at {reset_time}',
            'auto_recoverable': True
        }

    def _recover_ffmpeg(self, error: str, channel_id: int) -> Dict:
        """Recover from FFmpeg errors"""
        from channel_manager import add_log
        import subprocess

        add_log(channel_id, 'warning', 'recovery', '🔧 FFmpeg error detected. Checking installation...')

        # Check if ffmpeg is available
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            ffmpeg_available = result.returncode == 0
        except:
            ffmpeg_available = False

        if not ffmpeg_available:
            add_log(
                channel_id,
                'error',
                'recovery',
                '❌ FFmpeg not found. Install with: brew install ffmpeg'
            )
            return {
                'success': False,
                'category': 'ffmpeg',
                'action': 'FFmpeg not installed',
                'recommendation': 'Run: brew install ffmpeg',
                'auto_recoverable': False
            }
        else:
            add_log(channel_id, 'info', 'recovery', '✅ FFmpeg is installed. Error may be transient.')
            return {
                'success': True,
                'category': 'ffmpeg',
                'action': 'FFmpeg is available',
                'recommendation': 'Retry the operation',
                'auto_recoverable': True
            }

    def _recover_groq_api(self, error: str, channel_id: int) -> Dict:
        """Recover from Groq API errors"""
        from channel_manager import add_log

        # Groq API errors are handled by GroqManager automatic failover
        add_log(
            channel_id,
            'info',
            'recovery',
            '🔄 Groq API error. GroqManager will automatically switch to backup key.'
        )

        return {
            'success': True,
            'category': 'groq_api',
            'action': 'Automatic API key failover',
            'recommendation': 'Error should resolve automatically',
            'auto_recoverable': True
        }

    def _recover_duplicate(self, error: str, channel_id: int) -> Dict:
        """Recover from duplicate video detection"""
        from channel_manager import add_log

        add_log(
            channel_id,
            'info',
            'recovery',
            '🔄 Duplicate detected. System will generate alternative topic on next attempt.'
        )

        return {
            'success': True,
            'category': 'duplicate',
            'action': 'Will generate different topic',
            'recommendation': 'Automatic - no action needed',
            'auto_recoverable': True
        }


# Global recovery manager instance
_recovery_manager = None

def get_recovery_manager() -> ErrorRecoveryManager:
    """Get global recovery manager instance"""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = ErrorRecoveryManager()
    return _recovery_manager


# Testing
if __name__ == "__main__":
    print("Testing Error Recovery System\n")

    # Test retry decorator
    print("1. Testing retry decorator:")
    attempt_count = [0]

    @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.1))
    def flaky_function():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise ConnectionError(f"Attempt {attempt_count[0]} failed")
        return "Success!"

    try:
        result = flaky_function()
        print(f"   ✅ {result} (after {attempt_count[0]} attempts)\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")

    # Test error categorization
    print("2. Testing error categorization:")
    manager = get_recovery_manager()

    test_errors = [
        "Channel not authenticated",
        "YouTube API quota exceeded",
        "ffmpeg version check failed",
        "Error code: 500 from Groq API",
        "Duplicate video detected"
    ]

    for error in test_errors:
        category = manager.categorize_error(error)
        print(f"   '{error[:40]}...' → {category}")

    print("\n✅ Error recovery system ready!")
