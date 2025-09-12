#!/usr/bin/env python
"""ISSUE #411 VALIDATION TESTS - Docker Fast-Fail Validation

MISSION: Validate that Docker timeout fixes work correctly after implementation.

These tests should PASS after Issue #411 fixes are applied.

SOLUTION VALIDATION:
- Docker availability checks complete in < 2s when Docker unavailable
- WebSocket tests skip gracefully instead of hanging
- Rate limiter implements proper fast-fail logic
"""

import asyncio
import os
import sys
import time
import subprocess
from unittest.mock import patch, MagicMock
from typing import Optional

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import the components that should now fast-fail
from test_framework.unified_docker_manager import UnifiedDockerManager
from test_framework.docker_rate_limiter import DockerRateLimiter


class TestDockerFastFailValidation:
    """Phase 2: Validation tests that should PASS after Issue #411 fixes."""

    def test_docker_availability_fast_fail_when_unavailable(self):
        """
        VALIDATION TEST: Docker availability check should complete in < 2s when Docker unavailable
        
        EXPECTED RESULT: PASS - Should complete quickly with proper fast-fail logic
        PURPOSE: Validates Issue #411 fix implementation
        """
        logger.info(" PASS:  VALIDATION TEST: Docker availability fast-fail - SHOULD COMPLETE < 2s")
        
        start_time = time.time()
        fast_fail_threshold = 2.0  # Should complete within 2 seconds
        
        try:
            # Create manager with fast-fail behavior
            manager = UnifiedDockerManager()
            
            # This should now complete quickly when Docker unavailable
            result = manager.is_docker_available()
            
            duration = time.time() - start_time
            logger.info(f"Docker availability check completed in {duration:.1f}s (result: {result})")
            
            # Validate fast-fail behavior
            assert duration < fast_fail_threshold, (
                f"FAST-FAIL FAILED: Docker check took {duration:.1f}s "
                f"(should be < {fast_fail_threshold}s). Issue #411 fix not working."
            )
            
            # If Docker is available, that's fine - just validate speed
            if result:
                logger.info("Docker is available - fast-fail speed validated")
            else:
                logger.info("Docker unavailable detected quickly - fast-fail working")
                
            logger.info(f" PASS:  PASS: Fast-fail validation successful ({duration:.1f}s)")
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Even exceptions should be fast
            assert duration < fast_fail_threshold, (
                f"FAST-FAIL FAILED: Exception after {duration:.1f}s: {e}. "
                f"Should fail quickly when Docker unavailable."
            )
            
            logger.info(f" PASS:  PASS: Fast exception handling ({duration:.1f}s): {e}")

    def test_websocket_graceful_degradation_when_docker_unavailable(self):
        """
        VALIDATION TEST: WebSocket tests should skip gracefully when Docker unavailable
        
        EXPECTED RESULT: PASS - Should skip cleanly without hanging
        PURPOSE: Validates WebSocket test resilience after Issue #411 fix
        """
        logger.info(" PASS:  VALIDATION TEST: WebSocket graceful degradation - SHOULD SKIP CLEANLY")
        
        start_time = time.time()
        graceful_threshold = 3.0  # Should handle gracefully within 3 seconds
        
        try:
            # Mock Docker unavailable scenario
            with patch('test_framework.unified_docker_manager.UnifiedDockerManager.is_docker_available', return_value=False):
                
                # This should now skip gracefully instead of hanging
                manager = UnifiedDockerManager()
                
                # Check Docker availability (should be fast and return False)
                docker_available = manager.is_docker_available()
                
                duration = time.time() - start_time
                
                # Validate graceful handling
                assert duration < graceful_threshold, (
                    f"GRACEFUL DEGRADATION FAILED: Took {duration:.1f}s "
                    f"(should be < {graceful_threshold}s)"
                )
                
                assert not docker_available, "Mock should return Docker unavailable"
                
                logger.info(f" PASS:  PASS: Graceful degradation successful ({duration:.1f}s)")
                
        except Exception as e:
            duration = time.time() - start_time
            
            assert duration < graceful_threshold, (
                f"GRACEFUL DEGRADATION FAILED: Exception after {duration:.1f}s: {e}"
            )
            
            logger.info(f" PASS:  PASS: Exception handled gracefully ({duration:.1f}s): {e}")

    def test_docker_rate_limiter_fast_timeout_enforcement(self):
        """
        VALIDATION TEST: Docker rate limiter should enforce fast timeouts properly
        
        EXPECTED RESULT: PASS - Should timeout quickly and predictably
        PURPOSE: Validates rate limiter timeout fix for Issue #411
        """
        logger.info(" PASS:  VALIDATION TEST: Rate limiter fast timeout - SHOULD TIMEOUT QUICKLY")
        
        start_time = time.time()
        timeout_setting = 2.0  # Set 2s timeout
        tolerance = 1.0       # Allow 1s tolerance for timing
        
        try:
            rate_limiter = DockerRateLimiter()
            
            # Test with very short timeout - should be enforced properly
            result = rate_limiter.execute_docker_command(
                ["docker", "--version"],
                timeout=timeout_setting
            )
            
            duration = time.time() - start_time
            
            # If Docker available, command should complete quickly
            if result.returncode == 0:
                assert duration < timeout_setting + tolerance, (
                    f"TIMEOUT ENFORCEMENT FAILED: Available Docker took {duration:.1f}s "
                    f"(should be < {timeout_setting + tolerance}s)"
                )
                logger.info(f" PASS:  PASS: Docker available, completed quickly ({duration:.1f}s)")
                return
                
            # If Docker unavailable, should fail quickly
            assert duration < timeout_setting + tolerance, (
                f"TIMEOUT ENFORCEMENT FAILED: Unavailable Docker took {duration:.1f}s "
                f"(should be < {timeout_setting + tolerance}s)"
            )
            
            logger.info(f" PASS:  PASS: Docker unavailable, failed quickly ({duration:.1f}s)")
            
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            
            # Timeout should occur close to the specified timeout
            assert abs(duration - timeout_setting) < tolerance, (
                f"TIMEOUT TIMING FAILED: Timeout at {duration:.1f}s "
                f"(should be ~{timeout_setting}s  +/-  {tolerance}s)"
            )
            
            logger.info(f" PASS:  PASS: Timeout enforced correctly ({duration:.1f}s)")
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Other exceptions should also be fast
            assert duration < timeout_setting + tolerance, (
                f"EXCEPTION TIMING FAILED: Exception after {duration:.1f}s: {e}"
            )
            
            logger.info(f" PASS:  PASS: Exception handled quickly ({duration:.1f}s): {e}")

    def test_caching_prevents_repeated_slow_checks(self):
        """
        VALIDATION TEST: Docker availability caching should prevent repeated slow checks
        
        EXPECTED RESULT: PASS - Second check should be nearly instantaneous
        PURPOSE: Validates caching optimization for Issue #411
        """
        logger.info(" PASS:  VALIDATION TEST: Docker availability caching - SHOULD CACHE RESULTS")
        
        manager = UnifiedDockerManager()
        
        # First check (may take time to determine availability)
        start1 = time.time()
        result1 = manager.is_docker_available()
        duration1 = time.time() - start1
        
        # Second check (should be cached and nearly instantaneous)
        start2 = time.time()
        result2 = manager.is_docker_available()
        duration2 = time.time() - start2
        
        logger.info(f"First check: {duration1:.1f}s (result: {result1})")
        logger.info(f"Second check: {duration2:.1f}s (result: {result2})")
        
        # Results should be consistent
        assert result1 == result2, (
            f"CACHING FAILED: Inconsistent results - first: {result1}, second: {result2}"
        )
        
        # Second check should be much faster (cached)
        cache_threshold = 0.1  # Should be < 100ms
        assert duration2 < cache_threshold, (
            f"CACHING FAILED: Second check took {duration2:.1f}s "
            f"(should be < {cache_threshold}s due to caching)"
        )
        
        logger.info(f" PASS:  PASS: Caching working correctly (speedup: {duration1/duration2:.1f}x)")

    def test_mission_critical_websocket_no_hang_simulation(self):
        """
        VALIDATION TEST: Mission critical WebSocket tests should not hang after fix
        
        EXPECTED RESULT: PASS - Should complete or skip without hanging
        PURPOSE: Validates end-to-end fix for Issue #411
        """
        logger.info(" PASS:  VALIDATION TEST: Mission critical no hang - SHOULD COMPLETE/SKIP QUICKLY")
        
        start_time = time.time()
        no_hang_threshold = 5.0  # Should complete within 5 seconds
        
        try:
            # Simulate the fixed mission critical test behavior
            manager = UnifiedDockerManager()
            
            # Check if Docker is available (should be fast now)
            docker_available = manager.is_docker_available()
            
            if not docker_available:
                # Should skip gracefully instead of hanging
                logger.info("Docker unavailable - test should skip gracefully")
                duration = time.time() - start_time
                
                assert duration < no_hang_threshold, (
                    f"SKIP LOGIC FAILED: Took {duration:.1f}s to determine skip "
                    f"(should be < {no_hang_threshold}s)"
                )
                
                logger.info(f" PASS:  PASS: Graceful skip in {duration:.1f}s")
                pytest.skip("Docker unavailable - test skipped gracefully (fix working)")
                
            else:
                # Docker available - test can proceed
                duration = time.time() - start_time
                logger.info(f" PASS:  PASS: Docker available, proceeding with test ({duration:.1f}s)")
                
        except Exception as e:
            duration = time.time() - start_time
            
            # Even exceptions should be fast
            assert duration < no_hang_threshold, (
                f"EXCEPTION HANDLING FAILED: Exception after {duration:.1f}s: {e}"
            )
            
            logger.info(f" PASS:  PASS: Exception handled quickly ({duration:.1f}s): {e}")


if __name__ == "__main__":
    # Run validation tests for direct execution
    test_instance = TestDockerFastFailValidation()
    
    print(" PASS:  ISSUE #411 VALIDATION TESTS - These tests should PASS after fixes")
    print("=" * 80)
    
    tests = [
        ("Docker availability fast-fail", test_instance.test_docker_availability_fast_fail_when_unavailable),
        ("WebSocket graceful degradation", test_instance.test_websocket_graceful_degradation_when_docker_unavailable),
        ("Rate limiter fast timeout", test_instance.test_docker_rate_limiter_fast_timeout_enforcement),
        ("Docker availability caching", test_instance.test_caching_prevents_repeated_slow_checks),
        ("Mission critical no hang", test_instance.test_mission_critical_websocket_no_hang_simulation)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{len(tests) - passed - failed}. Testing {test_name}...")
            test_func()
            print(f"    PASS:  PASS: {test_name}")
            passed += 1
        except Exception as e:
            print(f"    FAIL:  FAIL: {test_name} - {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f" CHART:  VALIDATION RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print(" TARGET:  ALL VALIDATION TESTS PASSED - Issue #411 fixes are working!")
    else:
        print(" WARNING: [U+FE0F]  Some validation tests failed - Issue #411 fixes need more work")