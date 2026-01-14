#!/usr/bin/env python3
"""
SYSTEM HEALTH MONITOR
Comprehensive health dashboard for the entire automation system.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List
import subprocess


class SystemHealthMonitor:
    """Monitors overall system health"""

    def __init__(self):
        self.db_path = 'channels.db'

    def check_database_health(self) -> Dict:
        """Check database connectivity and integrity"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Test query
            cursor.execute("SELECT COUNT(*) FROM channels")
            channel_count = cursor.fetchone()[0]

            # Check for corruption
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()[0]

            conn.close()

            return {
                'status': 'healthy' if integrity == 'ok' else 'corrupted',
                'channels': channel_count,
                'integrity': integrity,
                'error': None
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def check_daemon_health(self) -> Dict:
        """Check if daemon is running"""
        pid_file = 'daemon.pid'

        if not os.path.exists(pid_file):
            return {
                'status': 'stopped',
                'running': False,
                'error': 'PID file not found'
            }

        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())

            # Check if process is running
            try:
                os.kill(pid, 0)  # Signal 0 = check if process exists
                return {
                    'status': 'running',
                    'running': True,
                    'pid': pid
                }
            except OSError:
                return {
                    'status': 'stopped',
                    'running': False,
                    'error': 'Process not found'
                }
        except Exception as e:
            return {
                'status': 'error',
                'running': False,
                'error': str(e)
            }

    def check_authentication_health(self) -> Dict:
        """Check authentication status for all channels"""
        from auth_health_monitor import check_all_channels_auth

        try:
            report = check_all_channels_auth()

            status = 'healthy'
            if report['not_authenticated'] > 0:
                status = 'degraded' if report['authenticated'] > 0 else 'critical'

            critical_issues = [i for i in report.get('issues', []) if i.get('severity') == 'CRITICAL']

            return {
                'status': status,
                'authenticated': report['authenticated'],
                'not_authenticated': report['not_authenticated'],
                'critical_issues': len(critical_issues),
                'issues': report.get('issues', [])
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def check_video_generation_health(self) -> Dict:
        """Check video generation success rate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Last 24 hours stats
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status='posted' THEN 1 ELSE 0 END) as posted,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status='generating' THEN 1 ELSE 0 END) as generating
            FROM videos
            WHERE created_at >= datetime('now', '-24 hours')
        """)

        row = cursor.fetchone()
        total, posted, failed, generating = row

        # Overall stats
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status='posted' THEN 1 ELSE 0 END) as posted,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
            FROM videos
        """)

        overall_total, overall_posted, overall_failed = cursor.fetchone()

        conn.close()

        # Calculate success rates
        success_rate_24h = (posted / total * 100) if total > 0 else 0
        success_rate_overall = (overall_posted / overall_total * 100) if overall_total > 0 else 0

        # Determine status
        if success_rate_24h >= 70:
            status = 'healthy'
        elif success_rate_24h >= 40:
            status = 'degraded'
        else:
            status = 'critical'

        return {
            'status': status,
            'last_24h': {
                'total': total,
                'posted': posted,
                'failed': failed,
                'generating': generating,
                'success_rate': round(success_rate_24h, 1)
            },
            'overall': {
                'total': overall_total,
                'posted': overall_posted,
                'failed': overall_failed,
                'success_rate': round(success_rate_overall, 1)
            }
        }

    def check_disk_space_health(self) -> Dict:
        """Check disk space usage"""
        from file_cleanup import get_disk_usage_report, scan_output_directory

        usage = get_disk_usage_report()

        if not usage.get('exists'):
            return {
                'status': 'unknown',
                'error': 'outputs directory not found'
            }

        # Check for deletable files
        scan = scan_output_directory(days_old=7)
        deletable_gb = scan['deletable_size_mb'] / 1024

        # Determine status
        if usage['total_size_gb'] < 10:
            status = 'healthy'
        elif usage['total_size_gb'] < 20:
            status = 'warning'
        else:
            status = 'critical'

        return {
            'status': status,
            'total_size_gb': usage['total_size_gb'],
            'total_files': usage['total_files'],
            'deletable_gb': round(deletable_gb, 2),
            'deletable_files': scan['deletable_files']
        }

    def check_dependencies_health(self) -> Dict:
        """Check required dependencies"""
        dependencies = {
            'ffmpeg': ['ffmpeg', '-version'],
            'ffprobe': ['ffprobe', '-version'],
            'python': ['python3', '--version']
        }

        results = {}

        for name, command in dependencies.items():
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    timeout=5
                )
                results[name] = {
                    'available': result.returncode == 0,
                    'version': result.stdout.decode().split('\n')[0] if result.returncode == 0 else None
                }
            except Exception as e:
                results[name] = {
                    'available': False,
                    'error': str(e)
                }

        all_available = all(r['available'] for r in results.values())

        return {
            'status': 'healthy' if all_available else 'critical',
            'dependencies': results
        }

    def check_api_keys_health(self) -> Dict:
        """Check API keys configuration"""
        from groq_manager import get_groq_client

        try:
            groq_client = get_groq_client()
            groq_keys = len(groq_client.api_keys)
        except:
            groq_keys = 0

        # Check secrets.toml
        secrets_path = '.streamlit/secrets.toml'
        secrets_exists = os.path.exists(secrets_path)

        if secrets_exists:
            import toml
            secrets = toml.load(secrets_path)

            api_keys = {
                'GEMINI_API_KEY': bool(secrets.get('GEMINI_API_KEY')),
                'PEXELS_API_KEY': bool(secrets.get('PEXELS_API_KEY')),
                'ELEVENLABS_API_KEY': bool(secrets.get('ELEVENLABS_API_KEY')),
                'GROQ_API_KEY': bool(secrets.get('GROQ_API_KEY')),
                'YOUTUBE_API_KEY': bool(secrets.get('YOUTUBE_API_KEY')),
                'GROQ_API_KEY_2': bool(secrets.get('GROQ_API_KEY_2'))
            }

            configured_count = sum(api_keys.values())
            total_count = len(api_keys)

            return {
                'status': 'healthy' if configured_count == total_count else 'degraded',
                'configured': configured_count,
                'total': total_count,
                'groq_keys': groq_keys,
                'keys': api_keys
            }
        else:
            return {
                'status': 'critical',
                'error': 'secrets.toml not found'
            }

    def get_full_health_report(self) -> Dict:
        """Get comprehensive health report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {
                'database': self.check_database_health(),
                'daemon': self.check_daemon_health(),
                'authentication': self.check_authentication_health(),
                'video_generation': self.check_video_generation_health(),
                'disk_space': self.check_disk_space_health(),
                'dependencies': self.check_dependencies_health(),
                'api_keys': self.check_api_keys_health()
            }
        }

        # Determine overall status (worst component status)
        statuses = [c['status'] for c in report['components'].values()]

        if 'critical' in statuses:
            report['overall_status'] = 'critical'
        elif 'degraded' in statuses or 'warning' in statuses:
            report['overall_status'] = 'degraded'

        return report

    def print_health_report(self):
        """Print formatted health report"""
        report = self.get_full_health_report()

        print("=" * 70)
        print("🏥 SYSTEM HEALTH REPORT")
        print("=" * 70)
        print(f"\nTimestamp: {report['timestamp']}")

        # Overall status
        status_icon = {
            'healthy': '✅',
            'degraded': '⚠️',
            'warning': '⚠️',
            'critical': '❌',
            'error': '❌',
            'stopped': '⏸️',
            'unknown': '❓'
        }

        overall_icon = status_icon.get(report['overall_status'], '❓')
        print(f"Overall Status: {overall_icon} {report['overall_status'].upper()}\n")

        # Component details
        print("📊 Component Status:\n")

        for component_name, data in report['components'].items():
            icon = status_icon.get(data['status'], '❓')
            print(f"   {icon} {component_name.replace('_', ' ').title()}: {data['status'].upper()}")

            # Show relevant details
            if component_name == 'video_generation':
                rate = data['last_24h']['success_rate']
                print(f"      Last 24h: {data['last_24h']['posted']}/{data['last_24h']['total']} posted ({rate}% success)")
                print(f"      Overall: {data['overall']['posted']}/{data['overall']['total']} posted ({data['overall']['success_rate']}% success)")

            elif component_name == 'authentication':
                if data['critical_issues'] > 0:
                    print(f"      ⚠️  {data['critical_issues']} CRITICAL authentication issues")
                print(f"      {data['authenticated']} authenticated, {data['not_authenticated']} not authenticated")

            elif component_name == 'disk_space':
                print(f"      {data['total_size_gb']:.1f} GB used ({data['total_files']:,} files)")
                if data['deletable_files'] > 0:
                    print(f"      💡 Can recover {data['deletable_gb']:.1f} GB by deleting {data['deletable_files']} old files")

            elif component_name == 'api_keys':
                if 'error' not in data:
                    print(f"      {data['configured']}/{data['total']} API keys configured")
                    print(f"      {data['groq_keys']} Groq keys available for failover")

            elif component_name == 'daemon':
                if data['running']:
                    print(f"      PID: {data['pid']}")

        print("\n" + "=" * 70)

        # Recommendations
        recommendations = []

        if report['components']['authentication']['status'] in ['degraded', 'critical']:
            recommendations.append("🔧 Re-authenticate channels in UI Settings tab")

        if report['components']['video_generation']['last_24h']['success_rate'] < 50:
            recommendations.append("🔧 Check daemon logs for recurring errors")

        if report['components']['disk_space']['deletable_gb'] > 1:
            recommendations.append("🧹 Run: python3 file_cleanup.py --execute")

        if not report['components']['daemon']['running']:
            recommendations.append("🚀 Start daemon: python3 youtube_daemon.py start")

        if recommendations:
            print("\n📋 RECOMMENDED ACTIONS:\n")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
            print()

        return report


# CLI
if __name__ == "__main__":
    monitor = SystemHealthMonitor()
    monitor.print_health_report()
