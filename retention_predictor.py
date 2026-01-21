#!/usr/bin/env python3
"""
VIDEO RETENTION PREDICTOR
Predicts second-by-second viewer retention before generation.

Uses script analysis to predict:
- Hook strength (first 3 seconds)
- Retention curve throughout video
- Drop-off points
- Overall watch time percentage

This enables:
- Pre-generation optimization
- Script improvements before generation
- Pacing adjustments
- Hook testing
"""

import re
import sqlite3
from typing import Dict, List, Tuple
import math


class RetentionPredictor:
    """Predict video retention from script/title analysis."""

    def __init__(self):
        """Initialize retention predictor."""
        self.db_path = 'channels.db'

        # Retention factors (learned from data)
        self.hook_power_words = {
            'shocking', 'extreme', 'insane', 'unbelievable', 'never', 'secret',
            'terrifying', 'dangerous', 'deadly', 'forbidden', 'hidden'
        }

        self.urgency_words = {
            'now', 'today', 'just', 'breaking', 'must', 'watch', 'before'
        }

        self.engagement_words = {
            'wait', 'incredible', 'believe', 'crazy', 'amazing', 'look',
            'check', 'see', 'wow', 'omg'
        }

    def predict_retention_curve(
        self,
        title: str,
        script: Dict,
        video_duration: int = 45
    ) -> Dict[str, any]:
        """
        Predict retention curve for a video.

        Args:
            title: Video title
            script: Video script with ranked_items or scenes
            video_duration: Total duration in seconds

        Returns:
            {
                'hook_strength': float (0-100),
                'predicted_avg_retention': float (0-100),
                'retention_curve': [(second, retention_pct), ...],
                'drop_off_points': [second, ...],
                'recommendations': [str, ...]
            }
        """
        # Analyze hook (first 3 seconds)
        hook_strength = self._analyze_hook(title, script)

        # Analyze script structure
        script_quality = self._analyze_script_structure(script)

        # Build retention curve
        retention_curve = self._build_retention_curve(
            hook_strength,
            script_quality,
            video_duration
        )

        # Identify drop-off points
        drop_off_points = self._find_drop_offs(retention_curve)

        # Calculate average retention
        avg_retention = sum(r for _, r in retention_curve) / len(retention_curve)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            hook_strength,
            script_quality,
            drop_off_points,
            avg_retention
        )

        return {
            'hook_strength': hook_strength,
            'predicted_avg_retention': avg_retention,
            'predicted_watch_time_pct': self._retention_to_watch_time(avg_retention),
            'retention_curve': retention_curve,
            'drop_off_points': drop_off_points,
            'recommendations': recommendations,
            'quality_score': self._calculate_quality_score(
                hook_strength,
                avg_retention,
                script_quality
            )
        }

    def _analyze_hook(self, title: str, script: Dict) -> float:
        """
        Analyze hook strength (first 3 seconds).

        Returns: score 0-100
        """
        score = 50.0  # Baseline

        title_lower = title.lower()
        title_words = set(re.findall(r'\b\w+\b', title_lower))

        # Power words in title (+30)
        power_word_count = len(title_words & self.hook_power_words)
        score += min(power_word_count * 10, 30)

        # Urgency words (+15)
        urgency_count = len(title_words & self.urgency_words)
        score += min(urgency_count * 7, 15)

        # Numbers in title (+10)
        if re.search(r'\d+', title):
            score += 10

        # All caps (+5)
        if title.isupper():
            score += 5

        # Exclamation mark (+5)
        if '!' in title:
            score += 5

        # Check if script has strong opening
        hook_text = script.get('hook', '')
        if hook_text:
            hook_words = set(re.findall(r'\b\w+\b', hook_text.lower()))

            # Engagement words in hook (+15)
            engagement_count = len(hook_words & self.engagement_words)
            score += min(engagement_count * 5, 15)

        # Cap at 100
        return min(score, 100)

    def _analyze_script_structure(self, script: Dict) -> Dict[str, float]:
        """
        Analyze script structure quality.

        Returns: {
            'pacing_score': float,
            'variety_score': float,
            'build_score': float
        }
        """
        quality = {
            'pacing_score': 70.0,
            'variety_score': 70.0,
            'build_score': 70.0
        }

        # Check for ranked items (countdown format)
        ranked_items = script.get('ranked_items', [])

        if ranked_items:
            # Pacing: check if durations increase towards end
            if len(ranked_items) >= 3:
                # Ideal: later items get more time
                first_item = ranked_items[0]
                last_item = ranked_items[-1]

                # Check narration length as proxy for time
                first_len = len(first_item.get('narration', ''))
                last_len = len(last_item.get('narration', ''))

                if last_len > first_len:
                    quality['pacing_score'] = 85
                    quality['build_score'] = 85

            # Variety: check narration variety
            narrations = [item.get('narration', '') for item in ranked_items]

            # Count unique starting words
            start_words = [n.split()[0].lower() for n in narrations if n.split()]
            unique_starts = len(set(start_words))

            variety_ratio = unique_starts / max(len(start_words), 1)
            quality['variety_score'] = 50 + (variety_ratio * 50)

        return quality

    def _build_retention_curve(
        self,
        hook_strength: float,
        script_quality: Dict,
        duration: int
    ) -> List[Tuple[int, float]]:
        """
        Build predicted retention curve.

        Returns: [(second, retention_pct), ...]
        """
        curve = []

        # Initial retention (based on hook)
        initial_retention = hook_strength

        # Calculate decay rate
        # Strong videos: 0.5% drop per second
        # Weak videos: 2% drop per second
        avg_quality = (
            script_quality['pacing_score'] +
            script_quality['variety_score'] +
            script_quality['build_score']
        ) / 3

        base_decay = 0.02 - (avg_quality / 100 * 0.015)  # 0.5% to 2% per second

        # Build curve with varying decay
        retention = initial_retention

        for second in range(duration + 1):
            # Add curve point
            curve.append((second, retention))

            # Update retention for next second
            if second < 3:
                # First 3 seconds: minimal drop (hook holds attention)
                decay = base_decay * 0.3
            elif second < 10:
                # 3-10 seconds: higher drop (deciding to stay)
                decay = base_decay * 1.5
            elif second > duration - 5:
                # Last 5 seconds: slight recovery (climax)
                decay = base_decay * 0.7
            else:
                # Middle: steady decay
                decay = base_decay

            retention = max(retention - decay, 20)  # Floor at 20%

        return curve

    def _find_drop_offs(self, curve: List[Tuple[int, float]]) -> List[int]:
        """
        Find sharp drop-off points in retention curve.

        Returns: list of seconds where drop-offs occur
        """
        drop_offs = []

        for i in range(1, len(curve)):
            prev_retention = curve[i-1][1]
            curr_retention = curve[i][1]

            # Drop > 3% in one second
            if prev_retention - curr_retention > 3:
                drop_offs.append(curve[i][0])

        return drop_offs

    def _retention_to_watch_time(self, avg_retention: float) -> float:
        """
        Convert average retention % to watch time %.

        Retention is different from watch time:
        - Retention: % of viewers still watching at each point
        - Watch Time: % of video actually watched

        Approximation: watch_time ≈ retention * 0.8
        """
        return avg_retention * 0.8

    def _generate_recommendations(
        self,
        hook_strength: float,
        script_quality: Dict,
        drop_off_points: List[int],
        avg_retention: float
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Hook recommendations
        if hook_strength < 60:
            recommendations.append(
                "❌ WEAK HOOK: Add power words to title (shocking, extreme, insane)"
            )
            recommendations.append(
                "💡 Consider adding number + exclamation (e.g., 'TOP 5 MOST EXTREME!')"
            )

        elif hook_strength < 75:
            recommendations.append(
                "⚠️ MODERATE HOOK: Could be stronger with urgency words (must watch, never, secret)"
            )

        else:
            recommendations.append(
                "✅ STRONG HOOK: Title should grab attention effectively"
            )

        # Pacing recommendations
        if script_quality['pacing_score'] < 65:
            recommendations.append(
                "⚠️ PACING: Increase time for later items to build suspense"
            )

        # Variety recommendations
        if script_quality['variety_score'] < 65:
            recommendations.append(
                "⚠️ VARIETY: Start narrations differently - avoid repetitive structure"
            )

        # Build recommendations
        if script_quality['build_score'] < 65:
            recommendations.append(
                "⚠️ BUILD: Make #1 item significantly more exciting than others"
            )

        # Overall retention
        if avg_retention < 60:
            recommendations.append(
                "❌ LOW PREDICTED RETENTION: Consider regenerating with different topic"
            )
            recommendations.append(
                "💡 Try more visual/action-oriented topic"
            )
        elif avg_retention >= 75:
            recommendations.append(
                "✅ HIGH PREDICTED RETENTION: This script looks strong!"
            )

        return recommendations

    def _calculate_quality_score(
        self,
        hook_strength: float,
        avg_retention: float,
        script_quality: Dict
    ) -> float:
        """
        Calculate overall quality score.

        Returns: 0-100
        """
        # Weighted average
        score = (
            hook_strength * 0.4 +  # Hook is most important
            avg_retention * 0.35 +  # Retention second
            script_quality['pacing_score'] * 0.10 +
            script_quality['variety_score'] * 0.10 +
            script_quality['build_score'] * 0.05
        )

        return round(score, 1)

    def should_regenerate(
        self,
        title: str,
        script: Dict,
        threshold: float = 65.0
    ) -> Tuple[bool, str]:
        """
        Determine if script should be regenerated based on retention prediction.

        Returns: (should_regenerate, reason)
        """
        prediction = self.predict_retention_curve(title, script)

        quality_score = prediction['quality_score']

        if quality_score < threshold:
            reasons = []

            if prediction['hook_strength'] < 60:
                reasons.append("weak hook")

            if prediction['predicted_avg_retention'] < 60:
                reasons.append("low predicted retention")

            reason = f"Quality score {quality_score:.0f}/100 - " + ", ".join(reasons)
            return True, reason

        return False, f"Quality score {quality_score:.0f}/100 - looks good!"


# ==============================================================================
# PUBLIC API
# ==============================================================================

def predict_video_retention(title: str, script: Dict, duration: int = 45) -> Dict:
    """
    Predict video retention before generation.

    Args:
        title: Video title
        script: Video script
        duration: Video duration in seconds

    Returns:
        Retention prediction data
    """
    predictor = RetentionPredictor()
    return predictor.predict_retention_curve(title, script, duration)


def check_retention_quality(title: str, script: Dict, threshold: float = 65.0) -> Tuple[bool, Dict]:
    """
    Check if video will have good retention.

    Args:
        title: Video title
        script: Video script
        threshold: Minimum quality score

    Returns:
        (is_good_quality, prediction_data)
    """
    predictor = RetentionPredictor()
    prediction = predictor.predict_retention_curve(title, script)

    is_good = prediction['quality_score'] >= threshold

    return is_good, prediction


if __name__ == '__main__':
    # Test the predictor
    print("📊 Retention Predictor Test\n")

    # Test script
    test_script = {
        'title': 'TOP 5 MOST DANGEROUS ANIMALS IN THE WORLD!',
        'hook': 'Wait until you see number one!',
        'ranked_items': [
            {
                'rank': 5,
                'narration': 'At number 5, the saltwater crocodile is one of the most feared predators.'
            },
            {
                'rank': 4,
                'narration': 'Coming in at 4, we have the box jellyfish with its deadly venom.'
            },
            {
                'rank': 3,
                'narration': 'Number 3 might surprise you - the hippopotamus is incredibly dangerous.'
            },
            {
                'rank': 2,
                'narration': 'At number 2, the African elephant, despite its size, is highly aggressive.'
            },
            {
                'rank': 1,
                'narration': 'And the most dangerous animal on Earth is... the mosquito! These tiny insects kill millions every year through disease transmission.'
            }
        ]
    }

    prediction = predict_video_retention(
        test_script['title'],
        test_script,
        45
    )

    print(f"Title: {test_script['title']}\n")
    print(f"Hook Strength: {prediction['hook_strength']:.0f}/100")
    print(f"Predicted Avg Retention: {prediction['predicted_avg_retention']:.1f}%")
    print(f"Predicted Watch Time: {prediction['predicted_watch_time_pct']:.1f}%")
    print(f"Quality Score: {prediction['quality_score']:.0f}/100\n")

    print("Retention Curve (sample points):")
    for i in [0, 5, 15, 30, 45]:
        if i < len(prediction['retention_curve']):
            second, retention = prediction['retention_curve'][i]
            print(f"  {second}s: {retention:.1f}%")

    print(f"\nRecommendations:")
    for rec in prediction['recommendations']:
        print(f"  {rec}")
