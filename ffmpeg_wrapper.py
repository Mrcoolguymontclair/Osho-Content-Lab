"""
Safe FFmpeg Wrapper

Provides a safe interface for running FFmpeg and FFprobe commands,
preventing command injection vulnerabilities.

Key features:
- Uses subprocess list syntax (not shell strings)
- Validates all file paths
- Prevents command injection
- Proper timeout handling
- Detailed error reporting
"""

import subprocess
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from input_validator import ValidationError, InputValidator
from logger import get_logger
from constants import (
    FFMPEG_COMMAND,
    FFPROBE_COMMAND,
    FFmpeg_TIMEOUT,
    FFMPEG_LOGLEVEL
)

logger = get_logger(__name__)


class FFmpegError(Exception):
    """Raised when FFmpeg command fails."""
    pass


class FFmpegWrapper:
    """
    Safe wrapper for FFmpeg operations.

    All methods use subprocess list syntax and validate inputs
    to prevent command injection.
    """

    def __init__(
        self,
        ffmpeg_path: str = FFMPEG_COMMAND,
        ffprobe_path: str = FFPROBE_COMMAND,
        timeout: int = FFmpeg_TIMEOUT
    ):
        """
        Initialize FFmpeg wrapper.

        Args:
            ffmpeg_path: Path to ffmpeg executable
            ffprobe_path: Path to ffprobe executable
            timeout: Default timeout for commands (seconds)

        Raises:
            FFmpegError: If ffmpeg or ffprobe not found
        """
        self.ffmpeg_path = self._find_executable(ffmpeg_path)
        self.ffprobe_path = self._find_executable(ffprobe_path)
        self.timeout = timeout

    def _find_executable(self, name: str) -> str:
        """
        Find executable in PATH.

        Args:
            name: Executable name

        Returns:
            Full path to executable

        Raises:
            FFmpegError: If executable not found
        """
        path = shutil.which(name)
        if not path:
            raise FFmpegError(f"{name} not found in PATH. Please install it.")
        return path

    def _validate_file_path(self, path: str, must_exist: bool = False) -> str:
        """
        Validate and sanitize file path.

        Args:
            path: File path to validate
            must_exist: If True, path must exist

        Returns:
            Validated absolute path

        Raises:
            ValidationError: If path is invalid
        """
        try:
            validated_path = InputValidator.sanitize_path(path)
        except ValidationError as e:
            raise FFmpegError(f"Invalid file path: {e}")

        if must_exist and not os.path.exists(validated_path):
            raise FFmpegError(f"File not found: {validated_path}")

        return validated_path

    def _run_command(
        self,
        cmd: List[str],
        timeout: Optional[int] = None,
        capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Run command safely using subprocess list syntax.

        Args:
            cmd: Command as list of arguments
            timeout: Command timeout (seconds)
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess instance

        Raises:
            FFmpegError: If command fails or times out
        """
        timeout = timeout or self.timeout

        logger.debug(f"Running command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                timeout=timeout,
                check=False,  # Don't raise on non-zero exit
                text=True
            )

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "Unknown error"
                raise FFmpegError(f"Command failed: {error_msg}")

            return result

        except subprocess.TimeoutExpired:
            raise FFmpegError(f"Command timed out after {timeout} seconds")
        except Exception as e:
            raise FFmpegError(f"Command execution failed: {str(e)}")

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get video file information using ffprobe.

        Args:
            video_path: Path to video file

        Returns:
            Dictionary with video information

        Raises:
            FFmpegError: If probe fails
        """
        video_path = self._validate_file_path(video_path, must_exist=True)

        cmd = [
            self.ffprobe_path,
            '-v', 'error',
            '-show_entries', 'format=duration:stream=width,height,codec_name,bit_rate',
            '-of', 'default=noprint_wrappers=1',
            video_path
        ]

        result = self._run_command(cmd)

        # Parse output
        info = {}
        for line in result.stdout.split('\n'):
            if '=' in line:
                key, value = line.strip().split('=', 1)
                info[key] = value

        # Convert numeric fields
        if 'duration' in info:
            try:
                info['duration'] = float(info['duration'])
            except ValueError:
                pass

        if 'width' in info:
            try:
                info['width'] = int(info['width'])
            except ValueError:
                pass

        if 'height' in info:
            try:
                info['height'] = int(info['height'])
            except ValueError:
                pass

        return info

    def convert_video(
        self,
        input_path: str,
        output_path: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[int] = None,
        video_codec: Optional[str] = None,
        audio_codec: Optional[str] = None,
        video_bitrate: Optional[str] = None,
        audio_bitrate: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        overwrite: bool = True
    ) -> str:
        """
        Convert video with specified parameters.

        Args:
            input_path: Input video path
            output_path: Output video path
            width: Target width
            height: Target height
            fps: Target FPS
            video_codec: Video codec (e.g., 'libx264')
            audio_codec: Audio codec (e.g., 'aac')
            video_bitrate: Video bitrate (e.g., '4M')
            audio_bitrate: Audio bitrate (e.g., '192k')
            extra_args: Additional FFmpeg arguments
            overwrite: Whether to overwrite output file

        Returns:
            Path to output file

        Raises:
            FFmpegError: If conversion fails
        """
        input_path = self._validate_file_path(input_path, must_exist=True)
        output_path = self._validate_file_path(output_path, must_exist=False)

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Build command
        cmd = [
            self.ffmpeg_path,
            '-loglevel', FFMPEG_LOGLEVEL,
        ]

        if overwrite:
            cmd.append('-y')

        cmd.extend(['-i', input_path])

        # Video filters
        filters = []
        if width and height:
            filters.append(f'scale={width}:{height}')
        if fps:
            filters.append(f'fps={fps}')

        if filters:
            cmd.extend(['-vf', ','.join(filters)])

        # Codecs
        if video_codec:
            cmd.extend(['-c:v', video_codec])
        if audio_codec:
            cmd.extend(['-c:a', audio_codec])

        # Bitrates
        if video_bitrate:
            cmd.extend(['-b:v', video_bitrate])
        if audio_bitrate:
            cmd.extend(['-b:a', audio_bitrate])

        # Extra arguments
        if extra_args:
            # Validate extra args
            for arg in extra_args:
                try:
                    InputValidator.safe_ffmpeg_arg(str(arg))
                except ValidationError as e:
                    raise FFmpegError(f"Invalid extra argument: {e}")
            cmd.extend(extra_args)

        cmd.append(output_path)

        # Run conversion
        self._run_command(cmd, capture_output=False)

        if not os.path.exists(output_path):
            raise FFmpegError("Output file was not created")

        return output_path

    def concatenate_videos(
        self,
        input_paths: List[str],
        output_path: str,
        overwrite: bool = True
    ) -> str:
        """
        Concatenate multiple videos into one.

        Args:
            input_paths: List of input video paths
            output_path: Output video path
            overwrite: Whether to overwrite output file

        Returns:
            Path to output file

        Raises:
            FFmpegError: If concatenation fails
        """
        if not input_paths:
            raise FFmpegError("No input files provided")

        # Validate all paths
        validated_inputs = [
            self._validate_file_path(p, must_exist=True)
            for p in input_paths
        ]
        output_path = self._validate_file_path(output_path, must_exist=False)

        # Create concat file
        concat_file = output_path + '.concat.txt'
        try:
            with open(concat_file, 'w') as f:
                for path in validated_inputs:
                    # Escape single quotes in path
                    escaped_path = path.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            # Build command
            cmd = [
                self.ffmpeg_path,
                '-loglevel', FFMPEG_LOGLEVEL,
            ]

            if overwrite:
                cmd.append('-y')

            cmd.extend([
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                output_path
            ])

            # Run concatenation
            self._run_command(cmd, capture_output=False)

            if not os.path.exists(output_path):
                raise FFmpegError("Output file was not created")

            return output_path

        finally:
            # Clean up concat file
            if os.path.exists(concat_file):
                try:
                    os.remove(concat_file)
                except:
                    pass

    def extract_audio(
        self,
        input_path: str,
        output_path: str,
        audio_codec: str = 'aac',
        audio_bitrate: str = '192k',
        overwrite: bool = True
    ) -> str:
        """
        Extract audio from video.

        Args:
            input_path: Input video path
            output_path: Output audio path
            audio_codec: Audio codec
            audio_bitrate: Audio bitrate
            overwrite: Whether to overwrite output file

        Returns:
            Path to output file

        Raises:
            FFmpegError: If extraction fails
        """
        input_path = self._validate_file_path(input_path, must_exist=True)
        output_path = self._validate_file_path(output_path, must_exist=False)

        cmd = [
            self.ffmpeg_path,
            '-loglevel', FFMPEG_LOGLEVEL,
        ]

        if overwrite:
            cmd.append('-y')

        cmd.extend([
            '-i', input_path,
            '-vn',  # No video
            '-c:a', audio_codec,
            '-b:a', audio_bitrate,
            output_path
        ])

        self._run_command(cmd, capture_output=False)

        if not os.path.exists(output_path):
            raise FFmpegError("Output file was not created")

        return output_path

    def add_audio_to_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        video_volume: float = 1.0,
        audio_volume: float = 1.0,
        overwrite: bool = True
    ) -> str:
        """
        Add audio track to video.

        Args:
            video_path: Input video path
            audio_path: Input audio path
            output_path: Output video path
            video_volume: Video audio volume (0.0 to 1.0)
            audio_volume: Added audio volume (0.0 to 1.0)
            overwrite: Whether to overwrite output file

        Returns:
            Path to output file

        Raises:
            FFmpegError: If mixing fails
        """
        video_path = self._validate_file_path(video_path, must_exist=True)
        audio_path = self._validate_file_path(audio_path, must_exist=True)
        output_path = self._validate_file_path(output_path, must_exist=False)

        cmd = [
            self.ffmpeg_path,
            '-loglevel', FFMPEG_LOGLEVEL,
        ]

        if overwrite:
            cmd.append('-y')

        cmd.extend([
            '-i', video_path,
            '-i', audio_path,
            '-filter_complex',
            f'[0:a]volume={video_volume}[a1];[1:a]volume={audio_volume}[a2];[a1][a2]amix=inputs=2:duration=first',
            '-c:v', 'copy',
            '-c:a', 'aac',
            output_path
        ])

        self._run_command(cmd, capture_output=False)

        if not os.path.exists(output_path):
            raise FFmpegError("Output file was not created")

        return output_path


# Global instance
_ffmpeg = None


def get_ffmpeg() -> FFmpegWrapper:
    """
    Get global FFmpeg wrapper instance.

    Returns:
        FFmpeg wrapper instance
    """
    global _ffmpeg
    if _ffmpeg is None:
        _ffmpeg = FFmpegWrapper()
    return _ffmpeg


if __name__ == '__main__':
    # Test FFmpeg wrapper
    print("Testing FFmpeg Wrapper")
    print("=" * 70)

    try:
        ffmpeg = get_ffmpeg()
        print(f"FFmpeg path: {ffmpeg.ffmpeg_path}")
        print(f"FFprobe path: {ffmpeg.ffprobe_path}")
        print("\n[OK] FFmpeg wrapper initialized successfully")
    except FFmpegError as e:
        print(f"\n[ERROR] FFmpeg initialization failed: {e}")
