# Ranking Video Generation Implementation Plan

## Overview
Implement a ranking-style video format that displays 5 clips in ascending order (5→1), with persistent overlays showing title, ranking sidebar, and live captions.

## Current System vs Ranking Format

### Current System
- Generates single-topic videos with sequential segments
- Each segment has: narration, video clip, subtitles
- No persistent visual ranking or countdown structure

### New Ranking System
- **5 distinct ranked moments** instead of sequential segments
- **Persistent ranking sidebar** (left side, numbers 1-5)
- **Title bar at top** with ranking theme
- **Live captions** for each moment
- **Countdown structure** building to #1

## Implementation Plan

### Phase 1: Script Generation Changes

**Update AI Prompt Structure:**
```python
# Current: generates sequential segments about one topic
# New: generates 5 ranked items with titles

{
  "title": "Ranking Funniest Fails",
  "theme": "Funniest Fails",
  "adjective": "Funny",  # Used for "Most Funny" at #1
  "ranked_items": [
    {
      "rank": 5,
      "title": "Slippery Slope",
      "narration": "This guy thought he could...",
      "searchQuery": "person slipping ice fail",
      "duration": 12
    },
    {
      "rank": 4,
      "title": "Wrong Button",
      "narration": "She pressed the wrong...",
      "searchQuery": "elevator button fail funny",
      "duration": 12
    },
    // ... ranks 3, 2, 1
  ]
}
```

**Key Changes:**
- Each item needs a short **title** (2-4 words) for sidebar
- Items ordered 5→1 (ascending quality/intensity)
- Clear **adjective** for ranking (funniest, scariest, best, etc.)

### Phase 2: Video Overlay System

**New Visual Components:**

1. **Title Bar (Top Center)**
   - Text: "Ranking [adjective] [category]"
   - Position: Top 10% of frame
   - Style: Bold, semi-transparent background
   - Persistent throughout video

2. **Ranking Sidebar (Left Side)**
   - Numbers 1-5 vertically stacked
   - Position: Left edge, centered vertically
   - Each number with space for title text
   - Highlight current rank as it plays
   - Style:
     ```
     5 [Slippery Slope]
     4 [Wrong Button]
     3 [Epic Timing]
     2 [Gravity Wins]
     1 [What Just Happened??]  ← highlighted when playing
     ```

3. **Live Captions (Upper-Middle)**
   - Current narration text
   - Position: Below title, above video center
   - Standard subtitle styling

**FFmpeg Overlay Implementation:**
```bash
# Pseudo-code for overlay layers
ffmpeg -i base_video.mp4 \
  # Title bar overlay
  -vf "drawtext=text='Ranking Funniest Fails':x=(w-text_w)/2:y=50:fontsize=48:fontcolor=white:box=1:boxcolor=black@0.7" \
  # Ranking sidebar (5 text layers, one per rank)
  -vf "drawtext=text='5 Slippery Slope':x=20:y=200:fontsize=32" \
  -vf "drawtext=text='4 Wrong Button':x=20:y=280:fontsize=32" \
  # ... etc
  # Current rank highlight
  -vf "drawbox=x=10:y=190:w=250:h=60:color=yellow@0.3:t=fill" \
  output.mp4
```

### Phase 3: Video Assembly Pipeline Changes

**Modify `assemble_viral_video()` function:**

1. **Pre-Generation:**
   - Create ranking sidebar image/overlay
   - Generate title bar graphic
   - Prepare all text overlays

2. **Per-Clip Assembly:**
   - Download clip for current rank
   - Add rank highlight to sidebar
   - Add live captions for narration
   - Maintain title bar throughout

3. **Final Assembly:**
   - Concatenate clips (5→4→3→2→1 order)
   - Apply persistent overlays
   - Add music snippet
   - Mix voiceover

### Phase 4: Database Schema (Optional)

Add ranking metadata to videos table:
```sql
ALTER TABLE videos ADD COLUMN video_type TEXT DEFAULT 'standard';
-- video_type: 'standard' or 'ranking'

ALTER TABLE videos ADD COLUMN ranking_data TEXT;
-- JSON: {"theme": "Funniest Fails", "adjective": "Funny", "items": [...]}
```

## Technical Challenges & Solutions

### Challenge 1: Persistent Overlays
**Problem:** FFmpeg subtitle burns can't be persistent across different clips
**Solution:** Use `drawtext` filter for all text, apply to final concatenated video

### Challenge 2: Sidebar Updates
**Problem:** Highlighting current rank as video progresses
**Solution:**
- Option A: Create 5 separate overlay videos, apply per segment
- Option B: Use timestamp-based drawtext with enable expressions
- **Recommended:** Option A (simpler, more reliable)

### Challenge 3: Video Pacing
**Problem:** 5 clips need consistent timing for 60s total
**Solution:** Each clip = 12 seconds (5 clips × 12s = 60s)

### Challenge 4: Search Query Quality
**Problem:** Need specific, rankable moments (not generic content)
**Solution:** Update AI prompt to generate queries for SPECIFIC moments/fails/goals

## File Structure Changes

### New Files:
```
overlay_templates/
  └── ranking_sidebar.png      # Template for sidebar
  └── title_bar_template.png   # Template for title

video_engine_ranking.py         # New: Ranking-specific video generation
ranking_prompts.py              # New: AI prompts for ranking content
```

### Modified Files:
```
video_engine.py                 # Add ranking mode
new_vid_gen.py                  # UI for ranking vs standard videos
channel_manager.py              # Track video type
```

## Implementation Steps

### Step 1: Update Script Generation (1-2 hours)
- [ ] Create new Groq prompt template for ranking videos
- [ ] Add title/adjective extraction
- [ ] Ensure 5 distinct items with clear progression
- [ ] Test with various ranking themes

### Step 2: Design Overlay Graphics (1 hour)
- [ ] Create sidebar background/template
- [ ] Design title bar layout
- [ ] Choose fonts and colors (high contrast for readability)
- [ ] Create highlight effect for current rank

### Step 3: Implement FFmpeg Overlays (2-3 hours)
- [ ] Add drawtext filters for title bar
- [ ] Add drawtext filters for ranking sidebar
- [ ] Implement rank highlighting
- [ ] Test overlay positioning on 1080x1920 canvas

### Step 4: Modify Video Assembly (2-3 hours)
- [ ] Update assemble_viral_video() for ranking mode
- [ ] Add per-clip overlay application
- [ ] Ensure proper concatenation with overlays
- [ ] Test full pipeline end-to-end

### Step 5: UI Integration (1 hour)
- [ ] Add ranking video option to Streamlit UI
- [ ] Let users choose: "Standard" vs "Ranking" format
- [ ] Update channel settings for default video type

### Step 6: Testing & Refinement (1-2 hours)
- [ ] Generate test ranking videos
- [ ] Verify readability on mobile (most important)
- [ ] Adjust timing/pacing if needed
- [ ] Fine-tune overlay positions

**Total Estimated Time:** 8-12 hours

## Example Output Structure

```
Video Timeline:
0:00-0:12  Rank 5: "Slippery Slope" plays
           [Sidebar shows all 5, #5 highlighted]
           [Title: "Ranking Funniest Fails"]
           [Caption: narration about this clip]

0:12-0:24  Rank 4: "Wrong Button" plays
           [#4 now highlighted in sidebar]
           [Title remains persistent]
           [New caption for this clip]

... continues through ranks 3, 2, 1

0:48-0:60  Rank 1: "What Just Happened??" plays
           [#1 highlighted - THE BEST ONE]
           [Maximum engagement here]
```

## Prompting Strategy for AI

### Ranking Video Prompt Template:
```
Generate a viral YouTube Shorts ranking video script.

THEME: {theme from channel config}
FORMAT: Countdown ranking of 5 distinct moments/items

Your task:
1. Create a catchy ranking title: "Ranking [superlative] [category]"
   Examples: "Ranking Craziest Sports Moments", "Ranking Funniest Pet Fails"

2. Choose an adjective that scales (funny→funniest, scary→scariest, good→best)

3. Generate 5 DISTINCT items ranked from LEAST to MOST [adjective]:
   - Rank 5: Decent but not amazing
   - Rank 4: Good, getting better
   - Rank 3: Really good
   - Rank 2: Excellent
   - Rank 1: THE BEST, most [adjective]

4. For each item provide:
   - Short punchy title (2-4 words)
   - 1-2 sentence narration explaining why it's at this rank
   - Specific search query for Pexels (concrete moment, not generic)

IMPORTANT:
- Items must clearly progress in quality/intensity
- Make #1 unmistakably the BEST
- Keep narration concise (under 100 characters)
- Search queries should find SPECIFIC moments, not stock footage

Output JSON format:
{
  "title": "Ranking ...",
  "adjective": "...",
  "theme": "...",
  "ranked_items": [
    {
      "rank": 5,
      "title": "...",
      "narration": "...",
      "searchQuery": "...",
      "duration": 12
    },
    ...
  ]
}
```

## Next Steps After Seeing Picture

Once you share the picture, I can refine:
- **Exact positioning** of title, sidebar, captions
- **Color scheme** and styling
- **Font choices** and sizes
- **Highlight effects** for current rank
- **Transition animations** between ranks

Please share the image so I can see the specific visual layout you want to replicate!
