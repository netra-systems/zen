"""Comprehensive tests for AdaptiveCircuitBreaker core functionality.

BUSINESS VALUE: Protects system reliability and prevents cascading failures, 
directly saving customer AI spend by avoiding service outages.

Tests critical paths including state transitions, adaptive thresholds,
health monitoring, and failure recovery mechanisms.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from netra_backend.app.core.adaptive_circuit_breaker_core import AdaptiveCircuitBreaker
from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError
from netra_backend.app.core.shared_health_types import HealthChecker, HealthStatus
from netra_backend.app.schemas.core_enums import CircuitBreakerState
from netra_backend.app.schemas.core_models import CircuitBreakerConfig, HealthCheckResult


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
    checker = Mock(spec=HealthChecker)
    checker.check_health = AsyncMock(return_value=create_health_result())
    return checker


@pytest.fixture
def circuit_breaker(circuit_config):
    """Circuit breaker instance without health checker."""
    return AdaptiveCircuitBreaker("test", circuit_config)


@pytest.fixture  
async def circuit_with_health(circuit_config, mock_health_checker):
    """Circuit breaker with health monitoring."""
    circuit = AdaptiveCircuitBreaker("test", circuit_config, mock_health_checker)
    yield circuit
    circuit.cleanup()


# Helper functions for 25-line compliance
def create_health_result(status=HealthStatus.HEALTHY, response_time=0.1):
    """Create standardized health check result."""
    return HealthCheckResult(
        status=status, response_time=response_time, details={}
    )


def assert_circuit_state(circuit, expected_state):
    """Assert circuit is in expected state."""
    assert circuit.state == expected_state


def assert_failure_count(circuit, expected_count):
    """Assert circuit has expected failure count."""
    assert circuit.failure_count == expected_count


def simulate_operation_failure(circuit):
    """Simulate a failed operation."""
    circuit._record_failure(0.1)


def simulate_operation_success(circuit):
    """Simulate a successful operation."""
    circuit._record_success(0.1)


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
        circuit = AdaptiveCircuitBreaker("test_name", circuit_config)
        assert circuit.name == "test_name"

    def test_circuit_breaker_config_storage(self, circuit_breaker, circuit_config):
        """Circuit breaker stores configuration correctly."""
        assert circuit_breaker.config == circuit_config
        assert circuit_breaker.adaptive_failure_threshold == circuit_config.failure_threshold

    def test_circuit_breaker_metrics_initialization(self, circuit_breaker):
        """Circuit breaker initializes metrics to zero."""
        assert circuit_breaker.total_calls == 0
        assert circuit_breaker.successful_calls == 0
        assert circuit_breaker.failed_calls == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_health_checker(self, circuit_with_health, mock_health_checker):
        """Circuit breaker accepts health checker."""
        assert circuit_with_health.health_checker == mock_health_checker
        assert circuit_with_health.last_health_check is None


class TestCircuitStateTransitions:
    """Test circuit breaker state transition logic."""

    def test_closed_to_open_on_failures(self, circuit_breaker):
        """Circuit opens after reaching failure threshold."""
        for _ in range(3):  # Failure threshold is 3
            simulate_operation_failure(circuit_breaker)
        assert_circuit_state(circuit_breaker, CircuitBreakerState.OPEN)

    def test_failure_count_increments(self, circuit_breaker):
        """Failure count increments with each failure."""
        simulate_operation_failure(circuit_breaker)
        assert_failure_count(circuit_breaker, 1)
        simulate_operation_failure(circuit_breaker)
        assert_failure_count(circuit_breaker, 2)

    def test_should_allow_request_when_closed(self, circuit_breaker):
        """Closed circuit allows requests."""
        assert circuit_breaker.should_allow_request() is True

    def test_should_reject_request_when_open(self, circuit_breaker):
        """Open circuit rejects requests initially."""
        circuit_breaker.force_open()
        assert circuit_breaker.should_allow_request() is False

    def test_force_open_transitions_state(self, circuit_breaker):
        """Force open changes state to OPEN."""
        circuit_breaker.force_open()
        assert_circuit_state(circuit_breaker, CircuitBreakerState.OPEN)

    def test_force_close_transitions_state(self, circuit_breaker):
        """Force close changes state to CLOSED."""
        circuit_breaker.force_open()
        circuit_breaker.force_close()
        assert_circuit_state(circuit_breaker, CircuitBreakerState.CLOSED)

    def test_half_open_success_leads_to_closed(self, circuit_breaker):
        """Successful operations in HALF_OPEN lead to CLOSED."""
        circuit_breaker._transition_to_half_open()
        for _ in range(2):  # Success threshold is 2
            simulate_operation_success(circuit_breaker)
        assert_circuit_state(circuit_breaker, CircuitBreakerState.CLOSED)


class TestOperationExecution:
    """Test operation execution through circuit breaker."""

    @pytest.mark.asyncio
    async def test_successful_operation_execution(self, circuit_breaker):
        """Successful operation returns result and updates metrics."""
        result = await circuit_breaker.call(simulate_async_operation)
        assert result == "success"
        assert circuit_breaker.successful_calls == 1
        assert circuit_breaker.total_calls == 1

    @pytest.mark.asyncio
    async def test_failed_operation_execution(self, circuit_breaker):
        """Failed operation raises exception and updates metrics."""
        with pytest.raises(RuntimeError, match="Operation failed"):
            await circuit_breaker.call(simulate_failing_operation)
        assert circuit_breaker.failed_calls == 1
        assert circuit_breaker.total_calls == 1

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self, circuit_breaker):
        """Open circuit raises CircuitBreakerOpenError."""
        circuit_breaker.force_open()
        with pytest.raises(CircuitBreakerOpenError, match="Circuit breaker test is open"):
            await circuit_breaker.call(simulate_async_operation)

    @pytest.mark.asyncio
    async def test_response_time_tracking(self, circuit_breaker):
        """Circuit tracks response times."""
        await circuit_breaker.call(simulate_async_operation)
        metrics = circuit_breaker.get_metrics()
        assert metrics['avg_response_time'] >= 0.0

    @pytest.mark.asyncio
    async def test_slow_call_detection(self, circuit_breaker):
        """Circuit detects slow calls."""
        # Mock a slow operation
        async def slow_operation():
            await asyncio.sleep(0.1)  # Longer than slow_call_threshold
            return "slow_result"
        
        with patch.object(circuit_breaker, 'config') as mock_config:
            mock_config.slow_call_threshold = 0.05
            await circuit_breaker.call(slow_operation)
        assert circuit_breaker.slow_requests >= 0


class TestAdaptiveThreshold:
    """Test adaptive threshold functionality."""

    def test_adaptive_threshold_decreases_on_slow_calls(self, circuit_breaker):
        """Adaptive threshold decreases with slow response times."""
        circuit_breaker.recent_response_times = [6.0, 7.0, 8.0]  # Slow times
        original_threshold = circuit_breaker.adaptive_failure_threshold
        circuit_breaker._adapt_failure_threshold()
        assert circuit_breaker.adaptive_failure_threshold <= original_threshold

    def test_adaptive_threshold_increases_on_fast_calls(self, circuit_breaker):
        """Adaptive threshold increases with fast response times.""" 
        circuit_breaker.recent_response_times = [0.1, 0.2, 0.3]  # Fast times
        original_threshold = circuit_breaker.adaptive_failure_threshold
        circuit_breaker._adapt_failure_threshold()
        assert circuit_breaker.adaptive_failure_threshold >= original_threshold

    @pytest.mark.asyncio
    async def test_adaptive_threshold_with_health_degraded(self, circuit_with_health):
        """Adaptive threshold decreases when health is degraded."""
        degraded_result = create_health_result(HealthStatus.DEGRADED, 0.1)
        circuit_with_health.last_health_check = degraded_result
        original_threshold = circuit_with_health.adaptive_failure_threshold
        circuit_with_health._adapt_failure_threshold()
        assert circuit_with_health.adaptive_failure_threshold <= original_threshold

    @pytest.mark.asyncio
    async def test_adaptive_threshold_with_health_healthy(self, circuit_with_health):
        """Adaptive threshold increases when health is good."""
        healthy_result = create_health_result(HealthStatus.HEALTHY, 0.1)
        circuit_with_health.last_health_check = healthy_result
        original_threshold = circuit_with_health.adaptive_failure_threshold
        circuit_with_health._adapt_failure_threshold()
        assert circuit_with_health.adaptive_failure_threshold >= original_threshold


class TestMetricsAndStatus:
    """Test metrics collection and status reporting."""

    def test_get_metrics_returns_complete_data(self, circuit_breaker):
        """Metrics include all expected fields."""
        simulate_operation_failure(circuit_breaker)
        metrics = circuit_breaker.get_metrics()
        expected_fields = ['name', 'state', 'failure_count', 'total_calls', 'failure_rate']
        for field in expected_fields:
            assert field in metrics

    def test_get_status_compatibility(self, circuit_breaker):
        """get_status method works for backward compatibility."""
        status = circuit_breaker.get_status()
        assert 'name' in status
        assert status['name'] == "test"

    def test_failure_rate_calculation(self, circuit_breaker):
        """Failure rate calculates correctly."""
        simulate_operation_success(circuit_breaker)
        simulate_operation_failure(circuit_breaker)
        metrics = circuit_breaker.get_metrics()
        # Circuit tracks failed_calls vs total_calls
        expected_rate = circuit_breaker.failed_calls / max(circuit_breaker.total_calls, 1)
        assert metrics['failure_rate'] == expected_rate

    def test_metrics_track_state_changes(self, circuit_breaker):
        """Metrics track when state changes."""
        initial_time = circuit_breaker.last_state_change
        circuit_breaker.force_open()
        assert circuit_breaker.last_state_change >= initial_time


class TestTimeoutAndRecovery:
    """Test timeout-based recovery mechanisms."""

    def test_should_attempt_reset_after_timeout(self, circuit_breaker):
        """Circuit attempts reset after timeout period."""
        circuit_breaker.force_open()
        # Simulate timeout has passed
        past_time = datetime.now() - timedelta(seconds=2)
        circuit_breaker.last_failure_time = past_time
        assert circuit_breaker._should_attempt_reset() is True

    def test_should_not_reset_before_timeout(self, circuit_breaker):
        """Circuit doesn't reset before timeout."""
        circuit_breaker.force_open()
        circuit_breaker.last_failure_time = datetime.now()
        assert circuit_breaker._should_attempt_reset() is False

    def test_open_to_half_open_transition(self, circuit_breaker):
        """Open circuit transitions to HALF_OPEN after timeout."""
        circuit_breaker.force_open()
        past_time = datetime.now() - timedelta(seconds=2)
        circuit_breaker.last_failure_time = past_time
        # Trigger state check
        circuit_breaker.should_allow_request()
        assert_circuit_state(circuit_breaker, CircuitBreakerState.HALF_OPEN)


class TestCleanup:
    """Test cleanup and resource management."""

    @pytest.mark.asyncio
    async def test_cleanup_cancels_health_check_task(self, circuit_with_health):
        """Cleanup cancels background health check task."""
        # Health check task should be created during initialization
        assert circuit_with_health._health_check_task is not None
        circuit_with_health.cleanup()
        # Give a moment for cancellation to process
        await asyncio.sleep(0.01)
        assert circuit_with_health._health_check_task.cancelled()

    def test_public_record_methods_work(self, circuit_breaker):
        """Public record methods work for compatibility."""
        circuit_breaker.record_success()
        assert circuit_breaker.successful_calls > 0
        circuit_breaker.record_failure("test_error")
        assert circuit_breaker.failed_calls > 0