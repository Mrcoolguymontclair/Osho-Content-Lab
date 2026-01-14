#!/usr/bin/env python3
"""
Test the new V2 video engine with all quality improvements.
"""

from video_engine_ranking_v2 import generate_ranking_video_v2
from channel_manager import get_channel
import sys

print("=" * 70)
print("TESTING V2 VIDEO ENGINE - ALL QUALITY FIXES")
print("=" * 70)
print()

# Get RankRiot channel
import sqlite3
conn = sqlite3.connect('channels.db')
cursor = conn.cursor()
cursor.execute("SELECT id, name FROM channels WHERE name = 'RankRiot'")
result = cursor.fetchone()
conn.close()

if not result:
    print("ERROR: RankRiot channel not found")
    sys.exit(1)

channel_id = result[0]
theme = "Extreme natural wonders"
tone = "Exciting"
style = "Fast-paced"
ranking_count = 5

print(f"Channel: RankRiot (ID: {channel_id})")
print(f"Theme: {theme}")
print(f"Format: Top {ranking_count} ranking")
print()
print("Starting generation...")
print("-" * 70)
print()

# Generate video
video_path, error = generate_ranking_video_v2(
    theme=theme,
    tone=tone,
    style=style,
    channel_id=channel_id,
    ranking_count=ranking_count
)

print()
print("=" * 70)

if error:
    print(f"❌ GENERATION FAILED: {error}")
    sys.exit(1)
else:
    print(f"✅ SUCCESS!")
    print(f"Video: {video_path}")

    # Check file size
    import os
    if os.path.exists(video_path):
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"Size: {size_mb:.2f} MB")

        # Check duration
        import subprocess
        result = subprocess.run([
            '/opt/homebrew/bin/ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ], capture_output=True, text=True)

        if result.returncode == 0:
            duration = float(result.stdout.strip())
            print(f"Duration: {duration:.2f} seconds")

            if abs(duration - 45.0) < 1.0:
                print("✅ Duration perfect!")
            else:
                print(f"⚠️ Duration off by {abs(duration - 45.0):.2f}s")

    print()
    print("=" * 70)
    print("TEST COMPLETE - CHECK THE VIDEO QUALITY!")
    print("=" * 70)
