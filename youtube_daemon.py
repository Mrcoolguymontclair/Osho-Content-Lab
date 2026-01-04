#!/usr/bin/env python3
"""
YOUTUBE AUTOMATION DAEMON
Background service that runs continuously, managing multiple channels.
Generates videos 30 minutes before scheduled post time and uploads them.

This runs independently from the Streamlit UI.
"""

import os
import sys
import time
import signal
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from channel_manager import (
    get_active_channels, get_channel, update_channel,
    add_video, update_video, get_next_scheduled_video,
    add_log, track_error, reset_error_tracker, get_error_stats
)
from video_engine import (
    generate_video_script, assemble_viral_video,
    cleanup_video_files, check_disk_space
)
from auth_manager import upload_to_youtube, generate_youtube_metadata, is_channel_authenticated
from learning_loop import analytics_worker_24h

# ==============================================================================
# Global State
# ==============================================================================

daemon_running = False
channel_threads = {}  # channel_id -> Thread
analytics_thread = None  # Analytics worker thread
daemon_pid_file = "daemon.pid"

# ==============================================================================
# Error Handling & Recovery
# ==============================================================================

ERROR_THRESHOLD = 20  # Pause channel after 20 identical errors

def handle_error(channel_id: int, error_type: str, error_message: str):
    """
    Handle error with tracking and threshold checking.

    If same error occurs 20 times, pause channel and generate detailed report.
    """
    error_count = track_error(channel_id, error_type)

    add_log(channel_id, "error", error_type, f"Error #{error_count}: {error_message}")

    if error_count >= ERROR_THRESHOLD:
        # Pause channel
        update_channel(channel_id, is_active=False)

        # Generate detailed error report with Groq
        try:
            from groq import Groq
            import toml

            secrets = toml.load('.streamlit/secrets.toml')
            groq_client = Groq(api_key=secrets.get('GROQ_API_KEY'))

            channel = get_channel(channel_id)

            prompt = f"""You are a technical support specialist. This error occurred 20 times in a YouTube automation system:

Error Type: {error_type}
Error Message: {error_message}
Channel: {channel['name']}
Theme: {channel['theme']}

Provide:
1. What caused this error
2. Detailed diagnosis
3. Step-by-step fix instructions for the user
4. Prevention tips

Be specific and technical."""

            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )

            diagnosis = response.choices[0].message.content

            add_log(channel_id, "error", "diagnosis", f"CHANNEL PAUSED - {ERROR_THRESHOLD} errors", diagnosis)

            # Try to send browser notification
            try:
                # This would need implementation in Streamlit UI
                print(f"\n🚨 ALERT: Channel '{channel['name']}' paused due to repeated errors!")
                print(f"Error: {error_type}")
                print(f"See logs for detailed diagnosis.\n")
            except:
                pass

        except Exception as e:
            add_log(channel_id, "error", "diagnosis", f"Could not generate error report: {str(e)}")

        return True  # Channel paused

    return False  # Continue

# ==============================================================================
# Video Generation Pipeline
# ==============================================================================

def generate_next_video(channel: Dict) -> Optional[int]:
    """
    Generate next video for a channel.

    Returns: video_id if successful, None if failed
    """
    channel_id = channel['id']
    channel_name = channel['name']

    add_log(channel_id, "info", "generation", "🎬 Starting video generation...")

    try:
        # Calculate next post time
        now = datetime.now()
        next_post_time = now + timedelta(minutes=channel['post_interval_minutes'])

        # Create video record
        video_id = add_video(
            channel_id=channel_id,
            title="Generating...",
            topic="",
            status="generating",
            scheduled_post_time=next_post_time
        )

        # Step 1: Generate script
        add_log(channel_id, "info", "generation", "Step 1: Generating script...")

        script, error = generate_video_script(channel)

        if not script:
            update_video(video_id, status="failed", error_message=f"Script generation failed: {error}")
            paused = handle_error(channel_id, "script_generation", error)
            if paused:
                return None

            # Retry with simpler prompt
            add_log(channel_id, "warning", "generation", "Retrying with simpler theme...")
            simple_channel = channel.copy()
            simple_channel['theme'] = channel['theme'].split()[0]  # Use first word only

            script, error = generate_video_script(simple_channel)

            if not script:
                return None

        # Update video with script info
        update_video(video_id, title=script['title'], topic=script.get('topic', ''))

        # Step 2: Assemble video
        add_log(channel_id, "info", "generation", f"Step 2: Assembling '{script['title']}'...")

        output_dir = os.path.join("outputs", f"channel_{channel_name}")
        os.makedirs(output_dir, exist_ok=True)

        video_path, error = assemble_viral_video(script, channel, output_dir)

        if not video_path:
            update_video(video_id, status="failed", error_message=f"Assembly failed: {error}")
            paused = handle_error(channel_id, "video_assembly", error)
            return None if paused else video_id

        # Update video with path
        update_video(video_id, video_path=video_path, status="ready")

        add_log(channel_id, "info", "generation", f"✅ Video ready: {os.path.basename(video_path)}")

        # Reset error counter on success
        reset_error_tracker(channel_id, "script_generation")
        reset_error_tracker(channel_id, "video_assembly")

        return video_id

    except Exception as e:
        add_log(channel_id, "error", "generation", f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# ==============================================================================
# Video Upload
# ==============================================================================

def upload_video(video_id: int, channel: Dict) -> bool:
    """
    Upload video to YouTube.

    Returns: True if successful
    """
    channel_id = channel['id']
    channel_name = channel['name']

    video = get_next_scheduled_video(channel_id)
    if not video or video['id'] != video_id:
        add_log(channel_id, "error", "upload", "Video not found or not ready")
        return False

    add_log(channel_id, "info", "upload", f"📤 Uploading: {video['title']}")

    try:
        # Check authentication
        if not is_channel_authenticated(channel_name):
            update_video(video_id, status="failed", error_message="Channel not authenticated")
            add_log(channel_id, "error", "upload", "Channel not authenticated - please authenticate in UI")
            return False

        # Generate metadata
        metadata = generate_youtube_metadata(
            video['title'],
            channel['theme']
        )

        # Upload
        success, result = upload_to_youtube(
            video_path=video['video_path'],
            title=metadata['title'],
            description=metadata['description'],
            tags=metadata['tags'],
            channel_name=channel_name,
            category_id='24',  # Entertainment
            privacy='public'
        )

        if success:
            youtube_url = result

            # Update video
            update_video(
                video_id,
                status="posted",
                youtube_url=youtube_url,
                actual_post_time=datetime.now().isoformat()
            )

            # Update channel
            update_channel(
                channel_id,
                last_post_at=datetime.now().isoformat(),
                next_post_at=(datetime.now() + timedelta(minutes=channel['post_interval_minutes'])).isoformat()
            )

            add_log(channel_id, "info", "upload", f"✅ Posted: {youtube_url}")

            # Cleanup files after successful upload
            try:
                cleanup_video_files(video['video_path'])
                add_log(channel_id, "info", "cleanup", "Cleaned up source files")
            except Exception as e:
                add_log(channel_id, "warning", "cleanup", f"Cleanup failed: {str(e)}")

            # Reset error counters
            reset_error_tracker(channel_id, "upload")

            return True

        else:
            error_msg = result

            # Update video
            update_video(video_id, status="failed", error_message=error_msg)

            # Handle error
            paused = handle_error(channel_id, "upload", error_msg)

            return False

    except Exception as e:
        error_msg = str(e)
        add_log(channel_id, "error", "upload", f"Unexpected error: {error_msg}")
        update_video(video_id, status="failed", error_message=error_msg)
        handle_error(channel_id, "upload", error_msg)
        return False

# ==============================================================================
# Channel Worker Thread
# ==============================================================================

def channel_worker(channel_id: int):
    """
    Worker thread for a single channel.

    Runs continuously:
    1. Calculate next post time
    2. Wait until 30 mins before
    3. Generate video
    4. Wait until exact post time
    5. Upload video
    6. Repeat
    """
    global daemon_running

    add_log(channel_id, "info", "daemon", "Channel worker started")

    while daemon_running:
        try:
            # Reload channel config (may have been updated)
            channel = get_channel(channel_id)

            if not channel or not channel['is_active']:
                add_log(channel_id, "info", "daemon", "Channel deactivated, stopping worker")
                break

            # Calculate timing
            now = datetime.now()

            if channel['next_post_at']:
                next_post_time = datetime.fromisoformat(channel['next_post_at'])
            else:
                next_post_time = now + timedelta(minutes=channel['post_interval_minutes'])
                update_channel(channel_id, next_post_at=next_post_time.isoformat())

            prepare_time = next_post_time - timedelta(minutes=3)

            # Check if we need to generate video
            next_video = get_next_scheduled_video(channel_id)

            if not next_video or next_video['status'] != 'ready':
                # Need to generate video
                if now >= prepare_time:
                    # Time to generate
                    add_log(channel_id, "info", "daemon", "Starting video generation (3 min before post)")

                    video_id = generate_next_video(channel)

                    if not video_id:
                        add_log(channel_id, "warning", "daemon", "Video generation failed, will retry next cycle")
                        # Move next post time forward
                        update_channel(
                            channel_id,
                            next_post_at=(next_post_time + timedelta(minutes=channel['post_interval_minutes'])).isoformat()
                        )
                        time.sleep(60)  # Wait 1 minute before retry
                        continue

                else:
                    # Wait until prepare time
                    wait_seconds = (prepare_time - now).total_seconds()
                    if wait_seconds > 0:
                        add_log(channel_id, "info", "daemon", f"Waiting {wait_seconds/60:.1f} mins until video generation")
                        time.sleep(min(wait_seconds, 60))  # Check every minute
                        continue

            # Video is ready, wait for post time
            next_video = get_next_scheduled_video(channel_id)

            if next_video and next_video['status'] == 'ready':
                if now >= next_post_time:
                    # Time to upload!
                    add_log(channel_id, "info", "daemon", "Uploading video now!")

                    success = upload_video(next_video['id'], channel)

                    if not success:
                        add_log(channel_id, "warning", "daemon", "Upload failed, will retry next cycle")

                    # Always move to next cycle
                    time.sleep(5)
                    continue

                else:
                    # Wait until post time
                    wait_seconds = (next_post_time - now).total_seconds()
                    if wait_seconds > 0:
                        add_log(channel_id, "info", "daemon", f"Video ready! Posting in {wait_seconds/60:.1f} mins")
                        time.sleep(min(wait_seconds, 60))
                        continue

            # Check disk space periodically
            used_percent, free_gb = check_disk_space()
            if used_percent > 90:
                add_log(channel_id, "warning", "system", f"⚠️ Disk space low: {used_percent:.1f}% used, {free_gb:.1f}GB free")

            time.sleep(10)  # Check every 10 seconds

        except Exception as e:
            add_log(channel_id, "error", "daemon", f"Worker error: {str(e)}")
            import traceback
            traceback.print_exc()
            time.sleep(60)  # Wait before retry

    add_log(channel_id, "info", "daemon", "Channel worker stopped")

# ==============================================================================
# Daemon Control
# ==============================================================================

def start_daemon():
    """Start the daemon"""
    global daemon_running, channel_threads, analytics_thread

    # Write PID file
    with open(daemon_pid_file, 'w') as f:
        f.write(str(os.getpid()))

    daemon_running = True

    print("=" * 60)
    print("🚀 YOUTUBE AUTOMATION DAEMON STARTED")
    print("=" * 60)
    print(f"PID: {os.getpid()}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Load all active channels
    channels = get_active_channels()

    if not channels:
        print("⚠️ No active channels found. Waiting...")
        print("Activate channels in the Streamlit UI.")
        print()

    # Start worker for each active channel
    for channel in channels:
        start_channel_worker(channel['id'])

    # Start analytics worker (runs every 24 hours)
    print("\n🧠 Starting AI Analytics worker...")
    analytics_thread = threading.Thread(
        target=analytics_worker_24h,
        args=(lambda: daemon_running,),
        daemon=True
    )
    analytics_thread.start()
    print("✅ Analytics worker started (runs every 24 hours)\n")

    # Monitor loop
    while daemon_running:
        try:
            # Reload active channels (may have changed)
            current_channels = get_active_channels()
            current_ids = {ch['id'] for ch in current_channels}
            running_ids = set(channel_threads.keys())

            # Start new channels
            for channel_id in current_ids - running_ids:
                start_channel_worker(channel_id)

            # Stop removed channels
            for channel_id in running_ids - current_ids:
                stop_channel_worker(channel_id)

            time.sleep(10)  # Check every 10 seconds

        except KeyboardInterrupt:
            print("\n⚠️ Received interrupt signal...")
            stop_daemon()
            break
        except Exception as e:
            print(f"Error in daemon monitor: {e}")
            time.sleep(60)

def start_channel_worker(channel_id: int):
    """Start worker thread for a channel"""
    global channel_threads

    if channel_id in channel_threads:
        return  # Already running

    channel = get_channel(channel_id)
    if not channel:
        return

    thread = threading.Thread(
        target=channel_worker,
        args=(channel_id,),
        daemon=True
    )
    thread.start()

    channel_threads[channel_id] = thread
    print(f"✅ Started worker for channel: {channel['name']}")

def stop_channel_worker(channel_id: int):
    """Stop worker thread for a channel"""
    global channel_threads

    if channel_id in channel_threads:
        # Thread will stop on next iteration when it sees is_active=False
        del channel_threads[channel_id]

        channel = get_channel(channel_id)
        if channel:
            print(f"⏸️  Stopped worker for channel: {channel['name']}")

def stop_daemon():
    """Stop the daemon"""
    global daemon_running

    print("\n" + "=" * 60)
    print("🛑 STOPPING DAEMON...")
    print("=" * 60)

    daemon_running = False

    # Wait for threads to finish
    for thread in channel_threads.values():
        thread.join(timeout=5)

    # Remove PID file
    if os.path.exists(daemon_pid_file):
        os.remove(daemon_pid_file)

    print("✅ Daemon stopped")

def signal_handler(signum, frame):
    """Handle signals (SIGTERM, SIGINT)"""
    stop_daemon()
    sys.exit(0)

# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        start_daemon()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
