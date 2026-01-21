"""
File Reorganization Script

Consolidates the codebase into a clean frontend/backend structure.
"""

import os
import shutil
from pathlib import Path

# New directory structure
STRUCTURE = {
    'frontend': [
        'new_vid_gen.py',
    ],
    'backend/core': [
        'youtube_daemon.py',
        'daemon_keeper.py',
        'daemon_startup_validator.py',
        'youtube_analytics.py',
    ],
    'backend/video': [
        'video_engine_base.py',
        'video_engine.py',
        'video_engine_ranking.py',
        'video_engine_ranking_v2.py',
        'video_engine_dynamic.py',
        'unified_video_generator.py',
        'advanced_video_enhancer.py',
        'video_quality_enhancer.py',
        'video_planner_ai.py',
        'audio_ducking.py',
        'pacing_optimizer.py',
        'thumbnail_ai.py',
        'thumbnail_generator.py',
        'title_thumbnail_optimizer.py',
    ],
    'backend/ai': [
        'ai_analyzer.py',
        'ai_analytics_enhanced.py',
        'learning_loop.py',
        'ab_testing_framework.py',
        'ab_experiment_runner.py',
        'groq_manager.py',
    ],
    'backend/workers': [
        'autonomous_learner.py',
        'google_trends_fetcher.py',
        'trend_analyzer.py',
        'trend_tracker.py',
    ],
    'backend/config': [
        'config_manager.py',
        'constants.py',
        'auth_manager.py',
        'auth_manager_bulletproof.py',
        'auth_health_monitor.py',
        'quota_manager.py',
    ],
    'backend/utils': [
        'channel_manager.py',
        'logger.py',
        'error_handler.py',
        'error_recovery.py',
        'input_validator.py',
        'cache_manager.py',
        'ffmpeg_wrapper.py',
        'health_monitor.py',
        'parallel_downloader.py',
        'music_manager.py',
        'system_health.py',
        'pre_generation_validator.py',
        'quality_checker.py',
        'performance_tracker.py',
        'duplicate_detector.py',
        'viral_topic_selector.py',
        'file_cleanup.py',
        'time_formatter.py',
    ],
    'backend/legacy': [
        # Old/deprecated files we might still need
        'add_music.py',
        'harmony_snippets.py',
        'engagement_handler.py',
        'remove_emojis.py',
    ],
    'docs': [
        # Move all .md files here
    ],
}

def create_directory_structure():
    """Create all directories."""
    print("Creating directory structure...")

    for directory in STRUCTURE.keys():
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"  Created: {directory}/")

    # Create __init__.py files for Python packages
    backend_dirs = [
        'backend',
        'backend/core',
        'backend/video',
        'backend/ai',
        'backend/workers',
        'backend/config',
        'backend/utils',
        'backend/legacy',
    ]

    for directory in backend_dirs:
        init_file = Path(directory) / '__init__.py'
        if not init_file.exists():
            init_file.write_text('"""Backend package."""\n')
            print(f"  Created: {directory}/__init__.py")

def move_files_dry_run():
    """Show what would be moved (dry run)."""
    print("\nDRY RUN - Files to be moved:")
    print("=" * 70)

    for destination, files in STRUCTURE.items():
        if files and destination != 'docs':
            print(f"\n{destination}:")
            for file in files:
                source = Path(file)
                if source.exists():
                    print(f"  {file} -> {destination}/")
                else:
                    print(f"  {file} [NOT FOUND]")

    # Show markdown files
    md_files = list(Path('.').glob('*.md'))
    print(f"\ndocs/ ({len(md_files)} markdown files)")

def move_files():
    """Actually move the files."""
    print("\nMoving files...")
    moved_count = 0
    not_found = []

    for destination, files in STRUCTURE.items():
        if destination == 'docs':
            continue

        for file in files:
            source = Path(file)
            dest = Path(destination) / file

            if source.exists():
                shutil.copy2(source, dest)
                moved_count += 1
                print(f"  Copied: {file} -> {destination}/")
            else:
                not_found.append(file)

    # Move markdown files
    md_files = list(Path('.').glob('*.md'))
    for md_file in md_files:
        if md_file.name not in ['README.md']:  # Keep README in root
            dest = Path('docs') / md_file.name
            shutil.copy2(md_file, dest)
            moved_count += 1

    print(f"\n  Total files copied: {moved_count}")

    if not_found:
        print(f"\n  Files not found: {len(not_found)}")
        for f in not_found[:5]:
            print(f"    - {f}")

def create_init_files():
    """Create comprehensive __init__.py files."""

    # Backend main init
    backend_init = Path('backend/__init__.py')
    backend_init.write_text('''"""
Osho Content Lab - Backend

Core video generation and automation system.
"""

from .config.config_manager import get_config
from .config.constants import *
from .utils.logger import get_logger

__version__ = '2.0.0'
''')

    # Config init
    config_init = Path('backend/config/__init__.py')
    config_init.write_text('''"""Backend configuration."""

from .config_manager import get_config, ConfigManager
from .constants import *
from .auth_manager_bulletproof import (
    get_valid_credentials,
    authenticate_channel,
    get_youtube_service
)

__all__ = ['get_config', 'ConfigManager', 'get_valid_credentials',
           'authenticate_channel', 'get_youtube_service']
''')

    # Utils init
    utils_init = Path('backend/utils/__init__.py')
    utils_init.write_text('''"""Backend utilities."""

from .logger import get_logger
from .error_handler import retry_with_backoff, handle_errors
from .cache_manager import get_cache_manager, cached
from .input_validator import InputValidator
from .parallel_downloader import get_downloader
from .health_monitor import get_health_monitor

__all__ = ['get_logger', 'retry_with_backoff', 'handle_errors',
           'get_cache_manager', 'cached', 'InputValidator',
           'get_downloader', 'get_health_monitor']
''')

    print("\n__init__.py files created with proper exports")

def main():
    """Main reorganization function."""
    print("=" * 70)
    print("OSHO CONTENT LAB - FILE REORGANIZATION")
    print("=" * 70)

    # Step 1: Show what will be done
    move_files_dry_run()

    print("\n" + "=" * 70)
    response = input("\nProceed with reorganization? (yes/no): ")

    if response.lower() != 'yes':
        print("Aborted.")
        return

    # Step 2: Create structure
    create_directory_structure()

    # Step 3: Move files
    move_files()

    # Step 4: Create init files
    create_init_files()

    print("\n" + "=" * 70)
    print("REORGANIZATION COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Update imports in files (use backend.config, backend.utils, etc.)")
    print("  2. Test that everything still works")
    print("  3. Remove old files from root (after testing)")
    print("  4. Update documentation")

if __name__ == '__main__':
    main()
