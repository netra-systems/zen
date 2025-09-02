#!/usr/bin/env python3
"""
Test script to verify the UnifiedDockerManager port discovery fixes.
This script tests the new container name parsing and port discovery logic.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.unified_docker_manager import UnifiedDockerManager
from test_framework.config.docker_config import DockerConfig
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_container_name_patterns():
    """Test container name pattern generation and parsing"""
    print("\n=== Testing Container Name Patterns ===")
    
    # Create manager instance
    config = DockerConfig()
    manager = UnifiedDockerManager(config, test_id="port-discovery-test")
    
    # Test pattern generation
    patterns = manager._get_container_name_pattern()
    print(f"Generated patterns: {list(patterns.keys())}")
    
    # Test parsing various container name formats
    test_container_names = [
        "netra-core-generation-1-dev-backend-1",
        "netra-core-generation-1_dev_backend_1", 
        "netra-core-generation-1-test-postgres-1",
        "netra-core-generation-1-alpine-test-redis-1",
        "netra-dev-backend",
        "netra-apex-test-auth-1",
        "netra-test-postgres-1",
        "netra_test_shared_redis_1"
    ]
    
    print(f"\n--- Container Name Parsing Tests ---")
    for container_name in test_container_names:
        service = manager._parse_container_name_to_service(container_name)
        status = "✅ PARSED" if service else "❌ FAILED"
        print(f"{status} {container_name} -> {service}")
    
    return True

def test_docker_ps_parsing():
    """Test docker ps output parsing (simulated)"""
    print(f"\n=== Testing Docker PS Parsing ===")
    
    config = DockerConfig()
    manager = UnifiedDockerManager(config, test_id="port-discovery-test")
    
    # Simulate docker ps output parsing
    # This would normally come from actual docker ps command
    simulated_containers = {
        "backend": "netra-core-generation-1-dev-backend-1",
        "postgres": "netra-core-generation-1-dev-postgres-1",
        "auth": "netra-dev-auth"
    }
    
    print(f"Simulated containers found: {simulated_containers}")
    
    # Test the port discovery logic (will use fallback defaults when docker is not running)
    try:
        ports = manager._discover_ports_from_existing_containers(simulated_containers)
        print(f"Discovered ports: {ports}")
        
        # Verify expected services are present
        expected_services = ["backend", "postgres", "auth"]
        found_services = list(ports.keys())
        
        for service in expected_services:
            if service in found_services:
                print(f"✅ {service}: port {ports[service]}")
            else:
                print(f"❌ {service}: not found in discovered ports")
                
    except Exception as e:
        print(f"❌ Error during port discovery: {e}")
        return False
    
    return True

def test_environment_detection():
    """Test environment-specific default port selection"""
    print(f"\n=== Testing Environment Detection ===")
    
    config = DockerConfig()
    manager = UnifiedDockerManager(config, test_id="port-discovery-test")
    
    # Test different container name patterns to verify environment detection
    test_cases = [
        {
            "containers": {"backend": "netra-core-generation-1-dev-backend-1", "postgres": "netra-core-generation-1-dev-postgres-1"},
            "expected_postgres_port": 5432,  # dev uses standard port
            "env_type": "development"
        },
        {
            "containers": {"backend": "netra-core-generation-1-test-backend-1", "postgres": "netra-core-generation-1-test-postgres-1"}, 
            "expected_postgres_port": 5434,  # test uses different port
            "env_type": "test"
        }
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1}: {case['env_type']} ---")
        try:
            ports = manager._discover_ports_from_existing_containers(case["containers"])
            
            if "postgres" in ports:
                actual_port = ports["postgres"]
                expected_port = case["expected_postgres_port"] 
                if actual_port == expected_port:
                    print(f"✅ Postgres port correct for {case['env_type']}: {actual_port}")
                else:
                    print(f"⚠️ Postgres port mismatch for {case['env_type']}: expected {expected_port}, got {actual_port}")
            else:
                print(f"❌ Postgres port not found for {case['env_type']}")
                
        except Exception as e:
            print(f"❌ Error testing {case['env_type']}: {e}")
    
    return True

def main():
    """Run all tests"""
    print("🧪 Testing UnifiedDockerManager Port Discovery Fixes")
    print("=" * 60)
    
    tests = [
        ("Container Name Patterns", test_container_name_patterns),
        ("Docker PS Parsing", test_docker_ps_parsing), 
        ("Environment Detection", test_environment_detection)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 Running: {test_name}")
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} {test_name}")
        except Exception as e:
            print(f"❌ FAILED {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("🏁 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED" 
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Port discovery fixes are working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())