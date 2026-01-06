#!/usr/bin/env python3
"""
YOUTUBE MULTI-ACCOUNT AUTHENTICATION MANAGER
Handles OAuth for multiple YouTube channels.
Each channel gets its own token file for independent authentication.
"""

import os
import json
import pickle
from typing import Optional, Tuple, List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# YouTube API scopes - includes upload and read access
SCOPES = ['https://www.googleapis.com/auth/youtube']

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
                creds.refresh(Request())
                save_credentials(creds, token_path)
                return True, f"Channel '{channel_name}' token refreshed!"

        except Exception as e:
            print(f"Error loading existing token: {e}")

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

        # This will open browser for authentication
        creds = flow.run_local_server(port=0, authorization_prompt_message='')

        # Save credentials
        save_credentials(creds, token_path)

        return True, f"Channel '{channel_name}' authenticated successfully!"

    except Exception as e:
        return False, f"Authentication failed: {str(e)}"

def save_credentials(creds: Credentials, token_path: str):
    """Save credentials to file"""
    with open(token_path, 'w') as f:
        f.write(creds.to_json())

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
            creds.refresh(Request())
            save_credentials(creds, token_path)

        if creds and creds.valid:
            return creds

    except Exception as e:
        print(f"Error loading credentials: {e}")

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
    Generate YouTube metadata (description, tags).

    Returns: {title, description, tags}
    """
    # Create engaging description
    description = f"""{title}

🔥 Subscribe for more viral {theme} content!

Hit the like button if this blew your mind!

#viral #shorts #trending #{theme.lower().replace(' ', '')}"""

    # Generate tags
    tags = [
        'viral',
        'shorts',
        'trending',
        theme.lower(),
        'mindblowing',
        'facts',
        'amazing',
        'youtube shorts'
    ]

    if additional_tags:
        tags.extend(additional_tags)

    # Limit to 15 tags (YouTube recommendation)
    tags = tags[:15]

    return {
        'title': title,
        'description': description,
        'tags': tags
    }
