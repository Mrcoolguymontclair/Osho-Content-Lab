# YouTube Multi-Channel Automation System - User Guide

## 🎬 Welcome to Your YouTube Empire Builder!

This system automatically generates and posts viral YouTube Shorts to multiple channels simultaneously. Each video includes:
- ✅ 10 HD video clips matching your theme
- ✅ AI-generated voiceover (gTTS)
- ✅ Background music
- ✅ Viral-style subtitles
- ✅ Professional audio mixing

---

## 🚀 Quick Start Guide

### Step 1: Launch the System

```bash
cd /Users/owenshowalter/CODE/Osho-Content-Lab
streamlit run new_vid_gen.py
```

The interface will open in your browser at `http://localhost:8501`

### Step 2: Start the Automation Engine

1. Click the **"🚀 Start Engine"** button on the home page
2. The background daemon will start (runs independently from the UI)
3. Green status: "✅ Automation Engine RUNNING"

### Step 3: Create Your First Channel

1. Click **"➕ Add New Channel"**
2. Fill in the details:
   - **Channel Name**: e.g., "Science Facts Daily"
   - **Theme**: e.g., "Mind-blowing Science Facts"
   - **Tone**: e.g., "Exciting" or "Dramatic"
   - **Style**: e.g., "Fast-paced" or "Educational"
   - **Post Interval**: How often to post (in minutes, default: 60)
   - **Music Volume**: Background music volume (0-100%, default: 15%)
3. Click **"Create Channel"**

### Step 4: Authenticate with YouTube

1. Click **"View"** on your channel card
2. Go to **"🔐 YouTube Auth"** tab
3. Click **"🔐 Authenticate with YouTube"**
4. Browser will open for Google login
5. Sign in to the YouTube account you want to use
6. Grant permissions
7. Done! Channel is now authenticated

### Step 5: Activate the Channel

1. Go to **"⚙️ Settings"** tab
2. Click **"▶️ Activate Channel"**
3. The channel will start generating videos!

---

## 📖 How It Works

### The Automated Workflow:

1. **30 Minutes Before Post Time**:
   - AI generates a unique viral topic based on your theme
   - System creates script with 10 segments
   - Downloads 10 theme-matching video clips from Pexels
   - Generates 10 voiceovers with gTTS
   - Downloads background music from Pixabay
   - Assembles everything into a complete 60-second video
   - Burns in viral-style subtitles

2. **At Exact Post Time**:
   - Uploads video to YouTube
   - Sets title, description, and tags automatically
   - Marks video as public and not for kids
   - Cleans up source files to save disk space

3. **Repeats Forever**:
   - Calculates next post time based on your interval
   - Starts preparing the next video 30 minutes early
   - Fully autonomous - no manual intervention needed!

---

## 🎛️ Channel Settings Explained

### Theme/Niche
The core topic of your channel. The AI will generate all video topics based on this.
- Examples: "Ocean Life", "Space Exploration", "Ancient History", "Future Technology"

### Tone
The emotional feel of the narration.
- Examples: "Exciting", "Calm", "Dramatic", "Funny", "Mysterious"

### Style
The pacing and presentation style.
- Examples: "Fast-paced", "Educational", "Story-driven", "List-based"

### Additional Info
Any extra context for the AI. This helps refine the content.
- Examples: "Focus on lesser-known facts", "Target audience: teenagers", "Avoid controversial topics"

### Post Interval
How often to post videos (in minutes).
- Minimum: 15 minutes
- Recommended: 60-180 minutes (1-3 hours)
- For multiple daily posts: 360 minutes (6 hours) = 4 posts/day

### Music Volume
Background music volume as percentage of voiceover.
- 0% = No music
- 15% = Default (music subtle, voiceover clear)
- 50% = Equal mix
- 100% = Music as loud as voiceover

---

## 🔐 Multi-Account YouTube Setup

### Why Separate Authentication?

Each channel needs its own YouTube account authentication because:
- You might run multiple different YouTube channels
- Each channel posts independently
- Quota limits are per account

### How to Manage Multiple Accounts:

1. **First Channel**: Authenticate with Google Account A
2. **Second Channel**:
   - Open browser in incognito/private mode
   - Authenticate with Google Account B
3. **Third Channel**: Repeat with Account C

The system stores separate token files for each channel in the `tokens/` directory.

---

## 📊 Understanding the Interface

### Home Page

- **Channel Cards**: Quick overview of all channels
- **Status Indicators**:
  - ● ACTIVE (green) = Channel is posting automatically
  - ○ PAUSED (yellow) = Channel is stopped
- **Next Post Timer**: Shows when the next video will be posted
- **Last Video Link**: Quick access to most recent upload

### Channel Page - Settings Tab

- Modify channel configuration
- Activate/pause posting
- Delete channel (requires confirmation)

### Channel Page - Status & Logs Tab

- **Current Activity**: What the system is doing right now
- **Live Logs**: Real-time updates (auto-refreshes every 5 seconds)
- Color-coded logs:
  - 🔵 Info = Normal operations
  - 🟡 Warning = Non-critical issues
  - 🔴 Error = Problems that need attention

### Channel Page - Videos Tab

- History of all generated videos
- Status indicators:
  - ✅ Posted = Successfully uploaded to YouTube
  - ⏳ Ready = Video generated, waiting to post
  - 🎬 Generating = Currently being created
  - ❌ Failed = Generation or upload failed
- Clickable YouTube links

### Channel Page - YouTube Auth Tab

- Authentication status
- YouTube channel statistics (subscribers, views, videos)
- Authenticate/revoke buttons

---

## 🛠️ Troubleshooting

### "Automation Engine STOPPED"

**Solution**: Click "🚀 Start Engine" button

The daemon runs independently. If you restart your computer or stop it manually, you need to start it again.

### "Channel not authenticated"

**Solution**:
1. Go to channel page
2. Click "🔐 YouTube Auth" tab
3. Click "🔐 Authenticate with YouTube"
4. Complete Google login

### "Video generation failed" (repeated errors)

**What happens**:
- After 20 identical errors, the channel automatically pauses
- AI generates a detailed error diagnosis
- Check the logs for the diagnosis

**Common causes**:
- API quota exceeded (Pexels, Pixabay, or YouTube)
- Network connection issues
- Invalid channel settings

**Solution**:
1. Read the error diagnosis in logs
2. Fix the issue (wait for quota reset, check internet, etc.)
3. Click "▶️ Activate Channel" to resume

### "Disk space low" warning

**What it means**: Less than 10% disk space remaining

**Solution**:
1. System automatically deletes source files after successful uploads
2. Final videos are kept for 24 hours then deleted
3. If needed, manually delete old videos from `outputs/` folder

### Music or clips not matching theme

**Solution**:
- Update the "Additional Info" field in settings
- Be more specific: "Use only ocean-related clips" or "Avoid abstract imagery"
- The AI will refine its search queries

### Videos have no audio

**This shouldn't happen** - system verifies audio before uploading.

If it does:
1. Check logs for "Audio stream not found" errors
2. System will retry automatically
3. If persists after 5 retries, check ffmpeg installation

---

## 🎯 Best Practices

### For Maximum Virality:

1. **Theme Selection**:
   - Choose specific niches: "Deep Ocean Creatures" > "Animals"
   - Trending topics: Space, Technology, History, Psychology
   - Shock value: "Facts That Sound Fake", "Mysteries Scientists Can't Explain"

2. **Tone & Style**:
   - **Exciting + Fast-paced** = Most viral
   - **Mysterious + Story-driven** = Good for mysteries/unsolved topics
   - **Dramatic + Educational** = Science/history content

3. **Posting Schedule**:
   - **High frequency** (every 1-2 hours) = Faster channel growth
   - **Consistent timing** = Builds audience expectations
   - **Prime times** = Post when your target audience is online

4. **Multi-Channel Strategy**:
   - Run 3-5 different themed channels simultaneously
   - Different niches attract different audiences
   - Diversifies your content portfolio

### Resource Management:

- **CPU**: Each channel uses minimal CPU (only during video generation)
- **Disk**: ~500MB per video × channels × interval
  - Example: 3 channels posting every 2 hours = ~18 videos/day = ~9GB/day
  - System cleans up automatically, so ~1-2GB steady state
- **APIs**:
  - Groq: Unlimited (use as much as needed!)
  - Pexels: Check your quota at https://www.pexels.com/api/
  - Pixabay: 5,000 requests/hour (more than enough)
  - YouTube: 10,000 units/day (each upload = ~1,600 units = ~6 uploads/day per account)

---

## 🔧 Advanced Features

### Error Recovery System

The system has intelligent error handling:

- **Retry Logic**:
  - Script generation: 5 attempts with exponential backoff
  - Voiceover: 5 attempts (always uses gTTS, unlimited)
  - Video clips: 20 attempts with AI-generated alternative search queries
  - Music: 5 attempts with simpler keywords

- **Error Tracking**:
  - Counts each error type separately
  - After 20 identical errors: pauses channel + generates diagnosis
  - Resets counter after successful video

### Automatic File Cleanup

- **After successful upload**:
  - Deletes: Source clips, voiceovers, music, intermediate files
  - Keeps: Final video (for 24 hours as backup)

- **Disk space monitoring**:
  - Checks before each generation
  - Warns at 90% full
  - Suggests cleanup in UI

### Background Operation

The daemon runs completely independently:
- Close the Streamlit UI ✅
- Close your browser ✅
- Log out of your account ✅
- Restart your computer ❌ (need to start engine again)

Videos will continue posting on schedule!

---

## 📝 API Keys Required

All keys are in `.streamlit/secrets.toml`:

1. **GROQ_API_KEY** ✅ (Already configured)
   - Get from: https://console.groq.com/keys
   - Usage: AI script generation
   - Quota: Unlimited!

2. **PEXELS_API_KEY** ✅ (Already configured)
   - Get from: https://www.pexels.com/api/
   - Usage: HD video clips
   - Quota: Check your account

3. **PIXABAY_API_KEY** ✅ (Already configured)
   - Get from: https://pixabay.com/api/docs/
   - Usage: Background music
   - Quota: 5,000/hour

4. **YOUTUBE_CLIENT_SECRET** ✅ (Already configured)
   - Get from: https://console.cloud.google.com/apis/credentials
   - Usage: Video uploads
   - Quota: 10,000 units/day

---

## 🎬 Your First Video - What to Expect

1. **Generation Time**: ~2-3 minutes
   - Script generation: 5 seconds
   - Voiceovers: 30 seconds
   - Video clips: 60-90 seconds (depends on Pexels API)
   - Music download: 5 seconds
   - Video assembly: 45 seconds

2. **File Size**: 6-10MB final video

3. **Upload Time**: 30-60 seconds (depends on internet speed)

4. **Total**: ~3-4 minutes from start to YouTube

---

## 🆘 Getting Help

### Check Logs First

99% of issues are visible in the logs:
1. Go to channel page
2. Click "📊 Status & Logs" tab
3. Look for 🔴 red error messages
4. Read the AI-generated diagnosis (appears after 20 errors)

### Common Error Messages:

- **"Pexels API returned 429"**: Rate limit, wait 1 hour
- **"YouTube API quota exceeded"**: Daily limit reached, resets at midnight Pacific Time
- **"Channel not authenticated"**: Need to re-authenticate (token expired)
- **"FFmpeg failed"**: Video assembly issue, check ffmpeg installation
- **"No videos found for search query"**: AI will retry with different queries (automatic)

### Emergency Stop

If something goes wrong:
1. Click "🛑 Stop Engine" (stops all channels immediately)
2. Fix the issue
3. Click "🚀 Start Engine" to resume

---

## 🎉 Success Metrics

### What to Monitor:

- **Videos Posted**: Check "Videos" tab for successful uploads
- **YouTube Performance**: View count, engagement in YouTube Studio
- **Error Rate**: Should be <5% (check logs)
- **Disk Usage**: Should stay under 10GB with cleanup enabled

### Scaling Up:

Once comfortable:
1. Add more channels (different niches)
2. Increase posting frequency (shorter intervals)
3. Run 24/7 for maximum output

**Example setup**:
- 5 channels
- 2-hour intervals
- = 60 videos/day
- = 1,800 videos/month
- Fully automated! 🚀

---

## 📞 System Files

- `new_vid_gen.py` - Streamlit UI (run this)
- `youtube_daemon.py` - Background service
- `video_engine.py` - Video generation core
- `channel_manager.py` - Database operations
- `auth_manager.py` - YouTube authentication
- `channels.db` - SQLite database
- `outputs/` - Generated videos
- `tokens/` - YouTube OAuth tokens
- `daemon.pid` - Daemon process ID
- `daemon_stdout.log` - Daemon output logs
- `daemon_stderr.log` - Daemon error logs

---

## ✅ Final Checklist

Before going live:

- [ ] Streamlit UI loads successfully
- [ ] Automation engine starts (green status)
- [ ] First channel created
- [ ] YouTube authenticated
- [ ] Channel activated
- [ ] First video generated successfully (check logs)
- [ ] First video uploaded to YouTube
- [ ] Verify video on YouTube has audio + subtitles
- [ ] System continues to next video automatically

---

## 🚀 You're Ready!

The system is now running 24/7, automatically creating and posting viral content to your YouTube channels.

**Sit back and watch your channel grow!** 📈

For issues or questions, check the logs first - the AI diagnosis feature will help you troubleshoot.

Happy automating! 🎬✨
