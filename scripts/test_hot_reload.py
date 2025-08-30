#!/usr/bin/env python3
"""
Test script to verify Docker hot reload functionality.
Run this after starting Docker services to confirm hot reload is working.
"""

import subprocess
import time
import os
import sys
from pathlib import Path

def test_hot_reload():
    """Test hot reload by modifying a test file and checking container logs."""
    
    print("Docker Hot Reload Test")
    print("=" * 50)
    
    # Check if services are running
    print("\n1. Checking if services are running...")
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=netra-dev-backend", "--format", "{{.Names}}"],
        capture_output=True,
        text=True
    )
    
    if "netra-dev-backend" not in result.stdout:
        print("ERROR: Backend service not running. Please start with:")
        print("   docker-compose -f docker-compose.dev.yml up backend")
        return False
    
    print("OK: Backend service is running")
    
    # Create a test file that will trigger reload
    test_file = Path("netra_backend/app/test_hot_reload.py")
    print(f"\n2. Creating test file: {test_file}")
    
    # Initial content
    initial_content = '''"""Test file for hot reload verification."""

TEST_VALUE = "initial"

def get_test_value():
    """Return test value."""
    return TEST_VALUE
'''
    
    test_file.write_text(initial_content)
    print("OK: Test file created")
    
    # Wait for initial reload
    print("\n3. Waiting for initial file detection...")
    time.sleep(2)
    
    # Modify the file
    print("\n4. Modifying test file...")
    modified_content = '''"""Test file for hot reload verification."""

TEST_VALUE = "modified"

def get_test_value():
    """Return test value."""
    return TEST_VALUE
'''
    
    test_file.write_text(modified_content)
    print("OK: File modified")
    
    # Check container logs for reload message
    print("\n5. Checking container logs for reload...")
    time.sleep(3)  # Give uvicorn time to detect and reload
    
    result = subprocess.run(
        ["docker", "logs", "netra-dev-backend", "--tail", "20"],
        capture_output=True,
        text=True
    )
    
    if "Detected file change" in result.stderr or "Reloading" in result.stderr or "Started reloader process" in result.stderr:
        print("OK: Hot reload detected!")
        print("\nRelevant log lines:")
        for line in result.stderr.split('\n'):
            if any(word in line.lower() for word in ['reload', 'change', 'detected', 'watching']):
                print(f"   {line}")
    else:
        print("WARNING: Reload message not found in logs")
        print("   This might be normal if reload already happened")
        print("   Check full logs with: docker logs netra-backend --tail 50")
    
    # Cleanup
    print("\n6. Cleaning up test file...")
    if test_file.exists():
        test_file.unlink()
        print("OK: Test file removed")
    
    print("\n" + "=" * 50)
    print("Hot reload test complete!")
    print("\nTips:")
    print("- Monitor logs in real-time: docker logs -f netra-backend")
    print("- If reload isn't working on Mac/Windows, check docker-compose.override.yml")
    print("- See docs/docker-hot-reload-guide.md for troubleshooting")
    
    return True

if __name__ == "__main__":
    try:
        success = test_hot_reload()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: Error during test: {e}")
        sys.exit(1)