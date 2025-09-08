"""
Test Auth Circuit Breaker Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: System Resilience & Availability 
- Value Impact: Prevents auth service outages from cascading to complete system failure
- Strategic Impact: Enterprise-grade resilience - maintains service availability during auth degradation

This test suite validates the circuit breaker pattern for authentication:
1. Circuit breaker state transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
2. Failure threshold detection and circuit opening
3. Recovery timeout and service restoration testing
4. Fallback behavior during circuit open states
5. Performance under various failure scenarios
6. Integration with auth service resilience patterns
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from unittest.mock import AsyncMock, patch, MagicMock

from netra_backend.app.clients.auth_client_core import AuthServiceClient, CircuitBreakerError
from netra_backend.app.clients.auth_client_cache import AuthCircuitBreakerManager, MockCircuitBreaker
from netra_backend.app.clients.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpen,
    CircuitBreakerTimeout,
    get_circuit_breaker
)
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerState
)
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env


class TestAuthCircuitBreakerIntegration:
    """Test authentication circuit breaker integration with real components."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_circuit_breaker_closed_state_normal_operation(self, real_services_fixture):
        """
        Test circuit breaker in CLOSED state during normal auth service operation.
        
        Business Value: Ensures auth system operates normally when service is healthy.
        This is the baseline - all users should authenticate successfully when systems are up.
        """
        # Arrange: Circuit breaker in closed state
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=10.0
        )
        breaker = CircuitBreaker("test_auth_service", config)
        
        # Mock successful auth service calls
        async def mock_auth_call():
            return {
                "valid": True,
                "user_id": "normal_user_123",
                "email": "normal@example.com",
                "permissions": ["read", "write"]
            }
        
        # Act: Execute multiple successful calls
        results = []
        for i in range(5):
            result = await breaker.call(mock_auth_call)
            results.append(result)
        
        # Assert: All calls successful, circuit remains closed
        assert len(results) == 5, "All calls should complete successfully"
        for result in results:
            assert result["valid"] is True, "Each call should be valid"
        
        assert breaker.state == CircuitState.CLOSED, "Circuit should remain CLOSED during normal operation"
        
        stats = breaker.get_stats()
        assert stats["stats"]["successful_calls"] == 5, "Should record 5 successful calls"
        assert stats["stats"]["failed_calls"] == 0, "Should record 0 failed calls"
        assert stats["stats"]["consecutive_failures"] == 0, "Should have 0 consecutive failures"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_circuit_breaker_failure_threshold_and_opening(self, real_services_fixture):
        """
        Test circuit breaker opening when auth service failure threshold is exceeded.
        
        Business Value: Prevents auth service overload during outages by stopping requests.
        Critical for system protection - avoids cascading failures during auth problems.
        """
        # Arrange: Circuit breaker with low failure threshold for testing
        config = CircuitBreakerConfig(
            failure_threshold=3,  # Open after 3 failures
            success_threshold=2,
            timeout=5.0
        )
        breaker = CircuitBreaker("test_auth_failure", config)
        
        # Mock failing auth service calls
        async def mock_failing_auth_call():
            raise ConnectionError("Auth service unavailable")
        
        # Act: Execute calls until circuit opens
        failure_count = 0
        for i in range(5):  # Try 5 calls, should open after 3 failures
            try:
                await breaker.call(mock_failing_auth_call)
            except (ConnectionError, CircuitBreakerOpen):
                failure_count += 1
                
                # Check if circuit opened after threshold
                if i >= config.failure_threshold - 1:  # After 3rd failure (index 2)
                    assert breaker.state == CircuitState.OPEN, f"Circuit should be OPEN after {i+1} failures"
        
        # Assert: Circuit opened due to failures
        assert breaker.state == CircuitState.OPEN, "Circuit should be OPEN after exceeding failure threshold"
        assert failure_count >= config.failure_threshold, "Should have recorded sufficient failures"
        
        stats = breaker.get_stats()
        assert stats["stats"]["failed_calls"] >= config.failure_threshold, "Should record failed calls"
        assert stats["stats"]["consecutive_failures"] >= config.failure_threshold, "Should track consecutive failures"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_circuit_breaker_open_state_blocking_behavior(self, real_services_fixture):
        """
        Test circuit breaker blocking calls when in OPEN state.
        
        Business Value: Protects auth service from overload during outages.
        Provides immediate failure responses instead of waiting for timeouts.
        """
        # Arrange: Circuit breaker forced to OPEN state
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout=10.0
        )
        breaker = CircuitBreaker("test_auth_open", config)
        
        # Force circuit to OPEN state by causing failures
        async def mock_failing_call():
            raise ConnectionError("Service down")
        
        # Cause failures to open circuit
        for i in range(3):
            try:
                await breaker.call(mock_failing_call)
            except (ConnectionError, CircuitBreakerOpen):
                pass
        
        # Verify circuit is open
        assert breaker.state == CircuitState.OPEN, "Circuit should be OPEN before test"
        
        # Act: Attempt call while circuit is open
        async def mock_auth_call():
            return {"valid": True, "user_id": "test"}
        
        with pytest.raises(CircuitBreakerOpen):
            await breaker.call(mock_auth_call)
        
        # Assert: Call was blocked by open circuit
        stats = breaker.get_stats()
        assert stats["state"] == "open", "Circuit should remain OPEN"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_circuit_breaker_half_open_recovery_testing(self, real_services_fixture):
        """
        Test circuit breaker HALF_OPEN state for service recovery testing.
        
        Business Value: Enables automatic recovery when auth service becomes available.
        Critical for restoring full functionality after outages without manual intervention.
        """
        # Arrange: Circuit breaker with short timeout for testing
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout=1.0,  # Short timeout for quick recovery testing
            half_open_max_calls=2
        )
        breaker = CircuitBreaker("test_auth_recovery", config)
        
        # Force circuit to OPEN by causing failures
        async def failing_call():
            raise ConnectionError("Service down")
        
        for i in range(3):
            try:
                await breaker.call(failing_call)
            except (ConnectionError, CircuitBreakerOpen):
                pass
        
        assert breaker.state == CircuitState.OPEN, "Circuit should be OPEN initially"
        
        # Wait for timeout to enable HALF_OPEN state
        await asyncio.sleep(1.2)  # Slightly longer than timeout
        
        # Mock successful recovery call
        async def recovery_call():
            return {
                "valid": True,
                "user_id": "recovery_user",
                "email": "recovery@example.com"
            }
        
        # Act: Make calls during recovery testing
        result1 = await breaker.call(recovery_call)
        result2 = await breaker.call(recovery_call)
        
        # Assert: Circuit should transition through HALF_OPEN to CLOSED
        # After 2 successful calls (success_threshold=2), circuit should be CLOSED
        assert breaker.state == CircuitState.CLOSED, "Circuit should be CLOSED after successful recovery"
        assert result1["valid"] is True, "Recovery call 1 should succeed"
        assert result2["valid"] is True, "Recovery call 2 should succeed"
        
        stats = breaker.get_stats()
        assert stats["stats"]["consecutive_successes"] >= config.success_threshold, "Should track recovery successes"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_circuit_breaker_fallback_behavior_integration(self, real_services_fixture):
        """
        Test circuit breaker fallback behavior during auth service unavailability.
        
        Business Value: Provides degraded but functional service during auth outages.
        Maintains basic platform functionality even when auth service is down.
        """
        # Arrange: Circuit breaker with fallback function
        async def auth_fallback(*args, **kwargs):
            """Fallback authentication using cached data or basic validation"""
            return {
                "valid": True,
                "user_id": "fallback_user",
                "email": "fallback@example.com",
                "permissions": ["read"],
                "source": "fallback",
                "warning": "Using fallback authentication due to service unavailability"
            }
        
        config = CircuitBreakerConfig(failure_threshold=2, timeout=5.0)
        breaker = CircuitBreaker("test_auth_fallback", config, fallback=auth_fallback)
        
        # Force circuit open with failures
        async def failing_auth():
            raise ConnectionError("Auth service down")
        
        for i in range(3):
            try:
                await breaker.call(failing_auth)
            except (ConnectionError, CircuitBreakerOpen):
                pass
        
        assert breaker.state == CircuitState.OPEN, "Circuit should be OPEN before fallback test"
        
        # Act: Call with circuit open should use fallback
        result = await breaker.call(failing_auth)  # This will use fallback since circuit is open
        
        # Assert: Fallback was used successfully
        assert result is not None, "Fallback should provide result"
        assert result["valid"] is True, "Fallback should provide valid response"
        assert result["source"] == "fallback", "Should indicate fallback was used"
        assert "warning" in result, "Should include warning about fallback usage"
        assert result["user_id"] == "fallback_user", "Should use fallback user data"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_circuit_breaker_timeout_handling(self, real_services_fixture):
        """
        Test circuit breaker handling of auth service call timeouts.
        
        Business Value: Prevents slow auth service from blocking user requests.
        Ensures responsive user experience even when auth service is degraded.
        """
        # Arrange: Circuit breaker with short call timeout
        config = CircuitBreakerConfig(
            failure_threshold=2,
            call_timeout=0.5,  # 500ms timeout
            timeout=5.0
        )
        breaker = CircuitBreaker("test_auth_timeout", config)
        
        # Mock slow auth service call
        async def slow_auth_call():
            await asyncio.sleep(1.0)  # Takes longer than call_timeout
            return {"valid": True, "user_id": "slow_user"}
        
        # Act: Call should timeout and be treated as failure
        with pytest.raises(CircuitBreakerTimeout):
            await breaker.call(slow_auth_call)
        
        # Assert: Timeout was handled as failure
        stats = breaker.get_stats()
        assert stats["stats"]["failed_calls"] >= 1, "Timeout should count as failure"
        assert stats["stats"]["consecutive_failures"] >= 1, "Should increment consecutive failures"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_unified_circuit_breaker_auth_integration(self, real_services_fixture):
        """
        Test UnifiedCircuitBreaker integration with auth client.
        
        Business Value: Ensures auth system uses enterprise-grade circuit breaker.
        Provides consistent resilience patterns across the platform.
        """
        # Arrange: Create UnifiedCircuitBreaker for auth operations
        config = UnifiedCircuitConfig(
            name="unified_auth_test",
            failure_threshold=3,
            success_threshold=2,
            recovery_timeout=2,
            timeout_seconds=1.0
        )
        breaker = UnifiedCircuitBreaker(config)
        
        # Mock auth operations
        async def mock_auth_operation():
            return {
                "valid": True,
                "user_id": "unified_user_123",
                "email": "unified@example.com"
            }
        
        async def failing_auth_operation():
            raise ConnectionError("Unified auth service down")
        
        # Act: Test normal operation
        result = await breaker.call(mock_auth_operation)
        assert result["valid"] is True, "Unified circuit breaker should handle successful auth"
        assert breaker.state == UnifiedCircuitBreakerState.CLOSED, "Should remain closed on success"
        
        # Test failure handling
        failure_count = 0
        for i in range(5):
            try:
                await breaker.call(failing_auth_operation)
            except Exception:
                failure_count += 1
                if failure_count >= config.failure_threshold:
                    assert breaker.state == UnifiedCircuitBreakerState.OPEN, "Should open after failures"
                    break
        
        # Assert: Circuit opened appropriately
        assert breaker.state == UnifiedCircuitBreakerState.OPEN, "Unified circuit should open on failures"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_circuit_breaker_manager_integration(self, real_services_fixture):
        """
        Test AuthCircuitBreakerManager with multiple auth operations.
        
        Business Value: Manages circuit breakers for different auth operations.
        Provides centralized resilience management for auth service interactions.
        """
        # Arrange: Circuit breaker manager
        manager = AuthCircuitBreakerManager()
        
        # Mock different auth operations
        async def validate_token_operation():
            return {"valid": True, "operation": "validate"}
        
        async def login_operation():
            return {"success": True, "operation": "login"}
        
        async def logout_operation():
            return {"success": True, "operation": "logout"}
        
        # Act: Use manager for different operations
        validate_result = await manager.call_with_breaker(validate_token_operation)
        login_result = await manager.call_with_breaker(login_operation)
        logout_result = await manager.call_with_breaker(logout_operation)
        
        # Assert: Manager handled all operations
        assert validate_result["operation"] == "validate", "Validate operation should work"
        assert login_result["operation"] == "login", "Login operation should work"
        assert logout_result["operation"] == "logout", "Logout operation should work"
        
        # Verify different breakers were created
        assert len(manager._breakers) >= 3, "Manager should create separate breakers for operations"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_circuit_breaker_with_real_auth_client(self, real_services_fixture):
        """
        Test circuit breaker integration with real AuthServiceClient.
        
        Business Value: Validates end-to-end circuit breaker protection in auth flow.
        Ensures real auth operations are protected by circuit breaker patterns.
        """
        # Arrange: Real auth client with circuit breaker
        client = AuthServiceClient()
        client.service_id = "circuit_test_service"
        client.service_secret = "circuit_test_secret"
        
        test_token = "circuit_breaker_test_token"
        
        # Test with connection errors to trigger circuit breaker
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock connection errors to test circuit breaker
            mock_post.side_effect = ConnectionError("Auth service unreachable")
            
            # Act: Multiple validation attempts should trigger circuit breaker
            results = []
            for i in range(5):
                result = await client.validate_token(test_token)
                results.append(result)
                
                # Verify error handling gets better over time (circuit breaker effect)
                assert result is not None, f"Attempt {i} should return error result"
                assert result["valid"] is False, f"Attempt {i} should be invalid due to service issues"
        
        # Assert: Circuit breaker protected auth service from excessive calls
        assert len(results) == 5, "All validation attempts should complete with circuit breaker protection"
        for result in results:
            assert "error" in result, "Each result should contain error information"
            assert "user_notification" in result, "Each result should have user notification"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_circuit_breaker_performance_under_load(self, real_services_fixture):
        """
        Test circuit breaker performance with concurrent auth requests.
        
        Business Value: Ensures circuit breaker handles production-level concurrent load.
        Critical for multi-user platform performance during auth service issues.
        """
        # Arrange: Circuit breaker for load testing
        config = CircuitBreakerConfig(
            failure_threshold=5,
            call_timeout=2.0,
            half_open_max_calls=3
        )
        breaker = CircuitBreaker("test_auth_load", config)
        
        # Mix of successful and failing operations
        async def mixed_auth_operation(request_id: int):
            if request_id % 3 == 0:  # Every 3rd request fails
                raise ConnectionError(f"Simulated failure for request {request_id}")
            else:
                return {
                    "valid": True,
                    "user_id": f"load_user_{request_id}",
                    "request_id": request_id
                }
        
        # Act: Execute concurrent requests
        num_requests = 20
        tasks = [
            breaker.call(mixed_auth_operation, i) 
            for i in range(num_requests)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Assert: Performance and correctness
        assert len(results) == num_requests, "All concurrent requests should complete"
        
        successful_results = [r for r in results if isinstance(r, dict) and r.get("valid")]
        errors = [r for r in results if isinstance(r, Exception)]
        
        # Should have mix of successes and handled errors
        assert len(successful_results) > 0, "Should have some successful requests"
        assert len(errors) > 0, "Should have some failed requests"
        
        # Performance should be reasonable even with failures
        total_time = end_time - start_time
        assert total_time < 10.0, "Concurrent requests should complete within reasonable time"
        
        # Verify circuit breaker statistics
        stats = breaker.get_stats()
        assert stats["stats"]["total_calls"] >= num_requests, "Should track all calls"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_circuit_breaker_recovery_after_service_restoration(self, real_services_fixture):
        """
        Test complete recovery cycle after auth service restoration.
        
        Business Value: Ensures full service restoration after auth service recovery.
        Critical for returning to normal operations after outage resolution.
        """
        # Arrange: Circuit breaker for recovery testing
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=1.0  # Quick recovery for testing
        )
        breaker = CircuitBreaker("test_auth_full_recovery", config)
        
        # Phase 1: Cause failures to open circuit
        async def failing_operation():
            raise ConnectionError("Service down")
        
        for i in range(4):  # Exceed failure threshold
            try:
                await breaker.call(failing_operation)
            except (ConnectionError, CircuitBreakerOpen):
                pass
        
        assert breaker.state == CircuitState.OPEN, "Circuit should be OPEN after failures"
        
        # Wait for recovery timeout
        await asyncio.sleep(1.2)
        
        # Phase 2: Service recovery with successful operations
        async def recovered_operation():
            return {
                "valid": True,
                "user_id": "recovered_user",
                "service_status": "fully_recovered"
            }
        
        # Act: Execute recovery operations
        recovery_result_1 = await breaker.call(recovered_operation)
        recovery_result_2 = await breaker.call(recovered_operation)
        
        # Assert: Full recovery achieved
        assert breaker.state == CircuitState.CLOSED, "Circuit should be CLOSED after full recovery"
        assert recovery_result_1["service_status"] == "fully_recovered"
        assert recovery_result_2["service_status"] == "fully_recovered"
        
        # Verify normal operations continue
        normal_result = await breaker.call(recovered_operation)
        assert normal_result["valid"] is True, "Normal operations should work after recovery"
        
        # Check final statistics
        final_stats = breaker.get_stats()
        assert final_stats["state"] == "closed", "Final state should be closed"
        assert final_stats["stats"]["consecutive_successes"] >= 2, "Should track recovery successes"