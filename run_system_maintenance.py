#!/usr/bin/env python3
"""
SYSTEM MAINTENANCE - ALL-IN-ONE
Runs all system improvements and maintenance tasks.
"""

import sys
import subprocess


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"🔧 {text}")
    print("=" * 70 + "\n")


def run_command(script_name, description):
    """Run a Python script and show output"""
    print(f"Running: {description}...")
    try:
        result = subprocess.run(
            ['python3', script_name],
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all maintenance tasks"""
    print("=" * 70)
    print("🚀 SYSTEM MAINTENANCE - ALL-IN-ONE")
    print("=" * 70)
    print("\nThis script will:")
    print("  1. Check system health")
    print("  2. Check authentication status")
    print("  3. Validate RankRiot channel")
    print("  4. Show trending system status")
    print("  5. Show file cleanup opportunities")
    print()

    # Ask for confirmation
    if '--yes' not in sys.argv:
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            return

    # 1. System Health
    print_header("SYSTEM HEALTH CHECK")
    run_command('system_health.py', 'System Health Monitor')

    # 2. Authentication
    print_header("AUTHENTICATION STATUS")
    run_command('auth_health_monitor.py', 'Authentication Health Monitor')

    # 3. RankRiot Status
    print_header("RANKRIOT CHANNEL STATUS")
    run_command('check_rankriot_status.py', 'RankRiot Status Check')

    # 4. Pre-Generation Validation
    print_header("PRE-GENERATION VALIDATION")
    run_command('pre_generation_validator.py', 'Pre-Generation Validator')

    # 5. Trending System
    print_header("TRENDING SYSTEM STATUS")
    run_command('test_trending_system.py', 'Trending System Test')

    # 6. File Cleanup Preview
    print_header("FILE CLEANUP OPPORTUNITIES")
    run_command('file_cleanup.py', 'File Cleanup Scanner')

    # Summary
    print("\n" + "=" * 70)
    print("✅ MAINTENANCE COMPLETE")
    print("=" * 70)
    print("\n📋 Next Steps:")
    print("   1. Review any CRITICAL issues above")
    print("   2. Fix authentication if needed (Settings tab)")
    print("   3. Run cleanup: python3 file_cleanup.py --execute")
    print("   4. Monitor success rate in daemon logs")
    print()


if __name__ == "__main__":
    main()
