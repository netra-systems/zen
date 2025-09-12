#!/usr/bin/env python3
"""
Test script to verify Docker hot reload is working for development containers.
This ensures that code changes are immediately reflected without rebuilding containers.
"""

import json
import subprocess
import time
import tempfile
import os
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

def run_command(cmd, capture=True):
    """Run a command and return output."""
    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    else:
        return subprocess.run(cmd, shell=True).returncode

def test_frontend_hot_reload():
    """Test that frontend container picks up code changes via volume mounts."""
    print("\n SEARCH:  Testing Frontend Hot Reload...")
    
    # 1. Create a test marker file
    test_file = Path("frontend/auth/test_hot_reload_marker.ts")
    timestamp = int(time.time())
    test_content = f"""// TEST HOT RELOAD MARKER - {timestamp}
export const HOT_RELOAD_TEST = {timestamp};
export const HOT_RELOAD_WORKING = true;
"""
    
    try:
        # Write test marker
        print(f"  [U+270D][U+FE0F]  Writing test marker with timestamp {timestamp}")
        test_file.write_text(test_content)
        
        # Give Next.js time to detect the change
        time.sleep(3)
        
        # Check if the file exists in the container
        stdout, stderr, code = run_command(
            f'docker exec netra-dev-frontend cat /app/auth/test_hot_reload_marker.ts 2>/dev/null'
        )
        
        if code == 0 and str(timestamp) in stdout:
            print(f"   PASS:  Frontend hot reload WORKING - marker {timestamp} found in container")
            return True
        else:
            print(f"   FAIL:  Frontend hot reload FAILED - marker not found in container")
            print(f"     Expected timestamp: {timestamp}")
            print(f"     Container output: {stdout[:100]}...")
            return False
            
    finally:
        # Clean up test file
        if test_file.exists():
            test_file.unlink()
            print(f"  [U+1F9F9] Cleaned up test marker file")

def test_backend_hot_reload():
    """Test that backend container picks up code changes via volume mounts."""
    print("\n SEARCH:  Testing Backend Hot Reload...")
    
    # 1. Create a test marker file
    test_file = Path("netra_backend/app/test_hot_reload_marker.py")
    timestamp = int(time.time())
    test_content = f'''"""Test hot reload marker - {timestamp}"""
HOT_RELOAD_TEST = {timestamp}
HOT_RELOAD_WORKING = True
'''
    
    try:
        # Write test marker
        print(f"  [U+270D][U+FE0F]  Writing test marker with timestamp {timestamp}")
        test_file.write_text(test_content)
        
        # Give uvicorn time to detect the change
        time.sleep(2)
        
        # Check if the file exists in the container
        stdout, stderr, code = run_command(
            f'docker exec netra-dev-backend cat /app/netra_backend/app/test_hot_reload_marker.py 2>/dev/null'
        )
        
        if code == 0 and str(timestamp) in stdout:
            print(f"   PASS:  Backend hot reload WORKING - marker {timestamp} found in container")
            return True
        else:
            print(f"   FAIL:  Backend hot reload FAILED - marker not found in container")
            return False
            
    finally:
        # Clean up test file
        if test_file.exists():
            test_file.unlink()
            print(f"  [U+1F9F9] Cleaned up test marker file")

def test_auth_hot_reload():
    """Test that auth service container picks up code changes via volume mounts."""
    print("\n SEARCH:  Testing Auth Service Hot Reload...")
    
    # 1. Create a test marker file
    test_file = Path("auth_service/test_hot_reload_marker.py")
    timestamp = int(time.time())
    test_content = f'''"""Test hot reload marker - {timestamp}"""
HOT_RELOAD_TEST = {timestamp}
HOT_RELOAD_WORKING = True
'''
    
    try:
        # Write test marker
        print(f"  [U+270D][U+FE0F]  Writing test marker with timestamp {timestamp}")
        test_file.write_text(test_content)
        
        # Give uvicorn time to detect the change
        time.sleep(2)
        
        # Check if the file exists in the container
        stdout, stderr, code = run_command(
            f'docker exec netra-dev-auth cat /app/auth_service/test_hot_reload_marker.py 2>/dev/null'
        )
        
        if code == 0 and str(timestamp) in stdout:
            print(f"   PASS:  Auth service hot reload WORKING - marker {timestamp} found in container")
            return True
        else:
            print(f"   FAIL:  Auth service hot reload FAILED - marker not found in container")
            return False
            
    finally:
        # Clean up test file
        if test_file.exists():
            test_file.unlink()
            print(f"  [U+1F9F9] Cleaned up test marker file")

def check_container_mounts():
    """Check if containers have proper volume mounts configured."""
    print("\n[U+1F4C2] Checking Container Volume Mounts...")
    
    containers = {
        'netra-dev-frontend': ['./frontend/', '/app/'],
        'netra-dev-backend': ['./netra_backend/', '/app/netra_backend'],
        'netra-dev-auth': ['./auth_service/', '/app/auth_service']
    }
    
    all_good = True
    for container, expected_mount in containers.items():
        stdout, stderr, code = run_command(
            f'docker inspect {container} --format="{{{{json .Mounts}}}}" 2>/dev/null'
        )
        
        if code != 0:
            print(f"   WARNING: [U+FE0F]  Container {container} not running")
            all_good = False
            continue
            
        try:
            mounts = json.loads(stdout)
            has_mount = any(
                expected_mount[0] in mount.get('Source', '') and 
                expected_mount[1] in mount.get('Destination', '')
                for mount in mounts
            )
            
            if has_mount:
                print(f"   PASS:  {container}: Volume mounts configured")
            else:
                print(f"   FAIL:  {container}: Missing volume mounts")
                print(f"     Expected: {expected_mount[0]} -> {expected_mount[1]}")
                all_good = False
                
        except json.JSONDecodeError:
            print(f"   FAIL:  {container}: Failed to parse mount info")
            all_good = False
    
    return all_good

def main():
    """Run all hot reload tests."""
    print("=" * 60)
    print("Docker Hot Reload Test Suite")
    print("=" * 60)
    
    # Check if containers are running
    print("\n[U+1F433] Checking Docker Containers...")
    stdout, stderr, code = run_command('docker ps --filter "name=netra-dev" --format "{{.Names}}"')
    
    running_containers = stdout.strip().split('\n') if stdout else []
    if not running_containers or not any('netra-dev' in c for c in running_containers):
        print(" FAIL:  No dev containers running! Start them with:")
        print("   docker-compose -f docker-compose.dev.yml up -d")
        return 1
    
    print(f" PASS:  Found {len(running_containers)} dev containers running")
    
    # Run tests
    results = []
    
    # Check mounts first
    mounts_ok = check_container_mounts()
    results.append(("Volume Mounts", mounts_ok))
    
    # Test hot reload for each service
    if 'netra-dev-frontend' in running_containers:
        results.append(("Frontend Hot Reload", test_frontend_hot_reload()))
    
    if 'netra-dev-backend' in running_containers:
        results.append(("Backend Hot Reload", test_backend_hot_reload()))
    
    if 'netra-dev-auth' in running_containers:
        results.append(("Auth Hot Reload", test_auth_hot_reload()))
    
    # Summary
    print("\n" + "=" * 60)
    print(" CHART:  Test Summary:")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = " PASS:  PASS" if passed else " FAIL:  FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n CELEBRATION:  All hot reload tests passed!")
        return 0
    else:
        print("\n WARNING: [U+FE0F]  Some tests failed. Fix volume mounts in docker-compose.dev.yml")
        print("\n[U+1F4DD] Required volume mounts:")
        print("  Frontend: ./frontend/* -> /app/*")
        print("  Backend:  ./netra_backend -> /app/netra_backend")
        print("  Auth:     ./auth_service -> /app/auth_service")
        return 1

if __name__ == "__main__":
    sys.exit(main())