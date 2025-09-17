#!/usr/bin/env python3
'''
Quick validation script for Docker Stability Comprehensive Test Suite
'''

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the test module
try:
from tests.mission_critical.test_docker_stability_comprehensive import ( )
DockerStabilityMetrics,
check_docker_daemon_health,
create_stress_container,
safe_container_cleanup,
TestDockerForceProhibition,
TestDockerRateLimiting,
TestSafeContainerLifecycle,
    
from test_framework.docker_force_flag_guardian import ( )
DockerForceFlagGuardian,
DockerForceFlagViolation
    
from test_framework.docker_rate_limiter import get_docker_rate_limiter

print(" PASS:  All imports successful!")

    # Test basic functionality
print(" )
[U+1F512] Testing Force Flag Guardian...")
guardian = DockerForceFlagGuardian()

try:
guardian.validate_command("docker rm -f test")
print(" FAIL:  CRITICAL: Force flag not detected!")
sys.exit(1)
except DockerForceFlagViolation:
print(" PASS:  Force flag guardian working correctly")

print(" )
[U+23F1][U+FE0F] Testing Rate Limiter...")
rate_limiter = get_docker_rate_limiter()
health = rate_limiter.health_check()

if health:
print(" PASS:  Docker rate limiter is healthy")
else:
print(" FAIL:  Docker rate limiter unhealthy")
sys.exit(1)

print(" )
[U+1F433] Testing Docker Daemon...")
daemon_health = check_docker_daemon_health()

if daemon_health:
print(" PASS:  Docker daemon is healthy and responsive")
else:
print(" FAIL:  Docker daemon is not healthy")
sys.exit(1)

print(" )
CHART:  Testing Metrics Collection...")
metrics = DockerStabilityMetrics()
metrics.record_operation("test_op", 1.5, True)
metrics.record_force_flag_violation()
metrics.record_rate_limit()

report = metrics.generate_report()
print("formatted_string")
print("formatted_string")
print("formatted_string")

print(" )
" + "=" * 60)
print(" PASS:  DOCKER STABILITY TEST SUITE VALIDATION PASSED")
print("=" * 60)
print("The comprehensive test suite is ready for production use!")
print(" )
To run the full test suite:")
print("python -m pytest tests/mission_critical/test_docker_stability_comprehensive.py -v")
print("=" * 60)

except ImportError as e:
print("formatted_string")
sys.exit(1)
except Exception as e:
print("formatted_string")
sys.exit(1)
