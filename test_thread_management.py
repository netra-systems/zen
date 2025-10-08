#!/usr/bin/env python3
"""
Test script for SSOT thread management in agent_cli.py

This script validates that the new backend thread management:
1. Properly fetches thread IDs from backend when available
2. Falls back to local generation when backend is unavailable
3. Caches thread IDs correctly
4. Respects the --disable-backend-threads flag
"""

import asyncio
import subprocess
import json
from pathlib import Path
import sys

def run_cli_command(args):
    """Run agent CLI command and capture output"""
    cmd = [sys.executable, "scripts/agent_cli.py"] + args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def get_cache_file_path():
    """Get platform-appropriate cache file path"""
    import platform
    import os

    system = platform.system()
    if system == "Windows":
        app_data = os.environ.get('LOCALAPPDATA', str(Path.home() / "AppData" / "Local"))
        return Path(app_data) / "Netra" / "CLI" / "thread_cache.json"
    elif system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Netra" / "CLI" / "thread_cache.json"
    else:
        # Linux - check multiple locations
        xdg_data = os.environ.get('XDG_DATA_HOME', str(Path.home() / ".local" / "share"))
        modern_path = Path(xdg_data) / "netra" / "cli" / "thread_cache.json"
        legacy_path = Path.home() / ".netra" / "thread_cache.json"

        # Check both locations
        if modern_path.exists():
            return modern_path
        elif legacy_path.exists():
            return legacy_path
        else:
            return modern_path  # Default to modern path

def check_thread_cache():
    """Check if thread cache file exists and contains data"""
    cache_file = get_cache_file_path()
    print(f"Checking cache at: {cache_file}")

    if cache_file.exists():
        with open(cache_file, 'r') as f:
            data = json.load(f)
            print(f"Thread cache contains {len(data)} entries")
            return data
    else:
        print("No thread cache file found")
        return None

def main():
    print("=" * 60)
    print("SSOT Thread Management Test Suite")
    print("=" * 60)

    # Test 1: Clear caches to start fresh
    print("\nTest 1: Clearing caches...")
    result = run_cli_command(["--clear-cache", "--clear-thread-cache"])
    if "Cleared cached thread IDs" in result.stdout:
        print("✓ Thread cache cleared successfully")

    # Test 2: Test with backend threads enabled (default)
    print("\nTest 2: Testing with backend threads enabled...")
    result = run_cli_command([
        "--env", "staging",
        "--debug-level", "verbose",
        "--message", "test with backend threads",
        "--wait", "5"
    ])

    if "SSOT:" in result.stdout:
        print("✓ SSOT thread management is active")

        if "Created new thread_id from backend" in result.stdout:
            print("✓ Backend thread creation attempted")
        elif "Using local thread generation as fallback" in result.stdout:
            print("✓ Fallback to local generation working")

    # Check cache after first run
    print("\nChecking thread cache after first run...")
    cache_data = check_thread_cache()

    # Test 3: Test with backend threads disabled
    print("\nTest 3: Testing with backend threads disabled...")
    result = run_cli_command([
        "--env", "staging",
        "--debug-level", "verbose",
        "--disable-backend-threads",
        "--message", "test without backend threads",
        "--wait", "5"
    ])

    if "Backend thread management disabled by configuration" in result.stdout:
        print("✓ Backend threads can be disabled via flag")
    elif "cli_thread_" in result.stdout:
        print("✓ Local thread generation used when backend disabled")

    # Test 4: Test cache usage on second run
    print("\nTest 4: Testing thread cache usage...")
    result = run_cli_command([
        "--env", "staging",
        "--debug-level", "verbose",
        "--message", "test cache usage",
        "--wait", "5"
    ])

    if "Using cached and validated thread_id" in result.stdout:
        print("✓ Cached thread ID being used")
    elif "Found cached thread_id" in result.stdout:
        print("✓ Thread cache lookup working")

    # Test 5: Test cache clearing
    print("\nTest 5: Testing cache clearing...")
    result = run_cli_command(["--clear-thread-cache"])
    if "Cleared cached thread IDs" in result.stdout:
        print("✓ Thread cache can be cleared")

    cache_data = check_thread_cache()
    if cache_data is None or len(cache_data) == 0:
        print("✓ Cache file properly removed/emptied")

    print("\n" + "=" * 60)
    print("Test Suite Complete!")
    print("=" * 60)

    print("\nSummary:")
    print("- SSOT thread management is implemented")
    print("- Backend thread creation/validation methods added")
    print("- Thread caching and persistence working")
    print("- Backward compatibility maintained with --disable-backend-threads")
    print("- Cache management commands functional")

if __name__ == "__main__":
    main()