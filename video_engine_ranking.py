#!/usr/bin/env python3
"""
RANKING VIDEO GENERATION ENGINE
Generates countdown-style ranking videos (5→1) with persistent overlays.
Separate from standard video_engine.py
"""

import os
import subprocess
import time
import shutil
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Import shared utilities
from video_engine import (
    FFMPEG, FFPROBE, groq_client, PEXELS_API_KEY,
    log_to_db, log_dev, download_video_clip,
    generate_voiceover, download_background_music
)

# ==============================================================================
# Ranking Script Generation
# ==============================================================================

def generate_ranking_script(
    theme: str,
    tone: str = "Exciting",
    style: str = "Fast-paced",
    channel_id: int = 0
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Generate ranking video script using Groq AI.

    Returns: (script_dict, error_message)
    script_dict contains: title, adjective, ranked_items[{rank, title, narration, searchQuery}]
    """
    if not groq_client:
        return None, "Groq API key not configured"

    try:
        log_to_db(channel_id, "info", "script", "Generating ranking script...")

        prompt = f"""Generate a viral YouTube Shorts RANKING video script.

THEME: {theme}
TONE: {tone}
STYLE: {style}

Your task:
1. Create a catchy ranking title: "Ranking [superlative] [category]"
   Examples: "Ranking Craziest Sports Moments", "Ranking Most Unbelievable Facts", "Ranking Best Hidden Gems"

2. Choose an adjective that scales (crazy→craziest, amazing→most amazing, good→best)

3. Generate 5 DISTINCT items ranked from LEAST to MOST [adjective]:
   - Rank 5: Decent but not the best (baseline)
   - Rank 4: Good, noticeably better
   - Rank 3: Really good, impressive
   - Rank 2: Excellent, almost the best
   - Rank 1: THE ABSOLUTE BEST, most [adjective] of all

4. For each item provide:
   - title: Short punchy descriptor (2-4 words, like "Mind Blown", "No Way!", "Pure Chaos")
   - narration: 1-2 sentences explaining WHY it's at this rank (under 100 characters)
   - searchQuery: Specific Pexels search (concrete visuals, not generic stock)

CRITICAL RULES:
- Items must CLEARLY progress in quality/intensity (5 is okay, 1 is INCREDIBLE)
- Make #1 unmistakably THE BEST
- Narration must be CONCISE (under 100 chars)
- Search queries = SPECIFIC moments/scenes (not "person smiling")
- Duration: Each clip is exactly 12 seconds (total 60s)

Output ONLY valid JSON (no markdown, no extra text):
{{
  "title": "Ranking [superlative] [category]",
  "adjective": "crazy/amazing/good/etc",
  "theme": "{theme}",
  "ranked_items": [
    {{
      "rank": 5,
      "title": "Getting Started",
      "narration": "This is where it begins but trust me it gets way better",
      "searchQuery": "specific moment or scene",
      "duration": 12
    }},
    {{
      "rank": 4,
      "title": "Now We're Talking",
      "narration": "Things are heating up with this one",
      "searchQuery": "another specific scene",
      "duration": 12
    }},
    {{
      "rank": 3,
      "title": "Getting Serious",
      "narration": "This is where things get really interesting",
      "searchQuery": "specific action scene",
      "duration": 12
    }},
    {{
      "rank": 2,
      "title": "Almost There",
      "narration": "You thought that was good wait for number one",
      "searchQuery": "intense moment",
      "duration": 12
    }},
    {{
      "rank": 1,
      "title": "The Ultimate",
      "narration": "This is it the absolute most [adjective] thing you will ever see",
      "searchQuery": "most dramatic scene",
      "duration": 12
    }}
  ]
}}"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=1500
        )

        response_text = response.choices[0].message.content.strip()

        # Remove markdown if present
        if response_text.startswith("```"):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])

        script = json.loads(response_text)

        # Validate structure
        if not script.get('title') or not script.get('ranked_items'):
            raise Exception("Invalid script structure")

        if len(script['ranked_items']) != 5:
            raise Exception(f"Expected 5 items, got {len(script['ranked_items'])}")

        log_to_db(channel_id, "info", "script", f"Generated: {script['title']}")

        return script, None

    except json.JSONDecodeError as e:
        error_msg = f"JSON parse error: {str(e)}"
        log_to_db(channel_id, "error", "script", error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Script generation failed: {str(e)}"
        log_to_db(channel_id, "error", "script", error_msg)
        return None, error_msg


# ==============================================================================
# Ranking Video Assembly with Overlays
# ==============================================================================

def create_ranking_overlay(
    title: str,
    ranked_items: List[Dict],
    current_rank: int,
    output_path: str,
    width: int = 1080,
    height: int = 1920
) -> bool:
    """
    Create overlay image with title bar and ranking sidebar.

    Args:
        title: Video title (e.g., "Ranking Craziest Moments")
        ranked_items: List of all 5 items with rank and title
        current_rank: Which rank is currently playing (1-5)
        output_path: Where to save overlay image

    Returns: True if successful
    """
    try:
        # Create filter complex for drawtext overlays
        filters = []

        # Title bar at top (semi-transparent background)
        title_text = title.replace("'", "'\\\\\\''")  # Escape quotes for FFmpeg
        filters.append(
            f"drawbox=x=0:y=0:w={width}:h=150:color=black@0.7:t=fill,"
            f"drawtext=text='{title_text}':fontfile=/System/Library/Fonts/Supplemental/Arial Bold.ttf:"
            f"fontsize=48:fontcolor=white:x=(w-text_w)/2:y=50"
        )

        # Ranking sidebar on left
        sidebar_x = 20
        sidebar_start_y = 400
        item_height = 200

        for item in ranked_items:
            rank = item['rank']
            item_title = item['title'].replace("'", "'\\\\\\''")
            y_pos = sidebar_start_y + (rank - 1) * item_height

            # Highlight if this is the current rank
            if rank == current_rank:
                # Yellow highlight box
                filters.append(
                    f"drawbox=x={sidebar_x-10}:y={y_pos-10}:w=320:h=80:"
                    f"color=yellow@0.4:t=fill"
                )

            # Rank number and title
            filters.append(
                f"drawtext=text='{rank}':fontfile=/System/Library/Fonts/Supplemental/Arial Bold.ttf:"
                f"fontsize=56:fontcolor=white:x={sidebar_x}:y={y_pos},"
                f"drawtext=text='{item_title}':fontfile=/System/Library/Fonts/Supplemental/Arial.ttf:"
                f"fontsize=32:fontcolor=white:x={sidebar_x+80}:y={y_pos+10}"
            )

        # Create blank video frame and apply overlays
        filter_string = ",".join(filters)

        result = subprocess.run([
            FFMPEG, '-y',
            '-f', 'lavfi',
            '-i', f'color=c=black@0:s={width}x{height}:d=0.1',
            '-vf', filter_string,
            '-frames:v', '1',
            output_path
        ], capture_output=True, timeout=30)

        if result.returncode != 0:
            log_dev("Overlay", f"FFmpeg error: {result.stderr.decode()}")
            return False

        return os.path.exists(output_path)

    except Exception as e:
        log_dev("Overlay", f"Error creating overlay: {e}")
        return False


def assemble_ranking_video(
    script: Dict,
    channel_config: Dict
) -> Tuple[Optional[str], Optional[str]]:
    """
    Assemble complete ranking video from script.

    Process:
    1. Generate voiceovers for all 5 items
    2. Download video clips for all 5 items
    3. Create overlay for each rank
    4. Assemble clips with overlays + captions
    5. Add background music
    6. Mix final audio

    Returns: (final_video_path, error_message)
    """
    channel_id = channel_config.get('id', 0)
    channel_name = channel_config.get('name', 'default')
    music_volume = channel_config.get('music_volume', 15) / 100.0

    timestamp = int(time.time() * 1000)
    base_name = f"{channel_name}_{timestamp}_ranking"
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    try:
        title = script['title']
        ranked_items = script['ranked_items']

        log_to_db(channel_id, "info", "assembly", f"Starting ranking video: {title}")

        # =============================================================
        # STEP 1: Generate voiceovers for all items
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 1/7: Generating voiceovers...")

        voiceover_files = []
        for i, item in enumerate(ranked_items):
            vo_path = os.path.join(output_dir, f"{base_name}_vo_{item['rank']}.mp3")

            success, error = generate_voiceover(
                item['narration'],
                vo_path,
                channel_id
            )

            if not success:
                return None, f"Voiceover {item['rank']} failed: {error}"

            voiceover_files.append(vo_path)

        log_to_db(channel_id, "info", "assembly", f"✓ Generated {len(voiceover_files)} voiceovers")

        # =============================================================
        # STEP 2: Download video clips for all items
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 2/7: Downloading clips...")

        clip_files = []
        for i, item in enumerate(ranked_items):
            clip_path = os.path.join(output_dir, f"{base_name}_clip_{item['rank']}.mp4")

            success, error = download_video_clip(
                item['searchQuery'],
                clip_path,
                duration=12,  # Each clip is 12 seconds
                channel_id=channel_id
            )

            if not success:
                return None, f"Clip {item['rank']} download failed: {error}"

            clip_files.append(clip_path)

        log_to_db(channel_id, "info", "assembly", f"✓ Downloaded {len(clip_files)} clips")

        # =============================================================
        # STEP 3: Download background music
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 3/7: Getting background music...")

        music_path = os.path.join(output_dir, f"{base_name}_music.mp3")
        music_keywords = script.get('ranked_items', [{}])[0].get('musicKeywords', 'energetic upbeat')

        music_success, music_error = download_background_music(music_keywords, music_path, channel_id)
        if not music_success:
            log_to_db(channel_id, "warning", "assembly", f"Music failed: {music_error}")
            music_path = None

        # =============================================================
        # STEP 4: Create clips with overlays and captions
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 4/7: Adding overlays...")

        processed_clips = []
        for i, item in enumerate(ranked_items):
            rank = item['rank']
            clip_path = clip_files[i]
            vo_path = voiceover_files[i]

            # Create subtitle file for this clip
            subs_path = os.path.join(output_dir, f"{base_name}_subs_{rank}.srt")
            with open(subs_path, 'w', encoding='utf-8') as f:
                f.write("1\n")
                f.write("00:00:00,000 --> 00:00:12,000\n")
                f.write(f"{item['narration']}\n")

            # Output with overlays and captions
            processed_path = os.path.join(output_dir, f"{base_name}_processed_{rank}.mp4")

            # Create overlay image for this rank
            overlay_path = os.path.join(output_dir, f"{base_name}_overlay_{rank}.png")
            if not create_ranking_overlay(title, ranked_items, rank, overlay_path):
                return None, f"Failed to create overlay for rank {rank}"

            # Apply overlay + subtitles
            subtitle_style = (
                "Alignment=10,FontName=Arial Bold,FontSize=28,PrimaryColour=&H00FFFFFF,"
                "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=180"
            )

            result = subprocess.run([
                FFMPEG, '-y',
                '-i', clip_path,
                '-i', overlay_path,
                '-filter_complex',
                f"[0:v][1:v]overlay=0:0[vid];[vid]subtitles={subs_path}:force_style='{subtitle_style}'[out]",
                '-map', '[out]',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-t', '12',
                processed_path
            ], capture_output=True, cwd=output_dir, timeout=60)

            if result.returncode != 0:
                return None, f"Processing rank {rank} failed: {result.stderr.decode()}"

            processed_clips.append(processed_path)

        log_to_db(channel_id, "info", "assembly", "✓ Overlays and captions added")

        # =============================================================
        # STEP 5: Concatenate all processed clips
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 5/7: Concatenating clips...")

        concat_list = os.path.join(output_dir, f"{base_name}_concat_list.txt")
        with open(concat_list, 'w') as f:
            for clip in processed_clips:
                f.write(f"file '{os.path.basename(clip)}'\n")

        concat_video = os.path.join(output_dir, f"{base_name}_concat.mp4")

        result = subprocess.run([
            FFMPEG, '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', os.path.basename(concat_list),
            '-c', 'copy',
            concat_video
        ], capture_output=True, cwd=output_dir, timeout=120)

        if result.returncode != 0:
            return None, f"Concatenation failed: {result.stderr.decode()}"

        log_to_db(channel_id, "info", "assembly", "✓ Clips concatenated")

        # =============================================================
        # STEP 6: Mix audio (voiceovers + music)
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 6/7: Mixing audio...")

        # Concatenate voiceovers
        vo_list = os.path.join(output_dir, f"{base_name}_vo_list.txt")
        with open(vo_list, 'w') as f:
            for vo in voiceover_files:
                f.write(f"file '{os.path.basename(vo)}'\n")

        concat_vo = os.path.join(output_dir, f"{base_name}_full_vo.mp3")
        subprocess.run([
            FFMPEG, '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', os.path.basename(vo_list),
            '-c', 'copy',
            concat_vo
        ], capture_output=True, cwd=output_dir, timeout=60)

        # Mix with music if available
        final_audio = concat_vo
        if music_path and os.path.exists(music_path):
            mixed_audio = os.path.join(output_dir, f"{base_name}_mixed_audio.mp3")
            result = subprocess.run([
                FFMPEG, '-y',
                '-i', os.path.basename(concat_vo),
                '-i', os.path.basename(music_path),
                '-filter_complex',
                f"[1:a]volume={music_volume}[music];[0:a][music]amix=inputs=2:duration=shortest[out]",
                '-map', '[out]',
                mixed_audio
            ], capture_output=True, cwd=output_dir, timeout=60)

            if result.returncode == 0:
                final_audio = mixed_audio

        log_to_db(channel_id, "info", "assembly", "✓ Audio mixed")

        # =============================================================
        # STEP 7: Merge final audio with video
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 7/7: Creating final video...")

        final_video = os.path.join(output_dir, f"{base_name}_FINAL.mp4")

        result = subprocess.run([
            FFMPEG, '-y',
            '-i', concat_video,
            '-i', final_audio,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            final_video
        ], capture_output=True, timeout=180)

        if result.returncode != 0:
            return None, f"Final merge failed: {result.stderr.decode()}"

        # Verify
        if not os.path.exists(final_video) or os.path.getsize(final_video) < 100000:
            return None, "Final video file invalid"

        size_mb = os.path.getsize(final_video) / (1024 * 1024)
        log_to_db(channel_id, "info", "assembly", f"✓ Ranking video complete! Size: {size_mb:.1f}MB")

        return final_video, None

    except Exception as e:
        error_msg = f"Assembly failed: {str(e)}"
        log_to_db(channel_id, "error", "assembly", error_msg)
        return None, error_msg


# ==============================================================================
# Main Generation Function
# ==============================================================================

def generate_ranking_video(channel_config: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Main function to generate a complete ranking video.

    Args:
        channel_config: Channel configuration dict with theme, tone, style, etc.

    Returns: (video_path, error_message)
    """
    channel_id = channel_config.get('id', 0)

    try:
        # Step 1: Generate script
        log_to_db(channel_id, "info", "generation", "Step 1: Generating ranking script...")

        script, error = generate_ranking_script(
            theme=channel_config.get('theme', 'interesting facts'),
            tone=channel_config.get('tone', 'Exciting'),
            style=channel_config.get('style', 'Fast-paced'),
            channel_id=channel_id
        )

        if not script:
            return None, f"Script generation failed: {error}"

        log_to_db(channel_id, "info", "generation", f"Step 2: Assembling '{script['title']}'...")

        # Step 2: Assemble video
        video_path, error = assemble_ranking_video(script, channel_config)

        if not video_path:
            return None, f"Video assembly failed: {error}"

        return video_path, None

    except Exception as e:
        error_msg = f"Ranking video generation failed: {str(e)}"
        log_to_db(channel_id, "error", "generation", error_msg)
        return None, error_msg
