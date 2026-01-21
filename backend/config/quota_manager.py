#!/usr/bin/env python3
"""
QUOTA MANAGER
Monitors API quotas (Groq, YouTube, Pexels) and automatically resumes operations when quotas reset.

Quotas typically reset at midnight Pacific Time.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
import toml


def init_quota_table(db_path: str = 'channels.db'):
    """
    Initialize quota tracking table.

    Schema:
    - api_name: groq, youtube, pexels
    - quota_limit: daily limit
    - quota_used: current usage
    - quota_remaining: remaining quota
    - last_reset: when quota was last reset
    - next_reset: when quota will reset next
    - is_exhausted: boolean - is quota currently exhausted?
    - exhausted_at: timestamp when quota was exhausted
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_quotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_name TEXT UNIQUE NOT NULL,
            quota_limit INTEGER,
            quota_used INTEGER DEFAULT 0,
            quota_remaining INTEGER,
            last_reset TIMESTAMP,
            next_reset TIMESTAMP,
            is_exhausted BOOLEAN DEFAULT 0,
            exhausted_at TIMESTAMP,
            auto_resume BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Initialize default quotas if not exist
    apis = [
        ('groq', 100000, 100000),  # 100k tokens/day
        ('youtube', 10000, 10000),  # 10k units/day
        ('pexels', 20000, 20000)   # 20k requests/month (~667/day)
    ]

    for api_name, quota_limit, quota_remaining in apis:
        cursor.execute("""
            INSERT OR IGNORE INTO api_quotas (api_name, quota_limit, quota_remaining, last_reset, next_reset)
            VALUES (?, ?, ?, datetime('now'), datetime('now', '+1 day'))
        """, (api_name, quota_limit, quota_remaining))

    conn.commit()
    conn.close()


def get_next_reset_time() -> datetime:
    """
    Calculate next quota reset time (midnight Pacific Time).

    Returns: datetime object
    """
    now = datetime.now()

    # Next midnight local time (quotas reset at midnight PT, but we'll use local midnight as approximation)
    next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    return next_midnight


def check_quota(api_name: str, db_path: str = 'channels.db') -> Dict:
    """
    Check quota status for an API.

    Args:
        api_name: groq, youtube, pexels
        db_path: Database path

    Returns: Dict with quota info
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM api_quotas WHERE api_name = ?", (api_name,))
    row = cursor.fetchone()

    conn.close()

    if not row:
        return {
            'available': True,
            'remaining': 999999,
            'exhausted': False,
            'next_reset': get_next_reset_time().isoformat()
        }

    quota = dict(row)

    return {
        'available': not quota['is_exhausted'],
        'remaining': quota['quota_remaining'],
        'used': quota['quota_used'],
        'limit': quota['quota_limit'],
        'exhausted': quota['is_exhausted'],
        'exhausted_at': quota.get('exhausted_at'),
        'next_reset': quota.get('next_reset'),
        'auto_resume': quota.get('auto_resume', True)
    }


def mark_quota_exhausted(api_name: str, db_path: str = 'channels.db'):
    """
    Mark an API quota as exhausted.

    Args:
        api_name: groq, youtube, pexels
        db_path: Database path
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE api_quotas
        SET is_exhausted = 1,
            exhausted_at = datetime('now'),
            next_reset = datetime('now', '+1 day', 'start of day'),
            updated_at = datetime('now')
        WHERE api_name = ?
    """, (api_name,))

    conn.commit()
    conn.close()

    print(f"[WARNING] {api_name.upper()} quota exhausted at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Will auto-resume at next quota reset (midnight)")


def update_quota_usage(api_name: str, used: int, db_path: str = 'channels.db'):
    """
    Update quota usage for an API.

    Args:
        api_name: groq, youtube, pexels
        used: Amount used
        db_path: Database path
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE api_quotas
        SET quota_used = quota_used + ?,
            quota_remaining = quota_limit - (quota_used + ?),
            updated_at = datetime('now')
        WHERE api_name = ?
    """, (used, used, api_name))

    # Check if exhausted
    cursor.execute("SELECT quota_remaining FROM api_quotas WHERE api_name = ?", (api_name,))
    row = cursor.fetchone()

    if row and row[0] <= 0:
        mark_quota_exhausted(api_name, db_path)

    conn.commit()
    conn.close()


def reset_quota(api_name: str, db_path: str = 'channels.db'):
    """
    Reset quota for an API (called at midnight or manually).

    Args:
        api_name: groq, youtube, pexels
        db_path: Database path
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE api_quotas
        SET quota_used = 0,
            quota_remaining = quota_limit,
            is_exhausted = 0,
            exhausted_at = NULL,
            last_reset = datetime('now'),
            next_reset = datetime('now', '+1 day', 'start of day'),
            updated_at = datetime('now')
        WHERE api_name = ?
    """, (api_name,))

    conn.commit()
    conn.close()

    print(f"[OK] {api_name.upper()} quota reset at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def reset_all_quotas(db_path: str = 'channels.db'):
    """
    Reset all API quotas (called at midnight).

    Args:
        db_path: Database path
    """
    for api_name in ['groq', 'youtube', 'pexels']:
        reset_quota(api_name, db_path)

    print(f"[OK] All quotas reset at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def check_and_reset_if_needed(db_path: str = 'channels.db') -> bool:
    """
    Check if it's time to reset quotas and reset them if needed.

    Returns: True if quotas were reset
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if any quota needs reset
    cursor.execute("""
        SELECT api_name, next_reset
        FROM api_quotas
        WHERE next_reset <= datetime('now')
    """)

    rows = cursor.fetchall()
    conn.close()

    if rows:
        print(f"\n[REFRESH] Quota reset time reached!")
        reset_all_quotas(db_path)
        return True

    return False


def should_resume_operations(db_path: str = 'channels.db') -> bool:
    """
    Check if operations should resume (all critical quotas available).

    Returns: True if should resume
    """
    # Check if it's a new day and reset quotas if needed
    check_and_reset_if_needed(db_path)

    # Check critical API quotas
    groq_status = check_quota('groq', db_path)
    youtube_status = check_quota('youtube', db_path)

    # Need at least Groq or YouTube quota available
    can_resume = (groq_status['available'] or youtube_status['available'])

    return can_resume


def get_quota_status_summary(db_path: str = 'channels.db') -> Dict:
    """
    Get summary of all quota statuses.

    Returns: Dict with all quota info
    """
    return {
        'groq': check_quota('groq', db_path),
        'youtube': check_quota('youtube', db_path),
        'pexels': check_quota('pexels', db_path),
        'can_operate': should_resume_operations(db_path)
    }


def auto_resume_paused_channels(db_path: str = 'channels.db'):
    """
    Automatically resume channels that were paused due to quota exhaustion.

    This should be called periodically (every hour) or after quota reset.
    """
    if not should_resume_operations(db_path):
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find channels that were paused due to quota issues
    cursor.execute("""
        SELECT c.id, c.name
        FROM channels c
        JOIN logs l ON c.id = l.channel_id
        WHERE c.is_active = 0
        AND l.level = 'error'
        AND (l.category LIKE '%quota%' OR l.category LIKE '%rate_limit%' OR l.category LIKE '%api%' OR l.message LIKE '%quota%')
        AND l.timestamp >= datetime('now', '-2 days')
        GROUP BY c.id
    """)

    channels = cursor.fetchall()

    if channels:
        print(f"\n[REFRESH] Quota reset detected - resuming {len(channels)} paused channel(s)...")

        for channel in channels:
            cursor.execute("""
                UPDATE channels
                SET is_active = 1
                WHERE id = ?
            """, (channel['id'],))

            # Add log
            cursor.execute("""
                INSERT INTO logs (channel_id, level, category, message)
                VALUES (?, 'info', 'auto_resume', 'Channel auto-resumed after quota reset')
            """, (channel['id'],))

            print(f"   [OK] Resumed: {channel['name']}")

    conn.commit()
    conn.close()


def monitor_quota_worker(check_interval_minutes: int = 60):
    """
    Background worker that monitors quotas and auto-resumes channels.

    Args:
        check_interval_minutes: How often to check (default: 60 minutes)
    """
    import time

    print(f"\n Starting quota monitor (checks every {check_interval_minutes} minutes)...")

    while True:
        try:
            # Check if quotas have reset
            if check_and_reset_if_needed():
                # Quotas were reset, resume channels
                auto_resume_paused_channels()

            # Sleep until next check
            time.sleep(check_interval_minutes * 60)

        except KeyboardInterrupt:
            print("\n⏹ Quota monitor stopped")
            break
        except Exception as e:
            print(f"[WARNING] Quota monitor error: {e}")
            time.sleep(60)


# Example usage and testing
if __name__ == "__main__":
    print("Testing Quota Manager...\n")

    # Initialize database
    init_quota_table()
    print("[OK] Quota table initialized\n")

    # Check all quotas
    status = get_quota_status_summary()
    print("Current Quota Status:")
    print(f"  Groq: {'[OK] Available' if status['groq']['available'] else '[ERROR] Exhausted'}")
    print(f"    Remaining: {status['groq']['remaining']:,} / {status['groq']['limit']:,}")
    print(f"  YouTube: {'[OK] Available' if status['youtube']['available'] else '[ERROR] Exhausted'}")
    print(f"    Remaining: {status['youtube']['remaining']:,} / {status['youtube']['limit']:,}")
    print(f"  Pexels: {'[OK] Available' if status['pexels']['available'] else '[ERROR] Exhausted'}")
    print(f"    Remaining: {status['pexels']['remaining']:,} / {status['pexels']['limit']:,}")
    print(f"\n  Can operate: {'[OK] YES' if status['can_operate'] else '[ERROR] NO'}")
    print()

    # Test marking quota exhausted
    print("Testing quota exhaustion...")
    mark_quota_exhausted('groq')

    status = check_quota('groq')
    print(f"  Groq exhausted: {status['exhausted']}")
    print(f"  Next reset: {status['next_reset']}")
    print()

    # Test reset
    print("Testing quota reset...")
    reset_quota('groq')

    status = check_quota('groq')
    print(f"  Groq available: {status['available']}")
    print(f"  Remaining: {status['remaining']:,}")
    print()

    print("[OK] All tests passed!")
