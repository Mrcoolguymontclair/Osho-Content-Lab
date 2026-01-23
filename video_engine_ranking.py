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

# Import duplicate detector
from duplicate_detector import is_duplicate_title, is_duplicate_topic

# Import music manager
from music_manager import get_music_for_mood, get_default_music_for_video_type

# Import enhanced AI analytics
from ai_analytics_enhanced import should_generate_video, get_video_generation_config

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

# ==============================================================================
# Ranking Script Generation
# ==============================================================================

def generate_ranking_script(
    theme: str,
    tone: str = "Exciting",
    style: str = "Fast-paced",
    channel_id: int = 0,
    use_strategy: bool = True,
    ranking_count: int = 5
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Generate ranking video script using Groq AI.

    Args:
        theme: Video theme
        tone: Video tone
        style: Video style
        channel_id: Channel ID for logging
        use_strategy: If False, ignore AI recommendations (for A/B testing)
        ranking_count: Number of items to rank (default 5, determines clip count)

    Returns: (script_dict, error_message)
    script_dict contains: title, adjective, ranked_items[{rank, title, narration, searchQuery}]
    """
    if not groq_client:
        return None, "Groq API key not configured"

    try:
        log_to_db(channel_id, "info", "script", "Generating ranking script...")

        # Get recent video titles to avoid duplicates
        from channel_manager import get_channel_videos
        recent_videos = get_channel_videos(channel_id, limit=30)
        recent_titles = [v['title'] for v in recent_videos if v.get('title')]

        # Extract key topics from recent titles to avoid
        avoid_keywords = set()
        for title in recent_titles:
            words = title.lower().split()
            for word in words:
                if len(word) > 5 and word not in ['ranking', 'ranked', 'worst', 'extreme']:
                    avoid_keywords.add(word)

        avoid_topics_str = ", ".join(list(avoid_keywords)[:10]) if avoid_keywords else "none"

        # Conditionally fetch AI strategy
        strategy_prompt = ""
        if use_strategy:
            from ai_analyzer import get_latest_content_strategy
            strategy = get_latest_content_strategy(channel_id)

            if strategy:
                recommended_topics = strategy.get('recommended_topics', [])[:3]
                avoid_topics = strategy.get('avoid_topics', [])[:2]
                content_style = strategy.get('content_style', '')

                if recommended_topics:
                    strategy_prompt = f"""

DATA-DRIVEN INSIGHTS (proven successful patterns):
[OK] WINNING TOPICS: {', '.join(recommended_topics)}
[OK] EFFECTIVE STYLE: {content_style}
[WARNING] AVOID: {', '.join(avoid_topics) if avoid_topics else 'N/A'}

Use these insights to guide your ranking topic selection.
"""
                    log_to_db(channel_id, "info", "script", f"Using AI strategy: {recommended_topics[0]}")

        # Calculate seconds per clip for pacing guidance (total video = 45 seconds)
        seconds_per_rank = 45 / ranking_count

        prompt = f"""Generate an engaging and ACCURATE YouTube Shorts RANKING video script.
{strategy_prompt}

THEME: {theme}
TONE: {tone}
STYLE: {style}
VIDEO FORMAT: {ranking_count} items, 45 seconds total ({seconds_per_rank:.1f}s per item)

 AVOID THESE RECENT TOPICS (we already covered them):
{avoid_topics_str}

[WARNING] IMPORTANT: Choose a COMPLETELY DIFFERENT topic from the ones above. Be creative and unique!

ACCURACY & SAFETY REQUIREMENTS (CRITICAL):
[WARNING] DO NOT create false, exaggerated, or unverifiable claims
[WARNING] DO NOT use misleading hooks like "99% don't know" or "this will change everything"
[WARNING] DO NOT rank things that require expert knowledge (medical, legal, safety)
[WARNING] DO focus on subjective rankings (beauty, entertainment, personal preference)
[OK] Rankings should be based on commonly agreed opinions or measurable criteria
[OK] Use honest, enthusiastic language without deception
[OK] Prefer entertainment/aesthetic rankings over factual/scientific claims

Your task:
1. Create an engaging title: "Ranking [superlative] [category]" or "Top {ranking_count} [category]"
   [OK] GOOD: "Ranking Most Beautiful Sunsets", "Top {ranking_count} Satisfying Moments"
   [ERROR] BAD: "Ranking Healthiest Foods" (requires expertise), "Top {ranking_count} Medical Cures" (dangerous)

   TITLE FORMATTING RULES (CRITICAL):
   - Use Title Case (Capital First Letters Only)
   - NEVER use ALL CAPS (reduces clicks, looks spammy)
   - Keep under 60 characters for mobile
   - Be descriptive, not clickbait
   - [OK] Example: "Top 5 Most Relaxing Nature Scenes"
   - [ERROR] Example: "TOP 10 MOST EXTREME LANDSCAPES RANKED!"

2. Choose an adjective that scales (beautiful→most beautiful, satisfying→most satisfying)

3. Generate {ranking_count} DISTINCT items ranked from LEAST to MOST [adjective]:
   - Rank {ranking_count}: Good but not the best (baseline)
   {'   - ' + ', '.join([f"Rank {i}" for i in range(ranking_count-1, 1, -1)]) + ': Progressively better' if ranking_count > 3 else ''}
   - Rank 1: THE ABSOLUTE BEST, most [adjective] of all

4. For each item provide:
   - title: Descriptive phrase (2-5 words)
   - narration: {int(seconds_per_rank * 8)}-{int(seconds_per_rank * 10)} words, factual and engaging
   - searchQuery: Common Pexels terms (generic, widely available footage)

ENGAGEMENT HOOKS (CRITICAL - First 3 Seconds):
The FIRST RANK narration MUST grab attention immediately. Use ONE of these proven patterns:

TIER 1 - HIGHEST RETENTION (Use these):
1. DRAMATIC REVEAL TEASE: "Number one will shock you, but let's start here..."
2. IMMEDIATE SUSPENSE: "Before I show you the best one, check this out..."
3. BOLD PROMISE: "By the end, you'll see the most [adjective] [thing] ever filmed"

TIER 2 - SOLID HOOKS (Good alternatives):
4. CURIOSITY GAP: "Most people don't know about number one..."
5. DIRECT CHALLENGE: "Can you guess what's number one before we get there?"
6. TIME URGENCY: "We've got 45 seconds to show you the [superlative] [things]"

TIER 3 - SAFE BACKUPS (Use if nothing else fits):
7. PROGRESSION TEASE: "We're building up to something incredible"
8. INCLUSIVE QUESTION: "Which one do you think will be number one?"

RULES:
- Hook must be in FIRST 3 SECONDS of narration
- Reference "number one" or "the best" to create suspense
- Be honest but exciting (no false claims)
- Create curiosity gap: tease without revealing

SEARCH QUERY RULES (for Pexels clip availability):
- Use COMMON, BROADLY AVAILABLE visuals (2-4 general keywords)
- Examples that WORK: "sunset ocean waves", "mountain peak clouds", "forest waterfall", "city lights night"
- Examples that FAIL: "specific cliff Iceland", "Mount Kilimanjaro sunrise" (too specific)
- Think: What common stock footage exists? Use generic terms
- Avoid: Specific locations, people's faces, brands, copyrighted content
- Prefer: Natural phenomena, landscapes, abstract concepts, actions, textures

CRITICAL RULES:
- Items must CLEARLY progress in quality/intensity (lower rank = good, rank 1 = AMAZING)
- Make #1 unmistakably THE BEST without exaggeration
- Narration must be CONCISE ({int(seconds_per_rank * 8)}-{int(seconds_per_rank * 10)} words)
- First rank narration = ENGAGING HOOK (honest, no clickbait)
- Search queries = COMMON stock footage terms
- Duration: Each clip is exactly {seconds_per_rank:.1f} seconds (total 45s)
- Content must be ACCURATE, SAFE, and APPROPRIATE for all ages

Output ONLY valid JSON (no markdown, no extra text):
{{
  "title": "Ranking [superlative] [category]",
  "adjective": "beautiful/satisfying/relaxing/etc",
  "theme": "{theme}",
  "ranked_items": [
    {{
      "rank": {ranking_count},
      "title": "Peaceful Beginning",
      "narration": "Let's start with something calming and beautiful",
      "searchQuery": "sunset ocean waves",
      "duration": {seconds_per_rank:.1f}
    }},
    ... (continue for all {ranking_count} ranks with CLEAR progression)
    {{
      "rank": 1,
      "title": "Absolute Perfection",
      "narration": "This is pure natural beauty at its finest",
      "searchQuery": "mountain aurora lights",
      "duration": {seconds_per_rank:.1f}
    }}
  ]
}}

REMEMBER: Generate exactly {ranking_count} items, each with duration {seconds_per_rank:.1f} seconds."""

        response = groq_client.chat_completions_create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,  # Reduced from 0.9 for more accurate/consistent output
            max_tokens=2000  # Increased to handle more items (3-10 range)
        )

        response_text = response.choices[0].message.content.strip()

        # Remove markdown if present
        if response_text.startswith("```"):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])

        script = json.loads(response_text)

        # Validate structure
        if not script.get('title') or not script.get('ranked_items'):
            raise Exception("Invalid script structure - missing title or ranked_items")

        # Validate correct number of items
        actual_count = len(script['ranked_items'])
        if actual_count != ranking_count:
            raise Exception(f"Expected {ranking_count} items, got {actual_count}")

        # Content safety check - basic keyword filtering
        unsafe_keywords = ['medical', 'cure', 'disease', 'legal advice', 'financial advice',
                          'drug', 'weapon', 'illegal', 'hack', 'violence', 'explicit']
        title_lower = script['title'].lower()

        for keyword in unsafe_keywords:
            if keyword in title_lower:
                log_to_db(channel_id, "warning", "script", f"Content safety warning: title contains '{keyword}'")
                raise Exception(f"Content safety check failed: potentially unsafe topic detected ('{keyword}')")

        # Quality check - ensure content meets engagement standards
        try:
            from quality_checker import check_script_quality, generate_quality_report

            is_valid, issues = check_script_quality(script, ranking_count)

            if not is_valid:
                report = generate_quality_report(script, ranking_count)
                log_to_db(channel_id, "warning", "script", f"Quality issues detected:\n{report}")
                # Log but don't fail - let through with warning
                # To enforce strictly, uncomment next line:
                # raise Exception(f"Quality check failed: {len(issues)} issues found")

        except ImportError:
            log_to_db(channel_id, "info", "script", "Quality checker not available, skipping quality check")

        # TITLE OPTIMIZATION - Make titles viral!
        original_title = script['title']
        optimized_title = title_optimizer.optimize_ranking_title(theme, ranking_count)
        title_score = title_optimizer.analyze_title_effectiveness(optimized_title)

        script['title'] = optimized_title
        log_to_db(channel_id, "info", "title_opt", f"Title optimized: {original_title[:50]}... → {optimized_title} (score: {title_score['score']}/100)")

        # DUPLICATE CHECK - Prevent repeat videos
        title = script['title']
        is_dup, dup_video = is_duplicate_title(title, channel_id, similarity_threshold=0.85, lookback_days=30)

        if is_dup:
            error_msg = f"Duplicate video detected: '{title}' is {dup_video['similarity']:.0%} similar to '{dup_video['title']}' (created {dup_video['created_at']})"
            log_to_db(channel_id, "warning", "duplicate", error_msg)
            return None, error_msg

        log_to_db(channel_id, "info", "script", f"Generated: {script['title']} ({ranking_count} items) [Title Score: {title_score['score']}/100]")

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

        # Ranking sidebar on left - only show ranks that have been revealed
        sidebar_x = 20
        sidebar_start_y = 400
        item_height = 200

        for item in ranked_items:
            rank = item['rank']

            # Only show ranks that have been revealed (countdown: 5, 4, 3, 2, 1)
            # If current_rank is 3, show ranks 5, 4, and 3 (but not 2 or 1 yet)
            if rank < current_rank:
                continue  # Skip ranks not yet revealed

            item_title = item['title'].replace("'", "'\\\\\\''")
            # Position ranks in countdown order: 5 at top (y=400), 1 at bottom (y=1200)
            y_pos = sidebar_start_y + (5 - rank) * item_height

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
            '-i', f'color=c=0x00000000:s={width}x{height}:d=0.1',  # Fully transparent RGBA
            '-vf', filter_string,
            '-frames:v', '1',
            '-pix_fmt', 'rgba',
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
    ranking_count = channel_config.get('ranking_count', 5)

    timestamp = int(time.time() * 1000)
    base_name = f"{channel_name}_{timestamp}_ranking"
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    try:
        title = script['title']
        ranked_items = script['ranked_items']

        # Sort items by rank descending (5 -> 4 -> 3 -> 2 -> 1) for countdown effect
        ranked_items = sorted(ranked_items, key=lambda x: x['rank'], reverse=True)

        # CRITICAL: Fixed duration - exactly 45 seconds total
        TOTAL_DURATION = 45.0

        # DYNAMIC PACING: Vary clip duration by importance
        # Last item (#1) gets most time, first item (#5) gets least
        log_to_db(channel_id, "info", "assembly", f"Starting ranking video: {title}")
        log_to_db(channel_id, "info", "assembly", f"Using dynamic pacing (dramatic build-up to #1)")

        # =============================================================
        # STEP 1: Generate voiceovers for all items (+ ATTENTION HOOK!)
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 1/7: Generating voiceovers...")

        voiceover_files = []
        voiceover_durations = []  # Track actual durations for subtitle timing

        # ATTENTION HOOK - First 3 seconds to grab viewers!
        hook_script = quality_enhancer.generate_hook_script(theme, "ranking")
        hook_path = os.path.join(output_dir, f"{base_name}_hook.mp3")

        log_to_db(channel_id, "info", "hook", f"Adding attention hook: '{hook_script}'")
        success, error = generate_voiceover(hook_script, hook_path, channel_id)

        if success:
            voiceover_files.append(hook_path)
            try:
                probe_result = subprocess.run([
                    FFPROBE, '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    hook_path
                ], capture_output=True, text=True, timeout=10)
                hook_duration = float(probe_result.stdout.strip())
                voiceover_durations.append(hook_duration)
                log_to_db(channel_id, "info", "hook", f"[OK] Hook added ({hook_duration:.1f}s) - 80% retention boost!")
            except:
                voiceover_durations.append(3.0)
        else:
            log_to_db(channel_id, "warning", "hook", "Hook generation failed, continuing without it")

        # Generate main item voiceovers
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

            # Measure actual voiceover duration for accurate subtitle timing
            try:
                probe_result = subprocess.run([
                    FFPROBE, '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    vo_path
                ], capture_output=True, text=True, timeout=10)

                vo_duration = float(probe_result.stdout.strip())
                voiceover_durations.append(vo_duration)
                log_to_db(channel_id, "info", "assembly", f"Voiceover {item['rank']}: {vo_duration:.1f}s")
            except Exception as e:
                log_to_db(channel_id, "warning", "assembly", f"Could not measure VO duration for rank {item['rank']}: {e}, using 12s default")
                voiceover_durations.append(12.0)  # Fallback to 12s if measurement fails

        log_to_db(channel_id, "info", "assembly", f"[OK] Generated {len(voiceover_files)} voiceovers")

        # =============================================================
        # STEP 2: Download video clips for all items
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 2/7: Downloading clips...")

        clip_files = []
        clip_durations = []  # Track individual durations
        used_video_ids = set()  # Track used videos to prevent repeats within this video

        for i, item in enumerate(ranked_items):
            clip_path = os.path.join(output_dir, f"{base_name}_clip_{item['rank']}.mp4")

            # DYNAMIC PACING: Get duration for this specific rank
            clip_duration = get_pacing_for_rank(item['rank'], ranking_count, TOTAL_DURATION)
            clip_durations.append(clip_duration)

            log_to_db(channel_id, "info", "assembly", f"Rank {item['rank']}: {clip_duration:.1f}s duration")

            success, error, video_id = download_video_clip(
                item['searchQuery'],
                clip_path,
                duration=clip_duration,  # Dynamic duration based on rank importance
                channel_id=channel_id,
                exclude_video_ids=used_video_ids
            )

            if not success:
                return None, f"Clip {item['rank']} download failed: {error}"

            if video_id:
                used_video_ids.add(video_id)
                log_to_db(channel_id, "info", "assembly", f"Added video ID {video_id} to exclusion list (total: {len(used_video_ids)})")

            clip_files.append(clip_path)

        log_to_db(channel_id, "info", "assembly", f"[OK] Downloaded {len(clip_files)} clips")

        # =============================================================
        # STEP 3: Get background music (local library)
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 3/7: Getting background music...")

        # Use local music library with mood matching
        mood_tags = get_default_music_for_video_type('ranking')
        music_path = get_music_for_mood(mood_tags)

        if music_path:
            log_to_db(channel_id, "info", "assembly", f"[OK] Selected: {os.path.basename(music_path)}")
        else:
            log_to_db(channel_id, "warning", "assembly", "No music available")
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
            clip_duration = clip_durations[i]  # Use dynamic duration for this rank

            # Create subtitle file for this clip with ACCURATE timing
            subs_path = os.path.join(output_dir, f"{base_name}_subs_{rank}.srt")
            with open(subs_path, 'w', encoding='utf-8') as f:
                f.write("1\n")

                # Use dynamic clip_duration for subtitle timing (matches video length exactly)
                mins = int(clip_duration // 60)
                secs = int(clip_duration % 60)
                millis = int((clip_duration % 1) * 1000)

                f.write(f"00:00:00,000 --> 00:{mins:02d}:{secs:02d},{millis:03d}\n")

                # Format narration text for readability
                narration = item['narration']
                # Remove SRT-breaking characters
                narration = narration.replace('-->', '->').replace('\n', ' ').replace('\r', ' ')

                # Add word wrapping for long text (YouTube Shorts optimal: 50-60 chars per line)
                if len(narration) > 120:
                    words = narration.split()
                    lines = []
                    current_line = ""
                    for word in words:
                        if len(current_line) + len(word) + 1 <= 60:
                            current_line += word + " "
                        else:
                            lines.append(current_line.strip())
                            current_line = word + " "
                            if len(lines) >= 2:  # Max 2 lines for readability
                                break
                    if current_line and len(lines) < 2:
                        lines.append(current_line.strip())
                    narration = "\\N".join(lines)  # \\N is SRT line break syntax
                else:
                    narration = narration.strip()

                f.write(f"{narration}\n")

            # Output with overlays and captions
            processed_path = os.path.join(output_dir, f"{base_name}_processed_{rank}.mp4")

            # Create overlay image for this rank
            overlay_path = os.path.join(output_dir, f"{base_name}_overlay_{rank}.png")
            if not create_ranking_overlay(title, ranked_items, rank, overlay_path):
                return None, f"Failed to create overlay for rank {rank}"

            # Apply overlay + subtitles
            # OPTIMIZED styling for mobile viewing (YouTube Shorts)
            # Centered, large text with high contrast for maximum readability
            subtitle_style = (
                "Alignment=2,"  # Bottom-center alignment (safest position)
                "FontName=Arial Black,"  # Bolder font for impact
                "FontSize=64,"  # Larger for mobile (was 56, now 64)
                "PrimaryColour=&H00FFFFFF,"  # White text (maximum contrast)
                "OutlineColour=&H00000000,"  # Black outline
                "BorderStyle=4,"  # Opaque box background (best readability)
                "Outline=5,"  # Thicker outline (was 4, now 5)
                "Shadow=2,"  # Moderate shadow for depth
                "MarginV=280,"  # Slightly lower (was 320, now 280) - more visible
                "MarginL=40,"  # Left margin for word wrap
                "MarginR=40,"  # Right margin for word wrap
                "BackColour=&HC0000000"  # Semi-opaque black (was A0, now C0 = more opaque)
            )

            # Use absolute path for subtitle file and escape it properly for FFmpeg
            abs_subs_path = os.path.abspath(subs_path)
            # Escape special characters for FFmpeg filter: backslashes, colons, quotes
            subs_filter = abs_subs_path.replace('\\', '\\\\').replace(':', '\\:').replace("'", "'\\\\''")

            # Ensure clip is properly scaled/cropped to vertical before overlaying the ranking UI
            filter_complex = (
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[bg];"
                f"[bg][1:v]overlay=0:0:format=yuv420[vid];"  # Explicit alpha blending
                f"[vid]subtitles='{subs_filter}':force_style='{subtitle_style}'[out]"
            )

            result = subprocess.run([
                FFMPEG, '-y',
                '-i', os.path.basename(clip_path),
                '-i', os.path.basename(overlay_path),
                '-filter_complex',
                filter_complex,
                '-map', '[out]',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '18',
                '-b:v', '4000k',
                '-maxrate', '5000k',
                '-bufsize', '8000k',
                '-r', '30',
                '-t', str(clip_duration),  # Dynamic clip duration based on rank
                os.path.basename(processed_path)
            ], capture_output=True, cwd=output_dir, timeout=120)

            if result.returncode != 0:
                return None, f"Processing rank {rank} failed: {result.stderr.decode()}"

            # Quick verification: if processed clip is unusually small or detected as all-black, retry with a simpler fallback
            try:
                if not os.path.exists(processed_path) or os.path.getsize(processed_path) < 100 * 1024:
                    log_to_db(channel_id, "warning", "assembly", f"Processed clip {rank} suspiciously small ({os.path.getsize(processed_path) if os.path.exists(processed_path) else 'missing'} bytes). Running fallback processing.")

                    # Fallback: create a scaled version of the original clip (no overlay/subtitles) to ensure visuals are present
                    fallback = subprocess.run([
                        FFMPEG, '-y',
                        '-i', os.path.basename(clip_path),
                        '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
                        '-t', str(clip_duration),
                        os.path.basename(processed_path)
                    ], capture_output=True, cwd=output_dir, timeout=120)

                    if fallback.returncode != 0:
                        return None, f"Processing rank {rank} failed (fallback): {fallback.stderr.decode()}"

                else:
                    # Run a quick black-detect check to avoid all-black clips
                    black_check = subprocess.run([
                        FFMPEG, '-v', 'error', '-i', os.path.basename(processed_path),
                        '-vf', 'blackdetect=d=0.5:pix_th=0.98', '-an', '-f', 'null', '-'
                    ], capture_output=True, text=True, cwd=output_dir, timeout=30)

                    stderr = (black_check.stderr or '').lower()
                    if 'black_start' in stderr and 'black_end' in stderr:
                        # If black covers the whole clip, retry fallback
                        log_to_db(channel_id, "warning", "assembly", f"Detected black video for rank {rank}; rerunning fallback processing")
                        fallback = subprocess.run([
                            FFMPEG, '-y',
                            '-i', os.path.basename(clip_path),
                            '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
                            '-t', str(clip_duration),
                            os.path.basename(processed_path)
                        ], capture_output=True, cwd=output_dir, timeout=120)

                        if fallback.returncode != 0:
                            return None, f"Processing rank {rank} failed (black-detect fallback): {fallback.stderr.decode()}"

            except Exception as e:
                log_to_db(channel_id, "warning", "assembly", f"Black-detection check failed for rank {rank}: {e}")

            processed_clips.append(processed_path)

        log_to_db(channel_id, "info", "assembly", "[OK] Overlays and captions added")

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
            os.path.basename(concat_video)
        ], capture_output=True, cwd=output_dir, timeout=120)

        if result.returncode != 0:
            return None, f"Concatenation failed: {result.stderr.decode()}"

        log_to_db(channel_id, "info", "assembly", "[OK] Clips concatenated")

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
            os.path.basename(concat_vo)
        ], capture_output=True, cwd=output_dir, timeout=60)

        # Mix with music using audio ducking (music lowers when voice speaks)
        final_audio = concat_vo
        if music_path and os.path.exists(music_path):
            mixed_audio = os.path.join(output_dir, f"{base_name}_mixed_audio.mp3")

            # Try advanced ducking first (music ducks during voice)
            log_to_db(channel_id, "info", "assembly", "Using audio ducking for clear voiceover...")
            success = mix_audio_with_ducking(
                concat_vo,
                music_path,
                mixed_audio,
                music_volume_normal=0.12,  # 12% when quiet
                music_volume_ducked=0.06   # 6% during voice
            )

            # Fallback to simple mix if ducking fails
            if not success:
                log_to_db(channel_id, "warning", "assembly", "Advanced ducking failed, using simple mix")
                success = mix_audio_simple_duck(
                    concat_vo,
                    music_path,
                    mixed_audio,
                    music_volume=0.10  # Fixed 10% volume
                )

            if success:
                final_audio = mixed_audio
                log_to_db(channel_id, "info", "assembly", "[OK] Audio mixed with ducking")
            else:
                log_to_db(channel_id, "warning", "assembly", "Audio mixing failed, using voiceover only")

        else:
            log_to_db(channel_id, "info", "assembly", "[OK] Using voiceover only (no music)")

        # =============================================================
        # STEP 7: Merge final audio with video
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 7/7: Creating final video...")

        final_video = os.path.join(output_dir, f"{base_name}_FINAL.mp4")

        result = subprocess.run([
            FFMPEG, '-y',
            '-i', os.path.basename(concat_video),
            '-i', os.path.basename(final_audio),
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            os.path.basename(final_video)
        ], capture_output=True, timeout=180, cwd=output_dir)

        if result.returncode != 0:
            ffmpeg_err = result.stderr.decode()
            log_to_db(channel_id, "error", "assembly", f"FFmpeg final merge failed: {ffmpeg_err}")
            return None, f"Final merge failed: {ffmpeg_err}"

        # Verify file exists and size
        if not os.path.exists(final_video) or os.path.getsize(final_video) < 100000:
            return None, "Final video file invalid"

        # CRITICAL: Verify duration is exactly 45 seconds
        try:
            probe_result = subprocess.run([
                FFPROBE, '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                final_video
            ], capture_output=True, text=True, timeout=10)

            actual_duration = float(probe_result.stdout.strip())
            duration_diff = abs(actual_duration - TOTAL_DURATION)

            log_to_db(channel_id, "info", "assembly", f"Duration check: {actual_duration:.2f}s (target: {TOTAL_DURATION}s)")

            # Allow 0.5s tolerance for encoding variations
            if duration_diff > 0.5:
                log_to_db(channel_id, "warning", "assembly", f"Duration off by {duration_diff:.2f}s - expected {TOTAL_DURATION}s, got {actual_duration:.2f}s")
                # Don't fail, just warn - slight variations are acceptable

        except Exception as e:
            log_to_db(channel_id, "warning", "assembly", f"Could not verify duration: {e}")

        size_mb = os.path.getsize(final_video) / (1024 * 1024)
        log_to_db(channel_id, "info", "assembly", f"[OK] Ranking video complete! Size: {size_mb:.1f}MB")

        return final_video, None

    except Exception as e:
        error_msg = f"Assembly failed: {str(e)}"
        log_to_db(channel_id, "error", "assembly", error_msg)
        return None, error_msg


# ==============================================================================
# Main Generation Function
# ==============================================================================

def generate_ranking_video(channel_config: Dict, use_strategy: bool = True) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Main function to generate a complete ranking video.

    Args:
        channel_config: Channel configuration dict with theme, tone, style, etc.
        use_strategy: If False, ignore AI recommendations (for A/B testing control group)

    Returns: (video_path, title, error_message)
    """
    channel_id = channel_config.get('id', 0)

    try:
        # Step 1: Generate script (with duplicate retry logic)
        log_to_db(channel_id, "info", "generation", "Step 1: Generating ranking script...")

        MAX_RETRIES = 3
        script = None
        error = None

        for attempt in range(1, MAX_RETRIES + 1):
            script, error = generate_ranking_script(
                theme=channel_config.get('theme', 'interesting facts'),
                tone=channel_config.get('tone', 'Exciting'),
                style=channel_config.get('style', 'Fast-paced'),
                channel_id=channel_id,
                use_strategy=use_strategy,
                ranking_count=channel_config.get('ranking_count', 5)
            )

            if script:
                # Success! Non-duplicate script generated
                break

            # Check if error is duplicate
            if error and "Duplicate video detected" in error:
                if attempt < MAX_RETRIES:
                    log_to_db(channel_id, "info", "duplicate", f"Duplicate detected (attempt {attempt}/{MAX_RETRIES}), regenerating...")
                else:
                    log_to_db(channel_id, "error", "duplicate", f"Failed to generate unique video after {MAX_RETRIES} attempts")
            else:
                # Non-duplicate error, don't retry
                break

        if not script:
            return None, None, f"Script generation failed: {error}"

        title = script['title']

        # AI PREDICTIVE SCORING - Check if video should be generated
        log_to_db(channel_id, "info", "ai_prediction", "AI analyzing video potential...")

        # Extract theme from script for prediction
        theme = channel_config.get('theme', 'unknown')
        topic = script.get('ranked_items', [{}])[0].get('title', theme) if script.get('ranked_items') else theme

        should_gen, prediction = should_generate_video(title, topic, channel_id)

        if not should_gen:
            predicted_score = prediction.get('predicted_score', 0)
            reasoning = prediction.get('reasoning', 'Low performance predicted')
            log_to_db(channel_id, "warning", "ai_blocked", f"[STOP] AI BLOCKED: '{title}' - Score {predicted_score}/100")
            log_to_db(channel_id, "info", "ai_blocked", f"Reasoning: {reasoning}")
            return None, None, f"AI blocked video generation: {reasoning} (predicted score: {predicted_score}/100)"

        # Log successful AI approval
        predicted_score = prediction.get('predicted_score', 50)
        predicted_views = prediction.get('predicted_views', 0)
        log_to_db(channel_id, "info", "ai_approved", f"[OK] AI APPROVED: '{title}' - Score {predicted_score}/100 (predicted {predicted_views:.0f} views)")

        log_to_db(channel_id, "info", "generation", f"Step 2: Assembling '{title}'...")

        # Step 2: Assemble video
        video_path, error = assemble_ranking_video(script, channel_config)

        if not video_path:
            return None, None, f"Video assembly failed: {error}"

        return video_path, title, None

    except Exception as e:
        error_msg = f"Ranking video generation failed: {str(e)}"
        log_to_db(channel_id, "error", "generation", error_msg)
        return None, None, error_msg
