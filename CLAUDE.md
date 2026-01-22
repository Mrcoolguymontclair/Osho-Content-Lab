# CLAUDE.md - AI Assistant Development Guide

**Last Updated:** 2026-01-22
**Repository:** Osho Content Lab - YouTube Shorts Automation System
**Purpose:** Comprehensive guide for AI assistants working on this codebase

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Codebase Architecture](#codebase-architecture)
3. [Directory Structure](#directory-structure)
4. [Key Technologies](#key-technologies)
5. [Development Workflows](#development-workflows)
6. [Git Conventions](#git-conventions)
7. [Code Conventions](#code-conventions)
8. [Configuration Management](#configuration-management)
9. [Testing Practices](#testing-practices)
10. [Deployment and Operations](#deployment-and-operations)
11. [AI Assistant Guidelines](#ai-assistant-guidelines)
12. [Common Tasks](#common-tasks)
13. [Key Files Reference](#key-files-reference)
14. [Troubleshooting](#troubleshooting)

---

## Project Overview

### Purpose
Osho Content Studio is an autonomous AI system for generating and uploading YouTube Shorts 24/7. It features:
- Multi-channel support with independent scheduling
- AI-powered viral topic selection
- Advanced analytics and self-optimization
- Bulletproof authentication (never-expire tokens)
- ML-based performance prediction
- A/B testing framework
- Real-time monitoring and recovery

### Current Status
- **Daemon:** Active with auto-restart
- **Auth:** Bulletproof (never expires)
- **Video Quality:** V2 engine (all fixes deployed)
- **Expected Performance:** 50-150 views per video (vs 5 before)

### Project Goals
1. Generate high-quality YouTube Shorts automatically
2. Optimize content strategy using AI/ML analytics
3. Maintain 24/7 operation with minimal intervention
4. Scale to multiple channels efficiently
5. Continuously improve through data-driven learning

---

## Codebase Architecture

### Architecture Pattern
**Modular Python System** with the following components:

```
┌─────────────────────────────────────────────────┐
│         Streamlit UI (new_vid_gen.py)          │
│      Multi-channel Management Dashboard        │
└────────────────────┬────────────────────────────┘
                     │ (API calls)
┌────────────────────▼────────────────────────────┐
│    YouTube Daemon (youtube_daemon.py)           │
│  - Thread per channel                          │
│  - Analytics worker thread                     │
│  - Trends worker thread                        │
│  - Quota monitor thread                        │
└────────────┬─────────────────────┬──────────────┘
             │                     │
    ┌────────▼─────────┐  ┌────────▼──────────┐
    │ Video Generation │  │ AI Analytics     │
    │ Engines (V2)     │  │ (Super Brain)    │
    │ - Groq LLM       │  │ - ML Predictor   │
    │ - Pexels Videos  │  │ - A/B Testing    │
    │ - TTS            │  │ - Retention Pred │
    └────────┬─────────┘  │ - Real-time Mon  │
             │            └────────┬─────────┘
    ┌────────▼─────────┐  ┌────────▼──────────┐
    │ YouTube API      │  │ SQLite Database  │
    │ - Upload         │  │ (channels.db)    │
    │ - Analytics      │  │ - Channels       │
    │ - Auth           │  │ - Videos         │
    └──────────────────┘  │ - Logs           │
                          │ - Analytics      │
                          └──────────────────┘
```

### Core Components

1. **Background Daemon** (`youtube_daemon.py`)
   - Continuous 24/7 operation
   - Multi-threaded channel management
   - Background workers for trends, analytics, and quotas

2. **Video Generation Pipeline** (`backend/video/`)
   - V2 engine with all quality fixes (RECOMMENDED)
   - Multiple engine variants for different use cases
   - AI-powered script generation via Groq LLM

3. **AI/ML Subsystems** (`backend/ai/`)
   - Performance prediction
   - A/B testing (Thompson Sampling)
   - Retention prediction
   - Topic similarity analysis
   - Real-time monitoring

4. **Database Layer** (`backend/utils/channel_manager.py`)
   - SQLite with 6 core tables
   - Thread-safe operations
   - Multi-channel support

5. **Streamlit UI** (`frontend/new_vid_gen.py`)
   - Live dashboard
   - Channel management
   - OAuth authentication
   - Schedule configuration

---

## Directory Structure

### Root Level: `/home/user/Osho-Content-Lab`

```
/
├── backend/                    # Organized backend modules
│   ├── ai/                    # AI and analytics systems
│   ├── config/                # Configuration management
│   ├── core/                  # Core daemon operations
│   ├── legacy/                # Backward compatibility
│   ├── utils/                 # Shared utilities
│   ├── video/                 # Video generation engines
│   └── workers/               # Background workers
│
├── frontend/                  # Streamlit UI interface
│   └── new_vid_gen.py        # Main dashboard
│
├── tests/                     # Unit and integration tests
│   ├── test_error_handler.py
│   ├── test_cache_manager.py
│   └── ...
│
├── music/                     # Background music library
│   ├── README.md             # Music tagging guide
│   └── music_library.json    # Music metadata
│
├── docs/                      # Comprehensive documentation
│   ├── COMPLETE_SYSTEM_STATUS.md
│   ├── AI_SUPER_BRAIN_GUIDE.md
│   ├── RASPBERRY_PI_DEPLOYMENT.md
│   └── ...
│
├── Root Python Files (~50)    # Entry points and utilities
│   ├── youtube_daemon.py     # Main daemon
│   ├── daemon_keeper.py      # Auto-restart wrapper
│   ├── cook_up.py            # On-demand generator
│   └── ...
│
├── Configuration Files
│   ├── .gitignore            # Git ignore rules
│   ├── .env.example          # Environment template
│   ├── requirements.txt      # Python dependencies
│   ├── pytest.ini            # Test configuration
│   ├── setup.sh              # Initial setup script
│   └── start.sh              # System starter
│
└── Database & Runtime
    ├── channels.db           # Main database (gitignored)
    ├── tokens/               # OAuth tokens (gitignored)
    ├── video_outputs/        # Generated videos (gitignored)
    └── *.log                 # Log files (gitignored)
```

### Backend Subdirectories

#### `/backend/ai/` - AI Subsystems
- `ai_super_brain.py` - Unified AI orchestrator
- `ai_ml_predictor.py` - ML performance prediction
- `multi_armed_bandit.py` - A/B testing framework
- `retention_predictor.py` - Retention analysis
- `topic_similarity.py` - Topic recommendations
- `realtime_monitor.py` - Performance tracking
- `ai_analyzer.py` - Pattern recognition
- `learning_loop.py` - 24h analytics cycle
- `ab_testing_framework.py` - A/B infrastructure
- `groq_manager.py` - LLM API management

#### `/backend/config/` - Configuration
- `constants.py` - **Centralized configuration values**
- `config_manager.py` - Config file management
- `auth_manager.py` - YouTube OAuth
- `auth_manager_bulletproof.py` - Enhanced auth
- `quota_manager.py` - API quota tracking

#### `/backend/core/` - Core Operations
- `youtube_daemon.py` - Main background service
- `daemon_keeper.py` - Auto-restart wrapper
- `youtube_analytics.py` - Analytics API integration

#### `/backend/workers/` - Background Workers
- `trend_analyzer.py` - Google Trends analysis
- `google_trends_fetcher.py` - Trend fetching
- `autonomous_learner.py` - Self-optimizing system

#### `/backend/video/` - Video Generation
- `video_engine_ranking_v2.py` - **RECOMMENDED V2 engine**
- `video_engine.py` - Standard generation
- `unified_video_generator.py` - Unified interface
- `title_thumbnail_optimizer.py` - SEO optimization
- `thumbnail_ai.py` - AI thumbnail generation
- `viral_topic_selector.py` - Viral topic selection

#### `/backend/utils/` - Utilities
- `channel_manager.py` - **Database operations hub**
- `logger.py` - Logging infrastructure
- `error_handler.py` - Error handling
- `error_recovery.py` - Retry logic
- `duplicate_detector.py` - Duplicate prevention
- `health_monitor.py` - System health
- `quality_checker.py` - Video quality validation

---

## Key Technologies

### Core Framework
- **Python 3.9+** - Primary language
- **Streamlit 1.50.0** - Web UI dashboard
- **SQLite** - Database (built-in, no installation needed)

### AI/LLM
- **Groq API** (PRIMARY) - Fast LLM for video scripts
  - Model: `llama-3.3-70b-versatile`
  - Fallback support with multiple API keys
- **Gemini API** (SECONDARY) - Backup LLM
- **Custom ML Models** - Performance prediction, A/B testing

### Video/Media Processing
- **FFmpeg** (REQUIRED) - Video encoding/processing
- **FFprobe** - Video analysis (comes with FFmpeg)
- **Pexels API** (REQUIRED) - Stock video clips (portrait-oriented)
- **Edge-TTS** - Text-to-speech narration
- **Pillow 11.1.0** - Image manipulation

### APIs & Integrations
- **YouTube API v3** (REQUIRED)
  - Video uploads (1600 quota per upload)
  - Analytics data
  - Channel management
- **Google OAuth 2.0** - Channel authentication
- **Google Trends** - Trending topics

### Key Dependencies
```python
streamlit==1.50.0              # UI framework
groq==1.0.0                    # LLM API
google-api-python-client==2.187.0  # YouTube API
google-auth==2.41.1            # OAuth
google-auth-oauthlib==1.2.3    # OAuth flow
edge-tts==7.2.7                # Text-to-speech
requests==2.32.5               # HTTP client
Pillow==11.1.0                 # Image processing
pytz==2024.1                   # Timezone support
```

---

## Development Workflows

### Initial Setup Workflow

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd Osho-Content-Lab
   ```

2. **Run Setup Script**
   ```bash
   ./setup.sh
   ```
   - Checks Python 3.9+
   - Verifies FFmpeg installation
   - Installs dependencies
   - Creates directory structure
   - Generates config templates

3. **Configure API Keys**
   - Edit `.streamlit/secrets.toml`:
     ```toml
     GROQ_API_KEY = "your_groq_api_key"
     PEXELS_API_KEY = "your_pexels_api_key"
     ```
   - OR set environment variables in `.env`

4. **Add Music (Optional)**
   ```bash
   python3 add_music.py
   ```
   - Add MP3 files to `music/` directory
   - Tag with moods: uplifting, dramatic, calm, energetic

5. **Start System**
   ```bash
   # Option 1: Streamlit UI
   streamlit run new_vid_gen.py

   # Option 2: Daemon (24/7 operation)
   python3 daemon_keeper.py &

   # Option 3: On-demand generation
   python3 cook_up.py
   ```

### Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b claude/<feature-description>-<session-id>
   ```
   - ALWAYS use `claude/` prefix
   - Include session ID for tracking
   - Example: `claude/improve-thumbnails-abc123`

2. **Make Changes**
   - Read relevant files first
   - Follow code conventions (see below)
   - Update constants in `backend/config/constants.py`
   - Add tests if needed

3. **Test Changes**
   ```bash
   # Run tests
   pytest
   pytest -m "not slow"  # Skip slow tests

   # Test specific functionality
   python3 cook_up.py --no-upload  # Test video generation
   ```

4. **Commit Changes**
   ```bash
   git add <files>
   git commit -m "Brief description of changes"
   ```
   - Use imperative mood: "Add feature" not "Added feature"
   - Focus on "why" not "what"
   - Reference issues if applicable

5. **Push to Branch**
   ```bash
   git push -u origin claude/<feature-description>-<session-id>
   ```
   - MUST match session ID
   - Will fail with 403 if branch name incorrect

6. **Create Pull Request**
   ```bash
   gh pr create --title "Feature description" --body "..."
   ```

### Continuous Operation Workflow

**Daemon Mode (Production):**
```bash
# Start with auto-restart
python3 daemon_keeper.py &

# Monitor logs
tail -f daemon_stdout.log

# Check status
ps aux | grep daemon_keeper

# Stop gracefully
pkill -f daemon_keeper
```

**On-Demand Mode (Testing):**
```bash
# Generate one video immediately
python3 cook_up.py

# Specific channel
python3 cook_up.py --channel "Channel Name"

# Generate without uploading
python3 cook_up.py --no-upload
```

---

## Git Conventions

### Branch Naming

**CRITICAL:** All development branches MUST follow this pattern:
```
claude/<description>-<session-id>
```

Examples:
- `claude/fix-audio-sync-abc123`
- `claude/improve-thumbnails-xyz789`
- `claude/add-new-engine-def456`

**Why:** Push operations are restricted to branches matching this pattern. Incorrect branch names will fail with HTTP 403.

### Commit Messages

**Format:**
```
<type>: <subject>

<body (optional)>
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code restructuring (no behavior change)
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `perf:` - Performance improvements
- `chore:` - Maintenance tasks

**Examples:**
```
feat: Add A/B testing framework for title optimization

Implements Thompson Sampling for adaptive testing. Automatically
shifts traffic to winning variants. Includes confidence intervals
and statistical significance checks.

fix: Resolve audio/video sync issue in V2 engine

Videos were ending with 2-3 seconds of silence. Fixed by trimming
audio precisely to match narration duration.

refactor: Modularize video engine into backend/video/

Moved all video generation code to backend/video/ for better
organization. No functional changes.
```

### Commit Frequency

- Commit logical units of work
- Don't commit half-finished features
- DO commit incremental progress (small, working changes)
- Use descriptive messages even for small commits

### Push Strategy

**ALWAYS use:**
```bash
git push -u origin <branch-name>
```

**Retry Logic:**
- If push fails due to network errors, retry up to 4 times
- Use exponential backoff: 2s, 4s, 8s, 16s
- For 403 errors (permission denied), check branch name pattern

**DON'T:**
- Force push to main/master: `git push --force origin main` ❌
- Push without branch tracking: `git push` (without -u on first push) ❌
- Skip hooks: `git push --no-verify` (unless explicitly needed) ❌

### Pull Request Conventions

**PR Title Format:**
```
<Type>: Brief description of changes
```

**PR Body Template:**
```markdown
## Summary
- Bullet point 1
- Bullet point 2
- Bullet point 3

## Changes Made
- File 1: What changed
- File 2: What changed

## Testing
- [ ] Manual testing completed
- [ ] Automated tests pass
- [ ] Video generation tested
- [ ] No regressions observed

## Impact
- Expected views improvement: +X%
- Performance impact: None/Minimal/Significant
- Breaking changes: Yes/No
```

---

## Code Conventions

### Python Style

**Follow PEP 8 with these specifics:**

1. **Imports**
   ```python
   # Standard library
   import os
   import sys
   from datetime import datetime

   # Third-party
   import streamlit as st
   from groq import Groq

   # Local
   from backend.config.constants import *
   from backend.utils.logger import logger
   from backend.utils.channel_manager import get_channel
   ```

2. **Naming Conventions**
   ```python
   # Constants (use backend/config/constants.py)
   SHORTS_WIDTH = 1080
   MAX_VIDEO_DURATION = 60

   # Functions (snake_case)
   def generate_video_script(topic, duration):
       pass

   # Classes (PascalCase)
   class VideoEngine:
       pass

   # Private functions/variables (leading underscore)
   def _internal_helper():
       pass
   ```

3. **Docstrings**
   ```python
   def upload_video(video_path, channel_id, metadata):
       """
       Upload a video to YouTube.

       Args:
           video_path (str): Path to video file
           channel_id (int): Channel ID from database
           metadata (dict): Title, description, tags

       Returns:
           str: YouTube video ID

       Raises:
           UploadError: If upload fails after retries
       """
       pass
   ```

4. **Error Handling**
   ```python
   from backend.utils.error_recovery import retry_with_backoff
   from backend.utils.logger import logger

   @retry_with_backoff(max_attempts=5)
   def api_call():
       try:
           result = external_api.call()
           return result
       except APIError as e:
           logger.error(f"API call failed: {e}")
           raise
       finally:
           cleanup_resources()
   ```

### Configuration Management

**ALWAYS use `backend/config/constants.py` for configuration values:**

```python
# ❌ DON'T hardcode values
video_width = 1080
max_duration = 60

# ✅ DO use constants
from backend.config.constants import SHORTS_WIDTH, MAX_VIDEO_DURATION

video_width = SHORTS_WIDTH
max_duration = MAX_VIDEO_DURATION
```

**Common Constants:**
- Video specs: `SHORTS_WIDTH`, `SHORTS_HEIGHT`, `SHORTS_FPS`
- Durations: `MIN_VIDEO_DURATION`, `MAX_VIDEO_DURATION`
- Intervals: `MIN_POSTING_INTERVAL`, `DEFAULT_POSTING_INTERVAL`
- Quotas: `YOUTUBE_QUOTA_DAILY_LIMIT`, `YOUTUBE_QUOTA_UPLOAD_COST`
- Timeouts: `VIDEO_DOWNLOAD_TIMEOUT`, `VIDEO_UPLOAD_TIMEOUT`
- Feature flags: `ENABLE_AB_TESTING`, `ENABLE_AI_ANALYTICS`

### Database Operations

**ALWAYS use `backend/utils/channel_manager.py`:**

```python
from backend.utils.channel_manager import (
    get_all_channels,
    get_channel,
    add_video,
    update_video,
    get_channel_videos
)

# Get channel data
channel = get_channel(channel_id)

# Add video record
video_id = add_video(
    channel_id=1,
    title="Video Title",
    youtube_id="abc123",
    status="uploaded"
)

# Update video with analytics
update_video(video_id, views=100, ctr=0.05)
```

**Available Functions:**
- Channel: `get_all_channels()`, `get_channel()`, `add_channel()`, `update_channel()`
- Video: `add_video()`, `update_video()`, `get_channel_videos()`, `get_video_id_from_url()`
- Analytics: `log_action()`, `log_error()`, `track_trend()`

### Logging

**Use centralized logger:**

```python
from backend.utils.logger import logger

# Info level (general operations)
logger.info("Starting video generation")

# Warning level (recoverable issues)
logger.warning("API quota running low: 2000/10000")

# Error level (failures)
logger.error(f"Failed to upload video: {error}")

# Debug level (detailed info)
logger.debug(f"Processing clip {i}/{total}")
```

### Video Generation Best Practices

1. **ALWAYS use V2 Engine** (`video_engine_ranking_v2.py`)
   ```python
   from backend.video.video_engine_ranking_v2 import generate_video

   video_path = generate_video(
       topic="Dangerous Animals",
       channel_id=1,
       engine_type="ranking"
   )
   ```

2. **Validate Before Generation**
   ```python
   from backend.utils.pre_generation_validator import validate_before_generation

   # Check channel, quota, duplicates
   is_valid, error_msg = validate_before_generation(channel_id, topic)
   if not is_valid:
       logger.error(f"Validation failed: {error_msg}")
       return
   ```

3. **Check Duplicates**
   ```python
   from backend.utils.duplicate_detector import is_duplicate_topic

   if is_duplicate_topic(topic, channel_id, days=30):
       logger.warning(f"Topic '{topic}' used recently, skipping")
       return
   ```

4. **Use Viral Topic Selector**
   ```python
   from backend.utils.viral_topic_selector import select_viral_topic

   topic = select_viral_topic(channel_id)
   logger.info(f"Selected viral topic: {topic}")
   ```

---

## Configuration Management

### Environment Variables

**Two Methods:**

1. **Streamlit Secrets** (Recommended for UI)
   - File: `.streamlit/secrets.toml`
   - Format:
     ```toml
     GROQ_API_KEY = "gsk_..."
     PEXELS_API_KEY = "..."
     ```
   - Access: `st.secrets["GROQ_API_KEY"]`

2. **Environment File** (For daemon/scripts)
   - File: `.env`
   - Format:
     ```bash
     GROQ_API_KEY=gsk_...
     PEXELS_API_KEY=...
     ```
   - Load: `python-dotenv` or manual

### Required API Keys

| Service | Required | Purpose | Get From |
|---------|----------|---------|----------|
| **Groq** | YES | LLM for video scripts | https://console.groq.com/keys |
| **Pexels** | YES | Stock video clips | https://www.pexels.com/api/ |
| **YouTube OAuth** | YES | Video uploads | https://console.cloud.google.com/ |
| Gemini | No | Backup LLM | https://aistudio.google.com/ |
| ElevenLabs | No | Premium TTS | https://elevenlabs.io/ |

### YouTube OAuth Setup

1. **Create Project** in Google Cloud Console
2. **Enable YouTube API v3**
3. **Create OAuth 2.0 Credentials** (Desktop app)
4. **Download JSON**, save as environment variable:
   ```bash
   YOUTUBE_CLIENT_SECRET='{"installed":{...}}'
   ```
5. **First Run:** Will open browser for authentication
6. **Tokens Saved:** In `tokens/<channel_name>/` directory
7. **Auto-refresh:** Tokens refresh automatically every 15 minutes

### Feature Flags

Located in `backend/config/constants.py`:

```python
# Enable/disable features
ENABLE_AB_TESTING = True           # A/B testing framework
ENABLE_AI_ANALYTICS = True         # AI Super Brain
ENABLE_AUTO_LEARNING = True        # Auto-optimization
ENABLE_VIRAL_TOPIC_SELECTOR = True # Viral topics
ENABLE_BACKGROUND_MUSIC = True     # Music in videos
ENABLE_QUALITY_ENHANCER = True     # Quality improvements
ENABLE_DUPLICATE_DETECTION = True  # Duplicate prevention
```

To disable a feature, set to `False` and restart daemon.

---

## Testing Practices

### Test Structure

Located in `/tests/`:
```
tests/
├── test_error_handler.py
├── test_cache_manager.py
├── test_config_manager.py
└── test_input_validator.py
```

### Running Tests

```bash
# Run all tests
pytest

# Skip slow tests
pytest -m "not slow"

# Verbose output
pytest -v

# Specific test file
pytest tests/test_error_handler.py

# Specific test function
pytest tests/test_error_handler.py::test_retry_logic
```

### Test Markers

Defined in `pytest.ini`:
- `@pytest.mark.slow` - Slow tests (API calls, long processing)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests

### Writing Tests

```python
import pytest
from backend.utils.error_handler import retry_with_backoff

class TestErrorHandler:
    def test_retry_success_on_third_attempt(self):
        """Test successful retry after 2 failures"""
        attempt = 0

        @retry_with_backoff(max_attempts=5)
        def flaky_function():
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                raise Exception("Temporary failure")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert attempt == 3

    @pytest.mark.slow
    def test_api_integration(self):
        """Test actual API call (slow)"""
        # Test real API integration
        pass
```

### Manual Testing

**Video Generation:**
```bash
# Test without uploading
python3 cook_up.py --no-upload

# Check video quality
ffprobe output/video.mp4

# Test specific topic
python3 -c "from backend.video.video_engine_ranking_v2 import generate_video; generate_video('Test Topic', 1)"
```

**Database Operations:**
```bash
# Check database
sqlite3 channels.db "SELECT * FROM channels;"
sqlite3 channels.db "SELECT * FROM videos ORDER BY created_at DESC LIMIT 10;"
```

**Authentication:**
```bash
# Test auth refresh
python3 -c "from backend.config.auth_manager import refresh_token; refresh_token(1)"
```

---

## Deployment and Operations

### System Requirements

**Minimum:**
- Python 3.9+
- 4GB RAM
- 20GB disk space
- FFmpeg installed
- Internet connection

**Recommended:**
- Python 3.10+
- 8GB RAM
- 100GB disk space
- SSD storage
- Stable internet (upload speed: 5+ Mbps)

**Raspberry Pi:**
- Pi 4 8GB or Pi 5 8GB
- 128GB+ microSD or NVMe SSD
- Active cooling (mandatory)
- See: `docs/RASPBERRY_PI_DEPLOYMENT.md`

### Production Deployment

1. **Initial Setup**
   ```bash
   # Clone and setup
   git clone <repo>
   cd Osho-Content-Lab
   ./setup.sh

   # Configure secrets
   nano .streamlit/secrets.toml

   # Add music (optional)
   python3 add_music.py
   ```

2. **Start Daemon**
   ```bash
   # With auto-restart (recommended)
   python3 daemon_keeper.py &

   # Monitor
   tail -f daemon_stdout.log

   # Check process
   ps aux | grep daemon_keeper
   ```

3. **Setup Auto-start** (Linux systemd)
   ```bash
   # Create service file
   sudo nano /etc/systemd/system/osho-daemon.service
   ```

   ```ini
   [Unit]
   Description=Osho Content Lab Daemon
   After=network.target

   [Service]
   Type=simple
   User=youruser
   WorkingDirectory=/home/youruser/Osho-Content-Lab
   ExecStart=/usr/bin/python3 /home/youruser/Osho-Content-Lab/daemon_keeper.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   # Enable and start
   sudo systemctl enable osho-daemon
   sudo systemctl start osho-daemon
   sudo systemctl status osho-daemon
   ```

### Monitoring

**Log Files:**
```bash
# Daemon output
tail -f daemon_stdout.log

# Daemon errors
tail -f daemon_stderr.log

# Application logs
tail -f *.log
```

**Database Monitoring:**
```bash
# Recent videos
sqlite3 channels.db "SELECT title, views, youtube_id FROM videos ORDER BY created_at DESC LIMIT 10;"

# Channel status
sqlite3 channels.db "SELECT name, status, last_post_at FROM channels;"

# Error tracking
sqlite3 channels.db "SELECT * FROM error_tracker ORDER BY timestamp DESC LIMIT 10;"
```

**System Health:**
```bash
# Check daemon
ps aux | grep daemon_keeper

# Check disk space
df -h

# Check memory
free -h

# Check API quotas (in Python)
python3 -c "from backend.config.quota_manager import check_quota; print(check_quota(1))"
```

### Maintenance Tasks

**Daily:**
- Check daemon is running
- Review logs for errors
- Monitor video performance

**Weekly:**
- Check API quotas
- Review analytics
- Backup database:
  ```bash
  cp channels.db channels.db.backup.$(date +%Y%m%d)
  ```

**Monthly:**
- Update dependencies:
  ```bash
  pip install -r requirements.txt --upgrade
  ```
- Clean old logs:
  ```bash
  find . -name "*.log" -mtime +30 -delete
  ```
- Review A/B test results:
  ```bash
  python3 ab_experiment_runner.py
  ```

### Troubleshooting Common Issues

**Daemon Not Running:**
```bash
# Check if process exists
ps aux | grep daemon

# Check logs
cat daemon_stderr.log

# Restart
pkill -f daemon_keeper
python3 daemon_keeper.py &
```

**Upload Failures:**
```bash
# Check quota
python3 -c "from backend.config.quota_manager import get_quota_usage; print(get_quota_usage(1))"

# Check auth
python3 -c "from backend.config.auth_manager import verify_token; verify_token(1)"

# Refresh token
python3 -c "from backend.config.auth_manager import refresh_token; refresh_token(1)"
```

**Video Generation Errors:**
```bash
# Check FFmpeg
ffmpeg -version

# Check API keys
python3 -c "import streamlit as st; st.secrets.load_if_toml_exists(); print(st.secrets.get('GROQ_API_KEY', 'NOT SET'))"

# Test generation
python3 cook_up.py --no-upload
```

---

## AI Assistant Guidelines

### When Working on This Codebase

1. **ALWAYS Read Before Modifying**
   - Read existing files completely before suggesting changes
   - Understand the full context of functions/classes
   - Check for dependencies and side effects

2. **Use Existing Infrastructure**
   - Use `backend/config/constants.py` for all configuration
   - Use `backend/utils/channel_manager.py` for all database operations
   - Use `backend/utils/logger.py` for all logging
   - Use `backend/utils/error_recovery.py` for retry logic

3. **Follow the Module Structure**
   - Backend code goes in `/backend/`
   - Frontend code goes in `/frontend/`
   - Tests go in `/tests/`
   - Documentation goes in `/docs/`
   - Root level is for entry points only

4. **Respect Feature Flags**
   - Check feature flags in `constants.py` before using features
   - Don't assume features are enabled
   - Document when new flags are needed

5. **Maintain Backward Compatibility**
   - Don't break existing API interfaces
   - Don't remove functions without checking usage
   - Deprecate gradually, don't delete immediately

6. **Security Considerations**
   - Never commit API keys or secrets
   - Check `.gitignore` before adding new file types
   - Sanitize user inputs
   - Use parameterized SQL queries (done via channel_manager)

7. **Performance Awareness**
   - Video generation is CPU-intensive
   - API calls have rate limits and quotas
   - Database operations should be efficient
   - Cache expensive operations

8. **Error Handling**
   - Always handle exceptions gracefully
   - Use retry logic for API calls
   - Log errors with context
   - Don't crash the daemon

### Understanding the Codebase

**Key Architectural Decisions:**

1. **Why SQLite?**
   - Simple, no separate server needed
   - Thread-safe with proper locking
   - Sufficient for multi-channel operation
   - Easy backups (single file)

2. **Why V2 Engine?**
   - V1 had audio sync issues (silence at end)
   - V1 had boring topics (landscapes, no views)
   - V2 fixes all quality issues
   - V2 uses viral topic selection

3. **Why Groq (not OpenAI)?**
   - Faster response times (important for generation)
   - Lower cost
   - llama-3.3-70b sufficient for scripts
   - Fallback to Gemini if needed

4. **Why Daemon + Streamlit?**
   - Daemon: 24/7 operation, no browser needed
   - Streamlit: Easy management UI, user-friendly
   - Separation of concerns: operations vs. management

5. **Why Thread-per-Channel?**
   - Independent scheduling per channel
   - Isolation (one channel failure doesn't affect others)
   - Parallel operations
   - Scalable to many channels

### Common Pitfalls to Avoid

1. **Don't Hardcode Paths**
   ```python
   # ❌ BAD
   music_path = "/home/user/music/song.mp3"

   # ✅ GOOD
   from backend.config.constants import MUSIC_DIR
   music_path = os.path.join(MUSIC_DIR, "song.mp3")
   ```

2. **Don't Skip Validation**
   ```python
   # ❌ BAD
   video_path = generate_video(topic, channel_id)
   upload_video(video_path, channel_id)

   # ✅ GOOD
   from backend.utils.pre_generation_validator import validate_before_generation

   is_valid, error = validate_before_generation(channel_id, topic)
   if not is_valid:
       logger.error(f"Validation failed: {error}")
       return

   video_path = generate_video(topic, channel_id)
   upload_video(video_path, channel_id)
   ```

3. **Don't Ignore Quotas**
   ```python
   # ❌ BAD
   for i in range(100):
       upload_video(video)  # Will exhaust quota!

   # ✅ GOOD
   from backend.config.quota_manager import check_quota, track_upload

   if check_quota(channel_id):
       upload_video(video)
       track_upload(channel_id)
   else:
       logger.warning("Quota exhausted, waiting...")
   ```

4. **Don't Create New Video Engines**
   - Use V2 engine unless you have specific reason
   - V1 engines kept for backward compatibility
   - If V2 needs fixes, fix V2, don't create V3

5. **Don't Break the Daemon**
   - Daemon runs 24/7, stability is critical
   - Always catch exceptions
   - Always log errors
   - Always clean up resources
   - Test thoroughly before deploying

### Code Review Checklist

Before committing, verify:

- [ ] Read all files before modifying
- [ ] Used constants from `backend/config/constants.py`
- [ ] Used `channel_manager.py` for database operations
- [ ] Used `logger.py` for all logging
- [ ] Added error handling with retry logic
- [ ] Validated inputs
- [ ] Checked for duplicates (if video generation)
- [ ] Tested manually (at least once)
- [ ] No hardcoded paths, API keys, or magic numbers
- [ ] No breaking changes to existing APIs
- [ ] Updated documentation if needed
- [ ] Followed naming conventions
- [ ] Added docstrings to new functions
- [ ] Cleaned up temporary files
- [ ] No debug print statements left behind

---

## Common Tasks

### Task: Add a New Video Engine

1. **Create Engine File**
   ```bash
   # Create in backend/video/
   touch backend/video/video_engine_<name>.py
   ```

2. **Implement Engine**
   ```python
   from backend.config.constants import *
   from backend.utils.logger import logger

   def generate_video_<name>(topic, channel_id, **kwargs):
       """
       Generate video using <name> engine.

       Args:
           topic (str): Video topic
           channel_id (int): Channel ID
           **kwargs: Additional parameters

       Returns:
           str: Path to generated video
       """
       logger.info(f"Generating video with <name> engine: {topic}")

       # Implementation

       return video_path
   ```

3. **Register in Unified Generator**
   ```python
   # Edit backend/video/unified_video_generator.py

   from backend.video.video_engine_<name> import generate_video_<name>

   ENGINES = {
       'standard': generate_video_standard,
       'ranking': generate_video_ranking,
       '<name>': generate_video_<name>,  # Add here
   }
   ```

4. **Update Constants**
   ```python
   # Edit backend/config/constants.py

   # Video engines
   AVAILABLE_ENGINES = ['standard', 'ranking', '<name>']
   DEFAULT_ENGINE = 'ranking'  # or '<name>'
   ```

5. **Test**
   ```bash
   python3 -c "from backend.video.unified_video_generator import generate_video; generate_video('Test', 1, engine='<name>')"
   ```

### Task: Add a New AI Feature

1. **Create Feature File**
   ```bash
   touch backend/ai/<feature_name>.py
   ```

2. **Implement Feature**
   ```python
   from backend.utils.channel_manager import get_channel_videos
   from backend.utils.logger import logger

   def analyze_<feature>(channel_id):
       """
       Analyze <feature> for channel.

       Args:
           channel_id (int): Channel ID

       Returns:
           dict: Analysis results
       """
       videos = get_channel_videos(channel_id)

       # Analysis logic

       return results
   ```

3. **Integrate with AI Super Brain**
   ```python
   # Edit ai_super_brain.py

   from backend.ai.<feature_name> import analyze_<feature>

   def get_ai_report(channel_id):
       # Existing code...

       # Add feature
       feature_results = analyze_<feature>(channel_id)
       report['<feature>'] = feature_results

       return report
   ```

4. **Add Feature Flag**
   ```python
   # Edit backend/config/constants.py

   ENABLE_<FEATURE> = True
   ```

5. **Test**
   ```bash
   python3 -c "from backend.ai.<feature_name> import analyze_<feature>; print(analyze_<feature>(1))"
   ```

### Task: Fix a Bug

1. **Reproduce the Bug**
   ```bash
   # Run the failing scenario
   python3 cook_up.py  # or other command

   # Check logs
   tail -f daemon_stdout.log
   ```

2. **Locate the Issue**
   ```python
   # Add debug logging
   from backend.utils.logger import logger

   logger.debug(f"Variable value: {variable}")
   ```

3. **Fix the Bug**
   - Understand root cause
   - Fix minimal code necessary
   - Don't refactor unrelated code

4. **Test the Fix**
   ```bash
   # Test the specific scenario
   python3 cook_up.py

   # Run relevant tests
   pytest tests/test_<relevant>.py
   ```

5. **Commit**
   ```bash
   git add <fixed_files>
   git commit -m "fix: Resolve <issue description>

   <Details about the fix>"
   git push -u origin claude/fix-<issue>-<session-id>
   ```

### Task: Optimize Performance

1. **Profile the Code**
   ```python
   import time

   start = time.time()
   # Code to profile
   end = time.time()
   logger.info(f"Operation took {end - start:.2f}s")
   ```

2. **Identify Bottleneck**
   - API calls? → Add caching
   - Database queries? → Optimize queries, add indexes
   - Video processing? → Optimize FFmpeg commands
   - File I/O? → Use async operations

3. **Implement Optimization**
   ```python
   # Example: Add caching
   from backend.utils.cache_manager import cache_result

   @cache_result(ttl=3600)
   def expensive_operation():
       # Implementation
       pass
   ```

4. **Measure Improvement**
   ```python
   # Before and after comparison
   logger.info(f"Old time: {old_time}s, New time: {new_time}s, Improvement: {(1 - new_time/old_time)*100:.1f}%")
   ```

### Task: Update Documentation

1. **Identify What Changed**
   - New features?
   - Changed behavior?
   - Deprecated functionality?

2. **Update Relevant Docs**
   - `README.md` - High-level overview
   - `CLAUDE.md` - This file (for AI assistants)
   - `docs/*.md` - Specific feature guides
   - Docstrings - Function/class documentation

3. **Update Examples**
   - Code snippets should work
   - Commands should be tested
   - Screenshots should be current

4. **Commit Docs**
   ```bash
   git add *.md docs/*.md
   git commit -m "docs: Update documentation for <feature>"
   ```

---

## Key Files Reference

### Critical Files (Do Not Delete)

| File | Size | Purpose | Notes |
|------|------|---------|-------|
| `youtube_daemon.py` | 42.9 KB | Main 24/7 daemon | Core system, handles all automation |
| `backend/video/video_engine_ranking_v2.py` | 28.8 KB | Video generation (V2) | BEST engine, all fixes applied |
| `frontend/new_vid_gen.py` | 80+ KB | Streamlit dashboard | User interface for management |
| `backend/utils/channel_manager.py` | 22.9 KB | Database operations | All DB access goes through this |
| `backend/config/constants.py` | 10.5 KB | Configuration hub | All constants defined here |
| `backend/config/auth_manager.py` | 22.4 KB | YouTube OAuth | Authentication and token refresh |
| `ai_super_brain.py` | 17.3 KB | AI orchestrator | Unified AI intelligence |
| `cook_up.py` | 9.2 KB | On-demand generator | Quick video generation |

### Entry Points

| File | Purpose | Usage |
|------|---------|-------|
| `youtube_daemon.py` | 24/7 automation | `python3 youtube_daemon.py` |
| `daemon_keeper.py` | Auto-restart wrapper | `python3 daemon_keeper.py &` |
| `cook_up.py` | On-demand generation | `python3 cook_up.py [--channel NAME] [--no-upload]` |
| `frontend/new_vid_gen.py` | UI dashboard | `streamlit run new_vid_gen.py` |
| `ai_super_brain.py` | AI analytics | `python3 ai_super_brain.py` |
| `ab_experiment_runner.py` | A/B test analysis | `python3 ab_experiment_runner.py` |
| `add_music.py` | Add music to library | `python3 add_music.py` |
| `setup.sh` | Initial setup | `./setup.sh` |

### Configuration Files

| File | Purpose | Format |
|------|---------|--------|
| `.streamlit/secrets.toml` | API keys (UI) | TOML |
| `.env` | Environment variables | Shell |
| `backend/config/constants.py` | Application constants | Python |
| `requirements.txt` | Python dependencies | pip |
| `pytest.ini` | Test configuration | INI |
| `music/music_library.json` | Music metadata | JSON |

### Database Schema

**File:** `channels.db` (SQLite)

**Tables:**
1. `channels` - Channel configurations
   - id, name, youtube_channel_id, status, schedule, etc.

2. `videos` - Video records
   - id, channel_id, title, youtube_id, views, ctr, retention, etc.

3. `logs` - Operation logs
   - id, channel_id, message, level, timestamp

4. `error_tracker` - Error tracking
   - id, channel_id, error_type, error_message, timestamp

5. `trends` - Trend data
   - id, topic, search_volume, region, fetched_at

6. `ml_models` - ML model data
   - id, model_type, model_data, trained_at

---

## Troubleshooting

### Issue: Daemon Won't Start

**Symptoms:**
- `daemon_keeper.py` exits immediately
- No `daemon.pid` file created
- Errors in `daemon_stderr.log`

**Solutions:**
1. Check Python version: `python3 --version` (need 3.9+)
2. Check dependencies: `pip3 install -r requirements.txt`
3. Check FFmpeg: `ffmpeg -version`
4. Check API keys: `cat .streamlit/secrets.toml`
5. Check logs: `cat daemon_stderr.log`
6. Check database: `sqlite3 channels.db "SELECT COUNT(*) FROM channels;"`

### Issue: Upload Failures

**Symptoms:**
- Videos generate but don't upload
- "403 Forbidden" errors
- "Quota exceeded" errors

**Solutions:**
1. **Check Authentication:**
   ```bash
   python3 -c "from backend.config.auth_manager import verify_token; verify_token(1)"
   ```

2. **Refresh Token:**
   ```bash
   python3 -c "from backend.config.auth_manager import refresh_token; refresh_token(1)"
   ```

3. **Check Quota:**
   ```bash
   python3 -c "from backend.config.quota_manager import get_quota_usage; print(get_quota_usage(1))"
   ```

4. **Reset Quota (if new day):**
   ```bash
   python3 -c "from backend.config.quota_manager import reset_quota; reset_quota(1)"
   ```

5. **Re-authenticate:**
   - Delete `tokens/<channel_name>/` directory
   - Run `streamlit run new_vid_gen.py`
   - Click "Connect to YouTube" for the channel

### Issue: Poor Video Quality

**Symptoms:**
- Low views (< 10)
- Black screens
- Audio/video out of sync
- Boring topics

**Solutions:**
1. **Verify V2 Engine:**
   ```bash
   grep -r "video_engine_ranking_v2" youtube_daemon.py cook_up.py
   ```
   - Should be using V2, not V1

2. **Check Viral Topics:**
   ```bash
   python3 -c "from backend.utils.viral_topic_selector import select_viral_topic; print(select_viral_topic(1))"
   ```
   - Should return interesting topics (not landscapes)

3. **Test Video Generation:**
   ```bash
   python3 cook_up.py --no-upload
   ```
   - Watch generated video
   - Check for issues

4. **Check Feature Flags:**
   ```python
   from backend.config.constants import (
       ENABLE_VIRAL_TOPIC_SELECTOR,
       ENABLE_QUALITY_ENHANCER
   )
   print(f"Viral Topics: {ENABLE_VIRAL_TOPIC_SELECTOR}")
   print(f"Quality Enhancer: {ENABLE_QUALITY_ENHANCER}")
   ```

### Issue: Database Corruption

**Symptoms:**
- "database locked" errors
- "database disk image is malformed"
- Daemon crashes frequently

**Solutions:**
1. **Backup Database:**
   ```bash
   cp channels.db channels.db.backup.$(date +%Y%m%d)
   ```

2. **Check Integrity:**
   ```bash
   sqlite3 channels.db "PRAGMA integrity_check;"
   ```

3. **Repair (if corrupted):**
   ```bash
   sqlite3 channels.db ".recover" | sqlite3 channels_repaired.db
   mv channels.db channels_corrupted.db
   mv channels_repaired.db channels.db
   ```

4. **Restore from Backup:**
   ```bash
   cp channels.db.backup.YYYYMMDD channels.db
   ```

### Issue: Memory/CPU Usage High

**Symptoms:**
- System slow
- Daemon using > 2GB RAM
- CPU at 100%

**Solutions:**
1. **Check Running Processes:**
   ```bash
   ps aux | grep python
   ```
   - Kill duplicate daemons if found

2. **Reduce Posting Frequency:**
   - Edit channel settings
   - Increase posting interval (e.g., 6 hours instead of 2)

3. **Limit Concurrent Channels:**
   - Deactivate unused channels
   - Daemon uses one thread per active channel

4. **Optimize FFmpeg:**
   - Check `backend/config/constants.py`
   - Consider using "faster" preset instead of "medium"

5. **Clean Temp Files:**
   ```bash
   rm -rf temp_videos/*
   rm -rf video_outputs/*
   ```

### Issue: API Rate Limits

**Symptoms:**
- "Rate limit exceeded"
- "Too many requests"
- Delays in generation

**Solutions:**
1. **Groq Rate Limit:**
   - 30 requests/minute
   - Add delay between calls
   - Use multiple API keys for rotation

2. **Pexels Rate Limit:**
   - 200 requests/minute
   - Cache video results
   - Reduce clip count in videos

3. **YouTube Rate Limit:**
   - 10000 quota/day
   - Each upload costs 1600
   - Max ~6 uploads/day per channel
   - Use quota tracking to stay within limits

### Getting Help

**Check Documentation:**
1. `README.md` - Quick start and overview
2. `COMPLETE_SYSTEM_STATUS.md` - Full technical documentation
3. `AI_SUPER_BRAIN_GUIDE.md` - AI features guide
4. `docs/` - Specific feature guides

**Check Logs:**
```bash
# Daemon logs
tail -100 daemon_stdout.log
tail -100 daemon_stderr.log

# Database logs
sqlite3 channels.db "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 20;"

# Error tracking
sqlite3 channels.db "SELECT * FROM error_tracker ORDER BY timestamp DESC LIMIT 20;"
```

**Debug Mode:**
```python
# Edit backend/config/constants.py
DEBUG_MODE = True
VERBOSE_LOGGING = True
SAVE_DEBUG_FILES = True
```

---

## Changelog

### 2026-01-22
- Initial creation of CLAUDE.md
- Comprehensive documentation of codebase structure
- Development workflows and conventions
- AI assistant guidelines

### Future Updates
- Update when major architectural changes occur
- Update when new features are added
- Update when conventions change
- Keep synchronized with actual codebase

---

## Quick Reference

### Most Common Commands

```bash
# Start system
python3 daemon_keeper.py &

# Generate one video
python3 cook_up.py

# Open UI
streamlit run new_vid_gen.py

# Check status
tail -f daemon_stdout.log

# Stop system
pkill -f daemon_keeper

# Run tests
pytest -m "not slow"

# Check database
sqlite3 channels.db "SELECT * FROM channels;"
```

### Most Important Files

1. `youtube_daemon.py` - Main daemon
2. `backend/video/video_engine_ranking_v2.py` - Video generation
3. `backend/config/constants.py` - All configuration
4. `backend/utils/channel_manager.py` - All database ops
5. `frontend/new_vid_gen.py` - UI dashboard

### Most Important Concepts

1. **Always use V2 engine** for video generation
2. **Always use constants.py** for configuration
3. **Always use channel_manager.py** for database
4. **Always check quotas** before uploading
5. **Always validate** before generating
6. **Always log** operations and errors
7. **Always handle** exceptions gracefully

---

**End of CLAUDE.md**

*This document should be updated whenever significant changes are made to the codebase architecture, workflows, or conventions.*
