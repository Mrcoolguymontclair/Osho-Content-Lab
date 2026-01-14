#!/usr/bin/env python3
"""
Quick status check for RankRiot channel
"""

import sqlite3
from datetime import datetime

print("=" * 70)
print("🎬 RANKRIOT CHANNEL STATUS")
print("=" * 70)

conn = sqlite3.connect('channels.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Channel info
cursor.execute("SELECT * FROM channels WHERE name='RankRiot'")
channel = dict(cursor.fetchone())

print(f"\n📊 CHANNEL CONFIGURATION:")
print(f"   Status: {'🟢 ACTIVE' if channel['is_active'] else '🔴 PAUSED'}")
print(f"   Video Format: {channel['video_type'].upper()}")
print(f"   Post Interval: {channel['post_interval_minutes']} minutes")
print(f"   Next Post: {channel['next_post_at']}")

# Recent videos
print(f"\n🎥 RECENT VIDEOS (Last 5):")
cursor.execute("""
    SELECT title, status, created_at, error_message
    FROM videos
    WHERE channel_id=?
    ORDER BY created_at DESC
    LIMIT 5
""", (channel['id'],))

for video in cursor.fetchall():
    video = dict(video)
    status_icon = {
        'posted': '✅',
        'ready': '📦',
        'generating': '⏳',
        'failed': '❌'
    }.get(video['status'], '❓')

    print(f"   {status_icon} {video['status'].upper():12s} - {video['title']}")
    if video['error_message'] and video['status'] == 'failed':
        error_short = video['error_message'][:80] + '...' if len(video['error_message']) > 80 else video['error_message']
        print(f"      ⚠️  {error_short}")

# Trending stats
if channel['video_type'] == 'trending':
    print(f"\n🔥 TRENDING TOPICS:")
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM trends
        WHERE is_approved=1 AND video_generated=0
    """)
    pending_count = cursor.fetchone()[0]

    print(f"   Pending Trends: {pending_count}")

    if pending_count > 0:
        cursor.execute("""
            SELECT topic, confidence, urgency, recommended_format
            FROM trends
            WHERE is_approved=1 AND video_generated=0 AND video_plan_json IS NOT NULL
            ORDER BY urgency DESC, confidence DESC
            LIMIT 1
        """)
        next_trend = cursor.fetchone()
        if next_trend:
            next_trend = dict(next_trend)
            print(f"\n   🎯 NEXT TREND:")
            print(f"      Topic: {next_trend['topic']}")
            print(f"      Urgency: {next_trend['urgency']}")
            print(f"      Confidence: {next_trend['confidence']}%")
            print(f"      Format: {next_trend['recommended_format']}")

# Timing
print(f"\n⏰ TIMING:")
now = datetime.now()
if channel['next_post_at']:
    next_post = datetime.fromisoformat(channel['next_post_at'])
    time_diff = (next_post - now).total_seconds()

    if time_diff > 0:
        mins = int(time_diff / 60)
        secs = int(time_diff % 60)
        print(f"   Next video generation in: {mins}m {secs}s")
    else:
        print(f"   Next video: OVERDUE by {abs(int(time_diff/60))} minutes")
else:
    print(f"   Next video: Not scheduled")

print(f"\n{'=' * 70}")

conn.close()

# Check daemon
import os
if os.path.exists('daemon.pid'):
    with open('daemon.pid') as f:
        pid = f.read().strip()
    print(f"✅ Daemon running (PID: {pid})")
else:
    print(f"❌ Daemon not running")

print(f"{'=' * 70}\n")
