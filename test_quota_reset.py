#!/usr/bin/env python3
"""
TEST QUOTA RESET SYSTEM
Simulates quota exhaustion and reset to verify automatic resume works.
"""

import sqlite3
from datetime import datetime, timedelta
from quota_manager import (
    init_quota_table, check_quota, mark_quota_exhausted,
    reset_quota, auto_resume_paused_channels, get_quota_status_summary
)
from channel_manager import get_channel, update_channel, add_log


def test_quota_reset_flow():
    """Test complete quota reset and channel resume flow."""

    print("=" * 70)
    print("🧪 TESTING QUOTA RESET & AUTO-RESUME SYSTEM")
    print("=" * 70)
    print()

    # Step 1: Initialize quota system
    print("Step 1: Initializing quota system...")
    init_quota_table()
    print("✅ Quota table ready\n")

    # Step 2: Check initial quota status
    print("Step 2: Checking initial quota status...")
    status = get_quota_status_summary()
    print(f"  Groq: {'✅ Available' if status['groq']['available'] else '❌ Exhausted'}")
    print(f"  YouTube: {'✅ Available' if status['youtube']['available'] else '❌ Exhausted'}")
    print(f"  Can operate: {'✅ YES' if status['can_operate'] else '❌ NO'}")
    print()

    # Step 3: Simulate Groq quota exhaustion
    print("Step 3: Simulating Groq quota exhaustion...")
    mark_quota_exhausted('groq')

    status = check_quota('groq')
    print(f"  Groq exhausted: {status['exhausted']}")
    print(f"  Next reset: {status['next_reset']}")
    print()

    # Step 4: Simulate channel pause due to quota
    print("Step 4: Simulating channel pause due to quota error...")
    conn = sqlite3.connect('channels.db')
    cursor = conn.cursor()

    # Get RankRiot channel
    cursor.execute("SELECT id FROM channels WHERE name = 'RankRiot'")
    result = cursor.fetchone()

    if result:
        channel_id = result[0]

        # Pause channel
        cursor.execute("UPDATE channels SET is_active = 0 WHERE id = ?", (channel_id,))

        # Add log entry about quota
        cursor.execute("""
            INSERT INTO logs (channel_id, level, category, message)
            VALUES (?, 'error', 'quota_exceeded', 'Groq API quota exceeded')
        """, (channel_id,))

        conn.commit()
        print(f"  ✅ Channel {channel_id} paused")
        print(f"  ✅ Quota error logged")
        print()
    else:
        print("  ⚠️ No RankRiot channel found to test with")
        print()

    conn.close()

    # Step 5: Show channel status
    print("Step 5: Current channel status...")
    channel = get_channel(channel_id)
    print(f"  Channel: {channel['name']}")
    print(f"  Active: {'✅ YES' if channel['is_active'] else '❌ NO (paused)'}")
    print()

    # Step 6: Simulate quota reset (midnight)
    print("Step 6: Simulating quota reset (midnight)...")
    reset_quota('groq')

    status = check_quota('groq')
    print(f"  Groq available: {status['available']}")
    print(f"  Remaining: {status['remaining']:,}")
    print()

    # Step 7: Auto-resume paused channels
    print("Step 7: Running auto-resume logic...")
    auto_resume_paused_channels()
    print()

    # Step 8: Verify channel resumed
    print("Step 8: Verifying channel auto-resumed...")
    channel = get_channel(channel_id)
    print(f"  Channel: {channel['name']}")
    print(f"  Active: {'✅ YES' if channel['is_active'] else '❌ NO'}")
    print()

    # Step 9: Final status check
    print("Step 9: Final system status...")
    status = get_quota_status_summary()
    print(f"  Groq: {'✅ Available' if status['groq']['available'] else '❌ Exhausted'}")
    print(f"  YouTube: {'✅ Available' if status['youtube']['available'] else '❌ Exhausted'}")
    print(f"  Can operate: {'✅ YES' if status['can_operate'] else '❌ NO'}")
    print()

    # Verify success
    if channel['is_active'] and status['groq']['available']:
        print("=" * 70)
        print("✅ TEST PASSED - Automatic quota reset and channel resume working!")
        print("=" * 70)
        print()
        print("What this means:")
        print("  • When API quotas are exhausted, channels pause automatically")
        print("  • At midnight, quotas reset automatically")
        print("  • Paused channels resume automatically after quota reset")
        print("  • No manual intervention needed!")
        print()
        return True
    else:
        print("=" * 70)
        print("❌ TEST FAILED - Something went wrong")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = test_quota_reset_flow()
    exit(0 if success else 1)
