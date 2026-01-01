import time
import json
import os
import logging
import traceback
import subprocess
import concurrent.futures
import requests
from datetime import datetime, timedelta

from video_gen import (
    generate_script, process_clip, generate_voiceover, 
    upload_to_youtube, cleanup_old_files, generate_theme_variations,
    append_history, GEMINI_API_KEY
)

# Setup logging
logging.basicConfig(
    filename='scheduler.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

STATE_FILE = 'scheduler_state.json'
THEME_FILE = 'auto_theme_list.json'
LOG_FILE = 'scheduler_log.json'

def log_ui(status, message):
    """Writes logs to a JSON file so the UI can read them"""
    # FIX 1: 12-Hour Timestamp
    entry = {
        "timestamp": datetime.now().strftime("%I:%M:%S %p"), 
        "status": status, 
        "message": message
    }
    try:
        data = {'entries': []}
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f: data = json.load(f)

        data['entries'].insert(0, entry)
        data['entries'] = data['entries'][:50]

        with open(LOG_FILE, 'w') as f: json.dump(data, f, indent=2)
        print(f"[{status.upper()}] {message}") 
    except Exception as e: 
        print(f"Log error: {e}")

def get_state():
    default_state = {
        'running': False, 
        'interval_mins': 60, 
        'last_upload': 0, 
        'general_theme': 'random facts',
        'youtube_limit_reached': False,
        'staged_video': None,       # FIX 4: Staging Area
        'staged_metadata': None,
        'heartbeat': 0              # FIX 5: Heartbeat
    }
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f: 
                loaded = json.load(f)
                for k, v in default_state.items():
                    if k not in loaded: loaded[k] = v
                return loaded
        except: pass
    return default_state

def update_state(updates):
    state = get_state()
    for k, v in updates.items():
        state[k] = v
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=2)

def get_next_theme():
    if os.path.exists(THEME_FILE):
        with open(THEME_FILE, 'r') as f: themes = json.load(f)
        if themes:
            theme = themes.pop(0)
            with open(THEME_FILE, 'w') as f: json.dump(themes, f, indent=2)
            return theme
    return None

def replenish_queue(general_theme):
    try:
        if not general_theme: general_theme = "interesting facts"
        log_ui("info", f"Replenishing queue for: {general_theme}")
        
        from video_gen import GEMINI_API_KEY
        if not GEMINI_API_KEY:
            log_ui("error", "GEMINI_API_KEY is missing from environment. Check Secrets.")
            time.sleep(60)
            return

        # Check quota first
        quota_file = 'daily_quota.json'
        today = datetime.now().strftime("%Y-%m-%d")
        if os.path.exists(quota_file):
            with open(quota_file, 'r') as f:
                q = json.load(f)
                if q.get('date') == today and q.get('count', 0) >= 20:
                    log_ui("warning", "Daily Gemini Quota (20) reached. Sleeping...")
                    time.sleep(3600)
                    return

        # Batch Theme Generation: Get 5 variations at once to save requests
        new_ideas = generate_theme_variations(general_theme, 5)
        if new_ideas:
            current_themes = []
            if os.path.exists(THEME_FILE):
                with open(THEME_FILE, 'r') as f: current_themes = json.load(f)

            added_count = 0
            for idea in new_ideas:
                if idea not in current_themes:
                    current_themes.append(idea)
                    added_count += 1
            
            with open(THEME_FILE, 'w') as f: json.dump(current_themes, f, indent=2)
            log_ui("success", f"Batched {added_count} new ideas to queue.")
        else:
            log_ui("error", "No ideas generated. API might be limited. Waiting 60s...")
            time.sleep(60)
    except Exception as e:
        error_msg = str(e).lower()
        log_ui("error", f"Failed to replenish: {str(e)}")
        if "429" in error_msg or "resource_exhausted" in error_msg:
            log_ui("warning", "Rate limit hit. Entering 5-minute cooldown...")
            time.sleep(300)
        else:
            time.sleep(60)

def generate_video_job(theme):
    """Generates a video but DOES NOT upload it. Returns path and metadata."""
    log_ui("running", f"🎬 GENERATING: {theme}")
    try:
        from video_gen import GEMINI_API_KEY, PEXELS_API_KEY, ELEVENLABS_API_KEY
        if not GEMINI_API_KEY:
            log_ui("error", "GEMINI_API_KEY missing. Check Secrets.")
            return None, None, None
        if not PEXELS_API_KEY:
            log_ui("error", "PEXELS_API_KEY missing. Check Secrets.")
            return None, None, None
        if not ELEVENLABS_API_KEY:
            log_ui("error", "ELEVENLABS_API_KEY missing. Check Secrets.")
            return None, None, None

        log_ui("info", "Generating script...")
        script, _ = generate_script(theme, 60, 10, 6.0)
        seg_dur = 6.0

        log_ui("info", "Generating voiceovers...")
        voice_id = "21m00Tcm4TlvDq8ikWAM"

        def gen_vo(args):
            i, seg = args
            path = f"outputs/sched_vo_{i}_{int(time.time())}.mp3"
            ok, err = generate_voiceover(seg['narration'], voice_id, path)
            if not ok:
                log_ui("error", f"VO segment {i} failed: {err}")
            return path if ok else None

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            vo_files = list(ex.map(gen_vo, enumerate(script['segments'])))
        vo_files = [v for v in vo_files if v]
        if len(vo_files) < 3: 
            log_ui("error", f"Only {len(vo_files)}/10 voiceovers generated. Check ElevenLabs API key and quota.")
            raise Exception(f"Voiceover failure: only {len(vo_files)}/10 segments completed")

        log_ui("info", "Processing clips...")
        def process_clip_wrapper(args):
            i, seg = args
            try:
                out, _ = process_clip(seg, i, seg_dur)
                return (i, out, seg.get('narration', ''))
            except: return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            clip_results = list(ex.map(process_clip_wrapper, enumerate(script['segments'])))

        valid_clips = [c for c in clip_results if c and c[1]]
        valid_clips.sort(key=lambda x: x[0])
        if not valid_clips: raise Exception("Video generation failure")

        clip_paths = [c[1] for c in valid_clips]
        clip_narrations = [c[2] for c in valid_clips]

        log_ui("info", "Assembling final video...")
        timestamp = int(time.time())

        list_file = f"outputs/list_{timestamp}.txt"
        with open(list_file, 'w') as f:
            for clip in clip_paths: f.write(f"file '{os.path.basename(clip)}'\n")

        concat_vid = f"outputs/concat_{timestamp}.mp4"
        subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', os.path.basename(list_file), '-c', 'copy', '-y', os.path.basename(concat_vid)], cwd='outputs', check=True, timeout=600)

        vo_list_file = f"outputs/volist_{timestamp}.txt"
        with open(vo_list_file, 'w') as f:
            for vo in vo_files: f.write(f"file '{os.path.basename(vo)}'\n")

        full_vo = f"outputs/full_vo_{timestamp}.mp3"
        subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', os.path.basename(vo_list_file), '-c', 'copy', '-y', os.path.basename(full_vo)], cwd='outputs', check=True, timeout=300)

        srt_file = f"outputs/subs_{timestamp}.srt"
        with open(srt_file, 'w', encoding='utf-8') as f:
            curr_time = 0
            for i, text in enumerate(clip_narrations):
                start = curr_time; end = curr_time + seg_dur
                def fmt(s): return f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d},{int((s%1)*1000):03d}"
                f.write(f"{i+1}\n{fmt(start)} --> {fmt(end)}\n{text}\n\n"); curr_time = end

        concat_subs = f"outputs/concat_subs_{timestamp}.mp4"
        subprocess.run(['ffmpeg', '-i', concat_vid, '-vf', f"subtitles={srt_file}:force_style='Fontname=Arial,Fontsize=24,PrimaryColour=&HFFFFFF&,Outline=2'", '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28', '-c:a', 'copy', '-y', concat_subs], check=True, timeout=600)

        music_file = f"outputs/music_{timestamp}.mp3"
        try:
            r = requests.get("https://www.bensound.com/bensound-music/bensound-creativeminds.mp3", timeout=15)
            with open(music_file, 'wb') as f: f.write(r.content)
        except:
            subprocess.run(['ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-t', '5', '-y', music_file], stderr=subprocess.DEVNULL)

        final_output = f"outputs/final_{theme.replace(' ', '_')}_{timestamp}.mp4"
        subprocess.run([
            'ffmpeg', '-i', concat_subs, '-i', full_vo, '-stream_loop', '-1', '-i', music_file,
            '-filter_complex', f'[1:a]volume=1.0[vo];[2:a]volume=0.15,afade=t=out:st={60-2}:d=2[music];[vo][music]amix=inputs=2:duration=first[a]',
            '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-t', '60', '-y', final_output
        ], check=True, timeout=600)

        log_ui("success", f"✅ VIDEO READY: {theme}")
        return final_output, script['title'], theme

    except Exception as e:
        log_ui("error", f"Generation Failed: {str(e)}")
        traceback.print_exc()
        return None, None, None

def upload_job(file_path, title, theme):
    log_ui("info", f"🚀 UPLOADING: {title}")
    try:
        tags = ["shorts", "facts", theme.replace(" ", "")]
        ok, res = upload_to_youtube(file_path, title, f"#shorts {theme}", tags)

        if ok:
            log_ui("success", f"🎉 PUBLISHED: {res}")
            append_history(title, theme, res, file_path, tags)
            return True
        else:
            log_ui("error", f"Upload Failed: {res}")
            if "quota" in str(res).lower() or "limit" in str(res).lower():
                return "LIMIT_REACHED"
            return False
    except Exception as e:
        log_ui("error", f"Upload Error: {str(e)}")
        return False

# --- MAIN LOOP ---
print("--- BACKGROUND SCHEDULER STARTED ---")

while True:
    try:
        # FIX 5: Heartbeat Update
        update_state({'heartbeat': time.time()})
        state = get_state()

        if state.get('running') and not state.get('youtube_limit_reached'):

            # FIX 4: PRE-GENERATION LOGIC
            staged_video = state.get('staged_video')
            staged_meta = state.get('staged_metadata')

            # 1. Do we have a video ready?
            if staged_video and os.path.exists(staged_video):
                # Yes -> Check if it's time to upload
                last_upload = state.get('last_upload', 0)
                interval_sec = float(state.get('interval_mins', 60)) * 60

                if time.time() - last_upload > interval_sec:
                    # TIME TO POST!
                    res = upload_job(staged_video, staged_meta['title'], staged_meta['theme'])

                    if res == "LIMIT_REACHED":
                        update_state({'youtube_limit_reached': True})
                    elif res:
                        # Upload Success -> Clear Buffer & Reset Timer
                        update_state({
                            'last_upload': time.time(),
                            'staged_video': None,
                            'staged_metadata': None
                        })
                        cleanup_old_files()
            else:
                # No video ready -> GENERATE ONE NOW (Buffer it)
                log_ui("info", "Buffer empty. Generating next video now...")
                theme = get_next_theme()

                if theme:
                    vid_path, title, thm = generate_video_job(theme)
                    if vid_path:
                        update_state({
                            'staged_video': vid_path,
                            'staged_metadata': {'title': title, 'theme': thm}
                        })

                        # Check queue size and replenish if needed
                        replenish_queue(state.get('general_theme', 'random facts'))
                else:
                    log_ui("warning", "Queue empty! Adding backup ideas...")
                    replenish_queue(state.get('general_theme', 'random facts'))

        time.sleep(10)

    except Exception as e:
        print(f"Scheduler Loop Error: {e}")
        time.sleep(30)