#!/usr/bin/env python3
"""
TITLE & THUMBNAIL OPTIMIZER
Data-driven title and thumbnail generation based on top performers.

Analysis shows:
- Top videos use "TOP 10", "RANKED!", "DEADLIEST", "EXTREME"
- ALL CAPS titles perform better
- Specific numbers (10) beat vague titles
- Superlatives work: "MOST", "DEADLIEST", "EXTREME"
"""

import re
from typing import List, Dict, Tuple, Optional
import random


class TitleThumbnailOptimizer:
    """
    Optimizes titles and thumbnails based on proven patterns.
    """

    def __init__(self):
        # Power words that drive clicks (from top performing videos)
        self.power_words = [
            "EXTREME", "DEADLIEST", "MOST", "INSANE", "SHOCKING",
            "UNBELIEVABLE", "TERRIFYING", "BREATHTAKING", "EPIC",
            "MIND-BLOWING", "ULTIMATE", "CRAZIEST", "WILDEST"
        ]

        # Proven title formats (from analysis of top videos)
        self.title_formats = [
            "TOP {count} {superlative} {topic} RANKED!",
            "TOP {count} MOST {adjective} {topic} ON EARTH RANKED!",
            "{superlative} {topic} RANKED FROM WORST TO BEST!",
            "TOP {count} {adjective} {topic} YOU WON'T BELIEVE!",
            "RANKING THE {count} MOST {adjective} {topic}!",
        ]

    def optimize_ranking_title(
        self,
        topic: str,
        count: int = 10,
        make_extreme: bool = True
    ) -> str:
        """
        Generate optimized ranking title based on proven patterns.

        Args:
            topic: Base topic
            count: Number of items (use specific numbers like 10, not 5)
            make_extreme: Add superlatives for more engagement

        Returns: Optimized title
        """
        # Extract key noun from topic
        topic_clean = self._clean_topic(topic)

        if make_extreme:
            # Add superlative
            superlative = random.choice(self.power_words)
            format_template = random.choice(self.title_formats)

            title = format_template.format(
                count=count,
                superlative=superlative,
                adjective=random.choice(["EXTREME", "DANGEROUS", "AMAZING", "INCREDIBLE"]),
                topic=topic_clean.upper()
            )
        else:
            title = f"TOP {count} {topic_clean.upper()} RANKED!"

        # Ensure title ends with exclamation (higher engagement)
        if not title.endswith('!'):
            title += '!'

        return title

    def _clean_topic(self, topic: str) -> str:
        """Clean and format topic"""
        # Remove common ranking words
        topic = re.sub(r'\b(ranking|ranked|top|best|worst)\b', '', topic, flags=re.IGNORECASE)
        # Remove extra spaces
        topic = ' '.join(topic.split())
        return topic.strip()

    def generate_thumbnail_text(
        self,
        title: str,
        rank: Optional[int] = None,
        max_words: int = 4
    ) -> str:
        """
        Generate short, punchy text for thumbnail.

        Research shows thumbnails with 2-4 words perform best.

        Args:
            title: Full video title
            rank: Ranking number to highlight
            max_words: Maximum words in thumbnail

        Returns: Thumbnail text
        """
        # Extract key words from title
        words = title.upper().split()

        # Remove common words
        stop_words = {'THE', 'A', 'AN', 'OF', 'ON', 'IN', 'AT', 'TO', 'FOR', 'FROM'}
        key_words = [w for w in words if w not in stop_words]

        # Prioritize power words
        power_words_in_title = [w for w in key_words if w in self.power_words]

        if power_words_in_title:
            # Use power word + context
            thumbnail_text = ' '.join(power_words_in_title[:1] + key_words[-2:])
        elif rank:
            # Use rank as focal point
            thumbnail_text = f"#{rank}\n{' '.join(key_words[:2])}"
        else:
            # Use first few key words
            thumbnail_text = ' '.join(key_words[:max_words])

        return thumbnail_text[:30]  # Limit to 30 chars for readability

    def generate_thumbnail_config(
        self,
        title: str,
        rank: Optional[int] = None,
        style: str = "bold"
    ) -> Dict:
        """
        Generate complete thumbnail configuration.

        Args:
            title: Video title
            rank: Ranking number
            style: Visual style ("bold", "neon", "minimal")

        Returns: Thumbnail config dict
        """
        text = self.generate_thumbnail_text(title, rank)

        styles = {
            'bold': {
                'background_color': '#FF0000',  # Red
                'text_color': '#FFFFFF',  # White
                'accent_color': '#FFD700',  # Gold
                'font_size': 120,
                'font_weight': 'bold'
            },
            'neon': {
                'background_color': '#000000',  # Black
                'text_color': '#00FFFF',  # Cyan
                'accent_color': '#FF00FF',  # Magenta
                'font_size': 110,
                'font_weight': 'bold'
            },
            'minimal': {
                'background_color': '#FFFFFF',  # White
                'text_color': '#000000',  # Black
                'accent_color': '#FF0000',  # Red
                'font_size': 100,
                'font_weight': 'normal'
            }
        }

        style_config = styles.get(style, styles['bold'])

        return {
            'text': text,
            'rank': rank,
            **style_config
        }

    def analyze_title_effectiveness(self, title: str) -> Dict:
        """
        Analyze title and predict effectiveness.

        Args:
            title: Title to analyze

        Returns: Analysis dict with score and suggestions
        """
        score = 0
        suggestions = []
        reasons = []

        # Check for ALL CAPS
        if title.isupper():
            score += 20
            reasons.append("[OK] ALL CAPS (proven to increase CTR)")
        else:
            suggestions.append("Use ALL CAPS for higher engagement")

        # Check for specific numbers
        if re.search(r'\b(10|5|20|7)\b', title):
            score += 15
            reasons.append("[OK] Specific number (10, 5, etc.)")
        else:
            suggestions.append("Add specific number (TOP 10, not TOP FIVE)")

        # Check for power words
        power_words_found = [w for w in self.power_words if w in title.upper()]
        if power_words_found:
            score += 15
            reasons.append(f"[OK] Power words: {', '.join(power_words_found[:2])}")
        else:
            suggestions.append(f"Add power words: {', '.join(self.power_words[:3])}")

        # Check for exclamation
        if title.endswith('!'):
            score += 10
            reasons.append("[OK] Ends with exclamation")
        else:
            suggestions.append("End with ! for excitement")

        # Check for "RANKED"
        if 'RANKED' in title.upper():
            score += 15
            reasons.append("[OK] Contains 'RANKED' (proven format)")

        # Check for superlatives
        superlatives = ['MOST', 'BEST', 'WORST', 'EXTREME', 'ULTIMATE']
        if any(s in title.upper() for s in superlatives):
            score += 10
            reasons.append("[OK] Uses superlatives")

        # Check length (50-70 chars is optimal for YouTube)
        if 50 <= len(title) <= 70:
            score += 15
            reasons.append("[OK] Optimal length (50-70 chars)")
        elif len(title) < 50:
            suggestions.append("Title too short - add more context")
        else:
            suggestions.append("Title too long - will be cut off")

        return {
            'score': score,
            'max_score': 100,
            'grade': self._score_to_grade(score),
            'reasons': reasons,
            'suggestions': suggestions
        }

    def _score_to_grade(self, score: int) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        else:
            return 'D'

    def improve_title(self, title: str) -> str:
        """
        Automatically improve a title based on proven patterns.

        Args:
            title: Original title

        Returns: Improved title
        """
        # Extract topic
        topic = self._clean_topic(title)

        # Check if it's a ranking video
        is_ranking = any(word in title.lower() for word in ['ranking', 'ranked', 'top', 'best', 'worst'])

        if is_ranking:
            # Extract count if present
            count_match = re.search(r'\b(\d+)\b', title)
            count = int(count_match.group(1)) if count_match else 10

            # Regenerate with optimal format
            return self.optimize_ranking_title(topic, count=count, make_extreme=True)
        else:
            # For non-ranking, add power word and exclamation
            power_word = random.choice(self.power_words)
            return f"{power_word} {topic.upper()}!"


# Testing
if __name__ == "__main__":
    print("=" * 70)
    print("[TARGET] TITLE & THUMBNAIL OPTIMIZER")
    print("=" * 70)

    optimizer = TitleThumbnailOptimizer()

    # Test 1: Generate optimized title
    print("\n1⃣ Title Optimization:")
    topics = [
        "Roller Coasters",
        "Natural Wonders",
        "Fast Food Fries"
    ]

    for topic in topics:
        title = optimizer.optimize_ranking_title(topic, count=10, make_extreme=True)
        print(f"   {topic:20s} → {title}")

    # Test 2: Analyze existing titles
    print("\n2⃣ Title Analysis:")
    test_titles = [
        "TOP 10 DEADLIEST ROLLER COASTERS RANKED!",  # Good
        "top 5 roller coasters",  # Bad
        "Ranking Some Interesting Places"  # Bad
    ]

    for title in test_titles:
        analysis = optimizer.analyze_title_effectiveness(title)
        print(f"\n   Title: {title}")
        print(f"   Score: {analysis['score']}/100 (Grade: {analysis['grade']})")
        if analysis['reasons']:
            print(f"   [OK] Strengths: {analysis['reasons'][0]}")
        if analysis['suggestions']:
            print(f"   [IDEA] Improve: {analysis['suggestions'][0]}")

    # Test 3: Thumbnail text generation
    print("\n3⃣ Thumbnail Text:")
    title = "TOP 10 MOST EXTREME UNDERWATER CAVERNS RANKED!"
    for rank in [5, 3, 1]:
        thumb_text = optimizer.generate_thumbnail_text(title, rank=rank)
        print(f"   Rank #{rank}: {thumb_text}")

    # Test 4: Auto-improve bad title
    print("\n4⃣ Title Improvement:")
    bad_title = "ranking some interesting roller coasters"
    improved = optimizer.improve_title(bad_title)
    print(f"   Before: {bad_title}")
    print(f"   After:  {improved}")
    analysis = optimizer.analyze_title_effectiveness(improved)
    print(f"   Score:  {analysis['score']}/100 (Grade: {analysis['grade']})")

    print("\n[OK] Title & thumbnail optimization ready!")
    print("\n" + "=" * 70)
