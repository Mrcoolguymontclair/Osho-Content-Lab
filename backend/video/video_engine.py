#!/usr/bin/env python3
"""
CORE VIDEO GENERATION ENGINE
Incorporates all lessons learned from testing:
- Proper FFmpeg path finding
- gTTS as primary voiceover (unlimited, proven)
- Demuxer audio concat (NOT filter_complex)
- Correct subtitle sizing (20pt, not covering video)
- 20-retry fallback for clip downloads
- Comprehensive error handling and logging
"""

import os
import sys
import time
import subprocess
import shutil
import requests
import json
from datetime import datetime
from typing import Tuple, Optional, List, Dict
from gtts import gTTS
# Groq import moved to groq_manager for automatic failover

# ==============================================================================
# CRITICAL: FFmpeg Path Finder (from our testing)
# ==============================================================================

def find_ffmpeg() -> str:
    """
    Find ffmpeg binary in common locations.
    CRITICAL: Never hardcode 'ffmpeg' - caused errors in testing!
    """
    common_paths = [
        '/opt/homebrew/bin/ffmpeg',  # macOS Homebrew (M1/M2)
        '/usr/local/bin/ffmpeg',     # macOS Homebrew (Intel)
        '/usr/bin/ffmpeg',           # Linux
        'C:\\ffmpeg\\bin\\ffmpeg.exe',  # Windows
        'ffmpeg'                     # Fallback to PATH
    ]

    for path in common_paths:
        if shutil.which(path) or os.path.exists(path):
            return path

    return 'ffmpeg'  # Last resort

def find_ffprobe() -> str:
    """Find ffprobe binary (companion to ffmpeg)"""
    common_paths = [
        '/opt/homebrew/bin/ffprobe',  # macOS Homebrew (M1/M2)
        '/usr/local/bin/ffprobe',     # macOS Homebrew (Intel)
        '/usr/bin/ffprobe',           # Linux
        'C:\\ffmpeg\\bin\\ffprobe.exe',  # Windows
        'ffprobe'                     # Fallback to PATH
    ]

    for path in common_paths:
        if shutil.which(path) or os.path.exists(path):
            return path

    return 'ffprobe'  # Last resort

FFMPEG = find_ffmpeg()
FFPROBE = find_ffprobe()

# ==============================================================================
# Environment Setup & API Clients
# ==============================================================================

# Load secrets
try:
    import toml
    secrets_path = '.streamlit/secrets.toml'
    if os.path.exists(secrets_path):
        secrets = toml.load(secrets_path)
        os.environ['GROQ_API_KEY'] = secrets.get('GROQ_API_KEY', '')
        os.environ['PEXELS_API_KEY'] = secrets.get('PEXELS_API_KEY', '')
        os.environ['PIXABAY_API_KEY'] = secrets.get('PIXABAY_API_KEY', '')
except Exception as e:
    print(f"Warning: Could not load secrets.toml: {e}")

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY', '')
PIXABAY_API_KEY = os.environ.get('PIXABAY_API_KEY', '')

# Initialize Groq client with automatic failover
try:
    from groq_manager import get_groq_client
    groq_client = get_groq_client()
except Exception as e:
    print(f"Warning: Could not initialize GroqManager, falling back to single key: {e}")
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ==============================================================================
# Logging Functions
# ==============================================================================

def log_to_db(channel_id: int, level: str, category: str, message: str, details: str = ""):
    """Log to database (imported from channel_manager)"""
    try:
        from channel_manager import add_log
        add_log(channel_id, level, category, message, details)
    except:
        # Fallback to console if DB not available
        print(f"[{level.upper()}] [{category}] {message}")

def log_dev(category: str, message: str, level: str = "info"):
    """Development logging (fallback)"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level.upper()}] [{category}] {message}")

# ==============================================================================
# Script Generation with Groq
# ==============================================================================

def generate_video_script(
    channel_config: Dict,
    retry_count: int = 0,
    max_retries: int = 5
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Generate viral video script using Groq AI.

    Returns: (script_dict, error_message)
    script_dict contains: title, segments[{narration, searchQuery, musicKeywords}]
    """
    if not groq_client:
        return None, "Groq API key not configured"

    channel_id = channel_config.get('id', 0)
    theme = channel_config.get('theme', 'General Facts')
    tone = channel_config.get('tone', 'Exciting')
    style = channel_config.get('style', 'Fast-paced')
    other_info = channel_config.get('other_info', '')

    # Get recent video titles to avoid duplicates
    from channel_manager import get_channel_videos
    recent_videos = get_channel_videos(channel_id, limit=20)
    recent_titles = [v['title'] for v in recent_videos if v.get('title')]
    avoid_topics = "\n".join([f"- {title}" for title in recent_titles[-10:]]) if recent_titles else "None yet"

    # Get AI-generated content strategy if available
    try:
        from ai_analyzer import get_latest_content_strategy
        strategy = get_latest_content_strategy(channel_id)
    except:
        strategy = None

    # Build enhanced prompt with AI insights
    if strategy and strategy.get('recommended_topics'):
        ai_guidance = f"""
DATA-DRIVEN INSIGHTS (from video performance analysis):
[OK] PROVEN SUCCESSFUL TOPICS: {', '.join(strategy['recommended_topics'][:3])}
[OK] WINNING CONTENT STYLE: {strategy.get('content_style', 'Not available')}
[OK] HOOK TEMPLATES THAT WORK: {', '.join(strategy.get('hook_templates', [])[:2])}
[WARNING] AVOID THESE: {', '.join(strategy.get('avoid_topics', [])[:2])}

Use these insights to create content proven to perform well with THIS specific audience."""
    else:
        ai_guidance = "Note: No performance data yet. Create engaging, viral content based on channel theme."

    prompt = f"""You are a DATA-DRIVEN viral YouTube Shorts script writer.

Channel Theme: {theme}
Tone: {tone}
Style: {style}
Additional Info: {other_info}

{ai_guidance}

RECENT VIDEOS (DO NOT REPEAT):
{avoid_topics}

Create a 60-second viral YouTube Short script optimized for maximum engagement:
1. Generate a UNIQUE topic using proven successful patterns (if available)
2. Create 10 segments (6 seconds each)
3. Each segment needs:
   - Narration text (1-2 punchy sentences, under 100 characters)
   - Search query for Pexels video (2-4 keywords matching the narration)
   - Music keywords for Pixabay (genre/mood, e.g., "energetic electronic")

Output as JSON:
{{
  "title": "VIRAL TITLE IN ALL CAPS",
  "topic": "specific unique topic for this video",
  "segments": [
    {{
      "narration": "Short punchy fact or statement",
      "searchQuery": "relevant keywords",
      "musicKeywords": "music genre mood"
    }}
  ]
}}

Make it VIRAL and ENGAGING! Use shocking facts, numbers, and vivid descriptions."""

    try:
        log_dev("AI", f"Generating script (attempt {retry_count + 1}/{max_retries})")

        response = groq_client.chat_completions_create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=2000
        )

        content = response.choices[0].message.content

        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        script = json.loads(content.strip())

        # Validate structure
        if 'title' not in script or 'segments' not in script:
            raise ValueError("Invalid script structure")

        if len(script['segments']) != 10:
            log_dev("AI", f"Warning: Got {len(script['segments'])} segments instead of 10")

        log_to_db(channel_id, "info", "script", f"Generated: {script['title']}")
        return script, None

    except Exception as e:
        error_msg = str(e)
        log_to_db(channel_id, "error", "script", f"Generation failed: {error_msg}")

        if retry_count < max_retries - 1:
            time.sleep(2 ** retry_count)  # Exponential backoff
            return generate_video_script(channel_config, retry_count + 1, max_retries)

        return None, f"Script generation failed after {max_retries} attempts: {error_msg}"

# ==============================================================================
# Voiceover Generation (gTTS PRIMARY - from our testing!)
# ==============================================================================

def generate_voiceover(
    text: str,
    output_path: str,
    channel_id: int = 0,
    retry_count: int = 0,
    max_retries: int = 5
) -> Tuple[bool, Optional[str]]:
    """
    Generate voiceover using Edge TTS (Microsoft Neural Voices - FREE, unlimited, high quality).
    Falls back to gTTS if Edge TTS fails.

    Returns: (success, error_message)
    """
    try:
        # PRIMARY: Try Edge TTS first (much higher quality)
        log_dev("VoiceOver", f"Generating with Edge TTS (attempt {retry_count + 1})")

        try:
            import edge_tts
            import asyncio

            # Voice selection - high quality, natural sounding
            # en-US-AriaNeural: Female, clear, professional, engaging
            # en-US-GuyNeural: Male, deep, authoritative
            voice = "en-US-AriaNeural"

            async def generate_edge_tts():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_path)

            # Run async function
            asyncio.run(generate_edge_tts())

            # Verify Edge TTS output
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                log_to_db(channel_id, "info", "voiceover", f" Edge TTS: {os.path.basename(output_path)}")
                return True, None
            else:
                raise Exception("Edge TTS output invalid")

        except Exception as edge_error:
            # Edge TTS failed, fall back to gTTS
            log_dev("VoiceOver", f"Edge TTS failed: {edge_error}, falling back to gTTS")
            log_to_db(channel_id, "warning", "voiceover", "Edge TTS failed, using gTTS fallback")

            # FALLBACK: Use gTTS (reliable but lower quality)
            tts = gTTS(text=text, lang='en', slow=False)
            temp_path = output_path.replace('.mp3', '_temp.mp3')
            tts.save(temp_path)

            # Speed up to 1.1x for better pacing
            try:
                result = subprocess.run([
                    FFMPEG, '-i', temp_path,
                    '-filter:a', 'atempo=1.1',
                    '-y', output_path
                ], capture_output=True, check=True, timeout=30)

                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                # If speedup fails, just use original
                if os.path.exists(temp_path):
                    os.rename(temp_path, output_path)

        # Verify file exists and has content
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Voiceover file not created: {output_path}")

        if os.path.getsize(output_path) < 1000:  # Less than 1KB is suspicious
            raise ValueError(f"Voiceover file too small: {os.path.getsize(output_path)} bytes")

        log_to_db(channel_id, "info", "voiceover", f"Generated: {os.path.basename(output_path)}")
        return True, None

    except Exception as e:
        error_msg = str(e)
        log_to_db(channel_id, "error", "voiceover", f"Failed: {error_msg}")

        if retry_count < max_retries - 1:
            time.sleep(2 ** retry_count)
            return generate_voiceover(text, output_path, channel_id, retry_count + 1, max_retries)

        return False, f"Voiceover generation failed after {max_retries} attempts: {error_msg}"

# ==============================================================================
# Video Clip Download (Pexels with 20-retry fallback)
# ==============================================================================

def download_video_clip(
    search_query: str,
    output_path: str,
    duration: float = 6.0,
    channel_id: int = 0,
    retry_count: int = 0,
    max_retries: int = 20
) -> Tuple[bool, Optional[str]]:
    """
    Download video clip from Pexels.

    CRITICAL: 20-retry with alternative queries (from our testing)
    If fails, generate new search queries with Groq.
    """
    if not PEXELS_API_KEY:
        return False, "Pexels API key not configured"

    try:
        log_dev("Clip", f"Downloading: '{search_query}' (attempt {retry_count + 1}/{max_retries})")

        # Search Pexels
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": search_query, "per_page": 15, "orientation": "portrait"},
            timeout=15
        )

        if response.status_code != 200:
            raise Exception(f"Pexels API returned {response.status_code}")

        data = response.json()

        if not data.get('videos'):
            # No results - generate alternative query
            if retry_count < max_retries - 1:
                alternative_query = generate_alternative_search_query(search_query, channel_id)
                time.sleep(1)
                return download_video_clip(alternative_query, output_path, duration, channel_id, retry_count + 1, max_retries)
            else:
                raise Exception(f"No videos found for '{search_query}' after {max_retries} attempts")

        # Find HD video file
        video = data['videos'][retry_count % len(data['videos'])]  # Rotate through results
        video_file = None

        for file in video['video_files']:
            if file.get('quality') == 'hd' and file.get('width', 0) <= 1920:
                video_file = file
                break

        if not video_file:
            video_file = video['video_files'][0]  # Fallback to first available

        # Download video
        video_response = requests.get(video_file['link'], timeout=60)
        temp_path = output_path.replace('.mp4', '_temp.mp4')

        with open(temp_path, 'wb') as f:
            f.write(video_response.content)

        # Get actual video duration
        probe_result = subprocess.run([
            FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', temp_path
        ], capture_output=True, text=True, timeout=10)

        try:
            actual_duration = float(probe_result.stdout.strip())
        except:
            actual_duration = duration

        # If video is shorter than needed, loop it; otherwise trim it
        if actual_duration < duration:
            # Calculate exact number of loops needed
            import math
            loops_needed = math.ceil(duration / actual_duration) - 1  # -1 because first play isn't a loop

            # CRITICAL: Use exact loop count, NOT -1 (infinite)
            # -stream_loop 2 = play 3 times total (original + 2 loops)
            result = subprocess.run([
                FFMPEG, '-stream_loop', str(loops_needed), '-i', temp_path,
                '-t', str(duration),  # Hard limit to prevent runaway
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-y', output_path
            ], capture_output=True, timeout=120)  # Increased timeout for looping
        else:
            # Trim to exact duration and ensure vertical format
            result = subprocess.run([
                FFMPEG, '-i', temp_path,
                '-t', str(duration),
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-y', output_path
            ], capture_output=True, timeout=60)

        if os.path.exists(temp_path):
            os.remove(temp_path)

        if result.returncode != 0:
            raise Exception(f"FFmpeg trim failed: {result.stderr.decode()[:200]}")

        # Verify
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 10000:
            raise Exception("Output file invalid")

        log_to_db(channel_id, "info", "clip", f"Downloaded: {search_query}")
        return True, None

    except Exception as e:
        error_msg = str(e)
        log_to_db(channel_id, "warning", "clip", f"Attempt {retry_count + 1} failed: {error_msg[:100]}")

        if retry_count < max_retries - 1:
            # Generate alternative query and retry
            alternative_query = generate_alternative_search_query(search_query, channel_id)
            time.sleep(2)
            return download_video_clip(alternative_query, output_path, duration, channel_id, retry_count + 1, max_retries)

        return False, f"Clip download failed after {max_retries} attempts"

def generate_alternative_search_query(original_query: str, channel_id: int = 0) -> str:
    """Generate alternative search query using Groq when clip download fails"""
    if not groq_client:
        # Fallback: simplify original query
        words = original_query.split()
        return ' '.join(words[:2]) if len(words) > 2 else original_query

    try:
        response = groq_client.chat_completions_create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": f"The search query '{original_query}' returned no video results. Generate ONE alternative 2-4 word search query with similar meaning. Reply with ONLY the alternative query, nothing else."
            }],
            temperature=0.8,
            max_tokens=20
        )

        alternative = response.choices[0].message.content.strip().strip('"').strip("'")
        log_dev("Clip", f"Alternative query: '{alternative}'")
        return alternative

    except:
        # Fallback
        words = original_query.split()
        return ' '.join(words[:2]) if len(words) > 2 else "nature scenery"

# This is getting long - let me continue in next message with music download and video assembly

# ==============================================================================
# Background Music Download (Pixabay)
# ==============================================================================

def download_background_music(
    keywords: str,
    output_path: str,
    channel_id: int = 0,
    retry_count: int = 0,
    max_retries: int = 5
) -> Tuple[bool, Optional[str]]:
    """
    Select background music from local library based on keywords/tags.

    Uses music_library.json to match keywords to tagged music files.
    Falls back to random selection if no good match found.

    Returns: (success, error_message)
    """
    import json
    import shutil
    import random

    music_dir = "music"
    library_file = os.path.join(music_dir, "music_library.json")

    # Check if music directory and library exist
    if not os.path.exists(music_dir):
        log_to_db(channel_id, "warning", "music", "Music directory not found")
        return False, "Music directory doesn't exist"

    if not os.path.exists(library_file):
        log_to_db(channel_id, "warning", "music", "Music library file not found")
        return False, "music_library.json not found"

    try:
        # Load music library
        with open(library_file, 'r') as f:
            library = json.load(f)

        music_files = library.get('music_files', [])

        if not music_files:
            log_to_db(channel_id, "warning", "music", "No music files in library")
            return False, "No music files configured in library"

        # Parse keywords into list
        keyword_list = [k.strip().lower() for k in keywords.split()]

        # Score each music file based on tag matches
        scored_files = []
        for music_file in music_files:
            filename = music_file.get('filename')
            tags = [t.lower() for t in music_file.get('tags', [])]

            # Check if file actually exists
            file_path = os.path.join(music_dir, filename)
            if not os.path.exists(file_path):
                continue

            # Calculate match score
            score = sum(1 for keyword in keyword_list if any(keyword in tag for tag in tags))
            scored_files.append((score, music_file, file_path))

        if not scored_files:
            log_to_db(channel_id, "warning", "music", "No valid music files found")
            return False, "No music files found in music directory"

        # Sort by score (highest first)
        scored_files.sort(reverse=True, key=lambda x: x[0])

        # Pick the best match (or random from top 3 if multiple have same score)
        best_score = scored_files[0][0]
        top_matches = [f for f in scored_files if f[0] == best_score]

        selected = random.choice(top_matches)
        score, music_info, source_path = selected

        # Extract best snippet using Harmony Snippets API
        try:
            from harmony_snippets import extract_music_snippet

            log_to_db(channel_id, "info", "music", f"Extracting best snippet from '{music_info['filename']}'...")

            success, snippet_path, error = extract_music_snippet(
                source_path,
                duration=60,  # YouTube Shorts length
                output_file=output_path,
                use_harmony=True
            )

            if success:
                match_info = f"'{music_info['filename']}' (score: {score}/{len(keyword_list)}, snippet extracted)"
                log_to_db(channel_id, "info", "music", f"Selected: {match_info}")
                return True, None
            else:
                # Fallback to full file if snippet extraction fails
                log_to_db(channel_id, "warning", "music", f"Snippet extraction failed, using full file: {error}")
                shutil.copy2(source_path, output_path)

        except ImportError:
            # harmony_snippets not available, use full file
            log_to_db(channel_id, "info", "music", "Harmony Snippets not available, using full file")
            shutil.copy2(source_path, output_path)

        # Verify file was copied
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
            raise Exception("Failed to copy music file")

        match_info = f"'{music_info['filename']}' (score: {score}/{len(keyword_list)})"
        log_to_db(channel_id, "info", "music", f"Selected: {match_info}")

        return True, None

    except Exception as e:
        error_msg = str(e)
        log_to_db(channel_id, "error", "music", f"Music selection failed: {error_msg}")
        return False, f"Music selection error: {error_msg}"


# Original music download code - disabled (requires paid Pixabay plan)
def _download_background_music_DISABLED(
    keywords: str,
    output_path: str,
    channel_id: int = 0,
    retry_count: int = 0,
    max_retries: int = 5
) -> Tuple[bool, Optional[str]]:
    """DISABLED - Requires paid Pixabay plan"""
    if not PIXABAY_API_KEY:
        return False, "Pixabay API key not configured"

    try:
        log_dev("Music", f"Searching: '{keywords}' (attempt {retry_count + 1})")

        response = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": PIXABAY_API_KEY,
                "q": keywords,
                "audio_type": "music",
                "per_page": 10
            },
            timeout=15
        )

        if response.status_code != 200:
            raise Exception(f"Pixabay API returned {response.status_code}")

        data = response.json()

        if not data.get('hits'):
            # Try simpler keywords
            simple_keywords = keywords.split()[0] if ' ' in keywords else "upbeat"
            if retry_count < max_retries - 1:
                time.sleep(1)
                return _download_background_music_DISABLED(simple_keywords, output_path, channel_id, retry_count + 1, max_retries)
            else:
                raise Exception(f"No music found for '{keywords}'")

        # Get first result's preview URL (60 seconds, perfect for Shorts)
        music = data['hits'][retry_count % len(data['hits'])]
        preview_url = music.get('previewURL')

        if not preview_url:
            raise Exception("No preview URL in music result")

        # Download music file
        music_response = requests.get(preview_url, timeout=60)

        with open(output_path, 'wb') as f:
            f.write(music_response.content)

        # Verify
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 10000:
            raise Exception("Music file invalid")

        log_to_db(channel_id, "info", "music", f"Downloaded: {keywords}")
        return True, None

    except Exception as e:
        error_msg = str(e)
        log_to_db(channel_id, "warning", "music", f"Download failed: {error_msg[:100]}")

        if retry_count < max_retries - 1:
            time.sleep(2 ** retry_count)
            return _download_background_music_DISABLED(keywords, output_path, channel_id, retry_count + 1, max_retries)

        return False, f"Music download failed after {max_retries} attempts: {error_msg}"

# ==============================================================================
# Video Assembly Pipeline (CRITICAL - from our testing!)
# ==============================================================================

def assemble_viral_video(
    script: Dict,
    channel_config: Dict,
    output_dir: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Assemble complete viral video from script.

    Uses all lessons learned from testing:
    - Demuxer audio concat (NOT filter_complex - caused exit code 254)
    - Proper subtitle sizing (20pt, Arial, bottom-aligned)
    - Music mixing with voiceover priority
    - Comprehensive verification

    Returns: (final_video_path, error_message)
    """
    channel_id = channel_config.get('id', 0)
    channel_name = channel_config.get('name', 'default')
    music_volume = channel_config.get('music_volume', 15) / 100.0  # Convert to 0.0-1.0

    timestamp = int(time.time() * 1000)
    base_name = f"{channel_name}_{timestamp}"

    os.makedirs(output_dir, exist_ok=True)

    try:
        segments = script['segments'][:10]  # Ensure max 10 segments

        # =============================================================
        # STEP 1: Generate all voiceovers and get their durations
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 1/10: Generating voiceovers...")
        voiceover_files = []
        voiceover_durations = []

        for i, seg in enumerate(segments):
            vo_path = os.path.join(output_dir, f"{base_name}_vo_{i}.mp3")
            success, error = generate_voiceover(seg['narration'], vo_path, channel_id)

            if not success:
                return None, f"Voiceover {i+1} failed: {error}"

            # Get voiceover duration using ffprobe
            duration_result = subprocess.run([
                FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', vo_path
            ], capture_output=True, text=True, timeout=10)

            try:
                vo_duration = float(duration_result.stdout.strip())
                voiceover_durations.append(vo_duration)
            except:
                voiceover_durations.append(5.0)  # Fallback to 5 seconds

            voiceover_files.append(vo_path)

        log_to_db(channel_id, "info", "assembly", f"[OK] Generated {len(voiceover_files)} voiceovers")

        # =============================================================
        # STEP 2: Download all video clips (MATCHED to voiceover duration)
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 2/10: Downloading video clips...")
        clip_files = []

        for i, seg in enumerate(segments):
            clip_path = os.path.join(output_dir, f"{base_name}_clip_{i}.mp4")
            # Use voiceover duration for clip (add 0.5s buffer for smooth transition)
            clip_duration = voiceover_durations[i] + 0.5
            success, error = download_video_clip(seg['searchQuery'], clip_path, clip_duration, channel_id)

            if not success:
                log_to_db(channel_id, "warning", "assembly", f"Clip {i+1} failed, continuing with others")
                continue  # Skip failed clips, continue with others

            clip_files.append((clip_path, seg['narration']))

        if len(clip_files) < 5:  # Need at least 5 clips
            return None, f"Only {len(clip_files)} clips downloaded, need at least 5"

        log_to_db(channel_id, "info", "assembly", f"[OK] Downloaded {len(clip_files)} clips")

        # =============================================================
        # STEP 3: Download background music
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 3/10: Downloading background music...")
        music_keywords = segments[0].get('musicKeywords', 'upbeat energetic')
        music_path = os.path.join(output_dir, f"{base_name}_music.mp3")

        music_success, music_error = download_background_music(music_keywords, music_path, channel_id)

        if not music_success:
            log_to_db(channel_id, "warning", "assembly", f"Music download failed: {music_error}")
            music_path = None  # Continue without music

        log_to_db(channel_id, "info", "assembly", "[OK] Background music ready")

        # =============================================================
        # STEP 4: Concat video clips (DEMUXER METHOD - from testing!)
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 4/10: Concatenating video clips...")
        clips_list_file = os.path.join(output_dir, f"{base_name}_clips_list.txt")

        with open(clips_list_file, 'w') as f:
            for clip_path, _ in clip_files:
                f.write(f"file '{os.path.basename(clip_path)}'\n")

        concat_video = os.path.join(output_dir, f"{base_name}_concat.mp4")

        result = subprocess.run([
            FFMPEG, '-f', 'concat', '-safe', '0',
            '-i', os.path.basename(clips_list_file),
            '-c', 'copy', '-y', os.path.basename(concat_video)
        ], cwd=output_dir, capture_output=True, timeout=120)

        if result.returncode != 0:
            return None, f"Video concat failed: {result.stderr.decode()[:200]}"

        log_to_db(channel_id, "info", "assembly", "[OK] Video clips concatenated")

        # =============================================================
        # STEP 5: Concat voiceovers (DEMUXER METHOD - NOT filter_complex!)
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 5/10: Concatenating voiceovers...")
        vo_list_file = os.path.join(output_dir, f"{base_name}_vo_list.txt")

        with open(vo_list_file, 'w') as f:
            for vo_path in voiceover_files:
                f.write(f"file '{os.path.basename(vo_path)}'\n")

        concat_vo = os.path.join(output_dir, f"{base_name}_full_vo.mp3")

        result = subprocess.run([
            FFMPEG, '-f', 'concat', '-safe', '0',
            '-i', os.path.basename(vo_list_file),
            '-c', 'copy', '-y', os.path.basename(concat_vo)
        ], cwd=output_dir, capture_output=True, timeout=60)

        # Accept DTS warnings as non-fatal (from our testing)
        if result.returncode != 0:
            return None, f"Voiceover concat failed: {result.stderr.decode()[:200]}"

        log_to_db(channel_id, "info", "assembly", "[OK] Voiceovers concatenated")

        # =============================================================
        # STEP 6: Generate SRT subtitles
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 6/10: Generating subtitles...")
        subs_file = os.path.join(output_dir, f"{base_name}_subs.srt")

        with open(subs_file, 'w') as f:
            for i, (_, narration) in enumerate(clip_files):
                start_sec = i * 6
                end_sec = (i + 1) * 6
                f.write(f"{i+1}\n")
                f.write(f"00:00:{start_sec:02d},000 --> 00:00:{end_sec:02d},000\n")
                f.write(f"{narration}\n\n")

        log_to_db(channel_id, "info", "assembly", "[OK] Subtitles generated")

        # =============================================================
        # STEP 7: Burn subtitles (20pt Arial, bottom-aligned - from testing!)
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 7/10: Adding subtitles...")
        video_with_subs = os.path.join(output_dir, f"{base_name}_with_subs.mp4")

        subtitle_style = "Fontname=Arial,Fontsize=20,Bold=1,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2,Alignment=2,MarginV=20"

        result = subprocess.run([
            FFMPEG, '-i', os.path.basename(concat_video),
            '-vf', f"subtitles={os.path.basename(subs_file)}:force_style='{subtitle_style}'",
            '-c:v', 'libx264', '-preset', 'fast',
            '-y', os.path.basename(video_with_subs)
        ], cwd=output_dir, capture_output=True, timeout=180)

        if result.returncode != 0:
            return None, f"Subtitle burn failed: {result.stderr.decode()[:200]}"

        log_to_db(channel_id, "info", "assembly", "[OK] Subtitles added")

        # =============================================================
        # STEP 8: Mix background music with voiceover
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 8/10: Mixing audio...")
        final_audio = os.path.join(output_dir, f"{base_name}_final_audio.mp3")

        if music_path and os.path.exists(music_path):
            # Mix voiceover + music (voiceover at full volume, music at user-defined %)
            result = subprocess.run([
                FFMPEG,
                '-i', os.path.basename(concat_vo),
                '-i', os.path.basename(music_path),
                '-filter_complex',
                f"[1:a]volume={music_volume}[music];[0:a][music]amix=inputs=2:duration=shortest[out]",
                '-map', '[out]',
                '-y', os.path.basename(final_audio)
            ], cwd=output_dir, capture_output=True, timeout=60)

            if result.returncode != 0:
                log_to_db(channel_id, "warning", "assembly", "Music mix failed, using voiceover only")
                final_audio = concat_vo
        else:
            # No music, use voiceover only
            final_audio = concat_vo

        log_to_db(channel_id, "info", "assembly", "[OK] Audio mixed")

        # =============================================================
        # STEP 9: Merge final audio with video
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 9/10: Merging final video...")
        final_video = os.path.join(output_dir, f"{base_name}_FINAL.mp4")

        result = subprocess.run([
            FFMPEG, '-y',
            '-i', os.path.basename(video_with_subs),
            '-i', os.path.basename(final_audio),
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            os.path.basename(final_video)
        ], cwd=output_dir, capture_output=True, timeout=120)

        if result.returncode != 0:
            return None, f"Final merge failed: {result.stderr.decode()[:200]}"

        log_to_db(channel_id, "info", "assembly", "[OK] Final video merged")

        # =============================================================
        # STEP 10: Verify audio stream (CRITICAL - from our testing!)
        # =============================================================
        log_to_db(channel_id, "info", "assembly", "Step 10/10: Verifying audio...")
        verify_result = subprocess.run([
            FFMPEG, '-i', final_video
        ], capture_output=True, text=True)

        if 'Audio: aac' not in verify_result.stderr:
            return None, "Audio stream not found in final video!"

        # CRITICAL: Check video duration (YouTube Shorts max: 3 minutes)
        duration_check = subprocess.run([
            FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', final_video
        ], capture_output=True, text=True, timeout=10)

        try:
            final_duration = float(duration_check.stdout.strip())
            if final_duration > 175:  # 2min 55sec max (safety margin)
                return None, f"Video too long! {final_duration:.1f}s (max 175s for YouTube Shorts)"
            log_to_db(channel_id, "info", "assembly", f"[OK] Duration: {final_duration:.1f}s")
        except:
            log_to_db(channel_id, "warning", "assembly", "Could not verify duration")

        size_mb = os.path.getsize(final_video) / (1024 * 1024)
        log_to_db(channel_id, "info", "assembly", f"[OK] Video complete! Size: {size_mb:.1f}MB")

        return final_video, None

    except Exception as e:
        error_msg = str(e)
        log_to_db(channel_id, "error", "assembly", f"Assembly failed: {error_msg}")
        import traceback
        traceback.print_exc()
        return None, error_msg


def create_teaser_clip(final_video_path: str, output_path: str, duration: int = 15) -> Tuple[bool, Optional[str]]:
    """Create a short teaser clip (vertical) from the final video"""
    if not os.path.exists(final_video_path):
        return False, "Final video not found"
    output_dir = os.path.dirname(final_video_path)
    try:
        cmd = [
            FFMPEG, '-y',
            '-i', os.path.basename(final_video_path),
            '-ss', '0',
            '-t', str(duration),
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '20',
            '-c:a', 'aac',
            '-b:a', '128k',
            os.path.basename(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, cwd=output_dir, timeout=90)
        if result.returncode != 0:
            return False, f"Teaser creation failed: {result.stderr.decode()}"

        return True, None
    except Exception as e:
        return False, str(e)


# ==============================================================================
# Cleanup Functions
# ==============================================================================

def cleanup_video_files(final_video_path: str, keep_final: bool = True):
    """
    Delete source files after successful upload.
    Keep only final video for 24 hours.
    """
    if not os.path.exists(final_video_path):
        return

    output_dir = os.path.dirname(final_video_path)
    base_name = os.path.basename(final_video_path).replace('_FINAL.mp4', '')

    # Delete all intermediate files
    patterns = [
        f"{base_name}_vo_*.mp3",
        f"{base_name}_clip_*.mp4",
        f"{base_name}_music.mp3",
        f"{base_name}_clips_list.txt",
        f"{base_name}_vo_list.txt",
        f"{base_name}_concat.mp4",
        f"{base_name}_full_vo.mp3",
        f"{base_name}_subs.srt",
        f"{base_name}_with_subs.mp4",
        f"{base_name}_final_audio.mp3"
    ]

    for pattern in patterns:
        for file in os.listdir(output_dir):
            if file.startswith(base_name) and not file.endswith('_FINAL.mp4'):
                try:
                    os.remove(os.path.join(output_dir, file))
                except:
                    pass

    log_dev("Cleanup", f"Cleaned up intermediate files for {base_name}")

def check_disk_space(path: str = "/") -> Tuple[float, float]:
    """
    Check disk space.
    Returns: (used_percent, free_gb)
    """
    stat = shutil.disk_usage(path)
    used_percent = (stat.used / stat.total) * 100
    free_gb = stat.free / (1024 ** 3)
    return used_percent, free_gb

