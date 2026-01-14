#!/usr/bin/env python3
"""
MUSIC MANAGER
Handles background music selection and mixing for videos.
Matches music to video mood/type automatically.
"""

import os
import json
import random
import subprocess
from typing import Dict, List, Optional, Tuple


MUSIC_DIR = "music"
MUSIC_LIBRARY_FILE = os.path.join(MUSIC_DIR, "music_library.json")


def load_music_library() -> Dict:
    """Load music library from JSON file."""
    if not os.path.exists(MUSIC_LIBRARY_FILE):
        return {"music_files": []}

    with open(MUSIC_LIBRARY_FILE, 'r') as f:
        return json.load(f)


def get_music_for_mood(mood_tags: List[str] = None) -> Optional[str]:
    """
    Get music file path that matches the mood/style.

    Args:
        mood_tags: List of mood keywords (e.g., ["upbeat", "energetic"])

    Returns: Path to music file or None
    """
    library = load_music_library()
    music_files = library.get('music_files', [])

    if not music_files:
        print("⚠️ No music files in library")
        return None

    if not mood_tags:
        # Random selection if no mood specified
        music = random.choice(music_files)
        music_path = os.path.join(MUSIC_DIR, music['filename'])

        if os.path.exists(music_path):
            return music_path
        else:
            print(f"⚠️ Music file not found: {music_path}")
            return None

    # Score each music file by tag matches
    scored_music = []

    for music in music_files:
        music_tags = [tag.lower() for tag in music.get('tags', [])]
        mood_tags_lower = [tag.lower() for tag in mood_tags]

        # Calculate match score
        matches = sum(1 for tag in mood_tags_lower if tag in music_tags)

        if matches > 0:
            scored_music.append((matches, music))

    if not scored_music:
        # No matches, return random
        music = random.choice(music_files)
    else:
        # Sort by score descending, pick best
        scored_music.sort(key=lambda x: x[0], reverse=True)
        music = scored_music[0][1]

    music_path = os.path.join(MUSIC_DIR, music['filename'])

    if os.path.exists(music_path):
        print(f"  🎵 Selected music: {music['filename']}")
        return music_path
    else:
        print(f"⚠️ Music file not found: {music_path}")
        # Try to find any working music file
        for m in music_files:
            fallback_path = os.path.join(MUSIC_DIR, m['filename'])
            if os.path.exists(fallback_path):
                print(f"  🎵 Using fallback: {m['filename']}")
                return fallback_path

    return None


def get_default_music_for_video_type(video_type: str) -> List[str]:
    """
    Get default mood tags for different video types.

    Args:
        video_type: "ranking", "comparison", "explainer", "highlights", etc.

    Returns: List of mood tags
    """
    mood_map = {
        'ranking': ['energetic', 'upbeat', 'powerful'],
        'comparison': ['electronic', 'modern', 'upbeat'],
        'explainer': ['chill', 'relaxing', 'beautiful'],
        'highlights': ['energetic', 'powerful', 'dramatic'],
        'timeline': ['uplifting', 'hopeful', 'beautiful'],
        'prediction': ['dramatic', 'intense', 'electronic'],
        'standard': ['upbeat', 'happy', 'catchy']
    }

    return mood_map.get(video_type.lower(), mood_map['standard'])


def trim_music_to_duration(music_path: str, duration: float, output_path: str) -> bool:
    """
    Trim music file to exact duration with fade in/out.

    Args:
        music_path: Input music file
        duration: Target duration in seconds
        output_path: Output trimmed music file

    Returns: True if successful
    """
    try:
        # Trim with fade in (1s) and fade out (2s)
        cmd = [
            'ffmpeg', '-y',
            '-i', music_path,
            '-t', str(duration),
            '-af', f'afade=t=in:st=0:d=1,afade=t=out:st={duration-2}:d=2',
            '-c:a', 'aac',
            '-b:a', '128k',
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=30)

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Music trim error: {e}")
        return False


def mix_audio_with_music(voiceover_path: str, music_path: str, output_path: str,
                         music_volume: float = 0.15) -> bool:
    """
    Mix voiceover with background music.

    Args:
        voiceover_path: Path to voiceover audio
        music_path: Path to background music
        output_path: Path for mixed output
        music_volume: Music volume level (0.0-1.0, default 0.15 = -16dB)

    Returns: True if successful
    """
    try:
        # Mix voiceover + music with music at lower volume
        cmd = [
            'ffmpeg', '-y',
            '-i', voiceover_path,
            '-i', music_path,
            '-filter_complex',
            f'[1:a]volume={music_volume}[music];[0:a][music]amix=inputs=2:duration=shortest:normalize=0',
            '-c:a', 'aac',
            '-b:a', '192k',
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=60)

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Audio mixing error: {e}")
        return False


def add_music_to_video(video_path: str, music_path: str, output_path: str,
                       music_volume: float = 0.15) -> bool:
    """
    Add background music to video (replaces audio track with voiceover + music mix).

    Args:
        video_path: Input video with voiceover
        music_path: Background music file
        output_path: Output video with music
        music_volume: Music volume level (0.0-1.0)

    Returns: True if successful
    """
    try:
        # Get video duration
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        video_duration = float(probe_result.stdout.strip())

        # Trim music to video duration
        import tempfile
        temp_music = tempfile.NamedTemporaryFile(suffix='.aac', delete=False).name

        if not trim_music_to_duration(music_path, video_duration, temp_music):
            print("⚠️ Failed to trim music, continuing without music")
            return False

        # Mix video audio with music
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', temp_music,
            '-filter_complex',
            f'[0:a]volume=1.0[voice];[1:a]volume={music_volume}[music];[voice][music]amix=inputs=2:duration=shortest',
            '-c:v', 'copy',  # Don't re-encode video
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=120)

        # Cleanup temp file
        try:
            os.unlink(temp_music)
        except:
            pass

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Add music error: {e}")
        return False


# Example usage and testing
if __name__ == "__main__":
    print("Testing Music Manager...\n")

    # Test 1: Load library
    library = load_music_library()
    print(f"✅ Loaded {len(library.get('music_files', []))} music files\n")

    # Test 2: Get music for different moods
    test_moods = [
        (['energetic', 'upbeat'], 'Ranking video'),
        (['chill', 'relaxing'], 'Explainer video'),
        (['dramatic', 'powerful'], 'Highlights video'),
        (None, 'Random selection')
    ]

    for mood_tags, description in test_moods:
        print(f"Test: {description}")
        music_path = get_music_for_mood(mood_tags)
        if music_path:
            print(f"  ✅ Found: {os.path.basename(music_path)}")
        else:
            print(f"  ❌ No music found")
        print()

    # Test 3: Get default moods for video types
    print("Default moods for video types:")
    for video_type in ['ranking', 'comparison', 'explainer', 'highlights']:
        moods = get_default_music_for_video_type(video_type)
        print(f"  {video_type}: {', '.join(moods)}")

    print("\n✅ All tests complete!")
