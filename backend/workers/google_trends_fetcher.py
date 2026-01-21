#!/usr/bin/env python3
"""
GOOGLE TRENDS FETCHER
Fetches trending topics from multiple sources for autonomous video generation.
Uses Google Trends RSS feeds (official, reliable, not rate-limited).
"""

import time
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

def fetch_google_trends(region: str = 'US', timeframe: str = 'now 1-d') -> List[Dict]:
    """
    Fetch trending topics from Google Trends RSS feed.

    This uses the official Google Trends RSS feed which is:
    - NOT rate limited
    - Always up-to-date (real-time trends)
    - Official Google endpoint
    - Much more reliable than pytrends library

    Args:
        region: Country code (US, GB, CA, etc.)
        timeframe: Ignored (RSS gives current trends)

    Returns: List of trending topics with metadata
    """
    try:
        # Official Google Trends RSS feed - not rate limited!
        url = f'https://trends.google.com/trending/rss?geo={region}'

        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        if response.status_code != 200:
            print(f"[WARNING] RSS feed returned status {response.status_code}")
            return []

        # Parse RSS feed
        feed = feedparser.parse(response.content)

        if not feed.entries:
            print("[WARNING] No entries in RSS feed")
            return []

        trends = []
        for idx, entry in enumerate(feed.entries[:20], 1):  # Top 20 trends
            title = entry.get('title', 'Unknown')
            traffic = entry.get('ht_approx_traffic', 'unknown')

            # Determine search volume based on traffic
            if '+' in str(traffic):
                traffic_num = int(str(traffic).replace('+', '').replace(',', ''))
                if traffic_num >= 50000:
                    volume = 'very_high'
                elif traffic_num >= 10000:
                    volume = 'high'
                elif traffic_num >= 2000:
                    volume = 'medium'
                else:
                    volume = 'normal'
            else:
                volume = 'medium'

            trend = {
                'topic': title,
                'source': 'google_trends_rss',
                'region': region,
                'rank': idx,
                'fetched_at': datetime.now().isoformat(),
                'category': 'unknown',  # Will be categorized by AI
                'search_volume': volume,
                'traffic': str(traffic)
            }
            trends.append(trend)

        return trends

    except Exception as e:
        print(f"[WARNING] Google Trends RSS fetch error: {str(e)[:100]}")
        return []


def fetch_realtime_trends(region: str = 'US', category: str = 'all') -> List[Dict]:
    """
    Fetch real-time trending searches using daily RSS feed.

    Note: RSS feed is updated throughout the day with real-time trends.

    Args:
        region: Country code
        category: Ignored for RSS (use fetch_google_trends instead)

    Returns: List of real-time trends
    """
    # RSS feed gives real-time trends, so just use the main fetch function
    # This ensures we're not duplicating trends
    return []  # Disabled to avoid duplicates, use fetch_google_trends() instead


def get_trending_topics_by_category(category: str, region: str = 'US') -> List[Dict]:
    """
    Get trending topics for specific categories.

    NOTE: RSS feed doesn't support category filtering.
    The AI will categorize trends after fetching.

    Categories:
    - 'sports' - Sports events, games, teams
    - 'entertainment' - Movies, TV, celebrities
    - 'business' - Tech, finance, products
    - 'science' - Science, health, technology

    Returns: Empty list (let AI categorize instead)
    """
    # RSS doesn't support categories - AI will categorize trends after fetching
    return []


def get_interest_over_time(keyword: str, region: str = 'US') -> Optional[Dict]:
    """
    Get search interest trend over time for a specific keyword.

    NOTE: Disabled - pytrends API is unreliable.
    RSS feed provides current interest level in traffic numbers.

    Returns: None (disabled)
    """
    # Disabled - unreliable API
    return None


def get_fallback_trends() -> List[Dict]:
    """
    Return sample trending topics when Google Trends API is unavailable.
    These are generic but realistic trending topics for testing.
    """
    now = datetime.now()
    sample_trends = [
        # Sports
        {'topic': 'NBA Highlights Today', 'category': 'sports', 'search_volume': 'high'},
        {'topic': 'NFL Playoff Predictions', 'category': 'sports', 'search_volume': 'high'},
        {'topic': 'Premier League Results', 'category': 'sports', 'search_volume': 'medium'},

        # Entertainment
        {'topic': 'New Movies 2026', 'category': 'entertainment', 'search_volume': 'high'},
        {'topic': 'Grammy Awards 2026', 'category': 'entertainment', 'search_volume': 'medium'},
        {'topic': 'Trending Music Videos', 'category': 'entertainment', 'search_volume': 'medium'},

        # Technology
        {'topic': 'iPhone 16 Features', 'category': 'technology', 'search_volume': 'high'},
        {'topic': 'AI Tools 2026', 'category': 'technology', 'search_volume': 'medium'},
        {'topic': 'Best Tech Gadgets', 'category': 'technology', 'search_volume': 'medium'},

        # General
        {'topic': 'Winter Storm Updates', 'category': 'news', 'search_volume': 'high'},
        {'topic': 'Stock Market Today', 'category': 'business', 'search_volume': 'medium'},
        {'topic': 'Travel Destinations 2026', 'category': 'lifestyle', 'search_volume': 'medium'},
    ]

    trends = []
    for idx, sample in enumerate(sample_trends):
        trend = {
            'topic': sample['topic'],
            'source': 'fallback',
            'region': 'US',
            'rank': idx + 1,
            'fetched_at': now.isoformat(),
            'category': sample['category'],
            'search_volume': sample['search_volume']
        }
        trends.append(trend)

    return trends


def fetch_all_trends(region: str = 'US') -> Dict[str, List[Dict]]:
    """
    Fetch trends from all sources.
    Falls back to sample trends if Google Trends API is unavailable.

    Returns: Dictionary of trends by source
    """
    print(f" Fetching trends for {region}...")

    all_trends = {
        'google_daily': [],
        'google_realtime': [],
        'sports': [],
        'entertainment': [],
        'business': [],
        'timestamp': datetime.now().isoformat()
    }

    total_fetched = 0

    # Fetch from different sources
    try:
        all_trends['google_daily'] = fetch_google_trends(region=region)
        total_fetched += len(all_trends['google_daily'])
        print(f"[OK] Found {len(all_trends['google_daily'])} daily trends")
    except Exception as e:
        print(f"[WARNING] Daily trends failed: {str(e)[:50]}")

    try:
        all_trends['google_realtime'] = fetch_realtime_trends(region=region)
        total_fetched += len(all_trends['google_realtime'])
        print(f"[OK] Found {len(all_trends['google_realtime'])} realtime trends")
    except Exception as e:
        print(f"[WARNING] Realtime trends failed: {str(e)[:50]}")

    # Category-specific
    for category in ['sports', 'entertainment', 'business']:
        try:
            all_trends[category] = get_trending_topics_by_category(category, region=region)
            total_fetched += len(all_trends[category])
            print(f"[OK] Found {len(all_trends[category])} {category} trends")
        except Exception as e:
            print(f"[WARNING] {category} trends failed: {str(e)[:50]}")

    # If all sources failed, use fallback trends
    if total_fetched == 0:
        print("\n[WARNING] Google Trends API unavailable, using fallback trending topics")
        print("ℹ System will still work, these are realistic sample trends\n")

        fallback = get_fallback_trends()
        # Distribute fallback trends across categories
        all_trends['google_daily'] = fallback[:4]
        all_trends['sports'] = [t for t in fallback if t['category'] == 'sports']
        all_trends['entertainment'] = [t for t in fallback if t['category'] == 'entertainment']
        all_trends['business'] = [t for t in fallback if t['category'] == 'business']

        print(f"[OK] Loaded {len(fallback)} fallback trends for testing")

    # Deduplicate across sources
    all_trends = deduplicate_trends(all_trends)

    return all_trends


def deduplicate_trends(trends_dict: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """
    Remove duplicate trends across different sources.
    Keep the one with the highest rank/priority.
    """
    seen = set()

    for source in trends_dict:
        if source == 'timestamp':
            continue

        unique_trends = []
        for trend in trends_dict[source]:
            topic_key = trend['topic'].lower().strip()
            if topic_key not in seen:
                seen.add(topic_key)
                unique_trends.append(trend)

        trends_dict[source] = unique_trends

    return trends_dict


# Example usage
if __name__ == "__main__":
    print("Testing Google Trends Fetcher...\n")

    # Test basic trends
    trends = fetch_google_trends()
    print(f"\nTop 5 Trending Topics:")
    for i, trend in enumerate(trends[:5], 1):
        print(f"{i}. {trend['topic']}")

    # Test category trends
    print(f"\nSports Trends:")
    sports_trends = get_trending_topics_by_category('sports')
    for trend in sports_trends[:3]:
        print(f"  - {trend['topic']}")

    # Test all trends
    print(f"\nFetching all trends...")
    all_trends = fetch_all_trends()

    total = sum(len(v) for k, v in all_trends.items() if k != 'timestamp')
    print(f"\n[OK] Total unique trends found: {total}")
