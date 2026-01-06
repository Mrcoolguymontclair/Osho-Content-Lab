# Background Music Library

## How to Add Music

1. **Download royalty-free music** from these sources:
   - [YouTube Audio Library](https://www.youtube.com/audiolibrary) - Completely free, no attribution needed
   - [Pixabay Music](https://pixabay.com/music/) - Free to download manually
   - [Free Music Archive](https://freemusicarchive.org/)
   - [Incompetech](https://incompetech.com/music/royalty-free/)
   - [Bensound](https://www.bensound.com/)

2. **Save music files** to this `music/` folder (MP3 format recommended)

3. **Update `music_library.json`** with your file information:

```json
{
  "filename": "your_music_file.mp3",
  "tags": ["energetic", "upbeat", "electronic"],
  "duration": 60,
  "notes": "Description of the music"
}
```

## Tag System

The AI generates videos with `musicKeywords` (like "energetic electronic" or "calm ambient"). The system matches these keywords to your music tags.

### Recommended Tags:

**Energy Level:**
- `energetic`, `high-energy`, `upbeat`, `fast`
- `calm`, `peaceful`, `relaxing`, `slow`
- `moderate`, `medium-paced`

**Genre:**
- `electronic`, `edm`, `synthwave`
- `acoustic`, `ambient`, `atmospheric`
- `rock`, `pop`, `hip-hop`
- `cinematic`, `orchestral`, `epic`

**Mood:**
- `exciting`, `motivational`, `inspiring`
- `dramatic`, `intense`, `powerful`
- `happy`, `cheerful`, `positive`
- `mysterious`, `dark`, `suspenseful`
- `chill`, `laid-back`, `smooth`

### Example Entry:

```json
{
  "filename": "upbeat_electronic_2024.mp3",
  "tags": ["energetic", "upbeat", "electronic", "fast", "exciting", "modern"],
  "duration": 60,
  "notes": "Fast-paced electronic track, great for tech/gaming content"
}
```

## How Matching Works

1. AI generates video with keywords like "energetic electronic"
2. System scores each music file based on tag matches
3. Best matching file is selected (or random from top matches)
4. Music is mixed with voiceover at your configured volume level

## Music Volume

Set the music volume in your channel settings (0-100%):
- 0% = No background music
- 15% = Recommended (subtle background)
- 30% = Moderate presence
- 50%+ = Music becomes prominent

The voiceover is always at full volume, music is mixed underneath.
