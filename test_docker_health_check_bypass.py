#!/usr/bin/env python3
"""
Test to verify that Docker health checks are properly bypassed for Issue #548
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import argparse
from unittest.mock import patch, MagicMock

# Import after path setup
from tests.unified_test_runner import UnifiedTestRunner

def test_docker_health_check_bypass():
    """Test that Docker health checks are bypassed when Docker not required"""
    
    runner = UnifiedTestRunner()
    
    # Create test args that should NOT require Docker
    args = argparse.Namespace()
    args.category = ['unit']
    args.categories = ['unit'] 
    args.no_docker = True
    args.prefer_staging = False  # Test non-staging path
    args.env = 'test'
    args.pattern = ''
    args.real_services = False
    
    print("🔍 Testing Docker health check bypass...")
    print(f"Initial docker_enabled: {runner.docker_enabled}")
    
    # Mock Docker operations to track if they're called inappropriately
    docker_operations_called = []
    
    def mock_docker_operation(name):
        def mock_func(*args, **kwargs):
            docker_operations_called.append(name)
            print(f"⚠️  Docker operation called inappropriately: {name}")
            return True  # Return success to avoid cascading failures
        return mock_func
    
    # Test the bypass logic
    with patch('tests.unified_test_runner.CENTRALIZED_DOCKER_AVAILABLE', True):
        with patch('tests.unified_test_runner.UnifiedDockerManager') as mock_docker_class:
            mock_docker_instance = MagicMock()
            mock_docker_instance.wait_for_services = mock_docker_operation('wait_for_services')
            mock_docker_instance.get_service_status = mock_docker_operation('get_service_status')
            mock_docker_instance.restart_service = mock_docker_operation('restart_service')
            mock_docker_class.return_value = mock_docker_instance
            
            try:
                # This should bypass Docker completely
                runner._initialize_docker_environment(args, running_e2e=False)
                
                print(f"After initialization:")
                print(f"  docker_enabled: {runner.docker_enabled}")
                print(f"  docker_manager: {runner.docker_manager}")
                print(f"  Docker operations called: {docker_operations_called}")
                
                # Verify no Docker operations were called
                if not docker_operations_called and not runner.docker_enabled:
                    print("✅ SUCCESS: Docker health checks properly bypassed")
                    return True
                elif docker_operations_called:
                    print(f"❌ FAILURE: Docker operations were called: {docker_operations_called}")
                    return False
                elif runner.docker_enabled:
                    print(f"❌ FAILURE: docker_enabled should be False but is {runner.docker_enabled}")
                    return False
                else:
                    print("✅ SUCCESS: Docker bypass working correctly")
                    return True
                    
            except Exception as e:
                print(f"❌ FAILURE: Exception during test: {e}")
                print(f"Docker operations called before exception: {docker_operations_called}")
                return False

if __name__ == "__main__":
    print("🔍 Issue #548 - Docker Health Check Bypass Test")
    print("=" * 60)
    
    success = test_docker_health_check_bypass()
    
    print("=" * 60)
    if success:
        print("✅ Docker health check bypass is working!")
    else:
        print("❌ Docker health check bypass is broken")
    
    sys.exit(0 if success else 1)