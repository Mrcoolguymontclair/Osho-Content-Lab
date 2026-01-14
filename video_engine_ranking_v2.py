#!/usr/bin/env python3
"""
RANKING VIDEO GENERATION ENGINE V2 - COMPLETE QUALITY OVERHAUL
Fixes ALL video quality issues:
- Audio/video sync problems
- Boring narration
- Poor clip selection
- Bad pacing
- Weak hooks
- Visual quality issues
"""

import os
import subprocess
import time
import shutil
import json
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Import shared utilities
from video_engine import (
    FFMPEG, FFPROBE, groq_client, PEXELS_API_KEY,
    log_to_db, log_dev, download_video_clip,
    generate_voiceover, download_background_music
)

# Import duplicate detector
from duplicate_detector import is_duplicate_title, is_duplicate_topic

# Import music manager
from music_manager import get_music_for_mood, get_default_music_for_video_type

# Import dynamic pacing optimizer
from pacing_optimizer import get_pacing_for_rank

# Import audio ducking
from audio_ducking import mix_audio_with_ducking, mix_audio_simple_duck

# Import QUALITY IMPROVEMENTS
from title_thumbnail_optimizer import TitleThumbnailOptimizer
from video_quality_enhancer import VideoQualityEnhancer

# Initialize optimizers
title_optimizer = TitleThumbnailOptimizer()
quality_enhancer = VideoQualityEnhancer()

# Video constants
TOTAL_DURATION = 45  # Total video length in seconds
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920

# ==============================================================================
# IMPROVED Script Generation with Better Narration
# ==============================================================================

def generate_ranking_script_v2(
    theme: str,
    tone: str = "Exciting",
    style: str = "Fast-paced",
    channel_id: int = 0,
    ranking_count: int = 5
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Generate ENGAGING ranking video script with varied narration.
    """
    if not groq_client:
        return None, "Groq API key not configured"

    try:
        log_to_db(channel_id, "info", "script", "Generating V2 ranking script (engaging)...")

        # Get recent videos to avoid duplicates
        from channel_manager import get_channel_videos
        recent_videos = get_channel_videos(channel_id, limit=30)
        recent_titles = [v['title'] for v in recent_videos if v.get('title')]

        # Extract topics to avoid
        avoid_keywords = set()
        for title in recent_titles:
            words = title.lower().split()
            for word in words:
                if len(word) > 5 and word not in ['ranking', 'ranked', 'worst', 'extreme', 'top']:
                    avoid_keywords.add(word)

        avoid_topics_str = ", ".join(list(avoid_keywords)[:10]) if avoid_keywords else "none"

        prompt = f"""Generate an EXTREMELY ENGAGING YouTube Shorts ranking video.

THEME: {theme}
TONE: {tone}
STYLE: {style}
FORMAT: Top {ranking_count} countdown (5→1 or 10→1)
TARGET: 45 seconds total

🚫 AVOID these recent topics: {avoid_topics_str}

CRITICAL REQUIREMENTS:

1. ENGAGING NARRATION (NOT BORING!)
   ✅ Use varied sentence structures (not all "This X is Y because Z")
   ✅ Add personality: "Wait till you see #1!", "Believe it or not...", "Here's the crazy part..."
   ✅ Use specific details and facts, not generic statements
   ✅ Create curiosity: "You've probably never heard of this one"
   ✅ Build excitement as you count down

   ❌ DON'T be robotic: "Number 5 is X. It is Y. This is because Z."
   ❌ DON'T repeat the same sentence structure every time
   ❌ DON'T use generic descriptions

2. TITLE FORMAT
   - ALL CAPS with exclamation mark
   - Include numbers and power words
   - Example: "TOP 5 MOST EXTREME VOLCANOES ON EARTH!"
   - NOT: "Ranking Volcanoes" or "Top Volcanoes"

3. SEARCH QUERIES (CRITICAL FOR GOOD CLIPS)
   - Be VERY specific and visual
   - Include adjectives that describe the visual you want
   - ✅ GOOD: "volcanic eruption with lava flow aerial view"
   - ✅ GOOD: "massive waterfall rainbow mist slow motion"
   - ❌ BAD: "volcano" or "waterfall" (too generic)

4. PACING
   - Rank 5: 7 seconds (intro + description)
   - Rank 4: 8 seconds
   - Rank 3: 9 seconds
   - Rank 2: 10 seconds
   - Rank 1: 11 seconds (build suspense!)

Return ONLY valid JSON:
{{
  "title": "TOP 5 [CATEGORY]!",
  "adjective": "extreme/amazing/incredible",
  "hook": "Short 1-sentence hook for opening",
  "ranked_items": [
    {{
      "rank": 5,
      "title": "Short descriptive title",
      "narration": "Engaging 2-3 sentence narration with personality and specific details (NOT boring/generic)",
      "searchQuery": "Highly specific visual search query with adjectives",
      "visual_note": "What makes this visually interesting"
    }},
    ...
  ]
}}

Make it EXCITING and VARIED! People should WANT to watch this!"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,  # Higher creativity
            max_tokens=2500
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        script = json.loads(content)

        # Validate structure
        if not script.get('ranked_items') or len(script['ranked_items']) != ranking_count:
            return None, f"Expected {ranking_count} items, got {len(script.get('ranked_items', []))}"

        # Optimize title for virality
        original_title = script['title']
        optimized_title = title_optimizer.optimize_ranking_title(theme, ranking_count)
        title_score = title_optimizer.analyze_title_effectiveness(optimized_title)

        script['title'] = optimized_title
        log_to_db(channel_id, "info", "title_opt", f"Title: {original_title[:40]}... → {optimized_title} (score: {title_score['score']}/100)")

        log_to_db(channel_id, "info", "script", f"✓ Generated: {script['title']} ({ranking_count} items)")
        return script, None

    except Exception as e:
        log_to_db(channel_id, "error", "script", f"Script generation failed: {str(e)}")
        return None, str(e)

# ==============================================================================
# IMPROVED Clip Download with Better Selection
# ==============================================================================

def download_engaging_clip(
    search_query: str,
    output_path: str,
    duration: float,
    channel_id: int = 0,
    attempt: int = 1
) -> Tuple[bool, Optional[str]]:
    """
    Download high-quality, engaging video clips with better selection.
    """
    try:
        log_to_db(channel_id, "info", "clip", f"Searching: '{search_query}' ({duration:.1f}s)")

        # Search Pexels for videos
        headers = {"Authorization": PEXELS_API_KEY}

        # Prioritize: high resolution, landscape orientation for better crop
        params = {
            "query": search_query,
            "per_page": 15,  # Get more options
            "orientation": "portrait",  # Prefer portrait for Shorts
            "size": "large"
        }

        import requests
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params,
            timeout=15
        )

        if response.status_code != 200:
            return False, f"Pexels API error: {response.status_code}"

        data = response.json()
        videos = data.get('videos', [])

        if not videos:
            return False, f"No clips found for '{search_query}'"

        # Select best video (prioritize HD and duration match)
        best_video = None
        best_score = -1

        for video in videos[:10]:  # Check top 10
            video_files = video.get('video_files', [])
            if not video_files:
                continue

            # Score based on quality and duration
            score = 0
            vid_duration = video.get('duration', 0)

            # Prefer videos close to desired duration
            duration_diff = abs(vid_duration - duration)
            if duration_diff < 5:
                score += 50
            elif duration_diff < 10:
                score += 30
            elif duration_diff < 20:
                score += 10

            # Prefer HD quality
            hd_file = None
            for vf in video_files:
                if vf.get('height', 0) >= 720:
                    score += 30
                    hd_file = vf
                    break

            if score > best_score and hd_file:
                best_score = score
                best_video = hd_file

        if not best_video:
            # Fallback to first video
            best_video = videos[0]['video_files'][0]

        video_url = best_video.get('link')
        if not video_url:
            return False, "No video URL found"

        # Download video
        log_to_db(channel_id, "info", "clip", f"Downloading from Pexels (quality: {best_video.get('height', '?')}p)...")

        vid_response = requests.get(video_url, stream=True, timeout=60)
        if vid_response.status_code != 200:
            return False, f"Download failed: {vid_response.status_code}"

        temp_path = output_path + ".temp"
        with open(temp_path, 'wb') as f:
            for chunk in vid_response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Process: crop to 9:16, trim to duration, ensure smooth loop
        result = subprocess.run([
            FFMPEG, '-y', '-i', temp_path,
            '-vf', f'scale={SHORTS_WIDTH}:{SHORTS_HEIGHT}:force_original_aspect_ratio=increase,crop={SHORTS_WIDTH}:{SHORTS_HEIGHT},loop=loop=3:size=1:start=0',
            '-t', str(duration),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-an',  # Remove audio
            output_path
        ], capture_output=True, timeout=60)

        os.remove(temp_path)

        if result.returncode != 0:
            return False, f"Processing failed: {result.stderr.decode()}"

        # Verify output
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 50000:
            return False, "Output file too small"

        log_to_db(channel_id, "info", "clip", f"✓ Downloaded: {search_query[:40]}")
        return True, None

    except Exception as e:
        return False, f"Clip download error: {str(e)}"

# ==============================================================================
# IMPROVED Audio Mixing (Perfect Sync)
# ==============================================================================

def create_perfect_audio_track(
    voiceover_files: List[str],
    music_path: Optional[str],
    output_path: str,
    target_duration: float,
    channel_id: int = 0
) -> Tuple[bool, Optional[str]]:
    """
    Create perfectly synced audio track that matches video duration EXACTLY.
    """
    try:
        # Step 1: Concatenate voiceovers
        temp_dir = os.path.dirname(output_path)
        concat_vo = os.path.join(temp_dir, "temp_vo_concat.mp3")

        vo_list_file = os.path.join(temp_dir, "vo_list.txt")
        with open(vo_list_file, 'w') as f:
            for vo in voiceover_files:
                f.write(f"file '{os.path.basename(vo)}'\n")

        # Concatenate
        result = subprocess.run([
            FFMPEG, '-y',
            '-f', 'concat', '-safe', '0',
            '-i', os.path.basename(vo_list_file),
            '-c', 'copy',
            os.path.basename(concat_vo)
        ], capture_output=True, cwd=temp_dir, timeout=30)

        if result.returncode != 0:
            return False, f"VO concat failed: {result.stderr.decode()}"

        # Step 2: Measure actual voiceover duration
        probe_result = subprocess.run([
            FFPROBE, '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            concat_vo
        ], capture_output=True, text=True, timeout=10)

        vo_duration = float(probe_result.stdout.strip())
        log_to_db(channel_id, "info", "audio", f"Voiceover: {vo_duration:.2f}s (target: {target_duration:.2f}s)")

        # Step 3: Mix with music and PAD/TRIM to exact duration
        if music_path and os.path.exists(music_path):
            # Use audio ducking for professional sound
            mixed_audio = os.path.join(temp_dir, "temp_mixed.mp3")

            success = mix_audio_with_ducking(
                concat_vo,
                music_path,
                mixed_audio,
                music_volume_normal=0.10,
                music_volume_ducked=0.04
            )

            if not success:
                # Fallback to simple mix
                success = mix_audio_simple_duck(concat_vo, music_path, mixed_audio, music_volume=0.08)

            source_audio = mixed_audio if success else concat_vo
        else:
            source_audio = concat_vo

        # Step 4: CRITICAL - Pad/trim to EXACT duration
        if vo_duration < target_duration:
            # Pad with silence at the end
            silence_duration = target_duration - vo_duration
            log_to_db(channel_id, "info", "audio", f"Padding {silence_duration:.2f}s silence")

            result = subprocess.run([
                FFMPEG, '-y',
                '-i', source_audio,
                '-f', 'lavfi', '-t', str(silence_duration), '-i', 'anullsrc=r=44100:cl=stereo',
                '-filter_complex', '[0:a][1:a]concat=n=2:v=0:a=1[out]',
                '-map', '[out]',
                '-c:a', 'aac', '-b:a', '192k',
                output_path
            ], capture_output=True, timeout=30)
        else:
            # Trim to exact duration
            log_to_db(channel_id, "info", "audio", f"Trimming to {target_duration:.2f}s")
            result = subprocess.run([
                FFMPEG, '-y',
                '-i', source_audio,
                '-t', str(target_duration),
                '-c:a', 'aac', '-b:a', '192k',
                output_path
            ], capture_output=True, timeout=30)

        if result.returncode != 0:
            return False, f"Final audio processing failed: {result.stderr.decode()}"

        # Verify exact duration
        probe_result = subprocess.run([
            FFPROBE, '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            output_path
        ], capture_output=True, text=True, timeout=10)

        final_duration = float(probe_result.stdout.strip())
        duration_diff = abs(final_duration - target_duration)

        if duration_diff > 0.1:
            log_to_db(channel_id, "warning", "audio", f"Duration off by {duration_diff:.2f}s")
        else:
            log_to_db(channel_id, "info", "audio", f"✓ Perfect audio: {final_duration:.2f}s")

        # Cleanup
        for temp_file in [concat_vo, mixed_audio, vo_list_file]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

        return True, None

    except Exception as e:
        return False, f"Audio creation error: {str(e)}"

# ==============================================================================
# IMPROVED Visual Assembly with Better Overlays
# ==============================================================================

def create_engaging_video_clip(
    clip_path: str,
    voiceover_path: str,
    rank: int,
    title: str,
    narration: str,
    clip_duration: float,
    output_path: str,
    channel_id: int = 0
) -> Tuple[bool, Optional[str]]:
    """
    Create visually engaging clip with improved overlays and effects.
    """
    try:
        temp_dir = os.path.dirname(output_path)

        # Create enhanced subtitle file
        subs_path = os.path.join(temp_dir, f"subs_{rank}.srt")
        with open(subs_path, 'w', encoding='utf-8') as f:
            f.write("1\n")
            f.write(f"00:00:00,000 --> {int(clip_duration // 60):02d}:{int(clip_duration % 60):02d},{int((clip_duration % 1) * 1000):03d}\n")

            # Clean and wrap text
            clean_narration = narration.replace('-->', '->').replace('\n', ' ').strip()

            # Word wrap for readability (max 40 chars per line for better readability)
            words = clean_narration.split()
            lines = []
            current_line = ""

            for word in words:
                if len(current_line) + len(word) + 1 <= 40:
                    current_line += word + " "
                else:
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word + " "

                    if len(lines) >= 2:  # Max 2 lines
                        break

            if current_line and len(lines) < 2:
                lines.append(current_line.strip())

            wrapped_text = "\\N".join(lines[:2])
            f.write(wrapped_text + "\n\n")

        # Create rank badge overlay (PNG with transparency)
        badge_path = os.path.join(temp_dir, f"badge_{rank}.png")

        # Badge color based on rank importance
        if rank == 1:
            color = "#FFD700"  # Gold
            size = "200"
        elif rank == 2:
            color = "#C0C0C0"  # Silver
            size = "180"
        elif rank == 3:
            color = "#CD7F32"  # Bronze
            size = "160"
        else:
            color = "#4A90E2"  # Blue
            size = "140"

        badge_cmd = [
            FFMPEG, '-y',
            '-f', 'lavfi', '-i', f'color=c={color}:s={size}x{size}:d={clip_duration}',
            '-vf', f"drawtext=text='#{rank}':fontsize=80:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:fontfile=/System/Library/Fonts/Helvetica.ttc",
            badge_path
        ]

        subprocess.run(badge_cmd, capture_output=True, timeout=15)

        # Build filter complex for video effects
        filter_parts = []

        # Base video with subtle zoom effect for dynamism
        filter_parts.append(f"[0:v]scale={SHORTS_WIDTH}:{SHORTS_HEIGHT}:force_original_aspect_ratio=increase,crop={SHORTS_WIDTH}:{SHORTS_HEIGHT},zoompan=z='min(zoom+0.0005,1.1)':d={int(clip_duration * 30)}:s={SHORTS_WIDTH}x{SHORTS_HEIGHT}[base]")

        # Add rank badge (top left corner)
        if os.path.exists(badge_path):
            filter_parts.append(f"[base][1:v]overlay=20:60[with_badge]")
            filter_parts.append(f"[with_badge]subtitles='{os.path.basename(subs_path)}':force_style='Alignment=2,MarginV=120,Fontsize=28,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=3,Shadow=2,Bold=1'[out]")
            overlay_input = ['-i', badge_path]
        else:
            filter_parts.append(f"[base]subtitles='{os.path.basename(subs_path)}':force_style='Alignment=2,MarginV=120,Fontsize=28,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=3,Shadow=2,Bold=1'[out]")
            overlay_input = []

        filter_complex = ";".join(filter_parts)

        # Assemble command
        cmd = [
            FFMPEG, '-y',
            '-i', clip_path
        ] + overlay_input + [
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '20',
            '-b:v', '5000k',
            '-maxrate', '6000k',
            '-bufsize', '10000k',
            '-r', '30',
            '-t', str(clip_duration),
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, cwd=temp_dir, timeout=120)

        if result.returncode != 0:
            return False, f"Visual processing failed: {result.stderr.decode()}"

        # Verify output
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 100000:
            return False, "Output too small"

        # Cleanup temp files
        for temp_file in [subs_path, badge_path]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

        return True, None

    except Exception as e:
        return False, f"Visual assembly error: {str(e)}"

# ==============================================================================
# MAIN: Generate Complete Ranking Video (V2 - ALL FIXES)
# ==============================================================================

def generate_ranking_video_v2(
    theme: str,
    tone: str = "Exciting",
    style: str = "Fast-paced",
    channel_id: int = 0,
    ranking_count: int = 5
) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate complete ranking video with ALL quality improvements.

    Returns: (video_path, error_message)
    """
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    base_name = f"RankRiot_{int(time.time()*1000)}_ranking_v2"

    try:
        log_to_db(channel_id, "info", "generation", "=== STARTING V2 GENERATION (ALL FIXES) ===")

        # STEP 1: Generate engaging script
        script, error = generate_ranking_script_v2(theme, tone, style, channel_id, ranking_count)
        if error:
            return None, f"Script generation failed: {error}"

        ranked_items = script['ranked_items']
        log_to_db(channel_id, "info", "generation", f"Title: {script['title']}")

        # STEP 2: Generate voiceovers
        log_to_db(channel_id, "info", "generation", "Generating voiceovers...")
        voiceover_files = []

        # Add hook first
        if script.get('hook'):
            hook_path = os.path.join(output_dir, f"{base_name}_hook.mp3")
            success, error = generate_voiceover(script['hook'], hook_path, channel_id)
            if success:
                voiceover_files.append(hook_path)
                log_to_db(channel_id, "info", "generation", f"✓ Hook: {script['hook'][:40]}...")

        # Generate narration for each rank
        for item in ranked_items:
            vo_path = os.path.join(output_dir, f"{base_name}_vo_{item['rank']}.mp3")
            intro = f"Number {item['rank']}. "
            narration = intro + item['narration']

            success, error = generate_voiceover(narration, vo_path, channel_id)
            if not success:
                return None, f"Voiceover failed for rank {item['rank']}: {error}"

            voiceover_files.append(vo_path)

        log_to_db(channel_id, "info", "generation", f"✓ Generated {len(voiceover_files)} voiceovers")

        # STEP 3: Download engaging clips
        log_to_db(channel_id, "info", "generation", "Downloading clips...")
        clip_files = []
        clip_durations = []

        for item in ranked_items:
            clip_path = os.path.join(output_dir, f"{base_name}_clip_{item['rank']}.mp4")
            clip_duration = get_pacing_for_rank(item['rank'], ranking_count, TOTAL_DURATION)
            clip_durations.append(clip_duration)

            success, error = download_engaging_clip(
                item['searchQuery'],
                clip_path,
                clip_duration,
                channel_id
            )

            if not success:
                return None, f"Clip download failed for rank {item['rank']}: {error}"

            clip_files.append(clip_path)

        log_to_db(channel_id, "info", "generation", f"✓ Downloaded {len(clip_files)} clips")

        # STEP 4: Get music
        mood_tags = get_default_music_for_video_type('ranking')
        music_path = get_music_for_mood(mood_tags)

        if music_path:
            log_to_db(channel_id, "info", "generation", f"✓ Music: {os.path.basename(music_path)}")
        else:
            log_to_db(channel_id, "warning", "generation", "No music available")

        # STEP 5: Create visual clips with overlays
        log_to_db(channel_id, "info", "generation", "Creating visual clips...")
        processed_clips = []

        # Skip hook for video (audio only)
        vo_start_idx = 1 if script.get('hook') else 0

        for i, item in enumerate(ranked_items):
            processed_path = os.path.join(output_dir, f"{base_name}_processed_{item['rank']}.mp4")

            success, error = create_engaging_video_clip(
                clip_files[i],
                voiceover_files[vo_start_idx + i],
                item['rank'],
                item['title'],
                item['narration'],
                clip_durations[i],
                processed_path,
                channel_id
            )

            if not success:
                return None, f"Visual processing failed for rank {item['rank']}: {error}"

            processed_clips.append(processed_path)

        log_to_db(channel_id, "info", "generation", "✓ Visual clips complete")

        # STEP 6: Concatenate video clips
        log_to_db(channel_id, "info", "generation", "Concatenating clips...")
        concat_list = os.path.join(output_dir, f"{base_name}_concat_list.txt")
        with open(concat_list, 'w') as f:
            for clip in processed_clips:
                f.write(f"file '{os.path.basename(clip)}'\n")

        concat_video = os.path.join(output_dir, f"{base_name}_concat.mp4")
        result = subprocess.run([
            FFMPEG, '-y',
            '-f', 'concat', '-safe', '0',
            '-i', os.path.basename(concat_list),
            '-c', 'copy',
            os.path.basename(concat_video)
        ], capture_output=True, cwd=output_dir, timeout=120)

        if result.returncode != 0:
            return None, f"Concatenation failed: {result.stderr.decode()}"

        # STEP 7: Create perfect audio track
        log_to_db(channel_id, "info", "generation", "Creating audio track...")
        final_audio = os.path.join(output_dir, f"{base_name}_audio.aac")

        success, error = create_perfect_audio_track(
            voiceover_files,
            music_path,
            final_audio,
            TOTAL_DURATION,
            channel_id
        )

        if not success:
            return None, f"Audio creation failed: {error}"

        # STEP 8: Final merge with PERFECT sync
        log_to_db(channel_id, "info", "generation", "Final merge...")
        final_video = os.path.join(output_dir, f"{base_name}_FINAL.mp4")

        # Use -shortest to match shortest stream duration
        # Both video and audio should be exactly 45 seconds now
        result = subprocess.run([
            FFMPEG, '-y',
            '-i', os.path.basename(concat_video),
            '-i', os.path.basename(final_audio),
            '-c:v', 'copy',
            '-c:a', 'copy',
            '-shortest',  # Stop at shortest stream (both should be 45s)
            os.path.basename(final_video)
        ], capture_output=True, cwd=output_dir, timeout=180)

        if result.returncode != 0:
            return None, f"Final merge failed: {result.stderr.decode()}"

        # Verify final video
        if not os.path.exists(final_video) or os.path.getsize(final_video) < 500000:
            return None, "Final video invalid"

        # Check duration
        probe_result = subprocess.run([
            FFPROBE, '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            final_video
        ], capture_output=True, text=True, timeout=10)

        actual_duration = float(probe_result.stdout.strip())
        size_mb = os.path.getsize(final_video) / (1024 * 1024)

        log_to_db(channel_id, "info", "generation", f"✓ COMPLETE! Duration: {actual_duration:.2f}s | Size: {size_mb:.1f}MB")

        if abs(actual_duration - TOTAL_DURATION) > 1.0:
            log_to_db(channel_id, "warning", "generation", f"Duration off by {abs(actual_duration - TOTAL_DURATION):.2f}s")

        return final_video, None

    except Exception as e:
        log_to_db(channel_id, "error", "generation", f"Video generation failed: {str(e)}")
        return None, str(e)
