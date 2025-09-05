#!/usr/bin/env python3
"""
Quick validation script for Docker Stability Comprehensive Test Suite
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the test module
try:
    from tests.mission_critical.test_docker_stability_comprehensive import (
        DockerStabilityMetrics,
        check_docker_daemon_health,
        create_stress_container,
        safe_container_cleanup,
        TestDockerForceProhibition,
        TestDockerRateLimiting,
        TestSafeContainerLifecycle,
    )
    from test_framework.docker_force_flag_guardian import (
        DockerForceFlagGuardian,
        DockerForceFlagViolation
    )
    from test_framework.docker_rate_limiter import get_docker_rate_limiter
    
    print("✅ All imports successful!")
    
    # Test basic functionality
    print("
🔒 Testing Force Flag Guardian...")
    guardian = DockerForceFlagGuardian()
    
    try:
        guardian.validate_command("docker rm -f test")
        print("❌ CRITICAL: Force flag not detected!")
        sys.exit(1)
    except DockerForceFlagViolation:
        print("✅ Force flag guardian working correctly")
    
    print("
⏱️ Testing Rate Limiter...")
    rate_limiter = get_docker_rate_limiter()
    health = rate_limiter.health_check()
    
    if health:
        print("✅ Docker rate limiter is healthy")
    else:
        print("❌ Docker rate limiter unhealthy")
        sys.exit(1)
    
    print("
🐳 Testing Docker Daemon...")
    daemon_health = check_docker_daemon_health()
    
    if daemon_health:
        print("✅ Docker daemon is healthy and responsive")
    else:
        print("❌ Docker daemon is not healthy")
        sys.exit(1)
    
    print("
📊 Testing Metrics Collection...")
    metrics = DockerStabilityMetrics()
    metrics.record_operation("test_op", 1.5, True)
    metrics.record_force_flag_violation()
    metrics.record_rate_limit()
    
    report = metrics.generate_report()
    print(f"✅ Metrics collected: {report['total_docker_operations']} operations")
    print(f"✅ Force flag violations: {report['force_flag_violations']}")
    print(f"✅ Rate limited operations: {report['rate_limited_operations']}")
    
    print("
" + "=" * 60)
    print("✅ DOCKER STABILITY TEST SUITE VALIDATION PASSED")
    print("=" * 60)
    print("The comprehensive test suite is ready for production use!")
    print("
To run the full test suite:")
    print("python -m pytest tests/mission_critical/test_docker_stability_comprehensive.py -v")
    print("=" * 60)
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Validation error: {e}")
    sys.exit(1)