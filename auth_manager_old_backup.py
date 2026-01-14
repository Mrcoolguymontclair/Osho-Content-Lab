#!/usr/bin/env python3
"""
YOUTUBE MULTI-ACCOUNT AUTHENTICATION MANAGER
Handles OAuth for multiple YouTube channels.
Each channel gets its own token file for independent authentication.
"""

import os
import json
import pickle
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# YouTube API scopes - includes upload and full access
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube'
]

# Tokens directory
TOKENS_DIR = "tokens"
os.makedirs(TOKENS_DIR, exist_ok=True)

# ==============================================================================
# Authentication Functions
# ==============================================================================

def get_token_path(channel_name: str) -> str:
    """Get token file path for a channel"""
    safe_name = "".join(c if c.isalnum() else "_" for c in channel_name)
    return os.path.join(TOKENS_DIR, f"channel_{safe_name}.json")

def authenticate_channel(channel_name: str, client_secret: str = None) -> Tuple[bool, str]:
    """
    Authenticate a YouTube channel.

    If token exists and is valid, returns success immediately.
    Otherwise, initiates OAuth flow.

    Args:
        channel_name: Name of the channel
        client_secret: YouTube OAuth client secret JSON string

    Returns:
        (success, message/error)
    """
    token_path = get_token_path(channel_name)

    # Check for existing valid token
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

            # Check if token is valid
            if creds and creds.valid:
                return True, f"Channel '{channel_name}' already authenticated!"

            # Try to refresh expired token
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    save_credentials(creds, token_path)
                    return True, f"Channel '{channel_name}' token refreshed!"
                except Exception as refresh_error:
                    # Token can't be refreshed, delete it and require re-auth
                    print(f"Token refresh failed: {refresh_error}")
                    if os.path.exists(token_path):
                        os.remove(token_path)

        except Exception as e:
            print(f"Error loading existing token: {e}")
            # Delete corrupted token file
            if os.path.exists(token_path):
                os.remove(token_path)

    # Need new authentication
    if not client_secret:
        # Try to load from secrets
        try:
            import toml
            secrets = toml.load('.streamlit/secrets.toml')
            client_secret = secrets.get('YOUTUBE_CLIENT_SECRET', '')
        except:
            return False, "YouTube client secret not provided"

    if not client_secret:
        return False, "YouTube client secret not configured"

    # Parse client secret
    try:
        if isinstance(client_secret, str):
            client_config = json.loads(client_secret)
        else:
            client_config = client_secret
    except:
        return False, "Invalid YouTube client secret format"

    try:
        # Run OAuth flow
        flow = InstalledAppFlow.from_client_config(
            client_config,
            SCOPES,
            redirect_uri='http://localhost'
        )

        # This will open browser for authentication. Request offline access so we receive a refresh token
        creds = flow.run_local_server(
            port=0,
            authorization_prompt_message='',
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true'  # Must be lowercase string, not Python boolean
        )

        # Save credentials (preserving refresh token if needed)
        save_credentials(creds, token_path)

        return True, f"Channel '{channel_name}' authenticated successfully!"

    except Exception as e:
        return False, f"Authentication failed: {str(e)}"

def save_credentials(creds: Credentials, token_path: str):
    """Save credentials to file, preserving existing refresh token if missing from creds"""
    try:
        # Preserve an existing refresh_token if the new creds don't include it
        existing_refresh = None
        if os.path.exists(token_path):
            try:
                with open(token_path, 'r') as ef:
                    existing = json.load(ef)
                    existing_refresh = existing.get('refresh_token')
            except Exception:
                existing_refresh = None

        if not getattr(creds, 'refresh_token', None) and existing_refresh:
            try:
                creds.refresh_token = existing_refresh
            except Exception:
                pass

        # Write to temp file first, then rename (atomic operation)
        temp_path = token_path + '.tmp'
        with open(temp_path, 'w') as f:
            f.write(creds.to_json())
        os.replace(temp_path, token_path)
    except Exception as e:
        print(f"Failed to save credentials: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)

def is_channel_authenticated(channel_name: str) -> bool:
    """Check if a channel is authenticated"""
    token_path = get_token_path(channel_name)

    if not os.path.exists(token_path):
        return False

    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        return creds and creds.valid
    except:
        return False

def get_channel_credentials(channel_name: str) -> Optional[Credentials]:
    """Get valid credentials for a channel"""
    token_path = get_token_path(channel_name)

    if not os.path.exists(token_path):
        return None

    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                save_credentials(creds, token_path)
            except Exception as refresh_error:
                print(f"Token refresh failed for {channel_name}: {refresh_error}")
                # Delete bad token
                if os.path.exists(token_path):
                    os.remove(token_path)
                return None

        if creds and creds.valid:
            return creds

    except Exception as e:
        print(f"Error loading credentials for {channel_name}: {e}")
        # Delete corrupted token
        if os.path.exists(token_path):
            os.remove(token_path)

    return None

def get_youtube_service(channel_name: str):
    """
    Get authenticated YouTube API service for a channel.

    Args:
        channel_name: Name of the channel

    Returns:
        YouTube API service object or None if not authenticated
    """
    creds = get_channel_credentials(channel_name)

    if not creds:
        return None

    try:
        from googleapiclient.discovery import build
        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error building YouTube service: {e}")
        return None


def revoke_channel_auth(channel_name: str) -> bool:
    """Revoke authentication for a channel"""
    token_path = get_token_path(channel_name)

    if os.path.exists(token_path):
        try:
            os.remove(token_path)
            return True
        except:
            return False

    return False

# ==============================================================================
# Token refresh scheduler
# ==============================================================================

_refresh_scheduler_thread = None
_refresh_scheduler_running = False


def refresh_tokens_if_needed(grace_minutes: int = 5):
    """Refresh tokens that are expired or expiring within `grace_minutes` minutes.

    Walks the `tokens/` directory and refreshes any credential whose access token is
    expired or will expire within the grace window. Saves refreshed creds back to
    the file.
    """
    for fname in os.listdir(TOKENS_DIR):
        if not fname.endswith('.json'):
            continue

        token_path = os.path.join(TOKENS_DIR, fname)

        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            if not creds:
                continue

            now = datetime.utcnow()
            expiry = getattr(creds, 'expiry', None)
            needs_refresh = False

            if creds.expired:
                needs_refresh = True
            elif expiry and (expiry - now) < timedelta(minutes=grace_minutes):
                needs_refresh = True

            if needs_refresh:
                if creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        save_credentials(creds, token_path)
                        print(f"Refreshed token: {fname}")
                    except Exception as e:
                        print(f"Failed to refresh token for {fname}: {e}")
                else:
                    print(f"No refresh token for {fname}; re-auth required")

        except Exception as e:
            print(f"Error checking token {fname}: {e}")


def _refresh_scheduler(interval_minutes: int, grace_minutes: int):
    global _refresh_scheduler_running
    print(f"🔁 Token refresh scheduler started (interval={interval_minutes}m)")
    while _refresh_scheduler_running:
        try:
            refresh_tokens_if_needed(grace_minutes=grace_minutes)
        except Exception as e:
            print(f"Error in token refresh scheduler: {e}")
        time.sleep(interval_minutes * 60)
    print("🔁 Token refresh scheduler stopped")


def start_token_refresh_scheduler(interval_minutes: int = 60, grace_minutes: int = 5):
    """Start a background thread that refreshes tokens periodically.

    interval_minutes: how often to check/refresh tokens
    grace_minutes: refresh tokens that will expire within this many minutes
    """
    global _refresh_scheduler_thread, _refresh_scheduler_running
    if _refresh_scheduler_running:
        return

    _refresh_scheduler_running = True
    _refresh_scheduler_thread = threading.Thread(
        target=_refresh_scheduler,
        args=(interval_minutes, grace_minutes),
        daemon=True
    )
    _refresh_scheduler_thread.start()


def stop_token_refresh_scheduler():
    """Stop the background token refresh thread."""
    global _refresh_scheduler_thread, _refresh_scheduler_running
    if not _refresh_scheduler_running:
        return

    _refresh_scheduler_running = False
    if _refresh_scheduler_thread:
        _refresh_scheduler_thread.join(timeout=5)
        _refresh_scheduler_thread = None

# ==============================================================================
# YouTube Upload Functions
# ==============================================================================
def upload_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: List[str],
    channel_name: str,
    category_id: str = '24',  # Entertainment
    privacy: str = 'public'
) -> Tuple[bool, str]:
    """
    Upload video to YouTube.

    CRITICAL: Sets selfDeclaredMadeForKids: False (from our testing!)

    Args:
        video_path: Path to video file
        title: Video title
        description: Video description
        tags: List of tags
        channel_name: Name of channel to upload to
        category_id: YouTube category ID
        privacy: 'public', 'unlisted', or 'private'

    Returns:
        (success, youtube_url_or_error)
    """
    # Get credentials
    creds = get_channel_credentials(channel_name)

    if not creds:
        return False, f"Channel '{channel_name}' not authenticated"

    try:
        # Build YouTube API client
        youtube = build('youtube', 'v3', credentials=creds)

        # Video metadata
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy,
                'selfDeclaredMadeForKids': False  # CRITICAL - from our testing!
            }
        }

        # Upload video
        media = MediaFileUpload(
            video_path,
            resumable=True,
            chunksize=1024*1024  # 1MB chunks
        )

        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"Upload progress: {progress}%")

        video_id = response['id']
        youtube_url = f"https://youtube.com/watch?v={video_id}"

        return True, youtube_url

    except Exception as e:
        error_msg = str(e)

        # Check for quota errors
        if 'quota' in error_msg.lower():
            return False, f"YouTube API quota exceeded: {error_msg}"

        # Check for auth errors
        if 'auth' in error_msg.lower() or '401' in error_msg or '403' in error_msg:
            return False, f"Authentication error: {error_msg}"

        return False, f"Upload failed: {error_msg}"


def get_video_id_from_url(youtube_url: str) -> Optional[str]:
    """Extract video ID from a YouTube URL or return the ID if provided"""
    if not youtube_url:
        return None
    try:
        if 'v=' in youtube_url:
            return youtube_url.split('v=')[1].split('&')[0]
        if 'youtu.be/' in youtube_url:
            return youtube_url.split('youtu.be/')[1].split('?')[0]
        if len(youtube_url) == 11 and all(c.isalnum() or c in '-_' for c in youtube_url):
            return youtube_url
    except:
        return None
    return None


def upload_thumbnail(video_id: str, channel_name: str, thumbnail_path: str) -> Tuple[bool, str]:
    """Upload a thumbnail image to YouTube for the given video ID"""
    creds = get_channel_credentials(channel_name)
    if not creds:
        return False, f"Channel '{channel_name}' not authenticated"
    try:
        youtube = build('youtube', 'v3', credentials=creds)
        media = MediaFileUpload(thumbnail_path)
        request = youtube.thumbnails().set(videoId=video_id, media_body=media)
        response = request.execute()
        return True, "Thumbnail uploaded"
    except Exception as e:
        return False, f"Thumbnail upload failed: {str(e)}"


def get_youtube_channel_info(channel_name: str) -> Optional[Dict]:
    """Get YouTube channel information"""
    creds = get_channel_credentials(channel_name)

    if not creds:
        return None

    try:
        youtube = build('youtube', 'v3', credentials=creds)

        request = youtube.channels().list(
            part='snippet,statistics',
            mine=True
        )

        response = request.execute()

        if response.get('items'):
            channel = response['items'][0]
            profile_pic = None
            if 'thumbnails' in channel['snippet']:
                # Try to get the best quality thumbnail available
                thumbnails = channel['snippet']['thumbnails']
                if 'medium' in thumbnails:
                    profile_pic = thumbnails['medium']['url']
                elif 'default' in thumbnails:
                    profile_pic = thumbnails['default']['url']
                elif 'high' in thumbnails:
                    profile_pic = thumbnails['high']['url']

            return {
                'title': channel['snippet']['title'],
                'description': channel['snippet']['description'],
                'subscribers': channel['statistics'].get('subscriberCount', '0'),
                'views': channel['statistics'].get('viewCount', '0'),
                'videos': channel['statistics'].get('videoCount', '0'),
                'profile_picture': profile_pic
            }

    except Exception as e:
        print(f"Error getting channel info: {e}")

    return None

# ==============================================================================
# Helper Functions
# ==============================================================================

def generate_youtube_metadata(title: str, theme: str, additional_tags: List[str] = None) -> Dict:
    """
    Generate YouTube metadata (description, tags) optimized for YouTube Shorts algorithm.

    Returns: {title, description, tags}
    """
    # Extract key topic words from title for better SEO
    title_words = [word.lower() for word in title.split() if len(word) > 3]
    topic_hashtags = ' '.join([f"#{word}" for word in title_words[:5]])

    # Create engaging, SEO-optimized description
    description = f"""{title}

{topic_hashtags}

🎬 Subscribe for more {theme} content!
👍 Like if you enjoyed this!
💬 Comment your favorite!

#shorts #youtubeshorts {f'#{theme.lower().replace(" ", "")}'}"""

    # Generate SEO-optimized tags (relevant to content, not spam)
    tags = [
        'shorts',
        'youtube shorts',
        theme.lower(),
        'ranking',
        'top 5',
        'countdown'
    ]

    # Add title-specific tags
    for word in title_words[:5]:
        if word not in tags:
            tags.append(word)

    if additional_tags:
        tags.extend(additional_tags)

    # Limit to 15 tags (YouTube recommendation)
    tags = list(set(tags))[:15]  # Remove duplicates and limit

    return {
        'title': title,  # Use original title only, no variants
        'title_variants': [title],  # Only the original title
        'description': description,
        'tags': tags
    }
