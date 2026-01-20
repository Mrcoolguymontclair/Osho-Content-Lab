"""
Health Monitoring System

Monitors system health and provides status endpoints.

Features:
- CPU and memory monitoring
- Disk space monitoring
- Service health checks
- Heartbeat system
- Alert generation
"""

import os
import time
import psutil
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from logger import get_logger
from constants import (
    HEALTH_CHECK_INTERVAL,
    DISK_SPACE_WARNING_THRESHOLD,
    MEMORY_WARNING_THRESHOLD
)

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Single health check result."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details
        }


class HealthMonitor:
    """
    System health monitor.

    Performs regular health checks and tracks system status.
    """

    def __init__(self, check_interval: int = HEALTH_CHECK_INTERVAL):
        """
        Initialize health monitor.

        Args:
            check_interval: Interval between health checks (seconds)
        """
        self.check_interval = check_interval
        self._checks: Dict[str, HealthCheck] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._alert_callbacks: List[Callable[[HealthCheck], None]] = []

    def register_alert_callback(self, callback: Callable[[HealthCheck], None]):
        """
        Register callback for health alerts.

        Args:
            callback: Function to call when health degrades
        """
        self._alert_callbacks.append(callback)

    def _notify_alerts(self, check: HealthCheck):
        """Notify all registered alert callbacks."""
        if check.status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY):
            for callback in self._alert_callbacks:
                try:
                    callback(check)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

    def check_cpu_usage(self) -> HealthCheck:
        """
        Check CPU usage.

        Returns:
            HealthCheck result
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)

            if cpu_percent < 70:
                status = HealthStatus.HEALTHY
                message = f"CPU usage is normal: {cpu_percent:.1f}%"
            elif cpu_percent < 90:
                status = HealthStatus.DEGRADED
                message = f"CPU usage is high: {cpu_percent:.1f}%"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"CPU usage is critical: {cpu_percent:.1f}%"

            return HealthCheck(
                name="cpu_usage",
                status=status,
                message=message,
                timestamp=datetime.now(),
                details={'cpu_percent': cpu_percent}
            )

        except Exception as e:
            logger.error(f"CPU check failed: {e}")
            return HealthCheck(
                name="cpu_usage",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check CPU: {e}",
                timestamp=datetime.now()
            )

    def check_memory_usage(self) -> HealthCheck:
        """
        Check memory usage.

        Returns:
            HealthCheck result
        """
        try:
            memory = psutil.virtual_memory()
            percent_used = memory.percent

            if percent_used < MEMORY_WARNING_THRESHOLD * 100:
                status = HealthStatus.HEALTHY
                message = f"Memory usage is normal: {percent_used:.1f}%"
            elif percent_used < 95:
                status = HealthStatus.DEGRADED
                message = f"Memory usage is high: {percent_used:.1f}%"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Memory usage is critical: {percent_used:.1f}%"

            return HealthCheck(
                name="memory_usage",
                status=status,
                message=message,
                timestamp=datetime.now(),
                details={
                    'percent': percent_used,
                    'available_mb': memory.available / (1024 * 1024),
                    'total_mb': memory.total / (1024 * 1024)
                }
            )

        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return HealthCheck(
                name="memory_usage",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check memory: {e}",
                timestamp=datetime.now()
            )

    def check_disk_space(self, path: str = "/") -> HealthCheck:
        """
        Check disk space.

        Args:
            path: Path to check

        Returns:
            HealthCheck result
        """
        try:
            disk = psutil.disk_usage(path)
            free_bytes = disk.free

            if free_bytes > DISK_SPACE_WARNING_THRESHOLD * 2:
                status = HealthStatus.HEALTHY
                message = f"Disk space is sufficient: {free_bytes / (1024**3):.2f} GB free"
            elif free_bytes > DISK_SPACE_WARNING_THRESHOLD:
                status = HealthStatus.DEGRADED
                message = f"Disk space is low: {free_bytes / (1024**3):.2f} GB free"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Disk space is critical: {free_bytes / (1024**3):.2f} GB free"

            return HealthCheck(
                name="disk_space",
                status=status,
                message=message,
                timestamp=datetime.now(),
                details={
                    'free_gb': free_bytes / (1024**3),
                    'total_gb': disk.total / (1024**3),
                    'percent_used': disk.percent
                }
            )

        except Exception as e:
            logger.error(f"Disk check failed: {e}")
            return HealthCheck(
                name="disk_space",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check disk: {e}",
                timestamp=datetime.now()
            )

    def check_database(self, db_path: str = "channels.db") -> HealthCheck:
        """
        Check database availability.

        Args:
            db_path: Path to database file

        Returns:
            HealthCheck result
        """
        try:
            if not os.path.exists(db_path):
                return HealthCheck(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Database file not found: {db_path}",
                    timestamp=datetime.now()
                )

            # Check file size
            size_mb = os.path.getsize(db_path) / (1024 * 1024)

            # Try to open (basic check)
            import sqlite3
            with sqlite3.connect(db_path, timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]

            return HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                message=f"Database is accessible ({table_count} tables, {size_mb:.2f} MB)",
                timestamp=datetime.now(),
                details={
                    'path': db_path,
                    'size_mb': size_mb,
                    'table_count': table_count
                }
            )

        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {e}",
                timestamp=datetime.now()
            )

    def check_ffmpeg(self) -> HealthCheck:
        """
        Check FFmpeg availability.

        Returns:
            HealthCheck result
        """
        try:
            import shutil
            ffmpeg_path = shutil.which('ffmpeg')
            ffprobe_path = shutil.which('ffprobe')

            if ffmpeg_path and ffprobe_path:
                return HealthCheck(
                    name="ffmpeg",
                    status=HealthStatus.HEALTHY,
                    message="FFmpeg and FFprobe are available",
                    timestamp=datetime.now(),
                    details={
                        'ffmpeg_path': ffmpeg_path,
                        'ffprobe_path': ffprobe_path
                    }
                )
            elif ffmpeg_path:
                return HealthCheck(
                    name="ffmpeg",
                    status=HealthStatus.DEGRADED,
                    message="FFmpeg found but FFprobe missing",
                    timestamp=datetime.now()
                )
            else:
                return HealthCheck(
                    name="ffmpeg",
                    status=HealthStatus.UNHEALTHY,
                    message="FFmpeg not found in PATH",
                    timestamp=datetime.now()
                )

        except Exception as e:
            logger.error(f"FFmpeg check failed: {e}")
            return HealthCheck(
                name="ffmpeg",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check FFmpeg: {e}",
                timestamp=datetime.now()
            )

    def run_all_checks(self) -> Dict[str, HealthCheck]:
        """
        Run all health checks.

        Returns:
            Dictionary mapping check names to results
        """
        checks = {
            'cpu': self.check_cpu_usage(),
            'memory': self.check_memory_usage(),
            'disk': self.check_disk_space(),
            'database': self.check_database(),
            'ffmpeg': self.check_ffmpeg()
        }

        with self._lock:
            self._checks = checks

        # Notify alerts
        for check in checks.values():
            self._notify_alerts(check)

        return checks

    def get_overall_status(self) -> HealthStatus:
        """
        Get overall system health status.

        Returns:
            Overall health status
        """
        with self._lock:
            if not self._checks:
                return HealthStatus.UNKNOWN

            statuses = [check.status for check in self._checks.values()]

            if HealthStatus.UNHEALTHY in statuses:
                return HealthStatus.UNHEALTHY
            elif HealthStatus.DEGRADED in statuses:
                return HealthStatus.DEGRADED
            elif HealthStatus.UNKNOWN in statuses:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY

    def get_health_report(self) -> Dict:
        """
        Get comprehensive health report.

        Returns:
            Health report dictionary
        """
        with self._lock:
            checks_dict = {
                name: check.to_dict()
                for name, check in self._checks.items()
            }

        return {
            'overall_status': self.get_overall_status().value,
            'timestamp': datetime.now().isoformat(),
            'checks': checks_dict
        }

    def _monitor_loop(self):
        """Background monitoring loop."""
        logger.info("Health monitor started")

        while self._running:
            try:
                self.run_all_checks()
            except Exception as e:
                logger.error(f"Health check error: {e}", exc_info=True)

            # Sleep for check interval
            for _ in range(self.check_interval):
                if not self._running:
                    break
                time.sleep(1)

        logger.info("Health monitor stopped")

    def start(self):
        """Start background health monitoring."""
        if self._running:
            logger.warning("Health monitor already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Health monitor background thread started")

    def stop(self):
        """Stop background health monitoring."""
        if not self._running:
            return

        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Health monitor stopped")


# Global health monitor instance
_monitor = None
_monitor_lock = threading.Lock()


def get_health_monitor() -> HealthMonitor:
    """
    Get global health monitor instance.

    Returns:
        HealthMonitor instance
    """
    global _monitor

    with _monitor_lock:
        if _monitor is None:
            _monitor = HealthMonitor()

    return _monitor


if __name__ == '__main__':
    # Test health monitor
    print("Testing Health Monitor")
    print("=" * 70)

    monitor = HealthMonitor()

    # Run all checks
    checks = monitor.run_all_checks()

    print("\nHealth Checks:")
    for name, check in checks.items():
        print(f"\n{name}:")
        print(f"  Status: {check.status.value}")
        print(f"  Message: {check.message}")
        if check.details:
            print(f"  Details: {check.details}")

    print(f"\nOverall Status: {monitor.get_overall_status().value}")

    print("\n[OK] Health monitor test completed")
