#!/usr/bin/env python3
"""
ENHANCED AI ANALYTICS SYSTEM
Actively drives video production decisions with predictive scoring and real-time adaptation.

This system has REAL POWER over video generation:
- Predicts video performance BEFORE generation
- Blocks low-potential videos
- Guides topic selection
- Adapts strategies in real-time
- Controls A/B test allocation
"""

import os
import sys
import json
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from groq import Groq
import toml
from channel_manager import get_channel_videos, get_channel, add_log

# Initialize Groq
secrets = toml.load('.streamlit/secrets.toml')
groq_client = Groq(api_key=secrets.get('GROQ_API_KEY')) if secrets.get('GROQ_API_KEY') else None


# ==============================================================================
# PREDICTIVE VIDEO SCORING (PRE-GENERATION)
# ==============================================================================

def predict_video_performance(title: str, topic: str, channel_id: int) -> Dict:
    """
    CRITICAL: Predict video performance BEFORE generation.

    This actively prevents bad videos from being made!

    Args:
        title: Proposed video title
        topic: Proposed video topic
        channel_id: Channel ID

    Returns:
        {
            'predicted_score': 0-100,
            'confidence': 0-100,
            'should_generate': bool,
            'reasoning': str,
            'recommendations': [str],
            'predicted_views': int,
            'risk_level': 'low'|'medium'|'high'
        }
    """
    if not groq_client:
        return {'should_generate': True, 'predicted_score': 50, 'confidence': 0}

    try:
        channel = get_channel(channel_id)
        recent_videos = get_channel_videos(channel_id, limit=30)

        # Get posted videos with stats
        posted = [v for v in recent_videos if v['status'] == 'posted' and v.get('views', 0) > 0]

        if len(posted) < 5:
            # Not enough data, allow all videos
            return {
                'predicted_score': 60,
                'confidence': 20,
                'should_generate': True,
                'reasoning': 'Insufficient historical data for prediction',
                'recommendations': ['Build more video history for better predictions'],
                'predicted_views': 100,
                'risk_level': 'medium'
            }

        # Calculate channel benchmarks
        avg_views = sum(v.get('views', 0) for v in posted) / len(posted)
        top_25 = sorted(posted, key=lambda x: x.get('views', 0), reverse=True)[:max(1, len(posted)//4)]
        bottom_25 = sorted(posted, key=lambda x: x.get('views', 0))[:max(1, len(posted)//4)]

        # Format high/low performers
        top_titles = [v.get('title', 'Unknown') for v in top_25]
        bottom_titles = [v.get('title', 'Unknown') for v in bottom_25]

        prompt = f"""You are a YouTube analytics AI predicting video performance BEFORE production.

PROPOSED VIDEO:
- Title: {title}
- Topic: {topic}

CHANNEL CONTEXT:
- Theme: {channel.get('theme')}
- Average Views: {avg_views:.0f}
- Total Videos: {len(posted)}

HIGH PERFORMERS (Top 25%): {json.dumps(top_titles[:5])}
LOW PERFORMERS (Bottom 25%): {json.dumps(bottom_titles[:5])}

TASK: Predict if this video will succeed or fail.

Respond as JSON:
{{
  "predicted_score": 0-100,
  "confidence": 0-100,
  "should_generate": true/false,
  "reasoning": "why this will succeed/fail",
  "recommendations": ["how to improve if low score"],
  "predicted_views": estimated_views,
  "risk_level": "low|medium|high"
}}

RULES:
- predicted_score < 40 → should_generate = false (BLOCK VIDEO)
- Check if title/topic matches successful patterns
- Check if it avoids failed patterns
- Be strict: only generate videos with >40% predicted success"""

        response = groq_client.chat_completions_create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # Low temp for consistent predictions
            max_tokens=800
        )

        content = response.choices[0].message.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        prediction = json.loads(content.strip())

        # Log prediction
        verdict = "✅ APPROVED" if prediction['should_generate'] else "❌ BLOCKED"
        add_log(channel_id, "info", "prediction",
               f"{verdict} '{title}' - Score: {prediction['predicted_score']}/100")

        return prediction

    except Exception as e:
        print(f"Prediction error: {e}")
        # On error, default to allowing (don't block videos due to tech issues)
        return {'should_generate': True, 'predicted_score': 50, 'confidence': 0}


# ==============================================================================
# REAL-TIME STRATEGY ADAPTATION
# ==============================================================================

def adapt_strategy_realtime(channel_id: int) -> Dict:
    """
    Analyze last 10 videos and adapt strategy IMMEDIATELY.

    Unlike periodic analytics (every 6 hours), this runs EVERY video generation
    to rapidly adapt to what's working.

    Returns:
        {
            'use_strategy': bool,  # Should we use AI recommendations?
            'confidence': 0-100,
            'strategy_working': bool,
            'recommended_changes': [str],
            'immediate_actions': [str]
        }
    """
    if not groq_client:
        return {'use_strategy': True, 'confidence': 50}

    try:
        recent = get_channel_videos(channel_id, limit=10)
        posted = [v for v in recent if v['status'] == 'posted' and v.get('views', 0) > 0]

        if len(posted) < 5:
            return {
                'use_strategy': True,
                'confidence': 50,
                'strategy_working': True,
                'recommended_changes': [],
                'immediate_actions': ['Continue building video history']
            }

        # Check last 5 strategy vs last 5 control
        strategy_vids = [v for v in posted if v.get('ab_test_group') == 'strategy'][-5:]
        control_vids = [v for v in posted if v.get('ab_test_group') == 'control'][-5:]

        if len(strategy_vids) >= 3 and len(control_vids) >= 3:
            strategy_avg = sum(v.get('views', 0) for v in strategy_vids) / len(strategy_vids)
            control_avg = sum(v.get('views', 0) for v in control_vids) / len(control_vids)

            lift = ((strategy_avg - control_avg) / control_avg * 100) if control_avg > 0 else 0

            # REAL-TIME DECISION: Turn off strategy if it's hurting performance
            if lift < -15:  # If strategy performing 15% worse, disable it
                add_log(channel_id, "warning", "strategy",
                       f"Strategy DISABLED - performing {lift:.1f}% worse")
                return {
                    'use_strategy': False,
                    'confidence': 90,
                    'strategy_working': False,
                    'recommended_changes': ['Revert to baseline approach'],
                    'immediate_actions': ['Disable AI recommendations until performance improves']
                }
            elif lift > 15:  # If strategy performing 15% better, keep it
                add_log(channel_id, "info", "strategy",
                       f"Strategy ENABLED - performing {lift:.1f}% better")
                return {
                    'use_strategy': True,
                    'confidence': 90,
                    'strategy_working': True,
                    'recommended_changes': [],
                    'immediate_actions': ['Continue current strategy']
                }

        # Default: use strategy with moderate confidence
        return {
            'use_strategy': True,
            'confidence': 60,
            'strategy_working': None,
            'recommended_changes': [],
            'immediate_actions': ['Continue A/B testing']
        }

    except Exception as e:
        print(f"Real-time adaptation error: {e}")
        return {'use_strategy': True, 'confidence': 50}


# ==============================================================================
# SMART A/B TEST ALLOCATION
# ==============================================================================

def get_optimal_ab_split(channel_id: int) -> str:
    """
    Intelligently decide if next video should use strategy or control.

    Ensures balanced testing but shifts allocation based on performance.

    Returns: 'strategy' or 'control'
    """
    try:
        recent = get_channel_videos(channel_id, limit=20)
        posted = [v for v in recent if v['status'] == 'posted']

        strategy_count = sum(1 for v in posted if v.get('ab_test_group') == 'strategy')
        control_count = sum(1 for v in posted if v.get('ab_test_group') == 'control')

        # If severely imbalanced, rebalance
        if strategy_count > control_count + 3:
            return 'control'
        elif control_count > strategy_count + 3:
            return 'strategy'

        # Check if strategy is winning
        strategy_vids = [v for v in posted if v.get('ab_test_group') == 'strategy' and v.get('views', 0) > 0]
        control_vids = [v for v in posted if v.get('ab_test_group') == 'control' and v.get('views', 0) > 0]

        if len(strategy_vids) >= 5 and len(control_vids) >= 5:
            strategy_avg = sum(v.get('views', 0) for v in strategy_vids) / len(strategy_vids)
            control_avg = sum(v.get('views', 0) for v in control_vids) / len(control_vids)

            lift = ((strategy_avg - control_avg) / control_avg * 100) if control_avg > 0 else 0

            # If strategy winning by >25%, allocate 70% to strategy
            if lift > 25:
                import random
                return 'strategy' if random.random() < 0.7 else 'control'
            # If strategy losing by >25%, allocate 70% to control
            elif lift < -25:
                import random
                return 'control' if random.random() < 0.7 else 'strategy'

        # Default: 50/50 split
        import random
        return 'strategy' if random.random() < 0.5 else 'control'

    except Exception as e:
        print(f"A/B allocation error: {e}")
        import random
        return 'strategy' if random.random() < 0.5 else 'control'


# ==============================================================================
# TOPIC RANKING & SELECTION
# ==============================================================================

def rank_topic_ideas(topics: List[str], channel_id: int) -> List[Tuple[str, int]]:
    """
    Rank multiple topic ideas by predicted performance.

    Enables intelligent topic selection instead of random.

    Args:
        topics: List of topic ideas
        channel_id: Channel ID

    Returns: List of (topic, score) sorted by score descending
    """
    ranked = []

    for topic in topics:
        prediction = predict_video_performance(
            title=f"Ranking {topic}",
            topic=topic,
            channel_id=channel_id
        )
        ranked.append((topic, prediction['predicted_score']))

    return sorted(ranked, key=lambda x: x[1], reverse=True)


# ==============================================================================
# VIDEO PERFORMANCE FORECASTING
# ==============================================================================

def forecast_next_30_days(channel_id: int) -> Dict:
    """
    Forecast channel performance for next 30 days based on current trajectory.

    Returns:
        {
            'projected_views': int,
            'projected_subscribers': int,
            'confidence': 0-100,
            'trajectory': str ('growing', 'stable', or 'declining'),
            'recommendations': [str]
        }
    """
    try:
        # Get last 30 days of videos
        recent = get_channel_videos(channel_id, limit=50)
        posted = [v for v in recent if v['status'] == 'posted' and v.get('views', 0) > 0]

        if len(posted) < 10:
            return {
                'projected_views': 0,
                'projected_subscribers': 0,
                'confidence': 20,
                'trajectory': 'unknown',
                'recommendations': ['Need more video history for forecasting']
            }

        # Calculate trend (last 10 vs previous 10)
        recent_10 = posted[:10]
        previous_10 = posted[10:20] if len(posted) >= 20 else posted[10:]

        recent_avg = sum(v.get('views', 0) for v in recent_10) / len(recent_10)
        previous_avg = sum(v.get('views', 0) for v in previous_10) / len(previous_10) if previous_10 else recent_avg

        growth_rate = ((recent_avg - previous_avg) / previous_avg) if previous_avg > 0 else 0

        # Project forward
        videos_per_month = 30 * (len(posted) / 60)  # Assuming 60-day window
        projected_avg_views = recent_avg * (1 + growth_rate)
        projected_total = projected_avg_views * videos_per_month

        # Determine trajectory
        if growth_rate > 0.15:
            trajectory = 'growing'
        elif growth_rate < -0.15:
            trajectory = 'declining'
        else:
            trajectory = 'stable'

        return {
            'projected_views': int(projected_total),
            'projected_avg_per_video': int(projected_avg_views),
            'current_avg': int(recent_avg),
            'growth_rate': growth_rate * 100,
            'confidence': 75,
            'trajectory': trajectory,
            'recommendations': generate_trajectory_recommendations(trajectory, growth_rate)
        }

    except Exception as e:
        print(f"Forecasting error: {e}")
        return {'projected_views': 0, 'confidence': 0, 'trajectory': 'unknown'}


def generate_trajectory_recommendations(trajectory: str, growth_rate: float) -> List[str]:
    """Generate recommendations based on trajectory."""
    if trajectory == 'growing':
        return [
            'Momentum is strong - maintain current strategy',
            'Consider increasing posting frequency',
            'Double down on what is working'
        ]
    elif trajectory == 'declining':
        return [
            'Performance declining - need strategy change',
            'Review recent failures for patterns',
            'Test new content approaches',
            'Consider topic refresh'
        ]
    else:
        return [
            'Stable but not growing - need innovation',
            'Experiment with new formats',
            'Test trending topics more aggressively'
        ]


# ==============================================================================
# MAIN CONTROL FUNCTIONS
# ==============================================================================

def should_generate_video(title: str, topic: str, channel_id: int) -> Tuple[bool, Dict]:
    """
    MASTER FUNCTION: Decide if a video should be generated.

    This gives AI VETO POWER over video production!

    Args:
        title: Proposed title
        topic: Proposed topic
        channel_id: Channel ID

    Returns: (should_generate, full_analysis)
    """
    prediction = predict_video_performance(title, topic, channel_id)

    # HARD BLOCK if predicted score too low
    if prediction['predicted_score'] < 40:
        add_log(channel_id, "warning", "blocked",
               f"VIDEO BLOCKED: '{title}' - Score {prediction['predicted_score']}/100")
        return False, prediction

    # Allow if score >= 40
    return True, prediction


def get_video_generation_config(channel_id: int) -> Dict:
    """
    Get current AI-driven configuration for video generation.

    This is called BEFORE each video generation to get latest AI decisions.

    Returns:
        {
            'use_ai_strategy': bool,
            'ab_test_group': 'strategy'|'control',
            'confidence': 0-100,
            'recommended_topics': [str],
            'avoid_topics': [str],
            'special_instructions': str
        }
    """
    # Get real-time strategy adaptation
    adaptation = adapt_strategy_realtime(channel_id)

    # Get A/B test allocation
    ab_group = get_optimal_ab_split(channel_id)

    # Get latest content strategy
    from ai_analyzer import get_latest_content_strategy
    strategy = get_latest_content_strategy(channel_id)

    return {
        'use_ai_strategy': adaptation['use_strategy'] and (ab_group == 'strategy'),
        'ab_test_group': ab_group,
        'confidence': adaptation['confidence'],
        'recommended_topics': strategy.get('recommended_topics', []) if strategy else [],
        'avoid_topics': strategy.get('avoid_topics', []) if strategy else [],
        'special_instructions': strategy.get('content_style', '') if strategy else '',
        'strategy_working': adaptation.get('strategy_working'),
        'immediate_actions': adaptation.get('immediate_actions', [])
    }


# Testing
if __name__ == "__main__":
    print("Testing Enhanced AI Analytics...\n")

    channel_id = 2  # RankRiot

    # Test 1: Predict video performance
    print("=" * 70)
    print("TEST 1: Predictive Scoring")
    print("=" * 70)

    test_videos = [
        ("Ranking Most Amazing Natural Wonders", "natural wonders"),
        ("Top 5 Best Quantum Physics Theories", "quantum physics"),
        ("Ranking Most Satisfying Moments", "satisfying moments")
    ]

    for title, topic in test_videos:
        prediction = predict_video_performance(title, topic, channel_id)
        print(f"\nTitle: {title}")
        print(f"  Score: {prediction['predicted_score']}/100")
        print(f"  Should Generate: {'✅ YES' if prediction['should_generate'] else '❌ NO'}")
        print(f"  Risk: {prediction.get('risk_level', 'unknown')}")

    # Test 2: Real-time strategy adaptation
    print("\n" + "=" * 70)
    print("TEST 2: Real-Time Strategy Adaptation")
    print("=" * 70)
    adaptation = adapt_strategy_realtime(channel_id)
    print(f"Use Strategy: {adaptation['use_strategy']}")
    print(f"Confidence: {adaptation['confidence']}%")
    print(f"Working: {adaptation.get('strategy_working')}")

    # Test 3: Get video generation config
    print("\n" + "=" * 70)
    print("TEST 3: Video Generation Config")
    print("=" * 70)
    config = get_video_generation_config(channel_id)
    print(json.dumps(config, indent=2))

    print("\n✅ All tests complete!")
