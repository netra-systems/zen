"""Simplified Circuit Breaker E2E Tests

Basic validation tests for circuit breaker functionality using real UnifiedCircuitBreaker.
Complies with CLAUDE.md requirements:
- Uses IsolatedEnvironment for environment management
- Uses absolute imports only
- Tests real services (no mocks)
- Focuses on basic circuit breaker flows
"""

import pytest
import asyncio
from typing import Dict, Any

from test_framework.environment_isolation import isolated_test_env
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerState,
    CircuitBreakerOpenError
)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_circuit_breaker_basic_functionality(isolated_test_env):
    """Test basic circuit breaker functionality with real UnifiedCircuitBreaker."""
    # Verify test environment is properly isolated
    assert isolated_test_env.get("TESTING") == "1", "Test should run in isolated environment"
    assert isolated_test_env.get("NETRA_ENV") == "testing", "Should be in testing environment"
    
    # Create real circuit breaker
    config = UnifiedCircuitConfig(
        name="test_basic",
        failure_threshold=3,
        recovery_timeout=1.0
    )
    circuit_breaker = UnifiedCircuitBreaker(config)
    
    # Test initial state
    assert circuit_breaker.is_closed
    assert not circuit_breaker.is_open
    assert not circuit_breaker.is_half_open
    
    # Test successful execution
    async def successful_operation():
        return "success"
    
    result = await circuit_breaker.call(successful_operation)
    assert result == "success"
    assert circuit_breaker.metrics.successful_calls == 1
    assert circuit_breaker.metrics.total_calls == 1


@pytest.mark.asyncio
@pytest.mark.e2e 
async def test_circuit_breaker_state_transitions(isolated_test_env):
    """Test circuit breaker state transitions from CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
    # Verify test environment is properly isolated
    assert isolated_test_env.get("TESTING") == "1", "Test should run in isolated environment"
    
    # Create circuit breaker with low failure threshold for testing
    config = UnifiedCircuitConfig(
        name="test_transitions",
        failure_threshold=2,
        recovery_timeout=0.5,
        success_threshold=2,
        exponential_backoff=False  # Use simple timeout for testing
    )
    circuit_breaker = UnifiedCircuitBreaker(config)
    
    # Start in CLOSED state
    assert circuit_breaker.internal_state == UnifiedCircuitBreakerState.CLOSED
    
    # Cause failures to transition to OPEN
    async def failing_operation():
        raise Exception("Test failure")
    
    # Record failures to open circuit
    for _ in range(2):
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_operation)
    
    # Circuit should now be OPEN
    assert circuit_breaker.internal_state == UnifiedCircuitBreakerState.OPEN
    assert circuit_breaker.is_open
    
    # Should reject calls when open
    with pytest.raises(CircuitBreakerOpenError):
        await circuit_breaker.call(failing_operation)
    
    # Wait for recovery timeout
    await asyncio.sleep(0.6)
    
    # After timeout, should allow execution (HALF_OPEN)
    async def recovery_operation():
        return "recovered"
    
    # Circuit should still be OPEN until we try to call
    assert circuit_breaker.internal_state == UnifiedCircuitBreakerState.OPEN
    
    # The first call after timeout should transition to HALF_OPEN and succeed
    result = await circuit_breaker.call(recovery_operation)
    assert result == "recovered"
    assert circuit_breaker.internal_state == UnifiedCircuitBreakerState.HALF_OPEN
    
    # Another success should close the circuit
    await circuit_breaker.call(recovery_operation)
    assert circuit_breaker.internal_state == UnifiedCircuitBreakerState.CLOSED


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_circuit_breaker_metrics_collection(isolated_test_env):
    """Test circuit breaker metrics collection with real operations."""
    # Verify test environment is properly isolated
    assert isolated_test_env.get("TESTING") == "1", "Test should run in isolated environment"
    
    # Create circuit breaker for metrics testing
    config = UnifiedCircuitConfig(
        name="test_metrics",
        failure_threshold=3,
        recovery_timeout=1.0
    )
    circuit_breaker = UnifiedCircuitBreaker(config)
    
    # Execute successful operations
    async def success_operation():
        return "success"
    
    for _ in range(5):
        await circuit_breaker.call(success_operation)
    
    # Execute some failures
    async def failure_operation():
        raise ValueError("Test failure")
    
    for _ in range(2):
        with pytest.raises(ValueError):
            await circuit_breaker.call(failure_operation)
    
    # Check metrics
    metrics = circuit_breaker.metrics
    assert metrics.total_calls == 7
    assert metrics.successful_calls == 5
    assert metrics.failed_calls == 2
    assert metrics.successful_calls > metrics.failed_calls
    
    # Check status includes metrics
    status = circuit_breaker.get_status()
    assert "metrics" in status
    assert status["metrics"]["total_calls"] == 7
    assert status["metrics"]["successful_calls"] == 5
    assert status["metrics"]["failed_calls"] == 2
    assert "failure_types" in status["metrics"]
    assert "ValueError" in status["metrics"]["failure_types"]


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_circuit_breaker_error_handling(isolated_test_env):
    """Test circuit breaker error handling with real timeouts and exceptions."""
    # Verify test environment is properly isolated
    assert isolated_test_env.get("TESTING") == "1", "Test should run in isolated environment"
    
    # Create circuit breaker for error handling testing
    config = UnifiedCircuitConfig(
        name="test_errors",
        failure_threshold=5,
        recovery_timeout=1.0,
        timeout_seconds=0.1,  # Short timeout for testing
        exponential_backoff=False  # Use simple timeout for testing
    )
    circuit_breaker = UnifiedCircuitBreaker(config)
    
    # Test timeout error handling
    async def timeout_operation():
        await asyncio.sleep(1.0)  # Will timeout
        return "should not reach"
    
    with pytest.raises(asyncio.TimeoutError):
        await circuit_breaker.call(timeout_operation)
    
    # Test connection error handling
    async def connection_error_operation():
        raise ConnectionError("Test connection error")
    
    with pytest.raises(ConnectionError):
        await circuit_breaker.call(connection_error_operation)
    
    # Test service unavailable error handling
    async def service_error_operation():
        raise Exception("Service unavailable")
    
    with pytest.raises(Exception):
        await circuit_breaker.call(service_error_operation)
    
    # We don't need additional failures since threshold is 5
    # The important thing is that various error types are tracked
    
    # Check that different error types are tracked
    metrics = circuit_breaker.metrics
    assert metrics.timeouts >= 1  # From timeout operation
    assert metrics.failed_calls >= 3  # From all failures
    assert "ConnectionError" in metrics.failure_types
    assert "Exception" in metrics.failure_types
    
    # Circuit might be open now due to accumulation of failures
    # The important thing is that errors were properly handled and tracked
    assert metrics.total_calls >= 3
    assert len(metrics.failure_types) >= 2


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_circuit_breaker_recovery(isolated_test_env):
    """Test circuit breaker recovery process with real timeout-based recovery."""
    # Verify test environment is properly isolated
    assert isolated_test_env.get("TESTING") == "1", "Test should run in isolated environment"
    
    # Create circuit breaker for recovery testing
    config = UnifiedCircuitConfig(
        name="test_recovery",
        failure_threshold=2,
        recovery_timeout=0.3,
        success_threshold=2,
        half_open_max_calls=3,
        exponential_backoff=False  # Use simple timeout for testing
    )
    circuit_breaker = UnifiedCircuitBreaker(config)
    
    # Step 1: Cause failures to open circuit
    async def failing_operation():
        raise RuntimeError("Recovery test failure")
    
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_operation)
    
    # Circuit should be open
    assert circuit_breaker.is_open
    recovery_start_state = circuit_breaker.internal_state
    assert recovery_start_state == UnifiedCircuitBreakerState.OPEN
    
    # Step 2: Wait for recovery timeout (health_check equivalent)
    await asyncio.sleep(0.4)
    
    # Step 3: Gradual traffic - circuit allows limited calls in HALF_OPEN
    async def recovery_operation():
        return "recovery_success"
    
    # Circuit should still be OPEN until we try to execute
    assert circuit_breaker.is_open
    
    # First recovery call should work and transition to HALF_OPEN
    result1 = await circuit_breaker.call(recovery_operation)
    assert result1 == "recovery_success"
    assert circuit_breaker.is_half_open
    
    # Step 4: Full recovery - enough successes should close circuit
    result2 = await circuit_breaker.call(recovery_operation)
    assert result2 == "recovery_success"
    
    # After success threshold (2), should be fully recovered (CLOSED)
    assert circuit_breaker.is_closed
    
    # Verify recovery is complete
    status = circuit_breaker.get_status()
    assert status["is_healthy"] is True
    assert status["state"] == "closed"
    
    # Should handle normal operations after recovery
    final_result = await circuit_breaker.call(recovery_operation)
    assert final_result == "recovery_success"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_circuit_breaker_threshold_configuration(isolated_test_env):
    """Test circuit breaker threshold configuration and validation."""
    # Verify test environment is properly isolated
    assert isolated_test_env.get("TESTING") == "1", "Test should run in isolated environment"
    
    # Test custom configuration
    config = UnifiedCircuitConfig(
        name="test_config",
        failure_threshold=3,
        success_threshold=2,
        recovery_timeout=30.0,
        timeout_seconds=60.0,
        sliding_window_size=15,
        error_rate_threshold=0.6,
        adaptive_threshold=True,
        slow_call_threshold=10.0
    )
    
    circuit_breaker = UnifiedCircuitBreaker(config)
    
    # Verify configuration was applied
    assert circuit_breaker.config.failure_threshold == 3
    assert circuit_breaker.config.success_threshold == 2
    assert circuit_breaker.config.recovery_timeout == 30.0
    assert circuit_breaker.config.timeout_seconds == 60.0
    assert circuit_breaker.config.sliding_window_size == 15
    assert circuit_breaker.config.error_rate_threshold == 0.6
    assert circuit_breaker.config.adaptive_threshold is True
    assert circuit_breaker.config.slow_call_threshold == 10.0
    
    # Test configuration validation
    with pytest.raises(ValueError, match="failure_threshold must be positive"):
        UnifiedCircuitConfig(name="invalid", failure_threshold=0)
    
    with pytest.raises(ValueError, match="error_rate_threshold must be between 0 and 1"):
        UnifiedCircuitConfig(name="invalid", error_rate_threshold=1.5)
    
    with pytest.raises(ValueError, match="recovery_timeout must be positive"):
        UnifiedCircuitConfig(name="invalid", recovery_timeout=-1.0)
    
    # Test that configuration affects behavior
    async def test_operation():
        return "test"
    
    async def slow_operation():
        await asyncio.sleep(0.02)  # Simulate slow operation
        return "slow"
    
    # Execute operations and verify metrics tracking
    await circuit_breaker.call(test_operation)
    await circuit_breaker.call(slow_operation)
    
    # Verify status includes configuration
    status = circuit_breaker.get_status()
    assert "config" in status
    config_dict = status["config"]
    assert config_dict["failure_threshold"] == 3
    assert config_dict["recovery_timeout"] == 30.0
    assert config_dict["timeout_seconds"] == 60.0
    assert config_dict["adaptive_threshold"] is True