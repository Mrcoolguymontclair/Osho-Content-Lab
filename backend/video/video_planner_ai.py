#!/usr/bin/env python3
"""
VIDEO PLANNER AI
Uses Groq AI to decide EVERYTHING about a video based on trending topics.
Determines: video type, clip count, music, tone, structure, etc.
"""

import json
import os
from typing import Dict, Optional
from groq import Groq

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def plan_video_from_trend(trend: Dict, trend_analysis: Dict, channel_config: Dict) -> Optional[Dict]:
    """
    AI decides EVERYTHING about the video based on trending topic.

    Args:
        trend: Original trend data from google_trends_fetcher
        trend_analysis: AI analysis from trend_analyzer
        channel_config: Channel settings (theme, tone, style)

    Returns: Complete video specification dict or None if planning fails
    """
    if not groq_client:
        return None

    topic = trend.get('topic', 'Unknown')
    channel_theme = channel_config.get('theme', 'General content')
    channel_tone = channel_config.get('tone', 'informative')

    # Extract key info from trend analysis
    video_format = trend_analysis.get('recommended_format', 'explainer')
    visual_potential = trend_analysis.get('visual_potential', 'medium')
    audience_interest = trend_analysis.get('audience_interest', 'medium')
    urgency = trend_analysis.get('urgency', 'moderate')
    suggested_angle = trend_analysis.get('suggested_video_angle', '')

    prompt = f"""You are a YouTube Shorts content strategist. Plan a COMPLETE 45-second video about this trending topic.

TRENDING TOPIC: {topic}
CATEGORY: {trend.get('category', 'unknown')}
SEARCH VOLUME: {trend.get('search_volume', 'unknown')}

CHANNEL INFO:
- Theme: {channel_theme}
- Tone: {channel_tone}
- Style: {channel_config.get('style', 'modern')}

AI ANALYSIS:
- Recommended Format: {video_format}
- Visual Potential: {visual_potential}
- Audience Interest: {audience_interest}
- Urgency: {urgency}
- Suggested Angle: {suggested_angle}

Your task: Design a COMPLETE video specification that will maximize engagement.

VIDEO TYPES YOU CAN USE:
1. **comparison** - "X vs Y" format (e.g., "Lakers vs Celtics: Key Differences")
2. **explainer** - "What is X?" educational format
3. **timeline** - "History of X" chronological format
4. **prediction** - "What to expect from X" future-focused
5. **tutorial** - "How to understand/follow X" instructional
6. **highlights** - "Best moments of X" compilation
7. **ranking** - "Top N X ranked" countdown format

CRITICAL DECISIONS TO MAKE:
1. **Video Type**: Choose the BEST format for this topic
2. **Clip Count**: How many segments? (3-10 clips, each clip = 45s ÷ count)
3. **Music Style**: energetic, calm, dramatic, upbeat, ambient, epic
4. **Tone**: educational, entertaining, hype, informative, inspirational
5. **Hook Strategy**: How to grab attention in first 3 seconds
6. **Segment Structure**: What each clip should show

TITLE RULES (CRITICAL):
- Title Case only (not ALL CAPS)
- Under 60 characters
- Descriptive and specific
- No clickbait ("won't believe", "secret", "unlock")
- Must match trending topic

CONTENT SAFETY:
- No medical/legal/financial advice
- No controversial politics
- No tragedy/negative news
- Must have good visual potential

Output ONLY valid JSON (no markdown):
{{
  "video_type": "comparison|explainer|timeline|prediction|tutorial|highlights|ranking",
  "clip_count": 3-10,
  "total_duration": 45,
  "title": "Engaging title under 60 chars (Title Case)",
  "hook": "First line of narration (grabs attention)",
  "music_style": "energetic|calm|dramatic|upbeat|ambient|epic",
  "tone": "educational|entertaining|hype|informative|inspirational",
  "pacing": "fast|medium|slow",
  "segments": [
    {{
      "segment_number": 1,
      "duration": <45 / clip_count>,
      "visual_description": "What should the Pexels clip show?",
      "narration": "What the voiceover should say",
      "search_query": "Pexels search query for this clip",
      "text_overlay": "Optional text to show on screen (or null)"
    }}
  ],
  "description": "YouTube description (1-2 sentences)",
  "tags": ["tag1", "tag2", "tag3"],
  "reasoning": "Why this format/structure will work best for this trend"
}}

Be specific and detailed. Every segment must have exact narration and visual descriptions.
The video MUST be exactly 45 seconds total (segments must sum to 45)."""

    try:
        response = groq_client.chat_completions_create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,  # Balance creativity with consistency
            max_tokens=2000  # Longer for detailed segment planning
        )

        response_text = response.choices[0].message.content.strip()

        # Remove markdown if present
        if response_text.startswith("```"):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])

        video_plan = json.loads(response_text)

        # Validation
        if not validate_video_plan(video_plan):
            print("[ERROR] Video plan failed validation")
            return None

        # Add metadata
        video_plan['trend_topic'] = topic
        video_plan['trend_source'] = trend.get('source', 'unknown')
        video_plan['urgency'] = urgency

        return video_plan

    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse error in video planning: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Video planning error: {e}")
        return None


def validate_video_plan(plan: Dict) -> bool:
    """
    Validate that AI-generated video plan meets requirements.

    Returns: True if valid, False otherwise
    """
    required_fields = ['video_type', 'clip_count', 'title', 'segments', 'music_style', 'tone']

    # Check required fields
    for field in required_fields:
        if field not in plan:
            print(f"[ERROR] Missing required field: {field}")
            return False

    # Validate video type
    valid_types = ['comparison', 'explainer', 'timeline', 'prediction', 'tutorial', 'highlights', 'ranking']
    if plan['video_type'] not in valid_types:
        print(f"[ERROR] Invalid video type: {plan['video_type']}")
        return False

    # Validate clip count
    clip_count = plan['clip_count']
    if not isinstance(clip_count, int) or clip_count < 3 or clip_count > 10:
        print(f"[ERROR] Invalid clip count: {clip_count} (must be 3-10)")
        return False

    # Validate segments
    segments = plan.get('segments', [])
    if len(segments) != clip_count:
        print(f"[ERROR] Segment count mismatch: {len(segments)} segments, expected {clip_count}")
        return False

    # Validate each segment
    for i, segment in enumerate(segments):
        required_segment_fields = ['segment_number', 'duration', 'visual_description', 'narration', 'search_query']
        for field in required_segment_fields:
            if field not in segment:
                print(f"[ERROR] Segment {i+1} missing field: {field}")
                return False

    # Validate total duration
    total_duration = sum(seg['duration'] for seg in segments)
    if abs(total_duration - 45) > 1:  # Allow 1 second tolerance
        print(f"[ERROR] Total duration {total_duration}s != 45s")
        return False

    # Validate title length
    title = plan.get('title', '')
    if len(title) > 60:
        print(f"[ERROR] Title too long: {len(title)} chars (max 60)")
        return False

    # Check for ALL CAPS (spam indicator)
    if title.isupper():
        print(f"[ERROR] Title is ALL CAPS (spam)")
        return False

    return True


def plan_comparison_video(topic_a: str, topic_b: str, channel_config: Dict) -> Optional[Dict]:
    """
    Plan a comparison video ("X vs Y" format).

    Args:
        topic_a: First topic to compare
        topic_b: Second topic to compare
        channel_config: Channel settings

    Returns: Video plan or None
    """
    if not groq_client:
        return None

    prompt = f"""Plan a 45-second comparison video: "{topic_a} vs {topic_b}"

Channel: {channel_config.get('theme', 'General')}
Tone: {channel_config.get('tone', 'informative')}

Structure this as a direct comparison with:
- Opening: Introduce both topics
- Comparison points: 3-5 key differences
- Conclusion: Summary/verdict

Output the same JSON format as plan_video_from_trend (segments, narration, etc.)
Total duration: exactly 45 seconds
Title: Under 60 chars, Title Case"""

    try:
        response = groq_client.chat_completions_create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )

        response_text = response.choices[0].message.content.strip()
        if response_text.startswith("```"):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])

        video_plan = json.loads(response_text)

        if validate_video_plan(video_plan):
            video_plan['video_type'] = 'comparison'
            return video_plan

        return None

    except Exception as e:
        print(f"[ERROR] Comparison planning error: {e}")
        return None


def plan_timeline_video(topic: str, time_range: str, channel_config: Dict) -> Optional[Dict]:
    """
    Plan a timeline/history video.

    Args:
        topic: What to show the timeline of
        time_range: "2020-2024", "last decade", "evolution", etc.
        channel_config: Channel settings

    Returns: Video plan or None
    """
    if not groq_client:
        return None

    prompt = f"""Plan a 45-second timeline video: "History of {topic}" ({time_range})

Channel: {channel_config.get('theme', 'General')}
Tone: {channel_config.get('tone', 'informative')}

Structure chronologically:
- Start with earliest event/era
- Progress through key milestones
- End with current state or future

Each segment = a different time period.
Use 4-6 segments for good pacing.

Output the same JSON format (segments, narration, etc.)
Total duration: exactly 45 seconds
Title: Under 60 chars, Title Case"""

    try:
        response = groq_client.chat_completions_create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )

        response_text = response.choices[0].message.content.strip()
        if response_text.startswith("```"):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])

        video_plan = json.loads(response_text)

        if validate_video_plan(video_plan):
            video_plan['video_type'] = 'timeline'
            return video_plan

        return None

    except Exception as e:
        print(f"[ERROR] Timeline planning error: {e}")
        return None


def get_video_plan_summary(plan: Dict) -> str:
    """
    Generate a human-readable summary of the video plan.

    Returns: Formatted summary string
    """
    summary = "=" * 60 + "\n"
    summary += "VIDEO PLAN SUMMARY\n"
    summary += "=" * 60 + "\n\n"

    summary += f"Title: {plan.get('title', 'N/A')}\n"
    summary += f"Type: {plan.get('video_type', 'N/A').upper()}\n"
    summary += f"Clips: {plan.get('clip_count', 0)}\n"
    summary += f"Duration: {plan.get('total_duration', 45)}s\n"
    summary += f"Music: {plan.get('music_style', 'N/A')}\n"
    summary += f"Tone: {plan.get('tone', 'N/A')}\n"
    summary += f"Hook: {plan.get('hook', 'N/A')}\n\n"

    summary += "SEGMENTS:\n"
    for i, segment in enumerate(plan.get('segments', []), 1):
        summary += f"\n{i}. [{segment.get('duration', 0)}s] {segment.get('visual_description', 'N/A')}\n"
        summary += f"   Narration: \"{segment.get('narration', 'N/A')}\"\n"
        summary += f"   Search: {segment.get('search_query', 'N/A')}\n"

    summary += "\n" + "=" * 60 + "\n"

    return summary


# Example usage
if __name__ == "__main__":
    print("Testing Video Planner AI...\n")

    # Test with sample trend
    sample_trend = {
        'topic': 'Lakers vs Celtics Game 7',
        'category': 'sports',
        'search_volume': 'very_high',
        'source': 'google_realtime'
    }

    sample_analysis = {
        'is_video_worthy': True,
        'confidence': 85,
        'visual_potential': 'high',
        'audience_interest': 'very_high',
        'urgency': 'very_urgent',
        'recommended_format': 'highlights',
        'suggested_video_angle': 'Show best moments from the game with key plays'
    }

    sample_channel = {
        'theme': 'Sports highlights and analysis',
        'tone': 'energetic',
        'style': 'modern'
    }

    print(f"Planning video for: {sample_trend['topic']}\n")

    video_plan = plan_video_from_trend(sample_trend, sample_analysis, sample_channel)

    if video_plan:
        print("[OK] VIDEO PLAN GENERATED\n")
        print(get_video_plan_summary(video_plan))

        print("\nFull JSON:")
        print(json.dumps(video_plan, indent=2))
    else:
        print("[ERROR] PLANNING FAILED")
