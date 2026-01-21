#!/usr/bin/env python3
"""
FILE CLEANUP SYSTEM
Automatically removes old, failed, and temporary video files.
Recovers disk space from 8000+ abandoned files.
"""

import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List
import sqlite3


def get_posted_video_paths() -> set:
    """
    Get file paths of all posted videos (these should be kept).

    Returns: Set of file paths to keep
    """
    conn = sqlite3.connect('channels.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT video_path
        FROM videos
        WHERE status='posted' AND video_path IS NOT NULL
    """)

    paths = set()
    for row in cursor.fetchall():
        video_path = row[0]
        if video_path and os.path.exists(video_path):
            paths.add(os.path.abspath(video_path))

    conn.close()
    return paths


def scan_output_directory(days_old: int = 7) -> Dict:
    """
    Scan output directory for files that can be deleted.

    Args:
        days_old: Delete files older than this many days

    Returns: Scan report
    """
    if not os.path.exists('outputs'):
        return {
            'total_files': 0,
            'total_size_mb': 0,
            'deletable_files': 0,
            'deletable_size_mb': 0,
            'categories': {}
        }

    posted_paths = get_posted_video_paths()
    cutoff_time = datetime.now() - timedelta(days=days_old)

    report = {
        'total_files': 0,
        'total_size_mb': 0,
        'deletable_files': 0,
        'deletable_size_mb': 0,
        'categories': {
            'posted_videos': {'count': 0, 'size_mb': 0},
            'old_temp_files': {'count': 0, 'size_mb': 0},
            'failed_videos': {'count': 0, 'size_mb': 0},
            'audio_clips': {'count': 0, 'size_mb': 0}
        },
        'files_to_delete': []
    }

    for root, dirs, files in os.walk('outputs'):
        for filename in files:
            filepath = os.path.join(root, filename)
            abs_path = os.path.abspath(filepath)

            try:
                stat = os.stat(filepath)
                file_size_mb = stat.st_size / (1024 * 1024)
                file_time = datetime.fromtimestamp(stat.st_mtime)
                file_age_days = (datetime.now() - file_time).days

                report['total_files'] += 1
                report['total_size_mb'] += file_size_mb

                # Categorize file
                is_posted = abs_path in posted_paths
                is_temp = not filename.endswith('_FINAL.mp4')
                is_old = file_time < cutoff_time

                if is_posted:
                    # Keep posted videos
                    report['categories']['posted_videos']['count'] += 1
                    report['categories']['posted_videos']['size_mb'] += file_size_mb

                elif filename.endswith('.mp3') or filename.endswith('.wav'):
                    # Audio clips (always deletable if old)
                    if is_old:
                        report['categories']['audio_clips']['count'] += 1
                        report['categories']['audio_clips']['size_mb'] += file_size_mb
                        report['deletable_files'] += 1
                        report['deletable_size_mb'] += file_size_mb
                        report['files_to_delete'].append({
                            'path': filepath,
                            'size_mb': file_size_mb,
                            'age_days': file_age_days,
                            'category': 'audio_clips'
                        })

                elif is_temp and is_old:
                    # Old temporary files
                    report['categories']['old_temp_files']['count'] += 1
                    report['categories']['old_temp_files']['size_mb'] += file_size_mb
                    report['deletable_files'] += 1
                    report['deletable_size_mb'] += file_size_mb
                    report['files_to_delete'].append({
                        'path': filepath,
                        'size_mb': file_size_mb,
                        'age_days': file_age_days,
                        'category': 'old_temp_files'
                    })

                elif filename.endswith('_FINAL.mp4') and not is_posted and is_old:
                    # Final videos that were never posted
                    report['categories']['failed_videos']['count'] += 1
                    report['categories']['failed_videos']['size_mb'] += file_size_mb
                    report['deletable_files'] += 1
                    report['deletable_size_mb'] += file_size_mb
                    report['files_to_delete'].append({
                        'path': filepath,
                        'size_mb': file_size_mb,
                        'age_days': file_age_days,
                        'category': 'failed_videos'
                    })

            except Exception as e:
                print(f"   [WARNING]  Error scanning {filepath}: {e}")

    return report


def cleanup_old_files(days_old: int = 7, dry_run: bool = True) -> Dict:
    """
    Delete old temporary and failed video files.

    Args:
        days_old: Delete files older than this many days
        dry_run: If True, only simulate deletion

    Returns: Cleanup report
    """
    report = scan_output_directory(days_old)

    deleted_count = 0
    deleted_size_mb = 0
    errors = []

    if not dry_run:
        for file_info in report['files_to_delete']:
            filepath = file_info['path']

            try:
                os.remove(filepath)
                deleted_count += 1
                deleted_size_mb += file_info['size_mb']
            except Exception as e:
                errors.append({
                    'file': filepath,
                    'error': str(e)
                })

    return {
        'dry_run': dry_run,
        'files_scanned': report['total_files'],
        'total_size_mb': round(report['total_size_mb'], 2),
        'files_deleted': deleted_count if not dry_run else 0,
        'files_to_delete': len(report['files_to_delete']) if dry_run else 0,
        'space_freed_mb': round(deleted_size_mb, 2) if not dry_run else round(report['deletable_size_mb'], 2),
        'errors': errors,
        'categories': report['categories']
    }


def cleanup_failed_video_records(days_old: int = 30) -> Dict:
    """
    Delete failed video records from database.

    Args:
        days_old: Delete records older than this many days

    Returns: Cleanup report
    """
    conn = sqlite3.connect('channels.db')
    cursor = conn.cursor()

    # Get count before deletion
    cursor.execute("""
        SELECT COUNT(*)
        FROM videos
        WHERE status='failed'
        AND created_at < datetime('now', '-' || ? || ' days')
    """, (days_old,))

    count_before = cursor.fetchone()[0]

    # Delete old failed records
    cursor.execute("""
        DELETE FROM videos
        WHERE status='failed'
        AND created_at < datetime('now', '-' || ? || ' days')
    """, (days_old,))

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return {
        'failed_records_found': count_before,
        'failed_records_deleted': deleted,
        'days_threshold': days_old
    }


def get_disk_usage_report() -> Dict:
    """
    Get current disk usage report for outputs directory.

    Returns: Usage report
    """
    if not os.path.exists('outputs'):
        return {
            'exists': False
        }

    total_size = 0
    file_count = 0

    for root, dirs, files in os.walk('outputs'):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                total_size += os.path.getsize(filepath)
                file_count += 1
            except:
                pass

    return {
        'exists': True,
        'total_files': file_count,
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2)
    }


# Testing and CLI
if __name__ == "__main__":
    import sys

    print("=" * 70)
    print("FILE CLEANUP SYSTEM")
    print("=" * 70)

    # Get disk usage
    print("\n[CHART] Current Disk Usage:")
    usage = get_disk_usage_report()
    if usage['exists']:
        print(f"   Total Files: {usage['total_files']:,}")
        print(f"   Total Size: {usage['total_size_gb']:.2f} GB ({usage['total_size_mb']:.0f} MB)")
    else:
        print("   outputs/ directory not found")

    # Scan for deletable files
    print("\n Scanning for deletable files (7+ days old)...")
    report = cleanup_old_files(days_old=7, dry_run=True)

    print(f"\n   Files Scanned: {report['files_scanned']:,}")
    print(f"   Total Size: {report['total_size_mb']:.2f} MB")
    print(f"\n   Deletable Files: {report['files_to_delete']:,}")
    print(f"   Recoverable Space: {report['space_freed_mb']:.2f} MB\n")

    print("   Breakdown by category:")
    for category, data in report['categories'].items():
        if data['count'] > 0:
            print(f"      {category:20s}: {data['count']:4d} files ({data['size_mb']:6.1f} MB)")

    # Check for confirmation
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        print("\n[WARNING]  EXECUTING CLEANUP (this will permanently delete files)...")
        result = cleanup_old_files(days_old=7, dry_run=False)

        print(f"\n[OK] Cleanup Complete!")
        print(f"   Files Deleted: {result['files_deleted']:,}")
        print(f"   Space Freed: {result['space_freed_mb']:.2f} MB")

        if result['errors']:
            print(f"\n   [WARNING]  {len(result['errors'])} errors occurred")

        # Also cleanup database
        print("\n  Cleaning up failed video records...")
        db_result = cleanup_failed_video_records(days_old=30)
        print(f"   Deleted {db_result['failed_records_deleted']} old failed records")

    else:
        print("\n[IDEA] To execute cleanup, run:")
        print("   python3 file_cleanup.py --execute")

    print("\n" + "=" * 70)
