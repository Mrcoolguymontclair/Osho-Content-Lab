import os
import subprocess
from typing import Tuple

from harmony_snippets import FFMPEG


def generate_thumbnail(video_path: str, overlay_path: str, out_path: str) -> Tuple[bool, str]:
    """Generate a 1280x720 thumbnail PNG from a video frame and optional overlay.

    Returns: (success, error_message_or_empty)
    """
    if not os.path.exists(video_path):
        return False, "Source video not found"

    output_dir = os.path.dirname(out_path) or '.'
    try:
        # Capture a frame at 1s and scale/crop to 1280x720
        if overlay_path and os.path.exists(overlay_path):
            cmd = [
                FFMPEG, '-y',
                '-i', os.path.basename(video_path),
                '-i', os.path.basename(overlay_path),
                '-ss', '00:00:01.000',
                '-vframes', '1',
                '-filter_complex', "[0:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720[bg];[bg][1:v]overlay=(W-w)/2:(H-h)/2",
                os.path.basename(out_path)
            ]
        else:
            cmd = [
                FFMPEG, '-y',
                '-i', os.path.basename(video_path),
                '-ss', '00:00:01.000',
                '-vframes', '1',
                '-vf', 'scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720',
                os.path.basename(out_path)
            ]

        result = subprocess.run(cmd, capture_output=True, cwd=output_dir, timeout=30)
        if result.returncode != 0:
            return False, result.stderr.decode()

        return True, ''
    except Exception as e:
        return False, str(e)
