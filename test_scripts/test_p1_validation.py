#!/usr/bin/env python3
"""
Quick P1 Docker Stability Validation Test
Tests the core P1 remediation components are working
"""

import sys
import os

from shared.isolated_environment import IsolatedEnvironment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_p1_components():
    """Test that all P1 components can be imported and initialized"""
    print("=" * 60)
    print("P1 DOCKER STABILITY VALIDATION TEST")
    print("=" * 60)
    
    results = []
    
    # Test 1: Environment Lock
    try:
        from test_framework.environment_lock import EnvironmentLock
        lock = EnvironmentLock()
        print("[PASS] P1.2: Environment Lock module - WORKING")
        results.append(("Environment Lock", True))
    except Exception as e:
        print(f"[FAIL] P1.2: Environment Lock module - FAILED: {e}")
        results.append(("Environment Lock", False))
    
    # Test 2: Resource Monitor
    try:
        from test_framework.resource_monitor import DockerResourceMonitor
        monitor = DockerResourceMonitor()
        status = monitor.check_system_resources()
        print(f"[PASS] P1.3: Resource Monitor module - WORKING (Status: {status['threshold'].name})")
        results.append(("Resource Monitor", True))
    except Exception as e:
        print(f"[FAIL] P1.3: Resource Monitor module - FAILED: {e}")
        results.append(("Resource Monitor", False))
    
    # Test 3: Docker Compose Base Config
    try:
        import os
        base_path = "docker-compose.base.yml"
        if os.path.exists(base_path):
            print("[PASS] P1.1: Base configuration file - EXISTS")
            results.append(("Base Config", True))
        else:
            print("[FAIL] P1.1: Base configuration file - NOT FOUND")
            results.append(("Base Config", False))
    except Exception as e:
        print(f"[FAIL] P1.1: Base configuration check - FAILED: {e}")
        results.append(("Base Config", False))
    
    # Test 4: tmpfs Volume Check
    try:
        with open("docker-compose.test.yml", "r") as f:
            content = f.read()
            if "tmpfs" not in content:
                print("[PASS] tmpfs volumes removed - NO RAM EXHAUSTION")
                results.append(("tmpfs Removal", True))
            else:
                print("[FAIL] tmpfs volumes still present - RAM EXHAUSTION RISK")
                results.append(("tmpfs Removal", False))
    except Exception as e:
        print(f"[FAIL] tmpfs volume check - FAILED: {e}")
        results.append(("tmpfs Removal", False))
    
    # Test 5: UnifiedDockerManager
    try:
        from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
        manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
        print("[PASS] UnifiedDockerManager - INITIALIZED")
        results.append(("Docker Manager", True))
    except Exception as e:
        print(f"[FAIL] UnifiedDockerManager - FAILED: {e}")
        results.append(("Docker Manager", False))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for component, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{component:20} {status}")
    
    print("\n" + "=" * 60)
    success_rate = (passed / total) * 100
    print(f"Success Rate: {passed}/{total} ({success_rate:.1f}%)")
    
    if success_rate == 100:
        print("SUCCESS! ALL P1 REMEDIATION COMPONENTS VALIDATED!")
    elif success_rate >= 80:
        print("WARNING: Most P1 components working, some issues remain")
    else:
        print("ERROR: Critical P1 components failing, immediate attention needed")
    
    print("=" * 60)
    
    return success_rate == 100

if __name__ == "__main__":
    success = test_p1_components()
    sys.exit(0 if success else 1)