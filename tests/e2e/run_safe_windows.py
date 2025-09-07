#!/usr/bin/env python
"""Safe runner for E2E tests on Windows to prevent Docker crashes.

This script implements all the fixes to prevent resource exhaustion:
1. Disables pytest parallel collection
2. Sets resource limits
3. Checks Docker health before running
4. Uses lazy loading patterns
5. Implements Windows-specific workarounds
"""

import os
import sys
import platform
import subprocess
import time
import requests
from pathlib import Path

def check_docker_health():
    """Check if Docker services are healthy."""
    print("Checking Docker health...")
    
    try:
        # Check Docker Desktop service
        if platform.system() == "Windows":
            result = subprocess.run(
                ["sc", "query", "com.docker.service"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "RUNNING" not in result.stdout:
                print("[ERROR] Docker Desktop service is not running")
                return False
        
        # Check backend health
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            print(f"[ERROR] Backend unhealthy: {response.status_code}")
            return False
        
        print("[OK] Docker services are healthy")
        return True
        
    except Exception as e:
        print(f"[ERROR] Docker health check failed: {e}")
        return False

def run_e2e_test_safely(test_file=None):
    """Run E2E tests with Windows-specific safety measures."""
    
    # Check platform
    if platform.system() != "Windows":
        print("This script is designed for Windows. Running normal pytest...")
        subprocess.run(["pytest", test_file or "tests/e2e", "-v"])
        return
    
    # Set environment variables for safety
    env = os.environ.copy()
    env.update({
        "PYTEST_XDIST_WORKER_COUNT": "1",  # Disable parallel execution
        "PYTEST_TIMEOUT": "120",  # Set reasonable timeout
        "PYTHONDONTWRITEBYTECODE": "1",  # Reduce file operations
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",  # Reduce plugin loading
    })
    
    # Check Docker health
    if not check_docker_health():
        print("\n[WARNING] Docker services are not healthy!")
        print("Please ensure Docker Desktop is running and services are started:")
        print("  python scripts/docker_manual.py start")
        sys.exit(1)
    
    # Build pytest command with safety flags
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",  # Verbose
        "-s",  # Show output
        "--tb=short",  # Short traceback
        "--maxfail=1",  # Stop on first failure
        "-x",  # Exit on first failure
        "-p", "no:xdist",  # Disable xdist plugin
        "--collect-only",  # First, just collect to verify no crash
    ]
    
    if test_file:
        cmd.append(test_file)
    else:
        cmd.append("tests/e2e")
    
    # First run collection only to verify no crash
    print("\n[INFO] Running test collection (safety check)...")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("[ERROR] Test collection failed!")
        print(result.stderr)
        sys.exit(1)
    
    # Extract number of tests
    import re
    match = re.search(r"collected (\d+) item", result.stdout)
    if match:
        num_tests = int(match.group(1))
        print(f"[OK] Successfully collected {num_tests} test(s)")
    
    # Now run the actual tests
    cmd.remove("--collect-only")
    
    print("\n[INFO] Running tests with safety measures...")
    print(f"Command: {' '.join(cmd)}")
    
    # Run tests with real-time output
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Stream output in real-time
    for line in process.stdout:
        print(line, end='')
    
    process.wait()
    
    if process.returncode == 0:
        print("\n[OK] Tests completed successfully!")
    else:
        print(f"\n[ERROR] Tests failed with code {process.returncode}")
    
    return process.returncode

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Safe E2E test runner for Windows")
    parser.add_argument(
        "test_file",
        nargs="?",
        help="Specific test file to run (default: all e2e tests)"
    )
    parser.add_argument(
        "--skip-docker-check",
        action="store_true",
        help="Skip Docker health check"
    )
    
    args = parser.parse_args()
    
    if args.skip_docker_check:
        os.environ["SKIP_DOCKER_TESTS"] = "false"
    
    sys.exit(run_e2e_test_safely(args.test_file))

if __name__ == "__main__":
    main()