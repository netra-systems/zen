"""
Critical Service Authentication Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (System Stability)
- Business Goal: Prevent CASCADE FAILURES from SERVICE_SECRET/SERVICE_ID mismatches
- Value Impact: Ensures 100% uptime by validating ultra-critical P0 authentication flows
- Strategic Impact: Prevents complete system outages that block ALL user authentication

This test suite validates the MOST CRITICAL authentication flows that can cause
complete system failure. Based on MISSION_CRITICAL_NAMED_VALUES_INDEX.xml:

1. SERVICE_SECRET missing = Complete authentication failure, 100% user lockout
2. SERVICE_ID mismatch = Service authentication failures every 60 seconds
3. Circuit breaker permanent failure states = System unusable

CRITICAL: These tests prevent the "error behind the error" scenarios where
authentication failures mask deeper architectural issues like circuit breaker flaws.

Incident References:
- 2025-09-05: SERVICE_SECRET missing caused complete staging outage (multiple hours)
- 2025-09-07: SERVICE_ID with timestamp caused auth failures every minute
- 2025-09-05: MockCircuitBreaker permanent failure (error behind the error)
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
from unittest.mock import patch, AsyncMock

import aiohttp
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.database_test_utilities import DatabaseTestUtilities
from test_framework.ssot.integration_auth_manager import (
    IntegrationAuthServiceManager,
    IntegrationTestAuthHelper,
    create_integration_test_helper
)
from shared.isolated_environment import get_env


logger = logging.getLogger(__name__)


class TestCriticalServiceAuthentication(SSotBaseTestCase):
    """
    Critical Service Authentication Integration Tests.
    
    Tests the ULTRA-CRITICAL P0 authentication flows that can cause complete
    system failure. These tests MUST pass or the system is unusable.
    
    CRITICAL: Uses real auth service, real database, real Redis.
    No mocks allowed for inter-service authentication validation.
    """
    
    @pytest.fixture(scope="class")
    async def auth_manager(self):
        """Start real auth service for integration testing."""
        manager = IntegrationAuthServiceManager()
        
        # Start auth service
        success = await manager.start_auth_service()
        if not success:
            pytest.fail("Failed to start auth service for critical integration tests")
        
        yield manager
        
        # Cleanup
        await manager.stop_auth_service()
    
    @pytest.fixture
    async def auth_helper(self, auth_manager):
        """Create auth helper for integration testing."""
        helper = IntegrationTestAuthHelper(auth_manager)
        yield helper
    
    @pytest.fixture
    async def test_database(self):
        """Provide isolated test database session."""
        async with DatabaseTestUtilities("auth_service").transaction_scope() as db_session:
            yield db_session
    
    # === ULTRA-CRITICAL P0 TESTS ===
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_service_secret_missing_causes_authentication_failure(
        self, auth_manager, auth_helper
    ):
        """
        CRITICAL P0: Missing SERVICE_SECRET causes complete authentication failure.
        
        This test validates the most critical failure scenario identified in
        MISSION_CRITICAL_NAMED_VALUES_INDEX.xml where missing SERVICE_SECRET
        triggers cascade failure with 100% user lockout.
        
        Incident Reference: 2025-09-05 complete staging outage (multiple hours)
        """
        # Record test start
        self.record_metric("test_category", "P0_critical_failure")
        self.record_metric("incident_reference", "2025-09-05_service_secret_outage")
        
        # Save original SERVICE_SECRET
        original_secret = self.get_env_var("SERVICE_SECRET")
        
        # Test with missing SERVICE_SECRET
        with self.temp_env_vars(SERVICE_SECRET=""):
            # Attempt inter-service authentication call
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Service-ID": "netra-backend",  # Hardcoded stable value
                    "X-Service-Secret": ""  # MISSING - should cause failure
                }
                
                request_data = {
                    "token": "dummy-token-for-validation-test",
                    "token_type": "access"
                }
                
                # This should FAIL due to missing SERVICE_SECRET
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/validate",
                    json=request_data,
                    headers=headers
                ) as response:
                    # CRITICAL: Must fail authentication
                    assert response.status in [401, 403], (
                        f"Expected authentication failure (401/403) with missing SERVICE_SECRET, "
                        f"got status {response.status}. This indicates SERVICE_SECRET validation "
                        f"is not working, which can cause cascade failures."
                    )
                    
                    error_data = await response.json()
                    
                    # Validate error indicates missing service secret
                    assert "service" in error_data.get("error", "").lower() or \
                           "authentication" in error_data.get("error", "").lower(), (
                        f"Error message should indicate service authentication failure. "
                        f"Got: {error_data}"
                    )
        
        self.record_metric("service_secret_validation", "working")
        self.increment_db_query_count(1)  # Validation attempt
        logger.info("✅ SERVICE_SECRET validation working correctly")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_service_id_hardcoded_netra_backend_required(
        self, auth_manager, auth_helper
    ):
        """
        CRITICAL P0: SERVICE_ID must be exactly "netra-backend" (hardcoded, stable).
        
        This test validates the critical requirement from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
        that SERVICE_ID must be the stable hardcoded value "netra-backend", NOT a variable
        with timestamps that causes authentication failures every 60 seconds.
        
        Incident Reference: 2025-09-07 auth failures every minute from timestamp SERVICE_ID
        """
        # Record test metadata
        self.record_metric("test_category", "P0_critical_stability")
        self.record_metric("incident_reference", "2025-09-07_service_id_timestamps")
        self.record_metric("required_service_id", "netra-backend")
        
        # Get valid SERVICE_SECRET
        service_secret = self.get_env_var("SERVICE_SECRET") or "test-service-secret-32-chars-long"
        
        # Test 1: Correct SERVICE_ID should work
        await self._test_service_id_authentication(
            auth_manager, 
            service_id="netra-backend",  # HARDCODED STABLE VALUE
            service_secret=service_secret,
            should_succeed=True,
            test_name="correct_hardcoded_service_id"
        )
        
        # Test 2: SERVICE_ID with timestamp should FAIL (prevent regression)
        await self._test_service_id_authentication(
            auth_manager,
            service_id="netra-auth-staging-20250907120000",  # With timestamp - BAD
            service_secret=service_secret,
            should_succeed=False,
            test_name="timestamp_service_id_regression"
        )
        
        # Test 3: Wrong service name should FAIL
        await self._test_service_id_authentication(
            auth_manager,
            service_id="wrong-service-name",
            service_secret=service_secret,
            should_succeed=False,
            test_name="wrong_service_name"
        )
        
        self.record_metric("service_id_validation", "working")
        logger.info("✅ SERVICE_ID hardcoded validation working correctly")
    
    async def _test_service_id_authentication(
        self,
        auth_manager: IntegrationAuthServiceManager,
        service_id: str,
        service_secret: str,
        should_succeed: bool,
        test_name: str
    ):
        """Helper to test SERVICE_ID authentication scenarios."""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "X-Service-ID": service_id,
                "X-Service-Secret": service_secret
            }
            
            request_data = {
                "token": "dummy-token-for-service-id-test",
                "token_type": "access"
            }
            
            async with session.post(
                f"{auth_manager.get_auth_url()}/auth/validate",
                json=request_data,
                headers=headers
            ) as response:
                if should_succeed:
                    # Note: This might return 401 due to invalid dummy token, but should not
                    # return service authentication errors (403)
                    assert response.status != 403, (
                        f"Service ID '{service_id}' should be accepted but got 403 Forbidden. "
                        f"This indicates SERVICE_ID validation failed."
                    )
                    self.record_metric(f"service_id_test_{test_name}", "passed")
                else:
                    # Should fail with service authentication error
                    assert response.status == 403, (
                        f"Service ID '{service_id}' should be rejected with 403 but got {response.status}. "
                        f"This indicates SERVICE_ID validation is not working properly."
                    )
                    self.record_metric(f"service_id_test_{test_name}", "correctly_rejected")
                
                self.increment_db_query_count(1)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_circuit_breaker_permanent_failure_prevention(
        self, auth_manager, auth_helper
    ):
        """
        CRITICAL P0: Prevent circuit breaker permanent failure states.
        
        This test validates the "error behind the error" scenario identified in
        MISSION_CRITICAL_NAMED_VALUES_INDEX.xml where MockCircuitBreaker enters
        permanent failure state, causing complete system unusability.
        
        Incident Reference: 2025-09-05 permanent circuit breaker failure
        """
        # Record test metadata
        self.record_metric("test_category", "P0_error_behind_error")
        self.record_metric("incident_reference", "2025-09-05_circuit_breaker_permanent")
        
        # Test rapid sequential authentication attempts to stress circuit breaker
        service_secret = self.get_env_var("SERVICE_SECRET") or "test-service-secret-32-chars-long"
        
        consecutive_failures = 0
        max_allowed_consecutive_failures = 3  # Circuit breaker threshold
        
        # Perform multiple authentication attempts
        for attempt in range(10):
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Content-Type": "application/json",
                        "X-Service-ID": "netra-backend",
                        "X-Service-Secret": service_secret
                    }
                    
                    request_data = {
                        "token": f"test-token-{attempt}",
                        "token_type": "access"
                    }
                    
                    async with session.post(
                        f"{auth_manager.get_auth_url()}/auth/validate",
                        json=request_data,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        
                        # Check if circuit breaker is open (permanent failure)
                        if response.status == 503:  # Service unavailable
                            consecutive_failures += 1
                            
                            # CRITICAL: Circuit breaker should not stay permanently open
                            assert consecutive_failures <= max_allowed_consecutive_failures, (
                                f"Circuit breaker appears to be permanently open after {consecutive_failures} "
                                f"consecutive failures. This indicates the MockCircuitBreaker permanent failure "
                                f"state bug has regressed. System would be unusable."
                            )
                        else:
                            # Reset consecutive failure count on success
                            consecutive_failures = 0
                        
                        self.increment_db_query_count(1)
                        
                        # Small delay to avoid overwhelming the service
                        await asyncio.sleep(0.1)
                        
            except asyncio.TimeoutError:
                consecutive_failures += 1
                logger.warning(f"Authentication request {attempt} timed out")
                
                # CRITICAL: Timeout could indicate permanent failure state
                assert consecutive_failures <= max_allowed_consecutive_failures, (
                    f"Multiple consecutive timeouts ({consecutive_failures}) suggest circuit breaker "
                    f"permanent failure state. This is a critical system failure."
                )
        
        self.record_metric("circuit_breaker_max_consecutive_failures", consecutive_failures)
        self.record_metric("circuit_breaker_permanent_failure_prevention", "working")
        logger.info(f"✅ Circuit breaker working correctly (max consecutive failures: {consecutive_failures})")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_authentication_cascade_failure_recovery(
        self, auth_manager, auth_helper
    ):
        """
        Integration test for service authentication cascade failure recovery.
        
        This test simulates and validates recovery from the cascade failure
        scenario where missing SERVICE_SECRET causes complete system failure.
        """
        # Record test metadata
        self.record_metric("test_category", "cascade_failure_recovery")
        
        # Step 1: Simulate missing SERVICE_SECRET (should cause failure)
        with self.temp_env_vars(SERVICE_SECRET=""):
            failure_confirmed = await self._verify_authentication_failure(
                auth_manager, "missing_service_secret"
            )
            assert failure_confirmed, "Missing SERVICE_SECRET should cause authentication failure"
        
        # Step 2: Restore SERVICE_SECRET (should recover immediately)
        service_secret = "test-service-secret-32-chars-long"
        with self.temp_env_vars(SERVICE_SECRET=service_secret):
            recovery_confirmed = await self._verify_authentication_recovery(
                auth_manager, service_secret, "service_secret_restored"
            )
            assert recovery_confirmed, "Authentication should recover immediately after SERVICE_SECRET restoration"
        
        self.record_metric("cascade_failure_recovery", "working")
        logger.info("✅ Cascade failure recovery working correctly")
    
    async def _verify_authentication_failure(
        self, auth_manager: IntegrationAuthServiceManager, scenario: str
    ) -> bool:
        """Verify that authentication fails in the given scenario."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Service-ID": "netra-backend",
                    "X-Service-Secret": self.get_env_var("SERVICE_SECRET", "")
                }
                
                request_data = {
                    "token": f"test-token-{scenario}",
                    "token_type": "access"
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/validate",
                    json=request_data,
                    headers=headers
                ) as response:
                    # Authentication should fail
                    is_failure = response.status in [401, 403]
                    self.record_metric(f"failure_scenario_{scenario}", "confirmed" if is_failure else "unexpected_success")
                    self.increment_db_query_count(1)
                    return is_failure
        except Exception as e:
            logger.warning(f"Authentication failure verification error: {e}")
            return True  # Exception also indicates failure
    
    async def _verify_authentication_recovery(
        self, auth_manager: IntegrationAuthServiceManager, service_secret: str, scenario: str
    ) -> bool:
        """Verify that authentication recovers in the given scenario."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Service-ID": "netra-backend",
                    "X-Service-Secret": service_secret
                }
                
                request_data = {
                    "token": f"test-token-{scenario}",
                    "token_type": "access"
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/validate",
                    json=request_data,
                    headers=headers
                ) as response:
                    # Service authentication should work (token might still be invalid)
                    # But we should not get service authentication errors (403)
                    is_recovery = response.status != 403
                    self.record_metric(f"recovery_scenario_{scenario}", "confirmed" if is_recovery else "still_failing")
                    self.increment_db_query_count(1)
                    return is_recovery
        except Exception as e:
            logger.error(f"Authentication recovery verification error: {e}")
            return False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_authentication_performance_requirements(
        self, auth_manager, auth_helper
    ):
        """
        Integration test for service authentication performance requirements.
        
        Validates that service authentication performs within acceptable limits
        to prevent performance degradation that could trigger circuit breakers.
        """
        # Record test metadata
        self.record_metric("test_category", "performance_requirements")
        
        service_secret = self.get_env_var("SERVICE_SECRET") or "test-service-secret-32-chars-long"
        
        # Test multiple authentication requests and measure performance
        response_times = []
        num_requests = 10
        
        for i in range(num_requests):
            start_time = time.time()
            
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Content-Type": "application/json",
                        "X-Service-ID": "netra-backend",
                        "X-Service-Secret": service_secret
                    }
                    
                    request_data = {
                        "token": f"perf-test-token-{i}",
                        "token_type": "access"
                    }
                    
                    async with session.post(
                        f"{auth_manager.get_auth_url()}/auth/validate",
                        json=request_data,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        response_time = time.time() - start_time
                        response_times.append(response_time)
                        
                        # Service authentication should not fail (token validation may fail)
                        assert response.status != 403, (
                            f"Service authentication failed on request {i}. "
                            f"This suggests SERVICE_SECRET or SERVICE_ID issues."
                        )
                        
                        self.increment_db_query_count(1)
                        
            except asyncio.TimeoutError:
                pytest.fail(f"Authentication request {i} timed out (>10s). This is unacceptable performance.")
        
        # Analyze performance
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # Performance requirements
        assert avg_response_time < 1.0, (
            f"Average authentication response time {avg_response_time:.3f}s exceeds 1.0s limit. "
            f"Slow authentication can trigger circuit breaker failures."
        )
        
        assert max_response_time < 3.0, (
            f"Maximum authentication response time {max_response_time:.3f}s exceeds 3.0s limit. "
            f"This could cause timeout-based failures."
        )
        
        self.record_metric("avg_auth_response_time_ms", avg_response_time * 1000)
        self.record_metric("max_auth_response_time_ms", max_response_time * 1000)
        self.record_metric("authentication_performance", "acceptable")
        
        logger.info(f"✅ Authentication performance acceptable (avg: {avg_response_time:.3f}s, max: {max_response_time:.3f}s)")
    
    # === TEARDOWN AND VALIDATION ===
    
    def teardown_method(self, method=None):
        """Enhanced teardown with critical metrics validation."""
        super().teardown_method(method)
        
        # Validate critical metrics were recorded
        metrics = self.get_all_metrics()
        
        # Ensure critical tests recorded their metrics
        if "P0_critical" in method.__name__ if method else "":
            assert "test_category" in metrics, "Critical P0 tests must record test_category metric"
            assert "incident_reference" in metrics, "Critical P0 tests must record incident_reference metric"
        
        # Log final metrics for analysis
        logger.info(f"Test metrics: {metrics}")
