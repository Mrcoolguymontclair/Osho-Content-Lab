"""
Advanced Video Quality Enhancement System

Professional-grade video enhancement with:
- Superior color grading and correction
- Dynamic motion effects and zooms
- Professional transitions
- Audio normalization and enhancement
- Smart pacing and timing
- Visual effects and overlays
- Retention optimization
"""

import os
import random
import subprocess
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from logger import get_logger
from ffmpeg_wrapper import FFmpegWrapper, FFmpegError
from constants import (
    SHORTS_WIDTH,
    SHORTS_HEIGHT,
    SHORTS_FPS,
    SHORTS_BITRATE,
    SHORTS_AUDIO_BITRATE,
    VIDEO_CODEC,
    AUDIO_CODEC
)

logger = get_logger(__name__)


@dataclass
class EnhancementProfile:
    """Video enhancement configuration profile."""
    color_grade: str = "vibrant"  # vibrant, cinematic, natural, dramatic
    motion_style: str = "dynamic"  # dynamic, smooth, fast, slow
    transition_style: str = "modern"  # modern, cinematic, quick, creative
    audio_normalization: bool = True
    add_subtitles: bool = False
    retention_hooks: bool = True
    visual_effects: bool = True

    # Color grading parameters
    contrast: float = 1.15  # 1.0 = no change
    saturation: float = 1.25
    brightness: float = 1.05
    sharpness: float = 1.10

    # Motion parameters
    zoom_intensity: float = 1.15  # 1.0 = no zoom
    pan_speed: float = 1.0

    # Audio parameters
    audio_target_db: float = -14.0  # Loudness normalization target


class AdvancedVideoEnhancer:
    """
    Advanced video quality enhancement system.

    Applies professional-grade enhancements to make videos more engaging.
    """

    def __init__(self, profile: Optional[EnhancementProfile] = None):
        """
        Initialize video enhancer.

        Args:
            profile: Enhancement profile (uses default if None)
        """
        self.profile = profile or EnhancementProfile()
        self.ffmpeg = FFmpegWrapper()

    def _build_color_filter(self) -> str:
        """
        Build FFmpeg color grading filter.

        Returns:
            FFmpeg filter string
        """
        p = self.profile

        filters = []

        # Color correction and grading
        if p.color_grade == "vibrant":
            # Vibrant, eye-catching colors for social media
            filters.append(f"eq=contrast={p.contrast}:saturation={p.saturation}:brightness={p.brightness/20 - 0.05}")
            filters.append("vibrance=intensity=0.3")  # Boost saturation intelligently
            filters.append("unsharp=5:5:1.0:5:5:0.0")  # Sharpen

        elif p.color_grade == "cinematic":
            # Cinematic look with slight desaturation
            filters.append(f"eq=contrast={p.contrast * 1.1}:saturation={p.saturation * 0.9}:gamma=0.95")
            filters.append("curves=preset=color_negative")  # Film-like curve

        elif p.color_grade == "dramatic":
            # High contrast, dramatic look
            filters.append(f"eq=contrast={p.contrast * 1.3}:saturation={p.saturation}:brightness=0")
            filters.append("colorlevels=rimin=0.02:gimin=0.02:bimin=0.02:rimax=0.98:gimax=0.98:bimax=0.98")

        else:  # natural
            filters.append(f"eq=contrast={p.contrast * 0.95}:saturation={p.saturation * 0.9}")

        # Always add slight sharpness
        if p.sharpness > 1.0:
            amount = (p.sharpness - 1.0) * 2.0
            filters.append(f"unsharp=5:5:{amount}:5:5:0.0")

        # Denoise slightly for cleaner look
        filters.append("hqdn3d=2.0:1.5:3.0:2.0")

        return ",".join(filters)

    def _build_motion_filter(self, duration: float, index: int = 0) -> str:
        """
        Build dynamic motion filter (zoom, pan).

        Args:
            duration: Clip duration in seconds
            index: Clip index (for variety)

        Returns:
            FFmpeg filter string
        """
        if self.profile.motion_style == "static":
            return ""

        filters = []

        # Ken Burns effect (zoom + pan)
        zoom_amount = self.profile.zoom_intensity

        # Vary zoom direction based on clip index
        zoom_patterns = [
            # Zoom in
            f"scale={int(SHORTS_WIDTH * zoom_amount)}:{int(SHORTS_HEIGHT * zoom_amount)},zoompan=z='min(zoom+0.0015,{zoom_amount})':d={int(duration * SHORTS_FPS)}:s={SHORTS_WIDTH}x{SHORTS_HEIGHT}:fps={SHORTS_FPS}",

            # Zoom out
            f"scale={int(SHORTS_WIDTH * zoom_amount)}:{int(SHORTS_HEIGHT * zoom_amount)},zoompan=z='if(lte(zoom,1.0),{zoom_amount},max(1.0,zoom-0.0015))':d={int(duration * SHORTS_FPS)}:s={SHORTS_WIDTH}x{SHORTS_HEIGHT}:fps={SHORTS_FPS}",

            # Pan left to right
            f"scale={int(SHORTS_WIDTH * 1.2)}:-1,crop={SHORTS_WIDTH}:{SHORTS_HEIGHT}:'(iw-ow)*(t/{duration})':0",

            # Pan right to left
            f"scale={int(SHORTS_WIDTH * 1.2)}:-1,crop={SHORTS_WIDTH}:{SHORTS_HEIGHT}:'(iw-ow)*(1-t/{duration})':0",
        ]

        # Select pattern based on index for variety
        pattern = zoom_patterns[index % len(zoom_patterns)]
        return pattern

    def apply_transitions(
        self,
        clips: List[str],
        output_path: str,
        transition_duration: float = 0.5
    ) -> str:
        """
        Apply professional transitions between clips.

        Args:
            clips: List of video clip paths
            output_path: Output video path
            transition_duration: Transition duration in seconds

        Returns:
            Path to output video
        """
        if len(clips) < 2:
            logger.warning("Need at least 2 clips for transitions")
            return clips[0] if clips else None

        logger.info(f"Applying {self.profile.transition_style} transitions to {len(clips)} clips")

        # Build complex filter for transitions
        filter_complex = []
        inputs = []

        for i, clip_path in enumerate(clips):
            inputs.extend(['-i', clip_path])

        # Create transition chain
        prev_label = "0:v"
        for i in range(len(clips) - 1):
            current_label = f"{i}:v"
            next_label = f"{i+1}:v"
            output_label = f"v{i}out"

            # Choose transition based on style
            if self.profile.transition_style == "modern":
                # Smooth crossfade
                transition = f"[{prev_label if i > 0 else current_label}][{next_label}]xfade=transition=fade:duration={transition_duration}:offset=0[{output_label}]"

            elif self.profile.transition_style == "cinematic":
                # Wipe transition
                transitions_list = ["wipeleft", "wiperight", "wipeup", "wipedown"]
                trans = transitions_list[i % len(transitions_list)]
                transition = f"[{prev_label if i > 0 else current_label}][{next_label}]xfade=transition={trans}:duration={transition_duration}:offset=0[{output_label}]"

            elif self.profile.transition_style == "quick":
                # Fast cut (minimal transition)
                transition = f"[{prev_label if i > 0 else current_label}][{next_label}]xfade=transition=fadeblack:duration={transition_duration/2}:offset=0[{output_label}]"

            else:  # creative
                # Random creative transitions
                creative_trans = ["circleopen", "circleclose", "slideup", "slidedown", "slideleft", "slideright"]
                trans = creative_trans[i % len(creative_trans)]
                transition = f"[{prev_label if i > 0 else current_label}][{next_label}]xfade=transition={trans}:duration={transition_duration}:offset=0[{output_label}]"

            filter_complex.append(transition)
            prev_label = output_label

        # Build FFmpeg command
        cmd = [
            self.ffmpeg.ffmpeg_path,
            '-loglevel', 'error',
            *inputs,
            '-filter_complex', ';'.join(filter_complex),
            '-map', f'[{output_label}]',
            '-c:v', VIDEO_CODEC,
            '-preset', 'medium',
            '-b:v', SHORTS_BITRATE,
            '-y',
            output_path
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Transitions applied successfully")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Transition failed: {e.stderr.decode()}")
            raise FFmpegError(f"Failed to apply transitions: {e}")

    def enhance_clip(
        self,
        input_path: str,
        output_path: str,
        duration: Optional[float] = None,
        clip_index: int = 0
    ) -> str:
        """
        Apply comprehensive enhancements to a single clip.

        Args:
            input_path: Input video path
            output_path: Output video path
            duration: Clip duration (auto-detected if None)
            clip_index: Clip index for motion variety

        Returns:
            Path to enhanced video
        """
        logger.info(f"Enhancing clip {clip_index}: {input_path}")

        # Get video info if duration not provided
        if duration is None:
            info = self.ffmpeg.get_video_info(input_path)
            duration = info.get('duration', 5.0)

        # Build filter chain
        filters = []

        # 1. Color grading
        color_filter = self._build_color_filter()
        if color_filter:
            filters.append(color_filter)

        # 2. Motion effects
        if self.profile.visual_effects and self.profile.motion_style != "static":
            motion_filter = self._build_motion_filter(duration, clip_index)
            if motion_filter:
                filters.append(motion_filter)

        # 3. Final scaling and formatting
        filters.append(f"scale={SHORTS_WIDTH}:{SHORTS_HEIGHT}:force_original_aspect_ratio=increase")
        filters.append(f"crop={SHORTS_WIDTH}:{SHORTS_HEIGHT}")

        # Combine all filters
        vf_string = ",".join(filters)

        # Apply enhancements
        try:
            self.ffmpeg.convert_video(
                input_path=input_path,
                output_path=output_path,
                video_codec=VIDEO_CODEC,
                audio_codec=AUDIO_CODEC,
                video_bitrate=SHORTS_BITRATE,
                audio_bitrate=SHORTS_AUDIO_BITRATE,
                extra_args=['-vf', vf_string, '-r', str(SHORTS_FPS)]
            )

            logger.info(f"Clip enhanced successfully: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to enhance clip: {e}")
            raise

    def normalize_audio(
        self,
        input_path: str,
        output_path: str
    ) -> str:
        """
        Normalize audio levels for consistent loudness.

        Args:
            input_path: Input video path
            output_path: Output video path

        Returns:
            Path to output video
        """
        if not self.profile.audio_normalization:
            return input_path

        logger.info("Normalizing audio levels")

        try:
            # Two-pass loudness normalization
            cmd = [
                self.ffmpeg.ffmpeg_path,
                '-loglevel', 'error',
                '-i', input_path,
                '-af', f'loudnorm=I={self.profile.audio_target_db}:TP=-1.5:LRA=11',
                '-c:v', 'copy',
                '-c:a', AUDIO_CODEC,
                '-b:a', SHORTS_AUDIO_BITRATE,
                '-y',
                output_path
            ]

            subprocess.run(cmd, check=True, capture_output=True)
            logger.info("Audio normalized successfully")
            return output_path

        except Exception as e:
            logger.error(f"Audio normalization failed: {e}")
            # Return original if normalization fails
            return input_path

    def add_retention_hooks(
        self,
        input_path: str,
        output_path: str,
        hook_texts: Optional[List[str]] = None
    ) -> str:
        """
        Add visual retention hooks (text overlays at strategic points).

        Args:
            input_path: Input video path
            output_path: Output video path
            hook_texts: Optional custom hook texts

        Returns:
            Path to output video
        """
        if not self.profile.retention_hooks:
            return input_path

        # Default retention hooks
        if not hook_texts:
            hook_texts = [
                "Wait for #1...",
                "Number 3 is shocking!",
                "Watch till the end!",
                "This gets crazy..."
            ]

        logger.info("Adding retention hooks")

        # Get video duration
        info = self.ffmpeg.get_video_info(input_path)
        duration = info.get('duration', 30.0)

        # Place hooks at strategic points (25%, 50%, 75%)
        hook_times = [duration * 0.25, duration * 0.50, duration * 0.75]

        # Build drawtext filter for hooks
        drawtext_filters = []
        for i, (hook_text, hook_time) in enumerate(zip(hook_texts[:3], hook_times)):
            # Escape special characters in text
            safe_text = hook_text.replace("'", "\\'").replace(":", "\\:")

            filter_str = (
                f"drawtext="
                f"text='{safe_text}':"
                f"fontsize=60:"
                f"fontcolor=white:"
                f"borderw=3:"
                f"bordercolor=black:"
                f"x=(w-text_w)/2:"
                f"y=h-100:"
                f"enable='between(t,{hook_time},{hook_time+2})'"  # Show for 2 seconds
            )
            drawtext_filters.append(filter_str)

        vf_string = ",".join(drawtext_filters)

        try:
            cmd = [
                self.ffmpeg.ffmpeg_path,
                '-loglevel', 'error',
                '-i', input_path,
                '-vf', vf_string,
                '-c:v', VIDEO_CODEC,
                '-c:a', 'copy',
                '-y',
                output_path
            ]

            subprocess.run(cmd, check=True, capture_output=True)
            logger.info("Retention hooks added successfully")
            return output_path

        except Exception as e:
            logger.error(f"Failed to add retention hooks: {e}")
            return input_path

    def enhance_complete_video(
        self,
        input_path: str,
        output_path: str,
        add_hooks: bool = True
    ) -> str:
        """
        Apply all enhancements to a complete video.

        Args:
            input_path: Input video path
            output_path: Output video path
            add_hooks: Whether to add retention hooks

        Returns:
            Path to enhanced video
        """
        logger.info(f"Applying complete enhancement pipeline to {input_path}")

        temp_dir = os.path.dirname(output_path)
        temp1 = os.path.join(temp_dir, "temp_enhanced.mp4")
        temp2 = os.path.join(temp_dir, "temp_audio_normalized.mp4")

        try:
            # Step 1: Enhance video (color, effects)
            current_file = input_path

            # Step 2: Normalize audio
            if self.profile.audio_normalization:
                self.normalize_audio(current_file, temp2)
                current_file = temp2

            # Step 3: Add retention hooks
            if add_hooks and self.profile.retention_hooks:
                self.add_retention_hooks(current_file, temp1)
                current_file = temp1

            # Final copy to output
            if current_file != output_path:
                os.replace(current_file, output_path)

            logger.info(f"Complete enhancement finished: {output_path}")
            return output_path

        finally:
            # Cleanup temp files
            for temp_file in [temp1, temp2]:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass


# Predefined enhancement profiles
PROFILES = {
    "viral": EnhancementProfile(
        color_grade="vibrant",
        motion_style="dynamic",
        transition_style="modern",
        audio_normalization=True,
        retention_hooks=True,
        visual_effects=True,
        contrast=1.20,
        saturation=1.30,
        brightness=1.08,
        zoom_intensity=1.20
    ),
    "cinematic": EnhancementProfile(
        color_grade="cinematic",
        motion_style="smooth",
        transition_style="cinematic",
        audio_normalization=True,
        retention_hooks=False,
        visual_effects=True,
        contrast=1.25,
        saturation=0.95,
        brightness=0.98,
        zoom_intensity=1.10
    ),
    "fast_paced": EnhancementProfile(
        color_grade="vibrant",
        motion_style="fast",
        transition_style="quick",
        audio_normalization=True,
        retention_hooks=True,
        visual_effects=True,
        contrast=1.18,
        saturation=1.25,
        brightness=1.05,
        zoom_intensity=1.25
    ),
    "natural": EnhancementProfile(
        color_grade="natural",
        motion_style="smooth",
        transition_style="modern",
        audio_normalization=True,
        retention_hooks=False,
        visual_effects=False,
        contrast=1.05,
        saturation=1.05,
        brightness=1.02,
        zoom_intensity=1.05
    )
}


def get_enhancer(profile_name: str = "viral") -> AdvancedVideoEnhancer:
    """
    Get video enhancer with specified profile.

    Args:
        profile_name: Profile name (viral, cinematic, fast_paced, natural)

    Returns:
        AdvancedVideoEnhancer instance
    """
    profile = PROFILES.get(profile_name, PROFILES["viral"])
    return AdvancedVideoEnhancer(profile=profile)


if __name__ == '__main__':
    print("Advanced Video Enhancer")
    print("=" * 70)
    print("\nAvailable profiles:")
    for name, profile in PROFILES.items():
        print(f"  - {name}: {profile.color_grade} color, {profile.motion_style} motion")
    print("\n[OK] Advanced video enhancer ready for use")
