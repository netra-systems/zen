#!/usr/bin/env python3
"""
Debug script to test Docker bypass logic in unified_test_runner.py
This script specifically tests Issue #548 - Golden Path Phase 2 Docker Dependency Blocking
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import argparse
from tests.unified_test_runner import UnifiedTestRunner

def test_docker_bypass():
    """Test the _docker_required_for_tests logic and Docker bypass"""
    
    runner = UnifiedTestRunner()
    
    # Create test args that should NOT require Docker
    args = argparse.Namespace()
    args.category = ['unit']
    args.categories = ['unit'] 
    args.no_docker = True
    args.prefer_staging = True
    args.env = 'staging'
    args.pattern = ''
    args.real_services = False
    
    # Test the logic
    print("Testing _docker_required_for_tests() with --no-docker flag...")
    needs_docker = runner._docker_required_for_tests(args, running_e2e=False)
    print(f"Result: Docker required = {needs_docker}")
    
    # Test the Docker initialization bypass
    print("\nTesting Docker initialization bypass...")
    print(f"Initial docker_enabled state: {runner.docker_enabled}")
    
    try:
        runner._initialize_docker_environment(args, running_e2e=False)
        print(f"After initialization docker_enabled state: {runner.docker_enabled}")
        print(f"Docker manager state: {runner.docker_manager}")
        
        if not runner.docker_enabled and runner.docker_manager is None:
            print("✅ SUCCESS: Docker properly bypassed - docker_enabled=False and docker_manager=None")
            return True
        elif runner.docker_enabled:
            print(f"❌ FAILURE: docker_enabled should be False but is {runner.docker_enabled}")
            return False
        else:
            print(f"❌ FAILURE: docker_manager should be None but is {runner.docker_manager}")
            return False
            
    except Exception as e:
        print(f"❌ FAILURE: Exception during Docker initialization: {e}")
        return False

if __name__ == '__main__':
    print("🔍 Issue #548 Docker Bypass Debug Test")
    print("=" * 50)
    
    success = test_docker_bypass()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Docker bypass logic is working correctly")
        print("💡 Issue may be in another code path")
    else:
        print("❌ Docker bypass logic has a bug")
        print("🔧 Fix needed in _docker_required_for_tests()")
    
    sys.exit(0 if success else 1)