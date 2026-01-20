#!/usr/bin/env python3
"""
AI ANALYSIS ENGINE
Uses Groq AI to analyze video performance and discover winning patterns.
"""

import os
import sys
import json
from typing import Dict, List, Optional
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from groq import Groq
import toml
from channel_manager import get_channel_videos, get_channel, add_log

# Initialize Groq
secrets = toml.load('.streamlit/secrets.toml')
groq_client = Groq(api_key=secrets.get('GROQ_API_KEY')) if secrets.get('GROQ_API_KEY') else None

# ==============================================================================
# Individual Video Analysis
# ==============================================================================

def analyze_video_performance(video: Dict, channel_avg: Dict) -> Optional[Dict]:
    """
    Analyze a single video's performance using AI.

    Args:
        video: Video dict with stats (views, likes, comments, etc.)
        channel_avg: Channel average metrics for comparison

    Returns:
        {
            'success_score': float (0-100),
            'strengths': [str],
            'weaknesses': [str],
            'key_insights': [str]
        }
    """
    if not groq_client:
        return None

    try:
        prompt = f"""Analyze this YouTube Short's performance:

Title: {video.get('title', 'Unknown')}
Topic: {video.get('topic', 'Unknown')}
Views: {video.get('views', 0):,}
Likes: {video.get('likes', 0):,}
Comments: {video.get('comments', 0):,}
Engagement Rate: {calculate_engagement_rate(video):.2f}%

Channel Benchmarks:
- Average Views: {channel_avg.get('avg_views', 0):,}
- Average Likes: {channel_avg.get('avg_likes', 0):,}
- Average Engagement: {channel_avg.get('avg_engagement', 0):.2f}%

Provide a detailed analysis as JSON:
{{
  "success_score": 0-100,
  "strengths": ["specific strength 1", "specific strength 2"],
  "weaknesses": ["specific weakness 1", "specific weakness 2"],
  "key_insights": ["actionable insight 1", "actionable insight 2"]
}}

Be specific and actionable. Focus on what made this video perform above/below average."""

        response = groq_client.chat_completions_create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )

        content = response.choices[0].message.content

        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        analysis = json.loads(content.strip())
        return analysis

    except Exception as e:
        print(f"Error analyzing video: {e}")
        return None


# ==============================================================================
# Pattern Recognition Across Videos
# ==============================================================================

def analyze_channel_trends(channel_id: int, limit: int = 20) -> Optional[Dict]:
    """
    Analyze patterns across recent videos to find what works.

    Returns:
        {
            'best_performing_topics': [str],
            'worst_performing_topics': [str],
            'optimal_characteristics': str,
            'successful_patterns': [str],
            'avoid_patterns': [str],
            'audience_preferences': str
        }
    """
    if not groq_client:
        return None

    try:
        channel = get_channel(channel_id)
        videos = get_channel_videos(channel_id, limit=limit)

        # Filter posted videos with stats
        posted = [v for v in videos if v['status'] == 'posted' and v.get('views', 0) > 0]

        if len(posted) < 3:
            return {
                'best_performing_topics': [],
                'worst_performing_topics': [],
                'optimal_characteristics': 'Not enough data yet. Need at least 3 posted videos.',
                'successful_patterns': [],
                'avoid_patterns': [],
                'audience_preferences': 'Insufficient data for analysis'
            }

        # Calculate A/B test effectiveness
        strategy_videos = [v for v in posted if v.get('ab_test_group') == 'strategy']
        control_videos = [v for v in posted if v.get('ab_test_group') == 'control']

        strategy_effectiveness = None
        if len(strategy_videos) >= 3 and len(control_videos) >= 3:
            strategy_avg_views = sum(v.get('views', 0) for v in strategy_videos) / len(strategy_videos)
            control_avg_views = sum(v.get('views', 0) for v in control_videos) / len(control_videos)

            strategy_avg_engagement = sum(calculate_engagement_rate(v) for v in strategy_videos) / len(strategy_videos)
            control_avg_engagement = sum(calculate_engagement_rate(v) for v in control_videos) / len(control_videos)

            lift_views = ((strategy_avg_views - control_avg_views) / control_avg_views * 100) if control_avg_views > 0 else 0
            lift_engagement = ((strategy_avg_engagement - control_avg_engagement) / control_avg_engagement * 100) if control_avg_engagement > 0 else 0

            strategy_effectiveness = {
                'strategy_count': len(strategy_videos),
                'control_count': len(control_videos),
                'strategy_avg_views': strategy_avg_views,
                'control_avg_views': control_avg_views,
                'lift_views_percentage': lift_views,
                'lift_engagement_percentage': lift_engagement,
                'is_effective': lift_views > 0
            }

            add_log(channel_id, "info", "analytics", f"A/B Test Results: {lift_views:+.1f}% views, {lift_engagement:+.1f}% engagement")

        # Sort by views
        sorted_videos = sorted(posted, key=lambda x: x.get('views', 0), reverse=True)

        # Get top and bottom performers
        top_25_percent = max(1, len(sorted_videos) // 4)
        top_videos = sorted_videos[:top_25_percent]
        bottom_videos = sorted_videos[-top_25_percent:] if len(sorted_videos) > 2 else []

        # Format for AI
        top_list = format_video_list(top_videos)
        bottom_list = format_video_list(bottom_videos) if bottom_videos else "Not enough data"

        # Add strategy effectiveness to prompt
        strategy_context = ""
        if strategy_effectiveness:
            verdict = "[OK] EFFECTIVE" if strategy_effectiveness['is_effective'] else "[WARNING] NOT EFFECTIVE"
            strategy_context = f"""

STRATEGY EFFECTIVENESS DATA (A/B Testing Results):
- Strategy videos (n={strategy_effectiveness['strategy_count']}): {strategy_effectiveness['strategy_avg_views']:.0f} avg views
- Control videos (n={strategy_effectiveness['control_count']}): {strategy_effectiveness['control_avg_views']:.0f} avg views
- Performance lift: {strategy_effectiveness['lift_views_percentage']:+.1f}% views, {strategy_effectiveness['lift_engagement_percentage']:+.1f}% engagement
- Verdict: {verdict}

{f"Previous recommendations are WORKING! Continue with similar strategies." if strategy_effectiveness['is_effective'] else "Previous recommendations NOT improving performance. Need different approach."}
"""

        prompt = f"""Analyze patterns across these {len(posted)} YouTube Shorts for trend insights.
{strategy_context}

CHANNEL INFO:
- Theme: {channel.get('theme', 'Unknown')}
- Style: {channel.get('style', 'Unknown')}
- Tone: {channel.get('tone', 'Unknown')}

HIGH PERFORMERS (Top 25%):
{top_list}

LOW PERFORMERS (Bottom 25%):
{bottom_list}

Identify clear patterns as JSON:
{{
  "best_performing_topics": ["specific topic 1", "specific topic 2"],
  "worst_performing_topics": ["topic to avoid 1", "topic to avoid 2"],
  "optimal_characteristics": "detailed description of what works",
  "successful_patterns": ["pattern 1", "pattern 2", "pattern 3"],
  "avoid_patterns": ["anti-pattern 1", "anti-pattern 2"],
  "audience_preferences": "what this specific audience clearly responds to"
}}

Be extremely specific. Focus on actionable, data-driven insights."""

        response = groq_client.chat_completions_create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500
        )

        content = response.choices[0].message.content

        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        trends = json.loads(content.strip())

        # Log insights
        add_log(channel_id, "info", "analytics", f"AI analyzed {len(posted)} videos, found {len(trends.get('successful_patterns', []))} success patterns")

        return trends

    except Exception as e:
        print(f"Error analyzing channel trends: {e}")
        import traceback
        traceback.print_exc()
        return None


# ==============================================================================
# Content Strategy Generation
# ==============================================================================

def generate_content_strategy(channel_id: int) -> Optional[Dict]:
    """
    Generate data-driven content strategy based on performance analysis.

    Returns:
        {
            'recommended_topics': [str],
            'content_style': str,
            'pacing_suggestions': str,
            'hook_templates': [str],
            'avoid_topics': [str],
            'optimal_post_interval_minutes': int,
            'posting_frequency_reasoning': str,
            'confidence_score': float
        }
    """
    if not groq_client:
        return None

    try:
        # Get channel trends
        trends = analyze_channel_trends(channel_id, limit=30)

        if not trends:
            return None

        channel = get_channel(channel_id)
        current_interval = channel.get('post_interval_minutes', 60)

        # Get recent videos to see what we've already done
        recent_videos = get_channel_videos(channel_id, limit=10)
        recent_titles = [v.get('title', '') for v in recent_videos if v.get('title')]

        # Calculate posting performance metrics
        posted_videos = [v for v in get_channel_videos(channel_id, limit=30) if v['status'] == 'posted']
        avg_views = sum(v.get('views', 0) for v in posted_videos) / len(posted_videos) if posted_videos else 0

        prompt = f"""Based on this performance data, create an optimal content strategy including posting frequency.

CHANNEL:
- Theme: {channel.get('theme')}
- Current Style: {channel.get('style')}
- Current Posting Interval: {current_interval} minutes ({60//current_interval if current_interval > 0 else 0} videos/hour)
- Average Views per Video: {avg_views:.0f}
- Total Videos Posted: {len(posted_videos)}

PERFORMANCE INSIGHTS:
- Best Topics: {', '.join(trends.get('best_performing_topics', []))}
- Avoid Topics: {', '.join(trends.get('worst_performing_topics', []))}
- Success Patterns: {', '.join(trends.get('successful_patterns', []))}
- Audience Preferences: {trends.get('audience_preferences')}

RECENT VIDEOS (don't repeat):
{chr(10).join(['- ' + t for t in recent_titles])}

Create a winning strategy as JSON:
{{
  "recommended_topics": ["unique topic 1", "unique topic 2", "unique topic 3", "unique topic 4", "unique topic 5"],
  "content_style": "specific style recommendations",
  "pacing_suggestions": "how to structure videos for max retention",
  "hook_templates": ["hook format 1", "hook format 2", "hook format 3"],
  "avoid_topics": ["what NOT to do"],
  "optimal_post_interval_minutes": 60,
  "posting_frequency_reasoning": "detailed explanation of why this interval is optimal",
  "confidence_score": 0.0-1.0
}}

POSTING FREQUENCY GUIDELINES:
- Too frequent (< 15 min): May dilute audience, spam perception, lower per-video views
- Moderate (15-60 min): Balanced approach, sustainable growth
- Spaced (60-180 min): Quality over quantity, higher per-video engagement
- Consider: If average views are LOW, post LESS frequently to focus on quality
- Consider: If engagement is HIGH, can increase frequency slightly
- YouTube algorithm favors consistent quality over volume

Recommend SPECIFIC, UNIQUE topics that match proven success patterns but are fresh.
CRITICAL: Set optimal_post_interval_minutes based on current performance (range: 15-180 minutes)."""

        response = groq_client.chat_completions_create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500
        )

        content = response.choices[0].message.content

        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        strategy = json.loads(content.strip())

        # Save strategy to database
        save_content_strategy(channel_id, strategy)

        add_log(channel_id, "info", "analytics", f"Generated new content strategy with {len(strategy.get('recommended_topics', []))} topic recommendations")

        return strategy

    except Exception as e:
        print(f"Error generating content strategy: {e}")
        import traceback
        traceback.print_exc()
        return None


# ==============================================================================
# Database Operations
# ==============================================================================

def save_content_strategy(channel_id: int, strategy: Dict):
    """Save content strategy to database."""
    import sqlite3

    try:
        conn = sqlite3.connect('channels.db')
        c = conn.cursor()

        # Create table if not exists
        c.execute('''
            CREATE TABLE IF NOT EXISTS content_strategy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER,
                recommended_topics TEXT,
                avoid_topics TEXT,
                content_style TEXT,
                hook_templates TEXT,
                pacing_suggestions TEXT,
                optimal_post_interval_minutes INTEGER,
                posting_frequency_reasoning TEXT,
                confidence_score REAL,
                generated_at TEXT,
                FOREIGN KEY (channel_id) REFERENCES channels(id)
            )
        ''')

        # Insert strategy
        c.execute('''
            INSERT INTO content_strategy
            (channel_id, recommended_topics, avoid_topics, content_style, hook_templates, pacing_suggestions, optimal_post_interval_minutes, posting_frequency_reasoning, confidence_score, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            channel_id,
            json.dumps(strategy.get('recommended_topics', [])),
            json.dumps(strategy.get('avoid_topics', [])),
            strategy.get('content_style', ''),
            json.dumps(strategy.get('hook_templates', [])),
            strategy.get('pacing_suggestions', ''),
            strategy.get('optimal_post_interval_minutes', 60),
            strategy.get('posting_frequency_reasoning', ''),
            strategy.get('confidence_score', 0.5),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Error saving strategy: {e}")


def get_latest_content_strategy(channel_id: int) -> Optional[Dict]:
    """Get the most recent content strategy from database."""
    import sqlite3

    try:
        conn = sqlite3.connect('channels.db')
        c = conn.cursor()

        c.execute('''
            SELECT recommended_topics, avoid_topics, content_style, hook_templates, pacing_suggestions, optimal_post_interval_minutes, posting_frequency_reasoning, confidence_score
            FROM content_strategy
            WHERE channel_id = ?
            ORDER BY generated_at DESC
            LIMIT 1
        ''', (channel_id,))

        row = c.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'recommended_topics': json.loads(row[0]),
            'avoid_topics': json.loads(row[1]),
            'content_style': row[2],
            'hook_templates': json.loads(row[3]),
            'pacing_suggestions': row[4],
            'optimal_post_interval_minutes': row[5] if len(row) > 5 else 60,
            'posting_frequency_reasoning': row[6] if len(row) > 6 else '',
            'confidence_score': row[7] if len(row) > 7 else row[5]
        }

    except Exception as e:
        print(f"Error getting strategy: {e}")
        return None


# ==============================================================================
# Apply AI Recommendations
# ==============================================================================

def apply_ai_recommendations(channel_id: int, auto_apply: bool = False) -> bool:
    """
    Apply AI-recommended settings to channel configuration.

    Args:
        channel_id: Channel ID to update
        auto_apply: If True, automatically apply settings. If False, just log recommendations.

    Returns:
        True if settings were applied/logged, False on error
    """
    import sqlite3

    try:
        strategy = get_latest_content_strategy(channel_id)

        if not strategy:
            add_log(channel_id, "warning", "ai_recommendations", "No AI strategy available to apply")
            return False

        optimal_interval = strategy.get('optimal_post_interval_minutes', 60)
        reasoning = strategy.get('posting_frequency_reasoning', 'No reasoning provided')
        confidence = strategy.get('confidence_score', 0.5)

        # Get current settings
        channel = get_channel(channel_id)
        current_interval = channel.get('post_interval_minutes', 60)

        # Log recommendations
        add_log(channel_id, "info", "ai_recommendations",
                f"AI recommends: {optimal_interval} min interval (currently {current_interval} min)")
        add_log(channel_id, "info", "ai_recommendations", f"Reasoning: {reasoning}")
        add_log(channel_id, "info", "ai_recommendations", f"Confidence: {confidence*100:.0f}%")

        if auto_apply and confidence >= 0.6:  # Only auto-apply if confidence is high
            # Apply the recommended interval
            conn = sqlite3.connect('channels.db')
            c = conn.cursor()

            c.execute('''
                UPDATE channels
                SET post_interval_minutes = ?
                WHERE id = ?
            ''', (optimal_interval, channel_id))

            conn.commit()
            conn.close()

            change_pct = ((optimal_interval - current_interval) / current_interval * 100) if current_interval > 0 else 0
            add_log(channel_id, "info", "ai_recommendations",
                    f"[OK] AUTO-APPLIED: Posting interval changed from {current_interval} to {optimal_interval} min ({change_pct:+.0f}%)")

            return True
        elif auto_apply:
            add_log(channel_id, "warning", "ai_recommendations",
                    f"[WARNING] Confidence too low ({confidence*100:.0f}%) - settings NOT auto-applied")
            return False
        else:
            add_log(channel_id, "info", "ai_recommendations",
                    " Recommendations logged (auto-apply disabled)")
            return True

    except Exception as e:
        add_log(channel_id, "error", "ai_recommendations", f"Failed to apply recommendations: {str(e)}")
        return False


# ==============================================================================
# Helper Functions
# ==============================================================================

def calculate_engagement_rate(video: Dict) -> float:
    """Calculate engagement rate."""
    views = video.get('views', 0)
    if views == 0:
        return 0.0

    likes = video.get('likes', 0)
    comments = video.get('comments', 0)

    return ((likes + comments) / views) * 100


def format_video_list(videos: List[Dict]) -> str:
    """Format video list for AI prompt."""
    lines = []
    for v in videos:
        lines.append(f"- {v.get('title', 'Unknown')}: {v.get('views', 0):,} views, {v.get('likes', 0):,} likes ({calculate_engagement_rate(v):.2f}% engagement)")
    return "\n".join(lines)


def get_channel_averages(channel_id: int) -> Dict:
    """Calculate channel average metrics."""
    videos = get_channel_videos(channel_id, limit=50)
    posted = [v for v in videos if v['status'] == 'posted' and v.get('views', 0) > 0]

    if not posted:
        return {
            'avg_views': 0,
            'avg_likes': 0,
            'avg_comments': 0,
            'avg_engagement': 0.0
        }

    total_views = sum(v.get('views', 0) for v in posted)
    total_likes = sum(v.get('likes', 0) for v in posted)
    total_comments = sum(v.get('comments', 0) for v in posted)

    count = len(posted)

    return {
        'avg_views': total_views // count,
        'avg_likes': total_likes // count,
        'avg_comments': total_comments // count,
        'avg_engagement': calculate_engagement_rate({
            'views': total_views,
            'likes': total_likes,
            'comments': total_comments
        })
    }
