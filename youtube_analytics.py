#!/usr/bin/env python3
"""
YOUTUBE ANALYTICS MODULE
Fetches video performance metrics from YouTube API for AI analysis.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth_manager import get_youtube_service
from channel_manager import get_channel_videos, update_video

# ==============================================================================
# Video Statistics Fetching
# ==============================================================================

def get_video_stats(video_url: str, channel_name: str) -> Optional[Dict]:
    """
    Fetch comprehensive stats for a single video from YouTube API.

    Args:
        video_url: Full YouTube URL or video ID
        channel_name: Channel name for authentication

    Returns:
        {
            'video_id': str,
            'views': int,
            'likes': int,
            'comments': int,
            'shares': int,  # Note: Not available via API
            'avg_watch_time': float,  # Percentage
            'ctr': float,  # Click-through rate percentage
            'published_at': str
        }
    """
    try:
        # Extract video ID from URL
        if 'youtube.com' in video_url or 'youtu.be' in video_url:
            if 'v=' in video_url:
                video_id = video_url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in video_url:
                video_id = video_url.split('youtu.be/')[1].split('?')[0]
            else:
                return None
        else:
            video_id = video_url  # Assume it's already just the ID

        # Get YouTube service
        youtube = get_youtube_service(channel_name)
        if not youtube:
            return None

        # Fetch video statistics
        request = youtube.videos().list(
            part='statistics,snippet,contentDetails',
            id=video_id
        )
        response = request.execute()

        if not response.get('items'):
            return None

        video_data = response['items'][0]
        stats = video_data['statistics']
        snippet = video_data['snippet']

        # Parse statistics
        result = {
            'video_id': video_id,
            'views': int(stats.get('viewCount', 0)),
            'likes': int(stats.get('likeCount', 0)),
            'comments': int(stats.get('commentCount', 0)),
            'shares': 0,  # Not available via basic API
            'avg_watch_time': 0.0,  # Requires YouTube Analytics API
            'ctr': 0.0,  # Requires YouTube Analytics API
            'published_at': snippet.get('publishedAt', '')
        }

        # Try to get analytics data (requires special permissions)
        try:
            result['avg_watch_time'], result['ctr'] = get_average_view_duration_and_ctr(channel_name, video_id)
        except Exception:
            # Analytics API not available or not authorized
            pass

        return result

    except Exception as e:
        print(f"Error fetching video stats: {e}")
        return None


def get_average_view_duration(youtube, video_id: str) -> float:
    """
    Get average view duration percentage using YouTube Analytics API.

    Note: This requires special YouTube Analytics API permissions.
    Returns 0.0 if not available.
    """
    try:
        # This requires youtubeAnalytics service, not regular youtube service
        # For now, return 0 - can be enhanced later with proper analytics API
        return 0.0
    except:
        return 0.0


def get_video_analytics(video_id: str, channel_id: int, days_window: int = 7) -> Optional[Dict]:
    """
    Fetch comprehensive video analytics from YouTube Analytics API.
    
    Args:
        video_id: YouTube video ID
        channel_id: DB channel ID
        days_window: How many days back to look
    
    Returns:
        {
            'video_id': str,
            'views': int,
            'impressions': int,
            'ctr': float,
            'avg_view_duration_secs': float,
            'avg_view_percentage': float,
            'views_24h': int,
            'views_7d': int,
            'retention_curve': List[float],  # [0s, 3s, 15s, 30s, 60s, ...]
            'fetched_at': str
        }
    """
    try:
        from channel_manager import get_channel
        channel = get_channel(channel_id)
        if not channel:
            return None

        # Get YouTube service
        youtube = get_youtube_service(channel['name'])
        if not youtube:
            return None

        # Try to fetch via basic video stats API (always available)
        request = youtube.videos().list(
            part='statistics,snippet',
            id=video_id
        )
        response = request.execute()

        if not response.get('items'):
            return None

        video_data = response['items'][0]
        stats = video_data['statistics']
        snippet = video_data['snippet']

        # Basic stats always available
        result = {
            'video_id': video_id,
            'views': int(stats.get('viewCount', 0)),
            'impressions': 0,  # Requires Analytics API
            'ctr': 0.0,  # Requires Analytics API
            'avg_view_duration_secs': 0.0,  # Requires Analytics API
            'avg_view_percentage': 0.0,  # Requires Analytics API
            'views_24h': 0,  # Would require time-series data
            'views_7d': int(stats.get('viewCount', 0)),  # Approximation
            'retention_curve': [],
            'published_at': snippet.get('publishedAt', ''),
            'fetched_at': datetime.now().isoformat()
        }

        # Future enhancement: add youtubeAnalytics API integration here
        # This would fetch impressions, ctr, avg_view_duration, retention curves

        return result

    except Exception as e:
        print(f"Error fetching video analytics: {e}")
        return None


def get_channel_videos_stats(channel_name: str, limit: int = 50) -> List[Dict]:
    """
    Get stats for multiple videos from the channel.

    Args:
        channel_name: Channel name for authentication
        limit: Max number of videos to fetch stats for

    Returns:
        List of video stats dictionaries
    """
    try:
        youtube = get_youtube_service(channel_name)
        if not youtube:
            return []

        # Get channel ID
        request = youtube.channels().list(
            part='contentDetails',
            mine=True
        )
        response = request.execute()

        if not response.get('items'):
            return []

        uploads_playlist = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Get videos from uploads playlist
        videos = []
        page_token = None

        while len(videos) < limit:
            request = youtube.playlistItems().list(
                part='contentDetails',
                playlistId=uploads_playlist,
                maxResults=min(50, limit - len(videos)),
                pageToken=page_token
            )
            response = request.execute()

            for item in response.get('items', []):
                video_id = item['contentDetails']['videoId']
                stats = get_video_stats(video_id, channel_name)
                if stats:
                    videos.append(stats)

            page_token = response.get('nextPageToken')
            if not page_token:
                break

        return videos

    except Exception as e:
        print(f"Error fetching channel videos stats: {e}")
        return []


def update_video_stats_in_db(db_video_id: int) -> bool:
    """
    Fetch latest stats from YouTube and update database.

    Args:
        db_video_id: Video ID in our database

    Returns:
        True if successful, False otherwise
    """
    try:
        from channel_manager import get_channel
        import sqlite3

        # Get video from database
        conn = sqlite3.connect('channels.db')
        c = conn.cursor()
        c.execute('SELECT id, channel_id, youtube_url, title FROM videos WHERE id = ?', (db_video_id,))
        row = c.fetchone()

        if not row:
            conn.close()
            return False

        video_id, channel_id, youtube_url, title = row

        if not youtube_url:
            conn.close()
            return False

        # Get channel info
        channel = get_channel(channel_id)
        if not channel:
            conn.close()
            return False

        # Fetch stats from YouTube
        stats = get_video_stats(youtube_url, channel['name'])

        if not stats:
            conn.close()
            return False

        # Update database
        c.execute('''
            UPDATE videos
            SET views = ?, likes = ?, comments = ?,
                avg_watch_time = ?, last_stats_update = ?
            WHERE id = ?
        ''', (
            stats['views'],
            stats['likes'],
            stats['comments'],
            stats['avg_watch_time'],
            datetime.now().isoformat(),
            video_id
        ))

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        print(f"Error updating video stats in DB: {e}")
        return False


def update_all_video_stats(channel_id: int) -> int:
    """
    Update stats for all posted videos in a channel.

    Args:
        channel_id: Channel ID in database

    Returns:
        Number of videos successfully updated
    """
    try:
        from channel_manager import get_channel

        videos = get_channel_videos(channel_id, limit=100)
        posted_videos = [v for v in videos if v['status'] == 'posted' and v.get('youtube_url')]

        updated_count = 0
        for video in posted_videos:
            if update_video_stats_in_db(video['id']):
                updated_count += 1
                time.sleep(0.5)  # Rate limiting

        return updated_count

    except Exception as e:
        print(f"Error updating all video stats: {e}")
        return 0


# ==============================================================================
# Database Schema Updates
# ==============================================================================

def upgrade_database_schema():
    """
    Add analytics columns to videos table if they don't exist.
    """
    import sqlite3

    conn = sqlite3.connect('channels.db')
    c = conn.cursor()

    # Check if columns exist
    c.execute("PRAGMA table_info(videos)")
    columns = [col[1] for col in c.fetchall()]

    # Add new columns if they don't exist
    if 'views' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN views INTEGER DEFAULT 0')

    if 'likes' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN likes INTEGER DEFAULT 0')

    if 'comments' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN comments INTEGER DEFAULT 0')

    if 'shares' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN shares INTEGER DEFAULT 0')

    if 'avg_watch_time' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN avg_watch_time REAL DEFAULT 0')

    if 'ctr' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN ctr REAL DEFAULT 0')

    if 'last_stats_update' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN last_stats_update TEXT')

    # Additional fields for experiments and A/B tests
    if 'title_variant' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN title_variant TEXT DEFAULT NULL')
    if 'thumbnail_variant' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN thumbnail_variant TEXT DEFAULT NULL')
    if 'thumbnail_results' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN thumbnail_results TEXT DEFAULT NULL')
    if 'retention_curve_json' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN retention_curve_json TEXT DEFAULT NULL')
    if 'views_24h' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN views_24h INTEGER DEFAULT 0')
    if 'views_7d' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN views_7d INTEGER DEFAULT 0')

    conn.commit()
    conn.close()

    print("✅ Database schema upgraded for analytics")


# ==============================================================================
# Helper Functions
# ==============================================================================

def calculate_engagement_rate(video_stats: Dict) -> float:
    """
    Calculate engagement rate: (likes + comments) / views * 100
    """
    views = video_stats.get('views', 0)
    if views == 0:
        return 0.0

    likes = video_stats.get('likes', 0)
    comments = video_stats.get('comments', 0)

    return ((likes + comments) / views) * 100


def get_video_age_hours(published_at: str) -> float:
    """
    Get how many hours old a video is.
    """
    try:
        published = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        now = datetime.now(published.tzinfo)
        delta = now - published
        return delta.total_seconds() / 3600
    except:
        return 0.0


def estimate_views_per_hour(video_stats: Dict) -> float:
    """
    Estimate views per hour (velocity metric).
    """
    age_hours = get_video_age_hours(video_stats.get('published_at', ''))
    views = video_stats.get('views', 0)

    if age_hours == 0:
        return 0.0

    return views / age_hours


# Run schema upgrade when module is imported
upgrade_database_schema()
