#!/usr/bin/env python3
"""Show trending topics without AI analysis (no API calls)"""

from google_trends_fetcher import fetch_all_trends
from datetime import datetime

print("=" * 70)
print("🔥 CURRENT TRENDING TOPICS (No AI Analysis)")
print("=" * 70)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)
print()

# Fetch trends
all_trends = fetch_all_trends(region='US')

# Combine
combined = []
for source, trends in all_trends.items():
    if source != 'timestamp' and isinstance(trends, list):
        combined.extend(trends)

print(f"✅ Found {len(combined)} trends\n")
print("TOP 15 TRENDING TOPICS:")
print("-" * 70)

for idx, trend in enumerate(combined[:15], 1):
    topic = trend['topic']
    source = trend.get('source', 'unknown')
    category = trend.get('category', 'unknown')
    volume = trend.get('search_volume', 'unknown')
    
    print(f"{idx:2}. {topic}")
    print(f"    📊 Volume: {volume.upper():12} | 📁 Category: {category}")
    print(f"    🔍 Source: {source}")
    print()

print("=" * 70)
print("\n💡 Note: Google Trends API is currently rate limited.")
print("   These are fallback trends for testing.")
print("   Real Google Trends will be fetched when API resets.\n")

# Check database for previously approved trends
print("=" * 70)
print("📊 TRENDS IN DATABASE (Previously Approved)")
print("=" * 70)

try:
    import sqlite3
    conn = sqlite3.connect('channels.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT topic, recommended_format, confidence, urgency, video_generated
        FROM trends
        WHERE is_approved = 1
        ORDER BY urgency DESC, confidence DESC
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        print(f"\n✅ {len(rows)} approved trends ready for videos:\n")
        for idx, row in enumerate(rows, 1):
            status = "✅ USED" if row['video_generated'] else "⏳ PENDING"
            print(f"{idx}. {row['topic']}")
            print(f"   Format: {row['recommended_format'].upper():12} | Confidence: {row['confidence']}%")
            print(f"   Urgency: {row['urgency']:12} | Status: {status}")
            print()
    else:
        print("\n⚠️ No approved trends in database yet")
        print("   (Groq API is out of tokens - resets in ~4 hours)\n")
    
    conn.close()
    
except Exception as e:
    print(f"\n❌ Database error: {e}\n")

print("=" * 70)
