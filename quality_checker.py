#!/usr/bin/env python3
"""
QUALITY CHECKER FOR VIDEO CONTENT
Ensures videos meet engagement standards before posting.
"""

import re
from typing import Tuple, List, Dict

def check_title_quality(title: str) -> Tuple[bool, List[str]]:
    """
    Check if title meets quality standards.

    Returns: (is_valid, list_of_issues)
    """
    issues = []

    # Check 1: No ALL CAPS
    if title.isupper():
        issues.append("❌ Title is ALL CAPS (looks like spam)")

    # Check 2: Length check (under 60 chars for mobile)
    if len(title) > 60:
        issues.append(f"❌ Title too long ({len(title)} chars, max 60)")

    # Check 3: No clickbait patterns
    clickbait_patterns = [
        r"won't believe",
        r"you won't",
        r"will change",
        r"99%",
        r"secret",
        r"unlock",
        r"unleash",
        r"\d+x ",  # "10X", "5X", etc.
        r"in \d+ (second|minute)",  # "in 60 seconds"
        r"instant",
        r"insane",
        r"extreme",
        r"shocking"
    ]

    title_lower = title.lower()
    for pattern in clickbait_patterns:
        if re.search(pattern, title_lower):
            issues.append(f"❌ Clickbait detected: '{pattern}'")

    # Check 4: Has descriptive content (not just generic words)
    generic_words = ["top", "best", "ranked", "ranking", "most"]
    content_words = [w for w in title.lower().split() if w not in generic_words and len(w) > 3]

    if len(content_words) < 3:
        issues.append("❌ Too generic - needs more specific content words")

    # Check 5: Not too much punctuation
    if title.count('!') > 1:
        issues.append("❌ Too many exclamation marks (looks spammy)")

    is_valid = len(issues) == 0
    return is_valid, issues


def check_narration_quality(narration: str, target_duration_seconds: float) -> Tuple[bool, List[str]]:
    """
    Check if narration is appropriate length and quality.

    Returns: (is_valid, list_of_issues)
    """
    issues = []

    # Rough estimate: 2.5 words per second for natural speech
    word_count = len(narration.split())
    expected_words = int(target_duration_seconds * 2.5)

    if word_count > expected_words * 1.3:
        issues.append(f"❌ Narration too long ({word_count} words, max ~{expected_words})")

    if word_count < expected_words * 0.5:
        issues.append(f"❌ Narration too short ({word_count} words, min ~{int(expected_words * 0.7)})")

    # Check for exaggerations
    exaggerations = [
        "most extreme",
        "most insane",
        "will blow your mind",
        "life changing",
        "game changer",
        "100%",
        "absolutely"
    ]

    narration_lower = narration.lower()
    for phrase in exaggerations:
        if phrase in narration_lower:
            issues.append(f"⚠️ Exaggeration detected: '{phrase}'")

    is_valid = len(issues) == 0
    return is_valid, issues


def check_script_quality(script: Dict, ranking_count: int) -> Tuple[bool, List[str]]:
    """
    Check entire script for quality issues.

    Returns: (is_valid, list_of_all_issues)
    """
    all_issues = []

    # Check title
    title_valid, title_issues = check_title_quality(script.get('title', ''))
    all_issues.extend(title_issues)

    # Check each rank
    ranked_items = script.get('ranked_items', [])

    if len(ranked_items) != ranking_count:
        all_issues.append(f"❌ Wrong number of items ({len(ranked_items)}, expected {ranking_count})")

    for i, item in enumerate(ranked_items):
        # Check narration
        narration = item.get('narration', '')
        clip_duration = 45 / ranking_count

        narr_valid, narr_issues = check_narration_quality(narration, clip_duration)

        for issue in narr_issues:
            all_issues.append(f"Rank {item.get('rank', i+1)}: {issue}")

    is_valid = len(all_issues) == 0
    return is_valid, all_issues


def generate_quality_report(script: Dict, ranking_count: int) -> str:
    """
    Generate a human-readable quality report for a script.

    Returns: formatted report string
    """
    is_valid, issues = check_script_quality(script, ranking_count)

    report = "=" * 60 + "\n"
    report += "VIDEO QUALITY REPORT\n"
    report += "=" * 60 + "\n\n"

    report += f"Title: {script.get('title', 'N/A')}\n"
    report += f"Item Count: {len(script.get('ranked_items', []))}/{ranking_count}\n\n"

    if is_valid:
        report += "✅ PASSED - Script meets all quality standards!\n"
    else:
        report += f"❌ FAILED - Found {len(issues)} issues:\n\n"
        for i, issue in enumerate(issues, 1):
            report += f"{i}. {issue}\n"

    report += "\n" + "=" * 60 + "\n"

    return report


# Example usage
if __name__ == "__main__":
    # Test with bad title
    bad_title = "TOP 10 MOST EXTREME DESERT LANDSCAPES ON EARTH RANKED!"
    valid, issues = check_title_quality(bad_title)
    print(f"Bad Title: {bad_title}")
    print(f"Valid: {valid}")
    print(f"Issues: {issues}\n")

    # Test with good title
    good_title = "Most Calming Forest Sounds Ranked"
    valid, issues = check_title_quality(good_title)
    print(f"Good Title: {good_title}")
    print(f"Valid: {valid}")
    print(f"Issues: {issues}\n")
