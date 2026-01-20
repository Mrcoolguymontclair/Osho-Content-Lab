"""
Structured Logging Module with Rotation

Provides a centralized logging system with:
- Log rotation (prevents disk space issues)
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured output with timestamps
- Per-module loggers
- Console and file output
- Thread-safe logging
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import threading


class ColoredFormatter(logging.Formatter):
    """
    Colored log formatter for console output.

    Makes logs easier to read by color-coding different log levels.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        """Format log record with colors."""
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}"
                f"{record.levelname:8s}"
                f"{self.COLORS['RESET']}"
            )
        else:
            record.levelname = f"{record.levelname:8s}"

        return super().format(record)


class LoggerManager:
    """
    Centralized logger manager.

    Handles creation and configuration of loggers with rotation.
    """

    _instance = None
    _lock = threading.Lock()
    _loggers = {}

    # Default configuration
    DEFAULT_LOG_DIR = 'logs'
    DEFAULT_LOG_LEVEL = 'INFO'
    DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    DEFAULT_BACKUP_COUNT = 5
    DEFAULT_FORMAT = '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
    DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LoggerManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize logger manager."""
        if self._initialized:
            return

        self.log_dir = self.DEFAULT_LOG_DIR
        self.log_level = self.DEFAULT_LOG_LEVEL
        self.max_bytes = self.DEFAULT_MAX_BYTES
        self.backup_count = self.DEFAULT_BACKUP_COUNT

        # Create log directory
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

        # Configure root logger
        self._configure_root_logger()

        self._initialized = True

    def _configure_root_logger(self):
        """Configure the root logger."""
        root_logger = logging.getLogger()
        root_logger.setLevel(self._get_log_level(self.log_level))

        # Remove existing handlers
        root_logger.handlers.clear()

        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._get_log_level(self.log_level))
        console_formatter = ColoredFormatter(
            self.DEFAULT_FORMAT,
            datefmt=self.DEFAULT_DATE_FORMAT
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # Add file handler with rotation (main log file)
        main_log_file = os.path.join(self.log_dir, 'osho_content_lab.log')
        file_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self._get_log_level(self.log_level))
        file_formatter = logging.Formatter(
            self.DEFAULT_FORMAT,
            datefmt=self.DEFAULT_DATE_FORMAT
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    def _get_log_level(self, level: str) -> int:
        """Convert string log level to logging constant."""
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return levels.get(level.upper(), logging.INFO)

    def get_logger(
        self,
        name: str,
        log_file: Optional[str] = None,
        level: Optional[str] = None
    ) -> logging.Logger:
        """
        Get or create a logger.

        Args:
            name: Logger name (usually module name)
            log_file: Optional separate log file for this logger
            level: Optional log level override

        Returns:
            Configured logger instance
        """
        # Check cache
        cache_key = f"{name}:{log_file}:{level}"
        if cache_key in self._loggers:
            return self._loggers[cache_key]

        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(self._get_log_level(level or self.log_level))

        # Add separate file handler if requested
        if log_file:
            log_path = os.path.join(self.log_dir, log_file)
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self._get_log_level(level or self.log_level))
            file_formatter = logging.Formatter(
                self.DEFAULT_FORMAT,
                datefmt=self.DEFAULT_DATE_FORMAT
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        # Cache logger
        self._loggers[cache_key] = logger

        return logger

    def configure(
        self,
        log_dir: Optional[str] = None,
        log_level: Optional[str] = None,
        max_bytes: Optional[int] = None,
        backup_count: Optional[int] = None
    ):
        """
        Configure logger manager.

        Args:
            log_dir: Directory for log files
            log_level: Default log level
            max_bytes: Maximum size of each log file
            backup_count: Number of backup files to keep
        """
        if log_dir:
            self.log_dir = log_dir
            Path(self.log_dir).mkdir(parents=True, exist_ok=True)

        if log_level:
            self.log_level = log_level

        if max_bytes:
            self.max_bytes = max_bytes

        if backup_count:
            self.backup_count = backup_count

        # Reconfigure root logger
        self._configure_root_logger()

        # Clear logger cache to force recreation
        self._loggers.clear()

    def set_level(self, level: str):
        """Set global log level."""
        self.log_level = level
        logging.getLogger().setLevel(self._get_log_level(level))

        # Update all existing loggers
        for logger in self._loggers.values():
            logger.setLevel(self._get_log_level(level))

    def cleanup_old_logs(self, days: int = 7):
        """
        Clean up log files older than specified days.

        Args:
            days: Delete logs older than this many days
        """
        import time

        now = time.time()
        cutoff = now - (days * 86400)  # days in seconds

        log_dir = Path(self.log_dir)
        if not log_dir.exists():
            return

        deleted_count = 0
        for log_file in log_dir.glob('*.log*'):
            try:
                if log_file.stat().st_mtime < cutoff:
                    log_file.unlink()
                    deleted_count += 1
            except Exception as e:
                print(f"Failed to delete {log_file}: {e}")

        if deleted_count > 0:
            print(f"Cleaned up {deleted_count} old log files")


# Global instance
_manager = None


def get_logger_manager() -> LoggerManager:
    """Get the global logger manager instance."""
    global _manager
    if _manager is None:
        _manager = LoggerManager()
    return _manager


def get_logger(
    name: str,
    log_file: Optional[str] = None,
    level: Optional[str] = None
) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (usually __name__)
        log_file: Optional separate log file
        level: Optional log level override

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Starting process")
        logger.error("An error occurred", exc_info=True)
    """
    return get_logger_manager().get_logger(name, log_file, level)


def configure_logging(
    log_dir: Optional[str] = None,
    log_level: Optional[str] = None,
    max_bytes: Optional[int] = None,
    backup_count: Optional[int] = None
):
    """
    Configure global logging settings.

    Args:
        log_dir: Directory for log files
        log_level: Default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep

    Example:
        configure_logging(
            log_dir='logs',
            log_level='INFO',
            max_bytes=10*1024*1024,  # 10MB
            backup_count=5
        )
    """
    get_logger_manager().configure(log_dir, log_level, max_bytes, backup_count)


def set_log_level(level: str):
    """
    Set global log level.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    get_logger_manager().set_level(level)


def cleanup_old_logs(days: int = 7):
    """
    Clean up log files older than specified days.

    Args:
        days: Delete logs older than this many days
    """
    get_logger_manager().cleanup_old_logs(days)


# Convenience functions for backward compatibility
def log_info(message: str, logger_name: str = 'osho'):
    """Log info message."""
    get_logger(logger_name).info(message)


def log_error(message: str, logger_name: str = 'osho', exc_info: bool = False):
    """Log error message."""
    get_logger(logger_name).error(message, exc_info=exc_info)


def log_warning(message: str, logger_name: str = 'osho'):
    """Log warning message."""
    get_logger(logger_name).warning(message)


def log_debug(message: str, logger_name: str = 'osho'):
    """Log debug message."""
    get_logger(logger_name).debug(message)


if __name__ == '__main__':
    # Test logging system
    print("Testing Logging System")
    print("=" * 70)

    # Configure logging
    configure_logging(
        log_dir='logs',
        log_level='DEBUG',
        max_bytes=1024*1024,  # 1MB for testing
        backup_count=3
    )

    # Test different loggers
    main_logger = get_logger('main')
    daemon_logger = get_logger('daemon', log_file='daemon.log')
    video_logger = get_logger('video', log_file='video.log')

    # Test different log levels
    main_logger.debug("This is a debug message")
    main_logger.info("This is an info message")
    main_logger.warning("This is a warning message")
    main_logger.error("This is an error message")
    main_logger.critical("This is a critical message")

    # Test exception logging
    try:
        raise ValueError("Test exception")
    except Exception as e:
        main_logger.error("Caught exception:", exc_info=True)

    # Test separate log files
    daemon_logger.info("Daemon started")
    video_logger.info("Video generation started")

    print("\n[OK] Logging system test completed!")
    print(f"   Check the 'logs' directory for log files")
    print(f"   - osho_content_lab.log (main log)")
    print(f"   - daemon.log (daemon log)")
    print(f"   - video.log (video log)")
