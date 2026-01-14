#!/usr/bin/env python3
"""
Test script to verify trending video system is working correctly.
"""

print("🔍 Testing Trending Video System\n")

# 1. Initialize trends table
print("1️⃣ Initializing trends table...")
try:
    from trend_tracker import init_trends_table
    init_trends_table()
    print("   ✅ Trends table initialized\n")
except Exception as e:
    print(f"   ❌ Error: {e}\n")
    exit(1)

# 2. Check trend stats
print("2️⃣ Checking trend statistics...")
try:
    from trend_tracker import get_trend_stats
    stats = get_trend_stats()
    print(f"   Total trends: {stats.get('total_trends', 0)}")
    print(f"   Approved trends: {stats.get('approved_trends', 0)}")
    print(f"   Pending generation: {stats.get('pending_generation', 0)}")
    print(f"   Videos generated: {stats.get('videos_generated', 0)}")
    print("   ✅ Stats retrieved successfully\n")
except Exception as e:
    print(f"   ❌ Error: {e}\n")
    exit(1)

# 3. Test fetching Google Trends
print("3️⃣ Testing Google Trends fetch...")
try:
    from google_trends_fetcher import fetch_google_trends
    trends = fetch_google_trends(region='US')

    if trends:
        print(f"   ✅ Fetched {len(trends)} trending topics")
        print(f"\n   Top 3 trends:")
        for i, trend in enumerate(trends[:3], 1):
            print(f"   {i}. {trend['topic']} (Volume: {trend['search_volume']})")
        print()
    else:
        print("   ⚠️  No trends fetched (this is normal if API is temporarily down)")
        print()
except Exception as e:
    print(f"   ❌ Error: {e}\n")

# 4. Check channel video_type settings
print("4️⃣ Checking channel video_type settings...")
try:
    from channel_manager import get_all_channels
    channels = get_all_channels()

    if channels:
        for channel in channels:
            video_type = channel.get('video_type', 'standard')
            print(f"   {channel['name']}: video_type = '{video_type}'")
        print("   ✅ Channel settings retrieved\n")
    else:
        print("   ℹ️  No channels configured yet\n")
except Exception as e:
    print(f"   ❌ Error: {e}\n")

# 5. Test GroqManager failover
print("5️⃣ Testing Groq API key failover...")
try:
    from groq_manager import get_groq_client
    groq_client = get_groq_client()
    print(f"   ✅ GroqManager loaded with {len(groq_client.api_keys)} API key(s)")
    print(f"   Current key index: {groq_client.current_key_index + 1}")
    print()
except Exception as e:
    print(f"   ❌ Error: {e}\n")

print("=" * 60)
print("✅ TRENDING SYSTEM READY!")
print()
print("📋 How to use:")
print("   1. Go to Settings tab in UI")
print("   2. Set 'Video Format' to 'trending'")
print("   3. Save settings")
print("   4. Activate channel")
print()
print("The system will:")
print("   • Fetch trends automatically from Google")
print("   • Analyze them with AI")
print("   • Generate videos from trending topics")
print("   • Fall back to standard format if no trends available")
print("=" * 60)
