#!/usr/bin/env python3
"""
ADVANCED ML-POWERED VIDEO PERFORMANCE PREDICTOR
Replaces LLM-only predictions with engineered features and statistical modeling.

Features:
- Feature engineering from title/topic/historical data
- Statistical prediction with confidence intervals
- Explainable predictions (feature importance)
- Cold-start handling for new channels
- Continuous model improvement from feedback
"""

import re
import sqlite3
import math
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import Counter
import json

# ==============================================================================
# FEATURE ENGINEERING
# ==============================================================================

class FeatureExtractor:
    """Extract predictive features from video metadata."""

    POWER_WORDS = {
        'extreme', 'shocking', 'amazing', 'incredible', 'insane', 'unbelievable',
        'dangerous', 'deadly', 'brutal', 'savage', 'epic', 'ultimate', 'best',
        'worst', 'top', 'secret', 'hidden', 'mysterious', 'crazy', 'wild',
        'massive', 'giant', 'rare', 'forbidden', 'terrifying', 'nightmare'
    }

    URGENCY_WORDS = {
        'now', 'today', 'urgent', 'breaking', 'just', 'new', 'latest', 'never',
        'before', 'first', 'last', 'must', 'need', 'watch'
    }

    def __init__(self):
        """Initialize feature extractor."""
        self.channel_cache = {}

    def extract_title_features(self, title: str) -> Dict[str, float]:
        """Extract features from video title."""
        title_lower = title.lower()
        words = re.findall(r'\b\w+\b', title_lower)

        return {
            # Length features
            'title_length': len(title),
            'word_count': len(words),
            'avg_word_length': sum(len(w) for w in words) / max(len(words), 1),

            # Capitalization features
            'caps_ratio': sum(1 for c in title if c.isupper()) / max(len(title), 1),
            'all_caps': 1.0 if title.isupper() else 0.0,
            'has_number': 1.0 if re.search(r'\d', title) else 0.0,

            # Power words
            'power_word_count': sum(1 for w in words if w in self.POWER_WORDS),
            'urgency_word_count': sum(1 for w in words if w in self.URGENCY_WORDS),

            # Punctuation
            'has_exclamation': 1.0 if '!' in title else 0.0,
            'has_question': 1.0 if '?' in title else 0.0,
            'emoji_count': len([c for c in title if ord(c) > 127]),

            # Structure
            'has_colon': 1.0 if ':' in title else 0.0,
            'has_dash': 1.0 if '-' in title or '–' in title else 0.0,
        }

    def extract_topic_features(self, topic: str, channel_id: int) -> Dict[str, float]:
        """Extract features from topic based on historical performance."""
        # Get topic similarity to past winners
        conn = sqlite3.connect('channels.db')
        cursor = conn.cursor()

        # Get top performing videos
        cursor.execute("""
            SELECT title, topic, views
            FROM videos
            WHERE channel_id = ? AND status = 'posted' AND views IS NOT NULL
            ORDER BY views DESC
            LIMIT 10
        """, (channel_id,))

        top_videos = cursor.fetchall()

        # Calculate topic overlap with winners
        topic_words = set(re.findall(r'\b\w+\b', topic.lower()))

        max_similarity = 0.0
        avg_similarity = 0.0

        if top_videos:
            similarities = []
            for _, past_topic, _ in top_videos:
                if past_topic:
                    past_words = set(re.findall(r'\b\w+\b', past_topic.lower()))
                    if past_words:
                        jaccard = len(topic_words & past_words) / len(topic_words | past_words)
                        similarities.append(jaccard)

            if similarities:
                max_similarity = max(similarities)
                avg_similarity = sum(similarities) / len(similarities)

        # Check if topic was used before
        cursor.execute("""
            SELECT COUNT(*), AVG(views)
            FROM videos
            WHERE channel_id = ? AND topic LIKE ? AND status = 'posted'
        """, (channel_id, f'%{topic[:20]}%'))

        topic_count, topic_avg_views = cursor.fetchone()
        topic_count = topic_count or 0
        topic_avg_views = topic_avg_views or 0

        conn.close()

        return {
            'topic_similarity_max': max_similarity,
            'topic_similarity_avg': avg_similarity,
            'topic_reuse_count': min(topic_count, 5),  # Cap at 5
            'topic_past_performance': topic_avg_views / 1000,  # Normalize
        }

    def extract_timing_features(self, channel_id: int) -> Dict[str, float]:
        """Extract timing-based features."""
        now = datetime.now()

        conn = sqlite3.connect('channels.db')
        cursor = conn.cursor()

        # Time since last upload
        cursor.execute("""
            SELECT posted_at
            FROM videos
            WHERE channel_id = ? AND status = 'posted'
            ORDER BY posted_at DESC
            LIMIT 1
        """, (channel_id,))

        result = cursor.fetchone()
        hours_since_last = 24.0  # Default

        if result and result[0]:
            try:
                last_posted = datetime.fromisoformat(result[0])
                hours_since_last = (now - last_posted).total_seconds() / 3600
            except:
                pass

        conn.close()

        return {
            'hour_of_day': now.hour,
            'day_of_week': now.weekday(),  # 0=Monday, 6=Sunday
            'is_weekend': 1.0 if now.weekday() >= 5 else 0.0,
            'hours_since_last_upload': min(hours_since_last, 48),  # Cap at 48
        }

    def extract_channel_features(self, channel_id: int) -> Dict[str, float]:
        """Extract channel performance features."""
        conn = sqlite3.connect('channels.db')
        cursor = conn.cursor()

        # Recent performance (last 7 days)
        cursor.execute("""
            SELECT
                COUNT(*) as count,
                AVG(views) as avg_views,
                AVG(CAST(likes AS FLOAT) / NULLIF(views, 0)) as avg_like_rate,
                AVG(CAST(comments AS FLOAT) / NULLIF(views, 0)) as avg_comment_rate
            FROM videos
            WHERE channel_id = ?
            AND status = 'posted'
            AND posted_at >= datetime('now', '-7 days')
            AND views IS NOT NULL
        """, (channel_id,))

        row = cursor.fetchone()
        recent_count = row[0] or 0
        recent_avg_views = row[1] or 0
        recent_like_rate = (row[2] or 0) * 100
        recent_comment_rate = (row[3] or 0) * 100

        # Overall channel stats
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                AVG(views) as avg_views,
                MAX(views) as max_views
            FROM videos
            WHERE channel_id = ? AND status = 'posted' AND views IS NOT NULL
        """, (channel_id,))

        row = cursor.fetchone()
        total_videos = row[0] or 0
        overall_avg_views = row[1] or 0
        max_views = row[2] or 0

        conn.close()

        return {
            'recent_video_count': min(recent_count, 20),
            'recent_avg_views': recent_avg_views / 1000,  # Normalize to thousands
            'recent_like_rate': recent_like_rate,
            'recent_comment_rate': recent_comment_rate,
            'total_videos': min(total_videos, 100),  # Cap at 100
            'overall_avg_views': overall_avg_views / 1000,
            'max_views': max_views / 1000,
            'channel_momentum': recent_avg_views / max(overall_avg_views, 1),
        }

    def extract_all_features(self, title: str, topic: str, channel_id: int) -> Dict[str, float]:
        """Extract all features for prediction."""
        features = {}

        features.update(self.extract_title_features(title))
        features.update(self.extract_topic_features(topic, channel_id))
        features.update(self.extract_timing_features(channel_id))
        features.update(self.extract_channel_features(channel_id))

        return features


# ==============================================================================
# STATISTICAL PREDICTOR
# ==============================================================================

class PerformancePredictor:
    """Statistical model for video performance prediction."""

    def __init__(self):
        """Initialize predictor."""
        self.extractor = FeatureExtractor()
        self.feature_weights = self._get_default_weights()

    def _get_default_weights(self) -> Dict[str, float]:
        """Get default feature weights (will be learned over time)."""
        return {
            # Title features (40% weight)
            'title_length': 0.02,
            'word_count': 0.05,
            'caps_ratio': 0.08,
            'power_word_count': 0.15,
            'urgency_word_count': 0.10,
            'has_exclamation': 0.05,
            'has_number': 0.08,

            # Topic features (25% weight)
            'topic_similarity_max': 0.12,
            'topic_similarity_avg': 0.08,
            'topic_reuse_count': -0.05,  # Negative: repetition is bad

            # Channel momentum (30% weight)
            'recent_avg_views': 0.20,
            'channel_momentum': 0.15,
            'recent_like_rate': 0.05,

            # Timing (5% weight)
            'hours_since_last_upload': 0.03,
            'is_weekend': 0.02,
        }

    def predict_views(
        self,
        title: str,
        topic: str,
        channel_id: int
    ) -> Tuple[float, float, Dict[str, float]]:
        """
        Predict video views with confidence interval.

        Returns:
            (predicted_views, confidence, feature_importance)
        """
        # Extract features
        features = self.extractor.extract_all_features(title, topic, channel_id)

        # Get baseline from channel history
        baseline_views = features.get('overall_avg_views', 50) * 1000
        if baseline_views < 10:
            baseline_views = 50  # Minimum baseline for new channels

        # Calculate weighted score
        score = 0.0
        feature_importance = {}

        for feature_name, feature_value in features.items():
            weight = self.feature_weights.get(feature_name, 0)
            contribution = feature_value * weight
            score += contribution

            if abs(contribution) > 0.01:  # Only track significant contributors
                feature_importance[feature_name] = contribution

        # Convert score to predicted views multiplier
        # Score typically ranges from -1 to +3
        # Map to 0.3x - 5x multiplier
        multiplier = 0.5 + (score * 0.5)
        multiplier = max(0.3, min(multiplier, 5.0))  # Clamp

        predicted_views = baseline_views * multiplier

        # Calculate confidence based on data availability
        total_videos = features.get('total_videos', 0)

        if total_videos < 5:
            confidence = 0.3  # Low confidence for new channels
        elif total_videos < 20:
            confidence = 0.5 + (total_videos / 40)  # 0.5 to 1.0
        else:
            confidence = min(0.9, 0.6 + (total_videos / 200))

        # Adjust confidence based on feature quality
        if features.get('topic_similarity_max', 0) > 0.5:
            confidence += 0.1  # Boost if similar to past winners

        confidence = min(confidence, 0.95)

        return predicted_views, confidence, feature_importance

    def should_generate_video(
        self,
        title: str,
        topic: str,
        channel_id: int,
        threshold_multiplier: float = 0.5
    ) -> Tuple[bool, Dict]:
        """
        Determine if video should be generated based on prediction.

        Args:
            threshold_multiplier: Generate if predicted views > baseline * threshold

        Returns:
            (should_generate, prediction_data)
        """
        predicted_views, confidence, feature_importance = self.predict_views(
            title, topic, channel_id
        )

        # Get baseline
        features = self.extractor.extract_all_features(title, topic, channel_id)
        baseline_views = features.get('overall_avg_views', 50) * 1000

        # Calculate predicted score (0-100)
        score = min(100, (predicted_views / max(baseline_views, 1)) * 50)

        # Determine if should generate
        should_generate = predicted_views >= (baseline_views * threshold_multiplier)

        # Risk assessment
        if score < 30:
            risk = 'high'
        elif score < 60:
            risk = 'medium'
        else:
            risk = 'low'

        # Build reasoning
        top_features = sorted(
            feature_importance.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:3]

        reasoning_parts = []
        for feat_name, feat_value in top_features:
            if feat_value > 0:
                reasoning_parts.append(f"✓ {feat_name.replace('_', ' ')} is strong")
            else:
                reasoning_parts.append(f"✗ {feat_name.replace('_', ' ')} is weak")

        reasoning = "; ".join(reasoning_parts)

        prediction_data = {
            'predicted_views': round(predicted_views),
            'predicted_score': round(score, 1),
            'confidence': round(confidence, 2),
            'risk': risk,
            'baseline_views': round(baseline_views),
            'multiplier': round(predicted_views / max(baseline_views, 1), 2),
            'reasoning': reasoning,
            'feature_importance': {
                k: round(v, 3)
                for k, v in feature_importance.items()
            }
        }

        return should_generate, prediction_data

    def learn_from_result(
        self,
        title: str,
        topic: str,
        channel_id: int,
        actual_views: int
    ):
        """
        Update model weights based on actual performance.
        Simple gradient descent on prediction error.
        """
        # Extract features for this video
        features = self.extractor.extract_all_features(title, topic, channel_id)

        # Get prediction
        predicted_views, _, _ = self.predict_views(title, topic, channel_id)

        # Calculate error
        error = (actual_views - predicted_views) / max(predicted_views, 1)

        # Update weights with learning rate
        learning_rate = 0.01  # Small updates to avoid instability

        for feature_name, feature_value in features.items():
            if feature_name in self.feature_weights and feature_value != 0:
                # Gradient: error * feature_value
                gradient = error * feature_value
                self.feature_weights[feature_name] += learning_rate * gradient

        # Save updated weights
        self._save_weights()

    def _save_weights(self):
        """Save learned weights to database."""
        try:
            conn = sqlite3.connect('channels.db')
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ml_model_weights (
                    id INTEGER PRIMARY KEY,
                    weights_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            weights_json = json.dumps(self.feature_weights)

            cursor.execute("""
                INSERT OR REPLACE INTO ml_model_weights (id, weights_json, updated_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
            """, (weights_json,))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving model weights: {e}")

    def _load_weights(self):
        """Load learned weights from database."""
        try:
            conn = sqlite3.connect('channels.db')
            cursor = conn.cursor()

            cursor.execute("""
                SELECT weights_json FROM ml_model_weights WHERE id = 1
            """)

            result = cursor.fetchone()
            conn.close()

            if result:
                self.feature_weights = json.loads(result[0])
        except Exception as e:
            print(f"Error loading model weights: {e}")


# ==============================================================================
# PUBLIC API
# ==============================================================================

# Global predictor instance
_predictor = None

def get_predictor() -> PerformancePredictor:
    """Get or create global predictor instance."""
    global _predictor
    if _predictor is None:
        _predictor = PerformancePredictor()
        _predictor._load_weights()
    return _predictor


def predict_video_performance(
    title: str,
    topic: str,
    channel_id: int
) -> Dict:
    """
    Predict video performance with ML-powered feature engineering.

    Returns:
        {
            'predicted_views': int,
            'predicted_score': float (0-100),
            'confidence': float (0-1),
            'risk': str ('low', 'medium', 'high'),
            'reasoning': str,
            'feature_importance': dict
        }
    """
    predictor = get_predictor()
    should_gen, prediction_data = predictor.should_generate_video(
        title, topic, channel_id, threshold_multiplier=0.5
    )
    return prediction_data


def should_generate_video_ml(
    title: str,
    topic: str,
    channel_id: int,
    min_score: float = 40
) -> Tuple[bool, Dict]:
    """
    ML-powered decision: should this video be generated?

    Args:
        min_score: Minimum predicted score (0-100) to generate

    Returns:
        (should_generate, prediction_data)
    """
    predictor = get_predictor()
    should_gen, prediction_data = predictor.should_generate_video(
        title, topic, channel_id, threshold_multiplier=0.5
    )

    # Override based on score threshold
    if prediction_data['predicted_score'] < min_score:
        should_gen = False

    return should_gen, prediction_data


def learn_from_video_result(
    title: str,
    topic: str,
    channel_id: int,
    actual_views: int
):
    """
    Update ML model with actual video performance.
    Call this periodically to improve predictions.
    """
    predictor = get_predictor()
    predictor.learn_from_result(title, topic, channel_id, actual_views)


if __name__ == '__main__':
    # Test the predictor
    print("🧠 ML Performance Predictor Test\n")

    # Test prediction
    title = "TOP 5 MOST DANGEROUS ANIMALS IN THE WORLD!"
    topic = "dangerous animals"
    channel_id = 1

    prediction = predict_video_performance(title, topic, channel_id)

    print(f"Title: {title}")
    print(f"Topic: {topic}\n")
    print(f"Predicted Views: {prediction['predicted_views']:,}")
    print(f"Predicted Score: {prediction['predicted_score']}/100")
    print(f"Confidence: {prediction['confidence']:.0%}")
    print(f"Risk: {prediction['risk'].upper()}")
    print(f"\nReasoning: {prediction['reasoning']}")
    print(f"\nTop Features:")
    for feat, importance in sorted(
        prediction['feature_importance'].items(),
        key=lambda x: abs(x[1]),
        reverse=True
    )[:5]:
        print(f"  {feat}: {importance:+.3f}")
