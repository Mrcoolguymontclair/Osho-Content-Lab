#!/usr/bin/env python3
"""
DUPLICATE VIDEO DETECTOR & PREVENTER
Prevents duplicate or near-duplicate videos from being generated.

Uses multiple detection methods:
1. Exact title match
2. Similar title match (fuzzy matching)
3. Topic similarity
4. Recent video lookback (don't repeat within N days)
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher


def normalize_title(title: str) -> str:
    """
    Normalize title for comparison.

    Removes:
    - Capitalization differences
    - Punctuation
    - Extra whitespace
    - Common prefixes like "TOP 10", "TOP 5", etc.
    """
    # Convert to lowercase
    normalized = title.lower()

    # Remove common prefixes and patterns
    prefixes_to_remove = [
        'top 10 ', 'top 5 ', 'top 3 ', 'top ',
        'best ', 'worst ', 'most ',
        'ranking ', 'ranked', '!',
        'you won\'t believe #1 — ',
        'you won\'t believe #1 - ',
        'best things ranked: '
    ]

    for prefix in prefixes_to_remove:
        normalized = normalized.replace(prefix, '')

    # Remove punctuation
    for char in '!.,?;:"-()[]{}':
        normalized = normalized.replace(char, ' ')

    # Remove extra whitespace
    normalized = ' '.join(normalized.split())

    return normalized.strip()


def calculate_similarity(title1: str, title2: str) -> float:
    """
    Calculate similarity between two titles (0.0 to 1.0).

    Uses SequenceMatcher for fuzzy string matching.

    Returns: Similarity score (1.0 = identical, 0.0 = completely different)
    """
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)

    return SequenceMatcher(None, norm1, norm2).ratio()


def is_duplicate_title(title: str, channel_id: int,
                       similarity_threshold: float = 0.85,
                       lookback_days: int = 30,
                       db_path: str = 'channels.db') -> Tuple[bool, Optional[Dict]]:
    """
    Check if title is a duplicate or near-duplicate of existing videos.

    Args:
        title: Video title to check
        channel_id: Channel ID
        similarity_threshold: Threshold for fuzzy matching (0.85 = 85% similar)
        lookback_days: How many days back to check (default: 30 days)
        db_path: Database path

    Returns: (is_duplicate, duplicate_video_dict)
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get recent videos for this channel
    cursor.execute("""
        SELECT id, title, topic, created_at, status
        FROM videos
        WHERE channel_id = ?
        AND status IN ('ready', 'uploaded', 'posting', 'scheduled', 'posted')
        AND created_at >= datetime('now', '-' || ? || ' days')
        ORDER BY created_at DESC
    """, (channel_id, lookback_days))

    recent_videos = cursor.fetchall()
    conn.close()

    # Check for exact match (after normalization)
    normalized_title = normalize_title(title)

    for video in recent_videos:
        existing_title = video['title']
        normalized_existing = normalize_title(existing_title)

        # Exact match after normalization
        if normalized_title == normalized_existing:
            return True, {
                'id': video['id'],
                'title': existing_title,
                'topic': video['topic'],
                'created_at': video['created_at'],
                'match_type': 'exact',
                'similarity': 1.0
            }

        # Fuzzy match (similarity above threshold)
        similarity = calculate_similarity(title, existing_title)

        if similarity >= similarity_threshold:
            return True, {
                'id': video['id'],
                'title': existing_title,
                'topic': video['topic'],
                'created_at': video['created_at'],
                'match_type': 'similar',
                'similarity': similarity
            }

    return False, None


def is_duplicate_topic(topic: str, channel_id: int,
                       lookback_days: int = 7,
                       db_path: str = 'channels.db') -> Tuple[bool, Optional[Dict]]:
    """
    Check if topic has been used recently.

    Prevents repeating the same topic within N days.

    Args:
        topic: Video topic
        channel_id: Channel ID
        lookback_days: How many days back to check (default: 7 days)
        db_path: Database path

    Returns: (is_duplicate, duplicate_video_dict)
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Normalize topic for comparison
    normalized_topic = topic.lower().strip()

    # Get recent videos with this topic
    cursor.execute("""
        SELECT id, title, topic, created_at
        FROM videos
        WHERE channel_id = ?
        AND LOWER(topic) = ?
        AND status IN ('ready', 'uploaded', 'posting', 'scheduled', 'posted')
        AND created_at >= datetime('now', '-' || ? || ' days')
        ORDER BY created_at DESC
        LIMIT 1
    """, (channel_id, normalized_topic, lookback_days))

    duplicate = cursor.fetchone()
    conn.close()

    if duplicate:
        return True, {
            'id': duplicate['id'],
            'title': duplicate['title'],
            'topic': duplicate['topic'],
            'created_at': duplicate['created_at'],
            'match_type': 'topic'
        }

    return False, None


def get_duplicate_statistics(channel_id: int,
                            db_path: str = 'channels.db') -> Dict:
    """
    Get statistics about duplicate videos for a channel.

    Returns: Dict with duplicate stats
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    stats = {}

    # Total videos
    cursor.execute("""
        SELECT COUNT(*) FROM videos
        WHERE channel_id = ?
        AND status IN ('ready', 'uploaded', 'posting', 'scheduled', 'posted')
    """, (channel_id,))
    stats['total_videos'] = cursor.fetchone()[0]

    # Duplicate titles
    cursor.execute("""
        SELECT title, COUNT(*) as count
        FROM videos
        WHERE channel_id = ?
        AND status IN ('ready', 'uploaded', 'posting', 'scheduled', 'posted')
        GROUP BY title
        HAVING count > 1
        ORDER BY count DESC
    """, (channel_id,))
    duplicates = cursor.fetchall()

    stats['duplicate_titles'] = len(duplicates)
    stats['total_duplicates'] = sum(count - 1 for title, count in duplicates)  # Subtract 1 for original

    # Most duplicated
    if duplicates:
        stats['most_duplicated'] = [
            {'title': title, 'count': count}
            for title, count in duplicates[:10]
        ]
    else:
        stats['most_duplicated'] = []

    # Duplicate percentage
    if stats['total_videos'] > 0:
        stats['duplicate_percentage'] = (stats['total_duplicates'] / stats['total_videos']) * 100
    else:
        stats['duplicate_percentage'] = 0.0

    conn.close()
    return stats


def find_all_duplicates(channel_id: int,
                       similarity_threshold: float = 0.85,
                       db_path: str = 'channels.db') -> List[Dict]:
    """
    Find all duplicate videos for a channel.

    Returns: List of duplicate groups
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all videos
    cursor.execute("""
        SELECT id, title, topic, created_at, status
        FROM videos
        WHERE channel_id = ?
        AND status IN ('ready', 'uploaded', 'posting', 'scheduled', 'posted')
        ORDER BY created_at DESC
    """, (channel_id,))

    videos = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Group duplicates
    duplicate_groups = []
    processed = set()

    for i, video1 in enumerate(videos):
        if video1['id'] in processed:
            continue

        group = [video1]
        processed.add(video1['id'])

        # Find similar videos
        for video2 in videos[i+1:]:
            if video2['id'] in processed:
                continue

            similarity = calculate_similarity(video1['title'], video2['title'])

            if similarity >= similarity_threshold:
                group.append(video2)
                processed.add(video2['id'])

        # Only include groups with 2+ videos
        if len(group) > 1:
            duplicate_groups.append({
                'title_pattern': normalize_title(group[0]['title']),
                'count': len(group),
                'videos': group,
                'similarity': similarity
            })

    return sorted(duplicate_groups, key=lambda x: x['count'], reverse=True)


def cleanup_duplicates(channel_id: int,
                      keep_newest: bool = True,
                      dry_run: bool = True,
                      db_path: str = 'channels.db') -> Dict:
    """
    Remove duplicate videos from database.

    Args:
        channel_id: Channel ID
        keep_newest: Keep newest video (True) or oldest (False)
        dry_run: If True, don't actually delete, just report
        db_path: Database path

    Returns: Dict with cleanup stats
    """
    duplicate_groups = find_all_duplicates(channel_id, db_path=db_path)

    to_delete = []
    to_keep = []

    for group in duplicate_groups:
        videos = group['videos']

        # Sort by date
        if keep_newest:
            videos.sort(key=lambda x: x['created_at'], reverse=True)
        else:
            videos.sort(key=lambda x: x['created_at'])

        # Keep first, delete rest
        to_keep.append(videos[0])
        to_delete.extend(videos[1:])

    if not dry_run and to_delete:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for video in to_delete:
            cursor.execute("UPDATE videos SET status = 'deleted' WHERE id = ?", (video['id'],))

        conn.commit()
        conn.close()

    return {
        'total_duplicates': len(to_delete),
        'kept': len(to_keep),
        'deleted': len(to_delete) if not dry_run else 0,
        'dry_run': dry_run,
        'to_delete': to_delete if dry_run else []
    }


# Example usage and testing
if __name__ == "__main__":
    print("Testing Duplicate Detector...\n")

    # Test title normalization
    test_titles = [
        "TOP 10 MOST EXTREME DESERT LANDSCAPES ON EARTH RANKED!",
        "Most Extreme Desert Landscapes on Earth",
        "top 10 extreme desert landscapes ranked",
        "Ranking Most Extreme Desert Landscapes"
    ]

    print("Title Normalization:")
    for title in test_titles:
        print(f"  Original: {title}")
        print(f"  Normalized: {normalize_title(title)}")
        print()

    # Test similarity
    print("\nSimilarity Testing:")
    title1 = "TOP 10 MOST EXTREME DESERT LANDSCAPES ON EARTH RANKED!"
    title2 = "TOP 10 MOST EXTREME DESERT LANDSCAPES ON EARTH RANKED!"
    similarity = calculate_similarity(title1, title2)
    print(f"  Title 1: {title1}")
    print(f"  Title 2: {title2}")
    print(f"  Similarity: {similarity:.2%}")
    print()

    # Get statistics for RankRiot (channel_id = 2)
    print("\nDuplicate Statistics for RankRiot:")
    stats = get_duplicate_statistics(2)
    print(f"  Total videos: {stats['total_videos']}")
    print(f"  Duplicate titles: {stats['duplicate_titles']}")
    print(f"  Total duplicates: {stats['total_duplicates']}")
    print(f"  Duplicate %: {stats['duplicate_percentage']:.1f}%")
    print()

    if stats['most_duplicated']:
        print("  Most duplicated titles:")
        for item in stats['most_duplicated'][:5]:
            print(f"    - {item['title']} (x{item['count']})")

    print("\n✅ Tests complete!")
