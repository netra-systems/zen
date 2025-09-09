"""
Unit tests for circuit breaker implementations.

This module tests critical circuit breaker functionality including state transitions,
failure thresholds, recovery timeouts, and business logic validation.

Business Value: Circuit breakers protect system stability and prevent cascade failures,
ensuring reliable service for all customer segments (Free → Enterprise).
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerState,
    UnifiedCircuitBreakerManager,
    CircuitBreakerMetrics,
    unified_circuit_breaker
)
from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError


class TestUnifiedCircuitBreakerStateTransitions:
    """Test circuit breaker state transitions and business logic."""
    
    def test_circuit_breaker_initial_state_is_closed(self):
        """Test that circuit breaker starts in CLOSED state by default."""
        config = UnifiedCircuitConfig(name="test_breaker", failure_threshold=3)
        breaker = UnifiedCircuitBreaker(config)
        
        assert breaker.get_state() == UnifiedCircuitBreakerState.CLOSED
        assert breaker.can_execute() is True
        
        status = breaker.get_status()
        assert status["state"] == "closed"
        assert status["is_healthy"] is True
        assert status["can_execute"] is True
    
    def test_circuit_breaker_opens_after_failure_threshold(self):
        """Test that circuit opens after reaching failure threshold."""
        config = UnifiedCircuitConfig(name="test_breaker", failure_threshold=2)
        breaker = UnifiedCircuitBreaker(config)
        
        # Record failures up to threshold
        breaker.record_failure("TestError")
        assert breaker.get_state() == UnifiedCircuitBreakerState.CLOSED
        
        breaker.record_failure("TestError")  # This should open the circuit
        assert breaker.get_state() == UnifiedCircuitBreakerState.OPEN
        assert breaker.can_execute() is False
        
        status = breaker.get_status()
        assert status["state"] == "open" 
        assert status["is_healthy"] is False
        assert status["can_execute"] is False
        assert status["metrics"]["failure_count"] == 2
    
    def test_circuit_breaker_half_open_after_recovery_timeout(self):
        """Test circuit transitions to half-open after recovery timeout."""
        config = UnifiedCircuitConfig(
            name="test_breaker", 
            failure_threshold=1, 
            recovery_timeout=1  # 1 second for fast test
        )
        breaker = UnifiedCircuitBreaker(config)
        
        # Open the circuit
        breaker.record_failure("TestError")
        assert breaker.get_state() == UnifiedCircuitBreakerState.OPEN
        
        # Wait for recovery timeout to elapse
        time.sleep(1.1)  # Slightly more than recovery timeout
        
        # Circuit should allow execution (transitioning to half-open internally)
        assert breaker.can_execute() is True
    
    def test_circuit_breaker_closes_on_success_in_half_open(self):
        """Test circuit closes after successful execution in half-open state."""
        config = UnifiedCircuitConfig(name="test_breaker", failure_threshold=1)
        breaker = UnifiedCircuitBreaker(config)
        
        # Open the circuit
        breaker.record_failure("TestError")
        assert breaker.get_state() == UnifiedCircuitBreakerState.OPEN
        
        # Manually transition to half-open
        breaker.state = UnifiedCircuitBreakerState.HALF_OPEN
        
        # Record success should close the circuit
        breaker.record_success()
        assert breaker.get_state() == UnifiedCircuitBreakerState.CLOSED
        assert breaker.metrics.consecutive_failures == 0
    
    def test_circuit_breaker_adaptive_threshold_decreases_on_poor_performance(self):
        """Test adaptive threshold reduces failure tolerance when performance degrades."""
        config = UnifiedCircuitConfig(
            name="adaptive_breaker",
            failure_threshold=5,
            adaptive_threshold=True,
            slow_call_threshold=2.0
        )
        breaker = UnifiedCircuitBreaker(config)
        
        # Simulate slow responses that should trigger threshold adaptation
        for _ in range(10):
            breaker._response_times.append(3.0)  # Slow responses
        
        breaker._adapt_threshold_if_enabled()
        
        # Adaptive threshold should be reduced from original value
        assert breaker.metrics.adaptive_failure_threshold < config.failure_threshold
        assert breaker.metrics.adaptive_failure_threshold >= 1  # Minimum threshold


class TestCircuitBreakerMetrics:
    """Test circuit breaker metrics collection and reporting."""
    
    def test_metrics_initialization(self):
        """Test circuit breaker metrics are properly initialized."""
        config = UnifiedCircuitConfig(name="metrics_test", failure_threshold=3)
        breaker = UnifiedCircuitBreaker(config)
        
        metrics = breaker.metrics
        assert metrics.consecutive_failures == 0
        assert metrics.successful_calls == 0
        assert metrics.failed_calls == 0
        assert metrics.total_calls == 0
        assert metrics.adaptive_failure_threshold == 3
    
    def test_metrics_update_on_success(self):
        """Test metrics are correctly updated on successful operations."""
        config = UnifiedCircuitConfig(name="metrics_test")
        breaker = UnifiedCircuitBreaker(config)
        
        breaker.record_success()
        
        assert breaker.metrics.successful_calls == 1
        assert breaker.metrics.consecutive_failures == 0
        assert breaker.last_success_time is not None
    
    def test_metrics_update_on_failure(self):
        """Test metrics are correctly updated on failed operations."""
        config = UnifiedCircuitConfig(name="metrics_test")
        breaker = UnifiedCircuitBreaker(config)
        
        breaker.record_failure("TestError")
        
        assert breaker.metrics.failed_calls == 1
        assert breaker.metrics.consecutive_failures == 1
        assert breaker.metrics.last_failure_time is not None
    
    def test_status_includes_comprehensive_metrics(self):
        """Test status report includes all expected metrics."""
        config = UnifiedCircuitConfig(name="status_test", failure_threshold=2)
        breaker = UnifiedCircuitBreaker(config)
        
        # Generate some activity
        breaker.record_success()
        breaker.record_failure("Error1")
        
        status = breaker.get_status()
        metrics = status["metrics"]
        
        # Verify all expected metrics are present
        expected_metrics = [
            "failure_count", "success_count", "total_calls", "failure_threshold",
            "success_rate", "error_rate", "last_failure_time", "last_success_time"
        ]
        
        for metric in expected_metrics:
            assert metric in metrics, f"Missing metric: {metric}"
        
        assert metrics["success_rate"] == 1.0  # 1 success out of 1 total call
        assert metrics["error_rate"] == 0.0   # No errors out of 1 total call


class TestCircuitBreakerExecution:
    """Test circuit breaker execution patterns and error handling."""
    
    @pytest.mark.asyncio
    async def test_async_call_success(self):
        """Test successful async function call through circuit breaker."""
        config = UnifiedCircuitConfig(name="async_test")
        breaker = UnifiedCircuitBreaker(config)
        
        async def mock_async_function(x, y):
            return x + y
        
        result = await breaker.call(mock_async_function, 2, 3)
        
        assert result == 5
        assert breaker.metrics.successful_calls == 1
        assert breaker.metrics.total_calls == 1
    
    @pytest.mark.asyncio
    async def test_sync_call_success(self):
        """Test successful sync function call through circuit breaker."""
        config = UnifiedCircuitConfig(name="sync_test")
        breaker = UnifiedCircuitBreaker(config)
        
        def mock_sync_function(x, y):
            return x * y
        
        result = await breaker.call(mock_sync_function, 4, 5)
        
        assert result == 20
        assert breaker.metrics.successful_calls == 1
        assert breaker.metrics.total_calls == 1
    
    @pytest.mark.asyncio
    async def test_call_failure_propagates_exception(self):
        """Test that function failures propagate correctly and update metrics."""
        config = UnifiedCircuitConfig(name="failure_test")
        breaker = UnifiedCircuitBreaker(config)
        
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            await breaker.call(failing_function)
        
        assert breaker.metrics.failed_calls == 1
        assert breaker.metrics.consecutive_failures == 1
    
    @pytest.mark.asyncio
    async def test_call_blocked_when_circuit_open(self):
        """Test that calls are blocked when circuit is in OPEN state."""
        config = UnifiedCircuitConfig(name="blocked_test", failure_threshold=1)
        breaker = UnifiedCircuitBreaker(config)
        
        # Open the circuit
        breaker.record_failure("TestError")
        assert breaker.get_state() == UnifiedCircuitBreakerState.OPEN
        
        def dummy_function():
            return "should not execute"
        
        with pytest.raises(CircuitBreakerOpenError, match="Circuit breaker blocked_test is OPEN"):
            await breaker.call(dummy_function)
    
    @pytest.mark.asyncio
    async def test_slow_call_tracking(self):
        """Test that slow calls are properly tracked for adaptive behavior."""
        config = UnifiedCircuitConfig(
            name="slow_test",
            slow_call_threshold=1.0  # 1 second threshold
        )
        breaker = UnifiedCircuitBreaker(config)
        
        async def slow_function():
            await asyncio.sleep(1.5)  # Simulate slow operation
            return "completed"
        
        result = await breaker.call(slow_function)
        
        assert result == "completed"
        assert breaker.metrics.slow_requests == 1
        assert breaker.metrics.average_response_time >= 1.5


class TestCircuitBreakerManager:
    """Test circuit breaker manager functionality."""
    
    def test_manager_creates_breakers_with_default_config(self):
        """Test manager creates circuit breakers with default configuration."""
        manager = UnifiedCircuitBreakerManager()
        
        breaker = manager.get_breaker("test_service")
        
        assert breaker is not None
        assert breaker.config.name == "default"  # Default config name
        assert "test_service" in manager.breakers
    
    def test_manager_creates_breakers_with_custom_config(self):
        """Test manager creates circuit breakers with custom configuration."""
        manager = UnifiedCircuitBreakerManager()
        custom_config = UnifiedCircuitConfig(
            name="custom_breaker",
            failure_threshold=10,
            recovery_timeout=30
        )
        
        breaker = manager.create_breaker("custom_service", custom_config)
        
        assert breaker is not None
        assert breaker.config.name == "custom_breaker"
        assert breaker.config.failure_threshold == 10
        assert breaker.config.recovery_timeout == 30
    
    def test_manager_returns_same_instance_for_same_name(self):
        """Test manager returns the same breaker instance for the same name."""
        manager = UnifiedCircuitBreakerManager()
        
        breaker1 = manager.get_breaker("shared_service")
        breaker2 = manager.get_breaker("shared_service")
        
        assert breaker1 is breaker2


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator functionality."""
    
    @pytest.mark.asyncio
    async def test_decorator_protects_async_function(self):
        """Test decorator provides circuit breaker protection for async functions."""
        config = UnifiedCircuitConfig(name="decorated_async", failure_threshold=2)
        
        @unified_circuit_breaker("decorated_async", config)
        async def protected_async_function(x):
            if x < 0:
                raise ValueError("Negative value")
            return x * 2
        
        # Should work normally
        result = await protected_async_function(5)
        assert result == 10
        
        # Should fail and record failure
        with pytest.raises(ValueError, match="Negative value"):
            await protected_async_function(-1)
        
        # Second failure should open circuit
        with pytest.raises(ValueError, match="Negative value"):
            await protected_async_function(-2)
        
        # Third call should be blocked by circuit breaker
        with pytest.raises(CircuitBreakerOpenError, match="Circuit breaker decorated_async is open"):
            await protected_async_function(3)
    
    def test_decorator_protects_sync_function(self):
        """Test decorator provides circuit breaker protection for sync functions.""" 
        config = UnifiedCircuitConfig(name="decorated_sync", failure_threshold=1)
        
        @unified_circuit_breaker("decorated_sync", config)
        def protected_sync_function(x):
            if x == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            return 10 / x
        
        # Should work normally
        result = protected_sync_function(2)
        assert result == 5.0
        
        # Should fail and open circuit (threshold=1)
        with pytest.raises(ZeroDivisionError, match="Cannot divide by zero"):
            protected_sync_function(0)
        
        # Second call should be blocked
        with pytest.raises(CircuitBreakerOpenError, match="Circuit breaker decorated_sync is open"):
            protected_sync_function(5)


class TestCircuitBreakerEdgeCases:
    """Test circuit breaker edge cases and error conditions."""
    
    def test_zero_failure_threshold_always_open(self):
        """Test circuit breaker behavior with zero failure threshold."""
        config = UnifiedCircuitConfig(name="zero_threshold", failure_threshold=0)
        breaker = UnifiedCircuitBreaker(config)
        
        # Even one failure should open circuit immediately
        breaker.record_failure("FirstError")
        assert breaker.get_state() == UnifiedCircuitBreakerState.OPEN
    
    def test_negative_recovery_timeout_immediate_recovery(self):
        """Test circuit breaker with immediate recovery (zero timeout)."""
        config = UnifiedCircuitConfig(
            name="immediate_recovery",
            failure_threshold=1,
            recovery_timeout=0  # Immediate recovery
        )
        breaker = UnifiedCircuitBreaker(config)
        
        # Open circuit
        breaker.record_failure("TestError")
        assert breaker.get_state() == UnifiedCircuitBreakerState.OPEN
        
        # Should be able to execute immediately due to zero timeout
        assert breaker.can_execute() is True
    
    @pytest.mark.asyncio
    async def test_force_open_and_reset_operations(self):
        """Test manual circuit breaker control operations."""
        config = UnifiedCircuitConfig(name="manual_control")
        breaker = UnifiedCircuitBreaker(config)
        
        assert breaker.get_state() == UnifiedCircuitBreakerState.CLOSED
        
        # Force open
        await breaker.force_open()
        assert breaker.get_state() == UnifiedCircuitBreakerState.OPEN
        assert breaker.metrics.last_failure_time is not None
        
        # Reset to closed
        await breaker.reset()
        assert breaker.get_state() == UnifiedCircuitBreakerState.CLOSED
        assert breaker.metrics.consecutive_failures == 0
    
    def test_health_checker_integration(self):
        """Test circuit breaker integration with health checker."""
        mock_health_checker = Mock()
        mock_health_result = Mock()
        mock_health_result.health_score = 0.5  # Poor health
        mock_health_checker.check_health = AsyncMock(return_value=mock_health_result)
        
        config = UnifiedCircuitConfig(
            name="health_integrated",
            adaptive_threshold=True,
            failure_threshold=5
        )
        breaker = UnifiedCircuitBreaker(config, health_checker=mock_health_checker)
        
        # Set up poor health condition
        breaker.last_health_check = mock_health_result
        breaker._adapt_threshold_if_enabled()
        
        # Threshold should be reduced due to poor health
        assert breaker.metrics.adaptive_failure_threshold < config.failure_threshold
    
    def test_cleanup_stops_health_check_task(self):
        """Test that cleanup properly stops background health check task."""
        mock_health_checker = Mock()
        config = UnifiedCircuitConfig(name="cleanup_test")
        breaker = UnifiedCircuitBreaker(config, health_checker=mock_health_checker)
        
        # Mock the health check task
        mock_task = Mock()
        breaker._health_check_task = mock_task
        
        breaker.cleanup()
        
        mock_task.cancel.assert_called_once()