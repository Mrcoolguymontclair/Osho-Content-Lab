import streamlit as st
import os
import time
import json
import subprocess
import threading
from datetime import datetime
import requests

from video_gen import (
    generate_theme_variations, generate_script, process_clip,
    generate_voiceover, upload_to_youtube, get_youtube_service,
    complete_youtube_auth, cleanup_old_files, append_history,
    GEMINI_API_KEY, PEXELS_API_KEY, ELEVENLABS_API_KEY, YOUTUBE_CLIENT_SECRET,
    check_keys
)

st.set_page_config(page_title="AutoTube Studio Pro", page_icon="▶", layout="wide")

# --- Debug Sidebar Section ---
with st.sidebar:
    with st.expander("Diagnostic Tool"):
        if st.button("Check API Keys Presence"):
            stats = check_keys()
            for k, v in stats.items():
                if v == "SET": st.success(f"{k}: {v}")
                else: st.error(f"{k}: {v}")
            st.info("If keys are MISSING, ensure they are in the Secrets tab (bottom left).")

# --- UI Setup ---
if 'colors' not in st.session_state:
    st.session_state.colors = {
        'bg_start': '#1a1a2e', 'bg_mid': '#16213e', 'bg_end': '#0f3460',
        'primary': '#9333ea', 'secondary': '#ec4899', 'accent': '#a78bfa',
        'text': '#ffffff', 'success': '#22c55e', 'error': '#ef4444'
    }

c = st.session_state.colors
st.markdown(f"""<style>
.main{{background:linear-gradient(135deg,{c['bg_start']} 0%,{c['bg_mid']} 50%,{c['bg_end']} 100%);}}
.stButton>button{{background:linear-gradient(135deg,{c['primary']} 0%,{c['secondary']} 100%);color:{c['text']};border:none;padding:12px 24px;font-size:16px;font-weight:bold;border-radius:8px;width:100%;transition:all 0.3s;}}
.stButton>button:hover{{transform:scale(1.02);box-shadow:0 0 20px rgba(147,51,234,0.5);}}
h1,h2,h3{{color:{c['accent']};text-shadow:0 0 10px rgba(167,139,250,0.3);}}
.metric-card{{background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;border:1px solid {c['accent']}40;backdrop-filter:blur(10px);}}
.log-entry{{padding:5px;border-bottom:1px solid rgba(255,255,255,0.1);font-family:monospace;font-size:12px;}}
.status-running{{color:#22c55e;font-weight:bold;}}
.status-stopped{{color:#ef4444;font-weight:bold;}}
.status-stalled{{color:#f59e0b;font-weight:bold;}}
.tag-pill{{background:{c['secondary']}40; padding:2px 8px; border-radius:12px; font-size:12px; margin-right:5px;}}
</style>""", unsafe_allow_html=True)

# --- Files ---
SCHED_STATE_FILE = 'scheduler_state.json'
SCHED_LOG_FILE = 'scheduler_log.json'
THEME_LIST_FILE = 'auto_theme_list.json'
HISTORY_FILE = 'video_history.json'

def get_sched_state():
    default_state = {
        'running': False, 'interval_mins': 60, 'last_upload': 0, 
        'general_theme': '', 'youtube_limit_reached': False,
        'staged_video': None, 'staged_metadata': None, 'heartbeat': 0
    }
    if os.path.exists(SCHED_STATE_FILE):
        try:
            with open(SCHED_STATE_FILE, 'r') as f: 
                loaded = json.load(f)
                for k, v in default_state.items():
                    if k not in loaded: loaded[k] = v
                return loaded
        except: pass
    return default_state

def save_sched_state(state):
    with open(SCHED_STATE_FILE, 'w') as f: json.dump(state, f, indent=2)

def get_sched_logs():
    if os.path.exists(SCHED_LOG_FILE):
        try:
            with open(SCHED_LOG_FILE, 'r') as f: return json.load(f).get('entries', [])
        except: pass
    return []

if 'theme_list' not in st.session_state:
    if os.path.exists(THEME_LIST_FILE):
        try:
            with open(THEME_LIST_FILE, 'r') as f: st.session_state.theme_list = json.load(f)
        except: st.session_state.theme_list = []
    else: st.session_state.theme_list = []

def save_theme_list():
    try:
        with open(THEME_LIST_FILE, 'w') as f: json.dump(st.session_state.theme_list, f, indent=2)
    except: pass

with st.sidebar:
    st.header("Configuration")
    for key, name in [(GEMINI_API_KEY, "Gemini 2.0"), (PEXELS_API_KEY, "Pexels"), (ELEVENLABS_API_KEY, "ElevenLabs")]:
        if key: st.success(f"✓ {name} Connected")
        else: st.error(f"✗ {name} Missing")

    st.divider()
    if os.path.exists('credentials/youtube_token.pickle'):
        st.success("✓ YouTube Authorized")
    else:
        if YOUTUBE_CLIENT_SECRET:
            st.warning("YouTube Not Authorized")
            service, error = get_youtube_service()
            if error and error.startswith("AUTHORIZE:"):
                st.info("Click link below:")
                st.link_button("Authorize", error.replace("AUTHORIZE: ", ""))
                auth_code = st.text_input("Code", type="password")
                if st.button("Complete") and auth_code:
                    success, msg = complete_youtube_auth(auth_code)
                    if success: st.success(msg); st.rerun()
        else: st.error("Set YOUTUBE_CLIENT_SECRET")

st.title("AutoTube Studio Pro")
tab1, tab2, tab3 = st.tabs(["Auto Pilot", "Manual Lab", "History"])

with tab1:
    st.header("Control Center")
    state = get_sched_state()

    # FIX 5: Status Calculation with Heartbeat
    time_since_hb = time.time() - state.get('heartbeat', 0)

    status_text = "STOPPED"
    status_class = "status-stopped"

    if state['running']:
        if time_since_hb > 60:
            status_text = "STALLED (No Heartbeat)"
            status_class = "status-stalled"
        else:
            status_text = "RUNNING (Synced)"
            status_class = "status-running"

    if state.get('youtube_limit_reached'):
        status_text = "QUOTA PAUSED"
        status_class = "status-stopped"

    # Metrics
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f"Status: <span class='{status_class}'>{status_text}</span>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        # FIX 2: Countdown Timer Logic
        next_msg = "Paused"
        if state['running']:
            if state.get('staged_video'):
                secs_since = time.time() - state['last_upload']
                secs_interval = state['interval_mins'] * 60
                secs_left = max(0, secs_interval - secs_since)
                if secs_left > 0:
                    next_msg = f"Uploading in {int(secs_left//60)}m {int(secs_left%60)}s"
                else:
                    next_msg = "Uploading NOW..."
            else:
                next_msg = "Generating Next Video..."
        st.markdown(f"Next Action: **{next_msg}**", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        # Quota Display
        quota_val = 0
        try:
            if os.path.exists('daily_quota.json'):
                with open('daily_quota.json', 'r') as f:
                    q = json.load(f)
                    if q.get('date') == datetime.now().strftime("%Y-%m-%d"):
                        quota_val = q.get('count', 0)
        except: pass
        st.markdown(f"Gemini Quota: **{quota_val}/20**", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    sc1, sc2 = st.columns([2, 1])
    with sc1:
        def save_theme():
            state['general_theme'] = st.session_state.theme_input
            save_sched_state(state)
        def save_interval():
            state['interval_mins'] = st.session_state.interval_input
            save_sched_state(state)
        
        new_theme = st.text_input("Replenish Theme", value=state.get('general_theme', ''),
                                  key="theme_input", on_change=save_theme)
        interval = st.number_input("Interval (mins)", min_value=1, value=int(state.get('interval_mins', 60)),
                                   key="interval_input", on_change=save_interval)
    with sc2:
        st.write("##")
        if state['running']:
            if st.button("🟥 STOP SCHEDULER", type="primary"):
                state['running'] = False; save_sched_state(state); st.rerun()
        else:
            if st.button("🟩 START SCHEDULER"):
                state['running'] = True; state['general_theme'] = new_theme; state['interval_mins'] = interval
                state['youtube_limit_reached'] = False; save_sched_state(state); st.rerun()

    # FIX 3: Always Visible Queue
    st.divider()
    st.subheader(f"Upcoming Ideas ({len(st.session_state.theme_list)})")
    
    # Reload theme list from file to ensure it's synced with background process
    if os.path.exists(THEME_LIST_FILE):
        try:
            with open(THEME_LIST_FILE, 'r') as f:
                st.session_state.theme_list = json.load(f)
        except: pass

    if st.session_state.theme_list:
        # Show only top 5 to save space
        for i, t in enumerate(st.session_state.theme_list[:5]):
            st.text(f"{i+1}. {t}")
        if len(st.session_state.theme_list) > 5:
            st.text(f"...and {len(st.session_state.theme_list)-5} more")
    else:
        st.info("Queue is empty. Scheduler will replenish automatically.")

    # Live Logs
    st.subheader("Live Logs")
    logs = get_sched_logs()
    
    # Auto-scroll and clean UI for logs
    log_container = st.container(height=300)
    with log_container:
        if not logs: 
            st.info("Waiting for logs... (Scheduler is checking every 10s)")
        else:
            for log in logs:
                icon = "✅" if log['status'] == 'success' else "❌" if log['status'] == 'error' else "ℹ️"
                if log['status'] == 'running': icon = "🚀"
                elif log['status'] == 'warning': icon = "⚠️"
                
                # Highlight critical errors
                msg_style = "color: #ef4444;" if log['status'] == 'error' else ""
                st.markdown(f"<div class='log-entry' style='{msg_style}'>{log['timestamp']} {icon} {log['message']}</div>", unsafe_allow_html=True)

    # FIX 6: Auto-Refresh Loop
    if state['running']:
        st.empty()
        time.sleep(10) # Reduced for better responsiveness, but enough for background
        st.rerun()

with tab2:
    st.header("Manual Generation")
    c1, c2 = st.columns([3, 1])
    with c1: new_manual_theme = st.text_input("Add specific topic to queue")
    with c2: 
        if st.button("Add to Queue") and new_manual_theme:
            st.session_state.theme_list.insert(0, new_manual_theme)
            save_theme_list(); st.success("Added!"); st.rerun()

with tab3:
    st.header("📜 Published History")
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f: 
                history = json.load(f)
            if not history: 
                st.info("No videos published yet.")
            else:
                for item in history:
                    with st.expander(f"**{item.get('title', 'Untitled')}** - {item.get('timestamp')}"):
                        c1, c2 = st.columns([1, 1])
                        with c1:
                            file_path = item.get('file_path', '')
                            if os.path.exists(file_path):
                                st.video(file_path)
                            else:
                                st.warning("⚠️ Local file expired or missing")
                        with c2:
                            st.write(f"**Theme:** {item.get('theme', 'N/A')}")
                            # Keywords/Tags
                            tags = item.get('tags', [])
                            if tags:
                                st.write("**Keywords:**")
                                tags_html = "".join([f"<span class='tag-pill'>{tag}</span>" for tag in tags])
                                st.markdown(tags_html, unsafe_allow_html=True)
                            
                            st.divider()
                            # Displaying description/metadata for expanded context
                            if 'description' in item:
                                st.write(f"**Description:** {item['description']}")
                            
                            if item.get('youtube_url'):
                                st.link_button("📺 Watch on YouTube", item['youtube_url'])
        except Exception as e:
            st.error(f"Error reading history: {e}")
    else:
        st.info("Upload a video to see")