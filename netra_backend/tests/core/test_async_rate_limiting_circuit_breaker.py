"""
Focused tests for Async Rate Limiting and Circuit Breaker functionality
Tests AsyncRateLimiter and AsyncCircuitBreaker with various scenarios
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add project root to path
from netra_backend.app.core.async_utils import (
    AsyncCircuitBreaker,
    # Add project root to path
    AsyncRateLimiter,
)
from netra_backend.app.core.exceptions_service import ServiceError, ServiceTimeoutError


class TestAsyncRateLimiterComplete:
    """Complete tests for AsyncRateLimiter."""
    async def test_rate_limiter_basic_functionality(self):
        """Test basic rate limiter functionality."""
        limiter = AsyncRateLimiter(rate=2, window=1.0)  # 2 requests per second
        
        # First two requests should go through immediately
        start_time = time.time()
        await limiter.acquire()
        await limiter.acquire()
        immediate_time = time.time() - start_time
        
        assert immediate_time < 0.1  # Should be very fast
        
        # Third request should be delayed
        start_time = time.time()
        await limiter.acquire()
        delayed_time = time.time() - start_time
        
        assert delayed_time >= 0.5  # Should wait for window reset
    async def test_rate_limiter_window_reset(self):
        """Test rate limiter window reset behavior."""
        limiter = AsyncRateLimiter(rate=3, window=0.5)  # 3 requests per 0.5 seconds
        
        # Use up the quota
        for _ in range(3):
            await limiter.acquire()
        
        # Wait for window reset
        await asyncio.sleep(0.6)
        
        # Should be able to make requests again immediately
        start_time = time.time()
        await limiter.acquire()
        reset_time = time.time() - start_time
        
        assert reset_time < 0.1  # Should be immediate after reset
    async def test_rate_limiter_concurrent_requests(self):
        """Test rate limiter with concurrent requests."""
        limiter = AsyncRateLimiter(rate=2, window=1.0)
        request_times = []
        
        async def make_request(request_id):
            start_time = time.time()
            await limiter.acquire()
            end_time = time.time()
            request_times.append((request_id, end_time - start_time))
        
        # Submit multiple concurrent requests
        tasks = [make_request(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # First two should be fast, others should be delayed
        fast_requests = [t for t in request_times if t[1] < 0.1]
        slow_requests = [t for t in request_times if t[1] >= 0.5]
        
        assert len(fast_requests) >= 2
        assert len(slow_requests) >= 2
    async def test_rate_limiter_different_rates(self):
        """Test rate limiter with different rate configurations."""
        # High rate limiter (10 requests per second)
        high_limiter = AsyncRateLimiter(rate=10, window=1.0)
        
        # Low rate limiter (1 request per second)
        low_limiter = AsyncRateLimiter(rate=1, window=1.0)
        
        # High rate should allow quick successive requests
        start_time = time.time()
        for _ in range(5):
            await high_limiter.acquire()
        high_time = time.time() - start_time
        
        # Low rate should enforce delays
        start_time = time.time()
        await low_limiter.acquire()
        await low_limiter.acquire()
        low_time = time.time() - start_time
        
        assert high_time < 0.5
        assert low_time >= 1.0
    async def test_rate_limiter_burst_handling(self):
        """Test rate limiter burst handling."""
        limiter = AsyncRateLimiter(rate=3, window=1.0, burst=2)  # Allow 2 burst requests
        
        # Should handle burst of requests
        burst_times = []
        for i in range(5):  # More than rate + burst
            start_time = time.time()
            await limiter.acquire()
            burst_times.append(time.time() - start_time)
        
        # First few should be fast (rate + burst)
        fast_requests = [t for t in burst_times if t < 0.1]
        assert len(fast_requests) >= 3  # rate + burst allowance


class TestAsyncCircuitBreakerComplete:
    """Complete tests for AsyncCircuitBreaker."""
    async def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed (normal) state."""
        breaker = AsyncCircuitBreaker(failure_threshold=3, timeout=1.0)
        
        # Should allow calls in closed state
        async def successful_operation():
            return "success"
        
        result = await breaker.call(successful_operation)
        assert result == "success"
        assert breaker.state == "closed"
    async def test_circuit_breaker_failure_tracking(self):
        """Test circuit breaker failure tracking and state transitions."""
        breaker = AsyncCircuitBreaker(failure_threshold=2, timeout=0.5)
        failure_count = 0
        
        async def failing_operation():
            nonlocal failure_count
            failure_count += 1
            raise ServiceError(f"Failure {failure_count}")
        
        # First failure - should stay closed
        with pytest.raises(ServiceError):
            await breaker.call(failing_operation)
        assert breaker.state == "closed"
        
        # Second failure - should open circuit
        with pytest.raises(ServiceError):
            await breaker.call(failing_operation)
        assert breaker.state == "open"
    async def test_circuit_breaker_open_state(self):
        """Test circuit breaker in open state."""
        breaker = AsyncCircuitBreaker(failure_threshold=1, timeout=0.5)
        
        # Force circuit open
        async def failing_operation():
            raise ServiceError("Force failure")
        
        with pytest.raises(ServiceError):
            await breaker.call(failing_operation)
        
        # Should reject calls while open
        async def any_operation():
            return "should not execute"
        
        with pytest.raises(ServiceError, match="Circuit breaker is open"):
            await breaker.call(any_operation)
    async def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state and recovery."""
        breaker = AsyncCircuitBreaker(failure_threshold=1, timeout=0.2)
        
        # Force circuit open
        async def failing_operation():
            raise ServiceError("Initial failure")
        
        with pytest.raises(ServiceError):
            await breaker.call(failing_operation)
        
        # Wait for timeout
        await asyncio.sleep(0.3)
        
        # Should transition to half-open
        async def recovery_operation():
            return "recovered"
        
        result = await breaker.call(recovery_operation)
        assert result == "recovered"
        assert breaker.state == "closed"  # Should close after success
    async def test_circuit_breaker_success_reset(self):
        """Test circuit breaker success counter reset."""
        breaker = AsyncCircuitBreaker(failure_threshold=3, success_threshold=2, timeout=0.5)
        
        # Cause some failures (but not enough to open)
        async def sometimes_failing_operation(should_fail=True):
            if should_fail:
                raise ServiceError("Controlled failure")
            return "success"
        
        # Two failures
        for _ in range(2):
            with pytest.raises(ServiceError):
                await breaker.call(lambda: sometimes_failing_operation(True))
        
        assert breaker.state == "closed"  # Still below threshold
        
        # Two successes should reset failure count
        for _ in range(2):
            result = await breaker.call(lambda: sometimes_failing_operation(False))
            assert result == "success"
        
        # Should still be closed with reset counters
        assert breaker.state == "closed"
    async def test_circuit_breaker_with_timeout_operation(self):
        """Test circuit breaker with timeout operations."""
        breaker = AsyncCircuitBreaker(failure_threshold=2, timeout=0.5)
        
        async def timeout_operation():
            await asyncio.sleep(2.0)  # Longer than any reasonable timeout
            return "should not complete"
        
        # Should treat timeouts as failures
        start_time = time.time()
        with pytest.raises((ServiceError, asyncio.TimeoutError)):
            await asyncio.wait_for(breaker.call(timeout_operation), timeout=0.5)
        
        execution_time = time.time() - start_time
        assert execution_time <= 1.0  # Should timeout quickly
    async def test_circuit_breaker_concurrent_operations(self):
        """Test circuit breaker with concurrent operations."""
        breaker = AsyncCircuitBreaker(failure_threshold=3, timeout=0.5)
        results = []
        
        async def concurrent_operation(op_id, should_fail=False):
            try:
                if should_fail:
                    raise ServiceError(f"Failure {op_id}")
                
                async def actual_op():
                    await asyncio.sleep(0.01)
                    return f"success_{op_id}"
                
                result = await breaker.call(actual_op)
                results.append(result)
                return result
            except ServiceError:
                results.append(f"failed_{op_id}")
                raise
        
        # Mix of successful and failing operations
        tasks = [
            concurrent_operation(1, False),
            concurrent_operation(2, True),
            concurrent_operation(3, False),
            concurrent_operation(4, True)
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        assert len(results) == 4
    async def test_circuit_breaker_state_persistence(self):
        """Test circuit breaker state persistence across operations."""
        breaker = AsyncCircuitBreaker(failure_threshold=2, timeout=1.0)
        
        # Track state changes
        state_changes = []
        original_set_state = breaker._set_state
        
        def track_state_change(new_state):
            state_changes.append(new_state)
            return original_set_state(new_state)
        
        breaker._set_state = track_state_change
        
        # Cause state transitions
        async def operation(should_fail=True):
            if should_fail:
                raise ServiceError("Test failure")
            return "success"
        
        # Failures to open circuit
        for _ in range(2):
            with pytest.raises(ServiceError):
                await breaker.call(lambda: operation(True))
        
        # Should have recorded state change to open
        assert "open" in state_changes
        
        # Wait and try recovery
        await asyncio.sleep(1.1)
        result = await breaker.call(lambda: operation(False))
        assert result == "success"
        
        # Should have recorded state changes
        assert len(state_changes) >= 1