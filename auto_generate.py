import os
import sys
import requests
import json
import subprocess
from pathlib import Path
import time
import concurrent.futures
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import Flow

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
YOUTUBE_CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET')
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

class SimpleCache:
    @staticmethod
    def _get_cache_path(cache_type: str, key: str) -> Path:
        return Path(f'cache/{cache_type}/{hashlib.md5(key.encode()).hexdigest()}.pkl')

    @staticmethod
    def get(cache_type: str, key: str, max_age_hours: int = 24):
        path = SimpleCache._get_cache_path(cache_type, key)
        if not path.exists():
            return None
        try:
            age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
            if age > timedelta(hours=max_age_hours):
                path.unlink()
                return None
            with open(path, 'rb') as f:
                return pickle.load(f)
        except:
            return None

    @staticmethod
    def set(cache_type: str, key: str, value):
        try:
            with open(SimpleCache._get_cache_path(cache_type, key), 'wb') as f:
                pickle.dump(value, f)
        except:
            pass

def retry_with_backoff(func, max_retries=3, initial_delay=1):
    for attempt in range(max_retries):
        try:
            return func(), None
        except Exception as e:
            if attempt == max_retries - 1:
                return None, str(e)
            time.sleep(initial_delay * (2 ** attempt))
    return None, "Max retries exceeded"

def generate_voiceover(text, voice_id, output_path):
    def _gen():
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY},
            json={"text": text, "model_id": "eleven_turbo_v2_5", 
                  "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": 1.0}},
            timeout=30
        )
        if r.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(r.content)
            return True
        raise Exception(f"Status {r.status_code}")
    result, error = retry_with_backoff(_gen, 3)
    return (result is not None, error)

def search_videos(query: str) -> List[Dict]:
    cache_key = f"{query}_portrait"
    cached = SimpleCache.get('videos', cache_key, 24)
    if cached:
        return cached

    def _search():
        r = requests.get(
            f"https://api.pexels.com/videos/search?query={query}&per_page=10&orientation=portrait",
            headers={'Authorization': PEXELS_API_KEY}, timeout=10
        )
        return r.json().get('videos', [])

    videos, _ = retry_with_backoff(_search)
    if not videos:
        def _fallback():
            r = requests.get(
                f"https://api.pexels.com/videos/search?query={' '.join(query.split()[:2])}&per_page=10",
                headers={'Authorization': PEXELS_API_KEY}, timeout=10
            )
            return r.json().get('videos', [])
        videos, _ = retry_with_backoff(_fallback)

    if videos:
        SimpleCache.set('videos', cache_key, videos)
    return videos or []

def process_clip(seg, i, target_dur):
    try:
        videos = search_videos(seg['searchQuery'])
        if not videos:
            return None, f"No video for: {seg['searchQuery']}"

        video_url = sorted(videos[0]['video_files'], key=lambda x: x.get('width', 0), reverse=True)[0]['link']

        def _dl():
            return requests.get(video_url, timeout=30).content
        content, err = retry_with_backoff(_dl)
        if not content:
            return None, f"Download failed: {err}"

        raw = f"outputs/raw_{i}_{int(time.time()*1000)}.mp4"
        with open(raw, 'wb') as f:
            f.write(content)

        out = f"outputs/clip_{i}_{int(time.time()*1000)}.mp4"

        cmd = [
            'ffmpeg', '-i', raw, '-ss', '0', '-t', str(target_dur),
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
            '-an',
            '-y', out
        ]

        subprocess.run(cmd, capture_output=True, timeout=30, check=True)

        if os.path.exists(raw):
            os.remove(raw)

        return (out, seg.get('narration', '')), None
    except Exception as e:
        return None, str(e)

def generate_script(theme, duration, num_segs, seg_dur):
    cache_key = f"{theme}_top10_{duration}_{num_segs}"
    cached = SimpleCache.get('scripts', cache_key, 168)
    if cached:
        return cached, True

    def _gen():
        r = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [{'role': 'user', 'content': f"""Create a {duration}s top 10 countdown video about: {theme}

Requirements:
- EXACTLY {num_segs} segments numbered 10 down to 1
- Each segment EXACTLY {seg_dur:.2f} seconds
- Narration: {int(seg_dur*2.5)} words per segment
- Simple search keywords (1-2 words)

Respond with ONLY this JSON structure:
{{"title":"Top 10 [Theme]","segments":[{{"number":10,"narration":"Short engaging narration.","searchQuery":"keyword"}}]}}"""}],
                'temperature': 0.8, 'max_tokens': 3000
            },
            timeout=30
        ).json()
        return r

    result, err = retry_with_backoff(_gen)
    if not result:
        raise Exception(f"Script failed: {err}")

    script_text = result['choices'][0]['message']['content'].replace('```json', '').replace('```', '').strip()
    script = json.loads(script_text)
    SimpleCache.set('scripts', cache_key, script)
    return script, False

def get_youtube_service():
    creds = None
    token_path = 'credentials/youtube_token.pickle'

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not YOUTUBE_CLIENT_SECRET:
                return None, "YOUTUBE_CLIENT_SECRET not set"

            client_config = json.loads(YOUTUBE_CLIENT_SECRET)
            flow = Flow.from_client_config(client_config, SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            return None, "AUTH_REQUIRED"

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds), None

def upload_to_youtube(video_path, title, description, tags):
    service, error = get_youtube_service()
    if error:
        return False, error

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype='video/mp4')
    request = service.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media
    )

    response = request.execute()
    video_id = response['id']
    return True, f"https://youtube.com/watch?v={video_id}"

def generate_video(theme, duration=60, auto_upload=True):
    for folder in ['outputs', 'cache', 'cache/scripts', 'cache/videos', 'cache/audio', 'credentials']:
        Path(folder).mkdir(exist_ok=True)

    try:
        num_segs = 10
        seg_dur = duration / num_segs

        script, cached = generate_script(theme, duration, num_segs, seg_dur)

        voice_id = "21m00Tcm4TlvDq8ikWAM"
        vo_files = []

        def gen_vo(args):
            idx, seg = args
            vo = f"outputs/vo_{idx}_{int(time.time()*1000)}.mp3"
            ok, err = generate_voiceover(seg.get('narration', ''), voice_id, vo)
            return (vo if ok else None, err)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(gen_vo, enumerate(script['segments'])))

        vo_files = [r[0] for r in results if r[0]]

        music_file = f"outputs/music_{int(time.time())}.mp3"
        try:
            def _dl_music():
                return requests.get("https://www.bensound.com/bensound-music/bensound-creativeminds.mp3", timeout=20).content
            content, _ = retry_with_backoff(_dl_music)
            if content:
                with open(music_file, 'wb') as f:
                    f.write(content)
        except:
            music_file = None

        clips = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            futures = []
            for i, seg in enumerate(script['segments']):
                fut = ex.submit(process_clip, seg, i, seg_dur)
                futures.append((fut, i))

            for fut, idx in futures:
                result = fut.result()
                if result[0]:
                    clip_data, err = result
                    clips.append((idx, clip_data[0], clip_data[1]))

        clips.sort(key=lambda x: x[0])
        clip_paths = [c[1] for c in clips]
        clip_narrations = [c[2] for c in clips]

        if not clips:
            raise Exception("No clips created")

        list_file = f"outputs/list_{int(time.time())}.txt"
        with open(list_file, 'w') as f:
            for clip in clip_paths:
                f.write(f"file '{os.path.basename(clip)}'\n")

        concat = f"outputs/concat_{int(time.time())}.mp4"
        subprocess.run([
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', os.path.basename(list_file),
            '-c', 'copy', '-y', os.path.basename(concat)
        ], cwd='outputs', capture_output=True, timeout=60, check=True)

        srt_file = f"outputs/subtitles_{int(time.time())}.srt"
        with open(srt_file, 'w', encoding='utf-8') as f:
            current_time = 0
            for i, text in enumerate(clip_narrations):
                start_time = current_time
                end_time = current_time + seg_dur

                def format_time(seconds):
                    hours = int(seconds // 3600)
                    minutes = int((seconds % 3600) // 60)
                    secs = int(seconds % 60)
                    millis = int((seconds % 1) * 1000)
                    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

                f.write(f"{i+1}\n")
                f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
                f.write(f"{text}\n\n")

                current_time = end_time

        concat_with_subs = f"outputs/concat_subs_{int(time.time())}.mp4"
        subprocess.run([
            'ffmpeg', '-i', concat, '-vf',
            f"subtitles={srt_file}:force_style='Fontname=DejaVu Sans Bold,Fontsize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2,Shadow=0,MarginV=80'",
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
            '-c:a', 'copy', '-y', concat_with_subs
        ], capture_output=True, timeout=120, check=True)

        output_file = f"video_{theme.replace(' ', '_')}_{int(time.time())}.mp4"
        output_path = f"outputs/{output_file}"

        vo_list = f"outputs/vo_list_{int(time.time())}.txt"
        with open(vo_list, 'w') as f:
            for vo in vo_files:
                f.write(f"file '{os.path.basename(vo)}'\n")

        full_vo = f"outputs/full_vo_{int(time.time())}.mp3"
        subprocess.run([
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', os.path.basename(vo_list),
            '-c', 'copy', '-y', os.path.basename(full_vo)
        ], cwd='outputs', capture_output=True, timeout=30, check=True)

        if music_file and os.path.exists(music_file):
            subprocess.run([
                'ffmpeg', '-i', concat_with_subs, '-i', full_vo, '-stream_loop', '-1', '-i', music_file,
                '-filter_complex',
                '[1:a]volume=1.0[vo];[2:a]volume=0.15,afade=t=out:st=' + str(duration-2) + ':d=2[music];[vo][music]amix=inputs=2:duration=first[a]',
                '-map', '0:v', '-map', '[a]',
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                '-t', str(duration),
                '-y', output_path
            ], capture_output=True, timeout=90, check=True)
        else:
            subprocess.run([
                'ffmpeg', '-i', concat_with_subs, '-i', full_vo,
                '-map', '0:v', '-map', '1:a',
                '-c:v', 'copy', '-c:a', 'aac',
                '-t', str(duration),
                '-y', output_path
            ], capture_output=True, timeout=60, check=True)

        youtube_url = None
        if auto_upload:
            try:
                video_title = script.get('title', f"Top 10 {theme}")
                video_desc = f"Top 10 {theme}\n\nGenerated automatically by AutoTube Studio Pro"
                video_tags = [theme, 'top10', 'countdown']

                success, result = upload_to_youtube(output_path, video_title, video_desc, video_tags)
                if success:
                    youtube_url = result
                else:
                    print(f"Upload failed: {result}", file=sys.stderr)
            except Exception as e:
                print(f"Upload error: {str(e)}", file=sys.stderr)

        print(f"SUCCESS: {output_file}")
        if youtube_url:
            print(f"YouTube: {youtube_url}")

        try:
            os.remove(list_file)
            os.remove(vo_list)
            os.remove(concat)
            os.remove(concat_with_subs)
            os.remove(srt_file)
            os.remove(full_vo)
            for clip in clip_paths:
                if os.path.exists(clip):
                    os.remove(clip)
            for vo in vo_files:
                if os.path.exists(vo):
                    os.remove(vo)
            if music_file and os.path.exists(music_file):
                os.remove(music_file)
        except:
            pass

        return True

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python auto_generate.py <theme> [duration] [auto_upload]", file=sys.stderr)
        sys.exit(1)
    
    theme = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    auto_upload = sys.argv[3].lower() != 'false' if len(sys.argv) > 3 else True
    
    success = generate_video(theme, duration, auto_upload)
    sys.exit(0 if success else 1)
