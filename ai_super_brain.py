#!/usr/bin/env python3
"""
AI SUPER BRAIN - UNIFIED INTELLIGENCE SYSTEM
Orchestrates all advanced AI capabilities for maximum performance.

This module integrates:
- ML-powered performance prediction
- Multi-armed bandit A/B testing
- Retention prediction
- Topic similarity & recommendations
- Real-time performance monitoring

Use this as the main AI interface instead of calling individual modules.
"""

from typing import Dict, List, Tuple, Optional
import sqlite3

# Import all AI modules
from ai_ml_predictor import (
    predict_video_performance as ml_predict,
    should_generate_video_ml,
    learn_from_video_result
)
from multi_armed_bandit import (
    get_ab_test_variant,
    update_ab_test_result,
    get_ab_test_statistics
)
from retention_predictor import (
    predict_video_retention,
    check_retention_quality
)
from topic_similarity import (
    get_recommended_topics,
    find_similar_topics,
    get_fatigued_topics
)
from realtime_monitor import (
    monitor_video,
    get_videos_to_monitor,
    record_performance_checkpoint
)


class AISuperBrain:
    """
    Unified AI system that orchestrates all intelligence capabilities.
    """

    def __init__(self):
        """Initialize AI Super Brain."""
        self.db_path = 'channels.db'

    # ==========================================================================
    # PRE-GENERATION INTELLIGENCE
    # ==========================================================================

    def evaluate_video_concept(
        self,
        title: str,
        topic: str,
        script: Dict,
        channel_id: int
    ) -> Dict:
        """
        Comprehensive pre-generation evaluation.

        Combines:
        - ML performance prediction
        - Retention prediction
        - Topic similarity analysis

        Returns:
            {
                'should_generate': bool,
                'confidence': float,
                'predicted_views': int,
                'predicted_score': float,
                'retention_score': float,
                'topic_similarity': float,
                'recommendations': [str, ...],
                'risk_factors': [str, ...],
                'strengths': [str, ...]
            }
        """
        # Get ML performance prediction
        ml_prediction = ml_predict(title, topic, channel_id)

        # Get retention prediction
        retention_pred = predict_video_retention(title, script, 45)

        # Get topic similarity (is this topic similar to winners?)
        similar_topics = find_similar_topics(topic, channel_id, 3)
        topic_similarity = (
            similar_topics[0]['similarity'] if similar_topics else 0.0
        )

        # Combine scores for overall assessment
        performance_score = ml_prediction['predicted_score']
        retention_score = retention_pred['quality_score']

        # Weighted composite score
        composite_score = (
            performance_score * 0.50 +  # Performance is most important
            retention_score * 0.35 +     # Retention second
            topic_similarity * 100 * 0.15  # Topic similarity boost
        )

        # Decision thresholds
        should_generate = composite_score >= 50

        # Calculate confidence
        confidence = min(
            ml_prediction['confidence'],
            0.8  # Cap at 80% since retention is estimated
        )

        # Collect recommendations
        recommendations = []
        risk_factors = []
        strengths = []

        # From ML prediction
        if ml_prediction['predicted_score'] < 50:
            risk_factors.append(f"ML predicts low performance ({ml_prediction['predicted_score']:.0f}/100)")
            recommendations.extend([
                rec for rec in ml_prediction['reasoning'].split('; ')
                if '✗' in rec
            ])
        else:
            strengths.append(f"ML predicts strong performance ({ml_prediction['predicted_score']:.0f}/100)")

        # From retention prediction
        if retention_pred['quality_score'] < 65:
            risk_factors.append(f"Low retention predicted ({retention_pred['quality_score']:.0f}/100)")
            recommendations.extend(retention_pred['recommendations'])
        else:
            strengths.append(f"Strong retention predicted ({retention_pred['quality_score']:.0f}/100)")

        # From topic similarity
        if topic_similarity > 0.5:
            strengths.append(f"Topic similar to past winners (similarity: {topic_similarity:.1%})")
        elif topic_similarity < 0.2:
            risk_factors.append("Topic is very different from past successes")
            recommendations.append("💡 Consider topics more similar to proven winners")

        # Overall assessment
        if composite_score >= 75:
            assessment = "EXCELLENT - High confidence winner"
        elif composite_score >= 60:
            assessment = "GOOD - Should perform well"
        elif composite_score >= 50:
            assessment = "MODERATE - May need optimization"
        else:
            assessment = "POOR - Recommend regeneration"

        return {
            'should_generate': should_generate,
            'confidence': confidence,
            'composite_score': composite_score,
            'assessment': assessment,

            # Individual scores
            'predicted_views': ml_prediction['predicted_views'],
            'predicted_score': performance_score,
            'retention_score': retention_score,
            'topic_similarity': topic_similarity,

            # Insights
            'recommendations': recommendations[:5],  # Top 5
            'risk_factors': risk_factors,
            'strengths': strengths,

            # Raw data
            'ml_prediction': ml_prediction,
            'retention_prediction': retention_pred
        }

    def get_smart_ab_test_variant(self, channel_id: int) -> Tuple[str, Dict]:
        """
        Get A/B test variant using multi-armed bandit.

        Returns:
            (variant, statistics)
        """
        variant = get_ab_test_variant(channel_id)
        stats = get_ab_test_statistics(channel_id)

        return variant, stats

    def get_smart_topics(self, channel_id: int, num_topics: int = 5) -> List[Dict]:
        """
        Get smart topic recommendations.

        Combines:
        - Topics similar to winners
        - Fatigue detection (avoid overused topics)

        Returns:
            List of recommended topics with scores
        """
        # Get recommended topics
        recommended = get_recommended_topics(channel_id, num_topics * 2)

        # Get fatigued topics to avoid
        fatigued = get_fatigued_topics(channel_id, 30)
        fatigued_set = {t['topic'] for t in fatigued}

        # Filter out fatigued topics
        fresh_topics = [
            t for t in recommended
            if t['topic'] not in fatigued_set
        ]

        return fresh_topics[:num_topics]

    # ==========================================================================
    # POST-GENERATION INTELLIGENCE
    # ==========================================================================

    def update_video_performance(
        self,
        video_id: int,
        channel_id: int,
        variant: str,
        actual_views: int,
        title: str,
        topic: str
    ):
        """
        Update AI models with actual video performance.

        Call this periodically to improve predictions.

        Args:
            video_id: Video ID
            channel_id: Channel ID
            variant: A/B test variant used
            actual_views: Actual views achieved
            title: Video title
            topic: Video topic
        """
        # Get baseline for success determination
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT AVG(views) as avg_views
            FROM videos
            WHERE channel_id = ? AND status = 'posted' AND views IS NOT NULL
        """, (channel_id,))

        result = cursor.fetchone()
        conn.close()

        baseline_views = (result[0] or 100) if result else 100

        # Determine if successful
        success = actual_views >= baseline_views

        # Update multi-armed bandit
        update_ab_test_result(
            channel_id,
            variant,
            success,
            reward=actual_views
        )

        # Update ML predictor
        learn_from_video_result(title, topic, channel_id, actual_views)

    def monitor_recent_videos(self) -> List[Dict]:
        """
        Monitor all recent videos and get recommendations.

        Returns:
            List of videos with monitoring data and recommendations
        """
        videos_to_check = get_videos_to_monitor()

        results = []
        for video_data in videos_to_check:
            # Check performance
            performance = monitor_video(
                video_data['video_id'],
                video_data['channel_id']
            )

            # Record checkpoint
            record_performance_checkpoint(
                video_data['video_id'],
                video_data['due_checkpoint'],
                performance
            )

            results.append({
                'video': video_data,
                'performance': performance
            })

        return results

    # ==========================================================================
    # ANALYTICS & INSIGHTS
    # ==========================================================================

    def get_ai_health_report(self, channel_id: int) -> Dict:
        """
        Get comprehensive AI health report.

        Returns:
            {
                'ab_test_status': dict,
                'top_topics': list,
                'fatigued_topics': list,
                'recent_performance': dict,
                'recommendations': list
            }
        """
        # A/B test status
        ab_stats = get_ab_test_statistics(channel_id)

        # Topic recommendations
        top_topics = self.get_smart_topics(channel_id, 5)
        fatigued = get_fatigued_topics(channel_id, 30)

        # Recent video performance
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                AVG(views) as avg_views,
                SUM(CASE WHEN views > (
                    SELECT AVG(views) FROM videos
                    WHERE channel_id = ? AND status = 'posted' AND views IS NOT NULL
                ) THEN 1 ELSE 0 END) as above_avg_count
            FROM videos
            WHERE channel_id = ?
            AND status = 'posted'
            AND posted_at >= datetime('now', '-7 days')
            AND views IS NOT NULL
        """, (channel_id, channel_id))

        row = cursor.fetchone()
        recent_total = row[0] or 0
        recent_avg = row[1] or 0
        above_avg = row[2] or 0

        conn.close()

        recent_success_rate = (above_avg / recent_total) if recent_total > 0 else 0

        # Generate recommendations
        recommendations = []

        # A/B test recommendations
        if ab_stats.get('winner'):
            winner_name, confidence = ab_stats['winner']
            recommendations.append(
                f"✅ A/B Test: '{winner_name}' is winning with {confidence:.0%} confidence"
            )
        else:
            recommendations.append(
                "⏳ A/B Test: Continue testing to find winner"
            )

        # Topic recommendations
        if top_topics:
            recommendations.append(
                f"💡 Top recommended topic: {top_topics[0]['topic']} "
                f"(similarity score: {top_topics[0]['similarity_score']:.2f})"
            )

        # Fatigue warnings
        if fatigued:
            recommendations.append(
                f"⚠️ Avoid topic: '{fatigued[0]['topic']}' "
                f"({fatigued[0]['reason']}, used {fatigued[0]['usage_count']}x)"
            )

        # Performance trends
        if recent_success_rate >= 0.6:
            recommendations.append(
                f"✅ Strong recent performance: {recent_success_rate:.0%} above average"
            )
        elif recent_success_rate < 0.4:
            recommendations.append(
                f"⚠️ Recent performance declining: only {recent_success_rate:.0%} above average"
            )
            recommendations.append(
                "💡 Consider refreshing content strategy or trying new topics"
            )

        return {
            'ab_test_status': ab_stats,
            'top_topics': top_topics[:3],
            'fatigued_topics': fatigued[:3],
            'recent_performance': {
                'total_videos': recent_total,
                'avg_views': recent_avg,
                'success_rate': recent_success_rate
            },
            'recommendations': recommendations
        }


# ==============================================================================
# GLOBAL INSTANCE & PUBLIC API
# ==============================================================================

_ai_brain = None

def get_ai_brain() -> AISuperBrain:
    """Get global AI Super Brain instance."""
    global _ai_brain
    if _ai_brain is None:
        _ai_brain = AISuperBrain()
    return _ai_brain


# Convenience functions

def evaluate_video(title: str, topic: str, script: Dict, channel_id: int) -> Dict:
    """Evaluate video concept before generation."""
    brain = get_ai_brain()
    return brain.evaluate_video_concept(title, topic, script, channel_id)


def get_recommended_variant(channel_id: int) -> Tuple[str, Dict]:
    """Get smart A/B test variant."""
    brain = get_ai_brain()
    return brain.get_smart_ab_test_variant(channel_id)


def get_smart_topic_recommendations(channel_id: int, num_topics: int = 5) -> List[Dict]:
    """Get smart topic recommendations."""
    brain = get_ai_brain()
    return brain.get_smart_topics(channel_id, num_topics)


def update_with_results(
    video_id: int,
    channel_id: int,
    variant: str,
    actual_views: int,
    title: str,
    topic: str
):
    """Update AI with actual results."""
    brain = get_ai_brain()
    brain.update_video_performance(
        video_id, channel_id, variant, actual_views, title, topic
    )


def get_ai_report(channel_id: int) -> Dict:
    """Get AI health report."""
    brain = get_ai_brain()
    return brain.get_ai_health_report(channel_id)


if __name__ == '__main__':
    # Demo the AI Super Brain
    print("🧠 AI SUPER BRAIN DEMO\n")
    print("="*60)

    channel_id = 1

    # Test video concept evaluation
    print("\n1. Video Concept Evaluation\n")

    test_script = {
        'title': 'TOP 5 MOST DANGEROUS ANIMALS IN THE WORLD!',
        'hook': 'Wait until you see number one!',
        'ranked_items': [
            {'rank': i, 'narration': f'Rank {i} narration here'}
            for i in range(5, 0, -1)
        ]
    }

    evaluation = evaluate_video(
        'TOP 5 MOST DANGEROUS ANIMALS IN THE WORLD!',
        'dangerous animals',
        test_script,
        channel_id
    )

    print(f"Assessment: {evaluation['assessment']}")
    print(f"Composite Score: {evaluation['composite_score']:.0f}/100")
    print(f"Should Generate: {evaluation['should_generate']}")
    print(f"Confidence: {evaluation['confidence']:.0%}")
    print(f"\nPredicted Views: {evaluation['predicted_views']:,}")
    print(f"Performance Score: {evaluation['predicted_score']:.0f}/100")
    print(f"Retention Score: {evaluation['retention_score']:.0f}/100")

    if evaluation['strengths']:
        print(f"\nStrengths:")
        for strength in evaluation['strengths']:
            print(f"  ✓ {strength}")

    if evaluation['risk_factors']:
        print(f"\nRisk Factors:")
        for risk in evaluation['risk_factors']:
            print(f"  ⚠ {risk}")

    # Test A/B variant selection
    print("\n" + "="*60)
    print("\n2. Smart A/B Test Variant\n")

    variant, stats = get_recommended_variant(channel_id)
    print(f"Selected Variant: {variant}")

    if stats.get('current_allocation'):
        print(f"\nCurrent Allocation:")
        for var, prob in stats['current_allocation'].items():
            print(f"  {var}: {prob:.0%}")

    # Test topic recommendations
    print("\n" + "="*60)
    print("\n3. Smart Topic Recommendations\n")

    topics = get_smart_topic_recommendations(channel_id, 3)

    if topics:
        for i, topic_data in enumerate(topics, 1):
            print(f"{i}. {topic_data['topic']}")
            print(f"   Score: {topic_data['similarity_score']:.2f}")
            print(f"   Used: {topic_data['usage_count']}x")
    else:
        print("No topics yet (need historical data)")

    # Test AI health report
    print("\n" + "="*60)
    print("\n4. AI Health Report\n")

    report = get_ai_report(channel_id)

    print(f"Recent Performance:")
    print(f"  Videos: {report['recent_performance']['total_videos']}")
    print(f"  Avg Views: {report['recent_performance']['avg_views']:.0f}")
    print(f"  Success Rate: {report['recent_performance']['success_rate']:.0%}")

    print(f"\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  {rec}")

    print("\n" + "="*60)
    print("\n✅ AI Super Brain initialized and ready!")
