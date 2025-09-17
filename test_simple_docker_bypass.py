#!/usr/bin/env python3
"""
Simple test to verify Docker bypass works for Issue #548
"""

import subprocess
import sys
import os

def test_docker_bypass_simple():
    """Test that unit tests can run with --no-docker flag without Docker errors"""
    
    print("🔍 Testing Docker bypass with simple unit test...")
    print("Command: python tests/unified_test_runner.py --category unit --no-docker --limit 1")
    
    try:
        # Run the command and capture output
        result = subprocess.run([
            sys.executable, 
            "tests/unified_test_runner.py",
            "--category", "unit",
            "--no-docker",
            "--limit", "1"
        ], 
        capture_output=True, 
        text=True, 
        timeout=60,
        cwd="/Users/anthony/Desktop/netra-apex"
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        # Check for Docker-related errors
        output = result.stdout + result.stderr
        docker_errors = [
            "Docker Desktop service is not running",
            "DOCKER SERVICES UNHEALTHY", 
            "Docker services not healthy",
            "docker: command not found",
            "Cannot connect to the Docker daemon"
        ]
        
        for error in docker_errors:
            if error in output:
                print(f"❌ FAILURE: Found Docker error: {error}")
                return False
        
        # Check for success indicators
        success_indicators = [
            "Docker not required for selected test categories",
            "Docker disabled for staging environment",
            "Skipping all Docker operations"
        ]
        
        found_bypass = any(indicator in output for indicator in success_indicators)
        
        if found_bypass:
            print("✅ SUCCESS: Docker bypass working - found bypass message")
            return True
        elif result.returncode == 0:
            print("✅ SUCCESS: Test completed without Docker errors")
            return True
        else:
            print(f"❌ FAILURE: Test failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ FAILURE: Test timed out")
        return False
    except Exception as e:
        print(f"❌ FAILURE: Exception running test: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Issue #548 - Docker Bypass Validation Test")
    print("=" * 60)
    
    success = test_docker_bypass_simple()
    
    print("=" * 60)
    if success:
        print("✅ Docker bypass is working correctly!")
        print("💡 Issue #548 fix has been successfully implemented")
    else:
        print("❌ Docker bypass is still broken")
        print("🔧 Additional fixes may be needed")
    
    sys.exit(0 if success else 1)