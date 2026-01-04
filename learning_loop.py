#!/usr/bin/env python3
"""
LEARNING LOOP - Continuous AI Improvement System
Automatically updates analytics and regenerates strategy based on performance.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from typing import List

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from channel_manager import get_active_channels, get_channel, add_log
from youtube_analytics import update_all_video_stats
from ai_analyzer import analyze_channel_trends, generate_content_strategy

# ==============================================================================
# Analytics Cycle
# ==============================================================================

def run_analytics_cycle(channel_id: int) -> bool:
    """
    Run complete analytics and learning cycle for a channel.

    Steps:
    1. Fetch latest stats for all posted videos
    2. Analyze performance patterns with AI
    3. Generate new content strategy
    4. Log results

    Returns:
        True if successful, False otherwise
    """
    try:
        channel = get_channel(channel_id)
        if not channel:
            return False

        channel_name = channel['name']

        add_log(channel_id, "info", "analytics", "🔄 Starting analytics cycle...")

        # Step 1: Update video stats from YouTube
        updated_count = update_all_video_stats(channel_id)
        add_log(channel_id, "info", "analytics", f"📊 Updated stats for {updated_count} videos")

        # Step 2: Analyze trends if we have enough data
        trends = analyze_channel_trends(channel_id, limit=30)

        if trends:
            add_log(channel_id, "info", "analytics", f"🧠 AI identified {len(trends.get('successful_patterns', []))} success patterns")
        else:
            add_log(channel_id, "warning", "analytics", "⚠️ Not enough data for trend analysis yet")

        # Step 3: Generate new content strategy
        strategy = generate_content_strategy(channel_id)

        if strategy:
            confidence = strategy.get('confidence_score', 0) * 100
            add_log(channel_id, "info", "analytics", f"✅ Generated new strategy (confidence: {confidence:.0f}%)")
        else:
            add_log(channel_id, "warning", "analytics", "⚠️ Could not generate strategy")

        add_log(channel_id, "info", "analytics", "✅ Analytics cycle complete")

        return True

    except Exception as e:
        add_log(channel_id, "error", "analytics", f"❌ Analytics cycle failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_channels_analytics() -> int:
    """
    Run analytics cycle for all active channels.

    Returns:
        Number of channels successfully analyzed
    """
    try:
        channels = get_active_channels()

        if not channels:
            print("No active channels to analyze")
            return 0

        success_count = 0

        for channel in channels:
            print(f"\n{'='*60}")
            print(f"Running analytics for: {channel['name']}")
            print(f"{'='*60}")

            if run_analytics_cycle(channel['id']):
                success_count += 1
                print(f"✅ Success: {channel['name']}")
            else:
                print(f"❌ Failed: {channel['name']}")

            # Rate limiting
            time.sleep(2)

        print(f"\n{'='*60}")
        print(f"Analytics complete: {success_count}/{len(channels)} channels")
        print(f"{'='*60}\n")

        return success_count

    except Exception as e:
        print(f"Error running analytics for all channels: {e}")
        return 0


# ==============================================================================
# Scheduled Analytics Worker
# ==============================================================================

def analytics_worker_24h(daemon_running_flag):
    """
    Background worker that runs analytics every 24 hours.

    This runs in a separate thread and continuously updates
    video stats and regenerates content strategies.

    Args:
        daemon_running_flag: Function that returns True if daemon should keep running
    """
    print("\n" + "="*60)
    print("📊 ANALYTICS WORKER STARTED")
    print("="*60)
    print("Schedule: Every 24 hours")
    print("Next run: In 24 hours")
    print("="*60 + "\n")

    # Run immediately on start
    print("Running initial analytics cycle...")
    run_all_channels_analytics()

    last_run = datetime.now()

    while daemon_running_flag():
        try:
            # Check if 24 hours have passed
            now = datetime.now()
            time_since_last = now - last_run

            if time_since_last >= timedelta(hours=24):
                print(f"\n{'='*60}")
                print(f"⏰ 24-hour analytics cycle triggered")
                print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}\n")

                run_all_channels_analytics()

                last_run = now

            # Sleep for 1 hour between checks
            time.sleep(3600)

        except Exception as e:
            print(f"Error in analytics worker: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(3600)  # Wait an hour before retry

    print("\n📊 Analytics worker stopped")


def analytics_worker_on_post(channel_id: int):
    """
    Run quick analytics update after a video is posted.

    This is called immediately after uploading a video to YouTube
    to fetch initial stats and log the posting.
    """
    try:
        # Wait 5 minutes for YouTube to process
        print(f"⏳ Waiting 5 minutes for YouTube to process video...")
        time.sleep(300)

        # Update stats for this channel
        print(f"📊 Fetching initial stats...")
        updated_count = update_all_video_stats(channel_id)

        if updated_count > 0:
            add_log(channel_id, "info", "analytics", f"📊 Fetched initial stats for new video")
            print(f"✅ Initial stats fetched")
        else:
            print(f"⚠️ Could not fetch initial stats")

    except Exception as e:
        print(f"Error in post-upload analytics: {e}")


# ==============================================================================
# Manual Triggers
# ==============================================================================

def force_analytics_update(channel_id: int):
    """
    Force an immediate analytics update for a channel.
    Called from UI when user clicks "Refresh Analytics" button.
    """
    return run_analytics_cycle(channel_id)


def get_next_analytics_run_time() -> datetime:
    """
    Get the scheduled time for next analytics run.
    """
    # For now, return 24 hours from now
    # In production, track actual last run time
    return datetime.now() + timedelta(hours=24)


# ==============================================================================
# Statistics & Reporting
# ==============================================================================

def get_analytics_summary(channel_id: int) -> dict:
    """
    Get summary of analytics data for display in UI.

    Returns:
        {
            'total_videos': int,
            'total_views': int,
            'total_likes': int,
            'avg_engagement': float,
            'best_video': dict,
            'worst_video': dict,
            'growth_trend': str
        }
    """
    from channel_manager import get_channel_videos

    try:
        videos = get_channel_videos(channel_id, limit=100)
        posted = [v for v in videos if v['status'] == 'posted' and v.get('views', 0) > 0]

        if not posted:
            return {
                'total_videos': 0,
                'total_views': 0,
                'total_likes': 0,
                'avg_engagement': 0.0,
                'best_video': None,
                'worst_video': None,
                'growth_trend': 'No data yet'
            }

        # Calculate totals
        total_views = sum(v.get('views', 0) for v in posted)
        total_likes = sum(v.get('likes', 0) for v in posted)
        total_comments = sum(v.get('comments', 0) for v in posted)

        # Best and worst
        best = max(posted, key=lambda x: x.get('views', 0))
        worst = min(posted, key=lambda x: x.get('views', 0))

        # Engagement rate
        avg_engagement = ((total_likes + total_comments) / total_views * 100) if total_views > 0 else 0.0

        # Growth trend
        if len(posted) >= 5:
            recent_5 = posted[:5]
            older_5 = posted[-5:]
            recent_avg = sum(v.get('views', 0) for v in recent_5) / 5
            older_avg = sum(v.get('views', 0) for v in older_5) / 5

            if recent_avg > older_avg * 1.2:
                growth_trend = "📈 Growing (+20%+)"
            elif recent_avg < older_avg * 0.8:
                growth_trend = "📉 Declining (-20%+)"
            else:
                growth_trend = "➡️ Stable"
        else:
            growth_trend = "📊 Building data..."

        return {
            'total_videos': len(posted),
            'total_views': total_views,
            'total_likes': total_likes,
            'avg_engagement': avg_engagement,
            'best_video': best,
            'worst_video': worst,
            'growth_trend': growth_trend
        }

    except Exception as e:
        print(f"Error getting analytics summary: {e}")
        return None


# ==============================================================================
# Main (for testing)
# ==============================================================================

if __name__ == "__main__":
    print("Running analytics cycle for all channels...")
    result = run_all_channels_analytics()
    print(f"\nCompleted: {result} channels analyzed")
