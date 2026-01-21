"""
Application Constants

Centralized location for all magic numbers and configuration constants
used throughout the Osho Content Lab application.
"""

# ==============================================================================
# Video Specifications
# ==============================================================================

# YouTube Shorts dimensions
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
SHORTS_ASPECT_RATIO = 9 / 16
SHORTS_FPS = 30
SHORTS_BITRATE = '4M'
SHORTS_AUDIO_BITRATE = '192k'

# Video duration
MIN_VIDEO_DURATION = 15  # seconds
MAX_VIDEO_DURATION = 60  # seconds
TARGET_VIDEO_DURATION = 45  # seconds

# Video quality
VIDEO_CODEC = 'libx264'
AUDIO_CODEC = 'aac'
VIDEO_PRESET = 'medium'  # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
VIDEO_CRF = 23  # Quality (0-51, lower is better, 23 is default)

# ==============================================================================
# API Configuration
# ==============================================================================

# YouTube API
YOUTUBE_API_VERSION = 'v3'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_UPLOAD_CATEGORY_ID = '24'  # Entertainment
YOUTUBE_DEFAULT_PRIVACY = 'public'  # public, private, unlisted

# YouTube API Quota
YOUTUBE_QUOTA_DAILY_LIMIT = 10000
YOUTUBE_QUOTA_UPLOAD_COST = 1600
YOUTUBE_QUOTA_SEARCH_COST = 100
YOUTUBE_QUOTA_VIDEO_LIST_COST = 1

# Pexels API
PEXELS_API_BASE_URL = 'https://api.pexels.com/v1'
PEXELS_VIDEOS_PER_PAGE = 15
PEXELS_MIN_VIDEO_DURATION = 5  # seconds
PEXELS_ORIENTATION = 'portrait'

# Groq API
GROQ_MODEL_DEFAULT = 'llama-3.3-70b-versatile'
GROQ_TEMPERATURE_DEFAULT = 0.7
GROQ_MAX_TOKENS_DEFAULT = 2000
GROQ_TIMEOUT_SECONDS = 30

# ==============================================================================
# Timing and Intervals
# ==============================================================================

# Posting intervals (seconds)
MIN_POSTING_INTERVAL = 3600  # 1 hour
MAX_POSTING_INTERVAL = 86400  # 24 hours
DEFAULT_POSTING_INTERVAL = 14400  # 4 hours

# Background workers
TRENDS_WORKER_INTERVAL = 21600  # 6 hours
ANALYTICS_WORKER_INTERVAL = 21600  # 6 hours
LEARNING_LOOP_INTERVAL = 21600  # 6 hours
AUTO_REFRESH_INTERVAL = 900  # 15 minutes (for auth tokens)

# Retry configuration
DEFAULT_RETRY_ATTEMPTS = 5
DEFAULT_RETRY_BASE_DELAY = 2  # seconds (exponential backoff base)
MAX_RETRY_DELAY = 300  # 5 minutes
NETWORK_RETRY_ATTEMPTS = 4

# Timeouts
DEFAULT_NETWORK_TIMEOUT = 30  # seconds
VIDEO_DOWNLOAD_TIMEOUT = 300  # 5 minutes
VIDEO_UPLOAD_TIMEOUT = 1800  # 30 minutes
FFmpeg_TIMEOUT = 600  # 10 minutes

# ==============================================================================
# File and Storage
# ==============================================================================

# Directories
TOKENS_DIR = 'tokens'
TOKENS_BACKUP_DIR = 'tokens_backup'
MUSIC_DIR = 'music'
LOGS_DIR = 'logs'
TEMP_DIR = 'temp'
OUTPUT_DIR = 'output'

# File sizes
MAX_LOG_SIZE = 10485760  # 10MB
LOG_BACKUP_COUNT = 5
MAX_VIDEO_FILE_SIZE = 104857600  # 100MB (YouTube Shorts limit)

# Database
DATABASE_NAME = 'channels.db'
DATABASE_BACKUP_SUFFIX = '.backup'

# ==============================================================================
# Error Handling
# ==============================================================================

# Error thresholds
ERROR_THRESHOLD = 999999  # NEVER pause - always auto-recover
MAX_CONSECUTIVE_ERRORS = 10
ERROR_RECOVERY_DELAY = 60  # seconds

# ==============================================================================
# Content Generation
# ==============================================================================

# Ranking videos
MIN_RANKING_ITEMS = 3
MAX_RANKING_ITEMS = 10
DEFAULT_RANKING_ITEMS = 5

# Script generation
MIN_SCRIPT_LENGTH = 100  # characters
MAX_SCRIPT_LENGTH = 500  # characters
TARGET_SCRIPT_LENGTH = 300  # characters

# Title and description
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 5000
MAX_TAGS_COUNT = 30
MAX_TAG_LENGTH = 30

# ==============================================================================
# AI and Analytics
# ==============================================================================

# Performance thresholds
HIGH_PERFORMING_VIEWS = 1000
VIRAL_VIEWS_THRESHOLD = 10000
EXCELLENT_VIEW_RATE = 0.5  # 50% view rate
GOOD_VIEW_RATE = 0.3  # 30% view rate

# A/B testing
MIN_SAMPLES_FOR_AB_TEST = 10
AB_TEST_CONFIDENCE_LEVEL = 0.95
AB_TEST_MIN_IMPROVEMENT = 0.1  # 10% improvement

# Prediction confidence
HIGH_CONFIDENCE_THRESHOLD = 0.8
MEDIUM_CONFIDENCE_THRESHOLD = 0.5
LOW_CONFIDENCE_THRESHOLD = 0.3

# ==============================================================================
# Audio Configuration
# ==============================================================================

# Voice settings
TTS_VOICE_DEFAULT = 'en-US-AriaNeural'
TTS_RATE = '+10%'
TTS_VOLUME = '+0%'
TTS_PITCH = '+0Hz'

# Background music
MUSIC_VOLUME = 0.1  # 10% of original volume
MUSIC_FADE_DURATION = 2  # seconds

# ==============================================================================
# Viral Content Categories
# ==============================================================================

# Topic weights (higher = more likely to be selected)
VIRAL_TOPIC_WEIGHTS = {
    'dangerous_animals': 10,
    'extreme_jobs': 8,
    'mysterious_places': 7,
    'survival_facts': 9,
    'historical_secrets': 6,
    'science_mysteries': 7,
    'criminal_cases': 8,
    'natural_disasters': 7,
    'space_discoveries': 6,
    'ocean_mysteries': 8
}

# Topic cooldown (prevent same topic too soon)
TOPIC_COOLDOWN_HOURS = 24

# ==============================================================================
# Rate Limiting
# ==============================================================================

# API rate limits (requests per minute)
PEXELS_RATE_LIMIT = 200
GROQ_RATE_LIMIT = 30
YOUTUBE_RATE_LIMIT = 10

# ==============================================================================
# Authentication
# ==============================================================================

# OAuth token refresh
TOKEN_REFRESH_THRESHOLD = 43200  # 12 hours before expiry
TOKEN_PROACTIVE_REFRESH = 86400  # 24 hours before expiry
TOKEN_REFRESH_CHECK_INTERVAL = 900  # 15 minutes

# OAuth scopes
YOUTUBE_SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

# ==============================================================================
# Validation Limits
# ==============================================================================

# Input validation
MIN_CHANNEL_NAME_LENGTH = 1
MAX_CHANNEL_NAME_LENGTH = 100
MIN_SEARCH_QUERY_LENGTH = 1
MAX_SEARCH_QUERY_LENGTH = 500
MAX_FILENAME_LENGTH = 255

# ==============================================================================
# FFmpeg Configuration
# ==============================================================================

# FFmpeg commands
FFMPEG_COMMAND = 'ffmpeg'
FFPROBE_COMMAND = 'ffprobe'
FFMPEG_LOGLEVEL = 'error'  # quiet, panic, fatal, error, warning, info, verbose, debug

# FFmpeg filters
FFMPEG_SCALE_FILTER = f'scale={SHORTS_WIDTH}:{SHORTS_HEIGHT}:force_original_aspect_ratio=increase'
FFMPEG_CROP_FILTER = f'crop={SHORTS_WIDTH}:{SHORTS_HEIGHT}'

# ==============================================================================
# Feature Flags
# ==============================================================================

# Enable/disable features
ENABLE_AB_TESTING = True
ENABLE_AI_ANALYTICS = True
ENABLE_AUTO_LEARNING = True
ENABLE_VIRAL_TOPIC_SELECTOR = True
ENABLE_BACKGROUND_MUSIC = True
ENABLE_QUALITY_ENHANCER = True
ENABLE_DUPLICATE_DETECTION = True

# ==============================================================================
# Daemon Configuration
# ==============================================================================

# Daemon settings
DAEMON_CHECK_INTERVAL = 60  # seconds
DAEMON_HEARTBEAT_INTERVAL = 300  # 5 minutes
DAEMON_SHUTDOWN_TIMEOUT = 30  # seconds

# PID file
PID_FILE = 'youtube_daemon.pid'

# ==============================================================================
# Streamlit UI
# ==============================================================================

# UI refresh rates
UI_REFRESH_INTERVAL = 5  # seconds
UI_LOG_MAX_LINES = 100
UI_CHART_MAX_POINTS = 50

# ==============================================================================
# Health Monitoring
# ==============================================================================

# Health check thresholds
HEALTH_CHECK_INTERVAL = 300  # 5 minutes
HEALTHY_RESPONSE_TIME = 5  # seconds
DISK_SPACE_WARNING_THRESHOLD = 1073741824  # 1GB
MEMORY_WARNING_THRESHOLD = 0.9  # 90% memory usage

# ==============================================================================
# Cache Configuration
# ==============================================================================

# Cache TTLs (Time To Live)
ANALYTICS_CACHE_TTL = 3600  # 1 hour
TRENDS_CACHE_TTL = 21600  # 6 hours
CHANNEL_INFO_CACHE_TTL = 86400  # 24 hours

# Cache sizes
MAX_CACHE_SIZE = 1000  # items
MAX_CACHE_MEMORY = 104857600  # 100MB

# ==============================================================================
# Debug Configuration
# ==============================================================================

# Debug modes
DEBUG_MODE = False
VERBOSE_LOGGING = False
SAVE_DEBUG_FILES = False


if __name__ == '__main__':
    # Display all constants
    print("Osho Content Lab - Constants")
    print("=" * 70)

    sections = [
        ('Video Specifications', ['SHORTS_', 'VIDEO_', 'AUDIO_', 'MIN_VIDEO', 'MAX_VIDEO', 'TARGET_VIDEO']),
        ('API Configuration', ['YOUTUBE_', 'PEXELS_', 'GROQ_']),
        ('Timing and Intervals', ['INTERVAL', 'RETRY', 'TIMEOUT', 'DELAY']),
        ('File and Storage', ['DIR', 'DATABASE', 'LOG']),
        ('Content Generation', ['RANKING', 'SCRIPT', 'TITLE', 'DESCRIPTION', 'TAG']),
        ('Feature Flags', ['ENABLE_']),
    ]

    for section_name, prefixes in sections:
        print(f"\n{section_name}:")
        print("-" * 70)
        for key, value in sorted(globals().items()):
            if key.startswith('__') or key in ['print', 'sections', 'section_name', 'prefixes', 'key', 'value']:
                continue
            if any(key.startswith(prefix) for prefix in prefixes):
                print(f"  {key:40s} = {value}")

    print("\n" + "=" * 70)
    print("[OK] All constants loaded successfully")
