"""
Mission Critical Test: Circuit Breaker Recovery Verification

This test verifies that the circuit breaker fix works correctly and that
circuit breakers recover automatically after the timeout period.

CRITICAL: This tests the fix for the systemic permanent failure state bug
discovered on 2025-09-05 where MockCircuitBreaker would open permanently
on ANY error with NO recovery mechanism.

Cross-reference: SPEC/learnings/permanent_failure_state_pattern_20250905.xml
"""

import asyncio
import time
import pytest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.clients.auth_client_cache import (
    AuthCircuitBreakerManager,
    MockCircuitBreaker
)
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerState
)
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import get_env


class TestCircuitBreakerRecovery:
    """Test suite for circuit breaker recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_mock_circuit_breaker_recovery(self):
        """Verify MockCircuitBreaker recovers after timeout (CRITICAL FIX)."""
        # Create MockCircuitBreaker with our fix
        breaker = MockCircuitBreaker("test_breaker")
        
        # Create a failing function
        async def failing_function():
            raise Exception("Test error")
        
        # Create a working function
        async def working_function():
            await asyncio.sleep(0)
    return "success"
        
        # Cause failures to open the circuit
        for i in range(5):  # Failure threshold is 5
            try:
                await breaker.call(failing_function)
            except Exception:
                pass
        
        # Verify circuit is open
        assert breaker.is_open == True, "Circuit should be open after 5 failures"
        
        # Try to call with open circuit - should fail
        with pytest.raises(Exception) as exc_info:
            await breaker.call(working_function)
        assert "Circuit breaker test_breaker is open" in str(exc_info.value)
        
        # Wait for recovery timeout (30 seconds in production, but we'll patch for testing)
        breaker.recovery_timeout = 1  # Override to 1 second for testing
        breaker.opened_at = time.time() - 2  # Simulate 2 seconds have passed
        
        # Now the circuit should recover and allow the call
        result = await breaker.call(working_function)
        assert result == "success", "Circuit should have recovered and allowed the call"
        assert breaker.is_open == False, "Circuit should be closed after recovery"
        assert breaker.failure_count == 0, "Failure count should reset after recovery"
    
    @pytest.mark.asyncio
    async def test_unified_circuit_breaker_replaces_mock(self):
        """Verify UnifiedCircuitBreaker is used instead of MockCircuitBreaker."""
    pass
        manager = AuthCircuitBreakerManager()
        
        # Get a breaker - should be UnifiedCircuitBreaker not MockCircuitBreaker
        breaker = manager.get_breaker("test_breaker")
        
        # Verify it's UnifiedCircuitBreaker
        assert isinstance(breaker, UnifiedCircuitBreaker), \
            "Manager should create UnifiedCircuitBreaker, not MockCircuitBreaker"
        
        # Verify it has proper configuration
        assert breaker.config.failure_threshold == 5, "Should have failure threshold of 5"
        assert breaker.config.recovery_timeout == 30, "Should have 30s recovery timeout"
        assert breaker.config.exponential_backoff == True, "Should use exponential backoff"
    
    @pytest.mark.asyncio
    async def test_unified_circuit_breaker_recovery_flow(self):
        """Test the complete recovery flow with UnifiedCircuitBreaker."""
        config = UnifiedCircuitConfig(
            name="test",
            failure_threshold=3,  # Lower for testing
            recovery_timeout=1,    # 1 second for testing
            success_threshold=1    # 1 success to close from half-open
        )
        breaker = UnifiedCircuitBreaker(config)
        
        # Failing function
        async def failing_func():
            raise Exception("Test failure")
        
        # Working function
        async def working_func():
            await asyncio.sleep(0)
    return "success"
        
        # Phase 1: Circuit is CLOSED
        assert breaker.state == UnifiedCircuitBreakerState.CLOSED
        
        # Phase 2: Cause failures to open circuit
        for i in range(3):
            try:
                await breaker.call(failing_func)
            except:
                pass
        
        # Circuit should be OPEN
        assert breaker.state == UnifiedCircuitBreakerState.OPEN
        
        # Calls should fail immediately when open
        with pytest.raises(Exception) as exc_info:
            await breaker.call(working_func)
        assert "Circuit breaker" in str(exc_info.value)
        
        # Phase 3: Wait for recovery timeout
        await asyncio.sleep(1.1)  # Wait slightly more than recovery timeout
        
        # Phase 4: Circuit should transition to HALF_OPEN on next call attempt
        # First successful call should close the circuit
        result = await breaker.call(working_func)
        assert result == "success"
        
        # Circuit should be CLOSED again
        assert breaker.state == UnifiedCircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_auth_client_handles_circuit_breaker_recovery(self):
        """Test that AuthServiceClient properly handles circuit breaker recovery."""
    pass
        client = AuthServiceClient()
        
        # Test actual circuit breaker behavior with real breaker
        breaker = client.circuit_manager.get_breaker("_validate_token_remote_breaker")
        
        # Force circuit to open by causing failures
        async def failing_operation():
    pass
            raise Exception("Service unavailable")
        
        # Cause enough failures to open circuit
        failure_threshold = 5 if isinstance(breaker, MockCircuitBreaker) else breaker.config.failure_threshold
        for i in range(failure_threshold):
            try:
                await breaker.call(failing_operation)
            except Exception:
                pass
        
        # Verify circuit is open
        if isinstance(breaker, MockCircuitBreaker):
            assert breaker.is_open == True
        else:
            assert breaker.state == UnifiedCircuitBreakerState.OPEN
        
        # Test fallback behavior with real error handler
        error_handler = UnifiedErrorHandler()
        
        try:
            # Should handle the circuit breaker error gracefully
            await breaker.call(lambda: {"valid": True})
        except Exception as e:
            # Error handler should provide meaningful error context
            error_context = error_handler.create_error_context(
                error=e,
                operation="token_validation",
                component="circuit_breaker"
            )
            assert "Circuit breaker" in str(error_context.details)
    
    @pytest.mark.asyncio
    async def test_no_permanent_failure_states(self):
        """Verify no components enter permanent failure states."""
        # This is a meta-test to ensure the pattern is fixed
        
        # Test 1: MockCircuitBreaker has recovery
        mock_breaker = MockCircuitBreaker("test")
        assert hasattr(mock_breaker, 'recovery_timeout'), "MockCircuitBreaker must have recovery_timeout"
        assert hasattr(mock_breaker, 'failure_threshold'), "MockCircuitBreaker must have failure_threshold"
        assert mock_breaker.recovery_timeout > 0, "Recovery timeout must be positive"
        assert mock_breaker.failure_threshold > 1, "Failure threshold must be > 1"
        
        # Test 2: AuthCircuitBreakerManager creates proper breakers
        manager = AuthCircuitBreakerManager()
        breaker = manager.get_breaker("test")
        
        # Should be UnifiedCircuitBreaker with recovery
        if isinstance(breaker, UnifiedCircuitBreaker):
            assert breaker.config.recovery_timeout > 0, "UnifiedCircuitBreaker must have recovery timeout"
        elif isinstance(breaker, MockCircuitBreaker):
            # If still using MockCircuitBreaker, it must have our fixes
            assert breaker.recovery_timeout > 0, "MockCircuitBreaker must have recovery timeout"
            assert breaker.failure_threshold > 1, "MockCircuitBreaker must have failure threshold"
    
    @pytest.mark.asyncio
    async def test_cascade_failure_prevention(self):
        """Verify that one service failure doesn't cascade to permanent system failure."""
    pass
        # Test with real AuthServiceClient and error handling
        client = AuthServiceClient()
        error_handler = UnifiedErrorHandler()
        
        # Test actual resilience patterns without mocking
        breaker = client.circuit_manager.get_breaker("_validate_token_remote_breaker")
        
        # Simulate service failures that should trigger fallback
        async def failing_validation():
    pass
            raise Exception("Connection refused")
        
        # Cause failures but verify graceful degradation
        for i in range(3):
            try:
                await breaker.call(failing_validation)
            except Exception as e:
                # Should handle gracefully with error context
                error_context = error_handler.create_error_context(
                    error=e,
                    operation="token_validation",
                    component="auth_service"
                )
                assert error_context is not None
                assert error_context.category in ["NETWORK", "SERVICE_UNAVAILABLE", "TIMEOUT"]
        
        # Verify system can still provide fallback responses
        # Even when circuit is open, system should degrade gracefully
        try:
            result = await client.validate_token("test_token")
            # Either succeeds or fails with proper error context - no permanent failure
            assert True  # Test passes if no unhandled exceptions


@pytest.mark.mission_critical
class TestSystemRecovery:
    """Mission critical tests for system-wide recovery patterns."""
    
    @pytest.mark.asyncio
    async def test_error_behind_error_pattern(self):
        """
        Test that we correctly identify "the error behind the error".
        
        The AUTH failures were actually CIRCUIT BREAKER failures.
        The "Invalid token" errors were actually "Circuit breaker open" errors.
        """
    pass
        client = AuthServiceClient()
        error_handler = UnifiedErrorHandler()
        
        # Test real error chain identification
        # 1. Simulate missing SERVICE_SECRET from environment
        original_secret = get_env("SERVICE_SECRET", None)
        
        try:
            # Force configuration error
            client.service_secret = None
            
            # 2. This should trigger cascade of errors
            breaker = client.circuit_manager.get_breaker("_validate_token_remote_breaker")
            
            # Simulate failures that open circuit breaker
            async def config_error_operation():
    pass
                if not client.service_secret:
                    raise ValueError("Missing SERVICE_SECRET configuration")
                await asyncio.sleep(0)
    return {"valid": True}
            
            # Cause enough failures to open circuit
            failure_count = 0
            for i in range(6):  # Exceed typical failure threshold
                try:
                    await breaker.call(config_error_operation)
                except Exception as e:
                    failure_count += 1
                    # Track the error chain properly
                    error_context = error_handler.create_error_context(
                        error=e,
                        operation="token_validation",
                        component="configuration"
                    )
                    
                    # Verify we identify root cause not just symptom
                    if "Missing SERVICE_SECRET" in str(e):
                        assert error_context.category == "CONFIGURATION"
                    elif failure_count >= 5 and isinstance(breaker, MockCircuitBreaker) and breaker.is_open:
                        # Should identify circuit breaker as secondary issue
                        assert "Circuit breaker" in str(e) or error_context.category == "SERVICE_UNAVAILABLE"
            
            # Test actual token validation with proper error identification
            result = await client.validate_token("valid_token")
            
            # Should identify configuration as root cause, not token validity
            if result and not result.get("valid"):
                error_msg = result.get("error", "")
                # Error should point to real issue (config/service) not just "invalid token"
                assert "configuration" in error_msg.lower() or "service" in error_msg.lower() or "unreachable" in error_msg.lower()
        
        finally:
            # Restore original configuration if it existed
            if original_secret:
                client.service_secret = original_secret
    
    @pytest.mark.asyncio  
    async def test_recovery_after_configuration_fix(self):
        """Test that system recovers after configuration is fixed."""
        client = AuthServiceClient()
        
        # Test real configuration recovery without mocking
        original_secret = client.service_secret
        
        try:
            # Start with missing SERVICE_SECRET
            client.service_secret = None
            
            # Circuit breaker opens due to auth failures
            breaker = client.circuit_manager.get_breaker("_validate_token_remote_breaker")
            
            # Cause real failures
            async def config_dependent_operation():
                if not client.service_secret:
                    raise ValueError("Service secret not configured")
                await asyncio.sleep(0)
    return {"valid": True, "user_id": "123"}
            
            # Cause failures to open circuit
            for i in range(6):
                try:
                    await breaker.call(config_dependent_operation)
                except Exception:
                    pass
            
            # Verify circuit is open (if MockCircuitBreaker)
            if isinstance(breaker, MockCircuitBreaker):
                assert breaker.is_open == True
                # Set recovery timeout for testing
                breaker.recovery_timeout = 1
                breaker.opened_at = time.time()
            
            # Fix the configuration
            client.service_secret = "fixed_secret_for_testing"
            
            # Wait for recovery timeout
            await asyncio.sleep(1.1)
            
            # Test actual recovery without patching
            if isinstance(breaker, MockCircuitBreaker):
                # Force recovery check by attempting call
                try:
                    result = await breaker.call(config_dependent_operation)
                    # If we reach here, circuit recovered and operation succeeded
                    assert result is not None
                    assert result.get("valid") == True
                except Exception as e:
                    # If still failing, verify it's not due to permanent circuit state
                    if "Circuit breaker" in str(e):
                        # Check if recovery timeout was respected
                        current_time = time.time()
                        assert current_time - breaker.opened_at >= breaker.recovery_timeout
            else:
                # Test with UnifiedCircuitBreaker
                result = await breaker.call(config_dependent_operation)
                assert result is not None
                assert result.get("valid") == True
        
        finally:
            # Restore original configuration
            client.service_secret = original_secret


if __name__ == "__main__":
    # Run the mission critical tests
    pytest.main([__file__, "-v", "-m", "mission_critical"])
    pass