#!/usr/bin/env python3
"""
CHANNEL & DATABASE MANAGER
Handles all database operations for multi-channel YouTube automation.
SQLite database for channel configs, video history, logs, and error tracking.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from threading import Lock

# Database file path
DB_PATH = "channels.db"
db_lock = Lock()  # Thread-safe database access

# ==============================================================================
# Database Initialization
# ==============================================================================

def init_database():
    """Create database tables if they don't exist"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Channels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                theme TEXT NOT NULL,
                tone TEXT NOT NULL,
                style TEXT NOT NULL,
                other_info TEXT DEFAULT '',
                post_interval_minutes INTEGER DEFAULT 60,
                music_volume INTEGER DEFAULT 15,
                is_active BOOLEAN DEFAULT 0,
                token_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_post_at TIMESTAMP,
                next_post_at TIMESTAMP
            )
        """)

        # Videos table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                title TEXT,
                topic TEXT,
                video_path TEXT,
                youtube_url TEXT,
                status TEXT DEFAULT 'pending',
                scheduled_post_time TIMESTAMP,
                actual_post_time TIMESTAMP,
                error_count INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE
            )
        """)

        # Logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT DEFAULT '',
                FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE
            )
        """)

        # Error tracker table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_tracker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                error_type TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                last_occurred TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE,
                UNIQUE(channel_id, error_type)
            )
        """)

        conn.commit()
        conn.close()

# Initialize on import
init_database()

# ==============================================================================
# Channel Management
# ==============================================================================

def add_channel(
    name: str,
    theme: str,
    tone: str = "Exciting",
    style: str = "Fast-paced",
    other_info: str = "",
    post_interval_minutes: int = 60,
    music_volume: int = 15
) -> Tuple[bool, str]:
    """
    Add a new channel.
    Returns: (success, message)
    """
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO channels (name, theme, tone, style, other_info, post_interval_minutes, music_volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, theme, tone, style, other_info, post_interval_minutes, music_volume))

            conn.commit()
            channel_id = cursor.lastrowid
            conn.close()

        add_log(channel_id, "info", "channel", f"Channel '{name}' created")
        return True, f"Channel '{name}' created successfully!"

    except sqlite3.IntegrityError:
        return False, f"Channel '{name}' already exists"
    except Exception as e:
        return False, f"Error creating channel: {str(e)}"

def get_channel(channel_id: int) -> Optional[Dict]:
    """Get channel by ID"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

def get_channel_by_name(name: str) -> Optional[Dict]:
    """Get channel by name"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM channels WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

def get_all_channels() -> List[Dict]:
    """Get all channels"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM channels ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

def get_active_channels() -> List[Dict]:
    """Get all active channels"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM channels WHERE is_active = 1")
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

def update_channel(channel_id: int, **kwargs) -> bool:
    """Update channel fields"""
    allowed_fields = ['name', 'theme', 'tone', 'style', 'other_info', 'post_interval_minutes', 'music_volume', 'is_active', 'token_file', 'last_post_at', 'next_post_at', 'video_type']

    updates = []
    values = []

    for key, value in kwargs.items():
        if key in allowed_fields:
            updates.append(f"{key} = ?")
            values.append(value)

    if not updates:
        return False

    values.append(channel_id)

    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute(f"""
                UPDATE channels
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)

            conn.commit()
            conn.close()

        return True
    except:
        return False

def delete_channel(channel_id: int) -> bool:
    """Delete channel and all associated data"""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
            conn.commit()
            conn.close()

        return True
    except:
        return False

def activate_channel(channel_id: int) -> bool:
    """Activate a channel for posting"""
    channel = get_channel(channel_id)
    if not channel:
        return False

    # Calculate next post time
    next_post = datetime.now() + timedelta(minutes=channel['post_interval_minutes'])

    update_channel(channel_id, is_active=True, next_post_at=next_post.isoformat())
    add_log(channel_id, "info", "channel", "Channel activated")
    return True

def deactivate_channel(channel_id: int) -> bool:
    """Deactivate a channel"""
    update_channel(channel_id, is_active=False)
    add_log(channel_id, "info", "channel", "Channel deactivated")
    return True

# ==============================================================================
# Video Management
# ==============================================================================

def add_video(
    channel_id: int,
    title: str,
    topic: str,
    video_path: str = "",
    status: str = "generating",
    scheduled_post_time: datetime = None
) -> int:
    """
    Add a new video record.
    Returns: video_id
    """
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO videos (channel_id, title, topic, video_path, status, scheduled_post_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (channel_id, title, topic, video_path, status, scheduled_post_time.isoformat() if scheduled_post_time else None))

        conn.commit()
        video_id = cursor.lastrowid
        conn.close()

    return video_id

def update_video(video_id: int, **kwargs) -> bool:
    """Update video fields"""
    allowed_fields = ['title', 'topic', 'video_path', 'youtube_url', 'status', 'actual_post_time', 'error_count', 'error_message']

    updates = []
    values = []

    for key, value in kwargs.items():
        if key in allowed_fields:
            updates.append(f"{key} = ?")
            values.append(value)

    if not updates:
        return False

    values.append(video_id)

    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute(f"""
                UPDATE videos
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)

            conn.commit()
            conn.close()

        return True
    except:
        return False

def get_video(video_id: int) -> Optional[Dict]:
    """Get video by ID"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

def get_channel_videos(channel_id: int, limit: int = 50) -> List[Dict]:
    """Get recent videos for a channel"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM videos
            WHERE channel_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (channel_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

def get_next_scheduled_video(channel_id: int) -> Optional[Dict]:
    """Get next video scheduled to post"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM videos
            WHERE channel_id = ? AND status = 'ready'
            ORDER BY scheduled_post_time ASC
            LIMIT 1
        """, (channel_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

# ==============================================================================
# Logging
# ==============================================================================

def add_log(channel_id: int, level: str, category: str, message: str, details: str = ""):
    """Add a log entry"""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO logs (channel_id, level, category, message, details)
                VALUES (?, ?, ?, ?, ?)
            """, (channel_id, level, category, message, details))

            conn.commit()
            conn.close()

        # Also print to console for debugging
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level.upper()}] [CH{channel_id}] [{category}] {message}")

    except Exception as e:
        print(f"Error logging to database: {e}")

def get_channel_logs(channel_id: int, limit: int = 100) -> List[Dict]:
    """Get recent logs for a channel"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM logs
            WHERE channel_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (channel_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

def clear_old_logs(days: int = 7):
    """Delete logs older than specified days"""
    cutoff = datetime.now() - timedelta(days=days)

    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff.isoformat(),))
        deleted = cursor.rowcount

        conn.commit()
        conn.close()

    return deleted

# ==============================================================================
# Error Tracking
# ==============================================================================

def track_error(channel_id: int, error_type: str):
    """Increment error count for a specific error type"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO error_tracker (channel_id, error_type, count, last_occurred)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(channel_id, error_type)
            DO UPDATE SET
                count = count + 1,
                last_occurred = CURRENT_TIMESTAMP
        """, (channel_id, error_type))

        conn.commit()

        # Get updated count
        cursor.execute("""
            SELECT count FROM error_tracker
            WHERE channel_id = ? AND error_type = ?
        """, (channel_id, error_type))

        row = cursor.fetchone()
        count = row[0] if row else 0

        conn.close()

    return count

def reset_error_tracker(channel_id: int, error_type: str = None):
    """Reset error count (for specific type or all)"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if error_type:
            cursor.execute("DELETE FROM error_tracker WHERE channel_id = ? AND error_type = ?", (channel_id, error_type))
        else:
            cursor.execute("DELETE FROM error_tracker WHERE channel_id = ?", (channel_id,))

        conn.commit()
        conn.close()

def get_error_stats(channel_id: int) -> List[Dict]:
    """Get all error statistics for a channel"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM error_tracker
            WHERE channel_id = ?
            ORDER BY count DESC
        """, (channel_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

# ==============================================================================
# Statistics
# ==============================================================================

def get_channel_stats(channel_id: int) -> Dict:
    """Get channel statistics"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Total videos
        cursor.execute("SELECT COUNT(*) FROM videos WHERE channel_id = ?", (channel_id,))
        total_videos = cursor.fetchone()[0]

        # Posted videos
        cursor.execute("SELECT COUNT(*) FROM videos WHERE channel_id = ? AND status = 'posted'", (channel_id,))
        posted_videos = cursor.fetchone()[0]

        # Failed videos
        cursor.execute("SELECT COUNT(*) FROM videos WHERE channel_id = ? AND status = 'failed'", (channel_id,))
        failed_videos = cursor.fetchone()[0]

        # Last post time
        cursor.execute("SELECT MAX(actual_post_time) FROM videos WHERE channel_id = ? AND status = 'posted'", (channel_id,))
        last_post = cursor.fetchone()[0]

        conn.close()

    return {
        'total_videos': total_videos,
        'posted_videos': posted_videos,
        'failed_videos': failed_videos,
        'last_post_time': last_post
    }
