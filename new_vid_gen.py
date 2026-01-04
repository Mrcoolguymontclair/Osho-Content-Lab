#!/usr/bin/env python3
"""
MULTI-CHANNEL YOUTUBE AUTOMATION - STREAMLIT UI
Main interface for managing multiple YouTube channels with automated viral video posting.

Features:
- Multi-channel management
- YouTube authentication for multiple accounts
- Live logs and status monitoring
- Schedule configuration per channel
- Fully autonomous operation
"""

import streamlit as st
import os
import sys
import time
import subprocess
from datetime import datetime, timedelta
import pandas as pd

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from channel_manager import (
    get_all_channels, get_channel, add_channel, update_channel, delete_channel,
    activate_channel, deactivate_channel, get_channel_videos, get_channel_logs,
    get_channel_stats, init_database
)
from auth_manager import (
    authenticate_channel, is_channel_authenticated, revoke_channel_auth,
    get_youtube_channel_info, get_token_path
)

# ==============================================================================
# Page Config
# ==============================================================================

st.set_page_config(
    page_title="YouTube Automation Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
init_database()

# Custom CSS to hide balloons/fireworks and customize loading indicator
st.markdown("""
<style>
    /* Hide the default Streamlit balloons/confetti */
    [data-testid="stStatusWidget"] {
        display: none;
    }

    /* Customize the running indicator in top right */
    .stApp > header [data-testid="stDecoration"] {
        display: none;
    }

    /* Make spinner cleaner */
    .stSpinner > div {
        border-color: #ff4b4b transparent transparent transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# Daemon Control Functions
# ==============================================================================

def is_daemon_running() -> bool:
    """Check if daemon is running"""
    if not os.path.exists("daemon.pid"):
        return False

    try:
        with open("daemon.pid", 'r') as f:
            pid = int(f.read().strip())

        # Check if process exists
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        # PID file exists but process doesn't
        if os.path.exists("daemon.pid"):
            os.remove("daemon.pid")
        return False

def start_daemon() -> bool:
    """Start the daemon process"""
    if is_daemon_running():
        return False

    try:
        # Start daemon in background
        subprocess.Popen(
            [sys.executable, "youtube_daemon.py"],
            stdout=open("daemon_stdout.log", "w"),
            stderr=open("daemon_stderr.log", "w"),
            cwd=os.getcwd()
        )

        time.sleep(2)  # Wait for daemon to start
        return is_daemon_running()
    except Exception as e:
        st.error(f"Failed to start daemon: {e}")
        return False

def stop_daemon() -> bool:
    """Stop the daemon process"""
    if not os.path.exists("daemon.pid"):
        return True

    try:
        with open("daemon.pid", 'r') as f:
            pid = int(f.read().strip())

        os.kill(pid, 15)  # SIGTERM
        time.sleep(1)

        # Force kill if still running
        try:
            os.kill(pid, 0)
            os.kill(pid, 9)  # SIGKILL
        except OSError:
            pass

        if os.path.exists("daemon.pid"):
            os.remove("daemon.pid")

        return True
    except Exception as e:
        st.error(f"Failed to stop daemon: {e}")
        return False

# ==============================================================================
# UI Components
# ==============================================================================

def render_channel_card(channel: dict):
    """Render a channel card on the home page"""
    with st.container():
        col1, col2, col3 = st.columns([3, 2, 2])

        with col1:
            st.markdown(f"### 🎬 {channel['name']}")
            st.caption(f"Theme: {channel['theme']}")

        with col2:
            if channel['is_active']:
                st.success("● ACTIVE")
                if channel['next_post_at']:
                    next_post = datetime.fromisoformat(channel['next_post_at'])
                    time_until = next_post - datetime.now()
                    if time_until.total_seconds() > 0:
                        mins = int(time_until.total_seconds() / 60)
                        st.caption(f"Next post in: {mins} mins")
                    else:
                        st.caption("Posting soon...")
            else:
                st.warning("○ PAUSED")

        with col3:
            if st.button("View", key=f"view_{channel['id']}"):
                st.session_state.current_channel = channel['id']
                st.rerun()

        # Recent video
        videos = get_channel_videos(channel['id'], limit=1)
        if videos:
            vid = videos[0]
            if vid['youtube_url']:
                st.caption(f"Last: [{vid['title'][:40]}...]({vid['youtube_url']})")

        st.divider()

def render_log_entry(log: dict):
    """Render a single log entry"""
    timestamp = datetime.fromisoformat(log['timestamp']).strftime("%H:%M:%S")
    level = log['level'].upper()

    # Color coding
    if level == 'ERROR':
        color = "🔴"
    elif level == 'WARNING':
        color = "🟡"
    else:
        color = "🔵"

    st.text(f"{color} [{timestamp}] [{log['category']}] {log['message']}")

# ==============================================================================
# Pages
# ==============================================================================

def home_page():
    """Home page - channel overview"""
    st.title("🎬 YouTube Automation Studio")
    st.markdown("### Multi-Channel Viral Content Engine")

    # Daemon status
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if is_daemon_running():
            st.success("✅ Automation Engine RUNNING")
        else:
            st.error("⚠️ Automation Engine STOPPED")

    with col2:
        if st.button("🚀 Start Engine"):
            if start_daemon():
                st.success("Started!")
                st.rerun()
            else:
                st.error("Failed to start")

    with col3:
        if st.button("🛑 Stop Engine"):
            if stop_daemon():
                st.success("Stopped!")
                st.rerun()
            else:
                st.error("Failed to stop")

    st.divider()

    # Channels
    channels = get_all_channels()

    if not channels:
        st.info("No channels yet. Create your first channel to get started!")

        with st.expander("➕ Create New Channel"):
            create_channel_form()
    else:
        # Show channels
        st.markdown("### Your Channels")

        for channel in channels:
            render_channel_card(channel)

        # Add new channel
        with st.expander("➕ Add New Channel"):
            create_channel_form()

def create_channel_form():
    """Form to create a new channel"""
    with st.form("new_channel_form"):
        name = st.text_input("Channel Name", placeholder="e.g., Science Facts Daily")
        theme = st.text_input("Theme/Niche", placeholder="e.g., Mind-blowing Science Facts")
        tone = st.text_input("Tone", value="Exciting", placeholder="e.g., Exciting, Calm, Dramatic")
        style = st.text_input("Style", value="Fast-paced", placeholder="e.g., Fast-paced, Educational")
        other_info = st.text_area("Additional Info (Optional)", placeholder="Any other context for the AI...")

        col1, col2 = st.columns(2)
        with col1:
            interval = st.number_input("Post Interval (minutes)", min_value=5, value=60)
        with col2:
            music_vol = st.slider("Music Volume % (Currently Disabled)", 0, 100, 0, disabled=True, help="Music requires paid Pixabay plan. Videos work great without it!")

        submitted = st.form_submit_button("Create Channel")

        if submitted:
            if not name or not theme:
                st.error("Name and Theme are required!")
            else:
                success, message = add_channel(
                    name=name,
                    theme=theme,
                    tone=tone,
                    style=style,
                    other_info=other_info,
                    post_interval_minutes=interval,
                    music_volume=music_vol
                )

                if success:
                    st.success(message)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(message)

def channel_page(channel_id: int):
    """Individual channel page"""
    channel = get_channel(channel_id)

    if not channel:
        st.error("Channel not found")
        if st.button("← Back to Home"):
            st.session_state.current_channel = None
            st.rerun()
        return

    # Header
    col1, col2 = st.columns([4, 1])

    with col1:
        st.title(f"🎬 {channel['name']}")

    with col2:
        if st.button("← Home"):
            st.session_state.current_channel = None
            st.rerun()

    # Status bar
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if channel['is_active']:
            st.success("● ACTIVE")
        else:
            st.warning("○ PAUSED")

    with col2:
        stats = get_channel_stats(channel_id)
        st.metric("Posted", stats['posted_videos'])

    with col3:
        if is_channel_authenticated(channel['name']):
            st.success("✓ Authenticated")
        else:
            st.error("✗ Not Authenticated")
            st.caption("👉 See Settings tab")

    with col4:
        if channel['next_post_at']:
            next_post = datetime.fromisoformat(channel['next_post_at'])
            time_until = next_post - datetime.now()
            if time_until.total_seconds() > 0:
                mins = int(time_until.total_seconds() / 60)
                st.info(f"Next: {mins}m")

    st.divider()

    # Manual tab selection using session state
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "Settings"

    # Tab buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("⚙️ Settings", use_container_width=True, type="primary" if st.session_state.active_tab == "Settings" else "secondary"):
            st.session_state.active_tab = "Settings"
            st.rerun()
    with col2:
        if st.button("📊 Status & Logs", use_container_width=True, type="primary" if st.session_state.active_tab == "Status" else "secondary"):
            st.session_state.active_tab = "Status"
            st.rerun()
    with col3:
        if st.button("🎥 Videos", use_container_width=True, type="primary" if st.session_state.active_tab == "Videos" else "secondary"):
            st.session_state.active_tab = "Videos"
            st.rerun()
    with col4:
        if st.button("📈 Analytics", use_container_width=True, type="primary" if st.session_state.active_tab == "Analytics" else "secondary"):
            st.session_state.active_tab = "Analytics"
            st.rerun()

    st.divider()

    # Render selected tab
    if st.session_state.active_tab == "Settings":
        render_settings_tab(channel)
    elif st.session_state.active_tab == "Status":
        render_status_tab(channel)
    elif st.session_state.active_tab == "Videos":
        render_videos_tab(channel)
    elif st.session_state.active_tab == "Analytics":
        render_analytics_tab(channel)

def render_settings_tab(channel: dict):
    """Channel settings tab"""
    st.markdown("### Channel Settings")

    with st.form("channel_settings"):
        col1, col2 = st.columns(2)

        with col1:
            theme = st.text_input("Theme/Niche", value=channel['theme'])
            tone = st.text_input("Tone", value=channel['tone'])
            style = st.text_input("Style", value=channel['style'])

        with col2:
            interval = st.number_input("Post Interval (minutes)", min_value=5, value=channel['post_interval_minutes'])
            music_vol = st.slider("Music Volume % (Disabled)", 0, 100, 0, disabled=True, help="Music requires paid Pixabay plan")

        other_info = st.text_area("Additional Info", value=channel.get('other_info', ''))

        submitted = st.form_submit_button("💾 Save Settings")

        if submitted:
            update_channel(
                channel['id'],
                theme=theme,
                tone=tone,
                style=style,
                other_info=other_info,
                post_interval_minutes=interval,
                music_volume=music_vol
            )
            st.success("Settings saved!")
            time.sleep(1)
            st.rerun()

    st.divider()

    # YouTube Authentication
    st.markdown("### 🔐 YouTube Authentication")

    channel_name = channel['name']

    if is_channel_authenticated(channel_name):
        st.success(f"✅ Channel '{channel_name}' is authenticated!")

        # Show channel info
        with st.spinner("Loading channel info..."):
            info = get_youtube_channel_info(channel_name)

            if info:
                st.markdown(f"**YouTube Channel:** {info['title']}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Subscribers", info['subscribers'])
                with col2:
                    st.metric("Views", info['views'])
                with col3:
                    st.metric("Videos", info['videos'])

        if st.button("🔓 Revoke Authentication"):
            revoke_channel_auth(channel_name)
            st.success("Authentication revoked")
            st.rerun()
    else:
        st.warning("⚠️ Not authenticated with YouTube")
        st.info("Click below to authenticate. This will open your browser for Google login.")

        if st.button("🔐 Authenticate with YouTube", type="primary"):
            with st.spinner("Opening browser for authentication..."):
                success, message = authenticate_channel(channel_name)

                if success:
                    st.success(message)
                    update_channel(channel['id'], token_file=get_token_path(channel_name))
                    st.rerun()
                else:
                    st.error(message)

    st.divider()

    # Controls
    col1, col2, col3 = st.columns(3)

    with col1:
        if channel['is_active']:
            if st.button("⏸️ Pause Channel", use_container_width=True):
                deactivate_channel(channel['id'])
                st.success("Channel paused")
                st.rerun()
        else:
            if st.button("▶️ Activate Channel", use_container_width=True):
                if not is_channel_authenticated(channel['name']):
                    st.error("Please authenticate YouTube first (see above)!")
                else:
                    activate_channel(channel['id'])
                    st.success("Channel activated!")
                    st.rerun()

    with col2:
        if st.button("🗑️ Delete Channel", use_container_width=True, type="secondary"):
            if st.session_state.get('confirm_delete'):
                delete_channel(channel['id'])
                st.success("Channel deleted")
                st.session_state.current_channel = None
                st.rerun()
            else:
                st.session_state.confirm_delete = True
                st.warning("Click again to confirm deletion")

def render_status_tab(channel: dict):
    """Status and logs tab"""
    st.markdown("### Live Status")

    # Current activity
    if channel['is_active']:
        from channel_manager import get_next_scheduled_video

        next_vid = get_next_scheduled_video(channel['id'])

        if next_vid:
            if next_vid['status'] == 'generating':
                st.info("🎬 Currently generating video...")
            elif next_vid['status'] == 'ready':
                st.success(f"✅ Next video ready: '{next_vid['title']}'")
                if next_vid['scheduled_post_time']:
                    post_time = datetime.fromisoformat(next_vid['scheduled_post_time'])
                    st.caption(f"Scheduled to post at: {post_time.strftime('%H:%M:%S')}")
        else:
            st.info("Waiting to generate next video...")
    else:
        st.warning("Channel is paused")

    st.divider()

    # Live logs
    st.markdown("### Live Logs")

    logs = get_channel_logs(channel['id'], limit=100)

    if not logs:
        st.info("No logs yet")
    else:
        # Reverse to show newest first
        for log in reversed(logs[-20:]):  # Show last 20 logs
            render_log_entry(log)

    # Auto-refresh
    if st.button("🔄 Refresh Logs"):
        st.rerun()

    # Auto-refresh every 5 seconds if active
    if channel['is_active']:
        time.sleep(5)
        st.rerun()

def render_videos_tab(channel: dict):
    """Videos history tab"""
    st.markdown("### 📅 Upcoming Videos")

    # Get upcoming/ready videos
    videos = get_channel_videos(channel['id'], limit=100)
    upcoming = [v for v in videos if v['status'] in ['ready', 'generating'] and v.get('scheduled_post_time')]

    if upcoming:
        st.markdown("**Next videos scheduled to post:**")
        for vid in sorted(upcoming, key=lambda x: x.get('scheduled_post_time', ''))[:5]:
            scheduled = datetime.fromisoformat(vid['scheduled_post_time'])
            time_until = scheduled - datetime.now()

            if time_until.total_seconds() > 0:
                mins = int(time_until.total_seconds() / 60)
                status_icon = '🎬' if vid['status'] == 'generating' else '✅'
                st.info(f"{status_icon} **{vid['title'][:60]}...** - Posts in {mins} minutes ({scheduled.strftime('%I:%M %p')})")
            else:
                st.success(f"⏰ **{vid['title'][:60]}...** - Ready to post!")
    else:
        if channel['is_active']:
            st.info("Next video will be generated 3 minutes before scheduled post time")
        else:
            st.warning("Channel is paused - activate it to start generating videos")

    st.divider()
    st.markdown("### 🎥 Posted Videos")

    # Get posted videos
    posted = [v for v in videos if v['status'] == 'posted']

    if not posted:
        st.info("No videos posted yet")
        return

    # Create clean display
    for vid in posted[:20]:  # Show last 20 posted
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            if vid['youtube_url']:
                st.markdown(f"**[{vid['title'][:60]}...]({vid['youtube_url']})**")
            else:
                st.markdown(f"**{vid['title'][:60]}...**")

        with col2:
            post_time = datetime.fromisoformat(vid['actual_post_time']) if vid.get('actual_post_time') else None
            if post_time:
                st.caption(f"Posted: {post_time.strftime('%m/%d %I:%M %p')}")

        with col3:
            if vid['youtube_url']:
                st.markdown(f"[🔗 Watch]({vid['youtube_url']})")

        st.divider()

def render_analytics_tab(channel: dict):
    """Analytics & AI Insights tab"""
    st.markdown("### 📈 Video Performance Analytics")

    # Import analytics functions
    try:
        from learning_loop import get_analytics_summary, force_analytics_update
        from ai_analyzer import get_latest_content_strategy
    except ImportError as e:
        st.error(f"Analytics modules not available: {e}")
        return

    # Refresh button at the top
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**AI-powered insights from your video performance**")
    with col2:
        if st.button("🔄 Refresh Analytics", type="primary", use_container_width=True):
            with st.spinner("Updating analytics from YouTube..."):
                success = force_analytics_update(channel['id'])
                if success:
                    st.success("✅ Analytics updated!")
                    st.rerun()
                else:
                    st.error("Failed to update analytics")

    st.divider()

    # Get analytics summary
    summary = get_analytics_summary(channel['id'])

    if not summary or summary['total_videos'] == 0:
        st.info("📊 No analytics data yet. Post some videos and check back!")
        st.markdown("""
        **What you'll see here once you have data:**
        - Total views, likes, and engagement metrics
        - Best and worst performing videos
        - Growth trends over time
        - AI-discovered success patterns
        - Data-driven content recommendations
        """)
        return

    # Performance Overview
    st.markdown("### 📊 Performance Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Videos", f"{summary['total_videos']}")
    with col2:
        st.metric("Total Views", f"{summary['total_views']:,}")
    with col3:
        st.metric("Total Likes", f"{summary['total_likes']:,}")
    with col4:
        st.metric("Avg Engagement", f"{summary['avg_engagement']:.2f}%")

    # Growth Trend
    st.markdown(f"**Trend:** {summary['growth_trend']}")

    st.divider()

    # Best & Worst Performers
    st.markdown("### 🏆 Performance Highlights")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🌟 Best Performer**")
        if summary['best_video']:
            best = summary['best_video']
            st.success(f"**{best['title'][:50]}...**")
            st.markdown(f"- 👁️ Views: {best.get('views', 0):,}")
            st.markdown(f"- 👍 Likes: {best.get('likes', 0):,}")
            st.markdown(f"- 💬 Comments: {best.get('comments', 0):,}")
            if best.get('youtube_url'):
                st.markdown(f"[🔗 Watch Video]({best['youtube_url']})")

    with col2:
        st.markdown("**📉 Needs Improvement**")
        if summary['worst_video']:
            worst = summary['worst_video']
            st.warning(f"**{worst['title'][:50]}...**")
            st.markdown(f"- 👁️ Views: {worst.get('views', 0):,}")
            st.markdown(f"- 👍 Likes: {worst.get('likes', 0):,}")
            st.markdown(f"- 💬 Comments: {worst.get('comments', 0):,}")
            if worst.get('youtube_url'):
                st.markdown(f"[🔗 Watch Video]({worst['youtube_url']})")

    st.divider()

    # AI Content Strategy
    st.markdown("### 🧠 AI-Discovered Insights")

    strategy = get_latest_content_strategy(channel['id'])

    if not strategy:
        st.info("🤖 Analyzing your videos... Check back after posting a few videos for AI insights!")
    else:
        # Confidence Score
        confidence = strategy.get('confidence_score', 0.5) * 100
        st.markdown(f"**Confidence Score:** {confidence:.0f}% (based on {summary['total_videos']} videos)")

        st.divider()

        # Recommended Topics
        if strategy.get('recommended_topics'):
            st.markdown("#### ✅ Recommended Topics (Data-Driven)")
            st.success("These topics are proven to perform well with your audience:")
            for i, topic in enumerate(strategy['recommended_topics'][:5], 1):
                st.markdown(f"{i}. {topic}")

        st.divider()

        # Content Style
        if strategy.get('content_style'):
            st.markdown("#### 🎨 Optimal Content Style")
            st.info(strategy['content_style'])

        # Pacing Suggestions
        if strategy.get('pacing_suggestions'):
            st.markdown("#### ⏱️ Pacing Recommendations")
            st.info(strategy['pacing_suggestions'])

        st.divider()

        # Hook Templates
        if strategy.get('hook_templates'):
            st.markdown("#### 🎣 Winning Hook Formats")
            st.success("These opening hooks work best for your channel:")
            for hook in strategy['hook_templates']:
                st.markdown(f"- {hook}")

        st.divider()

        # Avoid Topics
        if strategy.get('avoid_topics'):
            st.markdown("#### ⚠️ Topics to Avoid")
            st.warning("These performed below average:")
            for topic in strategy['avoid_topics']:
                st.markdown(f"- {topic}")

    st.divider()

    # How AI is improving content
    st.markdown("### 🔄 Continuous Improvement")
    st.markdown("""
    **How the AI learning loop works:**
    1. 📊 Every 24 hours, fetch latest stats from YouTube API
    2. 🧠 Analyze patterns in successful vs unsuccessful videos
    3. 📈 Generate data-driven content strategy
    4. 🎬 Future videos automatically use these insights
    5. 🔁 Repeat to continuously improve

    Your videos are getting smarter over time! 🚀
    """)

# ==============================================================================
# Main App
# ==============================================================================

def main():
    """Main app entry point"""
    # Initialize session state
    if 'current_channel' not in st.session_state:
        st.session_state.current_channel = None

    # Route to appropriate page - ONLY render one
    if st.session_state.current_channel is not None:
        channel_page(st.session_state.current_channel)
    else:
        home_page()

if __name__ == "__main__":
    main()
