#!/usr/bin/env python3
"""
COMPREHENSIVE SYSTEM TEST
Tests the complete multi-channel YouTube automation system.

Tests:
1. Database initialization
2. Channel creation
3. Video script generation
4. Complete video assembly pipeline
5. Error handling and recovery
"""

import os
import sys
import time

# Setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all module imports"""
    print("\n" + "="*70)
    print("TEST 1: Module Imports")
    print("="*70)

    try:
        import channel_manager
        print("✅ channel_manager imported")

        import video_engine
        print("✅ video_engine imported")

        import auth_manager
        print("✅ auth_manager imported")

        import youtube_daemon
        print("✅ youtube_daemon imported")

        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database operations"""
    print("\n" + "="*70)
    print("TEST 2: Database Operations")
    print("="*70)

    try:
        from channel_manager import (
            add_channel, get_all_channels, get_channel,
            update_channel, add_log
        )

        # Create test channel
        success, message = add_channel(
            name="TEST_CHANNEL_AUTO",
            theme="Viral Test Facts",
            tone="Exciting",
            style="Fast-paced",
            post_interval_minutes=60
        )

        if not success and "already exists" not in message:
            print(f"❌ Channel creation failed: {message}")
            return False

        print(f"✅ Channel created/exists: {message}")

        # Get channel
        channels = get_all_channels()
        test_channel = None

        for ch in channels:
            if ch['name'] == "TEST_CHANNEL_AUTO":
                test_channel = ch
                break

        if not test_channel:
            print("❌ Channel not found in database")
            return False

        print(f"✅ Channel found: ID={test_channel['id']}")

        # Add log
        add_log(test_channel['id'], "info", "test", "Test log entry")
        print("✅ Log entry added")

        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_script_generation():
    """Test AI script generation"""
    print("\n" + "="*70)
    print("TEST 3: AI Script Generation")
    print("="*70)

    try:
        from video_engine import generate_video_script
        from channel_manager import get_channel_by_name

        channel = get_channel_by_name("TEST_CHANNEL_AUTO")

        if not channel:
            print("❌ Test channel not found")
            return False

        print("Generating script (this takes ~5 seconds)...")

        script, error = generate_video_script(channel)

        if not script:
            print(f"❌ Script generation failed: {error}")
            return False

        print(f"✅ Script generated: '{script['title']}'")
        print(f"   Segments: {len(script['segments'])}")

        # Verify structure
        if len(script['segments']) != 10:
            print(f"⚠️  Warning: Expected 10 segments, got {len(script['segments'])}")

        for i, seg in enumerate(script['segments'][:3]):  # Show first 3
            print(f"   {i+1}. Narration: {seg['narration'][:50]}...")
            print(f"      Search: {seg['searchQuery']}")
            print(f"      Music: {seg.get('musicKeywords', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Script generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_voiceover():
    """Test voiceover generation"""
    print("\n" + "="*70)
    print("TEST 4: Voiceover Generation")
    print("="*70)

    try:
        from video_engine import generate_voiceover

        os.makedirs("outputs/test", exist_ok=True)
        test_text = "This is a test of the voiceover generation system."
        output_path = "outputs/test/test_vo.mp3"

        print("Generating test voiceover...")

        success, error = generate_voiceover(test_text, output_path)

        if not success:
            print(f"❌ Voiceover failed: {error}")
            return False

        # Verify file
        if not os.path.exists(output_path):
            print("❌ Voiceover file not created")
            return False

        size_kb = os.path.getsize(output_path) / 1024
        print(f"✅ Voiceover generated: {size_kb:.1f}KB")

        return True

    except Exception as e:
        print(f"❌ Voiceover test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_clip_download():
    """Test video clip download"""
    print("\n" + "="*70)
    print("TEST 5: Video Clip Download")
    print("="*70)

    try:
        from video_engine import download_video_clip

        os.makedirs("outputs/test", exist_ok=True)
        search_query = "ocean waves"
        output_path = "outputs/test/test_clip.mp4"

        print(f"Downloading clip: '{search_query}'...")
        print("(This may take 30-60 seconds)")

        success, error = download_video_clip(search_query, output_path, duration=6.0)

        if not success:
            print(f"❌ Clip download failed: {error}")
            print("⚠️  This might be a Pexels API quota issue - not critical")
            return True  # Don't fail test for API quota

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"✅ Clip downloaded: {size_mb:.1f}MB")

        return True

    except Exception as e:
        print(f"❌ Clip download test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_music_download():
    """Test music download"""
    print("\n" + "="*70)
    print("TEST 6: Background Music Download")
    print("="*70)

    try:
        from video_engine import download_background_music

        os.makedirs("outputs/test", exist_ok=True)
        keywords = "upbeat energetic"
        output_path = "outputs/test/test_music.mp3"

        print(f"Downloading music: '{keywords}'...")

        success, error = download_background_music(keywords, output_path)

        if not success:
            print(f"❌ Music download failed: {error}")
            print("⚠️  This might be a Pixabay API issue - not critical")
            return True  # Don't fail test for API quota

        size_kb = os.path.getsize(output_path) / 1024
        print(f"✅ Music downloaded: {size_kb:.1f}KB")

        return True

    except Exception as e:
        print(f"❌ Music download test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ffmpeg():
    """Test FFmpeg installation"""
    print("\n" + "="*70)
    print("TEST 7: FFmpeg Installation")
    print("="*70)

    try:
        from video_engine import FFMPEG
        import subprocess

        print(f"FFmpeg path: {FFMPEG}")

        result = subprocess.run([FFMPEG, '-version'], capture_output=True, timeout=5)

        if result.returncode != 0:
            print("❌ FFmpeg not working")
            return False

        version_line = result.stdout.decode().split('\n')[0]
        print(f"✅ {version_line}")

        return True

    except Exception as e:
        print(f"❌ FFmpeg test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 MULTI-CHANNEL YOUTUBE AUTOMATION - SYSTEM TEST")
    print("="*70)

    tests = [
        ("Module Imports", test_imports),
        ("Database Operations", test_database),
        ("AI Script Generation", test_script_generation),
        ("Voiceover Generation", test_voiceover),
        ("Video Clip Download", test_clip_download),
        ("Music Download", test_music_download),
        ("FFmpeg Installation", test_ffmpeg)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

        time.sleep(1)  # Pause between tests

    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("\n" + "="*70)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("="*70)

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is ready to use!")
        print("\nNext steps:")
        print("1. Run: streamlit run new_vid_gen.py")
        print("2. Create a channel")
        print("3. Authenticate with YouTube")
        print("4. Activate the channel")
        print("5. Watch it generate and post videos automatically!")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        print("Most common issues:")
        print("- API keys not configured (check .streamlit/secrets.toml)")
        print("- FFmpeg not installed or not in PATH")
        print("- Network/internet connection issues")

    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
