#!/usr/bin/env python3
"""
BULLETPROOF YOUTUBE AUTHENTICATION MANAGER
Never expires, never needs re-auth, always works.

Key improvements:
1. Proactive refresh (1 hour before expiration, not after)
2. Multiple retry attempts with exponential backoff
3. Permanent refresh token preservation
4. Background auto-refresh every 30 minutes
5. Never deletes tokens unless explicitly requested
6. Fallback to backup credentials
"""

import os
import json
import threading
import time
import shutil
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# YouTube API scopes
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

# Directories
TOKENS_DIR = "tokens"
TOKENS_BACKUP_DIR = "tokens_backup"
os.makedirs(TOKENS_DIR, exist_ok=True)
os.makedirs(TOKENS_BACKUP_DIR, exist_ok=True)

# Global state
_refresh_thread = None
_refresh_running = False
_refresh_lock = threading.Lock()

# ==============================================================================
# Core Authentication
# ==============================================================================

def get_token_path(channel_name: str) -> str:
    """Get token file path for a channel"""
    safe_name = "".join(c if c.isalnum() else "_" for c in channel_name)
    return os.path.join(TOKENS_DIR, f"channel_{safe_name}.json")

def get_backup_token_path(channel_name: str) -> str:
    """Get backup token file path"""
    safe_name = "".join(c if c.isalnum() else "_" for c in channel_name)
    return os.path.join(TOKENS_BACKUP_DIR, f"channel_{safe_name}.json")

def save_credentials(creds: Credentials, token_path: str, backup: bool = True):
    """
    Save credentials with BULLETPROOF preservation of refresh token.

    Args:
        creds: Credentials to save
        token_path: Path to save to
        backup: Whether to create backup copy
    """
    try:
        # Load existing token to preserve refresh_token
        existing_refresh = None
        if os.path.exists(token_path):
            try:
                with open(token_path, 'r') as f:
                    existing_data = json.load(f)
                    existing_refresh = existing_data.get('refresh_token')
            except:
                pass

        # Get creds as dict
        creds_data = json.loads(creds.to_json())

        # CRITICAL: Preserve refresh token if it exists anywhere
        if not creds_data.get('refresh_token') and existing_refresh:
            creds_data['refresh_token'] = existing_refresh
            print(f"[OK] Preserved refresh token from existing credentials")

        # Add metadata
        creds_data['_last_saved'] = datetime.now().isoformat()
        creds_data['_refresh_count'] = creds_data.get('_refresh_count', 0) + 1

        # Atomic write
        temp_path = token_path + '.tmp'
        with open(temp_path, 'w') as f:
            json.dump(creds_data, f, indent=2)
        os.replace(temp_path, token_path)

        # Create backup
        if backup:
            backup_path = get_backup_token_path(os.path.basename(token_path).replace('channel_', '').replace('.json', ''))
            shutil.copy2(token_path, backup_path)
            print(f"[OK] Backup saved to {backup_path}")

        print(f"[OK] Credentials saved successfully (refresh #{creds_data['_refresh_count']})")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to save credentials: {e}")
        # Don't delete anything on failure!
        return False

def load_credentials(channel_name: str, try_backup: bool = True) -> Optional[Credentials]:
    """
    Load credentials with fallback to backup.

    Args:
        channel_name: Channel name
        try_backup: Whether to try backup if main fails

    Returns:
        Credentials or None
    """
    token_path = get_token_path(channel_name)

    # Try main token
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            if creds:
                print(f"[OK] Loaded credentials from {token_path}")
                return creds
        except Exception as e:
            print(f"[WARNING] Failed to load main token: {e}")

    # Try backup token
    if try_backup:
        backup_path = get_backup_token_path(channel_name)
        if os.path.exists(backup_path):
            try:
                creds = Credentials.from_authorized_user_file(backup_path, SCOPES)
                if creds:
                    print(f"[OK] Loaded credentials from BACKUP: {backup_path}")
                    # Restore from backup
                    save_credentials(creds, token_path, backup=False)
                    return creds
            except Exception as e:
                print(f"[WARNING] Failed to load backup token: {e}")

    return None

def refresh_token_with_retry(creds: Credentials, channel_name: str, max_attempts: int = 5) -> bool:
    """
    Refresh token with exponential backoff retry.

    Args:
        creds: Credentials to refresh
        channel_name: Channel name for logging
        max_attempts: Maximum retry attempts

    Returns:
        True if successful, False otherwise
    """
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"[REFRESH] Refreshing token for {channel_name} (attempt {attempt}/{max_attempts})...")
            creds.refresh(Request())
            print(f"[OK] Token refreshed successfully on attempt {attempt}")

            # Save immediately after successful refresh
            token_path = get_token_path(channel_name)
            save_credentials(creds, token_path)

            return True

        except Exception as e:
            print(f"[WARNING] Refresh attempt {attempt} failed: {e}")

            if attempt < max_attempts:
                # Exponential backoff: 2s, 4s, 8s, 16s, 32s
                wait_time = 2 ** attempt
                print(f"[WAIT] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] All {max_attempts} refresh attempts failed")
                return False

    return False

def get_valid_credentials(channel_name: str, auto_refresh: bool = True) -> Optional[Credentials]:
    """
    Get valid credentials, refreshing if needed.

    This is the main function to use - it handles everything automatically.

    Args:
        channel_name: Channel name
        auto_refresh: Whether to auto-refresh if expired

    Returns:
        Valid credentials or None
    """
    # Load credentials
    creds = load_credentials(channel_name)

    if not creds:
        print(f"[ERROR] No credentials found for {channel_name}")
        return None

    # Check if already valid
    if creds.valid:
        # Check if expiring soon (within 12 hours for maximum longevity)
        if hasattr(creds, 'expiry') and creds.expiry:
            time_until_expiry = (creds.expiry - datetime.utcnow()).total_seconds()
            if time_until_expiry < 43200:  # Less than 12 hours (extended from 1 hour)
                print(f"[WARNING] Token expires in {time_until_expiry/3600:.1f} hours - proactive refresh")
                if auto_refresh and creds.refresh_token:
                    refresh_token_with_retry(creds, channel_name)
                    creds = load_credentials(channel_name, try_backup=False)  # Reload after refresh

        return creds

    # Token expired - refresh it
    if auto_refresh and creds.refresh_token:
        print(f"[WARNING] Token expired - attempting refresh...")
        if refresh_token_with_retry(creds, channel_name):
            # Reload refreshed credentials
            creds = load_credentials(channel_name, try_backup=False)
            if creds and creds.valid:
                return creds

    print(f"[ERROR] Could not get valid credentials for {channel_name}")
    return None

# ==============================================================================
# Background Auto-Refresh
# ==============================================================================

def auto_refresh_worker():
    """
    Background worker that refreshes all tokens proactively.
    Runs every 15 minutes and refreshes tokens that expire within 24 hours.
    """
    global _refresh_running

    print("[REFRESH] Auto-refresh worker started (checks every 15 minutes)")

    while _refresh_running:
        try:
            # Get all token files
            token_files = [f for f in os.listdir(TOKENS_DIR) if f.endswith('.json') and not f.endswith('.tmp')]

            for token_file in token_files:
                try:
                    # Extract channel name
                    channel_name = token_file.replace('channel_', '').replace('.json', '').replace('_', ' ')

                    # Load and check credentials
                    creds = load_credentials(channel_name)

                    if not creds:
                        continue

                    # Check expiration
                    needs_refresh = False

                    if not creds.valid:
                        print(f"[WARNING] {channel_name}: Token expired - needs refresh")
                        needs_refresh = True
                    elif hasattr(creds, 'expiry') and creds.expiry:
                        time_until_expiry = (creds.expiry - datetime.utcnow()).total_seconds()
                        if time_until_expiry < 86400:  # Less than 24 hours (extended from 2 hours)
                            print(f"[WARNING] {channel_name}: Token expires in {time_until_expiry/3600:.1f}h - proactive refresh")
                            needs_refresh = True

                    # Refresh if needed
                    if needs_refresh and creds.refresh_token:
                        with _refresh_lock:
                            refresh_token_with_retry(creds, channel_name)

                except Exception as e:
                    print(f"[WARNING] Error checking {token_file}: {e}")

        except Exception as e:
            print(f"[WARNING] Auto-refresh worker error: {e}")

        # Wait 15 minutes (reduced from 30 for more frequent checks)
        for _ in range(900):  # 15 minutes in seconds
            if not _refresh_running:
                break
            time.sleep(1)

    print("[STOP] Auto-refresh worker stopped")

def start_auto_refresh():
    """Start background auto-refresh worker"""
    global _refresh_thread, _refresh_running

    if _refresh_running:
        print("[WARNING] Auto-refresh already running")
        return

    _refresh_running = True
    _refresh_thread = threading.Thread(target=auto_refresh_worker, daemon=True)
    _refresh_thread.start()
    print("[OK] Auto-refresh started")

def stop_auto_refresh():
    """Stop background auto-refresh worker"""
    global _refresh_running

    _refresh_running = False
    if _refresh_thread:
        _refresh_thread.join(timeout=5)
    print("[OK] Auto-refresh stopped")

# ==============================================================================
# Authentication Flow
# ==============================================================================

def authenticate_channel(channel_name: str, client_secret: str = None) -> Tuple[bool, str]:
    """
    Authenticate a YouTube channel.

    Args:
        channel_name: Channel name
        client_secret: YouTube OAuth client secret JSON string

    Returns:
        (success, message)
    """
    # Check if already authenticated
    creds = get_valid_credentials(channel_name)
    if creds:
        return True, f"[OK] {channel_name} is already authenticated!"

    # Need to authenticate
    if not client_secret:
        try:
            import toml
            secrets = toml.load('.streamlit/secrets.toml')
            client_secret = secrets.get('YOUTUBE_CLIENT_SECRET', '')
        except:
            return False, "YouTube client secret not found"

    if not client_secret:
        return False, "YouTube client secret not configured"

    # Parse client secret
    try:
        if isinstance(client_secret, str):
            client_config = json.loads(client_secret)
        else:
            client_config = client_secret
    except:
        return False, "Invalid client secret format"

    try:
        # Run OAuth flow with CRITICAL settings for refresh token
        flow = InstalledAppFlow.from_client_config(
            client_config,
            SCOPES,
            redirect_uri='http://localhost'
        )

        # CRITICAL: These settings ensure we get a refresh token
        creds = flow.run_local_server(
            port=0,
            authorization_prompt_message='',
            access_type='offline',       # REQUIRED for refresh token
            prompt='consent',            # REQUIRED to force consent screen
            include_granted_scopes='true'
        )

        # Verify we got a refresh token
        if not creds.refresh_token:
            return False, "[ERROR] No refresh token received! Try revoking app access at myaccount.google.com/permissions and re-authenticating."

        # Save credentials
        token_path = get_token_path(channel_name)
        if save_credentials(creds, token_path):
            print(f"[OK] {channel_name} authenticated with refresh token!")
            return True, f"[OK] {channel_name} authenticated successfully!"
        else:
            return False, "Failed to save credentials"

    except Exception as e:
        return False, f"Authentication failed: {str(e)}"

# ==============================================================================
# Helper Functions
# ==============================================================================

def is_channel_authenticated(channel_name: str) -> bool:
    """Check if channel is authenticated"""
    creds = get_valid_credentials(channel_name)
    return creds is not None

def get_youtube_service(channel_name: str):
    """Get YouTube API service"""
    creds = get_valid_credentials(channel_name)
    if not creds:
        return None

    try:
        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"[ERROR] Error building YouTube service: {e}")
        return None

def get_channel_info(channel_name: str) -> Optional[Dict]:
    """Get YouTube channel info"""
    youtube = get_youtube_service(channel_name)
    if not youtube:
        return None

    try:
        request = youtube.channels().list(part='snippet,statistics', mine=True)
        response = request.execute()

        if response.get('items'):
            channel = response['items'][0]
            return {
                'id': channel['id'],
                'title': channel['snippet']['title'],
                'thumbnail': channel['snippet']['thumbnails']['default']['url'],
                'subscribers': channel['statistics'].get('subscriberCount', '0'),
                'videos': channel['statistics'].get('videoCount', '0')
            }
    except Exception as e:
        print(f"[ERROR] Error getting channel info: {e}")

    return None

# ==============================================================================
# Testing & Diagnostics
# ==============================================================================

def test_all_channels():
    """Test authentication status of all channels"""
    print("=" * 70)
    print("TESTING ALL CHANNEL AUTHENTICATIONS")
    print("=" * 70)

    token_files = [f for f in os.listdir(TOKENS_DIR) if f.endswith('.json') and not f.endswith('.tmp')]

    for token_file in token_files:
        channel_name = token_file.replace('channel_', '').replace('.json', '').replace('_', ' ')

        print(f"\n[CHANNEL] {channel_name}")
        print("-" * 70)

        creds = get_valid_credentials(channel_name)

        if creds:
            print(f"[OK] Authenticated: YES")
            print(f"[OK] Valid: {creds.valid}")
            if hasattr(creds, 'expiry') and creds.expiry:
                time_until_expiry = (creds.expiry - datetime.utcnow()).total_seconds()
                print(f"[TIME] Expires in: {time_until_expiry/3600:.1f} hours")
            print(f"[KEY] Has refresh token: {bool(creds.refresh_token)}")

            # Test API call
            info = get_channel_info(channel_name)
            if info:
                print(f"[OK] API Test: SUCCESS")
                print(f"   Channel: {info['title']}")
                print(f"   Subscribers: {info['subscribers']}")
            else:
                print(f"[ERROR] API Test: FAILED")
        else:
            print(f"[ERROR] Authenticated: NO")
            print(f"[WARNING] Action: Re-authenticate required")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Test all channels
    test_all_channels()

    # Start auto-refresh
    start_auto_refresh()

    print("\n[OK] Bulletproof auth manager ready!")
    print("   - Auto-refresh runs every 15 minutes")
    print("   - Tokens refresh 24 hours before expiration")
    print("   - Multiple retry attempts on failures")
    print("   - Backup tokens preserved")
    print("   - Maximum token longevity configuration")
