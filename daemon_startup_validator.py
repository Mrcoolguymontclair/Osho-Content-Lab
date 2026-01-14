#!/usr/bin/env python3
"""
DAEMON STARTUP VALIDATOR
Checks ALL dependencies before daemon starts to prevent crashes.
"""

import sys
import importlib

def validate_all_imports():
    """Validate all required imports before daemon starts."""

    print("=" * 70)
    print("VALIDATING DAEMON DEPENDENCIES")
    print("=" * 70)

    required_modules = [
        # Core modules
        ('channel_manager', ['get_active_channels', 'get_channel', 'update_channel', 'add_video', 'update_video', 'add_log', 'track_error', 'reset_error_tracker', 'get_error_stats']),
        ('groq_manager', ['get_groq_client']),
        ('error_recovery', ['retry_with_backoff', 'RetryConfig']),
        ('video_engine', ['generate_video_script', 'assemble_viral_video', 'cleanup_video_files', 'check_disk_space', 'create_teaser_clip']),
        ('video_engine_ranking', ['generate_ranking_video']),
        ('auth_manager', ['upload_to_youtube', 'generate_youtube_metadata', 'is_channel_authenticated', 'start_auto_refresh', 'get_video_id_from_url', 'upload_thumbnail']),
        ('thumbnail_generator', ['generate_thumbnail']),
        ('autonomous_learner', ['start_autonomous_learning']),
        ('quota_manager', ['init_quota_table', 'check_quota', 'mark_quota_exhausted', 'check_and_reset_if_needed', 'auto_resume_paused_channels', 'get_quota_status_summary']),

        # Trending system
        ('google_trends_fetcher', ['fetch_all_trends']),
        ('trend_analyzer', ['analyze_multiple_trends', 'get_best_trend_for_channel']),
        ('video_planner_ai', ['plan_video_from_trend']),
        ('video_engine_dynamic', ['generate_video_from_plan']),
        ('trend_tracker', ['save_trend', 'update_trend_analysis', 'update_trend_video_plan', 'mark_trend_video_generated', 'get_best_pending_trend', 'check_trend_exists']),

        # Quality improvements
        ('title_thumbnail_optimizer', ['TitleThumbnailOptimizer']),
        ('video_quality_enhancer', ['VideoQualityEnhancer']),
    ]

    all_passed = True

    for module_name, functions in required_modules:
        try:
            module = importlib.import_module(module_name)

            # Check if all required functions exist
            missing = []
            for func in functions:
                if not hasattr(module, func):
                    missing.append(func)

            if missing:
                print(f"❌ {module_name}: Missing {', '.join(missing)}")
                all_passed = False
            else:
                print(f"✅ {module_name}")

        except ImportError as e:
            print(f"❌ {module_name}: Import failed - {e}")
            all_passed = False
        except Exception as e:
            print(f"❌ {module_name}: Error - {e}")
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("✅ ALL DEPENDENCIES VALIDATED - SAFE TO START DAEMON")
        return True
    else:
        print("❌ VALIDATION FAILED - FIX ERRORS BEFORE STARTING DAEMON")
        return False

if __name__ == "__main__":
    success = validate_all_imports()
    sys.exit(0 if success else 1)
