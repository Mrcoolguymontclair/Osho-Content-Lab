#!/usr/bin/env python3
"""
Harmony Snippets Integration
Extracts the most engaging part of songs for video background music.
"""

import os
import requests
import subprocess
from typing import Optional, Tuple

HARMONY_API_KEY = "hsa_JWGPzfIN_hofP2VWWXmP0bvORvTcVR1cPRZH-gyACuc"
HARMONY_API_URL = "https://www.harmonysnippetsai.com/api/v1/extract-snippet"

def find_ffmpeg() -> str:
    """Find ffmpeg binary"""
    common_paths = [
        '/opt/homebrew/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/usr/bin/ffmpeg',
        'ffmpeg'
    ]

    for path in common_paths:
        if os.path.exists(path) or os.system(f'which {path} > /dev/null 2>&1') == 0:
            return path
    return 'ffmpeg'

FFMPEG = find_ffmpeg()

def get_best_snippet(
    audio_file: str,
    duration: int = 60,
    output_file: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Extract the most engaging snippet from an audio file using Harmony Snippets API.

    Args:
        audio_file: Path to the audio file
        duration: Desired snippet duration in seconds (default 60 for YouTube Shorts)
        output_file: Output path for the snippet (if None, creates one based on input)

    Returns:
        (success, output_path, error_message)
    """

    if not os.path.exists(audio_file):
        return False, None, f"Audio file not found: {audio_file}"

    if output_file is None:
        base = os.path.splitext(audio_file)[0]
        output_file = f"{base}_snippet.mp3"

    try:
        # Check audio duration first
        probe_result = subprocess.run([
            FFMPEG.replace('ffmpeg', 'ffprobe'),
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_file
        ], capture_output=True, text=True, timeout=10)

        total_duration = float(probe_result.stdout.strip())

        # If audio is longer than 2 minutes (120s), trim to 2 minutes from the middle
        upload_file = audio_file
        if total_duration > 120:
            print(f"Audio is {total_duration:.1f}s, trimming to 120s for API...")
            temp_trimmed = audio_file.replace('.mp3', '_temp_trim.mp3')

            # Extract middle 2 minutes
            start_time = (total_duration - 120) / 2

            trim_result = subprocess.run([
                FFMPEG, '-y',
                '-i', audio_file,
                '-ss', str(start_time),
                '-t', '120',
                '-acodec', 'copy',
                temp_trimmed
            ], capture_output=True, timeout=30)

            if trim_result.returncode != 0:
                print("Failed to trim audio, using fallback...")
                return False, None, "Audio trimming failed"

            upload_file = temp_trimmed

        # Upload audio file to Harmony Snippets
        print(f"Uploading to Harmony Snippets AI...")

        with open(upload_file, 'rb') as f:
            files = {'file': (os.path.basename(upload_file), f, 'audio/mpeg')}
            headers = {'X-API-Key': HARMONY_API_KEY}

            response = requests.post(
                HARMONY_API_URL,
                files=files,
                headers=headers,
                timeout=120
            )

        # Clean up temp file if created
        if upload_file != audio_file and os.path.exists(upload_file):
            os.remove(upload_file)

        print(f"Response status: {response.status_code}")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', f'HTTP {response.status_code}')
            except:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            return False, None, f"Harmony API error: {error_msg}"

        # Parse JSON response
        try:
            result = response.json()
        except:
            return False, None, f"Invalid JSON response: {response.text[:200]}"

        if not result.get('success'):
            error_msg = result.get('error', 'Unknown error')
            return False, None, f"API returned error: {error_msg}"

        # Get base64 audio snippet
        snippet_base64 = result.get('data', {}).get('snippet_base64')
        if not snippet_base64:
            return False, None, "No snippet data in response"

        # Decode and save snippet
        import base64
        audio_data = base64.b64decode(snippet_base64)

        # Save as WAV first (from API), then convert to MP3 if needed
        temp_wav = output_file.replace('.mp3', '_temp.wav')
        with open(temp_wav, 'wb') as f:
            f.write(audio_data)

        print(f"[OK] Snippet received from API")

        # Convert WAV to MP3 if output format is MP3
        if output_file.endswith('.mp3'):
            convert_result = subprocess.run([
                FFMPEG, '-y',
                '-i', temp_wav,
                '-acodec', 'libmp3lame',
                '-b:a', '192k',
                output_file
            ], capture_output=True, timeout=30)

            if convert_result.returncode != 0:
                return False, None, f"WAV to MP3 conversion failed: {convert_result.stderr.decode()}"

            # Remove temp WAV
            os.remove(temp_wav)
        else:
            # Just rename if output is WAV
            os.rename(temp_wav, output_file)

        if not os.path.exists(output_file):
            return False, None, "Snippet file not created"

        # Get snippet info
        snippet_duration = result.get('data', {}).get('snippet_duration', duration)
        print(f"[OK] Snippet saved: {snippet_duration}s, saved to: {output_file}")

        return True, output_file, None

    except requests.exceptions.Timeout:
        return False, None, "Harmony API timeout"
    except requests.exceptions.RequestException as e:
        return False, None, f"API request failed: {str(e)}"
    except Exception as e:
        return False, None, f"Snippet extraction failed: {str(e)}"


def get_best_snippet_fallback(
    audio_file: str,
    duration: int = 60,
    output_file: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Fallback method: Extract middle portion of song if Harmony API fails.

    The middle of a song is often the most engaging part (chorus).
    """

    if not os.path.exists(audio_file):
        return False, None, f"Audio file not found: {audio_file}"

    if output_file is None:
        base = os.path.splitext(audio_file)[0]
        output_file = f"{base}_snippet.mp3"

    try:
        # Get total duration of audio file
        probe_result = subprocess.run([
            FFMPEG.replace('ffmpeg', 'ffprobe'),
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_file
        ], capture_output=True, text=True, timeout=10)

        total_duration = float(probe_result.stdout.strip())

        # Start from middle of song
        start_time = max(0, (total_duration - duration) / 2)

        print(f"Using fallback: middle portion starting at {start_time:.1f}s")

        # Extract middle portion
        extract_result = subprocess.run([
            FFMPEG, '-y',
            '-i', audio_file,
            '-ss', str(start_time),
            '-t', str(duration),
            '-acodec', 'copy',
            output_file
        ], capture_output=True, timeout=30)

        if extract_result.returncode != 0:
            return False, None, f"FFmpeg extraction failed: {extract_result.stderr.decode()}"

        return True, output_file, None

    except Exception as e:
        return False, None, f"Fallback extraction failed: {str(e)}"


def extract_music_snippet(
    audio_file: str,
    duration: int = 60,
    output_file: Optional[str] = None,
    use_harmony: bool = True
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Extract the best snippet from an audio file.

    Tries Harmony Snippets API first, falls back to middle portion if that fails.

    Returns:
        (success, output_path, error_message)
    """

    if use_harmony:
        success, path, error = get_best_snippet(audio_file, duration, output_file)
        if success:
            return success, path, error

        print(f"Harmony API failed ({error}), using fallback method...")

    # Fallback to middle portion
    return get_best_snippet_fallback(audio_file, duration, output_file)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python harmony_snippets.py <audio_file> [duration]")
        print("Example: python harmony_snippets.py music/song.mp3 60")
        sys.exit(1)

    audio_file = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60

    success, output, error = extract_music_snippet(audio_file, duration)

    if success:
        print(f"\n[OK] Success! Snippet saved to: {output}")
    else:
        print(f"\n[FAIL] Failed: {error}")
        sys.exit(1)
