# How to Run Your YouTube Content Lab

**Last Updated:** 2026-01-04

---

## Quick Start (2 Steps)

### 1. Start the Web Interface (Streamlit UI)

Open your terminal and run:

```bash
streamlit run /Users/owenshowalter/CODE/Osho-Content-Lab/new_vid_gen.py
```

**What this does:**
- Opens your web browser automatically
- Shows the dashboard at `http://localhost:8501`
- Lets you manage channels, settings, and analytics
- You can manually generate videos from here

**To stop it:**
- Press `Ctrl + C` in the terminal

---

### 2. Start the Automation Daemon (Background Video Generation)

In a **separate** terminal window, run:

```bash
python3 /Users/owenshowalter/CODE/Osho-Content-Lab/youtube_daemon.py
```

**What this does:**
- Runs in the background continuously
- Automatically generates videos based on your schedule
- Posts videos to YouTube at scheduled times
- Runs 24-hour analytics updates
- Handles multiple channels simultaneously

**To stop it:**
- Press `Ctrl + C` in the terminal
- Or run: `pkill -f youtube_daemon.py`

---

## Full Workflow

### First Time Setup

1. **Start the Streamlit UI:**
   ```bash
   streamlit run new_vid_gen.py
   ```

2. **Configure Your Channel:**
   - Go to "⚙️ Settings" tab
   - Add channel name, theme, tone, style
   - Set posting schedule
   - Authenticate with YouTube

3. **Start the Daemon:**
   ```bash
   python3 youtube_daemon.py
   ```

4. **Everything is automated now!**
   - Videos generate 3 minutes before scheduled post time
   - Videos upload automatically
   - Analytics update every 24 hours

---

## Running Both at the Same Time

**Option 1: Two Terminal Windows**

Terminal 1:
```bash
streamlit run new_vid_gen.py
```

Terminal 2:
```bash
python3 youtube_daemon.py
```

**Option 2: Run Daemon in Background**

```bash
# Start daemon in background
nohup python3 youtube_daemon.py > daemon.log 2>&1 &

# Check if it's running
ps aux | grep youtube_daemon

# View logs
tail -f daemon.log

# Stop daemon
pkill -f youtube_daemon.py
```

**Option 3: Keep Terminal Open (Recommended for Mac)**

Terminal 1:
```bash
cd /Users/owenshowalter/CODE/Osho-Content-Lab
streamlit run new_vid_gen.py
```

Terminal 2:
```bash
cd /Users/owenshowalter/CODE/Osho-Content-Lab
python3 youtube_daemon.py
```

Just minimize the terminal windows and they'll keep running!

---

## Accessing Your Dashboard

Once Streamlit is running, your dashboard is available at:

**Local URL:** http://localhost:8501

**Network URL:** Your computer's IP address (shown in terminal when Streamlit starts)

---

## What Each Component Does

### Streamlit UI (`new_vid_gen.py`)
**Purpose:** Web interface for managing your system

**Features:**
- 📊 Dashboard - View all channels and their status
- ⚙️ Settings - Configure channels, authenticate YouTube
- 📈 Analytics - View performance data and AI insights
- ⚙️ Logs - See what the system is doing

**When to use:**
- Setting up new channels
- Viewing analytics
- Checking logs
- Manually generating videos
- Changing settings

**Do you need it running all the time?**
- NO - Only when you want to view the dashboard
- The daemon works independently

---

### YouTube Daemon (`youtube_daemon.py`)
**Purpose:** Background worker that automates everything

**Features:**
- Generates videos 3 minutes before scheduled time
- Uploads to YouTube automatically
- Runs analytics every 24 hours
- Handles multiple channels
- Logs all activity to database

**When to use:**
- Always running (24/7 automation)
- Runs independently of the UI

**Do you need it running all the time?**
- YES - If you want automated video posting
- NO - If you only manually generate videos

---

## Common Commands

### Start the UI
```bash
streamlit run new_vid_gen.py
```

### Start the Daemon
```bash
python3 youtube_daemon.py
```

### Stop the Daemon
```bash
pkill -f youtube_daemon.py
```

### Check if Daemon is Running
```bash
ps aux | grep youtube_daemon
```

### View Daemon Logs (if running in background)
```bash
tail -f daemon.log
```

### Restart Everything
```bash
# Stop daemon
pkill -f youtube_daemon.py

# Start UI
streamlit run new_vid_gen.py

# In another terminal, start daemon
python3 youtube_daemon.py
```

---

## File Locations

### Main Application Files
- **Streamlit UI:** `/Users/owenshowalter/CODE/Osho-Content-Lab/new_vid_gen.py`
- **Daemon:** `/Users/owenshowalter/CODE/Osho-Content-Lab/youtube_daemon.py`
- **Video Engine:** `/Users/owenshowalter/CODE/Osho-Content-Lab/video_engine.py`
- **Database:** `/Users/owenshowalter/CODE/Osho-Content-Lab/channels.db`

### Configuration
- **Secrets:** `/Users/owenshowalter/CODE/Osho-Content-Lab/.streamlit/secrets.toml`
- **Settings:** Stored in SQLite database

### Generated Files
- **Videos:** `/Users/owenshowalter/CODE/Osho-Content-Lab/output/`
- **Logs:** Stored in SQLite database (view via UI)

---

## Troubleshooting

### "Streamlit command not found"

Use the full path:
```bash
/Users/owenshowalter/Library/Python/3.9/bin/streamlit run new_vid_gen.py
```

Or add to your PATH:
```bash
export PATH="/Users/owenshowalter/Library/Python/3.9/bin:$PATH"
```

### "Address already in use"

Streamlit is already running. Either:
1. Use the existing instance (check http://localhost:8501)
2. Kill the old process: `pkill -f streamlit`
3. Use a different port: `streamlit run new_vid_gen.py --server.port=8502`

### Daemon not generating videos

Check:
1. Is the daemon actually running? `ps aux | grep youtube_daemon`
2. Are channels active? (Check in UI → Settings)
3. Is it scheduled time? (Daemon generates 3 min before post time)
4. Check logs in UI → Logs tab

### Can't access UI from browser

1. Check if Streamlit is running: `ps aux | grep streamlit`
2. Try opening manually: `open http://localhost:8501`
3. Check firewall settings
4. Try different port: `streamlit run new_vid_gen.py --server.port=8502`

---

## Advanced: Running as a Service (Optional)

If you want the daemon to run automatically on startup:

### macOS (launchd)

Create file: `~/Library/LaunchAgents/com.user.youtube-daemon.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.youtube-daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/owenshowalter/CODE/Osho-Content-Lab/youtube_daemon.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/owenshowalter/CODE/Osho-Content-Lab/daemon.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/owenshowalter/CODE/Osho-Content-Lab/daemon.error.log</string>
</dict>
</plist>
```

Then run:
```bash
launchctl load ~/Library/LaunchAgents/com.user.youtube-daemon.plist
```

---

## Quick Reference Card

**Print this and keep near your computer:**

```
┌─────────────────────────────────────────────────┐
│  YOUTUBE CONTENT LAB - QUICK COMMANDS           │
├─────────────────────────────────────────────────┤
│  START UI:                                      │
│    streamlit run new_vid_gen.py                 │
│                                                 │
│  START DAEMON:                                  │
│    python3 youtube_daemon.py                    │
│                                                 │
│  STOP DAEMON:                                   │
│    pkill -f youtube_daemon.py                   │
│                                                 │
│  VIEW DASHBOARD:                                │
│    http://localhost:8501                        │
│                                                 │
│  CHECK STATUS:                                  │
│    ps aux | grep youtube_daemon                 │
└─────────────────────────────────────────────────┘
```

---

## Summary

**For daily use:**
1. Open terminal
2. Run: `streamlit run new_vid_gen.py` (optional - only if you want to view dashboard)
3. Open another terminal
4. Run: `python3 youtube_daemon.py` (required - for automation)
5. Minimize terminals and let them run!

**That's it!** Your system will now:
- Generate videos automatically
- Post to YouTube on schedule
- Update analytics every 24 hours
- Learn and improve over time

---

*Last updated: 2026-01-04*
*System Status: ✅ All features implemented and ready*
