#!/usr/bin/env python3
"""
QUICK TRENDS TEST
Shows current trending topics with AI analysis
"""

import sys
from google_trends_fetcher import fetch_all_trends
from trend_analyzer import analyze_trend_for_video
from datetime import datetime

def test_trends(channel_theme="General content"):
    """
    Fetch and display current trending topics with AI analysis.

    Args:
        channel_theme: Your channel's theme for relevance matching
    """
    print("=" * 70)
    print("🔥 TRENDING TOPICS TEST")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Channel Theme: {channel_theme}")
    print("=" * 70)
    print()

    # Fetch all trends
    print("📡 Fetching trending topics...\n")
    all_trends = fetch_all_trends(region='US')

    # Combine all trends
    combined_trends = []
    for source, trends in all_trends.items():
        if source != 'timestamp' and isinstance(trends, list):
            combined_trends.extend(trends)

    if not combined_trends:
        print("❌ No trends found\n")
        return

    print(f"✅ Found {len(combined_trends)} total trends\n")
    print("=" * 70)
    print("TOP TRENDING TOPICS")
    print("=" * 70)
    print()

    # Display top 15 trends with analysis
    for idx, trend in enumerate(combined_trends[:15], 1):
        topic = trend['topic']
        source = trend.get('source', 'unknown')
        category = trend.get('category', 'unknown')
        search_volume = trend.get('search_volume', 'unknown')

        print(f"{idx}. {topic}")
        print(f"   Source: {source} | Category: {category} | Volume: {search_volume}")

        # AI Analysis
        try:
            is_worthy, analysis = analyze_trend_for_video(trend, channel_theme)

            if is_worthy:
                confidence = analysis.get('confidence', 0)
                video_format = analysis.get('recommended_format', 'unknown')
                visual_potential = analysis.get('visual_potential', 'unknown')
                audience_interest = analysis.get('audience_interest', 'unknown')
                urgency = analysis.get('urgency', 'unknown')

                print(f"   ✅ APPROVED (AI Confidence: {confidence}%)")
                print(f"   📹 Format: {video_format.upper()}")
                print(f"   👁️  Visual: {visual_potential} | 👥 Interest: {audience_interest} | ⏰ Urgency: {urgency}")

                angle = analysis.get('suggested_video_angle', '')
                if angle:
                    print(f"   💡 Angle: {angle}")
            else:
                print(f"   ❌ REJECTED")
                if 'rejection_reason' in analysis:
                    print(f"   Reason: {analysis['rejection_reason']}")

        except Exception as e:
            print(f"   ⚠️ Analysis failed: {str(e)[:80]}")

        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # Count approved vs rejected
    approved_count = 0
    formats = {}

    for trend in combined_trends[:15]:
        try:
            is_worthy, analysis = analyze_trend_for_video(trend, channel_theme)
            if is_worthy:
                approved_count += 1
                video_format = analysis.get('recommended_format', 'unknown')
                formats[video_format] = formats.get(video_format, 0) + 1
        except:
            pass

    print(f"Total Trends Analyzed: 15")
    print(f"✅ Approved: {approved_count} ({approved_count/15*100:.1f}%)")
    print(f"❌ Rejected: {15-approved_count} ({(15-approved_count)/15*100:.1f}%)")
    print()

    if formats:
        print("Recommended Formats:")
        for fmt, count in sorted(formats.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {fmt}: {count} videos")

    print()
    print("=" * 70)
    print()


if __name__ == "__main__":
    # Get channel theme from command line or use default
    if len(sys.argv) > 1:
        theme = " ".join(sys.argv[1:])
    else:
        # Try to get from database
        try:
            import sqlite3
            conn = sqlite3.connect('channels.db')
            cursor = conn.cursor()
            cursor.execute("SELECT theme FROM channels WHERE is_active = 1 LIMIT 1")
            result = cursor.fetchone()
            conn.close()

            if result:
                theme = result[0]
                print(f"📺 Using theme from active channel: '{theme}'")
                print()
            else:
                theme = "General content"
        except:
            theme = "General content"

    test_trends(theme)

    print("💡 TIP: Run with your channel theme:")
    print(f"   python3 test_trends.py \"Your Channel Theme\"")
    print()
    print("   Examples:")
    print("   python3 test_trends.py \"Sports highlights\"")
    print("   python3 test_trends.py \"Technology news\"")
    print("   python3 test_trends.py \"Entertainment updates\"")
    print()
