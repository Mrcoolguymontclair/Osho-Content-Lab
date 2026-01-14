#!/usr/bin/env python3
"""
VIRAL TOPIC SELECTOR
Generates actually interesting topics that people want to watch.

Problem: Generic topics like "extreme landscapes" get 0 views.
Solution: Human interest topics with mystery, danger, and curiosity.
"""

import random
from typing import Dict, List

# ==============================================================================
# PROVEN VIRAL TOPICS (Based on successful videos)
# ==============================================================================

VIRAL_TOPIC_CATEGORIES = {
    "dangerous_animals": {
        "weight": 10,  # High priority
        "templates": [
            "deadliest {animal_type} on earth",
            "most dangerous {animal_type} that can kill you",
            "scariest {animal_type} encounters",
            "most venomous {animal_type} in the world",
            "terrifying {animal_type} you should avoid"
        ],
        "animal_types": ["snakes", "spiders", "sharks", "insects", "sea creatures", "predators", "animals"]
    },

    "extreme_jobs": {
        "weight": 9,
        "templates": [
            "most dangerous jobs in the world",
            "deadliest occupations on earth",
            "scariest jobs that pay well",
            "most extreme careers",
            "jobs with highest death rates"
        ]
    },

    "mysterious_places": {
        "weight": 9,
        "templates": [
            "most mysterious places on earth",
            "creepiest abandoned locations",
            "haunted places caught on camera",
            "forbidden zones you can't visit",
            "scariest places on the planet"
        ]
    },

    "bizarre_food": {
        "weight": 8,
        "templates": [
            "weirdest foods people actually eat",
            "most disgusting delicacies around the world",
            "bizarre foods that taste amazing",
            "strangest dishes from different countries",
            "foods banned in most countries"
        ]
    },

    "survival_skills": {
        "weight": 8,
        "templates": [
            "survival skills that could save your life",
            "things you need to survive in the wild",
            "deadly mistakes people make when lost",
            "how to survive {situation}",
            "essential survival tactics"
        ],
        "situations": ["a plane crash", "in the wilderness", "a natural disaster", "being lost at sea", "extreme cold"]
    },

    "human_achievements": {
        "weight": 7,
        "templates": [
            "most isolated research stations on earth",
            "extreme places humans live",
            "most dangerous bridges in the world",
            "scariest roads on the planet",
            "deadliest hiking trails"
        ]
    },

    "natural_disasters": {
        "weight": 8,
        "templates": [
            "deadliest natural disasters in history",
            "most dangerous volcanoes about to erupt",
            "worst tsunamis caught on camera",
            "most powerful earthquakes ever recorded",
            "scariest tornadoes ever filmed"
        ]
    },

    "true_crime": {
        "weight": 7,
        "templates": [
            "unsolved mysteries that still baffle experts",
            "creepiest unsolved cases",
            "most bizarre disappearances",
            "strangest cold cases ever",
            "mysterious events with no explanation"
        ]
    },

    "extreme_sports": {
        "weight": 6,
        "templates": [
            "deadliest roller coasters",
            "most insane stunts ever performed",
            "scariest extreme sports",
            "most dangerous amusement park rides",
            "craziest base jumping spots"
        ]
    },

    "technology_fails": {
        "weight": 6,
        "templates": [
            "worst tech fails of all time",
            "most expensive tech disasters",
            "products that flopped spectacularly",
            "biggest engineering failures",
            "dangerous products that were recalled"
        ]
    }
}

# ==============================================================================
# BAD TOPICS TO AVOID (Get 0 views)
# ==============================================================================

BORING_TOPICS = [
    "landscapes", "formations", "mountain ranges", "deserts",
    "ice formations", "geothermal wonders", "geyser landscapes",
    "mud volcanoes", "geological features"
]

# ==============================================================================
# Topic Selection Functions
# ==============================================================================

def get_viral_topic(recent_topics: List[str] = None) -> Dict[str, str]:
    """
    Generate a viral topic that people actually want to watch.

    Args:
        recent_topics: List of recent video topics to avoid duplicates

    Returns:
        Dict with 'topic', 'category', 'search_hint'
    """
    recent_topics = recent_topics or []

    # Weight-based random selection
    categories = []
    weights = []

    for category, data in VIRAL_TOPIC_CATEGORIES.items():
        categories.append(category)
        weights.append(data['weight'])

    # Try up to 10 times to find non-duplicate
    for _ in range(10):
        category = random.choices(categories, weights=weights)[0]
        topic_data = VIRAL_TOPIC_CATEGORIES[category]

        # Select random template
        template = random.choice(topic_data['templates'])

        # Fill in variables if template has them
        if '{animal_type}' in template and 'animal_types' in topic_data:
            animal = random.choice(topic_data['animal_types'])
            topic = template.format(animal_type=animal)
        elif '{situation}' in template and 'situations' in topic_data:
            situation = random.choice(topic_data['situations'])
            topic = template.format(situation=situation)
        else:
            topic = template

        # Check if not duplicate
        if not any(topic.lower() in recent.lower() for recent in recent_topics):
            return {
                'topic': topic,
                'category': category,
                'search_hint': _get_search_hint(category)
            }

    # Fallback: return anyway
    return {
        'topic': topic,
        'category': category,
        'search_hint': _get_search_hint(category)
    }

def _get_search_hint(category: str) -> str:
    """Get search query hints for Pexels."""
    hints = {
        "dangerous_animals": "dangerous animal wildlife predator",
        "extreme_jobs": "dangerous work extreme occupation",
        "mysterious_places": "mysterious abandoned eerie location",
        "bizarre_food": "exotic food strange dish",
        "survival_skills": "survival wilderness outdoor",
        "human_achievements": "extreme location isolated structure",
        "natural_disasters": "natural disaster destruction",
        "true_crime": "mystery investigation dark",
        "extreme_sports": "extreme sport action adrenaline",
        "technology_fails": "technology disaster explosion"
    }
    return hints.get(category, "interesting amazing")

def is_boring_topic(topic: str) -> bool:
    """Check if topic contains boring keywords."""
    topic_lower = topic.lower()
    return any(boring in topic_lower for boring in BORING_TOPICS)

def get_engaging_theme(recent_videos: List[Dict] = None) -> str:
    """
    Get an engaging theme for video generation.

    Returns theme string that will generate interesting content.
    """
    recent_videos = recent_videos or []
    recent_topics = [v.get('title', '') for v in recent_videos]

    viral_topic = get_viral_topic(recent_topics)
    return viral_topic['topic']

# ==============================================================================
# Testing
# ==============================================================================

if __name__ == "__main__":
    print("VIRAL TOPIC SELECTOR - Testing")
    print("=" * 70)
    print("\nGenerating 10 viral topics:\n")

    recent = []
    for i in range(10):
        topic_data = get_viral_topic(recent)
        print(f"{i+1}. [{topic_data['category']}] {topic_data['topic']}")
        recent.append(topic_data['topic'])

    print("\n" + "=" * 70)
    print("\nThese topics have:")
    print("✅ Human interest (danger, mystery, curiosity)")
    print("✅ Emotional hooks (fear, surprise, shock)")
    print("✅ Click-worthy titles")
    print("✅ Variety (not all landscapes!)")
    print("\n❌ AVOID: Boring landscapes, formations, geological features")
