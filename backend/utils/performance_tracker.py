"""
Performance Tracking System
Measures system improvements over time and provides analytics.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics
from time_formatter import now_chicago, format_time_chicago, parse_time_to_chicago

@dataclass
class PerformanceSnapshot:
    """Single point-in-time performance measurement."""
    timestamp: str
    success_rate: float
    total_videos: int
    successful_videos: int
    failed_videos: int
    avg_views: float
    avg_likes: float
    avg_comments: float
    avg_title_score: float
    disk_usage_mb: float
    auth_failures: int
    api_failures: int

@dataclass
class PerformanceComparison:
    """Before/after comparison of metrics."""
    metric_name: str
    before_value: float
    after_value: float
    improvement_percent: float
    trend: str  # "improving", "declining", "stable"

class PerformanceTracker:
    """Tracks and analyzes system performance metrics."""

    def __init__(self, db_path: str = "channels.db"):
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        """Create performance tracking tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Performance snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                success_rate REAL,
                total_videos INTEGER,
                successful_videos INTEGER,
                failed_videos INTEGER,
                avg_views REAL,
                avg_likes REAL,
                avg_comments REAL,
                avg_title_score REAL,
                disk_usage_mb REAL,
                auth_failures INTEGER,
                api_failures INTEGER,
                metadata TEXT
            )
        """)

        # Video performance tracking (enhanced)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER,
                timestamp TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                watch_time_minutes REAL DEFAULT 0,
                title_score INTEGER DEFAULT 0,
                has_hook BOOLEAN DEFAULT 0,
                has_quality_enhancements BOOLEAN DEFAULT 0,
                FOREIGN KEY (video_id) REFERENCES videos(id)
            )
        """)

        # A/B test results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ab_test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                variant TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                video_id INTEGER,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                title_score INTEGER DEFAULT 0,
                metadata TEXT,
                FOREIGN KEY (video_id) REFERENCES videos(id)
            )
        """)

        # System improvements log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvement_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT,
                expected_impact TEXT,
                metadata TEXT
            )
        """)

        conn.commit()
        conn.close()

    def capture_snapshot(self, metadata: Optional[Dict] = None) -> PerformanceSnapshot:
        """Capture current system performance snapshot."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get overall video stats
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status='posted' THEN 1 ELSE 0 END) as posted,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
            FROM videos
        """)
        total, posted, failed = cursor.fetchone()
        success_rate = (posted / total * 100) if total > 0 else 0

        # Get engagement averages (from videos with analytics data)
        cursor.execute("""
            SELECT
                AVG(views) as avg_views,
                AVG(likes) as avg_likes,
                AVG(comments) as avg_comments
            FROM videos
            WHERE status='posted' AND views IS NOT NULL
        """)
        avg_views, avg_likes, avg_comments = cursor.fetchone()
        avg_views = avg_views or 0
        avg_likes = avg_likes or 0
        avg_comments = avg_comments or 0

        # Get average title score (if available)
        cursor.execute("""
            SELECT AVG(title_score)
            FROM video_performance
            WHERE title_score > 0
        """)
        result = cursor.fetchone()
        avg_title_score = result[0] if result and result[0] else 0

        # Get failure breakdown
        cursor.execute("""
            SELECT
                SUM(CASE WHEN error_message LIKE '%auth%' THEN 1 ELSE 0 END) as auth_fails,
                SUM(CASE WHEN error_message LIKE '%quota%' OR error_message LIKE '%api%' THEN 1 ELSE 0 END) as api_fails
            FROM videos
            WHERE status='failed'
        """)
        result = cursor.fetchone()
        auth_failures = result[0] if result and result[0] else 0
        api_failures = result[1] if result and result[1] else 0

        # Get disk usage (rough estimate from output directory)
        import os
        disk_usage_mb = 0
        output_dir = "output"
        if os.path.exists(output_dir):
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    if os.path.exists(filepath):
                        disk_usage_mb += os.path.getsize(filepath) / (1024 * 1024)

        snapshot = PerformanceSnapshot(
            timestamp=format_time_chicago(now_chicago(), "full"),
            success_rate=success_rate,
            total_videos=total,
            successful_videos=posted,
            failed_videos=failed,
            avg_views=avg_views,
            avg_likes=avg_likes,
            avg_comments=avg_comments,
            avg_title_score=avg_title_score,
            disk_usage_mb=disk_usage_mb,
            auth_failures=auth_failures,
            api_failures=api_failures
        )

        # Save to database
        cursor.execute("""
            INSERT INTO performance_snapshots
            (timestamp, success_rate, total_videos, successful_videos, failed_videos,
             avg_views, avg_likes, avg_comments, avg_title_score, disk_usage_mb,
             auth_failures, api_failures, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot.timestamp, snapshot.success_rate, snapshot.total_videos,
            snapshot.successful_videos, snapshot.failed_videos, snapshot.avg_views,
            snapshot.avg_likes, snapshot.avg_comments, snapshot.avg_title_score,
            snapshot.disk_usage_mb, snapshot.auth_failures, snapshot.api_failures,
            json.dumps(metadata) if metadata else None
        ))

        conn.commit()
        conn.close()

        return snapshot

    def log_improvement_event(self, event_type: str, description: str, expected_impact: str, metadata: Optional[Dict] = None):
        """Log when an improvement is deployed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO improvement_events (timestamp, event_type, description, expected_impact, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            format_time_chicago(now_chicago(), "full"),
            event_type,
            description,
            expected_impact,
            json.dumps(metadata) if metadata else None
        ))

        conn.commit()
        conn.close()

    def get_recent_snapshots(self, hours: int = 24) -> List[PerformanceSnapshot]:
        """Get snapshots from the last N hours."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = now_chicago() - timedelta(hours=hours)
        cutoff_str = format_time_chicago(cutoff, "full")

        cursor.execute("""
            SELECT timestamp, success_rate, total_videos, successful_videos, failed_videos,
                   avg_views, avg_likes, avg_comments, avg_title_score, disk_usage_mb,
                   auth_failures, api_failures
            FROM performance_snapshots
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """, (cutoff_str,))

        snapshots = []
        for row in cursor.fetchall():
            snapshots.append(PerformanceSnapshot(*row))

        conn.close()
        return snapshots

    def compare_periods(self, before_hours: int = 168, after_hours: int = 24) -> List[PerformanceComparison]:
        """Compare performance between two time periods.

        Args:
            before_hours: Hours to look back for "before" period (default 168 = 1 week ago)
            after_hours: Hours to look back for "after" period (default 24 = last day)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = now_chicago()

        # Before period: 1 week ago to 1 week + 24 hours ago
        before_end = now - timedelta(hours=before_hours)
        before_start = before_end - timedelta(hours=after_hours)

        # After period: last 24 hours
        after_end = now
        after_start = now - timedelta(hours=after_hours)

        def get_period_stats(start: datetime, end: datetime) -> Dict:
            start_str = format_time_chicago(start, "full")
            end_str = format_time_chicago(end, "full")

            cursor.execute("""
                SELECT
                    AVG(success_rate) as avg_success_rate,
                    AVG(avg_views) as avg_views,
                    AVG(avg_likes) as avg_likes,
                    AVG(avg_comments) as avg_comments,
                    AVG(avg_title_score) as avg_title_score,
                    AVG(auth_failures) as avg_auth_failures,
                    AVG(api_failures) as avg_api_failures
                FROM performance_snapshots
                WHERE timestamp >= ? AND timestamp <= ?
            """, (start_str, end_str))

            row = cursor.fetchone()
            if not row or row[0] is None:
                return None

            return {
                'success_rate': row[0] or 0,
                'avg_views': row[1] or 0,
                'avg_likes': row[2] or 0,
                'avg_comments': row[3] or 0,
                'avg_title_score': row[4] or 0,
                'auth_failures': row[5] or 0,
                'api_failures': row[6] or 0
            }

        before_stats = get_period_stats(before_start, before_end)
        after_stats = get_period_stats(after_start, after_end)

        conn.close()

        if not before_stats or not after_stats:
            return []

        def calculate_comparison(metric_name: str, before_val: float, after_val: float) -> PerformanceComparison:
            if before_val == 0:
                improvement_percent = 100 if after_val > 0 else 0
            else:
                improvement_percent = ((after_val - before_val) / before_val) * 100

            if improvement_percent > 5:
                trend = "improving"
            elif improvement_percent < -5:
                trend = "declining"
            else:
                trend = "stable"

            return PerformanceComparison(
                metric_name=metric_name,
                before_value=before_val,
                after_value=after_val,
                improvement_percent=improvement_percent,
                trend=trend
            )

        comparisons = [
            calculate_comparison("Success Rate", before_stats['success_rate'], after_stats['success_rate']),
            calculate_comparison("Avg Views", before_stats['avg_views'], after_stats['avg_views']),
            calculate_comparison("Avg Likes", before_stats['avg_likes'], after_stats['avg_likes']),
            calculate_comparison("Avg Comments", before_stats['avg_comments'], after_stats['avg_comments']),
            calculate_comparison("Title Score", before_stats['avg_title_score'], after_stats['avg_title_score']),
            calculate_comparison("Auth Failures", before_stats['auth_failures'], after_stats['auth_failures']),
            calculate_comparison("API Failures", before_stats['api_failures'], after_stats['api_failures']),
        ]

        return comparisons

    def get_top_performing_videos(self, limit: int = 10) -> List[Dict]:
        """Get top performing videos by views."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, views, likes, comments, created_at
            FROM videos
            WHERE status='posted' AND views > 0
            ORDER BY views DESC
            LIMIT ?
        """, (limit,))

        videos = []
        for row in cursor.fetchall():
            videos.append({
                'id': row[0],
                'title': row[1],
                'views': row[2],
                'likes': row[3],
                'comments': row[4],
                'created_at': row[5]
            })

        conn.close()
        return videos

    def get_improvement_timeline(self) -> List[Dict]:
        """Get timeline of improvement events."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT timestamp, event_type, description, expected_impact, metadata
            FROM improvement_events
            ORDER BY timestamp DESC
            LIMIT 50
        """)

        events = []
        for row in cursor.fetchall():
            events.append({
                'timestamp': row[0],
                'event_type': row[1],
                'description': row[2],
                'expected_impact': row[3],
                'metadata': json.loads(row[4]) if row[4] else None
            })

        conn.close()
        return events

    def generate_health_report(self) -> Dict:
        """Generate comprehensive health report with recommendations."""
        snapshot = self.capture_snapshot()
        comparisons = self.compare_periods()
        top_videos = self.get_top_performing_videos(5)

        # Calculate health score (0-100)
        health_score = 0
        if snapshot.success_rate >= 70:
            health_score += 30
        elif snapshot.success_rate >= 50:
            health_score += 20
        elif snapshot.success_rate >= 30:
            health_score += 10

        if snapshot.avg_views >= 100:
            health_score += 25
        elif snapshot.avg_views >= 50:
            health_score += 15
        elif snapshot.avg_views >= 10:
            health_score += 5

        if snapshot.avg_title_score >= 70:
            health_score += 20
        elif snapshot.avg_title_score >= 50:
            health_score += 10

        if snapshot.auth_failures == 0:
            health_score += 15
        elif snapshot.auth_failures < 5:
            health_score += 5

        if snapshot.api_failures < 10:
            health_score += 10
        elif snapshot.api_failures < 20:
            health_score += 5

        # Generate recommendations
        recommendations = []

        if snapshot.success_rate < 70:
            recommendations.append({
                'priority': 'high',
                'issue': f'Low success rate ({snapshot.success_rate:.1f}%)',
                'action': 'Review error logs and enable error recovery system'
            })

        if snapshot.avg_views < 50:
            recommendations.append({
                'priority': 'high',
                'issue': f'Low average views ({snapshot.avg_views:.1f})',
                'action': 'Enable video quality enhancements and title optimization'
            })

        if snapshot.auth_failures > 0:
            recommendations.append({
                'priority': 'critical',
                'issue': f'{snapshot.auth_failures} authentication failures',
                'action': 'Run auth health monitor and re-authenticate channels'
            })

        if snapshot.disk_usage_mb > 5000:
            recommendations.append({
                'priority': 'medium',
                'issue': f'High disk usage ({snapshot.disk_usage_mb:.0f} MB)',
                'action': 'Run file cleanup to remove old temporary files'
            })

        if snapshot.avg_title_score < 60:
            recommendations.append({
                'priority': 'medium',
                'issue': f'Low title scores ({snapshot.avg_title_score:.0f}/100)',
                'action': 'Enable title optimization for better engagement'
            })

        return {
            'health_score': health_score,
            'status': 'healthy' if health_score >= 70 else 'degraded' if health_score >= 40 else 'critical',
            'snapshot': asdict(snapshot),
            'comparisons': [asdict(c) for c in comparisons],
            'top_videos': top_videos,
            'recommendations': recommendations,
            'timestamp': format_time_chicago(now_chicago(), "full")
        }


def log_system_improvements():
    """Log all the improvements we've made to the system."""
    tracker = PerformanceTracker()

    improvements = [
        {
            'event_type': 'infrastructure',
            'description': 'Groq API Failover System - 2 API keys with automatic switching',
            'expected_impact': 'Eliminate 89% of quota-related failures',
            'metadata': {'keys': 2, 'total_quota': 200000}
        },
        {
            'event_type': 'reliability',
            'description': 'Error Recovery System - Exponential backoff retry with smart categorization',
            'expected_impact': 'Auto-recover from 60% of transient failures',
            'metadata': {'max_attempts': 3, 'categories': 4}
        },
        {
            'event_type': 'reliability',
            'description': 'Authentication Health Monitor - Proactive token validation',
            'expected_impact': 'Eliminate all 306 authentication failures (39% of total)',
            'metadata': {'checks': 3}
        },
        {
            'event_type': 'reliability',
            'description': 'Pre-Generation Validator - 6-check validation before generation',
            'expected_impact': 'Prevent 40% of failures before they happen',
            'metadata': {'checks': 6}
        },
        {
            'event_type': 'quality',
            'description': 'Video Quality Enhancer - 7 professional improvements',
            'expected_impact': 'Increase views 3-5x (60 → 200-300 views)',
            'metadata': {'features': ['hooks', 'overlays', 'clips', 'audio', 'motion', 'transitions', 'prompts']}
        },
        {
            'event_type': 'quality',
            'description': 'Title Optimization - 100-point scoring system',
            'expected_impact': 'Increase CTR by 40-60%',
            'metadata': {'scoring_criteria': 7, 'target_score': 70}
        },
        {
            'event_type': 'maintenance',
            'description': 'File Cleanup System - Automated removal of old files',
            'expected_impact': 'Recover 2.3 GB disk space, prevent disk full errors',
            'metadata': {'deletable_files': 699, 'space_freed_mb': 2300}
        },
        {
            'event_type': 'ux',
            'description': 'Time Formatting - Chicago timezone with 12-hour format',
            'expected_impact': 'Improved user experience and log readability',
            'metadata': {'timezone': 'America/Chicago', 'format': '12-hour'}
        },
        {
            'event_type': 'integration',
            'description': 'Unified Video Generator - Single pipeline for all improvements',
            'expected_impact': 'Consistent quality across all video types',
            'metadata': {'integrations': 7}
        },
        {
            'event_type': 'analytics',
            'description': 'Performance Tracking System - Comprehensive metrics and comparisons',
            'expected_impact': 'Data-driven optimization and validation',
            'metadata': {'metrics': 12, 'comparisons': 7}
        }
    ]

    for improvement in improvements:
        tracker.log_improvement_event(**improvement)

    print(f"[OK] Logged {len(improvements)} system improvements")


if __name__ == "__main__":
    # Initialize and log improvements
    log_system_improvements()

    # Generate health report
    tracker = PerformanceTracker()
    report = tracker.generate_health_report()

    print("\n" + "="*60)
    print("SYSTEM HEALTH REPORT")
    print("="*60)
    print(f"\nHealth Score: {report['health_score']}/100 ({report['status'].upper()})")
    print(f"\nCurrent Metrics:")
    print(f"  Success Rate: {report['snapshot']['success_rate']:.1f}%")
    print(f"  Avg Views: {report['snapshot']['avg_views']:.1f}")
    print(f"  Avg Likes: {report['snapshot']['avg_likes']:.1f}")
    print(f"  Title Score: {report['snapshot']['avg_title_score']:.1f}/100")
    print(f"  Disk Usage: {report['snapshot']['disk_usage_mb']:.0f} MB")

    if report['recommendations']:
        print(f"\n[WARNING]  Recommendations ({len(report['recommendations'])}):")
        for rec in report['recommendations']:
            print(f"  [{rec['priority'].upper()}] {rec['issue']}")
            print(f"    → {rec['action']}")

    print("\n" + "="*60)
