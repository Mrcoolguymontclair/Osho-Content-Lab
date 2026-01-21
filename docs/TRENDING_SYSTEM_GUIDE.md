# [HOT] Trending Video System - Complete Guide

## Overview

The trending video system automatically creates viral content based on real-time Google Trends data. It fetches trending topics, analyzes them with AI, and generates timely videos that ride the wave of current internet buzz.

## How It Works

### 1. **Trend Discovery** (Automatic)
- System fetches trending topics from Google Trends RSS feed (not rate-limited!)
- Runs automatically in the background
- Captures topics with high search volume

### 2. **AI Analysis** (trend_analyzer.py)
- AI analyzes each trend for video-worthiness
- Scores based on:
  - Urgency (very_urgent, urgent, moderate, low)
  - Confidence (0-100%)
  - Recommended format (comparison, explainer, timeline, etc.)
- Only approved trends move forward

### 3. **Video Planning** (video_planner_ai.py)
- AI creates complete video plan for approved trends
- Plans include:
  - Title (optimized for virality)
  - Script structure
  - Visual elements
  - Clip count and timing

### 4. **Video Generation** (video_engine_dynamic.py)
- Generates video from AI plan
- Fully automated - no manual intervention
- Uses dynamic pacing for maximum engagement

### 5. **Performance Tracking** (ai_analytics_enhanced.py)
- AI predicts video performance before generation
- Tracks actual views, likes, comments
- Learns what trending topics work best

## How to Activate Trending Videos

### Option 1: UI (Recommended)
1. Open Streamlit UI
2. Click on your channel
3. Go to **Settings** tab
4. Under "Video Format" dropdown, select **"trending"**
5. Click "[SAVE] Save Settings"
6. Activate the channel if not already active

### Option 2: Database (Advanced)
```python
from channel_manager import update_channel
update_channel(channel_id, video_type='trending')
```

## Checking Trending Status

### Dashboard Tab
When video_type is set to "trending", the Dashboard shows:
- **Pending Trends**: How many approved trends are ready
- **Videos Generated**: Total trending videos created
- **Next Trend**: Preview of the next topic to be used

### Settings Tab
Shows real-time status:
- [OK] "X trending topics ready for video generation!" (green = ready)
- [WAIT] "No trending topics available yet" (yellow = waiting)

## Three Video Format Options

| Format | Description | Best For |
|--------|-------------|----------|
| **standard** | Classic sequential video format | General evergreen content |
| **ranking** | Countdown-style (#5→#1) with overlays | Engagement-focused content |
| **trending** | AI-generated from Google Trends | Viral, timely content |

## Current Status

Run `python3 test_trending_system.py` to see:
- [OK] 29 approved trends ready for generation
- [OK] 10 new trends fetched from Google
- [OK] 2 Groq API keys configured for failover
- [OK] Trends table initialized and operational

## Fallback Behavior

If you set video_type to "trending" but no trends are available:
- System logs: "[WAIT] No trending topics available yet"
- Automatically falls back to standard video generation
- Continues checking for trends in background

## Database Tables

### trends table
```sql
CREATE TABLE trends (
    id INTEGER PRIMARY KEY,
    topic TEXT NOT NULL,
    source TEXT,
    category TEXT,
    search_volume TEXT,  -- very_high, high, medium, normal
    fetched_at TIMESTAMP,
    analyzed_at TIMESTAMP,
    analysis_json TEXT,
    is_approved BOOLEAN,
    video_planned BOOLEAN,
    video_generated BOOLEAN,
    video_posted BOOLEAN,
    video_id INTEGER,
    video_plan_json TEXT,
    confidence INTEGER,
    urgency TEXT,  -- very_urgent, urgent, moderate, low
    recommended_format TEXT
)
```

## Key Files

| File | Purpose |
|------|---------|
| `google_trends_fetcher.py` | Fetches trends from Google RSS |
| `trend_analyzer.py` | AI analysis of trends |
| `video_planner_ai.py` | Creates video plans from trends |
| `trend_tracker.py` | Database management |
| `video_engine_dynamic.py` | Generates videos from plans |
| `youtube_daemon.py` | Main orchestration logic |

## Troubleshooting

### "No trending topics available"
**Solution:**
1. Run `python3 google_trends_fetcher.py` to fetch manually
2. Wait a few hours - trends are fetched automatically
3. Check `python3 test_trending_system.py` for status

### "Trending system not initialized"
**Solution:**
```bash
python3 -c "from trend_tracker import init_trends_table; init_trends_table()"
```

### Videos still using ranking/standard format
**Check:**
1. Video Format is set to "trending" in Settings
2. Settings were saved (click [SAVE] Save Settings)
3. Channel was reactivated after changing settings

## Best Practices

1. **Mix formats**: Alternate between trending, ranking, and standard
2. **Monitor performance**: Check Dashboard → AI Insights for what's working
3. **Trending works best for**:
   - News-related channels
   - Entertainment channels
   - Sports/gaming channels
4. **Use ranking/standard for**:
   - Evergreen content
   - Educational content
   - When trends don't match your theme

## System Architecture

```
Google Trends RSS
    ↓
google_trends_fetcher.py (fetches trends)
    ↓
trend_analyzer.py (AI approval)
    ↓
video_planner_ai.py (creates video plan)
    ↓
trend_tracker.py (stores in database)
    ↓
youtube_daemon.py (checks when generating)
    ↓
video_engine_dynamic.py (generates video)
    ↓
YouTube upload
```

## Performance Expectations

**With Trending Videos:**
- 30-50% higher initial views (riding trend wave)
- Better click-through rate (timely topics)
- Requires quick turnaround (trends expire fast)

**Compared to Standard:**
- Standard: Consistent, predictable performance
- Trending: Higher variance, potential for viral hits

## Future Enhancements

- [ ] Multi-source trend aggregation (Twitter, Reddit, etc.)
- [ ] Custom trend keywords for your niche
- [ ] Trend scheduling (post during peak trend time)
- [ ] Trend performance analytics dashboard
- [ ] Automatic trend category filtering by channel theme

---

**Last Updated:** January 12, 2026
**System Status:** [OK] Operational (29 pending trends)
