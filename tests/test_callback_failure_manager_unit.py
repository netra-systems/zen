"""Unit tests for callback failure manager without full app dependencies."""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock

# Direct imports to avoid app configuration issues
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'websocket'))

from reconnection_types import CallbackType, CallbackCriticality, CallbackFailure, CallbackCircuitBreaker
from reconnection_exceptions import CriticalCallbackFailure, CallbackCircuitBreakerOpen, StateNotificationFailure
from callback_failure_manager import CallbackFailureManager


class TestCallbackFailureManager:
    """Test the callback failure manager directly."""
    
    @pytest.fixture
    def manager(self):
        """Create callback failure manager for testing."""
        return CallbackFailureManager("test-conn")
    
    def test_default_criticality_mapping(self, manager):
        """Test default callback criticality mapping."""
        assert manager.criticality_map[CallbackType.STATE_CHANGE] == CallbackCriticality.CRITICAL
        assert manager.criticality_map[CallbackType.CONNECT] == CallbackCriticality.IMPORTANT
        assert manager.criticality_map[CallbackType.DISCONNECT] == CallbackCriticality.NON_CRITICAL
    
    def test_circuit_breaker_initialization(self, manager):
        """Test that circuit breakers are properly initialized."""
        for callback_type in CallbackType:
            assert callback_type in manager.circuit_breakers
            breaker = manager.circuit_breakers[callback_type]
            assert isinstance(breaker, CallbackCircuitBreaker)
            assert breaker.is_open is False
            assert breaker.failure_count == 0
    
    def test_update_criticality(self, manager):
        """Test updating callback criticality."""
        manager.set_callback_criticality(CallbackType.CONNECT, CallbackCriticality.CRITICAL)
        assert manager.criticality_map[CallbackType.CONNECT] == CallbackCriticality.CRITICAL
    
    @pytest.mark.asyncio
    async def test_successful_callback_execution(self, manager):
        """Test successful callback execution."""
        callback = AsyncMock()
        await manager.execute_callback_safely(
            CallbackType.CONNECT, callback, "arg1", kwarg1="value1"
        )
        callback.assert_called_once_with("arg1", kwarg1="value1")
    
    @pytest.mark.asyncio
    async def test_critical_callback_failure_propagation(self, manager):
        """Test that critical callback failures are propagated."""
        failing_callback = AsyncMock(side_effect=Exception("Critical failure"))
        
        with pytest.raises(StateNotificationFailure):
            await manager.execute_callback_safely(
                CallbackType.STATE_CHANGE, failing_callback
            )
    
    @pytest.mark.asyncio
    async def test_important_callback_failure_logging(self, manager):
        """Test that important callback failures are logged but don't raise."""
        failing_callback = AsyncMock(side_effect=Exception("Important failure"))
        
        # Should not raise exception for important callbacks
        await manager.execute_callback_safely(
            CallbackType.CONNECT, failing_callback
        )
        
        # Should have recorded the failure
        assert len(manager.failure_history) == 1
        failure = manager.failure_history[0]
        assert failure.callback_type == CallbackType.CONNECT
        assert failure.criticality == CallbackCriticality.IMPORTANT
    
    @pytest.mark.asyncio
    async def test_non_critical_callback_failure_logging(self, manager):
        """Test that non-critical callback failures are logged but don't raise."""
        failing_callback = AsyncMock(side_effect=Exception("Non-critical failure"))
        
        # Should not raise exception for non-critical callbacks
        await manager.execute_callback_safely(
            CallbackType.DISCONNECT, failing_callback
        )
        
        # Should have recorded the failure
        assert len(manager.failure_history) == 1
        failure = manager.failure_history[0]
        assert failure.callback_type == CallbackType.DISCONNECT
        assert failure.criticality == CallbackCriticality.NON_CRITICAL
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, manager):
        """Test that circuit breaker opens after repeated failures."""
        failing_callback = AsyncMock(side_effect=Exception("Always fails"))
        
        # Set connect as non-critical to avoid exceptions
        manager.set_callback_criticality(CallbackType.CONNECT, CallbackCriticality.NON_CRITICAL)
        
        # Execute failures up to threshold (default 3)
        for i in range(3):
            await manager.execute_callback_safely(CallbackType.CONNECT, failing_callback)
        
        # Circuit breaker should be open now
        breaker = manager.circuit_breakers[CallbackType.CONNECT]
        assert breaker.is_open is True
        assert breaker.failure_count == 3
        
        # Next attempt should raise circuit breaker exception
        with pytest.raises(CallbackCircuitBreakerOpen):
            await manager.execute_callback_safely(CallbackType.CONNECT, failing_callback)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_reset_on_success(self, manager):
        """Test that circuit breaker resets on successful execution."""
        failing_callback = AsyncMock(side_effect=Exception("Fails initially"))
        success_callback = AsyncMock()
        
        # Set as non-critical
        manager.set_callback_criticality(CallbackType.CONNECT, CallbackCriticality.NON_CRITICAL)
        
        # Trigger circuit breaker
        for i in range(3):
            await manager.execute_callback_safely(CallbackType.CONNECT, failing_callback)
        
        breaker = manager.circuit_breakers[CallbackType.CONNECT]
        assert breaker.is_open is True
        
        # Manually reset to simulate timeout (in real system this happens automatically)
        breaker.is_open = False
        
        # Success should reset the breaker completely
        await manager.execute_callback_safely(CallbackType.CONNECT, success_callback)
        
        assert breaker.is_open is False
        assert breaker.failure_count == 0
        assert len(breaker.recent_failures) == 0
    
    def test_failure_metrics(self, manager):
        """Test failure metrics collection."""
        # Add some test failures
        failure1 = CallbackFailure(
            callback_type=CallbackType.CONNECT,
            timestamp=datetime.now(timezone.utc),
            error_message="Test error 1",
            criticality=CallbackCriticality.IMPORTANT
        )
        failure2 = CallbackFailure(
            callback_type=CallbackType.STATE_CHANGE,
            timestamp=datetime.now(timezone.utc),
            error_message="Test error 2",
            criticality=CallbackCriticality.CRITICAL
        )
        
        manager.failure_history = [failure1, failure2]
        
        # Update circuit breaker for testing
        manager.circuit_breakers[CallbackType.CONNECT].failure_count = 1
        manager.circuit_breakers[CallbackType.STATE_CHANGE].failure_count = 1
        
        metrics = manager.get_failure_metrics()
        
        assert metrics['total_failures'] == 2
        assert metrics['critical_failures'] == 1
        assert metrics['circuit_breakers'][CallbackType.CONNECT.value]['failure_count'] == 1
        assert metrics['circuit_breakers'][CallbackType.STATE_CHANGE.value]['failure_count'] == 1
    
    def test_failure_history_cleanup(self, manager):
        """Test that failure history is cleaned up when it gets too long."""
        # Create many failures to trigger cleanup
        for i in range(110):  # More than the 100 limit
            failure = CallbackFailure(
                callback_type=CallbackType.CONNECT,
                timestamp=datetime.now(timezone.utc),
                error_message=f"Test error {i}",
                criticality=CallbackCriticality.NON_CRITICAL
            )
            manager.failure_history.append(failure)
        
        # Trigger cleanup by recording one more failure
        manager._cleanup_old_failures()
        
        # Should be reduced to 50 most recent
        assert len(manager.failure_history) == 50


class TestCircuitBreakerLogic:
    """Test circuit breaker logic directly."""
    
    @pytest.fixture
    def manager(self):
        """Create manager with custom circuit breaker settings."""
        manager = CallbackFailureManager("test-conn")
        # Set low threshold for testing
        for breaker in manager.circuit_breakers.values():
            breaker.failure_threshold = 2
            breaker.reset_timeout_ms = 1000  # 1 second
        return manager
    
    def test_circuit_breaker_timeout_logic(self, manager):
        """Test circuit breaker timeout reset logic."""
        breaker = manager.circuit_breakers[CallbackType.CONNECT]
        
        # Set failure time to past
        past_time = datetime.now(timezone.utc)
        past_time = past_time.replace(second=past_time.second - 2)  # 2 seconds ago
        breaker.last_failure_time = past_time
        breaker.is_open = True
        
        # Should be ready to reset due to timeout
        assert manager._should_reset_circuit_breaker(breaker) is True
        
        # Set recent failure time
        breaker.last_failure_time = datetime.now(timezone.utc)
        
        # Should not be ready to reset
        assert manager._should_reset_circuit_breaker(breaker) is False
    
    def test_elapsed_time_calculation(self, manager):
        """Test elapsed time calculation."""
        start_time = datetime.now(timezone.utc)
        # Simulate some elapsed time
        import time
        time.sleep(0.01)  # 10ms
        
        elapsed = manager._calculate_elapsed_ms(start_time)
        assert elapsed > 5  # Should be at least a few milliseconds
        assert elapsed < 100  # But not too much


if __name__ == "__main__":
    pytest.main([__file__, "-v"])