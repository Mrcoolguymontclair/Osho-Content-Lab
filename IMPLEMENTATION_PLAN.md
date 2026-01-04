# Multi-Channel YouTube Automation System - Implementation Plan

## Project Overview
Build a fully autonomous multi-channel YouTube Shorts automation system that runs continuously in the background, generating and posting viral videos on scheduled intervals.

---

## Architecture Components

### 1. Background Service (`youtube_daemon.py`)
- Runs independently as Python daemon process
- Monitors all channels and their schedules
- Generates videos 30 minutes before post time
- Handles all video generation and upload logic
- Writes status to shared database/files

### 2. Streamlit UI (`new_vid_gen.py`)
- Connects to background service to display status
- Multi-tab interface (Home + one tab per channel)
- Channel management (add/remove/configure)
- YouTube authentication UI
- Live logs viewer
- Manual start/stop controls

### 3. Core Video Engine (`video_engine.py`)
- All video generation logic (learned from our testing)
- Script generation with Groq
- Voiceover with gTTS fallback
- Video clip processing from Pexels
- Background music from Pixabay
- Subtitle generation
- FFmpeg assembly with proper audio mixing

### 4. Data Layer (`channel_manager.py`)
- SQLite database for persistence
- Channel configurations
- Video history
- Error logs
- Schedule tracking

---

## Detailed Implementation Checklist

### Phase 1: Core Infrastructure ✓

#### 1.1 Project Setup
- [ ] Create new file structure:
  - `new_vid_gen.py` (Streamlit UI)
  - `youtube_daemon.py` (Background service)
  - `video_engine.py` (Video generation core)
  - `channel_manager.py` (Data management)
  - `music_manager.py` (Pixabay music downloads)
  - `auth_manager.py` (Multi-account YouTube OAuth)
- [ ] Update `requirements.txt` with new dependencies
- [ ] Add Pixabay API key to `.streamlit/secrets.toml`

#### 1.2 Database Schema Design
```sql
CREATE TABLE channels (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    theme TEXT NOT NULL,
    tone TEXT NOT NULL,
    style TEXT NOT NULL,
    other_info TEXT,
    post_interval_minutes INTEGER DEFAULT 60,
    music_volume INTEGER DEFAULT 15,
    is_active BOOLEAN DEFAULT 0,
    token_file TEXT,
    created_at TIMESTAMP,
    last_post_at TIMESTAMP
);

CREATE TABLE videos (
    id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    title TEXT,
    theme TEXT,
    video_path TEXT,
    youtube_url TEXT,
    status TEXT, -- 'generating', 'ready', 'posted', 'failed'
    scheduled_post_time TIMESTAMP,
    actual_post_time TIMESTAMP,
    error_count INTEGER DEFAULT 0,
    FOREIGN KEY(channel_id) REFERENCES channels(id)
);

CREATE TABLE logs (
    id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    timestamp TIMESTAMP,
    level TEXT, -- 'info', 'warning', 'error'
    category TEXT, -- 'script', 'voiceover', 'clip', 'upload', etc.
    message TEXT,
    details TEXT,
    FOREIGN KEY(channel_id) REFERENCES channels(id)
);

CREATE TABLE error_tracker (
    id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    error_type TEXT,
    count INTEGER DEFAULT 1,
    last_occurred TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(id)
);
```

---

### Phase 2: Video Engine (Core Logic)

#### 2.1 FFmpeg Path Finder (CRITICAL - from our testing)
- [ ] Create `find_ffmpeg()` function
- [ ] Check common paths: `/opt/homebrew/bin/ffmpeg`, `/usr/local/bin/ffmpeg`, `/usr/bin/ffmpeg`
- [ ] Global `FFMPEG` variable used everywhere
- [ ] Test on macOS (current system)

#### 2.2 Script Generation with Groq
- [ ] Function: `generate_video_script(channel_config)`
- [ ] Input: channel theme, tone, style, other_info
- [ ] Use Groq API with llama-3.3-70b-versatile
- [ ] Generate unique topic based on channel theme
- [ ] Output: 10 segments, each with:
  - `narration` (text to speak)
  - `searchQuery` (for Pexels video)
  - `musicKeywords` (for Pixabay music)
- [ ] Retry logic: 5 attempts with exponential backoff
- [ ] Error handling: catch API errors, quota issues
- [ ] Logging: detailed logs to database

#### 2.3 Voiceover Generation (gTTS Primary)
- [ ] Function: `generate_voiceover(text, output_path)`
- [ ] Use gTTS as PRIMARY (unlimited, free, proven working)
- [ ] Speed up to 1.1x with ffmpeg for better pacing
- [ ] ElevenLabs as optional fallback if quota available
- [ ] Retry logic: 5 attempts
- [ ] Error handling: catch network errors, file write errors
- [ ] Output verification: check file exists and size > 0

#### 2.4 Video Clip Processing (Pexels)
- [ ] Function: `download_video_clip(search_query, output_path, retry_count=0)`
- [ ] Download from Pexels using search query
- [ ] If fails: Generate 20 alternative search queries with Groq
- [ ] Try each alternative query (max 20 attempts)
- [ ] Trim to exactly 6 seconds
- [ ] Verify video downloaded and playable
- [ ] Detailed logging for each attempt

#### 2.5 Background Music (Pixabay) - NEW FEATURE
- [ ] Function: `download_background_music(keywords, output_path)`
- [ ] Use Pixabay API: `https://pixabay.com/api/videos/?key=API_KEY&q=KEYWORDS`
- [ ] Search using video's musicKeywords
- [ ] Download MP3 audio track
- [ ] Retry with simpler keywords if fails
- [ ] Cache popular music locally to avoid re-downloads

#### 2.6 Video Assembly Pipeline (CRITICAL - from our testing)
```python
def assemble_viral_video(script, channel_config, output_dir):
    # Step 1: Generate all voiceovers (10 segments)
    # Step 2: Download all video clips (10 clips, with 20-retry fallback)
    # Step 3: Download background music
    # Step 4: Concat video clips using demuxer method
    # Step 5: Concat voiceovers using demuxer method (NOT filter_complex - caused errors!)
    # Step 6: Generate SRT subtitles
    # Step 7: Burn subtitles into video (Arial font, 20pt, bottom-aligned)
    # Step 8: Mix background music with voiceover audio
    # Step 9: Merge final audio with video
    # Step 10: Verify audio stream exists in final video
```

**Critical FFmpeg Commands (from our testing):**
- [ ] Video concat: `ffmpeg -f concat -safe 0 -i list.txt -c copy output.mp4`
- [ ] Audio concat: `ffmpeg -f concat -safe 0 -i vo_list.txt -c copy output.mp3` (NOT filter_complex!)
- [ ] Subtitle burn: `ffmpeg -i video.mp4 -vf "subtitles=subs.srt:force_style='Fontname=Arial,Fontsize=20,Bold=1,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2,Alignment=2,MarginV=20'" -c:v libx264 -preset fast output.mp4`
- [ ] Music mixing: `ffmpeg -i voiceover.mp3 -i music.mp3 -filter_complex "[1:a]volume=0.15[music];[0:a][music]amix=inputs=2:duration=shortest[out]" -map [out] output.mp3`
- [ ] Final merge: `ffmpeg -y -i video.mp4 -i audio.mp3 -c:v copy -c:a aac -b:a 192k -map 0:v:0 -map 1:a:0 -shortest final.mp4`
- [ ] Audio verification: Check stderr contains "Audio: aac"

#### 2.7 Error Handling & Retry Logic
- [ ] Track errors per type in database
- [ ] If same error occurs 20 times: abort video, notify user
- [ ] If clip download fails: try 20 different search queries
- [ ] If voiceover fails: retry 5 times
- [ ] If script generation fails: retry 5 times with simpler prompt
- [ ] Generate detailed error report with Groq
- [ ] Reset error count after successful video

---

### Phase 3: Background Daemon Service

#### 3.1 Daemon Core Logic
- [ ] Function: `start_daemon()`
- [ ] Load all active channels from database
- [ ] For each channel, spawn a thread/process
- [ ] Each thread runs independently with its own schedule
- [ ] Write PID to file for management
- [ ] Graceful shutdown handler (SIGTERM, SIGINT)

#### 3.2 Channel Worker Thread
```python
def channel_worker(channel_id):
    while channel.is_active:
        next_post_time = calculate_next_post_time(channel)
        prepare_time = next_post_time - timedelta(minutes=30)

        # Wait until 30 mins before post time
        wait_until(prepare_time)

        # Generate next video
        video = generate_video(channel)

        # Wait until exact post time
        wait_until(next_post_time)

        # Upload to YouTube
        upload_video(video, channel)

        # Cleanup files if successful
        cleanup_video_files(video)
```

#### 3.3 Video Pre-Generation
- [ ] Calculate next post time based on interval
- [ ] Start generating 30 minutes before
- [ ] Store video as "ready" in database
- [ ] If generation fails, retry immediately
- [ ] If retries exhausted, skip this post and try next interval

#### 3.4 File Cleanup
- [ ] After successful YouTube upload:
  - Delete source clips (10 files)
  - Delete voiceover files (10 files)
  - Delete intermediate files (concat, subs, etc.)
  - Keep only final MP4 for 24 hours, then delete
- [ ] Check disk space before each video generation
- [ ] If disk > 90% full: send warning notification
- [ ] Provide cleanup UI in Streamlit

---

### Phase 4: Multi-Account YouTube Authentication

#### 4.1 OAuth Flow for Multiple Accounts
- [ ] Function: `authenticate_youtube_account(channel_name)`
- [ ] Store tokens as: `tokens/channel_{channel_name}.json`
- [ ] Use Google OAuth flow with localhost redirect
- [ ] Streamlit button: "Authenticate YouTube Account"
- [ ] Opens browser for OAuth consent
- [ ] Stores credentials in secure location
- [ ] Supports multiple Google accounts simultaneously

#### 4.2 Upload Function
- [ ] Function: `upload_to_youtube(video_path, metadata, token_file)`
- [ ] Load credentials from channel-specific token file
- [ ] Set `selfDeclaredMadeForKids: False` (from our testing - critical!)
- [ ] Upload with resumable upload
- [ ] Return YouTube URL on success
- [ ] Handle quota errors, network errors
- [ ] Retry 3 times on failure

---

### Phase 5: Streamlit UI

#### 5.1 Home Page (Dashboard)
- [ ] List all channels in grid/card layout
- [ ] For each channel show:
  - Channel name
  - Status: "Active" / "Paused" / "Error"
  - Next post time
  - Last posted video (thumbnail + link)
  - Quick actions: View, Pause, Delete
- [ ] Button: "Add New Channel"
- [ ] Global controls: Start All / Stop All

#### 5.2 Channel Page (Individual Tab)
- [ ] Channel settings panel (sidebar):
  - [ ] Channel name (editable)
  - [ ] Theme (text input)
  - [ ] Tone (text input)
  - [ ] Style (text input)
  - [ ] Other info (large text area)
  - [ ] Post interval (number input in minutes)
  - [ ] Music volume (slider 0-100%)
  - [ ] Save button
- [ ] Main area:
  - [ ] Current status indicator (Idle / Generating / Uploading / Scheduled)
  - [ ] Live log viewer (last 100 logs, auto-refresh every 2 seconds)
  - [ ] Timeline showing next 5 scheduled posts
  - [ ] Video history table:
    - Thumbnail
    - Title
    - Post time
    - YouTube link
    - Status
- [ ] YouTube authentication section:
  - [ ] "Authenticate YouTube" button
  - [ ] Shows current auth status
- [ ] Manual controls:
  - [ ] "Generate Test Video" (doesn't upload)
  - [ ] "Start Channel" / "Pause Channel"
  - [ ] "Force Generate Now"

#### 5.3 Live Logs Display
- [ ] Query last 100 logs from database for current channel
- [ ] Color coding:
  - Info: Blue
  - Warning: Yellow
  - Error: Red
- [ ] Format: `[HH:MM:SS] [CATEGORY] Message`
- [ ] Auto-scroll to bottom
- [ ] Auto-refresh every 2 seconds using `st.experimental_rerun()`

#### 5.4 Browser Notifications
- [ ] Use JavaScript notification API
- [ ] Request permission on load
- [ ] Send notification when:
  - Video successfully posted
  - Critical error after 20 failures
  - Disk space warning
- [ ] Fallback: In-app toast notifications if permission denied

---

### Phase 6: Error Handling & Resilience

#### 6.1 Comprehensive Logging
- [ ] Log every step to database with timestamp
- [ ] Categories: script, voiceover, clip, music, assembly, upload
- [ ] Include error details, stack traces
- [ ] Log API response times
- [ ] Log file sizes and durations

#### 6.2 Error Tracking & Reporting
- [ ] Track error types per channel
- [ ] Increment counter for each error type
- [ ] After 20 identical errors:
  - Pause channel
  - Generate error report with Groq:
    ```python
    prompt = f"This error occurred 20 times: {error_details}.
    Provide a detailed diagnosis and suggested fixes for the user."
    ```
  - Display in UI with notification
  - Reset counter after manual intervention

#### 6.3 API Quota Detection
- [ ] Groq API: Check for quota errors in response
- [ ] Pexels API: Check rate limit headers
- [ ] Pixabay API: Check for quota exceeded message
- [ ] YouTube API: Check for quota errors (403)
- [ ] If quota exceeded:
  - Log detailed message
  - Calculate retry time
  - Schedule next attempt
  - Notify user

#### 6.4 Network Resilience
- [ ] All API calls wrapped in retry logic
- [ ] Exponential backoff: 1s, 2s, 4s, 8s, 16s
- [ ] Timeout for all network requests (30s)
- [ ] Handle connection errors, DNS errors, SSL errors
- [ ] Log all retry attempts

---

### Phase 7: Testing Plan

#### 7.1 Unit Tests
- [ ] Test `find_ffmpeg()` returns valid path
- [ ] Test script generation with mock Groq response
- [ ] Test voiceover generation creates valid MP3
- [ ] Test clip download from Pexels
- [ ] Test music download from Pixabay
- [ ] Test SRT subtitle generation
- [ ] Test all FFmpeg commands individually

#### 7.2 Integration Tests
- [ ] Test complete video generation pipeline
- [ ] Test with failing clip downloads (verify 20-retry works)
- [ ] Test with failing voiceover (verify gTTS fallback works)
- [ ] Test audio mixing at different volumes
- [ ] Test subtitle positioning and sizing
- [ ] Verify final video has audio stream

#### 7.3 End-to-End Tests
- [ ] Create test channel with 1-minute interval
- [ ] Generate and upload 3 test videos
- [ ] Verify all videos have:
  - Working audio (voiceover + music)
  - Visible but non-intrusive subtitles
  - 10 HD video clips
  - 60-second duration
  - Available without restrictions on YouTube
- [ ] Test daemon start/stop
- [ ] Test Streamlit UI connects to daemon
- [ ] Test multi-channel scenario (2 channels simultaneously)

#### 7.4 Error Simulation Tests
- [ ] Simulate Pexels API failure (verify 20-query retry)
- [ ] Simulate Groq API quota (verify error reporting)
- [ ] Simulate disk full (verify warning)
- [ ] Simulate YouTube auth failure (verify clear error)
- [ ] Simulate network outage (verify retry logic)
- [ ] Verify error counter reaches 20 and pauses channel

#### 7.5 Performance Tests
- [ ] Measure video generation time (target < 3 minutes)
- [ ] Test with 5 channels running simultaneously
- [ ] Monitor memory usage
- [ ] Monitor disk usage growth rate
- [ ] Test cleanup functionality

---

### Phase 8: Documentation & Deployment

#### 8.1 User Documentation
- [ ] Create `NEW_SYSTEM_GUIDE.md`:
  - How to set up first channel
  - How to authenticate YouTube accounts
  - How to configure channel settings
  - How to monitor logs
  - How to troubleshoot common errors
  - How to add Pixabay API key

#### 8.2 Deployment Checklist
- [ ] Add Pixabay API key to secrets.toml
- [ ] Ensure ffmpeg installed at known path
- [ ] Create `outputs/` directory
- [ ] Create `tokens/` directory for OAuth tokens
- [ ] Initialize SQLite database
- [ ] Start daemon process
- [ ] Launch Streamlit UI
- [ ] Test with one channel first

---

## Critical Lessons from Testing (MUST IMPLEMENT)

### From Our Previous Testing Session:

1. **FFmpeg Path Issues**
   - ✓ NEVER hardcode 'ffmpeg'
   - ✓ Use `find_ffmpeg()` to locate binary
   - ✓ Test: `/opt/homebrew/bin/ffmpeg`, `/usr/local/bin/ffmpeg`

2. **Audio Concat Method**
   - ✓ DO NOT use filter_complex for audio concat (caused exit code 254)
   - ✓ USE demuxer method: `ffmpeg -f concat -safe 0 -i list.txt -c copy output.mp3`
   - ✓ Accept DTS warnings (non-fatal)

3. **Voiceover Strategy**
   - ✓ gTTS as PRIMARY (unlimited, proven working)
   - ✓ ElevenLabs only if quota available
   - ✓ Speed up gTTS audio to 1.1x

4. **Subtitle Sizing**
   - ✓ Fontsize=20 (NOT 38-42, was covering entire video)
   - ✓ Use Arial font (NOT Impact)
   - ✓ Bottom alignment with MarginV=20

5. **YouTube Upload**
   - ✓ MUST set `selfDeclaredMadeForKids: False`
   - ✓ Otherwise videos restricted

6. **Audio Verification**
   - ✓ After final merge, check stderr for "Audio: aac"
   - ✓ Verify before upload, not after

7. **Clip Download Failures**
   - ✓ Generate alternative search queries with Groq
   - ✓ Try 20 different queries before giving up
   - ✓ Some queries fail due to no results

8. **Environment Variables**
   - ✓ Load secrets.toml BEFORE importing modules
   - ✓ Set os.environ before any video_gen imports

---

## File Structure

```
Osho-Content-Lab/
├── new_vid_gen.py              # Streamlit UI (main entry)
├── youtube_daemon.py           # Background service
├── video_engine.py             # Core video generation
├── channel_manager.py          # Database operations
├── music_manager.py            # Pixabay music downloads
├── auth_manager.py             # YouTube OAuth
├── channels.db                 # SQLite database
├── outputs/                    # Generated videos
│   ├── channel_1/
│   ├── channel_2/
│   └── ...
├── tokens/                     # YouTube OAuth tokens
│   ├── channel_Science.json
│   ├── channel_Ocean.json
│   └── ...
├── music_cache/                # Cached background music
├── .streamlit/
│   └── secrets.toml            # API keys (including Pixabay)
└── NEW_SYSTEM_GUIDE.md         # User documentation
```

---

## Implementation Order

1. ✅ Create implementation plan (this document)
2. Add Pixabay API key to secrets.toml
3. Build `video_engine.py` (core video generation)
4. Build `music_manager.py` (Pixabay integration)
5. Build `channel_manager.py` (database layer)
6. Build `auth_manager.py` (YouTube multi-auth)
7. Build `youtube_daemon.py` (background service)
8. Build `new_vid_gen.py` (Streamlit UI)
9. Run unit tests on each component
10. Run integration test (generate 1 complete video)
11. Run end-to-end test (3 videos with different themes)
12. Test multi-channel scenario
13. Test error handling and recovery
14. Create user documentation
15. Deploy and verify

---

## Success Criteria

- [ ] System can run 3+ channels simultaneously
- [ ] Each channel posts videos on exact schedule
- [ ] Videos have working audio (voiceover + music)
- [ ] Subtitles are properly sized and positioned
- [ ] All videos upload successfully to YouTube
- [ ] Error recovery works (20-retry for clips, 5-retry for other failures)
- [ ] Daemon runs independently when Streamlit closed
- [ ] UI displays live logs and status correctly
- [ ] Multi-account YouTube auth works
- [ ] Browser notifications work for errors
- [ ] File cleanup happens after successful uploads
- [ ] System handles API quota errors gracefully
- [ ] Generated videos are viral-quality (based on our testing standards)

---

## Estimated Timeline

- Phase 1-2 (Infrastructure + Video Engine): 2-3 hours
- Phase 3 (Daemon Service): 1 hour
- Phase 4 (YouTube Auth): 1 hour
- Phase 5 (Streamlit UI): 2 hours
- Phase 6 (Error Handling): 1 hour
- Phase 7 (Testing): 2-3 hours
- Phase 8 (Documentation): 30 mins

**Total: ~10-12 hours of focused development**

---

## Ready to Build!

This plan incorporates all lessons learned from our testing session, including:
- Proper FFmpeg usage
- Reliable audio concat method
- gTTS as primary voiceover
- Correct subtitle sizing
- YouTube upload settings
- Comprehensive error handling

Let's build the ultimate YouTube automation empire! 🚀
