#!/usr/bin/env python
"""
Dev Mode Test Runner Helper Script

This script ensures the dev launcher is running and executes tests in dev mode.
It provides clear feedback about what mode is being used and validates the development environment.

Business Value: Enables seamless development workflow by automatically ensuring
dev services are running before executing tests against the local environment.

Usage:
    python scripts/run_tests_dev_mode.py [test_runner_args...]
    python scripts/run_tests_dev_mode.py --level integration
    python scripts/run_tests_dev_mode.py --level unit --fast-fail
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_dev_launcher_running() -> bool:
    """Check if dev launcher is running by looking for the backend process."""
    try:
        if sys.platform == "win32":
            # On Windows, check for uvicorn processes
            result = subprocess.run(
                ["powershell", "-Command", "Get-Process | Where-Object {$_.ProcessName -eq 'python'} | Where-Object {$_.CommandLine -like '*uvicorn*'}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "uvicorn" in result.stdout
        else:
            # On Unix-like systems
            result = subprocess.run(
                ["pgrep", "-f", "uvicorn.*app.main:app"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def check_backend_health() -> bool:
    """Check if backend is responding to health checks."""
    try:
        import requests
        response = requests.get("http://localhost:8001/health", timeout=2)
        return response.status_code == 200
    except ImportError:
        # If requests is not available, just check if port is open
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 8001))
        sock.close()
        return result == 0
    except Exception:
        return False


def start_dev_launcher() -> bool:
    """Start the dev launcher if not running."""
    print("[DEV MODE] Starting development services...")
    
    dev_launcher_path = PROJECT_ROOT / "scripts" / "dev_launcher.py"
    if not dev_launcher_path.exists():
        print(f"[ERROR] Dev launcher not found at {dev_launcher_path}")
        return False
    
    try:
        # Start dev launcher in background
        if sys.platform == "win32":
            subprocess.Popen([
                sys.executable, str(dev_launcher_path)
            ], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen([
                sys.executable, str(dev_launcher_path)
            ])
        
        # Wait for services to start
        print("[DEV MODE] Waiting for services to start...")
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            if check_backend_health():
                print("[DEV MODE] Backend is ready!")
                return True
            if i % 5 == 0:
                print(f"[DEV MODE] Still waiting for backend... ({i+1}/30)")
        
        print("[WARNING] Backend may not be fully ready, but proceeding with tests")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to start dev launcher: {e}")
        return False


def validate_dev_environment() -> bool:
    """Validate that the development environment is properly configured."""
    errors = []
    warnings = []
    
    # Check if required environment files exist
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        warnings.append(".env file not found - using default configuration")
    
    # Check if key directories exist
    required_dirs = ["app", "test_framework", "tests"]
    for dir_name in required_dirs:
        dir_path = PROJECT_ROOT / dir_name
        if not dir_path.exists():
            errors.append(f"Required directory not found: {dir_name}")
    
    # Print validation results
    if warnings:
        for warning in warnings:
            print(f"[WARNING] {warning}")
    
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return False
    
    return True


def run_tests_in_dev_mode(test_args: List[str]) -> int:
    """Run tests with dev mode configuration."""
    test_runner_path = PROJECT_ROOT / "test_runner.py"
    if not test_runner_path.exists():
        print(f"[ERROR] Test runner not found at {test_runner_path}")
        return 1
    
    # Build command with dev mode flag
    cmd = [sys.executable, str(test_runner_path), "--env", "dev"] + test_args
    
    print("[DEV MODE] Running tests with command:")
    print(f"  {' '.join(cmd)}")
    print("=" * 80)
    
    try:
        # Run tests and return exit code
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        return result.returncode
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Test run cancelled by user")
        return 130
    except Exception as e:
        print(f"[ERROR] Failed to run tests: {e}")
        return 1


def print_dev_mode_info():
    """Print information about dev mode testing."""
    print("=" * 80)
    print("NETRA AI PLATFORM - DEV MODE TEST RUNNER")
    print("=" * 80)
    print("Mode: Development Environment Testing")
    print("Backend: http://localhost:8001")
    print("Environment: development")
    print("Database: Local PostgreSQL")
    print("Services: Local Redis, ClickHouse")
    print("=" * 80)


def main():
    """Main entry point for dev mode test runner."""
    parser = argparse.ArgumentParser(
        description="Run tests in development mode",
        add_help=False  # We'll pass through to test runner
    )
    
    # Parse known args to extract our flags, pass rest to test runner
    args, unknown_args = parser.parse_known_args()
    
    # Print dev mode info
    print_dev_mode_info()
    
    # Validate environment
    if not validate_dev_environment():
        print("[ERROR] Development environment validation failed")
        return 1
    
    # Check if dev launcher is running
    if check_backend_health():
        print("[DEV MODE] Backend is already running and healthy")
    elif check_dev_launcher_running():
        print("[DEV MODE] Dev launcher is running, checking backend health...")
        # Wait a bit for backend to be ready
        for i in range(10):
            time.sleep(1)
            if check_backend_health():
                print("[DEV MODE] Backend is ready!")
                break
        else:
            print("[WARNING] Backend may not be fully ready")
    else:
        print("[DEV MODE] Dev launcher not running, starting it...")
        if not start_dev_launcher():
            print("[ERROR] Failed to start dev launcher")
            return 1
    
    # Run tests in dev mode
    exit_code = run_tests_in_dev_mode(unknown_args)
    
    if exit_code == 0:
        print("\n[SUCCESS] Dev mode tests completed successfully!")
    else:
        print(f"\n[FAILED] Tests failed with exit code {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())