#!/usr/bin/env python3
"""
AUTHENTICATION HEALTH MONITOR
Proactively checks and maintains YouTube authentication status.
Prevents 306 "Channel not authenticated" failures.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional


def check_token_file_exists(channel_name: str) -> bool:
    """
    Check if token file exists for channel.

    Args:
        channel_name: Name of channel

    Returns: True if token file exists
    """
    token_file = f"tokens/token_{channel_name.replace(' ', '_')}.json"
    return os.path.exists(token_file)


def check_token_validity(channel_name: str) -> Dict:
    """
    Check if token is valid and not expired.

    Args:
        channel_name: Name of channel

    Returns: Status dict
    """
    token_file = f"tokens/token_{channel_name.replace(' ', '_')}.json"

    if not os.path.exists(token_file):
        return {
            'valid': False,
            'reason': 'Token file not found',
            'action_needed': 'Re-authenticate in UI'
        }

    try:
        with open(token_file, 'r') as f:
            token_data = json.load(f)

        # Check if token has expiry info
        if 'expiry' in token_data:
            expiry = datetime.fromisoformat(token_data['expiry'].replace('Z', '+00:00'))
            now = datetime.now(expiry.tzinfo) if expiry.tzinfo else datetime.now()

            if expiry < now:
                return {
                    'valid': False,
                    'reason': f'Token expired {(now - expiry).days} days ago',
                    'action_needed': 'Token will auto-refresh on next use'
                }
            elif expiry < now + timedelta(days=1):
                return {
                    'valid': True,
                    'reason': 'Token expires soon',
                    'warning': 'Token expires within 24 hours'
                }

        # Token exists and is not expired
        return {
            'valid': True,
            'reason': 'Token is valid'
        }

    except Exception as e:
        return {
            'valid': False,
            'reason': f'Token file corrupted: {str(e)}',
            'action_needed': 'Delete token file and re-authenticate'
        }


def check_all_channels_auth() -> Dict:
    """
    Check authentication status for all channels.

    Returns: Status report
    """
    from channel_manager import get_all_channels
    from auth_manager import is_channel_authenticated

    channels = get_all_channels()
    report = {
        'total_channels': len(channels),
        'authenticated': 0,
        'not_authenticated': 0,
        'issues': []
    }

    for channel in channels:
        name = channel['name']
        is_active = channel.get('is_active', False)

        # Check if channel is authenticated
        try:
            authenticated = is_channel_authenticated(name)
        except:
            authenticated = False

        if authenticated:
            report['authenticated'] += 1

            # Check token validity
            token_status = check_token_validity(name)
            if not token_status['valid'] or 'warning' in token_status:
                report['issues'].append({
                    'channel': name,
                    'active': is_active,
                    'authenticated': True,
                    'issue': token_status.get('reason') or token_status.get('warning'),
                    'action': token_status.get('action_needed', 'Monitor')
                })
        else:
            report['not_authenticated'] += 1

            if is_active:
                # Active channel not authenticated = CRITICAL
                report['issues'].append({
                    'channel': name,
                    'active': is_active,
                    'authenticated': False,
                    'issue': 'Active channel not authenticated',
                    'action': 'URGENT: Re-authenticate in UI Settings tab',
                    'severity': 'CRITICAL'
                })

    return report


def auto_fix_auth_issues() -> Dict:
    """
    Automatically fix authentication issues where possible.

    Returns: Fix report
    """
    from channel_manager import get_all_channels, update_channel

    channels = get_all_channels()
    report = {
        'channels_checked': len(channels),
        'issues_found': 0,
        'auto_fixed': 0,
        'manual_action_needed': 0,
        'actions': []
    }

    for channel in channels:
        name = channel['name']
        is_active = channel.get('is_active', False)

        # Check token status
        token_status = check_token_validity(name)

        if not token_status['valid']:
            report['issues_found'] += 1

            # If channel is active but not authenticated, pause it
            if is_active:
                try:
                    update_channel(channel['id'], is_active=False)
                    report['auto_fixed'] += 1
                    report['actions'].append({
                        'channel': name,
                        'action': 'Auto-paused (not authenticated)',
                        'status': 'success'
                    })
                except Exception as e:
                    report['manual_action_needed'] += 1
                    report['actions'].append({
                        'channel': name,
                        'action': 'Failed to auto-pause',
                        'status': 'error',
                        'error': str(e)
                    })
            else:
                report['manual_action_needed'] += 1
                report['actions'].append({
                    'channel': name,
                    'action': 'Already paused, needs re-authentication',
                    'status': 'manual'
                })

    return report


def validate_before_generation(channel_name: str) -> Dict:
    """
    Pre-flight check before video generation.
    Prevents generation if authentication is invalid.

    Args:
        channel_name: Name of channel

    Returns: Validation result
    """
    from auth_manager import is_channel_authenticated

    checks = {
        'passed': True,
        'checks': []
    }

    # Check 1: Token file exists
    token_exists = check_token_file_exists(channel_name)
    checks['checks'].append({
        'name': 'Token file exists',
        'passed': token_exists,
        'details': 'Token file found' if token_exists else 'Token file missing'
    })

    if not token_exists:
        checks['passed'] = False
        checks['error'] = 'No token file - channel must be authenticated first'
        return checks

    # Check 2: Token is valid
    token_status = check_token_validity(channel_name)
    checks['checks'].append({
        'name': 'Token validity',
        'passed': token_status['valid'],
        'details': token_status['reason']
    })

    if not token_status['valid']:
        checks['passed'] = False
        checks['error'] = token_status['reason']
        return checks

    # Check 3: Can authenticate with YouTube API
    try:
        authenticated = is_channel_authenticated(channel_name)
        checks['checks'].append({
            'name': 'YouTube API authentication',
            'passed': authenticated,
            'details': 'Successfully authenticated' if authenticated else 'Authentication failed'
        })

        if not authenticated:
            checks['passed'] = False
            checks['error'] = 'Cannot authenticate with YouTube API'

    except Exception as e:
        checks['checks'].append({
            'name': 'YouTube API authentication',
            'passed': False,
            'details': f'Error: {str(e)}'
        })
        checks['passed'] = False
        checks['error'] = f'API authentication error: {str(e)}'

    return checks


# Testing
if __name__ == "__main__":
    print("=" * 70)
    print("AUTHENTICATION HEALTH MONITOR")
    print("=" * 70)

    # Check all channels
    print("\n[CHART] Checking all channels...\n")
    report = check_all_channels_auth()

    print(f"Total Channels: {report['total_channels']}")
    print(f"Authenticated: [OK] {report['authenticated']}")
    print(f"Not Authenticated: [ERROR] {report['not_authenticated']}\n")

    if report['issues']:
        print(f"[WARNING]  Found {len(report['issues'])} issue(s):\n")
        for issue in report['issues']:
            severity = issue.get('severity', 'WARNING')
            print(f"   [{severity}] {issue['channel']}")
            print(f"      Active: {issue['active']}")
            print(f"      Issue: {issue['issue']}")
            print(f"      Action: {issue['action']}\n")
    else:
        print("[OK] No authentication issues found!\n")

    print("=" * 70)
