#!/usr/bin/env python3
"""
COOK UP - On-Demand Video Generator
Instantly generate and upload a YouTube Short without waiting for the daemon schedule.

Usage:
    python cook_up.py                    # Use first active channel
    python cook_up.py --channel "Name"   # Use specific channel
    python cook_up.py --trending         # Use trending topic format
    python cook_up.py --no-upload        # Generate only, don't upload
"""

import os
import sys
import argparse
import time
from datetime import datetime
from typing import Optional, Tuple

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from channel_manager import (
    get_active_channels, get_channel_by_name, add_video,
    update_video, add_log, get_channel
)
from video_engine_ranking_v2 import generate_ranking_video_v2 as generate_ranking_video
from auth_manager import (
    upload_to_youtube, generate_youtube_metadata,
    is_channel_authenticated, get_video_id_from_url
)
from thumbnail_ai import generate_ai_thumbnail
from video_engine import cleanup_video_files

# ANSI color codes for pretty output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_status(emoji: str, message: str, color: str = ""):
    """Print a status message with emoji and color."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {emoji} {message}{RESET}")

def print_header():
    """Print the cook up header."""
    print("\n" + "="*60)
    print(f"{BOLD}{BLUE}🔥 COOK UP - On-Demand Video Generator 🔥{RESET}")
    print("="*60 + "\n")

def get_target_channel(channel_name: Optional[str] = None):
    """Get the target channel for video generation."""
    if channel_name:
        channel = get_channel_by_name(channel_name)
        if not channel:
            print_status("❌", f"Channel '{channel_name}' not found", RED)
            return None
    else:
        # Use first active channel
        active_channels = get_active_channels()
        if not active_channels:
            print_status("❌", "No active channels found", RED)
            return None
        channel = active_channels[0]

    return channel

def generate_video(channel: dict) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Generate a video for the channel.
    Returns: (video_path, title, video_id)
    """
    channel_id = channel['id']
    channel_name = channel['name']

    print_status("🎬", f"Generating video for channel: {BOLD}{channel_name}{RESET}")
    print_status("📝", "Theme: " + channel.get('theme', 'General'))

    # Create video record
    video_id = add_video(
        channel_id=channel_id,
        scheduled_time=datetime.now(),
        status='generating',
        title='Generating...'
    )

    try:
        print_status("🤖", "Selecting viral topic with AI...", YELLOW)

        # Generate ranking video (uses V2 engine with viral topics)
        video_path, title, error = generate_ranking_video(channel, use_strategy=True)

        if not video_path or error:
            print_status("❌", f"Video generation failed: {error}", RED)
            update_video(video_id, status="failed", error_message=error)
            return None, None, video_id

        # Update video record
        update_video(
            video_id,
            title=title,
            video_path=video_path,
            status="ready"
        )

        print_status("✅", f"Video ready: {BOLD}{title}{RESET}", GREEN)
        print_status("📁", f"Path: {video_path}")

        return video_path, title, video_id

    except Exception as e:
        print_status("❌", f"Error during generation: {str(e)}", RED)
        import traceback
        traceback.print_exc()
        update_video(video_id, status="failed", error_message=str(e))
        return None, None, video_id

def upload_video(channel: dict, video_path: str, title: str, video_id: int) -> Optional[str]:
    """
    Upload video to YouTube.
    Returns: YouTube URL or None
    """
    channel_id = channel['id']
    channel_name = channel['name']

    print_status("🔐", "Checking authentication...", YELLOW)

    # Check authentication
    if not is_channel_authenticated(channel_name):
        print_status("❌", "Channel not authenticated!", RED)
        print_status("💡", f"Run: streamlit run new_vid_gen.py")
        print_status("💡", f"Then authenticate '{channel_name}' in the UI")
        return None

    print_status("✅", "Authentication OK", GREEN)
    print_status("📤", "Uploading to YouTube...", YELLOW)

    try:
        # Generate metadata
        metadata = generate_youtube_metadata(title, channel['theme'])

        # Upload video
        success, result = upload_to_youtube(
            video_path=video_path,
            title=title,
            description=metadata['description'],
            tags=metadata['tags'],
            channel_name=channel_name,
            category_id='24',  # Entertainment
            privacy='public'
        )

        if not success:
            print_status("❌", f"Upload failed: {result}", RED)
            update_video(video_id, status="failed", error_message=str(result))
            return None

        youtube_url = result
        video_id_str = get_video_id_from_url(youtube_url)

        print_status("✅", f"Video uploaded: {BOLD}{youtube_url}{RESET}", GREEN)

        # Generate and upload thumbnail
        print_status("🖼️", "Generating AI thumbnail...", YELLOW)

        try:
            output_dir = os.path.dirname(video_path)
            base_name = os.path.basename(video_path).replace('_FINAL.mp4', '')
            thumb_path = os.path.join(output_dir, f"{base_name}_thumb.jpg")

            # Extract rank number for thumbnail
            rank_number = 1  # Default to showing #1

            success = generate_ai_thumbnail(
                video_path=video_path,
                output_path=thumb_path,
                title=title,
                rank_number=rank_number,
                variant='A'  # Use default variant
            )

            if success and os.path.exists(thumb_path):
                from auth_manager import upload_thumbnail
                upload_thumbnail(video_id_str, thumb_path, channel_name)
                print_status("✅", "Thumbnail uploaded", GREEN)
            else:
                print_status("⚠️", "Thumbnail generation failed (video still uploaded)", YELLOW)

        except Exception as e:
            print_status("⚠️", f"Thumbnail error: {e} (video still uploaded)", YELLOW)

        # Update video record with YouTube URL
        update_video(
            video_id,
            youtube_url=youtube_url,
            youtube_id=video_id_str,
            status='posted',
            posted_at=datetime.now()
        )

        return youtube_url

    except Exception as e:
        print_status("❌", f"Upload error: {str(e)}", RED)
        import traceback
        traceback.print_exc()
        return None

def main():
    parser = argparse.ArgumentParser(
        description='Cook up a YouTube Short on demand',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--channel', '-c',
        help='Channel name to use (default: first active channel)'
    )
    parser.add_argument(
        '--no-upload', '-n',
        action='store_true',
        help='Generate video but do not upload'
    )

    args = parser.parse_args()

    print_header()

    # Get target channel
    channel = get_target_channel(args.channel)
    if not channel:
        return 1

    start_time = time.time()

    # Generate video
    video_path, title, video_id = generate_video(channel)
    if not video_path:
        print_status("❌", "Failed to generate video", RED)
        return 1

    generation_time = time.time() - start_time
    print_status("⏱️", f"Generation took {generation_time:.1f} seconds")

    # Upload unless --no-upload flag is set
    if not args.no_upload:
        print()
        youtube_url = upload_video(channel, video_path, title, video_id)

        if youtube_url:
            total_time = time.time() - start_time
            print()
            print("="*60)
            print_status("🎉", f"{BOLD}SUCCESS!{RESET}", GREEN)
            print_status("🔗", f"YouTube URL: {BOLD}{youtube_url}{RESET}", GREEN)
            print_status("⏱️", f"Total time: {total_time:.1f} seconds")
            print("="*60 + "\n")
            return 0
        else:
            print_status("❌", "Upload failed", RED)
            return 1
    else:
        print()
        print("="*60)
        print_status("✅", f"{BOLD}Video generated (not uploaded){RESET}", GREEN)
        print_status("📁", f"Path: {video_path}")
        print("="*60 + "\n")
        return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_status("\n⚠️", "Interrupted by user", YELLOW)
        sys.exit(1)
    except Exception as e:
        print_status("❌", f"Unexpected error: {e}", RED)
        import traceback
        traceback.print_exc()
        sys.exit(1)
