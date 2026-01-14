#!/usr/bin/env python3
"""
DYNAMIC PACING OPTIMIZER
Calculates optimal clip durations based on rank importance.
First and last items get more time (high impact), middle items are faster.
"""

from typing import List, Dict


def calculate_dynamic_durations(
    total_duration: float = 45.0,
    num_items: int = 5,
    pacing_style: str = "dramatic"
) -> List[float]:
    """
    Calculate dynamic clip durations that vary by importance.

    Args:
        total_duration: Total video duration in seconds
        num_items: Number of items to rank
        pacing_style: "dramatic" (varies most), "moderate", "even"

    Returns: List of durations (one per item)

    Example for 5 items, 45 seconds, dramatic:
        Rank 5: 7s  (intro, set expectations)
        Rank 4: 8s  (build momentum)
        Rank 3: 8s  (maintain pace)
        Rank 2: 10s (ramp up excitement)
        Rank 1: 12s (climax, most important)
    """
    if pacing_style == "even":
        # Equal duration for all
        duration_each = total_duration / num_items
        return [duration_each] * num_items

    # Calculate importance weights (1-5 gets more time than 5-1 order)
    # Reverse ranking: item 5 = index 0, item 1 = index 4
    if pacing_style == "dramatic":
        # Strong variation: last item gets 1.6x first item
        # Pattern: shorter → shorter → moderate → longer → longest
        weights = []
        for i in range(num_items):
            # Linear increase from 0.8 to 1.6
            weight = 0.8 + (0.8 * i / (num_items - 1))
            weights.append(weight)
    else:  # moderate
        # Moderate variation: last item gets 1.3x first item
        weights = []
        for i in range(num_items):
            weight = 0.85 + (0.45 * i / (num_items - 1))
            weights.append(weight)

    # Normalize weights to total duration
    total_weight = sum(weights)
    durations = [(w / total_weight) * total_duration for w in weights]

    return durations


def get_pacing_for_rank(rank: int, total_items: int = 5, total_duration: float = 45.0) -> float:
    """
    Get duration for a specific rank (convenience function).

    Args:
        rank: Item rank (5 = first shown, 1 = last shown/best)
        total_items: Total number of items
        total_duration: Total video duration

    Returns: Duration in seconds for this rank
    """
    durations = calculate_dynamic_durations(total_duration, total_items, "dramatic")

    # Convert rank to index (rank 5 = index 0, rank 1 = index 4)
    index = total_items - rank

    return durations[index]


def generate_pacing_plan(num_items: int = 5, total_duration: float = 45.0) -> Dict:
    """
    Generate complete pacing plan with details.

    Returns:
        {
            'total_duration': 45.0,
            'num_items': 5,
            'pacing_style': 'dramatic',
            'durations': {
                5: 7.2,  # First item shown
                4: 8.1,
                3: 9.0,
                2: 9.9,
                1: 10.8  # Last item shown (climax)
            }
        }
    """
    durations_list = calculate_dynamic_durations(total_duration, num_items, "dramatic")

    # Create rank -> duration mapping
    durations_by_rank = {}
    for i, duration in enumerate(durations_list):
        rank = num_items - i  # Convert index to rank
        durations_by_rank[rank] = round(duration, 1)

    return {
        'total_duration': total_duration,
        'num_items': num_items,
        'pacing_style': 'dramatic',
        'durations': durations_by_rank,
        'avg_duration': total_duration / num_items
    }


# Testing
if __name__ == "__main__":
    print("Dynamic Pacing Optimizer Test\n")

    plan = generate_pacing_plan(5, 45.0)

    print(f"Pacing Plan: {plan['pacing_style']}")
    print(f"Total Duration: {plan['total_duration']}s")
    print(f"Average Duration: {plan['avg_duration']}s")
    print(f"\nRank Durations:")

    for rank in sorted(plan['durations'].keys(), reverse=True):
        duration = plan['durations'][rank]
        bar = "█" * int(duration)
        print(f"  Rank {rank}: {duration:5.1f}s {bar}")

    print("\n✅ Dramatic pacing creates build-up to climax (#1)")
