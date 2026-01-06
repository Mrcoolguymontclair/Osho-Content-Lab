#!/bin/bash

echo "YouTube Shorts Automation - Setup Script"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 not found. Please install Python 3.9 or higher."
    exit 1
fi
echo "✓ Python OK"
echo ""

# Check FFmpeg
echo "Checking FFmpeg..."
ffmpeg -version > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ FFmpeg not found."
    echo "Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
    exit 1
fi
echo "✓ FFmpeg OK"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi
echo "✓ Dependencies installed"
echo ""

# Create secrets template
echo "Creating secrets template..."
mkdir -p .streamlit
if [ ! -f .streamlit/secrets.toml ]; then
    cat > .streamlit/secrets.toml << 'SECRETS'
# Add your API keys here
GROQ_API_KEY = "your_groq_api_key_here"
PEXELS_API_KEY = "your_pexels_api_key_here"
SECRETS
    echo "✓ Created .streamlit/secrets.toml"
    echo "⚠️  IMPORTANT: Edit .streamlit/secrets.toml and add your API keys!"
else
    echo "✓ secrets.toml already exists"
fi
echo ""

# Create music directory
echo "Creating music directory..."
mkdir -p music
if [ ! -f music/music_library.json ]; then
    cat > music/music_library.json << 'MUSIC'
{
  "music_files": [],
  "instructions": "Add your music files to the music/ folder and update this JSON with their tags. Run 'python3 add_music.py' to add songs interactively."
}
MUSIC
    echo "✓ Created music/music_library.json"
else
    echo "✓ music_library.json already exists"
fi
echo ""

# Create output directories
echo "Creating output directories..."
mkdir -p video_outputs
mkdir -p temp_videos
echo "✓ Directories created"
echo ""

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .streamlit/secrets.toml and add your API keys"
echo "2. Run: streamlit run new_vid_gen.py"
echo "3. (Optional) Add music: python3 add_music.py"
echo "4. (Optional) Start daemon: python3 youtube_daemon.py"
echo ""
