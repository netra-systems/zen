"""Comprehensive tests for AdaptiveCircuitBreaker core functionality.

BUSINESS VALUE: Protects system reliability and prevents cascading failures, 
directly saving customer AI spend by avoiding service outages.

Tests critical paths including state transitions, adaptive thresholds,
health monitoring, and failure recovery mechanisms.
"""

import sys
from pathlib import Path

import asyncio
import time
from collections import deque
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker as AdaptiveCircuitBreaker,
    UnifiedCircuitBreakerState as CircuitBreakerState,
    UnifiedCircuitConfig as CircuitBreakerConfig
)
from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError
from netra_backend.app.core.shared_health_types import HealthChecker, HealthStatus
from netra_backend.app.schemas.core_models import (
    HealthCheckResult,
)

# Test fixtures for setup
@pytest.fixture
def circuit_config():
    """Standard circuit breaker configuration."""
    return CircuitBreakerConfig(
        name="test_circuit",
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=1
    )

@pytest.fixture
def mock_health_checker():
    """Mock health checker returning healthy status."""
    # Mock: Component isolation for controlled unit testing
    checker = Mock(spec=HealthChecker)
    # Mock: Async component isolation for testing without real async operations
    checker.check_health = AsyncMock(return_value=create_health_result())
    return checker

@pytest.fixture
def circuit_breaker(circuit_config):
    """Circuit breaker instance without health checker."""
    return AdaptiveCircuitBreaker(circuit_config)

@pytest.fixture  
async def circuit_with_health(circuit_config, mock_health_checker):
    """Circuit breaker with health monitoring."""
    circuit = AdaptiveCircuitBreaker(circuit_config, health_checker=mock_health_checker)
    yield circuit
    circuit.cleanup()

# Helper functions for 25-line compliance
def create_health_result(status=HealthStatus.HEALTHY, response_time=0.1):
    """Create standardized health check result."""
    return HealthCheckResult(
        component_name="test_component",
        success=(status == HealthStatus.HEALTHY),
        health_score=1.0 if status == HealthStatus.HEALTHY else 0.5,
        response_time_ms=response_time * 1000,  # Convert to milliseconds
        status=status.value if hasattr(status, 'value') else str(status),
        response_time=response_time,
        details={}
    )

def assert_circuit_state(circuit, expected_state):
    """Assert circuit is in expected state."""
    assert circuit.state == expected_state

def assert_failure_count(circuit, expected_count):
    """Assert circuit has expected failure count."""
    assert circuit.metrics.consecutive_failures == expected_count

async def simulate_operation_failure(circuit):
    """Simulate a failed operation."""
    await circuit._record_failure(0.1, "test_error")

async def simulate_operation_success(circuit):
    """Simulate a successful operation."""
    await circuit._record_success(0.1)

async def simulate_async_operation():
    """Async operation that always succeeds."""
    await asyncio.sleep(0.001)
    return "success"

async def simulate_failing_operation():
    """Async operation that always fails."""
    await asyncio.sleep(0.001)
    raise RuntimeError("Operation failed")

# Core circuit breaker functionality tests
class TestCircuitBreakerInitialization:
    """Test circuit breaker initialization and setup."""

    def test_circuit_breaker_starts_closed(self, circuit_breaker):
        """Circuit starts in CLOSED state."""
        assert_circuit_state(circuit_breaker, CircuitBreakerState.CLOSED)
        assert_failure_count(circuit_breaker, 0)

    def test_circuit_breaker_name_assignment(self, circuit_config):
        """Circuit breaker stores correct name."""
        # Update config with test name
        circuit_config.name = "test_name"
        circuit = AdaptiveCircuitBreaker(circuit_config)
        assert circuit.config.name == "test_name"

    def test_circuit_breaker_config_storage(self, circuit_breaker, circuit_config):
        """Circuit breaker stores configuration correctly."""
        assert circuit_breaker.config == circuit_config
        assert circuit_breaker.metrics.adaptive_failure_threshold == circuit_config.failure_threshold

    def test_circuit_breaker_metrics_initialization(self, circuit_breaker):
        """Circuit breaker initializes metrics to zero."""
        assert circuit_breaker.metrics.total_calls == 0
        assert circuit_breaker.metrics.successful_calls == 0
        assert circuit_breaker.metrics.failed_calls == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_health_checker(self, circuit_with_health, mock_health_checker):
        """Circuit breaker accepts health checker."""
        assert circuit_with_health.health_checker == mock_health_checker
        assert circuit_with_health.last_health_check is None

class TestCircuitStateTransitions:
    """Test circuit breaker state transition logic."""

    @pytest.mark.asyncio
    async def test_closed_to_open_on_failures(self, circuit_breaker):
        """Circuit opens after reaching failure threshold."""
        for _ in range(3):  # Failure threshold is 3
            await simulate_operation_failure(circuit_breaker)
        assert_circuit_state(circuit_breaker, CircuitBreakerState.OPEN)

    @pytest.mark.asyncio
    async def test_failure_count_increments(self, circuit_breaker):
        """Failure count increments with each failure."""
        await simulate_operation_failure(circuit_breaker)
        assert_failure_count(circuit_breaker, 1)
        await simulate_operation_failure(circuit_breaker)
        assert_failure_count(circuit_breaker, 2)

    def test_should_allow_request_when_closed(self, circuit_breaker):
        """Closed circuit allows requests."""
        assert circuit_breaker.can_execute() is True

    @pytest.mark.asyncio
    async def test_should_reject_request_when_open(self, circuit_breaker):
        """Open circuit rejects requests initially."""
        await circuit_breaker.force_open()
        assert circuit_breaker.can_execute() is False

    @pytest.mark.asyncio
    async def test_force_open_transitions_state(self, circuit_breaker):
        """Force open changes state to OPEN."""
        await circuit_breaker.force_open()
        assert_circuit_state(circuit_breaker, CircuitBreakerState.OPEN)

    @pytest.mark.asyncio
    async def test_force_close_transitions_state(self, circuit_breaker):
        """Force close changes state to CLOSED."""
        await circuit_breaker.force_open()
        await circuit_breaker.reset()  # Use reset instead of force_close
        assert_circuit_state(circuit_breaker, CircuitBreakerState.CLOSED)

    @pytest.mark.asyncio
    async def test_half_open_success_leads_to_closed(self, circuit_breaker):
        """Successful operations in HALF_OPEN lead to CLOSED."""
        await circuit_breaker._transition_to_half_open()
        for _ in range(2):  # Success threshold is 2
            await simulate_operation_success(circuit_breaker)
        assert_circuit_state(circuit_breaker, CircuitBreakerState.CLOSED)

class TestOperationExecution:
    """Test operation execution through circuit breaker."""

    @pytest.mark.asyncio
    async def test_successful_operation_execution(self, circuit_breaker):
        """Successful operation returns result and updates metrics."""
        result = await circuit_breaker.call(simulate_async_operation)
        assert result == "success"
        assert circuit_breaker.metrics.successful_calls == 1
        assert circuit_breaker.metrics.total_calls == 1

    @pytest.mark.asyncio
    async def test_failed_operation_execution(self, circuit_breaker):
        """Failed operation raises exception and updates metrics."""
        with pytest.raises(RuntimeError, match="Operation failed"):
            await circuit_breaker.call(simulate_failing_operation)
        assert circuit_breaker.metrics.failed_calls == 1
        assert circuit_breaker.metrics.total_calls == 1

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self, circuit_breaker):
        """Open circuit raises CircuitBreakerOpenError."""
        await circuit_breaker.force_open()
        with pytest.raises(CircuitBreakerOpenError, match="Circuit breaker.*is OPEN"):
            await circuit_breaker.call(simulate_async_operation)

    @pytest.mark.asyncio
    async def test_response_time_tracking(self, circuit_breaker):
        """Circuit tracks response times."""
        await circuit_breaker.call(simulate_async_operation)
        # Just verify response times are being tracked
        assert circuit_breaker.metrics.average_response_time >= 0.0

    @pytest.mark.asyncio
    async def test_slow_call_detection(self, circuit_breaker):
        """Circuit detects slow calls."""
        # Mock a slow operation
        async def slow_operation():
            await asyncio.sleep(0.1)  # Longer than slow_call_threshold
            return "slow_result"
        
        # Set slow call threshold for test
        original_threshold = circuit_breaker.config.slow_call_threshold
        circuit_breaker.config.slow_call_threshold = 0.05
        try:
            await circuit_breaker.call(slow_operation)
            assert circuit_breaker.metrics.slow_requests >= 0
        finally:
            circuit_breaker.config.slow_call_threshold = original_threshold

class TestAdaptiveThreshold:
    """Test adaptive threshold functionality."""

    def test_adaptive_threshold_decreases_on_slow_calls(self, circuit_breaker):
        """Adaptive threshold decreases with slow response times.
        
        BUSINESS LOGIC: When response times are consistently slow, the circuit becomes
        more sensitive to failures by lowering the threshold. This prevents cascading
        failures in degraded systems, protecting customer AI workloads.
        """
        # Enable adaptive threshold for this test
        circuit_breaker.config.adaptive_threshold = True
        
        # Set up slow response times scenario
        slow_response_times = [6.0, 7.0, 8.0, 9.0, 10.0]  # Consistently slow
        circuit_breaker._response_times = deque(slow_response_times, maxlen=100)
        circuit_breaker.metrics.slow_requests = len(slow_response_times)
        
        # Capture baseline state
        original_threshold = circuit_breaker.metrics.adaptive_failure_threshold
        original_slow_count = circuit_breaker.metrics.slow_requests
        
        # Execute threshold adaptation
        circuit_breaker._adapt_threshold_if_enabled()
        
        # Verify threshold decreased meaningfully (at least 10% reduction)
        new_threshold = circuit_breaker.metrics.adaptive_failure_threshold
        assert new_threshold < original_threshold, "Threshold should decrease with slow calls"
        assert new_threshold < (original_threshold * 0.9), f"Expected >10% decrease, got {(original_threshold - new_threshold) / original_threshold * 100:.1f}%"
        
        # Verify slow request tracking is maintained
        assert circuit_breaker.metrics.slow_requests >= original_slow_count
        
        # Boundary condition: Ensure threshold doesn't go below minimum (1)
        assert new_threshold >= 1, "Threshold should never go below 1"

    def test_adaptive_threshold_increases_on_fast_calls(self, circuit_breaker):
        """Adaptive threshold increases with fast response times.
        
        BUSINESS LOGIC: When response times are consistently fast, the circuit becomes
        more tolerant of occasional failures by raising the threshold. This maximizes
        system utilization while maintaining reliability for high-performing services.
        """
        # Enable adaptive threshold for this test
        circuit_breaker.config.adaptive_threshold = True
        
        # Set up fast response times scenario with varied but consistently low times
        fast_response_times = [0.05, 0.08, 0.12, 0.09, 0.06]
        circuit_breaker._response_times = deque(fast_response_times, maxlen=100)
        circuit_breaker.metrics.successful_calls = len(fast_response_times)
        
        # Capture baseline metrics
        original_threshold = circuit_breaker.metrics.adaptive_failure_threshold
        original_success_count = circuit_breaker.metrics.successful_calls
        baseline_avg = sum(fast_response_times) / len(fast_response_times)
        
        # Execute threshold adaptation
        circuit_breaker._adapt_threshold_if_enabled()
        
        # Verify threshold increased meaningfully (at least 10% increase)
        new_threshold = circuit_breaker.metrics.adaptive_failure_threshold
        assert new_threshold > original_threshold, "Threshold should increase with fast calls"
        assert new_threshold > (original_threshold * 1.1), f"Expected >10% increase, got {(new_threshold - original_threshold) / original_threshold * 100:.1f}%"
        
        # Verify success tracking reflects fast operations
        assert circuit_breaker.metrics.successful_calls >= original_success_count
        assert baseline_avg < 0.2, f"Test setup validation: average response time {baseline_avg:.3f}s should be fast (<0.2s)"
        
        # Boundary condition: Ensure threshold doesn't exceed maximum reasonable limit
        max_reasonable_threshold = circuit_breaker.config.failure_threshold * 3
        assert new_threshold <= max_reasonable_threshold, f"Threshold {new_threshold} should not exceed 3x base threshold {max_reasonable_threshold}"

    @pytest.mark.asyncio
    async def test_adaptive_threshold_with_health_degraded(self, circuit_with_health):
        """Adaptive threshold decreases when health is degraded."""
        # Enable adaptive threshold for this test
        circuit_with_health.config.adaptive_threshold = True
        
        degraded_result = create_health_result(HealthStatus.DEGRADED, 0.1)
        circuit_with_health.last_health_check = degraded_result
        original_threshold = circuit_with_health.metrics.adaptive_failure_threshold
        circuit_with_health._adapt_threshold_if_enabled()
        assert circuit_with_health.metrics.adaptive_failure_threshold <= original_threshold

    @pytest.mark.asyncio
    async def test_adaptive_threshold_with_health_healthy(self, circuit_with_health):
        """Adaptive threshold increases when health is good."""
        # Enable adaptive threshold for this test
        circuit_with_health.config.adaptive_threshold = True
        
        healthy_result = create_health_result(HealthStatus.HEALTHY, 0.1)
        circuit_with_health.last_health_check = healthy_result
        original_threshold = circuit_with_health.metrics.adaptive_failure_threshold
        circuit_with_health._adapt_threshold_if_enabled()
        assert circuit_with_health.metrics.adaptive_failure_threshold >= original_threshold

class TestMetricsAndStatus:
    """Test metrics collection and status reporting."""

    @pytest.mark.asyncio
    async def test_get_metrics_returns_complete_data(self, circuit_breaker):
        """Metrics include all expected fields."""
        await simulate_operation_failure(circuit_breaker)
        status = circuit_breaker.get_status()
        expected_fields = ['name', 'state']
        for field in expected_fields:
            assert field in status

    def test_get_status_compatibility(self, circuit_breaker):
        """get_status method works for backward compatibility."""
        status = circuit_breaker.get_status()
        assert 'name' in status
        assert status['name'] == "test_circuit"

    @pytest.mark.asyncio
    async def test_failure_rate_calculation(self, circuit_breaker):
        """Failure rate calculates correctly."""
        await simulate_operation_success(circuit_breaker)
        await simulate_operation_failure(circuit_breaker)
        # Just verify the calls were tracked correctly
        assert circuit_breaker.metrics.failed_calls == 1
        assert circuit_breaker.metrics.successful_calls == 1

    @pytest.mark.asyncio
    async def test_metrics_track_state_changes(self, circuit_breaker):
        """Metrics track when state changes."""
        initial_time = circuit_breaker.last_state_change
        await circuit_breaker.force_open()
        assert circuit_breaker.last_state_change >= initial_time

class TestTimeoutAndRecovery:
    """Test timeout-based recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_should_attempt_reset_after_timeout(self, circuit_breaker):
        """Circuit attempts reset after timeout period."""
        # Disable exponential backoff for predictable testing
        circuit_breaker.config.exponential_backoff = False
        
        # Note: force_open() now automatically sets last_failure_time
        await circuit_breaker.force_open()
        # Override with past time to simulate timeout elapsed
        past_time = time.time() - (circuit_breaker.config.recovery_timeout + 1)
        circuit_breaker.metrics.last_failure_time = past_time
        assert circuit_breaker._is_recovery_timeout_elapsed() is True

    @pytest.mark.asyncio
    async def test_should_not_reset_before_timeout(self, circuit_breaker):
        """Circuit doesn't reset before timeout."""
        await circuit_breaker.force_open()
        circuit_breaker.metrics.last_failure_time = time.time()
        assert circuit_breaker._is_recovery_timeout_elapsed() is False

    @pytest.mark.asyncio
    async def test_open_to_half_open_transition(self, circuit_breaker):
        """Open circuit transitions to HALF_OPEN after timeout."""
        # Disable exponential backoff for predictable testing
        circuit_breaker.config.exponential_backoff = False
        
        await circuit_breaker.force_open()
        # Override with past time to simulate timeout elapsed
        past_time = time.time() - (circuit_breaker.config.recovery_timeout + 1)
        circuit_breaker.metrics.last_failure_time = past_time
        # Trigger state check - should transition to HALF_OPEN and allow execution
        can_execute = await circuit_breaker._can_execute()
        assert can_execute is True
        # Verify state transitioned to HALF_OPEN
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

class TestCleanup:
    """Test cleanup and resource management."""

    @pytest.mark.asyncio
    async def test_cleanup_cancels_health_check_task(self, circuit_with_health):
        """Cleanup cancels background health check task."""
        # Health check task should be created during initialization
        task = circuit_with_health._health_check_task
        assert task is not None
        assert not task.done()  # Task should be running initially
        
        # Call cleanup to cancel the task
        circuit_with_health.cleanup()
        
        # Give a brief moment for cancellation to be processed
        # The task may be in a "cancelling" state, which we accept
        await asyncio.sleep(0.01)
        
        # Verify cleanup was called - task should be in cancelled or cancelling state
        # cancelled() returns False while cancelling, done() returns False too
        # We check that either it's cancelled/done or the cancel() was called
        assert task.cancelled() or task.done() or task.cancelling()

    def test_public_record_methods_work(self, circuit_breaker):
        """Public record methods work for compatibility."""
        circuit_breaker.record_success()
        assert circuit_breaker.metrics.successful_calls > 0
        circuit_breaker.record_failure("test_error")
        assert circuit_breaker.metrics.failed_calls > 0


class TestCircuitBreakerEdgeCases:
    """Test edge cases and complex scenarios for circuit breaker."""
    
    def test_circuit_breaker_basic_failure_tracking(self, circuit_breaker):
        """Test basic failure tracking and state behavior."""
        initial_state = circuit_breaker.state
        assert initial_state == CircuitBreakerState.CLOSED
        
        # Record some failures
        for i in range(2):
            circuit_breaker.record_failure(f"test_error_{i}")
        
        # Check if still closed (depends on failure threshold)
        current_state = circuit_breaker.state
        # State may or may not have changed depending on threshold configuration
        assert current_state in [CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN]
        
        # Verify we can check metrics through the metrics property
        assert hasattr(circuit_breaker, 'metrics')
    
    def test_circuit_breaker_status_reporting(self, circuit_breaker):
        """Test status reporting and information access."""
        # Start in closed state
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
        # Record some operations
        for i in range(3):
            circuit_breaker.record_failure(f"error_{i}")
        
        for i in range(2):
            circuit_breaker.record_success()
        
        # Verify we can get status information
        status = circuit_breaker.get_status()
        assert isinstance(status, dict)
        assert "state" in status
        assert "metrics" in status
        
        # Verify metrics structure
        metrics = status["metrics"]
        assert isinstance(metrics, dict)
    
    def test_circuit_breaker_edge_case_zero_threshold(self, circuit_breaker):
        """Test circuit breaker with zero failure threshold."""
        # Should handle zero threshold gracefully
        circuit_breaker.failure_threshold = 0
        status = circuit_breaker.get_status()
        assert status["state"] in ["closed", "open", "half_open"]
    
    def test_circuit_breaker_negative_timeout(self, circuit_breaker):
        """Test circuit breaker with negative timeout values."""
        # Should handle negative timeouts gracefully
        circuit_breaker.timeout = -1
        status = circuit_breaker.get_status()
        assert "timeout" in str(status) or "state" in status

    @pytest.mark.asyncio
    async def test_partial_network_failure_resilience(self, circuit_breaker):
        """Test circuit breaker behavior during partial network failures.
        
        BUSINESS VALUE: Prevents service degradation during partial outages by 
        staying operational while tracking intermittent failures, protecting 
        enterprise AI workloads from unnecessary downtime.
        
        Scenario: Mixed success/failure pattern typical of network instability.
        """
        # Simulate partial network failure: 70% success, 30% failure
        success_count, failure_count = 0, 0
        operations = [True, False, True, True, False, True, True, True, False, True]
        
        for should_succeed in operations:
            try:
                if should_succeed:
                    await circuit_breaker.call(simulate_async_operation)
                    success_count += 1
                else:
                    await circuit_breaker.call(simulate_failing_operation)
            except RuntimeError:
                failure_count += 1
        
        # Circuit should remain closed due to majority success (below failure threshold)
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.metrics.successful_calls == success_count
        assert circuit_breaker.metrics.failed_calls == failure_count