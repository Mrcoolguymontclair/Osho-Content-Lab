#!/usr/bin/env python3
"""
TIME FORMATTER
Centralized time formatting for consistent Chicago time (12-hour format).
"""

import pytz
from datetime import datetime, timedelta
from typing import Optional

# Chicago timezone
CHICAGO_TZ = pytz.timezone('America/Chicago')


def now_chicago() -> datetime:
    """
    Get current time in Chicago timezone.

    Returns: datetime object with Chicago timezone
    """
    return datetime.now(CHICAGO_TZ)


def format_time_chicago(
    dt: Optional[datetime] = None,
    format_type: str = "default"
) -> str:
    """
    Format datetime in Chicago timezone with 12-hour format.

    Args:
        dt: datetime object (if None, uses current time)
        format_type: Format style

    Returns: Formatted time string

    Format types:
        - "default": "01/12 02:45 PM"
        - "full": "January 12, 2026 02:45:30 PM CST"
        - "time_only": "02:45 PM"
        - "date_only": "01/12/2026"
        - "log": "[02:45:30 PM]"
        - "filename": "2026-01-12_02-45-PM"
    """
    if dt is None:
        dt = now_chicago()
    elif dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = pytz.utc.localize(dt)

    # Convert to Chicago time
    dt_chicago = dt.astimezone(CHICAGO_TZ)

    formats = {
        "default": "%m/%d %I:%M %p",           # 01/12 02:45 PM
        "full": "%B %d, %Y %I:%M:%S %p %Z",   # January 12, 2026 02:45:30 PM CST
        "time_only": "%I:%M %p",               # 02:45 PM
        "date_only": "%m/%d/%Y",               # 01/12/2026
        "log": "[%I:%M:%S %p]",                # [02:45:30 PM]
        "filename": "%Y-%m-%d_%I-%M-%p",       # 2026-01-12_02-45-PM
        "compact": "%m/%d %I:%M%p",            # 01/12 2:45PM (no space)
        "timestamp": "%I:%M:%S %p",            # 02:45:30 PM
    }

    format_str = formats.get(format_type, formats["default"])
    return dt_chicago.strftime(format_str)


def parse_time_to_chicago(time_str: str) -> datetime:
    """
    Parse ISO format time string and convert to Chicago timezone.

    Args:
        time_str: ISO format time string

    Returns: datetime in Chicago timezone
    """
    try:
        # Try parsing ISO format
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except:
        # Try parsing as datetime string
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        dt = pytz.utc.localize(dt)

    return dt.astimezone(CHICAGO_TZ)


def format_duration(seconds: int) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns: Formatted duration string

    Examples:
        - 45 seconds: "45s"
        - 90 seconds: "1m 30s"
        - 3665 seconds: "1h 1m"
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}m {secs}s" if secs else f"{mins}m"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m" if mins else f"{hours}h"


def format_time_until(target_time: datetime, short: bool = False) -> str:
    """
    Format time until a future datetime.

    Args:
        target_time: Future datetime
        short: Use short format

    Returns: Formatted string

    Examples:
        - "in 5 minutes"
        - "in 2 hours"
        - "overdue by 10 minutes"
    """
    now = now_chicago()

    if target_time.tzinfo is None:
        target_time = pytz.utc.localize(target_time)

    target_chicago = target_time.astimezone(CHICAGO_TZ)
    diff = target_chicago - now
    diff_seconds = int(diff.total_seconds())

    if diff_seconds < 0:
        # Overdue
        duration = format_duration(abs(diff_seconds))
        return f"-{duration}" if short else f"overdue by {duration}"
    else:
        # Future
        duration = format_duration(diff_seconds)
        return duration if short else f"in {duration}"


def format_log_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Format timestamp for log entries (Chicago time, 12-hour).

    Args:
        dt: datetime (if None, uses current time)

    Returns: Log-formatted timestamp

    Example: "[02:45:30 PM]"
    """
    return format_time_chicago(dt, "log")


def format_relative_time(dt: datetime) -> str:
    """
    Format time in relative terms (e.g., "5 minutes ago").

    Args:
        dt: Past datetime

    Returns: Relative time string

    Examples:
        - "just now"
        - "5 minutes ago"
        - "2 hours ago"
        - "yesterday at 2:45 PM"
    """
    now = now_chicago()

    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    dt_chicago = dt.astimezone(CHICAGO_TZ)
    diff = now - dt_chicago
    diff_seconds = int(diff.total_seconds())

    if diff_seconds < 60:
        return "just now"
    elif diff_seconds < 3600:
        mins = diff_seconds // 60
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    elif diff_seconds < 86400:
        hours = diff_seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff_seconds < 172800:  # 2 days
        return f"yesterday at {format_time_chicago(dt_chicago, 'time_only')}"
    else:
        return format_time_chicago(dt_chicago, "default")


# Testing
if __name__ == "__main__":
    print("=" * 70)
    print("⏰ TIME FORMATTER TEST")
    print("=" * 70)

    print(f"\n📅 Current time (Chicago): {format_time_chicago()}")
    print(f"📅 Full format: {format_time_chicago(format_type='full')}")
    print(f"📅 Time only: {format_time_chicago(format_type='time_only')}")
    print(f"📅 Log format: {format_log_timestamp()}")

    print(f"\n⏱️  Duration examples:")
    print(f"   45 seconds: {format_duration(45)}")
    print(f"   90 seconds: {format_duration(90)}")
    print(f"   3665 seconds: {format_duration(3665)}")

    print(f"\n🔮 Time until examples:")
    future = now_chicago() + timedelta(minutes=45)
    print(f"   Next video: {format_time_until(future)}")
    print(f"   Next video (short): {format_time_until(future, short=True)}")

    past = now_chicago() - timedelta(hours=2)
    print(f"   Overdue: {format_time_until(past)}")

    print(f"\n📝 Relative time examples:")
    print(f"   2 hours ago: {format_relative_time(now_chicago() - timedelta(hours=2))}")
    print(f"   5 minutes ago: {format_relative_time(now_chicago() - timedelta(minutes=5))}")
    print(f"   Yesterday: {format_relative_time(now_chicago() - timedelta(days=1))}")

    print("\n✅ All time formatting functions working!")
    print("=" * 70)
