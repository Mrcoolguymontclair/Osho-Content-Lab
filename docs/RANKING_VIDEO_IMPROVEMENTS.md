# Ranking Video Quality Improvements

## Issues Fixed

### 1. Extremely Low Video Quality (41 kb/s → 4000 kb/s)
**Problem:** Videos were being compressed to only 41 kb/s bitrate, making them look terrible on YouTube Shorts
**Root Cause:** FFmpeg encoding settings were too aggressive (CRF 23, fast preset)
**Fix:** Updated encoding parameters in [video_engine_ranking.py:376-382](video_engine_ranking.py#L376-L382)
- Changed CRF from 23 → 18 (higher quality)
- Changed preset from 'fast' → 'medium' (better compression)
- Added explicit bitrate target: 4000k
- Added maxrate: 5000k and bufsize: 8000k for consistent quality
- Increased timeout from 60s → 90s to accommodate higher quality encoding

### 2. Low Frame Rate (12.94 fps → 30 fps)
**Problem:** Videos had abnormally low frame rate causing choppy playback
**Fix:** Added explicit `-r 30` flag to force 30 fps output

### 3. Chronological Alignment Issues
**Problem:** Clips were being assembled in random order instead of countdown (5→4→3→2→1)
**Root Cause:** AI-generated ranked_items array wasn't sorted before processing
**Fix:** Added sorting in [video_engine_ranking.py:272](video_engine_ranking.py#L272)
```python
ranked_items = sorted(ranked_items, key=lambda x: x['rank'], reverse=True)
```

### 4. Ranking Sidebar Positioning Wrong
**Problem:** Sidebar displayed ranks upside down (rank 1 at top, rank 5 at bottom)
**Root Cause:** Y-position calculation was `y = 400 + (rank-1)*200`, putting lower ranks higher on screen
**Fix:** Fixed calculation in [video_engine_ranking.py:207](video_engine_ranking.py#L207)
```python
y_pos = sidebar_start_y + (5 - rank) * item_height
```
Now properly displays: Rank 5 at top (y=400), Rank 1 at bottom (y=1200)

### 5. Spoiler Issue - All Ranks Visible At Start
**Problem:** All 5 ranks shown from the beginning, spoiling the countdown reveal
**Root Cause:** Overlay loop didn't filter based on current rank being played
**Fix:** Added progressive reveal logic in [video_engine_ranking.py:202](video_engine_ranking.py#L202)
```python
if rank < current_rank:
    continue  # Skip ranks not yet revealed
```
Now ranks appear progressively:
- Clip 1 (rank 5): Only #5 visible
- Clip 2 (rank 4): #5 and #4 visible
- Clip 3 (rank 3): #5, #4, #3 visible
- Clip 4 (rank 2): #5, #4, #3, #2 visible
- Clip 5 (rank 1): All 5 ranks visible (full list)

### 6. Background Clips Not Visible
**Problem:** Videos showing black screen instead of background video clips
**Root Cause:** Overlay PNG not properly supporting RGBA transparency for compositing
**Fix:** Added explicit RGBA pixel format in [video_engine_ranking.py:234](video_engine_ranking.py#L234) and format=auto in overlay filter
```python
'-pix_fmt', 'rgba',  # Ensure PNG has proper alpha channel
```
And in overlay compositing [video_engine_ranking.py:383](video_engine_ranking.py#L383):
```python
overlay=0:0:format=auto  # Auto-detect alpha format for proper transparency
```

### 7. Generic "Ranking Video" Titles
**Problem:** All videos titled "Ranking Video" instead of actual generated titles
**Root Cause:** generate_ranking_video() only returned video path, not the script title
**Fix:** Modified function signature in [video_engine_ranking.py:510](video_engine_ranking.py#L510) to return title:
```python
def generate_ranking_video(channel_config: Dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    # Returns: (video_path, title, error_message)
```
Updated daemon in [youtube_daemon.py:152](youtube_daemon.py#L152) to use actual title:
```python
video_path, title, error = generate_ranking_video(channel)
```
Now videos will have descriptive titles like "Ranking Most Amazing Natural Wonders"

## Expected Results

### Before
- Bitrate: 41 kb/s
- FPS: 12.94
- Quality: Unwatchable, heavily pixelated
- Duration: Variable/incorrect
- Order: Random/incorrect
- Sidebar: Upside down

### After
- Bitrate: 4000 kb/s (100x improvement)
- FPS: 30 (smooth playback)
- Quality: High-quality suitable for YouTube Shorts
- Duration: Exactly 60 seconds (5 clips × 12 seconds each)
- Order: Proper countdown (5→4→3→2→1)
- Sidebar: Correct positioning with rank 5 at top

## Technical Details

### New FFmpeg Encoding Parameters
```bash
-c:v libx264         # H.264 codec
-preset medium       # Balanced speed/quality
-crf 18             # Very high quality (lower = better)
-b:v 4000k          # Target bitrate 4 Mbps
-maxrate 5000k      # Max bitrate 5 Mbps
-bufsize 8000k      # Buffer size for rate control
-r 30               # Force 30 fps output
```

### File Size Impact
- Before: ~540 KB for 1:47 video (extremely compressed)
- After: ~5-8 MB for 1:00 video (appropriate for YouTube Shorts)

## Testing
Daemon has been restarted with these improvements. Next ranking video generated will use the new high-quality settings and proper ordering.
