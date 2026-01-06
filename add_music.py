#!/usr/bin/env python3
"""
Helper script to add music files to the library.
Makes it easy to tag and catalog your music files.
"""

import json
import os
from mutagen import File as MutagenFile

LIBRARY_FILE = "music/music_library.json"

def get_duration(filepath):
    """Get duration of audio file in seconds"""
    try:
        audio = MutagenFile(filepath)
        if audio and audio.info:
            return int(audio.info.length)
    except:
        pass
    return 60  # Default

def load_library():
    """Load existing library"""
    if os.path.exists(LIBRARY_FILE):
        with open(LIBRARY_FILE, 'r') as f:
            return json.load(f)
    return {"music_files": [], "instructions": "Music library for YouTube automation"}

def save_library(library):
    """Save library to file"""
    with open(LIBRARY_FILE, 'w') as f:
        json.dump(library, f, indent=2)
    print(f"\n✓ Library saved to {LIBRARY_FILE}")

def add_music_interactive():
    """Interactive CLI to add music"""
    library = load_library()

    print("\n🎵 Add Music to Library")
    print("=" * 50)

    # List existing files in music directory
    music_dir = "music"
    existing_files = [f for f in os.listdir(music_dir)
                     if f.endswith(('.mp3', '.wav', '.m4a', '.ogg'))
                     and not f.startswith('.')]

    # Get already cataloged files
    cataloged = [m['filename'] for m in library['music_files']]
    uncataloged = [f for f in existing_files if f not in cataloged]

    if uncataloged:
        print(f"\nFound {len(uncataloged)} uncataloged file(s):")
        for i, filename in enumerate(uncataloged, 1):
            print(f"  {i}. {filename}")
    else:
        print("\nNo new music files found in music/ folder")
        print("Add .mp3 files to the music/ folder first!")
        return

    print("\n")
    filename = input("Enter filename to catalog (or press Enter to skip): ").strip()

    if not filename:
        print("Cancelled.")
        return

    if filename not in uncataloged:
        print(f"Error: '{filename}' not found in music folder")
        return

    filepath = os.path.join(music_dir, filename)

    # Get metadata
    print(f"\nCataloging: {filename}")
    print("-" * 50)

    tags_input = input("Tags (comma-separated, e.g., energetic,electronic,upbeat): ").strip()
    tags = [t.strip() for t in tags_input.split(',') if t.strip()]

    notes = input("Notes (optional description): ").strip()

    # Auto-detect duration
    duration = get_duration(filepath)
    print(f"Duration: {duration} seconds (auto-detected)")

    # Create entry
    entry = {
        "filename": filename,
        "tags": tags,
        "duration": duration,
        "notes": notes if notes else ""
    }

    # Add to library
    library['music_files'].append(entry)

    # Save
    save_library(library)

    print("\n✓ Music added to library!")
    print(f"  Filename: {filename}")
    print(f"  Tags: {', '.join(tags)}")
    print(f"  Duration: {duration}s")

def list_music():
    """List all music in library"""
    library = load_library()

    if not library['music_files']:
        print("\n📁 Music library is empty")
        return

    print(f"\n🎵 Music Library ({len(library['music_files'])} files)")
    print("=" * 70)

    for i, music in enumerate(library['music_files'], 1):
        print(f"\n{i}. {music['filename']}")
        print(f"   Tags: {', '.join(music['tags'])}")
        print(f"   Duration: {music['duration']}s")
        if music.get('notes'):
            print(f"   Notes: {music['notes']}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_music()
    else:
        add_music_interactive()
