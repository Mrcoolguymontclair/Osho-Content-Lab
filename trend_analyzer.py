#!/usr/bin/env python3
"""
TREND ANALYZER
Uses Groq AI to analyze if trending topics are suitable for video content.
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from groq import Groq

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def analyze_trend_for_video(trend: Dict, channel_theme: str) -> Tuple[bool, Dict]:
    """
    Use AI to determine if a trend is suitable for video content.

    Args:
        trend: Trend data from google_trends_fetcher
        channel_theme: Channel's content theme

    Returns: (is_video_worthy, analysis_dict)
    """
    if not groq_client:
        return False, {"error": "Groq API not configured"}

    prompt = f"""Analyze if this trending topic is suitable for a YouTube Short video.

TRENDING TOPIC: {trend['topic']}
CATEGORY: {trend.get('category', 'unknown')}
SEARCH VOLUME: {trend.get('search_volume', 'unknown')}
CHANNEL THEME: {channel_theme}

Your task: Determine if this trend would make a GOOD, ENGAGING YouTube Short (45 seconds).

Consider:
1. **Visual Potential** - Can we find good stock footage for this?
2. **Audience Interest** - Would people actually watch this?
3. **Timely Relevance** - Is this trend still hot or already fading?
4. **Content Safety** - Is it appropriate, non-controversial?
5. **Educational Value** - Can we teach/explain something interesting?
6. **Theme Alignment** - Does it fit the channel's theme?

CRITICAL RULES:
- ❌ REJECT: Medical advice, legal advice, financial advice, political controversy
- ❌ REJECT: Topics requiring expert knowledge we don't have
- ❌ REJECT: Negative/tragic news (deaths, disasters, etc.)
- ❌ REJECT: Topics with no visual content (pure text/data)
- ✅ ACCEPT: Sports, entertainment, pop culture, technology, lifestyle
- ✅ ACCEPT: Educational, explainer, comparison, ranking topics
- ✅ ACCEPT: Positive, uplifting, interesting content

Output ONLY valid JSON (no markdown):
{{
  "is_video_worthy": true/false,
  "confidence": 0-100,
  "visual_potential": "high"/"medium"/"low",
  "audience_interest": "very_high"/"high"/"medium"/"low",
  "urgency": "very_urgent"/"urgent"/"moderate"/"low",
  "content_category": "sports"/"entertainment"/"technology"/"lifestyle"/"education"/"other",
  "suggested_video_angle": "Brief description of how to approach this topic",
  "estimated_lifespan": "hours"/"days"/"weeks" (how long this trend will be relevant),
  "rejection_reason": "If rejected, why?" or null,
  "recommended_format": "comparison"/"explainer"/"ranking"/"timeline"/"prediction"/"highlights"
}}

Be strict - only approve trends that will make ENGAGING, SAFE, VISUAL content."""

    try:
        response = groq_client.chat_completions_create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,  # Lower for more consistent analysis
            max_tokens=800
        )

        response_text = response.choices[0].message.content.strip()

        # Remove markdown if present
        if response_text.startswith("```"):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])

        analysis = json.loads(response_text)

        is_worthy = analysis.get('is_video_worthy', False)
        return is_worthy, analysis

    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error in trend analysis: {e}")
        return False, {"error": "Invalid JSON response"}
    except Exception as e:
        print(f"❌ Trend analysis error: {e}")
        return False, {"error": str(e)}


def analyze_multiple_trends(trends: List[Dict], channel_theme: str, max_analyze: int = 10) -> List[Dict]:
    """
    Analyze multiple trends and return those suitable for videos.

    Args:
        trends: List of trend dictionaries
        channel_theme: Channel's content theme
        max_analyze: Maximum number to analyze (API rate limiting)

    Returns: List of approved trends with analysis
    """
    approved_trends = []

    for i, trend in enumerate(trends[:max_analyze]):
        print(f"\n🔍 Analyzing trend {i+1}/{min(len(trends), max_analyze)}: {trend['topic']}")

        is_worthy, analysis = analyze_trend_for_video(trend, channel_theme)

        if is_worthy:
            trend_with_analysis = {
                **trend,  # Original trend data
                'analysis': analysis,
                'analyzed_at': json.dumps(analysis)
            }
            approved_trends.append(trend_with_analysis)

            confidence = analysis.get('confidence', 0)
            format_rec = analysis.get('recommended_format', 'unknown')
            print(f"  ✅ APPROVED ({confidence}% confidence) - Format: {format_rec}")
        else:
            rejection = analysis.get('rejection_reason', 'Unknown')
            print(f"  ❌ REJECTED - {rejection}")

    print(f"\n✅ {len(approved_trends)} out of {min(len(trends), max_analyze)} trends approved for videos")
    return approved_trends


def rank_trends_by_urgency(trends: List[Dict]) -> List[Dict]:
    """
    Sort trends by urgency and potential.

    Priority order:
    1. Very urgent + very high interest
    2. Urgent + high interest
    3. Moderate urgency + medium interest
    """
    urgency_scores = {
        'very_urgent': 4,
        'urgent': 3,
        'moderate': 2,
        'low': 1
    }

    interest_scores = {
        'very_high': 4,
        'high': 3,
        'medium': 2,
        'low': 1
    }

    def get_priority_score(trend: Dict) -> int:
        analysis = trend.get('analysis', {})
        urgency = urgency_scores.get(analysis.get('urgency', 'low'), 1)
        interest = interest_scores.get(analysis.get('audience_interest', 'low'), 1)
        confidence = analysis.get('confidence', 50) / 100

        return int((urgency * 10 + interest * 10) * confidence)

    sorted_trends = sorted(trends, key=get_priority_score, reverse=True)
    return sorted_trends


def filter_trends_by_theme(trends: List[Dict], channel_theme: str) -> List[Dict]:
    """
    Filter trends to match channel theme.

    Theme categories:
    - "sports" → Sports-related trends
    - "entertainment" → Movies, TV, celebrities
    - "education" → Learning, how-to, explainers
    - "lifestyle" → Health, wellness, tips
    - "technology" → Tech, apps, products
    """
    theme_keywords = {
        'sports': ['game', 'team', 'player', 'championship', 'finals', 'match', 'vs', 'score', 'league'],
        'entertainment': ['movie', 'show', 'actor', 'series', 'premiere', 'trailer', 'season', 'celebrity'],
        'education': ['how to', 'learn', 'guide', 'tutorial', 'explain', 'understand', 'study'],
        'lifestyle': ['health', 'wellness', 'tips', 'habits', 'routine', 'self-care', 'mindful'],
        'technology': ['tech', 'app', 'software', 'device', 'update', 'release', 'feature', 'ai']
    }

    # Determine theme category
    theme_lower = channel_theme.lower()
    matched_keywords = []

    for category, keywords in theme_keywords.items():
        if any(keyword in theme_lower for keyword in keywords):
            matched_keywords.extend(keywords)

    if not matched_keywords:
        # Generic theme - accept all
        return trends

    # Filter trends
    filtered = []
    for trend in trends:
        topic_lower = trend['topic'].lower()
        analysis_category = trend.get('analysis', {}).get('content_category', '')

        # Check if topic contains theme keywords
        if any(keyword in topic_lower for keyword in matched_keywords):
            filtered.append(trend)
        # Or if AI categorized it as matching
        elif analysis_category in matched_keywords:
            filtered.append(trend)

    return filtered


def get_best_trend_for_channel(trends: List[Dict], channel_theme: str) -> Optional[Dict]:
    """
    Get the single best trend for a channel to make a video about.

    Returns: Best trend with full analysis, or None
    """
    if not trends:
        return None

    # Analyze all trends
    approved = analyze_multiple_trends(trends, channel_theme, max_analyze=15)

    if not approved:
        return None

    # Filter by theme
    theme_matched = filter_trends_by_theme(approved, channel_theme)

    if not theme_matched:
        # Use all approved if no theme matches
        theme_matched = approved

    # Rank by urgency
    ranked = rank_trends_by_urgency(theme_matched)

    # Return top trend
    return ranked[0] if ranked else None


# Example usage
if __name__ == "__main__":
    print("Testing Trend Analyzer...\n")

    # Test trend
    sample_trend = {
        'topic': 'Lakers vs Celtics Game 7',
        'category': 'sports',
        'search_volume': 'very_high',
        'source': 'google_realtime'
    }

    print(f"Analyzing: {sample_trend['topic']}\n")

    is_worthy, analysis = analyze_trend_for_video(sample_trend, "Sports highlights and analysis")

    if is_worthy:
        print(f"✅ APPROVED FOR VIDEO")
        print(f"Confidence: {analysis.get('confidence')}%")
        print(f"Format: {analysis.get('recommended_format')}")
        print(f"Angle: {analysis.get('suggested_video_angle')}")
    else:
        print(f"❌ REJECTED")
        print(f"Reason: {analysis.get('rejection_reason')}")

    print(f"\nFull Analysis:")
    print(json.dumps(analysis, indent=2))
