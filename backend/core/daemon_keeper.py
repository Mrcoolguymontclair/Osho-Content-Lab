#!/usr/bin/env python3
"""
DAEMON KEEPER - BULLETPROOF WRAPPER
Ensures daemon NEVER stops running.

Features:
- Pre-flight validation
- Auto-restart on crash
- Exponential backoff on repeated failures
- Monitors daemon health
- NEVER gives up
"""

import subprocess
import time
import os
import sys
import signal
from datetime import datetime

DAEMON_SCRIPT = "youtube_daemon.py"
PID_FILE = "daemon.pid"
LOG_FILE = "daemon_stdout.log"
KEEPER_PID_FILE = "daemon_keeper.pid"

# Global flag
keeper_running = True

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global keeper_running
    print(f"\n[WARNING] Received signal {signum}, stopping keeper...")
    keeper_running = False

def is_daemon_running():
    """Check if daemon is actually running"""
    if not os.path.exists(PID_FILE):
        return False

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())

        # Check if process exists
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False

def validate_dependencies():
    """Run pre-flight validation"""
    print(" Validating dependencies...")
    result = subprocess.run([sys.executable, "daemon_startup_validator.py"], capture_output=True)
    return result.returncode == 0

def start_daemon():
    """Start the daemon process"""
    print(f"[LAUNCH] Starting daemon at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Clear old PID file
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

    # Start daemon
    with open(LOG_FILE, 'a') as log:
        log.write(f"\n{'='*70}\n")
        log.write(f"DAEMON STARTED BY KEEPER: {datetime.now()}\n")
        log.write(f"{'='*70}\n")

        process = subprocess.Popen(
            [sys.executable, DAEMON_SCRIPT],
            stdout=log,
            stderr=log,
            cwd=os.getcwd()
        )

    # Wait for daemon to create PID file
    for i in range(10):
        time.sleep(1)
        if is_daemon_running():
            print(f"[OK] Daemon started successfully")
            return True

    print(f"[ERROR] Daemon failed to start")
    return False

def main():
    """Main keeper loop"""
    global keeper_running

    # Write keeper PID
    with open(KEEPER_PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 70)
    print("DAEMON KEEPER - BULLETPROOF MODE")
    print("=" * 70)
    print(f"Keeper PID: {os.getpid()}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Features:")
    print("  [OK] Auto-restart on crash")
    print("  [OK] Pre-flight validation")
    print("  [OK] Health monitoring")
    print("  [OK] NEVER gives up")
    print()

    consecutive_failures = 0
    max_failures_before_backoff = 3

    while keeper_running:
        try:
            # Check if daemon is running
            if not is_daemon_running():
                print(f"\n[WARNING] Daemon not running! (failures: {consecutive_failures})")

                # Validate dependencies before restart
                if not validate_dependencies():
                    print("[ERROR] Validation failed - waiting 60s before retry")
                    consecutive_failures += 1
                    time.sleep(60)
                    continue

                # Calculate backoff time
                if consecutive_failures >= max_failures_before_backoff:
                    backoff = min(60 * (2 ** (consecutive_failures - max_failures_before_backoff)), 600)  # Max 10 minutes
                    print(f"[WAIT] Multiple failures detected, waiting {backoff}s before restart...")
                    time.sleep(backoff)

                # Try to start daemon
                if start_daemon():
                    consecutive_failures = 0
                    print("[OK] Daemon recovered successfully")
                else:
                    consecutive_failures += 1
                    print(f"[ERROR] Restart attempt failed (total failures: {consecutive_failures})")
                    time.sleep(10)

            else:
                # Daemon is running - reset failure counter
                if consecutive_failures > 0:
                    consecutive_failures = 0
                    print("[OK] Daemon stable again")

            # Check every 10 seconds
            time.sleep(10)

        except KeyboardInterrupt:
            print("\n[WARNING] Keeper interrupted by user")
            keeper_running = False
            break
        except Exception as e:
            print(f"[ERROR] Keeper error: {e}")
            time.sleep(10)

    print("\n[STOP] Keeper stopped")

    # Clean up
    if os.path.exists(KEEPER_PID_FILE):
        os.remove(KEEPER_PID_FILE)

if __name__ == "__main__":
    main()
