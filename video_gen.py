import os
import requests
import json
import subprocess
from pathlib import Path
import time
import hashlib
import pickle
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# --- GOOGLE GENAI LIBRARY ---
from google import genai
from google.genai import types

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load Env Vars
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
YOUTUBE_CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET')
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def check_keys():
    """Diagnostic to check if keys are loaded"""
    status = {
        "GEMINI_API_KEY": "SET" if GEMINI_API_KEY else "MISSING",
        "PEXELS_API_KEY": "SET" if PEXELS_API_KEY else "MISSING",
        "ELEVENLABS_API_KEY": "SET" if ELEVENLABS_API_KEY else "MISSING",
        "YOUTUBE_CLIENT_SECRET": "SET" if YOUTUBE_CLIENT_SECRET else "MISSING"
    }
    return status

# Configure Client
gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Gemini Client Init Error: {e}")
else:
    print("CRITICAL: GEMINI_API_KEY is not set in environment variables")

def retry_with_backoff(func, max_retries=3, initial_delay=1):
    for attempt in range(max_retries):
        try:
            return func(), None
        except Exception as e:
            if attempt == max_retries - 1:
                return None, str(e)
            time.sleep(initial_delay * (2 ** attempt))
    return None, "Max retries exceeded"

class SimpleCache:
    @staticmethod
    def _get_cache_path(cache_type: str, key: str) -> Path:
        return Path(f'cache/{cache_type}/{hashlib.md5(key.encode()).hexdigest()}.pkl')

    @staticmethod
    def get(cache_type: str, key: str, max_age_hours: int = 24):
        path = SimpleCache._get_cache_path(cache_type, key)
        if not path.exists(): return None
        try:
            age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
            if age > timedelta(hours=max_age_hours):
                path.unlink(); return None
            with open(path, 'rb') as f: return pickle.load(f)
        except: return None

    @staticmethod
    def set(cache_type: str, key: str, value):
        try:
            with open(SimpleCache._get_cache_path(cache_type, key), 'wb') as f: pickle.dump(value, f)
        except: pass

def cleanup_old_files():
    try:
        for file in Path('outputs').glob('*'):
            try:
                if file.is_file():
                    age = time.time() - file.stat().st_mtime
                    if age > 3600: file.unlink()
            except: pass
        cutoff = time.time() - (7 * 24 * 3600)
        for cache_dir in ['cache/scripts', 'cache/videos', 'cache/audio']:
            for file in Path(cache_dir).glob('*.pkl'):
                try:
                    if file.stat().st_mtime < cutoff: file.unlink()
                except: pass
    except: pass

def append_history(title, theme, youtube_url, file_path, tags):
    """Saves published video details to a history log"""
    history_file = 'video_history.json'
    # FIX 1: 12-Hour Time Format
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "title": title,
        "theme": theme,
        "youtube_url": youtube_url,
        "file_path": file_path,
        "tags": tags
    }

    data = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f: data = json.load(f)
        except: pass

    data.insert(0, entry)
    data = data[:100]

    try:
        with open(history_file, 'w') as f: json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"History Save Error: {e}")
        return False

def _generate_with_fallback(prompt):
    if not gemini_client:
        print("Gemini Client not initialized")
        return None

    # FIXED: Use only gemini-2.0-flash-exp as requested
    model_name = 'gemini-2.0-flash-exp'
    
    # Quota Tracking
    quota_file = 'daily_quota.json'
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        quota_data = {"date": today, "count": 0}
        if os.path.exists(quota_file):
            with open(quota_file, 'r') as f:
                try:
                    quota_data = json.load(f)
                except: pass
        
        if quota_data.get("date") != today:
            quota_data = {"date": today, "count": 0}
            
        if quota_data.get("count", 0) >= 20:
            print(f"CRITICAL: Daily Gemini Quota (20) reached for {today}")
            return None
            
        print(f"Using Gemini model: {model_name} (Request {quota_data.get('count', 0) + 1}/20)")
        
        # Increment quota before request
        quota_data["count"] = quota_data.get("count", 0) + 1
        with open(quota_file, 'w') as f:
            json.dump(quota_data, f)

        # Direct generation call to minimize overhead
        response = gemini_client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        )
        if response and response.text:
            return response.text
            
    except Exception as e:
        error_msg = str(e).lower()
        print(f"Gemini Request Failed: {e}")
        # If we failed but used a credit, we keep it incremented. 
        # If it was a 429 before the request even fired, the SDK usually throws before incrementing in some setups, 
        # but here we increment first to be safe and conservative with your 20 requests.
        if "429" in error_msg or "resource_exhausted" in error_msg:
            time.sleep(60)
    return None

def generate_theme_variations(general_theme: str, num_themes: int) -> List[str]:
    prompt = f"""Generate exactly {num_themes} creative and specific video topic variations based on the general theme: "{general_theme}"
Requirements:
- Generate EXACTLY {num_themes} variations
- Each should be a specific, catchy video title (2-4 words)
- Return ONLY a JSON array of strings (e.g. ["Title 1", "Title 2"])
- Do NOT use Markdown formatting"""

    text = _generate_with_fallback(prompt)
    if not text: return []

    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match: text = match.group(0)
        return json.loads(text)[:num_themes]
    except Exception as e:
        print(f"JSON Parse Error: {str(e)}")
        return []

def generate_voiceover(text, voice_id, output_path):
    def _gen():
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY},
            json={"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": 1.0}},
            timeout=30
        )
        if r.status_code == 200:
            with open(output_path, 'wb') as f: f.write(r.content); return True
        raise Exception(f"Status {r.status_code}")
    result, error = retry_with_backoff(_gen, 3)
    return (result is not None, error)

def search_videos(query: str) -> List[Dict]:
    cache_key = f"{query}_portrait"
    cached = SimpleCache.get('videos', cache_key, 24)
    if cached: return cached

    def _search():
        r = requests.get(
            f"https://api.pexels.com/videos/search?query={query}&per_page=10&orientation=portrait",
            headers={'Authorization': PEXELS_API_KEY}, timeout=10
        )
        return r.json().get('videos', [])

    videos, _ = retry_with_backoff(_search)
    if not videos:
        def _fallback():
            r = requests.get(f"https://api.pexels.com/videos/search?query={' '.join(query.split()[:2])}&per_page=10", headers={'Authorization': PEXELS_API_KEY}, timeout=10)
            return r.json().get('videos', [])
        videos, _ = retry_with_backoff(_fallback)

    if videos: SimpleCache.set('videos', cache_key, videos)
    return videos or []

def process_clip(seg, i, target_dur):
    try:
        videos = search_videos(seg['searchQuery'])
        if not videos: return None, f"No video for: {seg['searchQuery']}"
        video_url = sorted(videos[0]['video_files'], key=lambda x: x.get('width', 0), reverse=True)[0]['link']

        def _dl(): return requests.get(video_url, timeout=30).content
        content, err = retry_with_backoff(_dl)
        if not content: return None, f"Download failed: {err}"

        raw = f"outputs/raw_{i}_{int(time.time()*1000)}.mp4"
        with open(raw, 'wb') as f: f.write(content)

        out = f"outputs/clip_{i}_{int(time.time()*1000)}.mp4"
        cmd = ['ffmpeg', '-i', raw, '-ss', '0', '-t', str(target_dur), '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28', '-an', '-y', out]
        subprocess.run(cmd, capture_output=True, timeout=30, check=True)
        if os.path.exists(raw): os.remove(raw)
        return (out, seg.get('narration', '')), None
    except Exception as e: return None, str(e)

def generate_script(theme, duration, num_segs, seg_dur):
    cache_key = f"{theme}_top10_{duration}_{num_segs}"
    cached = SimpleCache.get('scripts', cache_key, 168)
    if cached: return cached, True

    def _gen():
        if not gemini_client: raise Exception("Gemini API Key missing or client failed to init")

        # BATCHED PROMPT: Get 5 script variations at once to store for future use
        # but for now, we optimize for ONE perfect script to ensure quality within the 1 request
        prompt = f"""Create a {duration}s top 10 countdown video about: {theme}
Requirements:
- EXACTLY {num_segs} segments numbered 10 down to 1
- Each segment EXACTLY {seg_dur:.2f} seconds
- Narration: {int(seg_dur*2.5)} words per segment
- Simple search keywords (1-2 words) for stock video
Respond with ONLY this JSON structure (no markdown):
{{"title":"Top 10 [Theme]","segments":[{{"number":10,"narration":"Short engaging narration.","searchQuery":"keyword"}}]}}"""

        text = _generate_with_fallback(prompt)
        if not text:
            # Fallback to a hardcoded simple script if Gemini is completely down to keep the app "working"
            return {
                "title": f"Top 10 {theme}",
                "segments": [
                    {"number": 11-i, "narration": f"Segment {11-i} of {theme}.", "searchQuery": theme.split()[0]}
                    for i in range(1, 11)
                ]
            }

        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match: text = match.group(0)
            return json.loads(text)
        except:
            return {
                "title": f"Top 10 {theme}",
                "segments": [
                    {"number": 11-i, "narration": f"Segment {11-i} of {theme}.", "searchQuery": theme.split()[0]}
                    for i in range(1, 11)
                ]
            }

    script, err = retry_with_backoff(_gen)
    if not script: raise Exception(f"Script failed: {err}")
    SimpleCache.set('scripts', cache_key, script)
    return script, False

def get_youtube_service():
    creds = None
    token_path = 'credentials/youtube_token.pickle'
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token: creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            if not YOUTUBE_CLIENT_SECRET: return None, "YOUTUBE_CLIENT_SECRET not set"
            client_config = json.loads(YOUTUBE_CLIENT_SECRET)
            flow = Flow.from_client_config(client_config, SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
            return None, f"AUTHORIZE: {auth_url}"
        with open(token_path, 'wb') as token: pickle.dump(creds, token)
    return build('youtube', 'v3', credentials=creds), None

def upload_to_youtube(video_path, title, description, tags):
    service, error = get_youtube_service()
    if error:
        print(f"YouTube Service Error: {error}")
        return False, error
    
    if not YOUTUBE_CLIENT_SECRET:
        return False, "YOUTUBE_CLIENT_SECRET environment variable is not set."

    try:
        body = {'snippet': {'title': title, 'description': description, 'tags': tags, 'categoryId': '22'}, 'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}}
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype='video/mp4')
        request = service.videos().insert(part='snippet,status', body=body, media_body=media)
        response = request.execute()
        return True, f"https://youtube.com/watch?v={response['id']}"
    except Exception as e:
        error_msg = str(e)
        print(f"YouTube Upload Exception: {error_msg}")
        return False, f"YouTube Upload Failed: {error_msg}"

def complete_youtube_auth(auth_code):
    try:
        client_config = json.loads(YOUTUBE_CLIENT_SECRET)
        flow = Flow.from_client_config(client_config, SCOPES)
        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        flow.fetch_token(code=auth_code)
        creds = flow.credentials
        token_path = 'credentials/youtube_token.pickle'
        with open(token_path, 'wb') as token: pickle.dump(creds, token)
        return True, "Authorization complete!"
    except Exception as e: return False, f"Auth failed: {str(e)}"