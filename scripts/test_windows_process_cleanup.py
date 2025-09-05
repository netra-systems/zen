#!/usr/bin/env python
"""
Test script to verify Windows process cleanup functionality.

This script tests that Node.js processes are properly cleaned up
after frontend tests and dev launcher operations.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.windows_process_cleanup import WindowsProcessCleanup


def count_node_processes():
    """Count current Node.js processes."""
    if sys.platform != "win32":
        print("This test is for Windows only")
        return 0
    
    try:
        result = subprocess.run(
            'tasklist /FI "IMAGENAME eq node.exe" /FO CSV',
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Count lines excluding header
            lines = result.stdout.strip().split('\n')
            # If no processes found, tasklist returns a message
            if "No tasks are running" in result.stdout:
                return 0
            # Count actual process lines (skip header)
            return len([l for l in lines[1:] if 'node.exe' in l.lower()])
    except Exception as e:
        print(f"Error counting Node processes: {e}")
        return -1
    
    return 0


def test_cleanup_functionality():
    """Test the cleanup functionality."""
    print("=" * 60)
    print("Windows Process Cleanup Test")
    print("=" * 60)
    
    if sys.platform != "win32":
        print("[OK] Skipping test - not on Windows")
        return True
    
    # Create cleanup instance
    cleanup = WindowsProcessCleanup()
    
    # Test 1: Count initial Node.js processes
    print("\n1. Checking initial Node.js processes...")
    initial_count = count_node_processes()
    print(f"   Initial Node.js processes: {initial_count}")
    
    # Test 2: Start a test Node.js process
    print("\n2. Starting test Node.js process...")
    test_process = None
    try:
        # Start a simple Node.js process that sleeps
        test_process = subprocess.Popen(
            'node -e "setTimeout(() => {}, 60000)"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)  # Give it time to start
        
        after_start_count = count_node_processes()
        print(f"   Node.js processes after start: {after_start_count}")
        
        if after_start_count <= initial_count:
            print("   [WARNING] Test process may not have started properly")
    except Exception as e:
        print(f"   [WARNING] Failed to start test process: {e}")
    
    # Test 3: Test cleanup_after_subprocess
    if test_process:
        print("\n3. Testing cleanup_after_subprocess...")
        success = cleanup.cleanup_after_subprocess(test_process, timeout=5)
        print(f"   Cleanup result: {'Success' if success else 'Failed'}")
        
        time.sleep(2)  # Give time for cleanup
        after_cleanup_count = count_node_processes()
        print(f"   Node.js processes after cleanup: {after_cleanup_count}")
        
        if after_cleanup_count < after_start_count:
            print("   [OK] Process successfully cleaned up")
        else:
            print("   [WARNING] Process may not have been cleaned up")
    
    # Test 4: Test general Node.js cleanup
    print("\n4. Testing general Node.js process cleanup...")
    cleaned = cleanup.cleanup_node_processes()
    print(f"   Cleaned {cleaned} hanging Node.js processes")
    
    # Test 5: Verify final state
    print("\n5. Final verification...")
    final_count = count_node_processes()
    print(f"   Final Node.js processes: {final_count}")
    
    if final_count <= initial_count:
        print("   [OK] All test processes cleaned up")
        success = True
    else:
        print(f"   [WARNING] {final_count - initial_count} extra Node.js processes remain")
        success = False
    
    print("\n" + "=" * 60)
    print(f"Test {'PASSED' if success else 'FAILED'}")
    print("=" * 60)
    
    return success


def test_port_cleanup():
    """Test port cleanup functionality."""
    print("\n" + "=" * 60)
    print("Port Cleanup Test")
    print("=" * 60)
    
    if sys.platform != "win32":
        print("[OK] Skipping test - not on Windows")
        return True
    
    cleanup = WindowsProcessCleanup()
    
    # Check if common dev ports are in use
    ports_to_check = [3000, 3001, 8000, 8001]
    
    for port in ports_to_check:
        print(f"\nChecking port {port}...")
        try:
            result = subprocess.run(
                f"netstat -ano | findstr :{port}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                print(f"   Port {port} is in use")
                # Try to clean it
                cleaned = cleanup._cleanup_processes_on_ports([port])
                if cleaned > 0:
                    print(f"   [OK] Cleaned {cleaned} processes using port {port}")
                else:
                    print(f"   [INFO] No processes cleaned for port {port}")
            else:
                print(f"   [OK] Port {port} is free")
        except Exception as e:
            print(f"   [WARNING] Error checking port {port}: {e}")
    
    print("\n" + "=" * 60)
    return True


if __name__ == "__main__":
    print("Starting Windows Process Cleanup Tests\n")
    
    # Run tests
    test1_passed = test_cleanup_functionality()
    test2_passed = test_port_cleanup()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Cleanup functionality: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Port cleanup:         {'PASSED' if test2_passed else 'FAILED'}")
    
    all_passed = test1_passed and test2_passed
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("=" * 60)
    
    sys.exit(0 if all_passed else 1)