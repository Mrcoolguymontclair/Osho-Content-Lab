#!/usr/bin/env python3
"""
CHECK TOP TRENDING TOPIC ON GOOGLE
Shows the #1 trending topic right now with traffic data
"""

import requests
import feedparser
from datetime import datetime


def get_top_trend(region='US'):
    """
    Fetch the #1 trending topic on Google right now.

    Args:
        region: Country code (US, GB, etc.)

    Returns: Dict with top trend info
    """
    try:
        # Official Google Trends RSS feed
        url = f'https://trends.google.com/trending/rss?geo={region}'

        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        if response.status_code != 200:
            return {'error': f'RSS feed returned status {response.status_code}'}

        # Parse RSS feed
        feed = feedparser.parse(response.content)

        if not feed.entries:
            return {'error': 'No trends found in RSS feed'}

        # Get #1 trending topic
        top_entry = feed.entries[0]

        title = top_entry.get('title', 'Unknown')
        traffic = top_entry.get('ht_approx_traffic', 'unknown')
        link = top_entry.get('link', '')
        published = top_entry.get('published', '')

        # Try to extract description/context
        description = ''
        if hasattr(top_entry, 'summary'):
            description = top_entry.summary

        return {
            'rank': 1,
            'topic': title,
            'traffic': traffic,
            'link': link,
            'published': published,
            'description': description,
            'region': region,
            'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    except Exception as e:
        return {'error': f'Failed to fetch trends: {str(e)}'}


def main():
    print("=" * 70)
    print("🔥 GOOGLE TRENDS - TOP TRENDING TOPIC RIGHT NOW")
    print("=" * 70)
    print()

    # Fetch top trend
    print("📡 Fetching from Google Trends RSS feed...")
    trend = get_top_trend('US')

    if 'error' in trend:
        print(f"❌ Error: {trend['error']}")
        return

    print()
    print("=" * 70)
    print(f"🏆 #{trend['rank']} TRENDING TOPIC IN {trend['region']}")
    print("=" * 70)
    print()
    print(f"📌 Topic:     {trend['topic']}")
    print(f"🔥 Traffic:   {trend['traffic']}")
    print(f"🕐 Published: {trend['published']}")
    print(f"⏰ Fetched:   {trend['fetched_at']}")
    print()

    if trend.get('description'):
        print("📝 Description:")
        print(f"   {trend['description'][:200]}...")
        print()

    if trend.get('link'):
        print(f"🔗 Link: {trend['link']}")
        print()

    print("=" * 70)
    print()
    print("💡 This is what people are searching for on Google RIGHT NOW!")
    print()


if __name__ == "__main__":
    main()
