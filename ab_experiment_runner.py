#!/usr/bin/env python3
"""
A/B Experiment Runner & Automation
Orchestrates continuous A/B testing across channels for titles, thumbnails, hooks, etc.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ab_test_harness import analyze_ab_results, rollout_winner
from youtube_analytics import update_all_video_stats, get_video_analytics
from channel_manager import (
    get_all_channels, get_channel_videos, update_video, add_log
)


class ABExperimentRunner:
    """Orchestrates A/B testing experiments across a channel"""

    def __init__(self, channel_id: int):
        self.channel_id = channel_id

    def run_title_variant_experiment(self, duration_days: int = 7) -> Optional[Dict]:
        """Run a title variant A/B experiment for a 7-day window"""
        try:
            results = analyze_ab_results(self.channel_id, 'title_variants', days_window=duration_days)
            
            if not results or results['winner'] == 'tie':
                add_log(self.channel_id, 'info', 'experiment', 'Title A/B: No clear winner yet')
                return results
            
            # Log results
            add_log(self.channel_id, 'info', 'experiment',
                   f"Title A/B Winner: {results['winner']} (+{results['lift_percent']:.1f}%)")
            
            # Optionally rollout
            if results['confidence'] > 0.7:
                # Get winning variant from test videos
                test_videos = results['test_videos']
                if test_videos:
                    winning_title = test_videos[0].get('title_variant') or test_videos[0].get('title')
                    rollout_winner(self.channel_id, winning_title, 'title')
                    add_log(self.channel_id, 'info', 'experiment', f'Rolling out title: {winning_title}')
            
            return results
            
        except Exception as e:
            add_log(self.channel_id, 'error', 'experiment', f'Title A/B error: {e}')
            return None

    def run_thumbnail_variant_experiment(self, duration_days: int = 7) -> Optional[Dict]:
        """Run a thumbnail variant A/B experiment"""
        try:
            results = analyze_ab_results(self.channel_id, 'thumbnail_variants', days_window=duration_days)
            
            if not results or results['winner'] == 'tie':
                add_log(self.channel_id, 'info', 'experiment', 'Thumbnail A/B: No clear winner yet')
                return results
            
            add_log(self.channel_id, 'info', 'experiment',
                   f"Thumbnail A/B Winner: {results['winner']} (+{results['lift_percent']:.1f}%)")
            
            if results['confidence'] > 0.7:
                test_videos = results['test_videos']
                if test_videos:
                    winning_thumb = test_videos[0].get('thumbnail_variant', 'auto_frame')
                    rollout_winner(self.channel_id, winning_thumb, 'thumbnail')
                    add_log(self.channel_id, 'info', 'experiment', f'Rolling out thumbnail: {winning_thumb}')
            
            return results
            
        except Exception as e:
            add_log(self.channel_id, 'error', 'experiment', f'Thumbnail A/B error: {e}')
            return None

    def refresh_analytics_for_recent_videos(self, limit: int = 50, hours_old_min: int = 12) -> int:
        """Fetch fresh analytics for recently posted videos"""
        try:
            videos = get_channel_videos(self.channel_id, limit=limit)
            posted = [v for v in videos if v['status'] == 'posted']
            
            if not posted:
                return 0
            
            # Filter to videos at least 12 hours old but within last 7 days
            updated_count = 0
            for video in posted:
                if video.get('youtube_url'):
                    from auth_manager import get_video_id_from_url
                    video_id = get_video_id_from_url(video['youtube_url'])
                    
                    if video_id:
                        analytics = get_video_analytics(video_id, self.channel_id)
                        if analytics:
                            update_video(
                                video['id'],
                                views=analytics.get('views', 0),
                                ctr=analytics.get('ctr', 0),
                                avg_watch_time=analytics.get('avg_view_duration_secs', 0),
                                last_stats_update=datetime.now().isoformat()
                            )
                            updated_count += 1
                    
                    # Rate limit
                    import time
                    time.sleep(0.5)
            
            add_log(self.channel_id, 'info', 'analytics', f'Refreshed analytics for {updated_count} videos')
            return updated_count
            
        except Exception as e:
            add_log(self.channel_id, 'error', 'analytics', f'Analytics refresh error: {e}')
            return 0


def run_all_ab_experiments(channel_id: int = None):
    """Run all A/B experiments for all channels or a specific channel"""
    try:
        channels = [channel_id] if channel_id else [ch['id'] for ch in get_all_channels()]
        
        for ch_id in channels:
            runner = ABExperimentRunner(ch_id)
            
            # Run title variant test
            title_results = runner.run_title_variant_experiment()
            
            # Run thumbnail variant test
            thumb_results = runner.run_thumbnail_variant_experiment()
            
            # Refresh analytics
            runner.refresh_analytics_for_recent_videos(limit=20)
            
            # Summary
            if title_results:
                print(f"Channel {ch_id} - Title A/B: {title_results['recommendation']}")
            if thumb_results:
                print(f"Channel {ch_id} - Thumbnail A/B: {thumb_results['recommendation']}")
        
        print("✅ A/B experiments cycle complete")
        
    except Exception as e:
        print(f"Error running A/B experiments: {e}")


if __name__ == '__main__':
    # Can be run as standalone or imported
    run_all_ab_experiments()
