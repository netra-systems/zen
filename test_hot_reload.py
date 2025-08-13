#!/usr/bin/env python3
"""
Test script for hot reload functionality.

This script:
1. Starts the dev launcher with hot reload enabled
2. Waits for services to start
3. Makes a change to a Python file
4. Verifies that the service restarts
"""

import os
import sys
import time
import subprocess
import tempfile
from pathlib import Path

def test_hot_reload():
    """Test the hot reload functionality."""
    print("=" * 60)
    print("🧪 Testing Hot Reload Functionality")
    print("=" * 60)
    
    # Create a test file in the app directory
    test_file = Path("app/test_hot_reload_marker.py")
    
    try:
        # Write initial content
        print("📝 Creating test file...")
        test_file.write_text('# Test hot reload - version 1\ntest_version = 1\n')
        
        # Start dev launcher with hot reload in a subprocess
        print("🚀 Starting dev launcher with hot reload...")
        process = subprocess.Popen(
            [sys.executable, "dev_launcher.py", "--dynamic", "--load-secrets", "--no-browser"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Wait for services to start
        print("⏳ Waiting for services to start (30 seconds)...")
        start_time = time.time()
        backend_started = False
        frontend_started = False
        
        while time.time() - start_time < 30:
            if process.poll() is not None:
                print("❌ Dev launcher exited unexpectedly")
                return False
                
            line = process.stdout.readline()
            if line:
                print(f"  {line.strip()}")
                if "Backend started on port" in line:
                    backend_started = True
                if "Frontend started on port" in line:
                    frontend_started = True
                    
            if backend_started and frontend_started:
                break
                
        if not (backend_started and frontend_started):
            print("⚠️ Services did not start in time")
            
        # Now modify the test file to trigger hot reload
        print("\n📝 Modifying test file to trigger hot reload...")
        time.sleep(2)
        test_file.write_text('# Test hot reload - version 2\ntest_version = 2\n')
        
        # Watch for reload message
        print("👀 Watching for hot reload (15 seconds)...")
        reload_time = time.time()
        reload_detected = False
        
        while time.time() - reload_time < 15:
            if process.poll() is not None:
                print("❌ Dev launcher exited unexpectedly")
                break
                
            line = process.stdout.readline()
            if line:
                print(f"  {line.strip()}")
                if "Reloading Backend" in line or "restarting for hot reload" in line:
                    reload_detected = True
                    print("✅ Hot reload detected!")
                    break
                    
        if reload_detected:
            print("\n✨ Hot reload test PASSED!")
            return True
        else:
            print("\n❌ Hot reload test FAILED - no reload detected")
            return False
            
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        
        # Terminate the dev launcher
        if 'process' in locals() and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
            
        # Remove test file
        if test_file.exists():
            test_file.unlink()
            print("  Removed test file")
            
        print("  Done!")


if __name__ == "__main__":
    success = test_hot_reload()
    sys.exit(0 if success else 1)