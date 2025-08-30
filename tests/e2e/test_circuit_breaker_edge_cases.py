"""
End-to-end tests for circuit breaker edge cases.

This test module validates circuit breaker behavior in complex scenarios
that might not be covered by unit tests.
"""
import pytest
import asyncio
import time

from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerState
)
from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError


@pytest.mark.e2e
@pytest.mark.env_test
class TestCircuitBreakerEdgeCases:
    """Test edge cases for circuit breaker functionality."""

    @pytest.fixture
    def edge_case_config(self):
        """Configuration for edge case testing."""
        return UnifiedCircuitConfig(
            name="edge_case_test",
            failure_threshold=3,
            recovery_timeout=0.1,
            half_open_max_calls=2,
            sliding_window_size=5,
            error_rate_threshold=0.6,
            exponential_backoff=False,
            timeout_seconds=0.05
        )

    @pytest.fixture
    def circuit_breaker(self, edge_case_config):
        """Create circuit breaker for edge case testing."""
        return UnifiedCircuitBreaker(edge_case_config)

    @pytest.mark.asyncio
    async def test_rapid_failure_recovery_cycles(self, circuit_breaker):
        """Test circuit breaker behavior under rapid failure/recovery cycles."""
        async def intermittent_operation(success_count=[0]):
            success_count[0] += 1
            # Fail every 3rd call
            if success_count[0] % 3 == 0:
                raise ValueError("Intermittent failure")
            return f"success_{success_count[0]}"

        results = []
        errors = []
        
        # Run 20 operations to test stability
        for i in range(20):
            try:
                result = await circuit_breaker.call(intermittent_operation)
                results.append(result)
            except (ValueError, CircuitBreakerOpenError) as e:
                errors.append(str(e))
            
            # Small delay between operations
            await asyncio.sleep(0.01)

        # Should have both successes and failures
        assert len(results) > 0, "Should have some successful operations"
        assert len(errors) > 0, "Should have some failed operations"
        
        # Circuit breaker should eventually recover and allow operations
        final_status = circuit_breaker.get_status()
        assert final_status["metrics"]["total_calls"] == 20

    @pytest.mark.asyncio
    async def test_timeout_edge_cases(self, circuit_breaker):
        """Test edge cases related to operation timeouts."""
        async def slow_operation():
            await asyncio.sleep(0.1)  # Longer than timeout (0.05s)
            return "slow_success"

        async def fast_operation():
            await asyncio.sleep(0.01)  # Faster than timeout
            return "fast_success"

        # Slow operation should timeout
        with pytest.raises(asyncio.TimeoutError):
            await circuit_breaker.call(slow_operation)

        # Fast operation should succeed
        result = await circuit_breaker.call(fast_operation)
        assert result == "fast_success"

        # Circuit should handle mix of timeout and regular errors
        async def mixed_failure():
            await asyncio.sleep(0.1)  # Timeout
            raise ValueError("This shouldn't be reached")

        with pytest.raises(asyncio.TimeoutError):
            await circuit_breaker.call(mixed_failure)

    @pytest.mark.asyncio
    async def test_concurrent_state_changes(self, circuit_breaker):
        """Test circuit breaker behavior under concurrent access."""
        async def concurrent_operation(op_id: int):
            if op_id % 4 == 0:  # 25% failure rate
                raise ValueError(f"Operation {op_id} failed")
            await asyncio.sleep(0.001)  # Small delay
            return f"success_{op_id}"

        # Run multiple concurrent operations
        tasks = [
            circuit_breaker.call(concurrent_operation, i)
            for i in range(50)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successes = [r for r in results if isinstance(r, str)]
        failures = [r for r in results if isinstance(r, Exception)]

        assert len(successes) > 0, "Should have some successful operations"
        assert len(failures) > 0, "Should have some failed operations"
        
        # Circuit breaker state should be consistent
        status = circuit_breaker.get_status()
        assert status["metrics"]["total_calls"] == 50

    @pytest.mark.asyncio
    async def test_error_rate_calculation_edge_cases(self, circuit_breaker):
        """Test error rate calculation in edge scenarios."""
        # Fill sliding window with mostly successes
        async def success_op():
            return "success"
            
        async def failure_op():
            raise ValueError("failure")

        # Start with successes
        for _ in range(3):
            await circuit_breaker.call(success_op)

        # Should still be closed
        assert circuit_breaker.is_closed

        # Add failures to reach error rate threshold
        for _ in range(2):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failure_op)

        # Error rate should be 40% (2/5) - below threshold (60%)
        assert circuit_breaker.is_closed

        # Add one more failure to exceed threshold
        with pytest.raises(ValueError):
            await circuit_breaker.call(failure_op)

        # Should be open now (3/5 = 60% error rate, reaching threshold)
        # Since we need failure_threshold (3) failures to open
        assert circuit_breaker.is_open

    @pytest.mark.asyncio
    async def test_recovery_with_health_checker(self, edge_case_config):
        """Test recovery behavior with health checker integration."""
        health_checker = AsyncNone  # TODO: Use real service instead of Mock
        health_result = MagicNone  # TODO: Use real service instead of Mock
        health_result.status = MagicNone  # TODO: Use real service instead of Mock
        health_result.status.value = "healthy"
        health_checker.check_health.return_value = health_result
        
        circuit_breaker = UnifiedCircuitBreaker(
            edge_case_config, 
            health_checker=health_checker
        )

        # Force circuit to open
        async def failing_operation():
            raise ValueError("fail")

        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_operation)

        assert circuit_breaker.is_open

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Should now allow recovery attempts
        async def success_operation():
            return "recovered"

        result = await circuit_breaker.call(success_operation)
        assert result == "recovered"

        # Health checker should have been called
        health_checker.check_health.assert_called()

    @pytest.mark.asyncio
    async def test_metrics_accuracy_under_stress(self, circuit_breaker):
        """Test that metrics remain accurate under high load."""
        success_count = 0
        failure_count = 0
        timeout_count = 0

        async def stress_operation(op_type: str):
            if op_type == "success":
                return "ok"
            elif op_type == "failure":
                raise ValueError("error")
            else:  # timeout
                await asyncio.sleep(0.1)  # Longer than timeout
                return "slow"

        # Generate mixed operations
        operations = ["success"] * 30 + ["failure"] * 20 + ["timeout"] * 10
        
        for op_type in operations:
            try:
                await circuit_breaker.call(stress_operation, op_type)
                success_count += 1
            except ValueError:
                failure_count += 1
            except asyncio.TimeoutError:
                timeout_count += 1
            except CircuitBreakerOpenError:
                # Circuit opened, expected behavior
                pass

        status = circuit_breaker.get_status()
        metrics = status["metrics"]
        
        # Verify metrics make sense
        assert metrics["total_calls"] >= 60  # Should have attempted all operations
        assert metrics["successful_calls"] == success_count
        assert metrics["failed_calls"] + metrics.get("timeout_calls", 0) >= failure_count + timeout_count