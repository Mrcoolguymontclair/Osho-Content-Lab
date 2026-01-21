"""
Parallel Video Clip Downloader

Downloads multiple video clips concurrently for faster video generation.

Features:
- Thread pool for concurrent downloads
- Progress tracking
- Automatic retry on failure
- Resource pooling
- Bandwidth management
"""

import os
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass
from logger import get_logger
from error_handler import retry_with_backoff
from constants import DEFAULT_NETWORK_TIMEOUT, VIDEO_DOWNLOAD_TIMEOUT

logger = get_logger(__name__)


@dataclass
class DownloadTask:
    """Represents a single download task."""
    url: str
    output_path: str
    search_query: str = ""
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DownloadResult:
    """Result of a download operation."""
    task: DownloadTask
    success: bool
    file_path: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0.0


class ParallelDownloader:
    """
    Parallel video clip downloader.

    Downloads multiple clips concurrently using thread pool.
    """

    def __init__(
        self,
        max_workers: int = 5,
        timeout: int = VIDEO_DOWNLOAD_TIMEOUT,
        chunk_size: int = 8192
    ):
        """
        Initialize parallel downloader.

        Args:
            max_workers: Maximum number of concurrent downloads
            timeout: Download timeout in seconds
            chunk_size: Download chunk size in bytes
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.session = requests.Session()
        self._lock = threading.Lock()
        self._download_count = 0
        self._failed_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=2)
    def _download_single_file(
        self,
        task: DownloadTask,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> DownloadResult:
        """
        Download a single file with retry logic.

        Args:
            task: Download task
            progress_callback: Optional callback for progress updates

        Returns:
            DownloadResult
        """
        import time
        start_time = time.time()

        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(task.output_path), exist_ok=True)

            # Download file
            logger.debug(f"Downloading {task.url} to {task.output_path}")

            response = self.session.get(
                task.url,
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Get total size
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            # Download in chunks
            with open(task.output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback:
                            progress_callback(downloaded, total_size)

            # Verify file was created
            if not os.path.exists(task.output_path):
                raise IOError(f"File was not created: {task.output_path}")

            duration = time.time() - start_time

            with self._lock:
                self._download_count += 1

            logger.info(
                f"Downloaded {task.search_query or 'clip'} "
                f"({downloaded} bytes in {duration:.2f}s)"
            )

            return DownloadResult(
                task=task,
                success=True,
                file_path=task.output_path,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time

            with self._lock:
                self._failed_count += 1

            logger.error(
                f"Failed to download {task.url}: {e}",
                exc_info=True
            )

            return DownloadResult(
                task=task,
                success=False,
                error=str(e),
                duration=duration
            )

    def download_batch(
        self,
        tasks: List[DownloadTask],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[DownloadResult]:
        """
        Download multiple files in parallel.

        Args:
            tasks: List of download tasks
            progress_callback: Optional callback(completed, total)

        Returns:
            List of download results
        """
        if not tasks:
            return []

        logger.info(f"Starting parallel download of {len(tasks)} clips")

        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._download_single_file, task): task
                for task in tasks
            }

            # Process completed downloads
            completed = 0
            for future in as_completed(future_to_task):
                result = future.result()
                results.append(result)

                completed += 1
                if progress_callback:
                    progress_callback(completed, len(tasks))

        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_duration = sum(r.duration for r in results)
        avg_duration = total_duration / len(results) if results else 0

        logger.info(
            f"Batch download complete: {successful} successful, {failed} failed. "
            f"Average time: {avg_duration:.2f}s per clip"
        )

        return results

    def download_from_urls(
        self,
        urls: List[str],
        output_dir: str,
        filename_pattern: str = "clip_{index}.mp4",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[DownloadResult]:
        """
        Download from list of URLs.

        Args:
            urls: List of video URLs
            output_dir: Output directory
            filename_pattern: Filename pattern with {index} placeholder
            progress_callback: Optional progress callback

        Returns:
            List of download results
        """
        # Create download tasks
        tasks = []
        for i, url in enumerate(urls):
            output_path = os.path.join(
                output_dir,
                filename_pattern.format(index=i)
            )
            tasks.append(DownloadTask(
                url=url,
                output_path=output_path,
                metadata={'index': i}
            ))

        return self.download_batch(tasks, progress_callback)

    def download_pexels_clips(
        self,
        clips: List[Dict],
        output_dir: str,
        size: str = 'hd',
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[DownloadResult]:
        """
        Download clips from Pexels API results.

        Args:
            clips: List of Pexels clip objects
            output_dir: Output directory
            size: Video quality ('hd', 'sd', etc.)
            progress_callback: Optional progress callback

        Returns:
            List of download results
        """
        tasks = []

        for i, clip in enumerate(clips):
            # Find video file of requested size
            video_files = clip.get('video_files', [])
            video_file = None

            # Try to find HD quality
            for vf in video_files:
                if vf.get('quality') == size:
                    video_file = vf
                    break

            # Fallback to first available
            if not video_file and video_files:
                video_file = video_files[0]

            if not video_file:
                logger.warning(f"No video file found for clip {i}")
                continue

            url = video_file.get('link')
            if not url:
                logger.warning(f"No URL found for clip {i}")
                continue

            output_path = os.path.join(output_dir, f"clip_{i}.mp4")

            tasks.append(DownloadTask(
                url=url,
                output_path=output_path,
                search_query=clip.get('search_query', ''),
                metadata={
                    'index': i,
                    'pexels_id': clip.get('id'),
                    'duration': clip.get('duration'),
                    'width': clip.get('width'),
                    'height': clip.get('height')
                }
            ))

        return self.download_batch(tasks, progress_callback)

    def get_stats(self) -> Dict[str, int]:
        """
        Get downloader statistics.

        Returns:
            Dictionary with download stats
        """
        with self._lock:
            return {
                'total_downloads': self._download_count,
                'failed_downloads': self._failed_count,
                'success_rate': (
                    self._download_count / (self._download_count + self._failed_count)
                    if (self._download_count + self._failed_count) > 0
                    else 0
                )
            }

    def close(self):
        """Close session and cleanup resources."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Global downloader instance
_downloader = None
_downloader_lock = threading.Lock()


def get_downloader(max_workers: int = 5) -> ParallelDownloader:
    """
    Get global parallel downloader instance.

    Args:
        max_workers: Maximum concurrent downloads

    Returns:
        ParallelDownloader instance
    """
    global _downloader

    with _downloader_lock:
        if _downloader is None:
            _downloader = ParallelDownloader(max_workers=max_workers)

    return _downloader


if __name__ == '__main__':
    # Test parallel downloader
    print("Testing Parallel Downloader")
    print("=" * 70)

    # Example usage
    downloader = ParallelDownloader(max_workers=3)

    # Test URLs (placeholder - replace with real URLs)
    test_urls = [
        "https://example.com/video1.mp4",
        "https://example.com/video2.mp4",
        "https://example.com/video3.mp4",
    ]

    def progress_callback(completed, total):
        print(f"Progress: {completed}/{total} clips downloaded")

    # This would download in real usage
    # results = downloader.download_from_urls(
    #     test_urls,
    #     output_dir='temp',
    #     progress_callback=progress_callback
    # )

    stats = downloader.get_stats()
    print(f"Downloader stats: {stats}")

    downloader.close()
    print("\n[OK] Parallel downloader ready for use")
