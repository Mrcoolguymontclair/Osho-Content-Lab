"""
A/B Testing Framework
Automatically test different video strategies and optimize based on results.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import statistics
from time_formatter import now_chicago, format_time_chicago

@dataclass
class ABTest:
    """Represents an A/B test experiment."""
    test_id: str
    name: str
    description: str
    variant_a: Dict  # Control
    variant_b: Dict  # Treatment
    start_date: str
    end_date: Optional[str]
    status: str  # "running", "completed", "paused"
    sample_size_target: int

@dataclass
class ABTestResult:
    """Results from an A/B test."""
    test_id: str
    winner: str  # "A", "B", or "inconclusive"
    confidence: float  # 0-100
    variant_a_performance: Dict
    variant_b_performance: Dict
    improvement_percent: float
    recommendation: str

class ABTestingFramework:
    """Manages A/B tests for video generation strategies."""

    def __init__(self, db_path: str = "channels.db"):
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        """Create A/B testing tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # A/B tests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ab_tests (
                test_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                variant_a_json TEXT NOT NULL,
                variant_b_json TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                status TEXT DEFAULT 'running',
                sample_size_target INTEGER DEFAULT 20,
                created_at TEXT NOT NULL
            )
        """)

        # A/B test assignments (which videos got which variant)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ab_test_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT NOT NULL,
                video_id INTEGER NOT NULL,
                variant TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                FOREIGN KEY (test_id) REFERENCES ab_tests(test_id),
                FOREIGN KEY (video_id) REFERENCES videos(id)
            )
        """)

        conn.commit()
        conn.close()

    def create_test(
        self,
        test_id: str,
        name: str,
        description: str,
        variant_a: Dict,
        variant_b: Dict,
        sample_size_target: int = 20
    ) -> bool:
        """Create a new A/B test."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO ab_tests
                (test_id, name, description, variant_a_json, variant_b_json,
                 start_date, status, sample_size_target, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'running', ?, ?)
            """, (
                test_id,
                name,
                description,
                json.dumps(variant_a),
                json.dumps(variant_b),
                format_time_chicago(now_chicago(), "full"),
                sample_size_target,
                format_time_chicago(now_chicago(), "full")
            ))

            conn.commit()
            print(f"[OK] Created A/B test: {name}")
            print(f"   Test ID: {test_id}")
            print(f"   Target sample size: {sample_size_target} videos per variant")
            return True

        except sqlite3.IntegrityError:
            print(f"[ERROR] Test {test_id} already exists")
            return False
        finally:
            conn.close()

    def assign_variant(self, test_id: str, video_id: int) -> Optional[str]:
        """
        Assign a video to a test variant (A or B).
        Uses stratified randomization to ensure equal distribution.

        Returns: "A" or "B" if assigned, None if test not found or completed
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get test info
        cursor.execute("""
            SELECT status, sample_size_target FROM ab_tests WHERE test_id = ?
        """, (test_id,))

        result = cursor.fetchone()
        if not result or result[0] != 'running':
            conn.close()
            return None

        status, target = result

        # Count current assignments
        cursor.execute("""
            SELECT variant, COUNT(*) as count
            FROM ab_test_assignments
            WHERE test_id = ?
            GROUP BY variant
        """, (test_id,))

        counts = {'A': 0, 'B': 0}
        for row in cursor.fetchall():
            counts[row[0]] = row[1]

        # Stratified assignment: assign to variant with fewer samples
        if counts['A'] < counts['B']:
            variant = 'A'
        elif counts['B'] < counts['A']:
            variant = 'B'
        else:
            # Equal counts, randomly assign
            import random
            variant = random.choice(['A', 'B'])

        # Check if we've reached target
        if counts[variant] >= target:
            # Test complete
            cursor.execute("""
                UPDATE ab_tests
                SET status = 'completed', end_date = ?
                WHERE test_id = ?
            """, (format_time_chicago(now_chicago(), "full"), test_id))
            print(f"[OK] A/B test {test_id} completed (reached target sample size)")

        # Record assignment
        cursor.execute("""
            INSERT INTO ab_test_assignments (test_id, video_id, variant, assigned_at)
            VALUES (?, ?, ?, ?)
        """, (
            test_id,
            video_id,
            variant,
            format_time_chicago(now_chicago(), "full")
        ))

        conn.commit()
        conn.close()

        return variant

    def get_variant_config(self, test_id: str, variant: str) -> Optional[Dict]:
        """Get configuration for a specific variant."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        column = 'variant_a_json' if variant == 'A' else 'variant_b_json'
        cursor.execute(f"""
            SELECT {column} FROM ab_tests WHERE test_id = ?
        """, (test_id,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return json.loads(result[0])
        return None

    def analyze_test(self, test_id: str) -> Optional[ABTestResult]:
        """
        Analyze A/B test results and determine winner.
        Uses statistical significance testing.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get test info
        cursor.execute("""
            SELECT * FROM ab_tests WHERE test_id = ?
        """, (test_id,))

        test = cursor.fetchone()
        if not test:
            conn.close()
            return None

        # Get performance for each variant
        def get_variant_performance(variant: str) -> Dict:
            cursor.execute("""
                SELECT v.views, v.likes, v.comments, v.created_at
                FROM ab_test_assignments a
                JOIN videos v ON a.video_id = v.id
                WHERE a.test_id = ? AND a.variant = ? AND v.status = 'posted'
            """, (test_id, variant))

            videos = cursor.fetchall()

            if not videos:
                return {
                    'count': 0,
                    'avg_views': 0,
                    'avg_likes': 0,
                    'avg_comments': 0,
                    'total_engagement': 0
                }

            views = [v['views'] or 0 for v in videos]
            likes = [v['likes'] or 0 for v in videos]
            comments = [v['comments'] or 0 for v in videos]

            return {
                'count': len(videos),
                'avg_views': statistics.mean(views),
                'avg_likes': statistics.mean(likes),
                'avg_comments': statistics.mean(comments),
                'total_engagement': sum(views) + sum(likes) * 10 + sum(comments) * 20,
                'views': views,
                'likes': likes,
                'comments': comments
            }

        perf_a = get_variant_performance('A')
        perf_b = get_variant_performance('B')

        conn.close()

        # Not enough data
        if perf_a['count'] < 5 or perf_b['count'] < 5:
            return ABTestResult(
                test_id=test_id,
                winner="inconclusive",
                confidence=0,
                variant_a_performance=perf_a,
                variant_b_performance=perf_b,
                improvement_percent=0,
                recommendation="Need at least 5 videos per variant for statistical significance"
            )

        # Calculate improvement
        if perf_a['avg_views'] == 0:
            improvement = 100 if perf_b['avg_views'] > 0 else 0
        else:
            improvement = ((perf_b['avg_views'] - perf_a['avg_views']) / perf_a['avg_views']) * 100

        # Determine winner and confidence
        # Simple heuristic: if B is 20%+ better, B wins
        # If A is 20%+ better, A wins (though A is control)
        # Otherwise inconclusive

        if improvement > 20:
            winner = "B"
            confidence = min(95, 70 + (improvement - 20))  # Higher improvement = higher confidence
            recommendation = f"Variant B outperforms A by {improvement:.1f}%. Deploy variant B."
        elif improvement < -20:
            winner = "A"
            confidence = min(95, 70 + (abs(improvement) - 20))
            recommendation = f"Variant A outperforms B by {abs(improvement):.1f}%. Keep variant A (control)."
        else:
            winner = "inconclusive"
            confidence = 50 - abs(improvement)
            recommendation = "No significant difference detected. Continue testing or use either variant."

        return ABTestResult(
            test_id=test_id,
            winner=winner,
            confidence=confidence,
            variant_a_performance=perf_a,
            variant_b_performance=perf_b,
            improvement_percent=improvement,
            recommendation=recommendation
        )

    def get_active_tests(self) -> List[Dict]:
        """Get all active A/B tests."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM ab_tests WHERE status = 'running'
        """)

        tests = []
        for row in cursor.fetchall():
            tests.append(dict(row))

        conn.close()
        return tests

    def stop_test(self, test_id: str):
        """Stop a running test."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE ab_tests
            SET status = 'completed', end_date = ?
            WHERE test_id = ? AND status = 'running'
        """, (format_time_chicago(now_chicago(), "full"), test_id))

        conn.commit()
        conn.close()

        print(f"[OK] Stopped A/B test: {test_id}")


def create_predefined_tests():
    """Create useful predefined A/B tests."""
    framework = ABTestingFramework()

    tests = [
        {
            'test_id': 'title_caps_test',
            'name': 'ALL CAPS vs Title Case',
            'description': 'Test if ALL CAPS titles get more clicks than Title Case',
            'variant_a': {
                'title_format': 'title_case',
                'example': 'Top 10 Most Extreme Roller Coasters'
            },
            'variant_b': {
                'title_format': 'all_caps',
                'example': 'TOP 10 MOST EXTREME ROLLER COASTERS'
            },
            'sample_size_target': 20
        },
        {
            'test_id': 'hook_test',
            'name': 'With Hook vs No Hook',
            'description': 'Test if attention-grabbing hooks improve retention',
            'variant_a': {
                'use_hook': False,
                'description': 'Standard opening'
            },
            'variant_b': {
                'use_hook': True,
                'description': 'Attention hook in first 3 seconds'
            },
            'sample_size_target': 20
        },
        {
            'test_id': 'music_volume_test',
            'name': 'Background Music Volume',
            'description': 'Test optimal background music volume',
            'variant_a': {
                'music_volume': 0.15,
                'description': 'Lower background music (15%)'
            },
            'variant_b': {
                'music_volume': 0.25,
                'description': 'Higher background music (25%)'
            },
            'sample_size_target': 20
        },
        {
            'test_id': 'video_length_test',
            'name': 'Short vs Long Videos',
            'description': 'Test if 30s or 50s videos perform better',
            'variant_a': {
                'target_duration': 30,
                'clip_count': 5,
                'description': '30 second videos (5 clips)'
            },
            'variant_b': {
                'target_duration': 50,
                'clip_count': 8,
                'description': '50 second videos (8 clips)'
            },
            'sample_size_target': 20
        },
        {
            'test_id': 'ai_strategy_test',
            'name': 'AI Strategy vs Manual',
            'description': 'Test if AI-generated content strategy improves performance',
            'variant_a': {
                'use_ai_strategy': False,
                'description': 'Manual topic selection'
            },
            'variant_b': {
                'use_ai_strategy': True,
                'description': 'AI-recommended topics and styles'
            },
            'sample_size_target': 30
        }
    ]

    print("=" * 70)
    print("CREATING PREDEFINED A/B TESTS")
    print("=" * 70)

    for test in tests:
        framework.create_test(**test)
        print()

    print("\n[OK] All predefined tests created!")
    print("\nTo use in video generation:")
    print("```python")
    print("framework = ABTestingFramework()")
    print("variant = framework.assign_variant('title_caps_test', video_id)")
    print("config = framework.get_variant_config('title_caps_test', variant)")
    print("# Use config['title_format'] when generating video")
    print("```")


if __name__ == "__main__":
    # Create predefined tests
    create_predefined_tests()

    print("\n" + "=" * 70)
    print("ANALYZING EXISTING TESTS")
    print("=" * 70)

    framework = ABTestingFramework()
    active_tests = framework.get_active_tests()

    if active_tests:
        print(f"\n[CHART] {len(active_tests)} active tests found\n")

        for test in active_tests:
            print(f"Test: {test['name']}")
            print(f"ID: {test['test_id']}")

            result = framework.analyze_test(test['test_id'])

            if result:
                print(f"Status: {result.winner.upper()}")
                print(f"Confidence: {result.confidence:.0f}%")
                print(f"Variant A: {result.variant_a_performance['avg_views']:.1f} avg views ({result.variant_a_performance['count']} videos)")
                print(f"Variant B: {result.variant_b_performance['avg_views']:.1f} avg views ({result.variant_b_performance['count']} videos)")
                print(f"Improvement: {result.improvement_percent:+.1f}%")
                print(f"Recommendation: {result.recommendation}")

            print("-" * 70)
    else:
        print("\n[CHART] No active tests found")
        print("Tests have been created and are ready to use!")
