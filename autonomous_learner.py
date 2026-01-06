#!/usr/bin/env python3
"""
AUTONOMOUS AI LEARNING SYSTEM
Runs continuously in background, analyzes video performance,
and automatically improves future video generation.

NO USER INTERACTION NEEDED - fully autonomous self-improvement.
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from channel_manager import get_all_channels, get_channel_videos, add_log
from ai_analyzer import analyze_channel_trends, generate_content_strategy, get_latest_content_strategy
from youtube_analytics import update_all_video_stats

# ==============================================================================
# Autonomous Learning Configuration
# ==============================================================================

# How often to run learning cycles (in seconds)
LEARNING_CYCLE_INTERVAL = 6 * 3600  # Every 6 hours (was 24h, now faster)

# Minimum videos needed before AI analysis
MIN_VIDEOS_FOR_ANALYSIS = 3

# How many recent videos to analyze
ANALYSIS_WINDOW = 30

# ==============================================================================
# Core Autonomous Learning Loop
# ==============================================================================

def autonomous_learning_cycle():
    """
    Main learning cycle that runs automatically.

    Steps:
    1. Fetch latest analytics from YouTube
    2. Analyze performance patterns
    3. Generate improved content strategy
    4. Store strategy in DB (auto-used by video generation)
    5. Repeat forever
    """

    print(f"🧠 Autonomous Learning System Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Learning cycle interval: {LEARNING_CYCLE_INTERVAL / 3600:.1f} hours")
    print(f"   System will continuously improve video performance without user intervention.\n")

    while True:
        try:
            cycle_start = time.time()

            # Get all active channels
            channels = get_all_channels()
            active_channels = [ch for ch in channels if ch.get('status') == 'active']

            if not active_channels:
                print("   No active channels to analyze. Sleeping...")
                time.sleep(LEARNING_CYCLE_INTERVAL)
                continue

            print(f"\n{'='*60}")
            print(f"🔄 Starting Learning Cycle - {datetime.now().strftime('%H:%M:%S')}")
            print(f"   Analyzing {len(active_channels)} active channel(s)")
            print(f"{'='*60}\n")

            for channel in active_channels:
                try:
                    learn_from_channel(channel)
                except Exception as e:
                    print(f"   ✗ Error learning from channel {channel['id']}: {e}")
                    continue

            # Calculate next cycle time
            cycle_duration = time.time() - cycle_start
            sleep_time = max(60, LEARNING_CYCLE_INTERVAL - cycle_duration)

            next_cycle = datetime.now() + timedelta(seconds=sleep_time)
            print(f"\n{'='*60}")
            print(f"✓ Learning cycle complete")
            print(f"   Next cycle: {next_cycle.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}\n")

            time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n🛑 Autonomous learning stopped by user")
            break
        except Exception as e:
            print(f"\n✗ Learning cycle error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(300)  # Wait 5 minutes before retrying


def learn_from_channel(channel: Dict):
    """
    Autonomous learning for a single channel.

    Process:
    1. Fetch latest video stats from YouTube
    2. Analyze what's working / not working
    3. Generate improved strategy
    4. Store in DB (automatically used next video gen)
    """

    channel_id = channel['id']
    channel_name = channel.get('name', f'Channel {channel_id}')

    print(f"\n   📊 Analyzing: {channel_name}")

    # Step 1: Fetch latest analytics
    print(f"      → Fetching latest YouTube analytics...")
    videos = get_channel_videos(channel_id, limit=ANALYSIS_WINDOW)
    posted_videos = [v for v in videos if v['status'] == 'posted']

    if len(posted_videos) < MIN_VIDEOS_FOR_ANALYSIS:
        print(f"      ℹ Not enough data yet ({len(posted_videos)}/{MIN_VIDEOS_FOR_ANALYSIS} videos)")
        return

    # Fetch stats for all posted videos
    try:
        stats_updated = update_all_video_stats(channel_id)
        if stats_updated > 0:
            print(f"      ✓ Updated stats for {stats_updated} video(s)")
    except Exception as e:
        print(f"      ℹ Could not update stats: {e}")

    # Step 2: Analyze performance patterns
    print(f"      → Running AI pattern recognition...")

    trends = analyze_channel_trends(channel_id, limit=ANALYSIS_WINDOW)

    if not trends:
        print(f"      ✗ Pattern analysis failed")
        return

    # Display key insights (for developer monitoring only)
    success_patterns = trends.get('successful_patterns', [])
    if success_patterns:
        print(f"      ✓ Found {len(success_patterns)} success pattern(s):")
        for pattern in success_patterns[:2]:
            print(f"        • {pattern}")

    # Step 3: Generate improved content strategy
    print(f"      → Generating optimized strategy...")

    strategy = generate_content_strategy(channel_id)

    if not strategy:
        print(f"      ✗ Strategy generation failed")
        return

    recommended = strategy.get('recommended_topics', [])
    confidence = strategy.get('confidence_score', 0.0)

    print(f"      ✓ Strategy generated (confidence: {confidence:.0%})")
    print(f"        Next video will use: {recommended[0] if recommended else 'default'}")

    # Step 4: Strategy is auto-saved to DB by generate_content_strategy()
    # Video generation will automatically pull and use it

    add_log(
        channel_id,
        "info",
        "learning",
        f"Autonomous learning: {len(success_patterns)} patterns → {len(recommended)} optimized topics"
    )

    print(f"      ✓ Learning complete - improvements active for next video")


# ==============================================================================
# Background Thread Manager
# ==============================================================================

_learning_thread = None
_stop_flag = False

def start_autonomous_learning():
    """Start autonomous learning in background thread."""
    global _learning_thread, _stop_flag

    if _learning_thread and _learning_thread.is_alive():
        print("Autonomous learning already running")
        return False

    _stop_flag = False
    _learning_thread = threading.Thread(target=autonomous_learning_cycle, daemon=True)
    _learning_thread.start()

    return True


def stop_autonomous_learning():
    """Stop autonomous learning thread."""
    global _stop_flag
    _stop_flag = True
    print("Stopping autonomous learning...")


def is_learning_active() -> bool:
    """Check if autonomous learning is currently running."""
    global _learning_thread
    return _learning_thread and _learning_thread.is_alive()


# ==============================================================================
# Manual Trigger (for testing/debugging)
# ==============================================================================

def run_learning_now(channel_id: Optional[int] = None):
    """
    Manually trigger a learning cycle (for testing).

    Args:
        channel_id: If provided, only learn from this channel. Otherwise all channels.
    """

    if channel_id:
        from channel_manager import get_channel
        channel = get_channel(channel_id)
        if channel:
            learn_from_channel(channel)
        else:
            print(f"Channel {channel_id} not found")
    else:
        channels = get_all_channels()
        for channel in channels:
            if channel.get('status') == 'active':
                learn_from_channel(channel)


# ==============================================================================
# Main Entry Point
# ==============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Autonomous AI Learning System')
    parser.add_argument('--now', action='store_true', help='Run one learning cycle immediately')
    parser.add_argument('--channel', type=int, help='Channel ID to analyze (with --now)')

    args = parser.parse_args()

    if args.now:
        print("Running manual learning cycle...\n")
        run_learning_now(args.channel)
    else:
        # Start continuous autonomous learning
        autonomous_learning_cycle()
