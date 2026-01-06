# Music Setup Guide

Your YouTube automation system now supports background music with smart tag-based matching!

## 🎵 Quick Start

### Step 1: Download Music

Go to **[YouTube Audio Library](https://www.youtube.com/audiolibrary)** (100% free, no attribution needed):

1. Browse or search for music
2. Filter by mood, genre, duration
3. Download MP3 files (aim for 60-90 second tracks for YouTube Shorts)
4. Save them to the `music/` folder

**Other Free Sources:**
- [Pixabay Music](https://pixabay.com/music/) - Free downloads
- [Free Music Archive](https://freemusicarchive.org/)
- [Incompetech](https://incompetech.com/music/royalty-free/)

### Step 2: Add Music to Library

**Option A: Using the helper script (recommended)**
```bash
# Put your .mp3 files in the music/ folder, then run:
python3 add_music.py

# It will prompt you to:
# 1. Select a file
# 2. Add tags (energetic, calm, electronic, etc.)
# 3. Add optional notes
```

**Option B: Manually edit music_library.json**
```bash
# Open music/music_library.json and add:
{
  "filename": "your_track.mp3",
  "tags": ["energetic", "upbeat", "electronic"],
  "duration": 60,
  "notes": "High energy electronic track"
}
```

### Step 3: Enable Music in Channel Settings

1. Open Streamlit app: http://localhost:8501
2. Click "View" on your channel
3. Go to "Settings" tab
4. Set "Music Volume %" to 15-30% (recommended)
5. Click "Save Settings"

### Step 4: Generate a Video

The system will automatically:
1. AI generates video script with `musicKeywords` (e.g., "energetic electronic")
2. System matches keywords to your music tags
3. Best matching track is selected
4. Music is mixed with voiceover at your volume setting

## 📋 Tagging Guide

### Good Tag Examples

**Energetic Content (gaming, sports, tech):**
```json
{
  "filename": "high_energy_electronic.mp3",
  "tags": ["energetic", "upbeat", "electronic", "fast", "exciting", "modern"],
  "duration": 60
}
```

**Calm Content (nature, meditation, education):**
```json
{
  "filename": "peaceful_ambient.mp3",
  "tags": ["calm", "peaceful", "ambient", "slow", "relaxing", "atmospheric"],
  "duration": 75
}
```

**Dramatic Content (storytelling, mysteries):**
```json
{
  "filename": "cinematic_epic.mp3",
  "tags": ["dramatic", "cinematic", "epic", "intense", "orchestral"],
  "duration": 90
}
```

## 🎚️ Volume Recommendations

- **0%** = No music (voiceover only)
- **10-15%** = Subtle background (recommended for most content)
- **20-30%** = Noticeable music presence
- **40-50%** = Music prominent (use for music-focused content)
- **60%+** = Very loud (not recommended, may overpower voice)

## 🔍 How Matching Works

1. **AI generates script** with music keywords like "energetic electronic"
2. **System parses keywords**: ["energetic", "electronic"]
3. **Scores each music file**:
   - "high_energy_electronic.mp3" tags: ["energetic", "electronic"] → Score: 2/2 ✓
   - "peaceful_ambient.mp3" tags: ["calm", "peaceful"] → Score: 0/2
4. **Selects best match** (randomly picks from top-scoring files)

## 📁 File Organization Tips

**Organize by mood:**
```
music/
├── energetic_track_1.mp3
├── energetic_track_2.mp3
├── calm_ambient_1.mp3
├── calm_ambient_2.mp3
├── dramatic_epic_1.mp3
└── music_library.json
```

**Name files descriptively:**
- ✅ `energetic_electronic_upbeat.mp3`
- ✅ `calm_piano_peaceful.mp3`
- ❌ `track_01.mp3`
- ❌ `download_xyz.mp3`

## 🛠️ Helper Commands

```bash
# Add music interactively
python3 add_music.py

# List all cataloged music
python3 add_music.py list

# View library file
cat music/music_library.json
```

## ⚠️ Important Notes

1. **Only use royalty-free music** - YouTube Content ID will flag copyrighted music
2. **60-90 second tracks work best** for YouTube Shorts
3. **Add variety** - Include different moods/genres for different content types
4. **Test volume levels** - Start at 15% and adjust based on your preference
5. **Keep files under 5MB** each for faster processing

## 🎬 Video Generation With Music

When you generate a video, you'll see logs like:
```
✓ Selected: 'energetic_electronic.mp3' (score: 2/2)
✓ Background music ready
✓ Audio mixed
```

The music will be automatically mixed with the voiceover, playing throughout the entire video at your configured volume.

---

**Questions?** Check the logs in the "Status & Logs" tab to see which music was selected and any matching details.
