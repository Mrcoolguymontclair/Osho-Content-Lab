"""
Base Video Engine

Abstract base class for all video generation engines.
Provides common functionality and standardized interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import os
import time
from dataclasses import dataclass
from logger import get_logger
from ffmpeg_wrapper import get_ffmpeg
from advanced_video_enhancer import get_enhancer
from parallel_downloader import get_downloader
from error_handler import retry_with_backoff, ErrorCategory, handle_errors

logger = get_logger(__name__)


@dataclass
class VideoGenerationResult:
    """Result of video generation."""
    success: bool
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    metadata: Dict = None
    error: Optional[str] = None
    generation_time: float = 0.0

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class VideoEngineBase(ABC):
    """
    Abstract base class for video generation engines.

    All video engines should inherit from this class and implement
    the abstract methods.
    """

    def __init__(
        self,
        output_dir: str = "output",
        temp_dir: str = "temp",
        enhancement_profile: str = "viral"
    ):
        """
        Initialize video engine.

        Args:
            output_dir: Directory for final outputs
            temp_dir: Directory for temporary files
            enhancement_profile: Video enhancement profile
        """
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        self.enhancement_profile = enhancement_profile

        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        # Initialize components
        self.ffmpeg = get_ffmpeg()
        self.enhancer = get_enhancer(enhancement_profile)
        self.downloader = get_downloader(max_workers=5)

        logger.info(f"Initialized {self.__class__.__name__} with {enhancement_profile} profile")

    @abstractmethod
    def generate_script(self, **kwargs) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Generate video script.

        Returns:
            (success, script_dict, error_message)
        """
        pass

    @abstractmethod
    def search_clips(self, script: Dict, **kwargs) -> Tuple[bool, Optional[List], Optional[str]]:
        """
        Search for video clips.

        Args:
            script: Video script dictionary

        Returns:
            (success, clips_list, error_message)
        """
        pass

    @abstractmethod
    def generate_voiceover(self, script: Dict, output_path: str, **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Generate voiceover audio.

        Args:
            script: Video script dictionary
            output_path: Output audio file path

        Returns:
            (success, error_message)
        """
        pass

    def download_clips_parallel(
        self,
        clips: List[Dict],
        output_dir: str
    ) -> List[str]:
        """
        Download video clips in parallel.

        Args:
            clips: List of clip dictionaries from Pexels
            output_dir: Output directory

        Returns:
            List of downloaded file paths
        """
        logger.info(f"Downloading {len(clips)} clips in parallel")

        os.makedirs(output_dir, exist_ok=True)

        # Download using parallel downloader
        results = self.downloader.download_pexels_clips(
            clips=clips,
            output_dir=output_dir,
            size='hd'
        )

        # Extract successful downloads
        downloaded_paths = [
            r.file_path for r in results
            if r.success and r.file_path
        ]

        logger.info(f"Successfully downloaded {len(downloaded_paths)}/{len(clips)} clips")

        return downloaded_paths

    def enhance_clips(
        self,
        clip_paths: List[str],
        output_dir: str
    ) -> List[str]:
        """
        Apply enhancements to all clips.

        Args:
            clip_paths: List of clip file paths
            output_dir: Output directory for enhanced clips

        Returns:
            List of enhanced clip paths
        """
        logger.info(f"Enhancing {len(clip_paths)} clips")

        os.makedirs(output_dir, exist_ok=True)
        enhanced_paths = []

        for i, clip_path in enumerate(clip_paths):
            try:
                enhanced_path = os.path.join(output_dir, f"enhanced_{i}.mp4")
                self.enhancer.enhance_clip(
                    input_path=clip_path,
                    output_path=enhanced_path,
                    clip_index=i
                )
                enhanced_paths.append(enhanced_path)
            except Exception as e:
                logger.error(f"Failed to enhance clip {i}: {e}")
                # Use original if enhancement fails
                enhanced_paths.append(clip_path)

        logger.info(f"Enhanced {len(enhanced_paths)} clips")
        return enhanced_paths

    def assemble_video(
        self,
        clips: List[str],
        voiceover_path: str,
        output_path: str,
        background_music: Optional[str] = None
    ) -> str:
        """
        Assemble final video from clips and audio.

        Args:
            clips: List of video clip paths
            voiceover_path: Voiceover audio path
            output_path: Output video path
            background_music: Optional background music path

        Returns:
            Path to assembled video
        """
        logger.info(f"Assembling video from {len(clips)} clips")

        # Apply transitions between clips
        temp_video = os.path.join(self.temp_dir, "temp_assembled.mp4")
        self.enhancer.apply_transitions(
            clips=clips,
            output_path=temp_video,
            transition_duration=0.3
        )

        # Add audio
        if background_music:
            # Mix voiceover and background music
            temp_audio_mixed = os.path.join(self.temp_dir, "temp_audio_mixed.mp4")
            self.ffmpeg.add_audio_to_video(
                video_path=temp_video,
                audio_path=voiceover_path,
                output_path=temp_audio_mixed,
                video_volume=0.8,
                audio_volume=0.2
            )
            current_video = temp_audio_mixed
        else:
            # Just add voiceover
            temp_with_audio = os.path.join(self.temp_dir, "temp_with_audio.mp4")
            self.ffmpeg.add_audio_to_video(
                video_path=temp_video,
                audio_path=voiceover_path,
                output_path=temp_with_audio,
                video_volume=1.0,
                audio_volume=1.0
            )
            current_video = temp_with_audio

        # Final enhancement
        self.enhancer.enhance_complete_video(
            input_path=current_video,
            output_path=output_path,
            add_hooks=True
        )

        logger.info(f"Video assembled successfully: {output_path}")
        return output_path

    @handle_errors(category=ErrorCategory.UNKNOWN, raise_on_error=False)
    def cleanup_temp_files(self):
        """Clean up temporary files."""
        logger.debug("Cleaning up temporary files")

        if os.path.exists(self.temp_dir):
            for file in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {file_path}: {e}")

    @abstractmethod
    def generate(self, **kwargs) -> VideoGenerationResult:
        """
        Main video generation method.

        This is the primary method that should be called to generate a video.
        It orchestrates the entire video generation process.

        Returns:
            VideoGenerationResult
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup_temp_files()


class SimpleVideoEngine(VideoEngineBase):
    """
    Simple example implementation of video engine.

    This serves as a template for creating new video engines.
    """

    def generate_script(self, topic: str = "example", **kwargs) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Generate a simple script."""
        script = {
            'title': f"Amazing {topic}",
            'description': f"Learn about {topic}",
            'narration': f"This is a video about {topic}. It's very interesting!",
            'tags': [topic, 'shorts', 'viral']
        }
        return True, script, None

    def search_clips(self, script: Dict, **kwargs) -> Tuple[bool, Optional[List], Optional[str]]:
        """Search for clips (placeholder)."""
        # In real implementation, search Pexels/other sources
        return True, [], None

    def generate_voiceover(self, script: Dict, output_path: str, **kwargs) -> Tuple[bool, Optional[str]]:
        """Generate voiceover (placeholder)."""
        # In real implementation, use TTS
        return True, None

    def generate(self, topic: str = "example", **kwargs) -> VideoGenerationResult:
        """
        Generate video (simple implementation).

        Args:
            topic: Video topic
            **kwargs: Additional arguments

        Returns:
            VideoGenerationResult
        """
        start_time = time.time()

        try:
            # Generate script
            success, script, error = self.generate_script(topic=topic)
            if not success:
                return VideoGenerationResult(
                    success=False,
                    error=error or "Script generation failed"
                )

            # Search clips
            success, clips, error = self.search_clips(script)
            if not success:
                return VideoGenerationResult(
                    success=False,
                    error=error or "Clip search failed"
                )

            # Generate voiceover
            voiceover_path = os.path.join(self.temp_dir, "voiceover.mp3")
            success, error = self.generate_voiceover(script, voiceover_path)
            if not success:
                return VideoGenerationResult(
                    success=False,
                    error=error or "Voiceover generation failed"
                )

            # Assemble video (if we have clips)
            if clips:
                output_path = os.path.join(self.output_dir, f"video_{int(time.time())}.mp4")
                self.assemble_video(
                    clips=clips,
                    voiceover_path=voiceover_path,
                    output_path=output_path
                )

                generation_time = time.time() - start_time

                return VideoGenerationResult(
                    success=True,
                    video_path=output_path,
                    metadata=script,
                    generation_time=generation_time
                )
            else:
                return VideoGenerationResult(
                    success=False,
                    error="No clips found"
                )

        except Exception as e:
            logger.error(f"Video generation failed: {e}", exc_info=True)
            return VideoGenerationResult(
                success=False,
                error=str(e),
                generation_time=time.time() - start_time
            )


if __name__ == '__main__':
    print("Video Engine Base")
    print("=" * 70)
    print("\nBase class for all video generation engines.")
    print("Provides common functionality:")
    print("  - Parallel clip downloading")
    print("  - Video enhancement")
    print("  - Audio mixing")
    print("  - Transition effects")
    print("  - Standardized interface")
    print("\n[OK] Video engine base ready")
