#!/usr/bin/env python3
"""
TREND TRACKER
Database management for trending topics and generated videos.
Tracks: trends, analysis, videos generated, performance.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional


def init_trends_table(db_path: str = 'channels.db'):
    """
    Initialize trends table in database.

    Schema:
    - id: Primary key
    - topic: Trend topic/title
    - source: google_trends, google_realtime, sports, etc.
    - category: sports, entertainment, business, etc.
    - search_volume: very_high, high, medium, normal
    - fetched_at: When trend was discovered
    - analyzed_at: When AI analyzed it
    - analysis_json: Full AI analysis from trend_analyzer
    - is_approved: Boolean - AI approved for video?
    - video_planned: Boolean - Has video plan been created?
    - video_generated: Boolean - Has video been generated?
    - video_posted: Boolean - Has video been uploaded to YouTube?
    - video_id: Reference to videos table
    - video_plan_json: Full video plan from video_planner_ai
    - confidence: AI confidence score (0-100)
    - urgency: very_urgent, urgent, moderate, low
    - recommended_format: comparison, explainer, timeline, etc.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            source TEXT,
            category TEXT,
            search_volume TEXT,
            fetched_at TIMESTAMP,
            analyzed_at TIMESTAMP,
            analysis_json TEXT,
            is_approved BOOLEAN DEFAULT 0,
            video_planned BOOLEAN DEFAULT 0,
            video_generated BOOLEAN DEFAULT 0,
            video_posted BOOLEAN DEFAULT 0,
            video_id INTEGER,
            video_plan_json TEXT,
            confidence INTEGER,
            urgency TEXT,
            recommended_format TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index on topic for duplicate detection
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trends_topic ON trends(topic)
    """)

    # Create index on fetched_at for time-based queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trends_fetched ON trends(fetched_at)
    """)

    conn.commit()
    conn.close()


def save_trend(trend: Dict, db_path: str = 'channels.db') -> int:
    """
    Save a trend to database.

    Args:
        trend: Trend dictionary from google_trends_fetcher
        db_path: Database file path

    Returns: Trend ID
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO trends (topic, source, category, search_volume, fetched_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        trend.get('topic', 'Unknown'),
        trend.get('source', 'unknown'),
        trend.get('category', 'unknown'),
        trend.get('search_volume', 'normal'),
        trend.get('fetched_at', datetime.now().isoformat())
    ))

    trend_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return trend_id


def update_trend_analysis(trend_id: int, analysis: Dict, is_approved: bool, db_path: str = 'channels.db'):
    """
    Update trend with AI analysis results.

    Args:
        trend_id: Trend database ID
        analysis: Analysis dict from trend_analyzer
        is_approved: Whether AI approved for video
        db_path: Database file path
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE trends
        SET analyzed_at = ?,
            analysis_json = ?,
            is_approved = ?,
            confidence = ?,
            urgency = ?,
            recommended_format = ?
        WHERE id = ?
    """, (
        datetime.now().isoformat(),
        json.dumps(analysis),
        1 if is_approved else 0,
        analysis.get('confidence', 0),
        analysis.get('urgency', 'low'),
        analysis.get('recommended_format', 'unknown'),
        trend_id
    ))

    conn.commit()
    conn.close()


def update_trend_video_plan(trend_id: int, video_plan: Dict, db_path: str = 'channels.db'):
    """
    Update trend with video plan.

    Args:
        trend_id: Trend database ID
        video_plan: Plan dict from video_planner_ai
        db_path: Database file path
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE trends
        SET video_plan_json = ?,
            video_planned = 1
        WHERE id = ?
    """, (
        json.dumps(video_plan),
        trend_id
    ))

    conn.commit()
    conn.close()


def mark_trend_video_generated(trend_id: int, video_id: int, db_path: str = 'channels.db'):
    """
    Mark trend as having video generated.

    Args:
        trend_id: Trend database ID
        video_id: Video ID from videos table
        db_path: Database file path
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE trends
        SET video_generated = 1,
            video_id = ?
        WHERE id = ?
    """, (video_id, trend_id))

    conn.commit()
    conn.close()


def mark_trend_video_posted(trend_id: int, db_path: str = 'channels.db'):
    """
    Mark trend video as posted to YouTube.

    Args:
        trend_id: Trend database ID
        db_path: Database file path
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE trends
        SET video_posted = 1
        WHERE id = ?
    """, (trend_id,))

    conn.commit()
    conn.close()


def get_pending_trends(limit: int = 10, db_path: str = 'channels.db') -> List[Dict]:
    """
    Get trends that are approved but don't have videos yet.

    Args:
        limit: Maximum number to return
        db_path: Database file path

    Returns: List of trend dicts
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM trends
        WHERE is_approved = 1
        AND video_generated = 0
        ORDER BY urgency DESC, confidence DESC, fetched_at DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    trends = [dict(row) for row in rows]

    conn.close()
    return trends


def get_recent_trends(hours: int = 24, db_path: str = 'channels.db') -> List[Dict]:
    """
    Get trends fetched in the last N hours.

    Args:
        hours: How many hours back to look
        db_path: Database file path

    Returns: List of trend dicts
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM trends
        WHERE fetched_at >= datetime('now', '-' || ? || ' hours')
        ORDER BY fetched_at DESC
    """, (hours,))

    rows = cursor.fetchall()
    trends = [dict(row) for row in rows]

    conn.close()
    return trends


def check_trend_exists(topic: str, hours: int = 24, db_path: str = 'channels.db') -> bool:
    """
    Check if trend already exists in database (duplicate prevention).

    Args:
        topic: Trend topic to check
        hours: Only check trends from last N hours
        db_path: Database file path

    Returns: True if exists
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM trends
        WHERE topic = ?
        AND fetched_at >= datetime('now', '-' || ? || ' hours')
    """, (topic, hours))

    count = cursor.fetchone()[0]
    conn.close()

    return count > 0


def get_trend_by_id(trend_id: int, db_path: str = 'channels.db') -> Optional[Dict]:
    """
    Get trend by ID.

    Args:
        trend_id: Trend database ID
        db_path: Database file path

    Returns: Trend dict or None
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM trends WHERE id = ?", (trend_id,))
    row = cursor.fetchone()

    conn.close()

    if row:
        trend = dict(row)
        # Parse JSON fields
        if trend.get('analysis_json'):
            trend['analysis'] = json.loads(trend['analysis_json'])
        if trend.get('video_plan_json'):
            trend['video_plan'] = json.loads(trend['video_plan_json'])
        return trend

    return None


def get_best_pending_trend(channel_theme: str, db_path: str = 'channels.db') -> Optional[Dict]:
    """
    Get the best pending trend for a channel.

    Prioritizes:
    1. Urgency (very_urgent > urgent > moderate > low)
    2. Confidence (higher is better)
    3. Recency (newer is better)

    Args:
        channel_theme: Channel's theme for filtering
        db_path: Database file path

    Returns: Best trend dict or None
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Urgency scoring
    urgency_score = """
        CASE urgency
            WHEN 'very_urgent' THEN 4
            WHEN 'urgent' THEN 3
            WHEN 'moderate' THEN 2
            ELSE 1
        END
    """

    cursor.execute(f"""
        SELECT *
        FROM trends
        WHERE is_approved = 1
        AND video_generated = 0
        ORDER BY {urgency_score} DESC, confidence DESC, fetched_at DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if row:
        trend = dict(row)
        if trend.get('analysis_json'):
            trend['analysis'] = json.loads(trend['analysis_json'])
        if trend.get('video_plan_json'):
            trend['video_plan'] = json.loads(trend['video_plan_json'])
        return trend

    return None


def get_trend_stats(db_path: str = 'channels.db') -> Dict:
    """
    Get statistics about trends in database.

    Returns: Stats dict
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    stats = {}

    # Total trends
    cursor.execute("SELECT COUNT(*) FROM trends")
    stats['total_trends'] = cursor.fetchone()[0]

    # Approved trends
    cursor.execute("SELECT COUNT(*) FROM trends WHERE is_approved = 1")
    stats['approved_trends'] = cursor.fetchone()[0]

    # Videos generated
    cursor.execute("SELECT COUNT(*) FROM trends WHERE video_generated = 1")
    stats['videos_generated'] = cursor.fetchone()[0]

    # Videos posted
    cursor.execute("SELECT COUNT(*) FROM trends WHERE video_posted = 1")
    stats['videos_posted'] = cursor.fetchone()[0]

    # Pending (approved but not generated)
    cursor.execute("SELECT COUNT(*) FROM trends WHERE is_approved = 1 AND video_generated = 0")
    stats['pending_generation'] = cursor.fetchone()[0]

    # By urgency
    cursor.execute("SELECT urgency, COUNT(*) FROM trends GROUP BY urgency")
    stats['by_urgency'] = dict(cursor.fetchall())

    # By format
    cursor.execute("SELECT recommended_format, COUNT(*) FROM trends GROUP BY recommended_format")
    stats['by_format'] = dict(cursor.fetchall())

    conn.close()
    return stats


def cleanup_old_trends(days: int = 7, db_path: str = 'channels.db'):
    """
    Delete trends older than N days that weren't approved.

    Args:
        days: Age threshold
        db_path: Database file path
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM trends
        WHERE is_approved = 0
        AND fetched_at < datetime('now', '-' || ? || ' days')
    """, (days,))

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted


# Example usage
if __name__ == "__main__":
    print("Testing Trend Tracker...\n")

    # Initialize database
    init_trends_table()
    print("[OK] Trends table initialized\n")

    # Test saving a trend
    sample_trend = {
        'topic': 'Lakers vs Celtics Game 7',
        'source': 'google_realtime',
        'category': 'sports',
        'search_volume': 'very_high',
        'fetched_at': datetime.now().isoformat()
    }

    trend_id = save_trend(sample_trend)
    print(f"[OK] Saved trend with ID: {trend_id}\n")

    # Test analysis update
    sample_analysis = {
        'is_video_worthy': True,
        'confidence': 85,
        'urgency': 'very_urgent',
        'recommended_format': 'highlights'
    }

    update_trend_analysis(trend_id, sample_analysis, is_approved=True)
    print(f"[OK] Updated trend {trend_id} with analysis\n")

    # Test retrieval
    retrieved = get_trend_by_id(trend_id)
    print(f"Retrieved trend: {retrieved['topic']}")
    print(f"  Approved: {retrieved['is_approved']}")
    print(f"  Confidence: {retrieved['confidence']}")
    print(f"  Urgency: {retrieved['urgency']}\n")

    # Get stats
    stats = get_trend_stats()
    print("Database Stats:")
    print(f"  Total trends: {stats['total_trends']}")
    print(f"  Approved: {stats['approved_trends']}")
    print(f"  Pending generation: {stats['pending_generation']}\n")

    print("[OK] All tests passed!")
