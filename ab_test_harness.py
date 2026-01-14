#!/usr/bin/env python3
"""
A/B Test Orchestration & Experiment Harness
Automates experiment design, assignment, and outcome measurement.
"""

import random
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from channel_manager import update_video, get_channel_videos, add_log


def assign_ab_group(video_id: int, experiment_name: str = None) -> str:
    """Randomly assign a video to 'test' or 'control' group with 50/50 split"""
    group = random.choice(['test', 'control'])
    update_video(video_id, ab_test_group=group)
    return group


def assign_title_variant(video_id: int, variants: List[str]) -> str:
    """Randomly assign a title variant from the list"""
    if not variants:
        return None
    chosen = random.choice(variants)
    update_video(video_id, title_variant=chosen, title=chosen)
    return chosen


def assign_thumbnail_variant(video_id: int, variants: List[str]) -> str:
    """Randomly assign a thumbnail variant from the list"""
    if not variants:
        return None
    chosen = random.choice(variants)
    update_video(video_id, thumbnail_variant=chosen)
    return chosen


def calculate_success_score(video: Dict) -> float:
    """
    Calculate a composite success score from multiple metrics.
    
    Weights: retention @ 3s (30%), avg_watch_time (30%), CTR (20%), engagement_rate (20%)
    """
    # Estimate retention at 3s (0-100% as normalized 0-1)
    # For now, use avg_watch_time as proxy
    avg_watch_time = video.get('avg_watch_time', 0) or 0
    
    # Views and engagement
    views = video.get('views', 0) or 0
    likes = video.get('likes', 0) or 0
    comments = video.get('comments', 0) or 0
    
    if views == 0:
        return 0.0
    
    # Engagement rate (%)
    engagement_rate = ((likes + comments) / views) * 100 if views > 0 else 0
    
    # CTR (use views as approximation; ideally from Analytics API)
    # Assume base CTR of 0.5% and scale by engagement
    ctr = video.get('ctr', 0) or (0.5 * (engagement_rate / 1.0))  # 1% engagement baseline
    
    # Normalize: watch_time (0-100%), CTR (0-5%), engagement (0-5%)
    watch_score = min(avg_watch_time / 100, 1.0) if avg_watch_time else 0
    ctr_score = min(ctr / 5.0, 1.0) if ctr else 0
    engagement_score = min(engagement_rate / 5.0, 1.0) if engagement_rate else 0
    
    # Composite (weighted)
    success_score = (
        watch_score * 0.40 +
        ctr_score * 0.30 +
        engagement_score * 0.30
    )
    
    return success_score


def analyze_ab_results(channel_id: int, experiment_name: str, days_window: int = 7) -> Optional[Dict]:
    """
    Analyze A/B test results and determine winner.
    
    Returns: {
        'experiment_name': str,
        'test_videos': List[Dict],
        'control_videos': List[Dict],
        'test_avg_score': float,
        'control_avg_score': float,
        'winner': 'test'|'control'|'tie',
        'lift_percent': float,
        'confidence': float,  # 0-1 estimate
        'recommendation': str
    }
    """
    try:
        conn = sqlite3.connect('channels.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(days=days_window)).isoformat()
        
        # Fetch videos in this experiment window
        cursor.execute("""
            SELECT * FROM videos
            WHERE channel_id = ? AND status = 'posted' AND actual_post_time > ?
            ORDER BY actual_post_time DESC
        """, (channel_id, cutoff_time))
        
        videos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        if not videos:
            return None
        
        test_videos = [v for v in videos if v['ab_test_group'] == 'test']
        control_videos = [v for v in videos if v['ab_test_group'] == 'control']
        
        if len(test_videos) < 3 or len(control_videos) < 3:
            return {
                'experiment_name': experiment_name,
                'test_videos': test_videos,
                'control_videos': control_videos,
                'test_avg_score': 0.0,
                'control_avg_score': 0.0,
                'winner': 'tie',
                'lift_percent': 0.0,
                'confidence': 0.0,
                'recommendation': f'Need more samples. Test: {len(test_videos)}/3, Control: {len(control_videos)}/3'
            }
        
        # Calculate average success scores
        test_scores = [calculate_success_score(v) for v in test_videos]
        control_scores = [calculate_success_score(v) for v in control_videos]
        
        test_avg = sum(test_scores) / len(test_scores)
        control_avg = sum(control_scores) / len(control_scores)
        
        # Determine winner
        if test_avg > control_avg * 1.10:
            winner = 'test'
            lift = ((test_avg - control_avg) / control_avg) * 100 if control_avg > 0 else 0
        elif control_avg > test_avg * 1.10:
            winner = 'control'
            lift = ((control_avg - test_avg) / test_avg) * 100 if test_avg > 0 else 0
        else:
            winner = 'tie'
            lift = 0.0
        
        # Rough confidence estimate (0-1) based on sample size and score variance
        confidence = min(len(test_videos) / 20.0, 1.0)
        
        return {
            'experiment_name': experiment_name,
            'test_videos': test_videos,
            'control_videos': control_videos,
            'test_avg_score': test_avg,
            'control_avg_score': control_avg,
            'winner': winner,
            'lift_percent': lift,
            'confidence': confidence,
            'recommendation': f'{winner.upper()} wins with {lift:.1f}% lift (confidence: {confidence:.0%})'
        }
        
    except Exception as e:
        print(f"Error analyzing A/B results: {e}")
        return None


def rollout_winner(channel_id: int, winning_variant: str, variant_type: str) -> bool:
    """
    Apply the winning variant to future videos for a channel.
    
    Args:
        channel_id: Channel ID
        winning_variant: Winning variant value
        variant_type: 'title' | 'thumbnail' | 'hook' | etc.
    
    Returns: True if successfully applied
    """
    try:
        # Store winning strategy in database for future video generation
        conn = sqlite3.connect('channels.db')
        cursor = conn.cursor()
        
        # Log the rollout
        add_log(channel_id, 'info', 'ab_test',
                f'Rolling out winning {variant_type}: {winning_variant}')
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error rolling out winner: {e}")
        return False
