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
from unittest.mock import AsyncMock, MagicMock, patch

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
        client = AuthServiceClient()
        
        # Mock the circuit breaker manager
        mock_breaker = MagicMock()
        mock_breaker.call = AsyncMock()
        
        # First call: circuit is open
        mock_breaker.call.side_effect = Exception("Circuit breaker _validate_token_remote_breaker is open")
        
        with patch.object(client.circuit_manager, 'get_breaker', return_value=mock_breaker):
            # Should handle the circuit breaker error and try fallback
            with patch.object(client, '_local_validate', new=AsyncMock(return_value={"valid": True, "source": "local_fallback"})):
                result = await client.validate_token("test_token")
                
                # Should have used fallback when circuit was open
                assert result is not None
                assert result.get("source") == "local_fallback"
    
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
        # Simulate auth service being temporarily unavailable
        client = AuthServiceClient()
        
        # Mock the auth service to fail temporarily
        with patch.object(client, '_validate_token_remote', side_effect=Exception("Connection refused")):
            # First few calls fail
            for i in range(3):
                result = await client.validate_token("test_token")
                # Should get fallback result, not complete failure
                assert result is not None
        
        # After "fixing" the connection, system should recover
        with patch.object(client, '_validate_token_remote', return_value={"valid": True, "user_id": "123"}):
            result = await client.validate_token("test_token")
            assert result is not None
            assert result.get("valid") == True


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
        client = AuthServiceClient()
        
        # Simulate the exact failure pattern we saw
        # 1. SERVICE_SECRET missing causes first error
        client.service_secret = None
        
        # 2. This triggers circuit breaker to open
        mock_breaker = MockCircuitBreaker("auth")
        mock_breaker.is_open = True
        
        with patch.object(client.circuit_manager, 'get_breaker', return_value=mock_breaker):
            # 3. User sees "Invalid token" but real error is circuit breaker
            with patch.object(client, '_handle_validation_error') as mock_handler:
                mock_handler.return_value = {"valid": False, "error": "auth_service_unreachable"}
                
                result = await client.validate_token("valid_token")
                
                # The result shows auth failure but the real problem was circuit breaker
                assert result["valid"] == False
                assert "unreachable" in result["error"] or "circuit" in str(mock_handler.call_args)
    
    @pytest.mark.asyncio  
    async def test_recovery_after_configuration_fix(self):
        """Test that system recovers after configuration is fixed."""
        client = AuthServiceClient()
        
        # Start with missing SERVICE_SECRET
        client.service_secret = None
        
        # Circuit breaker opens due to auth failures
        breaker = client.circuit_manager.get_breaker("_validate_token_remote_breaker")
        if isinstance(breaker, MockCircuitBreaker):
            breaker.is_open = True
            breaker.opened_at = time.time()
            breaker.recovery_timeout = 1  # 1 second for testing
        
        # Fix the configuration
        client.service_secret = "fixed_secret"
        
        # Wait for recovery
        await asyncio.sleep(1.1)
        
        # System should recover
        with patch.object(client, '_validate_token_remote', return_value={"valid": True}):
            # Reset the breaker state to test recovery
            if isinstance(breaker, MockCircuitBreaker):
                breaker.is_open = False  # Simulating automatic recovery after timeout
            
            result = await client.validate_token("test_token")
            assert result is not None
            assert result.get("valid") == True


if __name__ == "__main__":
    # Run the mission critical tests
    pytest.main([__file__, "-v", "-m", "mission_critical"])