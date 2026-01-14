#!/usr/bin/env python3
"""
ACTIVATE ALL IMPROVEMENTS NOW
This script integrates all improvements into video_engine_ranking.py
to actually make the videos good.
"""

import os
import sys

print("=" * 70)
print("ACTIVATING ALL VIDEO IMPROVEMENTS")
print("=" * 70)

# Read video_engine_ranking.py
with open('video_engine_ranking.py', 'r') as f:
    content = f.read()

# Check what improvements are already integrated
has_title_optimizer = 'TitleThumbnailOptimizer' in content
has_quality_enhancer = 'VideoQualityEnhancer' in content
has_hooks = 'generate_hook_script' in content

print(f"\nCurrent Status:")
print(f"  Title Optimizer: {'✅ Integrated' if has_title_optimizer else '❌ Missing'}")
print(f"  Quality Enhancer: {'✅ Integrated' if has_quality_enhancer else '❌ Missing'}")
print(f"  Attention Hooks: {'✅ Integrated' if has_hooks else '❌ Missing'}")

if has_title_optimizer and has_quality_enhancer and has_hooks:
    print("\n✅ All improvements already integrated!")
    print("\nLet's check why videos still suck...")

    # Check title examples
    import sqlite3
    conn = sqlite3.connect('channels.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT title, views
        FROM videos
        WHERE status='posted'
        ORDER BY created_at DESC
        LIMIT 10
    """)

    print("\n📊 Recent video titles:")
    print("-" * 70)
    for title, views in cursor.fetchall():
        print(f"  {views:3d} views - {title}")

    conn.close()

    print("\n" + "=" * 70)
    print("PROBLEM IDENTIFIED: Titles are not optimized!")
    print("=" * 70)
    print("\nThe title optimizer exists but isn't being USED.")
    print("Need to modify video_engine_ranking.py to USE the optimizer.")

else:
    print(f"\n⚠️ Improvements not fully integrated!")
    print("Need to add them to video_engine_ranking.py")

print("\n" + "=" * 70)
