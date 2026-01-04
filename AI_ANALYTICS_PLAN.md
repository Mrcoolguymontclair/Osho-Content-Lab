# AI Video Analytics & Self-Improvement System
## Implementation Plan

---

## 📊 OVERVIEW

Build an AI-powered analytics system that:
1. Fetches video performance metrics from YouTube API
2. Analyzes what makes successful videos work
3. Automatically adapts future content based on insights
4. Learns continuously from each video's performance

---

## 🎯 PHASE 1: DATA COLLECTION (YouTube API Integration)

### 1.1 YouTube Analytics Data Fetching

**New File:** `youtube_analytics.py`

**Functions to Build:**
```python
def get_video_stats(video_id: str, channel_name: str) -> dict:
    """
    Fetch comprehensive stats for a single video

    Returns:
    {
        'video_id': str,
        'views': int,
        'likes': int,
        'comments': int,
        'shares': int,
        'watch_time_avg': float,  # Average watch time percentage
        'retention_curve': list,   # Audience retention data
        'ctr': float,              # Click-through rate
        'published_at': str
    }
    """

def get_channel_videos_stats(channel_name: str, limit: int = 50) -> list:
    """
    Get stats for multiple videos from the channel
    """

def update_video_stats_in_db(video_id: int):
    """
    Fetch latest stats from YouTube and update database
    """
```

**YouTube API Scopes Needed:**
- `youtube.readonly` - Read video analytics
- `yt-analytics.readonly` - Detailed analytics data

**Database Schema Update:**
```sql
ALTER TABLE videos ADD COLUMN views INTEGER DEFAULT 0;
ALTER TABLE videos ADD COLUMN likes INTEGER DEFAULT 0;
ALTER TABLE videos ADD COLUMN comments INTEGER DEFAULT 0;
ALTER TABLE videos ADD COLUMN shares INTEGER DEFAULT 0;
ALTER TABLE videos ADD COLUMN avg_watch_time REAL DEFAULT 0;
ALTER TABLE videos ADD COLUMN ctr REAL DEFAULT 0;
ALTER TABLE videos ADD COLUMN last_stats_update TEXT;

-- New table for retention data
CREATE TABLE video_retention (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER,
    timestamp INTEGER,  -- Seconds into video
    retention_percent REAL,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);
```

---

## 🧠 PHASE 2: AI ANALYSIS ENGINE

### 2.1 Performance Analysis with Groq

**New File:** `ai_analyzer.py`

**Core Analysis Functions:**

```python
def analyze_video_performance(video: dict) -> dict:
    """
    Analyze a single video's performance

    Input: Video with stats
    Output: {
        'success_score': float (0-100),
        'strengths': [str],
        'weaknesses': [str],
        'key_insights': [str]
    }
    """

def analyze_channel_trends(channel_id: int, limit: int = 20) -> dict:
    """
    Analyze patterns across recent videos

    Returns: {
        'best_performing_topics': [str],
        'optimal_video_length': float,
        'best_posting_times': [str],
        'successful_hooks': [str],
        'effective_pacing': str,
        'audience_preferences': dict
    }
    """

def generate_content_strategy(channel_id: int) -> dict:
    """
    Create data-driven content strategy

    Returns: {
        'recommended_topics': [str],
        'content_style': str,
        'pacing_suggestions': str,
        'hook_templates': [str],
        'avoid_topics': [str]
    }
    """
```

**Groq Prompts:**

1. **Individual Video Analysis:**
```python
prompt = f"""Analyze this YouTube Short's performance:

Title: {video['title']}
Views: {video['views']:,}
Likes: {video['likes']:,}
Comments: {video['comments']:,}
Average Watch Time: {video['avg_watch_time']}%
CTR: {video['ctr']}%

Channel Average Metrics:
- Avg Views: {channel_avg['views']:,}
- Avg Likes: {channel_avg['likes']:,}
- Avg Watch Time: {channel_avg['watch_time']}%

Provide a detailed analysis:
1. Success Score (0-100): How well did this video perform?
2. Key Strengths: What made this video successful?
3. Weaknesses: What could be improved?
4. Actionable Insights: Specific lessons for future videos

Output as JSON."""
```

2. **Pattern Recognition Across Videos:**
```python
prompt = f"""Analyze patterns across these {len(videos)} YouTube Shorts:

HIGH PERFORMERS (Top 25%):
{format_video_list(top_videos)}

LOW PERFORMERS (Bottom 25%):
{format_video_list(bottom_videos)}

Channel Theme: {channel['theme']}
Current Style: {channel['style']}

Identify:
1. Common traits of successful videos (topics, structure, pacing)
2. Red flags in underperforming videos
3. Optimal video characteristics for this channel
4. Content gaps and opportunities
5. Audience engagement patterns

Output as JSON with specific, actionable recommendations."""
```

---

## 🔄 PHASE 3: ADAPTIVE CONTENT GENERATION

### 3.1 Smart Script Generation

**Modify:** `video_engine.py` - `generate_video_script()`

**Enhanced Script Generation:**
```python
def generate_video_script_with_analytics(channel_config: dict) -> dict:
    """
    Generate script using AI insights from past performance
    """
    # 1. Get content strategy from AI analyzer
    strategy = generate_content_strategy(channel_config['id'])

    # 2. Get recent video titles to avoid
    recent_videos = get_channel_videos(channel_config['id'], limit=20)

    # 3. Build enhanced prompt with AI insights
    prompt = f"""You are a viral YouTube Shorts script writer with data-driven insights.

Channel Theme: {channel_config['theme']}
Proven Successful Topics: {strategy['best_performing_topics']}
Recommended Content Direction: {strategy['recommended_topics']}

WHAT WORKS FOR THIS CHANNEL:
{strategy['successful_hooks']}
{strategy['content_style']}
{strategy['pacing_suggestions']}

AVOID THESE (underperformed):
{strategy['avoid_topics']}

RECENT VIDEOS (don't repeat):
{recent_titles}

Create a viral script optimized for THIS SPECIFIC AUDIENCE based on proven data."""

    # 4. Generate with Groq
    # 5. Return optimized script
```

---

## 📈 PHASE 4: AUTOMATED LEARNING LOOP

### 4.1 Continuous Improvement System

**New File:** `learning_loop.py`

```python
def run_analytics_cycle(channel_id: int):
    """
    Run complete analytics and learning cycle

    Steps:
    1. Fetch latest stats for all posted videos
    2. Analyze performance patterns
    3. Update content strategy in database
    4. Adjust future video generation parameters
    """

def schedule_analytics_updates():
    """
    Run analytics every 24 hours for all active channels
    """
```

**Database Schema for Insights:**
```sql
CREATE TABLE channel_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER,
    insight_type TEXT,  -- 'topic', 'style', 'pacing', 'hook'
    insight_data TEXT,  -- JSON with details
    confidence_score REAL,
    created_at TEXT,
    last_validated TEXT,
    FOREIGN KEY (channel_id) REFERENCES channels(id)
);

CREATE TABLE content_strategy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER,
    recommended_topics TEXT,  -- JSON array
    avoid_topics TEXT,        -- JSON array
    optimal_style TEXT,
    hook_templates TEXT,      -- JSON array
    generated_at TEXT,
    performance_score REAL,
    FOREIGN KEY (channel_id) REFERENCES channels(id)
);
```

---

## 🎨 PHASE 5: UI INTEGRATION

### 5.1 Analytics Dashboard

**New Tab in `new_vid_gen.py`:**

```python
def render_analytics_tab(channel: dict):
    """
    📊 Analytics & AI Insights Tab
    """
    st.markdown("### 📊 Video Performance Analytics")

    # Performance Overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Avg Views", f"{stats['avg_views']:,}")
    with col2:
        st.metric("Avg Watch Time", f"{stats['avg_retention']:.1f}%")
    with col3:
        st.metric("Total Likes", f"{stats['total_likes']:,}")
    with col4:
        st.metric("Engagement Rate", f"{stats['engagement_rate']:.2f}%")

    # Top Performing Videos
    st.markdown("### 🏆 Best Performers")
    display_top_videos(channel['id'])

    # AI Insights
    st.markdown("### 🧠 AI-Discovered Patterns")
    insights = get_latest_insights(channel['id'])

    st.success(f"✅ Winning Formula: {insights['successful_pattern']}")
    st.info(f"💡 Recommendation: {insights['next_action']}")
    st.warning(f"⚠️ Avoid: {insights['avoid_pattern']}")

    # Content Strategy
    st.markdown("### 🎯 Data-Driven Strategy")
    strategy = get_content_strategy(channel['id'])

    st.write("**Recommended Next Topics:**")
    for topic in strategy['recommended_topics'][:5]:
        st.write(f"- {topic}")

    # Update button
    if st.button("🔄 Refresh Analytics from YouTube"):
        update_all_video_stats(channel['id'])
        st.success("Analytics updated!")
        st.rerun()
```

**Add 4th Tab:**
```python
# In channel_page()
col1, col2, col3, col4 = st.columns(4)
with col4:
    if st.button("📊 Analytics", ...):
        st.session_state.active_tab = "Analytics"
```

---

## ⚙️ PHASE 6: AUTOMATION & SCHEDULING

### 6.1 Background Analytics Worker

**Modify:** `youtube_daemon.py`

```python
def analytics_worker():
    """
    Background thread that runs analytics every 24 hours
    """
    while daemon_running:
        # For each active channel
        for channel in get_active_channels():
            # Update video stats
            update_all_video_stats(channel['id'])

            # Run AI analysis
            analyze_channel_trends(channel['id'])

            # Update content strategy
            generate_content_strategy(channel['id'])

        # Sleep for 24 hours
        time.sleep(86400)

# In start_daemon(), add:
analytics_thread = threading.Thread(target=analytics_worker, daemon=True)
analytics_thread.start()
```

---

## 🔧 IMPLEMENTATION ORDER

### Week 1: Data Collection
- [ ] Set up YouTube Analytics API
- [ ] Create `youtube_analytics.py`
- [ ] Add database columns for stats
- [ ] Implement `get_video_stats()`
- [ ] Test data fetching with existing videos

### Week 2: AI Analysis
- [ ] Create `ai_analyzer.py`
- [ ] Implement single video analysis with Groq
- [ ] Build pattern recognition across videos
- [ ] Create content strategy generator
- [ ] Test with real channel data

### Week 3: Integration
- [ ] Modify script generation to use insights
- [ ] Create learning loop system
- [ ] Add database tables for insights
- [ ] Implement analytics worker thread
- [ ] Test end-to-end flow

### Week 4: UI & Polish
- [ ] Build Analytics dashboard tab
- [ ] Add visualizations (charts/graphs)
- [ ] Create manual refresh button
- [ ] Add confidence scores to insights
- [ ] Polish UX and error handling

---

## 📊 KEY METRICS TO TRACK

### Video-Level Metrics:
- Views (absolute & velocity)
- Watch time (avg & retention curve)
- Likes, comments, shares
- CTR (click-through rate)
- Audience retention at key points (0s, 5s, 15s, 30s, 60s)

### Channel-Level Patterns:
- Best performing topics/themes
- Optimal video length
- Best posting times
- Hook effectiveness
- Pacing preferences
- Visual style success rate

### AI Learning Metrics:
- Prediction accuracy (projected vs actual views)
- Strategy improvement rate
- Topic success rate
- Engagement trend over time

---

## 🚀 ADVANCED FEATURES (Future)

### A/B Testing System:
- Generate 2 variations of hooks
- Test with first 1000 views
- Auto-select winning version
- Learn from A/B results

### Competitor Analysis:
- Analyze top channels in same niche
- Identify successful patterns
- Adapt winning strategies
- Find content gaps

### Predictive Analytics:
- Predict view count before posting
- Recommend optimal post time
- Suggest title variations
- Forecast engagement rate

### Multi-Channel Learning:
- Share insights across all channels
- Cross-channel pattern recognition
- Universal best practices library
- Niche-specific optimizations

---

## 🔐 IMPORTANT CONSIDERATIONS

### API Rate Limits:
- YouTube API: 10,000 quota units/day
- Batch requests to optimize quota
- Cache stats for 24 hours
- Prioritize most important metrics

### Privacy & Data:
- Store only aggregated metrics
- Don't store viewer personal data
- Comply with YouTube ToS
- Secure API credentials

### Cost Management:
- Groq API: Monitor token usage
- Batch analytics processing
- Run heavy analysis during off-peak
- Implement result caching

---

## 💡 SUCCESS CRITERIA

This system is successful when:
1. ✅ Videos show measurable improvement in views over time
2. ✅ AI accurately predicts high-performing topics
3. ✅ Content strategy adapts automatically to audience feedback
4. ✅ Channel growth accelerates month-over-month
5. ✅ User can see clear ROI from AI insights

---

## 🎯 EXPECTED OUTCOMES

After 30 days of data:
- 30-50% improvement in average views
- 20-30% better audience retention
- Higher engagement rates (likes/comments)
- More predictable performance
- Self-optimizing content machine

---

## 📝 NEXT STEPS

1. **Review this plan** - Make sure it aligns with your goals
2. **Set priorities** - Which phase to start with?
3. **Allocate time** - How much time can you dedicate?
4. **Start small** - Begin with Phase 1 (data collection)
5. **Iterate fast** - Test, learn, improve

Ready to build the future of AI-powered content creation! 🚀
