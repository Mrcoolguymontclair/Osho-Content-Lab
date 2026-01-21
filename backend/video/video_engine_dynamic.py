#!/usr/bin/env python3
"""
DYNAMIC VIDEO ENGINE
Generates videos from AI plans (any format: comparison, explainer, timeline, etc.)
Unlike video_engine_ranking.py (hardcoded), this adapts to ANY video structure.
"""

import os
import subprocess
import tempfile
import requests
from typing import Dict, List, Optional
import edge_tts
import asyncio

# Pexels API
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# Import music manager
from music_manager import get_music_for_mood, get_default_music_for_video_type, add_music_to_video


async def generate_tts_async(text: str, output_path: str, voice: str = "en-US-AriaNeural"):
    """Generate TTS audio file asynchronously."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_tts(text: str, output_path: str, voice: str = "en-US-AriaNeural"):
    """Generate TTS audio file (sync wrapper)."""
    asyncio.run(generate_tts_async(text, output_path, voice))


def search_pexels_video(query: str, orientation: str = 'portrait') -> Optional[str]:
    """
    Search Pexels for a video clip.

    Args:
        query: Search query
        orientation: 'portrait' for 9:16 Shorts format

    Returns: Video URL or None
    """
    if not PEXELS_API_KEY:
        print("[ERROR] PEXELS_API_KEY not set")
        return None

    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": orientation,
        "per_page": 5
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        if 'videos' in data and len(data['videos']) > 0:
            # Get HD video file
            video_files = data['videos'][0]['video_files']
            hd_file = next((f for f in video_files if f['quality'] == 'hd'), video_files[0])
            return hd_file['link']

        print(f"[WARNING] No videos found for query: {query}")
        return None

    except Exception as e:
        print(f"[ERROR] Pexels search error: {e}")
        return None


def download_video_clip(url: str, output_path: str) -> bool:
    """Download video clip from URL."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True

    except Exception as e:
        print(f"[ERROR] Download error: {e}")
        return False


def create_subtitle_file(segments: List[Dict], output_path: str):
    """
    Create SRT subtitle file from video plan segments.

    Args:
        segments: List of segment dicts with narration and duration
        output_path: Path to save .srt file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        current_time = 0.0

        for i, segment in enumerate(segments, 1):
            narration = segment.get('narration', '')
            duration = segment.get('duration', 5.0)

            start_time = current_time
            end_time = current_time + duration

            # SRT format: HH:MM:SS,mmm
            start_srt = format_srt_time(start_time)
            end_srt = format_srt_time(end_time)

            f.write(f"{i}\n")
            f.write(f"{start_srt} --> {end_srt}\n")
            f.write(f"{narration}\n\n")

            current_time = end_time


def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_voiceover(segments: List[Dict], output_dir: str, voice: str = "en-US-AriaNeural") -> List[str]:
    """
    Generate TTS voiceover files for each segment.

    Args:
        segments: Video plan segments
        output_dir: Directory to save audio files
        voice: TTS voice to use

    Returns: List of audio file paths
    """
    audio_files = []

    for i, segment in enumerate(segments):
        narration = segment.get('narration', '')
        if not narration:
            continue

        audio_path = os.path.join(output_dir, f'segment_{i+1}_audio.mp3')

        print(f"   Generating voiceover for segment {i+1}...")
        generate_tts(narration, audio_path, voice)

        audio_files.append(audio_path)

    return audio_files


def fetch_video_clips(segments: List[Dict], output_dir: str) -> List[str]:
    """
    Download video clips for each segment from Pexels.

    Args:
        segments: Video plan segments with search queries
        output_dir: Directory to save clips

    Returns: List of video file paths
    """
    video_clips = []

    for i, segment in enumerate(segments):
        search_query = segment.get('search_query', 'nature')

        print(f"  [VIDEO] Searching Pexels for: {search_query}")
        video_url = search_pexels_video(search_query)

        if not video_url:
            # Fallback to generic search
            print(f"  [WARNING] Trying fallback search...")
            video_url = search_pexels_video('abstract motion')

        if video_url:
            clip_path = os.path.join(output_dir, f'segment_{i+1}_clip.mp4')
            if download_video_clip(video_url, clip_path):
                video_clips.append(clip_path)
            else:
                video_clips.append(None)
        else:
            video_clips.append(None)

    return video_clips


def process_video_clip(clip_path: str, duration: float, output_path: str) -> bool:
    """
    Process video clip to exact duration and 9:16 format.

    Args:
        clip_path: Input video path
        duration: Target duration in seconds
        output_path: Output processed clip path

    Returns: True if successful
    """
    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', clip_path,
            '-t', str(duration),
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-an',  # No audio
            output_path
        ]

        subprocess.run(cmd, check=True, capture_output=True)
        return True

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] FFmpeg clip processing error: {e.stderr.decode()}")
        return False


def assemble_dynamic_video(
    video_plan: Dict,
    video_clips: List[str],
    audio_files: List[str],
    subtitle_file: str,
    output_path: str,
    music_volume: float = 0.1
) -> bool:
    """
    Assemble final video from clips, audio, and subtitles.

    Args:
        video_plan: Complete video plan from video_planner_ai
        video_clips: List of processed clip paths
        audio_files: List of voiceover audio paths
        subtitle_file: Path to SRT subtitle file
        output_path: Final video output path
        music_volume: Background music volume (0-1)

    Returns: True if successful
    """
    temp_dir = tempfile.mkdtemp()

    try:
        # Step 1: Concatenate video clips
        concat_file = os.path.join(temp_dir, 'concat_list.txt')
        with open(concat_file, 'w') as f:
            for clip in video_clips:
                if clip and os.path.exists(clip):
                    f.write(f"file '{clip}'\n")

        concatenated_video = os.path.join(temp_dir, 'concatenated.mp4')

        concat_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            concatenated_video
        ]

        subprocess.run(concat_cmd, check=True, capture_output=True)

        # Step 2: Concatenate audio files
        audio_concat_file = os.path.join(temp_dir, 'audio_concat_list.txt')
        with open(audio_concat_file, 'w') as f:
            for audio in audio_files:
                if audio and os.path.exists(audio):
                    f.write(f"file '{audio}'\n")

        concatenated_audio = os.path.join(temp_dir, 'concatenated_audio.mp3')

        audio_concat_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', audio_concat_file,
            '-c', 'copy',
            concatenated_audio
        ]

        subprocess.run(audio_concat_cmd, check=True, capture_output=True)

        # Step 3: Add subtitles
        subtitle_style = (
            "Alignment=10,"
            "FontName=Arial Bold,"
            "FontSize=56,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "BorderStyle=3,"
            "Outline=4,"
            "Shadow=3,"
            "MarginV=320,"
            "BackColour=&HA0000000"
        )

        # Escape subtitle path for FFmpeg
        subs_filter = subtitle_file.replace('\\', '/').replace(':', '\\\\:')

        final_cmd = [
            'ffmpeg', '-y',
            '-i', concatenated_video,
            '-i', concatenated_audio,
            '-vf', f"subtitles='{subs_filter}':force_style='{subtitle_style}'",
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            output_path
        ]

        subprocess.run(final_cmd, check=True, capture_output=True)

        return True

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Video assembly error: {e.stderr.decode()}")
        return False

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False


def generate_video_from_plan(video_plan: Dict, output_path: str, voice: str = "en-US-AriaNeural") -> bool:
    """
    Generate complete video from AI video plan.

    Args:
        video_plan: Complete plan from video_planner_ai.plan_video_from_trend()
        output_path: Where to save final video
        voice: TTS voice to use

    Returns: True if successful
    """
    print(f"\n[VIDEO] Generating {video_plan['video_type'].upper()} video...")
    print(f"Title: {video_plan['title']}")
    print(f"Clips: {video_plan['clip_count']}")

    temp_dir = tempfile.mkdtemp()

    try:
        segments = video_plan['segments']

        # Step 1: Generate voiceovers
        print("\n Generating voiceovers...")
        audio_files = generate_voiceover(segments, temp_dir, voice)

        # Step 2: Fetch video clips
        print("\n[CAMERA] Fetching video clips...")
        raw_clips = fetch_video_clips(segments, temp_dir)

        # Step 3: Process clips to exact duration
        print("\n Processing clips...")
        processed_clips = []
        for i, (raw_clip, segment) in enumerate(zip(raw_clips, segments)):
            if raw_clip:
                processed_path = os.path.join(temp_dir, f'processed_{i+1}.mp4')
                duration = segment['duration']

                if process_video_clip(raw_clip, duration, processed_path):
                    processed_clips.append(processed_path)
                else:
                    print(f"  [WARNING] Failed to process clip {i+1}")
                    processed_clips.append(None)
            else:
                processed_clips.append(None)

        # Step 4: Create subtitle file
        print("\n[NOTE] Creating subtitles...")
        subtitle_file = os.path.join(temp_dir, 'subtitles.srt')
        create_subtitle_file(segments, subtitle_file)

        # Step 5: Assemble final video (without music first)
        print("\n Assembling final video...")
        temp_video = os.path.join(temp_dir, 'video_no_music.mp4')

        success = assemble_dynamic_video(
            video_plan,
            processed_clips,
            audio_files,
            subtitle_file,
            temp_video
        )

        if not success:
            print("\n[ERROR] Video assembly failed")
            return False

        # Step 6: Add background music
        print("\n[MUSIC] Adding background music...")
        video_type = video_plan.get('video_type', 'standard')
        mood_tags = get_default_music_for_video_type(video_type)
        music_path = get_music_for_mood(mood_tags)

        if music_path:
            print(f"  Selected: {os.path.basename(music_path)}")
            music_success = add_music_to_video(temp_video, music_path, output_path, music_volume=0.12)

            if music_success:
                print(f"\n[OK] Video generated with music: {output_path}")
                return True
            else:
                print("\n[WARNING] Music failed, using video without music")
                # Copy temp video to output as fallback
                import shutil
                shutil.copy(temp_video, output_path)
                return True
        else:
            print("\n[WARNING] No music available, continuing without music")
            # Copy temp video to output
            import shutil
            shutil.copy(temp_video, output_path)
            print(f"\n[OK] Video generated: {output_path}")
            return True

    except Exception as e:
        print(f"\n[ERROR] Video generation error: {e}")
        return False


# Example usage
if __name__ == "__main__":
    # Test with sample video plan
    sample_plan = {
        "video_type": "explainer",
        "clip_count": 5,
        "total_duration": 45,
        "title": "What is Machine Learning Explained",
        "hook": "Let's break down machine learning in simple terms",
        "music_style": "calm",
        "tone": "educational",
        "pacing": "medium",
        "segments": [
            {
                "segment_number": 1,
                "duration": 9,
                "visual_description": "Computer with code on screen",
                "narration": "Machine learning is teaching computers to learn from data",
                "search_query": "computer programming code",
                "text_overlay": None
            },
            {
                "segment_number": 2,
                "duration": 9,
                "visual_description": "Brain and circuits merging",
                "narration": "Instead of programming every rule, we let the system find patterns",
                "search_query": "artificial intelligence brain",
                "text_overlay": None
            },
            {
                "segment_number": 3,
                "duration": 9,
                "visual_description": "Data visualization charts",
                "narration": "It analyzes massive amounts of data to make predictions",
                "search_query": "data visualization graphs",
                "text_overlay": None
            },
            {
                "segment_number": 4,
                "duration": 9,
                "visual_description": "Examples of ML in action",
                "narration": "That's how Netflix recommends shows or Spotify finds your music",
                "search_query": "smartphone apps technology",
                "text_overlay": None
            },
            {
                "segment_number": 5,
                "duration": 9,
                "visual_description": "Future tech visualization",
                "narration": "And it's getting smarter every single day",
                "search_query": "futuristic technology",
                "text_overlay": None
            }
        ]
    }

    output_file = "/tmp/test_dynamic_video.mp4"

    print("Testing Dynamic Video Engine...\n")
    success = generate_video_from_plan(sample_plan, output_file)

    if success:
        print(f"\n[OK] TEST PASSED - Video created at {output_file}")
    else:
        print("\n[ERROR] TEST FAILED")
