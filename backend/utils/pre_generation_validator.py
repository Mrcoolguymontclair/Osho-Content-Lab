#!/usr/bin/env python3
"""
PRE-GENERATION VALIDATOR
Validates all requirements before starting video generation.
Prevents wasted API calls and generation failures.
"""

import os
import subprocess
from typing import Dict, List
from datetime import datetime


class PreGenerationValidator:
    """
    Validates all prerequisites before video generation.
    Fails fast to prevent wasted resources.
    """

    def __init__(self):
        self.checks = [
            self.check_authentication,
            self.check_dependencies,
            self.check_api_keys,
            self.check_disk_space,
            self.check_quota,
            self.check_music_library
        ]

    def validate_all(self, channel_name: str) -> Dict:
        """
        Run all validation checks.

        Args:
            channel_name: Name of channel

        Returns: Validation result
        """
        result = {
            'passed': True,
            'channel': channel_name,
            'timestamp': datetime.now().isoformat(),
            'checks': [],
            'errors': [],
            'warnings': []
        }

        for check_func in self.checks:
            check_result = check_func(channel_name)
            result['checks'].append(check_result)

            if not check_result['passed']:
                result['passed'] = False
                result['errors'].append(check_result['message'])

            if check_result.get('warning'):
                result['warnings'].append(check_result['warning'])

        return result

    def check_authentication(self, channel_name: str) -> Dict:
        """Check YouTube authentication"""
        from auth_manager import is_channel_authenticated

        try:
            authenticated = is_channel_authenticated(channel_name)

            return {
                'name': 'Authentication',
                'passed': authenticated,
                'message': 'Channel authenticated' if authenticated else 'Channel not authenticated - please authenticate in Settings',
                'critical': True
            }
        except Exception as e:
            return {
                'name': 'Authentication',
                'passed': False,
                'message': f'Authentication check failed: {str(e)}',
                'critical': True
            }

    def check_dependencies(self, channel_name: str) -> Dict:
        """Check FFmpeg and other dependencies"""
        missing = []

        # Check ffmpeg
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                missing.append('ffmpeg')
        except:
            missing.append('ffmpeg')

        # Check ffprobe
        try:
            result = subprocess.run(['ffprobe', '-version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                missing.append('ffprobe')
        except:
            missing.append('ffprobe')

        if missing:
            return {
                'name': 'Dependencies',
                'passed': False,
                'message': f'Missing dependencies: {", ".join(missing)} - Install with: brew install ffmpeg',
                'critical': True
            }
        else:
            return {
                'name': 'Dependencies',
                'passed': True,
                'message': 'All dependencies available',
                'critical': True
            }

    def check_api_keys(self, channel_name: str) -> Dict:
        """Check required API keys"""
        import toml

        secrets_path = '.streamlit/secrets.toml'

        if not os.path.exists(secrets_path):
            return {
                'name': 'API Keys',
                'passed': False,
                'message': 'secrets.toml not found',
                'critical': True
            }

        try:
            secrets = toml.load(secrets_path)

            required_keys = ['GROQ_API_KEY', 'PEXELS_API_KEY', 'ELEVENLABS_API_KEY']
            missing = [key for key in required_keys if not secrets.get(key)]

            if missing:
                return {
                    'name': 'API Keys',
                    'passed': False,
                    'message': f'Missing API keys: {", ".join(missing)}',
                    'critical': True
                }
            else:
                return {
                    'name': 'API Keys',
                    'passed': True,
                    'message': 'All required API keys configured',
                    'critical': True
                }
        except Exception as e:
            return {
                'name': 'API Keys',
                'passed': False,
                'message': f'Error reading secrets: {str(e)}',
                'critical': True
            }

    def check_disk_space(self, channel_name: str) -> Dict:
        """Check available disk space"""
        import shutil

        try:
            stat = shutil.disk_usage('.')
            free_gb = stat.free / (1024 ** 3)

            if free_gb < 1:
                return {
                    'name': 'Disk Space',
                    'passed': False,
                    'message': f'Low disk space: {free_gb:.1f} GB free (need at least 1 GB)',
                    'critical': True
                }
            elif free_gb < 5:
                return {
                    'name': 'Disk Space',
                    'passed': True,
                    'message': f'Disk space OK: {free_gb:.1f} GB free',
                    'warning': f'Low disk space: {free_gb:.1f} GB free',
                    'critical': False
                }
            else:
                return {
                    'name': 'Disk Space',
                    'passed': True,
                    'message': f'Disk space OK: {free_gb:.1f} GB free',
                    'critical': False
                }
        except Exception as e:
            return {
                'name': 'Disk Space',
                'passed': True,
                'message': f'Could not check disk space: {str(e)}',
                'warning': 'Disk space check failed',
                'critical': False
            }

    def check_quota(self, channel_name: str) -> Dict:
        """Check YouTube API quota status"""
        from quota_manager import check_quota

        try:
            has_quota = check_quota()

            if not has_quota:
                return {
                    'name': 'YouTube Quota',
                    'passed': False,
                    'message': 'YouTube API quota exhausted - will auto-resume at midnight PST',
                    'critical': True
                }
            else:
                return {
                    'name': 'YouTube Quota',
                    'passed': True,
                    'message': 'YouTube quota available',
                    'critical': True
                }
        except Exception as e:
            return {
                'name': 'YouTube Quota',
                'passed': True,
                'message': f'Could not check quota: {str(e)}',
                'warning': 'Quota check failed',
                'critical': False
            }

    def check_music_library(self, channel_name: str) -> Dict:
        """Check music library availability"""
        music_dir = 'music'

        if not os.path.exists(music_dir):
            return {
                'name': 'Music Library',
                'passed': True,
                'message': 'Music directory not found (videos will have no background music)',
                'warning': 'No music directory found',
                'critical': False
            }

        try:
            music_files = [f for f in os.listdir(music_dir) if f.endswith(('.mp3', '.wav'))]

            if len(music_files) == 0:
                return {
                    'name': 'Music Library',
                    'passed': True,
                    'message': 'No music files found (videos will have no background music)',
                    'warning': 'No music files found',
                    'critical': False
                }
            else:
                return {
                    'name': 'Music Library',
                    'passed': True,
                    'message': f'{len(music_files)} music tracks available',
                    'critical': False
                }
        except Exception as e:
            return {
                'name': 'Music Library',
                'passed': True,
                'message': f'Could not check music library: {str(e)}',
                'warning': 'Music check failed',
                'critical': False
            }


def validate_before_generation(channel_name: str) -> Dict:
    """
    Convenience function for pre-generation validation.

    Args:
        channel_name: Name of channel

    Returns: Validation result
    """
    validator = PreGenerationValidator()
    return validator.validate_all(channel_name)


def print_validation_result(result: Dict):
    """Print formatted validation result"""
    print("=" * 70)
    print(f" PRE-GENERATION VALIDATION: {result['channel']}")
    print("=" * 70)

    # Overall result
    if result['passed']:
        print("\n[OK] PASSED - Ready for video generation\n")
    else:
        print("\n[ERROR] FAILED - Cannot generate video\n")

    # Individual checks
    print("Validation Checks:\n")
    for check in result['checks']:
        icon = '[OK]' if check['passed'] else '[ERROR]'
        critical = ' (CRITICAL)' if check.get('critical') else ''
        print(f"   {icon} {check['name']}{critical}")
        print(f"      {check['message']}")
        if check.get('warning'):
            print(f"      [WARNING]  {check['warning']}")
        print()

    # Errors
    if result['errors']:
        print("[ERROR] ERRORS:\n")
        for i, error in enumerate(result['errors'], 1):
            print(f"   {i}. {error}")
        print()

    # Warnings
    if result['warnings']:
        print("[WARNING]  WARNINGS:\n")
        for i, warning in enumerate(result['warnings'], 1):
            print(f"   {i}. {warning}")
        print()

    print("=" * 70)


# Testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        channel_name = sys.argv[1]
    else:
        # Get first channel from database
        from channel_manager import get_all_channels
        channels = get_all_channels()
        if channels:
            channel_name = channels[0]['name']
        else:
            print("No channels found in database")
            sys.exit(1)

    result = validate_before_generation(channel_name)
    print_validation_result(result)

    sys.exit(0 if result['passed'] else 1)
