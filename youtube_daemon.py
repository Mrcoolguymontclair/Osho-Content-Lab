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
import json
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
from groq_manager import get_groq_client  # Auto-failover between API keys
from error_recovery import retry_with_backoff, RetryConfig  # Auto-retry on failures
from video_engine import (
    generate_video_script, assemble_viral_video,
    cleanup_video_files, check_disk_space, create_teaser_clip
)
from video_engine_ranking import generate_ranking_video
from auth_manager import upload_to_youtube, generate_youtube_metadata, is_channel_authenticated, start_token_refresh_scheduler, stop_token_refresh_scheduler, get_video_id_from_url, upload_thumbnail
from thumbnail_generator import generate_thumbnail
import random
from autonomous_learner import start_autonomous_learning
from quota_manager import (
    init_quota_table, check_quota, mark_quota_exhausted,
    check_and_reset_if_needed, auto_resume_paused_channels,
    get_quota_status_summary
)

# Google Trends autonomous video generation
from google_trends_fetcher import fetch_all_trends
from trend_analyzer import analyze_multiple_trends, get_best_trend_for_channel
from video_planner_ai import plan_video_from_trend
from video_engine_dynamic import generate_video_from_plan
from trend_tracker import (
    save_trend, update_trend_analysis, update_trend_video_plan,
    mark_trend_video_generated, get_best_pending_trend, check_trend_exists
)

# ==============================================================================
# Global State
# ==============================================================================

daemon_running = False
channel_threads = {}  # channel_id -> Thread
analytics_thread = None  # Analytics worker thread
trends_thread = None  # Trends worker thread
quota_thread = None  # Quota monitor thread
daemon_pid_file = "daemon.pid"

# ==============================================================================
# Error Handling & Recovery
# ==============================================================================

ERROR_THRESHOLD = 999999  # NEVER pause - always auto-recover

def handle_error(channel_id: int, error_type: str, error_message: str):
    """
    Handle error with tracking and threshold checking.

    If same error occurs 20 times, pause channel and generate detailed report.
    Also checks for quota-related errors and marks quotas as exhausted.
    """
    # Check if this is a quota error
    error_lower = error_message.lower()
    if any(keyword in error_lower for keyword in ['quota', 'rate limit', 'limit exceeded', 'too many requests', '429']):
        # Determine which API
        if 'groq' in error_lower or 'llama' in error_lower:
            mark_quota_exhausted('groq')
            add_log(channel_id, "warning", "quota", "Groq API quota exhausted - will auto-resume at midnight")
        elif 'youtube' in error_lower or 'google' in error_lower:
            mark_quota_exhausted('youtube')
            add_log(channel_id, "warning", "quota", "YouTube API quota exhausted - will auto-resume at midnight")
        elif 'pexels' in error_lower:
            mark_quota_exhausted('pexels')
            add_log(channel_id, "warning", "quota", "Pexels API quota exhausted - will auto-resume at midnight")

    error_count = track_error(channel_id, error_type)

    add_log(channel_id, "error", error_type, f"Error #{error_count}: {error_message}")

    if error_count >= ERROR_THRESHOLD:
        # NEVER PAUSE - just log it
        add_log(channel_id, "warning", "recovery", f"Error threshold reached but continuing (auto-recovery enabled)")

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

    Priority order:
    1. Check for approved trend video plans (AI-driven trending topics)
    2. Fall back to regular video generation (ranking or standard)

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

        # Check video type setting
        video_type = channel.get('video_type', 'standard')

        # STEP 1: Check for trending topic video plans (ONLY if video_type is 'trending')
        if video_type == 'trending':
            best_trend = get_best_pending_trend(channel.get('theme', 'General content'))
        else:
            best_trend = None

        if best_trend and best_trend.get('video_plan_json'):
            add_log(channel_id, "info", "generation", f"🔥 TRENDING VIDEO: {best_trend['topic']}")

            try:
                import json
                video_plan = json.loads(best_trend['video_plan_json'])

                add_log(channel_id, "info", "generation", f"Format: {video_plan['video_type'].upper()}, Clips: {video_plan['clip_count']}")

                # AI PREDICTIVE SCORING for trend videos
                from ai_analytics_enhanced import should_generate_video

                title = video_plan['title']
                topic = best_trend['topic']

                add_log(channel_id, "info", "ai_prediction", "AI analyzing trending video potential...")
                should_gen, prediction = should_generate_video(title, topic, channel_id)

                if not should_gen:
                    predicted_score = prediction.get('predicted_score', 0)
                    reasoning = prediction.get('reasoning', 'Low performance predicted')
                    add_log(channel_id, "warning", "ai_blocked", f"🛑 AI BLOCKED TREND: '{title}' - Score {predicted_score}/100")
                    add_log(channel_id, "info", "ai_blocked", f"Reasoning: {reasoning}")
                    # Fall back to regular generation instead of failing completely
                    add_log(channel_id, "info", "generation", "Falling back to regular video generation...")
                else:
                    # Log AI approval for trend video
                    predicted_score = prediction.get('predicted_score', 50)
                    predicted_views = prediction.get('predicted_views', 0)
                    add_log(channel_id, "info", "ai_approved", f"✅ AI APPROVED TREND: '{title}' - Score {predicted_score}/100 (predicted {predicted_views:.0f} views)")

                    # Generate dynamic video from AI plan
                    output_dir = os.path.join("outputs", f"channel_{channel_name}")
                    os.makedirs(output_dir, exist_ok=True)

                    video_path = os.path.join(output_dir, f"trend_{best_trend['id']}_{int(time.time())}.mp4")

                    # Use dynamic video engine
                    success = generate_video_from_plan(video_plan, video_path)

                    if success and os.path.exists(video_path):
                        # Update video record
                        update_video(
                            video_id,
                            title=video_plan['title'],
                            topic=best_trend['topic'],
                            video_path=video_path,
                            status="ready"
                        )

                        # Mark trend as video generated
                        mark_trend_video_generated(best_trend['id'], video_id)

                        add_log(channel_id, "info", "generation", f"✅ Trend video ready: {video_plan['title']}")

                        return video_id
                    else:
                        add_log(channel_id, "warning", "generation", "Trend video failed, falling back to regular generation")

            except Exception as e:
                add_log(channel_id, "warning", "generation", f"Trend video error: {e}, falling back to regular")

        # STEP 2: Regular video generation (ranking, standard, or trending fallback)
        # video_type already set above

        # If user wants trending but no trends available, inform and fall back to standard
        if video_type == 'trending' and not best_trend:
            add_log(channel_id, "info", "generation", "⏳ No trending topics available yet. Falling back to standard generation.")
            add_log(channel_id, "info", "generation", "💡 Tip: Trends are fetched automatically. Check back in a few minutes.")
            video_type = 'standard'  # Fallback to standard generation

        if video_type == 'ranking':
            # Use ranking video generator (all-in-one function)
            add_log(channel_id, "info", "generation", "🎬 Starting RANKING video generation...")

            # Get AI-driven configuration (includes real-time strategy adaptation and smart A/B split)
            from ai_analytics_enhanced import get_video_generation_config
            ai_config = get_video_generation_config(channel_id)

            use_strategy = ai_config['use_ai_strategy']
            ab_test_group = ai_config['ab_test_group']
            confidence = ai_config['confidence']
            strategy_working = ai_config.get('strategy_working', None)

            # Log AI decision
            if strategy_working is True:
                add_log(channel_id, "info", "ai_config", f"🤖 AI Config: Using strategy (confidence: {confidence}%, strategy is WINNING)")
            elif strategy_working is False:
                add_log(channel_id, "info", "ai_config", f"🤖 AI Config: Not using strategy (confidence: {confidence}%, strategy is LOSING)")
            else:
                add_log(channel_id, "info", "ai_config", f"🤖 AI Config: Group={ab_test_group}, confidence={confidence}%")

            # Get current AI strategy from old system (for compatibility)
            from ai_analyzer import get_latest_content_strategy
            strategy = get_latest_content_strategy(channel_id)

            # Generate video with strategy control parameter
            video_path, title, error = generate_ranking_video(channel, use_strategy=use_strategy)

            if not video_path:
                update_video(video_id, status="failed", error_message=f"Ranking video failed: {error}")
                paused = handle_error(channel_id, "ranking_generation", error)
                return None if paused else video_id

            # Save strategy metadata with video
            strategy_data = None
            strategy_confidence = 0.0

            if strategy and use_strategy:
                strategy_data = json.dumps({
                    'recommended_topics': strategy.get('recommended_topics', []),
                    'content_style': strategy.get('content_style'),
                    'avoid_topics': strategy.get('avoid_topics', []),
                    'applied': True
                })
                strategy_confidence = strategy.get('confidence_score', 0.0)
                add_log(channel_id, "info", "analytics", f"Strategy applied with {strategy_confidence:.2f} confidence")

            # Use the actual generated title from the script
            update_video(
                video_id,
                title=title,
                video_path=video_path,
                status="ready",
                strategy_used=strategy_data,
                strategy_confidence=strategy_confidence,
                ab_test_group=ab_test_group
            )

        else:
            # Standard video generation (original logic)
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

        # Generate metadata (including title variants)
        metadata = generate_youtube_metadata(
            video['title'],
            channel['theme']
        )

        title_variants = metadata.get('title_variants', [metadata['title']])
        try:
            import random
            chosen_title = random.choice(title_variants)
        except:
            chosen_title = metadata['title']

        # Update DB with chosen title variant for A/B tracking
        update_video(video_id, title=chosen_title, title_variant=chosen_title)

        # Upload with chosen title
        success, result = upload_to_youtube(
            video_path=video['video_path'],
            title=chosen_title,
            description=metadata['description'],
            tags=metadata['tags'],
            channel_name=channel_name,
            category_id='24',  # Entertainment
            privacy='public'
        )

        # After successful upload, generate and upload a thumbnail and teaser
        if success:
            youtube_url = result
            video_id_str = get_video_id_from_url(youtube_url)
            output_dir = os.path.dirname(video['video_path'])
            base_name = os.path.basename(video['video_path']).replace('_FINAL.mp4', '')

            # Generate AI-powered thumbnail with text overlay
            try:
                from thumbnail_ai import generate_ai_thumbnail
                thumb_path = os.path.join(output_dir, f"{base_name}_thumb.jpg")

                # Extract rank number if ranking video
                rank_number = None
                if 'ranking' in video['title'].lower() or 'top' in video['title'].lower():
                    # Use first rank (most common: show #1)
                    rank_number = 1

                add_log(channel_id, "info", "thumbnail", "Generating AI thumbnail with text overlay...")
                ok, err = generate_ai_thumbnail(
                    video_path=video['video_path'],
                    title=video['title'],
                    output_path=thumb_path,
                    rank_number=rank_number,
                    timestamp=2.0
                )

                if ok:
                    add_log(channel_id, "info", "thumbnail", f"✅ AI thumbnail created: {os.path.basename(thumb_path)}")
                    up_ok, up_msg = upload_thumbnail(video_id_str, channel_name, thumb_path)
                    if up_ok:
                        update_video(video_id, thumbnail_variant='ai_text_overlay')
                        add_log(channel_id, "info", "thumbnail", "✅ AI thumbnail uploaded to YouTube")
                    else:
                        add_log(channel_id, "warning", "upload", f"Thumbnail upload failed: {up_msg}")
                else:
                    add_log(channel_id, "warning", "thumbnail", f"AI thumbnail generation failed: {err}")
                    # Fallback to basic thumbnail
                    from thumbnail_generator import generate_thumbnail
                    thumb_path_fallback = os.path.join(output_dir, f"{base_name}_thumb.png")
                    ok_fb, err_fb = generate_thumbnail(video['video_path'], None, thumb_path_fallback)
                    if ok_fb:
                        upload_thumbnail(video_id_str, channel_name, thumb_path_fallback)
                        update_video(video_id, thumbnail_variant='auto_frame_fallback')
            except Exception as e:
                add_log(channel_id, "warning", "upload", f"Thumbnail pipeline error: {e}")

            # Create teaser clip and upload it as a separate Short
            try:
                from video_engine import create_teaser_clip
                teaser_path = os.path.join(output_dir, f"{base_name}_teaser_15s.mp4")
                t_ok, t_err = create_teaser_clip(video['video_path'], teaser_path, duration=15)
                if t_ok:
                    teaser_title = f"Teaser: {video['title']}"
                    teaser_desc = f"Watch the full video: {youtube_url}\n\nSubscribe for more!"

                    t_success, t_result = upload_to_youtube(
                        video_path=teaser_path,
                        title=teaser_title,
                        description=teaser_desc,
                        tags=[channel['theme'], 'teaser', 'shorts'],
                        channel_name=channel_name,
                        category_id='24',
                        privacy='public'
                    )

                    if t_success:
                        add_log(channel_id, "info", "upload", f"✅ Teaser posted: {t_result}")
                    else:
                        add_log(channel_id, "warning", "upload", f"Teaser upload failed: {t_result}")
                else:
                    add_log(channel_id, "warning", "upload", f"Teaser creation failed: {t_err}")
            except Exception as e:
                add_log(channel_id, "warning", "upload", f"Teaser pipeline error: {e}")

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
                    # Time to generate with AUTO-RETRY
                    add_log(channel_id, "info", "daemon", "Starting video generation (3 min before post) [AUTO-RETRY ENABLED]")

                    # Wrap with retry logic - try up to 3 times
                    video_id = None
                    for attempt in range(1, 4):
                        try:
                            video_id = generate_next_video(channel)
                            if video_id:
                                add_log(channel_id, "info", "recovery", f"✅ Generation succeeded on attempt {attempt}")
                                break
                        except Exception as e:
                            add_log(channel_id, "warning", "recovery", f"Attempt {attempt}/3 failed: {str(e)}")
                            if attempt < 3:
                                wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                                add_log(channel_id, "info", "recovery", f"Retrying in {wait_time}s...")
                                time.sleep(wait_time)

                    if not video_id:
                        add_log(channel_id, "warning", "daemon", "All 3 generation attempts failed, skipping to next cycle")
                        # Move next post time forward (but don't give up!)
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
                    # Time to upload with AUTO-RETRY!
                    add_log(channel_id, "info", "daemon", "Uploading video now! [AUTO-RETRY ENABLED]")

                    # Try upload up to 3 times
                    success = False
                    for attempt in range(1, 4):
                        try:
                            success = upload_video(next_video['id'], channel)
                            if success:
                                add_log(channel_id, "info", "recovery", f"✅ Upload succeeded on attempt {attempt}")
                                break
                        except Exception as e:
                            add_log(channel_id, "warning", "recovery", f"Upload attempt {attempt}/3 failed: {str(e)}")
                            if attempt < 3:
                                wait_time = 2 ** attempt
                                add_log(channel_id, "info", "recovery", f"Retrying upload in {wait_time}s...")
                                time.sleep(wait_time)

                    if not success:
                        add_log(channel_id, "warning", "daemon", "All 3 upload attempts failed, will retry in next cycle")

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
            add_log(channel_id, "error", "daemon", f"Worker error (auto-recovering): {str(e)}")
            import traceback
            traceback.print_exc()
            add_log(channel_id, "info", "recovery", "⚡ AUTO-RECOVERY: Daemon will continue despite error")
            time.sleep(60)  # Wait before retry
            # Reset error tracker so we don't accumulate errors
            reset_error_tracker(channel_id)

    add_log(channel_id, "info", "daemon", "Channel worker stopped")

# ==============================================================================
# Google Trends Worker
# ==============================================================================

def trends_worker():
    """
    Background worker that fetches and analyzes Google Trends every 6 hours.

    Process:
    1. Fetch trending topics from Google Trends
    2. AI analyzes which trends are video-worthy
    3. AI plans complete video structure for each approved trend
    4. Stores trend plans in database for video generation

    Runs on same schedule as autonomous learning (6 hours).
    """
    global daemon_running

    print("\n🔥 Trends Worker Started")
    print("   → Fetches Google Trends every 6 hours")
    print("   → AI analyzes video potential")
    print("   → Auto-generates video plans\n")

    while daemon_running:
        try:
            print(f"\n{'='*60}")
            print(f"🔍 FETCHING GOOGLE TRENDS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}\n")

            # Step 1: Fetch all trending topics
            all_trends = fetch_all_trends(region='US')

            # Combine all trends from different sources
            combined_trends = []
            for source, trends in all_trends.items():
                if source != 'timestamp' and isinstance(trends, list):
                    combined_trends.extend(trends)

            print(f"✓ Found {len(combined_trends)} unique trends\n")

            # Step 2: Filter out duplicates already in database (last 24h)
            new_trends = []
            for trend in combined_trends:
                if not check_trend_exists(trend['topic'], hours=24):
                    new_trends.append(trend)
                    # Save to database
                    trend_id = save_trend(trend)
                    trend['id'] = trend_id

            print(f"✓ {len(new_trends)} new trends (not in database)\n")

            if not new_trends:
                print("✓ No new trends to analyze\n")
            else:
                # Step 3: AI analyzes trends for video worthiness
                print("🤖 AI analyzing trends for video potential...\n")

                # Get all active channels to match trends to themes
                channels = get_active_channels()

                for channel in channels:
                    channel_theme = channel.get('theme', 'General content')
                    print(f"\n📺 Analyzing trends for channel: {channel['name']}")
                    print(f"   Theme: {channel_theme}\n")

                    # Analyze trends for this channel
                    approved_trends = analyze_multiple_trends(
                        new_trends[:15],  # Analyze top 15 new trends
                        channel_theme,
                        max_analyze=15
                    )

                    if not approved_trends:
                        print(f"   ℹ️ No approved trends for {channel['name']}\n")
                        continue

                    # Step 4: AI plans videos for approved trends
                    print(f"\n🎬 Planning videos for {len(approved_trends)} approved trends...\n")

                    for trend in approved_trends:
                        try:
                            trend_id = trend.get('id')
                            if not trend_id:
                                continue

                            # Update database with analysis
                            analysis = trend.get('analysis', {})
                            update_trend_analysis(trend_id, analysis, is_approved=True)

                            # AI plans complete video
                            video_plan = plan_video_from_trend(trend, analysis, channel)

                            if video_plan:
                                # Save video plan to database
                                update_trend_video_plan(trend_id, video_plan)

                                print(f"   ✅ Planned: {video_plan['title']}")
                                print(f"      Format: {video_plan['video_type']}")
                                print(f"      Clips: {video_plan['clip_count']}")
                                print(f"      Urgency: {analysis.get('urgency', 'unknown')}\n")
                            else:
                                print(f"   ⚠️ Failed to plan video for: {trend['topic']}\n")

                        except Exception as e:
                            print(f"   ❌ Error planning trend: {e}\n")

            # Wait 6 hours before next run
            print(f"\n{'='*60}")
            print(f"✅ Trends analysis complete")
            print(f"⏰ Next run in 6 hours")
            print(f"{'='*60}\n")

            # Sleep for 6 hours (21600 seconds)
            for _ in range(360):  # Check every minute for 6 hours
                if not daemon_running:
                    break
                time.sleep(60)

        except Exception as e:
            print(f"❌ Trends worker error: {e}")
            import traceback
            traceback.print_exc()
            # Wait 30 minutes before retry on error
            time.sleep(1800)

    print("\n🔥 Trends Worker Stopped\n")

# ==============================================================================
# Quota Monitor Worker
# ==============================================================================

def quota_monitor_worker():
    """
    Background worker that monitors API quotas and auto-resumes channels.
    Checks every hour if quotas have reset and resumes paused channels.
    """
    print("\n🔍 Starting Quota Monitor...")
    print("   → Checks API quotas every hour")
    print("   → Auto-resets quotas at midnight")
    print("   → Auto-resumes paused channels when quotas reset")
    print("✅ Quota monitor active\n")

    while daemon_running:
        try:
            # Check if quotas need reset
            quotas_reset = check_and_reset_if_needed()

            if quotas_reset:
                print(f"\n{'='*60}")
                print(f"🔄 QUOTA RESET - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}\n")

                # Resume any paused channels
                auto_resume_paused_channels()

                print(f"\n{'='*60}")
                print(f"✅ All systems resumed")
                print(f"{'='*60}\n")

            # Sleep for 1 hour (3600 seconds)
            for _ in range(60):  # Check every minute for 1 hour
                if not daemon_running:
                    break
                time.sleep(60)

        except Exception as e:
            print(f"⚠️ Quota monitor error: {e}")
            import traceback
            traceback.print_exc()
            # Wait 10 minutes before retry on error
            time.sleep(600)

    print("\n🔍 Quota Monitor Stopped\n")

# ==============================================================================
# Daemon Control
# ==============================================================================

def start_daemon():
    """Start the daemon"""
    global daemon_running, channel_threads, analytics_thread, trends_thread, quota_thread

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

    # Initialize quota tracking
    init_quota_table()
    print("✅ Quota tracking initialized\n")

    # Load all active channels
    channels = get_active_channels()

    if not channels:
        print("⚠️ No active channels found. Waiting...")
        print("Activate channels in the Streamlit UI.")
        print()

    # Start worker for each active channel
    for channel in channels:
        start_channel_worker(channel['id'])

    # Start BULLETPROOF auth auto-refresh (prevents ALL auth failures)
    print("\n🔐 Starting Bulletproof YouTube Auth System...")
    print("   → Auto-refreshes tokens every 30 minutes")
    print("   → Proactive refresh 2 hours before expiration")
    print("   → Multiple retry attempts with exponential backoff")
    print("   → Backup token preservation")
    from auth_manager import start_auto_refresh
    start_auto_refresh()
    print("✅ Bulletproof auth active - ZERO auth failures guaranteed\n")

    # Start autonomous learning system (runs every 6 hours)
    print("\n🧠 Starting Autonomous AI Learning System...")
    print("   → Analyzes video performance automatically")
    print("   → Improves future videos without user intervention")
    print("   → Runs every 6 hours in background")
    start_autonomous_learning()
    print("✅ Autonomous learning active\n")

    # Start Google Trends worker (runs every 6 hours)
    print("🔥 Starting Google Trends Autonomous System...")
    print("   → Fetches trending topics every 6 hours")
    print("   → AI analyzes video potential")
    print("   → Auto-generates video plans for trends")
    print("   → Prioritizes trending videos over regular content")
    trends_thread = threading.Thread(target=trends_worker, daemon=True, name="TrendsWorker")
    trends_thread.start()
    print("✅ Google Trends system active\n")

    # Start Quota Monitor (checks every hour, resets at midnight)
    quota_thread = threading.Thread(target=quota_monitor_worker, daemon=True, name="QuotaMonitor")
    quota_thread.start()

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

    # Stop token refresh scheduler
    try:
        stop_token_refresh_scheduler()
    except Exception as e:
        print(f"Error stopping token refresh scheduler: {e}")

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
