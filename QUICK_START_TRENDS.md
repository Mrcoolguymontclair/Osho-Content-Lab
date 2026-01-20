# Google Trends System - Quick Start Guide

**Status:** [OK] Ready to Use
**Setup Time:** 2 minutes

---

## Prerequisites

Before starting, ensure you have:
- [OK] GROQ_API_KEY in `.streamlit/secrets.toml`
- [OK] PEXELS_API_KEY in `.streamlit/secrets.toml`
- [OK] At least one channel authenticated and active

---

## Start the System

### 1. Install pytrends (if not already installed)
```bash
cd /Users/owenshowalter/CODE/Osho-Content-Lab
pip3 install pytrends
```

### 2. Restart the Daemon
```bash
# Stop existing daemon
pkill -f youtube_daemon.py

# Start fresh with trends system
python3 youtube_daemon.py
```

### 3. Verify Trends System Started
Look for this output:
```
[HOT] Starting Google Trends Autonomous System...
   → Fetches trending topics every 6 hours
   → AI analyzes video potential
   → Auto-generates video plans for trends
   → Prioritizes trending videos over regular content
[OK] Google Trends system active
```

---

## What Happens Next

### Immediately (First Run)
The trends worker starts and fetches Google Trends right away:

```
============================================================
 FETCHING GOOGLE TRENDS - 2026-01-10 18:00:00
============================================================

[OK] Found 47 unique trends
[OK] 15 new trends (not in database)

 AI analyzing trends for video potential...

[CHANNEL] Analyzing trends for channel: YourChannel
   Theme: Your theme here

   [OK] APPROVED (85% confidence) - Format: highlights

[VIDEO] Planning videos for 1 approved trends...

   [OK] Planned: [Trending Topic Title]
      Format: highlights
      Clips: 5
      Urgency: very_urgent

============================================================
[OK] Trends analysis complete
[TIME] Next run in 6 hours
============================================================
```

### When Your Channel Needs a Video

The system will:
1. [OK] Check for approved trend video plans FIRST
2. [OK] If trend exists → Generate dynamic trend video
3. [OK] If no trends → Fall back to ranking/standard video
4. [OK] Auto-post to YouTube

---

## Manual Testing (Optional)

### Test Trend Fetching
```bash
python3 google_trends_fetcher.py
```

**Expected:** See list of current trending topics

### Test Trend Analysis
```bash
python3 trend_analyzer.py
```

**Expected:** AI analyzes sample trend and approves/rejects it

### Test Video Planning
```bash
python3 video_planner_ai.py
```

**Expected:** See complete video plan with segments

### Test Dynamic Video Generation
```bash
python3 video_engine_dynamic.py
```

**Expected:** Generate a sample explainer video

---

## Check Database for Trends

### View Approved Trends
```bash
sqlite3 channels.db "SELECT topic, urgency, recommended_format, confidence FROM trends WHERE is_approved = 1 ORDER BY urgency DESC LIMIT 10;"
```

### View Trends Statistics
```bash
sqlite3 channels.db "SELECT COUNT(*) as total_trends, SUM(CASE WHEN is_approved = 1 THEN 1 ELSE 0 END) as approved, SUM(CASE WHEN video_generated = 1 THEN 1 ELSE 0 END) as videos_generated FROM trends;"
```

### View Pending Trend Videos
```bash
sqlite3 channels.db "SELECT topic, recommended_format, urgency FROM trends WHERE is_approved = 1 AND video_generated = 0;"
```

---

## Monitor Logs

### Watch Trends Worker in Real-Time
```bash
tail -f youtube_daemon.log | grep -E "TREND||[OK]||[VIDEO]"
```

### Check for Trend Video Generation
```bash
tail -f youtube_daemon.log | grep "TRENDING VIDEO"
```

---

## Expected Timeline

### Hour 0 (Now)
- [OK] Daemon starts
- [OK] Trends worker fetches first batch of trends
- [OK] AI analyzes and approves 3-5 trends
- [OK] Video plans stored in database

### Hour 0-6 (First Cycle)
- [OK] When your channel needs a video, it checks for trends
- [OK] If approved trend exists → Generates trend video
- [OK] If no trends → Generates regular video
- [OK] Auto-posts to YouTube

### Hour 6 (Second Fetch)
- [OK] Trends worker wakes up again
- [OK] Fetches new trending topics
- [OK] Repeats analysis and planning

### Hour 12, 18, 24... (Every 6 Hours)
- [OK] Continuous trend monitoring
- [OK] Always has fresh trending topics ready
- [OK] Videos stay timely and relevant

---

## Verify It's Working

### 1. Check Daemon Output
Look for:
```
[HOT] TRENDING VIDEO: [Topic Name]
Format: HIGHLIGHTS, Clips: 5
```

### 2. Check Database
```bash
sqlite3 channels.db "SELECT COUNT(*) FROM trends WHERE video_generated = 1;"
```

Should increase over time as trend videos are generated.

### 3. Check YouTube Channel
Videos should have titles like:
- "Lakers vs Celtics Game 7 Best Moments" (not "TOP 10 BASKETBALL GAMES")
- "What is OpenAI GPT-5 Explained" (not "TOP 10 AI TOOLS")
- Real, current, trending topics!

---

## Troubleshooting

### Issue: "No module named 'pytrends'"
**Fix:**
```bash
pip3 install pytrends
```

### Issue: No trends being approved
**Check your channel theme:**
```bash
sqlite3 channels.db "SELECT name, theme FROM channels WHERE is_active = 1;"
```

**Make theme more general:**
- [ERROR] Too specific: "2024 NBA Lakers highlights"
- [OK] Good: "Sports highlights"
- [OK] Good: "Technology news"
- [OK] Good: "Entertainment updates"

### Issue: Trends worker not showing output
**Check daemon is running:**
```bash
ps aux | grep youtube_daemon
```

**Restart daemon:**
```bash
pkill -f youtube_daemon.py
python3 youtube_daemon.py
```

### Issue: Trend videos failing to generate
**Check PEXELS_API_KEY:**
```bash
grep PEXELS_API_KEY .streamlit/secrets.toml
```

**Check logs:**
```bash
tail -50 youtube_daemon.log
```

---

## Force Immediate Trend Fetch (Don't Wait 6 Hours)

If you want to test RIGHT NOW without waiting:

```python
# Run this in Python
from google_trends_fetcher import fetch_all_trends
from trend_analyzer import analyze_multiple_trends
from video_planner_ai import plan_video_from_trend
from trend_tracker import save_trend, update_trend_analysis, update_trend_video_plan
from channel_manager import get_channel

# Fetch trends
trends = fetch_all_trends(region='US')
combined_trends = []
for source, trend_list in trends.items():
    if isinstance(trend_list, list):
        combined_trends.extend(trend_list)

print(f"Found {len(combined_trends)} trends")

# Get your channel
channel = get_channel(1)  # Change ID if needed

# Analyze trends
approved = analyze_multiple_trends(combined_trends[:10], channel['theme'], max_analyze=10)

print(f"Approved {len(approved)} trends")

# Plan videos for approved trends
for trend in approved:
    trend_id = save_trend(trend)
    analysis = trend.get('analysis', {})
    update_trend_analysis(trend_id, analysis, is_approved=True)

    video_plan = plan_video_from_trend(trend, analysis, channel)
    if video_plan:
        update_trend_video_plan(trend_id, video_plan)
        print(f"[OK] Planned: {video_plan['title']}")
```

---

## Success Indicators

### [OK] System is Working If You See:

1. **Daemon Output:**
   ```
   [HOT] Trends Worker Started
   [OK] Found 47 unique trends
   [OK] Planned: [Trending Topic]
   ```

2. **Database Has Trends:**
   ```bash
   sqlite3 channels.db "SELECT COUNT(*) FROM trends WHERE is_approved = 1;"
   # Should return > 0
   ```

3. **Videos Being Generated:**
   ```
   [HOT] TRENDING VIDEO: Lakers vs Celtics
   Format: HIGHLIGHTS, Clips: 5
   [OK] Trend video ready: Lakers vs Celtics Game 7 Best Moments
   ```

4. **YouTube Has Trend Videos:**
   - Check your channel for videos about current events
   - Titles should reference real trending topics
   - Videos about things happening TODAY, not generic content

---

## What Makes This Different?

### BEFORE (Generic Content)
- "TOP 10 MOST EXTREME DESERT LANDSCAPES ON EARTH RANKED!"
- "TOP 5 BEST BASKETBALL GAMES EVER!"
- No connection to current events
- Low views, low engagement

### AFTER (Trending Content)
- "Lakers vs Celtics Game 7 Best Moments" (posted same day as game)
- "What is OpenAI GPT-5 Explained" (posted day of announcement)
- "iPhone 15 vs Samsung S24 Comparison" (posted during launch week)
- High views (people searching for these topics)
- High engagement (timely and relevant)

---

## Next Steps

1. [OK] Start the daemon with trends system
2. [OK] Wait for first trend fetch (happens immediately)
3. [OK] Check database for approved trends
4. [OK] Wait for next video generation
5. [OK] Watch your channel post videos about REAL trending topics!

**The system is now fully autonomous. It will:**
- [OK] Fetch trends every 6 hours
- [OK] Analyze with AI
- [OK] Plan complete videos
- [OK] Generate and post automatically
- [OK] Keep your channel timely and relevant forever

---

**Last Updated:** 2026-01-10
**Status:** [OK] Production Ready
**Support:** Check [GOOGLE_TRENDS_SYSTEM_COMPLETE.md](GOOGLE_TRENDS_SYSTEM_COMPLETE.md) for full documentation
