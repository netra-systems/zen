"""
Circuit Breaker State Transitions Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System State Management and Predictable Behavior
- Value Impact: Ensures circuit breaker state transitions are predictable and correct
- Strategic Impact: Protects $500K+ ARR by ensuring reliable state management for fault tolerance

This module tests circuit breaker state transition functionality including:
- CLOSED to OPEN transitions
- OPEN to HALF_OPEN transitions
- HALF_OPEN to CLOSED transitions
- HALF_OPEN to OPEN transitions
- State transition timing and conditions
- Event handling during transitions
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerException,
    FailureType
)


class CircuitBreakerStateTransitionTests(SSotAsyncTestCase):
    """Unit tests for circuit breaker state transitions."""

    def setup_method(self, method=None):
        """Setup test environment."""
        super().setup_method(method)
        
        # Create test configuration without invalid parameters
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            recovery_timeout=1.0,  # Short for testing
            half_open_max_requests=3,
            enable_metrics=True,
            enable_alerts=True
        )
        
        self.breaker = CircuitBreaker("state_test_service", self.config)
        self.state_changes = []
        
        # Track state changes
        def track_state_changes(name, old_state, new_state, reason):
            self.state_changes.append({
                'name': name,
                'old_state': old_state,
                'new_state': new_state,
                'reason': reason,
                'timestamp': datetime.now()
            })
        
        self.breaker.add_state_change_handler(track_state_changes)

    def test_initial_state(self):
        """Test initial circuit breaker state."""
        assert self.breaker.state == CircuitBreakerState.CLOSED
        assert self.breaker.is_closed is True
        assert self.breaker.is_open is False
        assert self.breaker.is_half_open is False
        
        # No state changes should have occurred yet
        assert len(self.state_changes) == 0

    async def test_closed_to_open_transition_failure_count(self):
        """Test CLOSED to OPEN transition based on failure count."""
        async def failing_operation():
            raise Exception("Service failure")
        
        # Should remain closed until failure threshold
        for i in range(self.config.failure_threshold - 1):
            with pytest.raises(Exception):
                await self.breaker.call(failing_operation)
            assert self.breaker.state == CircuitBreakerState.CLOSED
        
        # Final failure should trigger OPEN transition
        with pytest.raises(Exception):
            await self.breaker.call(failing_operation)
        
        assert self.breaker.state == CircuitBreakerState.OPEN
        assert self.breaker.is_open is True
        
        # Verify state change was recorded
        assert len(self.state_changes) == 1
        change = self.state_changes[0]
        assert change['old_state'] == CircuitBreakerState.CLOSED
        assert change['new_state'] == CircuitBreakerState.OPEN
        assert "Failure threshold exceeded" in change['reason']

    async def test_closed_to_open_transition_failure_rate(self):
        """Test CLOSED to OPEN transition based on failure rate."""
        config = CircuitBreakerConfig(
            failure_threshold=10,  # High threshold so rate triggers first
            minimum_requests=5,
            failure_rate_threshold=0.6,  # 60% failure rate
            enable_metrics=True
        )
        
        breaker = CircuitBreaker("rate_test", config)
        state_changes = []
        
        def track_changes(name, old_state, new_state, reason):
            state_changes.append({'old_state': old_state, 'new_state': new_state, 'reason': reason})
        
        breaker.add_state_change_handler(track_changes)
        
        async def sometimes_failing_operation(should_fail=False):
            if should_fail:
                raise Exception("Failure")
            return "success"
        
        # Send requests with 60% failure rate
        await breaker.call(sometimes_failing_operation, False)  # Success
        
        with pytest.raises(Exception):
            await breaker.call(sometimes_failing_operation, True)  # Failure
        
        with pytest.raises(Exception):
            await breaker.call(sometimes_failing_operation, True)  # Failure
        
        await breaker.call(sometimes_failing_operation, False)  # Success
        
        with pytest.raises(Exception):
            await breaker.call(sometimes_failing_operation, True)  # Failure (3/5 = 60%)
        
        assert breaker.state == CircuitBreakerState.OPEN
        assert len(state_changes) == 1
        assert state_changes[0]['new_state'] == CircuitBreakerState.OPEN

    async def test_open_to_half_open_transition_timing(self):
        """Test OPEN to HALF_OPEN transition based on recovery timeout."""
        # Force circuit open
        async def failing_operation():
            raise Exception("Service down")
        
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await self.breaker.call(failing_operation)
        
        assert self.breaker.state == CircuitBreakerState.OPEN
        initial_change_count = len(self.state_changes)
        
        # Should remain open before recovery timeout
        async def test_operation():
            return "test"
        
        with pytest.raises(CircuitBreakerException):
            await self.breaker.call(test_operation)
        
        assert self.breaker.state == CircuitBreakerState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(self.config.recovery_timeout + 0.1)
        
        # Next request should transition to half-open
        result = await self.breaker.call(test_operation)
        assert result == "test"
        assert self.breaker.state == CircuitBreakerState.HALF_OPEN
        
        # Verify state change
        assert len(self.state_changes) == initial_change_count + 1
        change = self.state_changes[-1]
        assert change['old_state'] == CircuitBreakerState.OPEN
        assert change['new_state'] == CircuitBreakerState.HALF_OPEN
        assert "Recovery timeout elapsed" in change['reason']

    async def test_half_open_to_closed_transition_success(self):
        """Test HALF_OPEN to CLOSED transition on sufficient successes."""
        # Force circuit to half-open state
        await self._force_to_half_open()
        
        assert self.breaker.state == CircuitBreakerState.HALF_OPEN
        initial_change_count = len(self.state_changes)
        
        async def successful_operation():
            return "success"
        
        # Need success_threshold successes to close
        for i in range(self.config.success_threshold - 1):
            result = await self.breaker.call(successful_operation)
            assert result == "success"
            assert self.breaker.state == CircuitBreakerState.HALF_OPEN
        
        # Final success should close the circuit
        result = await self.breaker.call(successful_operation)
        assert result == "success"
        assert self.breaker.state == CircuitBreakerState.CLOSED
        
        # Verify state change
        assert len(self.state_changes) == initial_change_count + 1
        change = self.state_changes[-1]
        assert change['old_state'] == CircuitBreakerState.HALF_OPEN
        assert change['new_state'] == CircuitBreakerState.CLOSED
        assert "Success threshold reached" in change['reason']

    async def test_half_open_to_open_transition_failure(self):
        """Test HALF_OPEN to OPEN transition on any failure."""
        # Force circuit to half-open state
        await self._force_to_half_open()
        
        assert self.breaker.state == CircuitBreakerState.HALF_OPEN
        initial_change_count = len(self.state_changes)
        
        # Any failure in half-open should return to open
        async def failing_operation():
            raise Exception("Still failing")
        
        with pytest.raises(Exception):
            await self.breaker.call(failing_operation)
        
        assert self.breaker.state == CircuitBreakerState.OPEN
        
        # Verify state change
        assert len(self.state_changes) == initial_change_count + 1
        change = self.state_changes[-1]
        assert change['old_state'] == CircuitBreakerState.HALF_OPEN
        assert change['new_state'] == CircuitBreakerState.OPEN
        assert "Failure in HALF_OPEN state" in change['reason']

    async def test_state_transition_with_concurrent_requests(self):
        """Test state transitions with concurrent requests."""
        # Force circuit open
        await self._force_to_open()
        
        # Wait for recovery timeout
        await asyncio.sleep(self.config.recovery_timeout + 0.1)
        
        async def concurrent_operation(request_id):
            await asyncio.sleep(0.01)  # Small delay
            return f"result_{request_id}"
        
        # Start multiple concurrent requests
        tasks = [
            asyncio.create_task(self.breaker.call(concurrent_operation, i))
            for i in range(6)  # More than half_open_max_requests
        ]
        
        results = []
        exceptions = []
        
        for task in tasks:
            try:
                result = await task
                results.append(result)
            except CircuitBreakerException:
                exceptions.append(True)
        
        # Should have limited successes and some blocked requests
        assert len(results) <= self.config.half_open_max_requests
        assert len(exceptions) > 0
        
        # Circuit should be in half-open or closed state
        assert self.breaker.state in [CircuitBreakerState.HALF_OPEN, CircuitBreakerState.CLOSED]

    async def test_rapid_state_transitions(self):
        """Test rapid state transitions under varying conditions."""
        async def unreliable_service(fail_probability=0.5):
            import random
            if random.random() < fail_probability:
                raise Exception("Random failure")
            return "success"
        
        # Perform many operations to trigger multiple state transitions
        for cycle in range(3):
            # High failure rate to open circuit
            for i in range(10):
                try:
                    await self.breaker.call(unreliable_service, 0.8)  # 80% failure
                except (Exception, CircuitBreakerException):
                    pass
            
            # Wait for potential recovery
            await asyncio.sleep(self.config.recovery_timeout + 0.1)
            
            # Low failure rate to potentially close circuit
            for i in range(5):
                try:
                    await self.breaker.call(unreliable_service, 0.2)  # 20% failure
                except (Exception, CircuitBreakerException):
                    pass
        
        # Should have recorded multiple state changes
        assert len(self.state_changes) > 0

    def test_manual_state_transitions(self):
        """Test manual state transitions through reset."""
        # Force circuit to open
        asyncio.run(self._force_to_open())
        
        assert self.breaker.state == CircuitBreakerState.OPEN
        initial_change_count = len(self.state_changes)
        
        # Reset should return to closed
        self.breaker.reset()
        
        assert self.breaker.state == CircuitBreakerState.CLOSED
        assert self.breaker._failure_count == 0
        assert self.breaker._success_count == 0
        assert self.breaker._last_failure_time is None
        assert self.breaker._last_success_time is None

    async def test_state_transition_metrics_tracking(self):
        """Test that state transitions are tracked in metrics."""
        # Force multiple state transitions
        await self._force_to_open()
        await asyncio.sleep(self.config.recovery_timeout + 0.1)
        await self._force_to_half_open()
        
        # Check metrics
        status = self.breaker.get_status()
        metrics = status['metrics']
        
        assert metrics['circuit_breaker_opens'] >= 1
        assert metrics['circuit_breaker_half_opens'] >= 1
        
        # Check state change history in metrics
        assert len(metrics.get('state_changes', [])) > 0 or len(self.state_changes) > 0

    async def test_state_transition_timing_precision(self):
        """Test timing precision of state transitions."""
        start_time = time.time()
        
        # Force circuit open
        await self._force_to_open()
        
        open_time = time.time()
        
        # Wait for exact recovery timeout
        await asyncio.sleep(self.config.recovery_timeout)
        
        # Should still be open (not quite time yet)
        async def test_op():
            return "test"
        
        # This might transition to half-open depending on timing precision
        try:
            await self.breaker.call(test_op)
            # If successful, circuit transitioned to half-open
            assert self.breaker.state == CircuitBreakerState.HALF_OPEN
        except CircuitBreakerException:
            # If blocked, still open (timing precision)
            assert self.breaker.state == CircuitBreakerState.OPEN
        
        # Small additional wait should definitely allow transition
        await asyncio.sleep(0.1)
        result = await self.breaker.call(test_op)
        assert result == "test"
        assert self.breaker.state == CircuitBreakerState.HALF_OPEN

    async def test_state_transition_edge_conditions(self):
        """Test state transitions under edge conditions."""
        # Test with minimum configuration values
        edge_config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=1,
            recovery_timeout=0.1,
            half_open_max_requests=1
        )
        
        edge_breaker = CircuitBreaker("edge_test", edge_config)
        edge_changes = []
        
        def track_edge_changes(name, old_state, new_state, reason):
            edge_changes.append({'old_state': old_state, 'new_state': new_state})
        
        edge_breaker.add_state_change_handler(track_edge_changes)
        
        # Single failure should open
        async def single_fail():
            raise Exception("One failure")
        
        with pytest.raises(Exception):
            await edge_breaker.call(single_fail)
        
        assert edge_breaker.state == CircuitBreakerState.OPEN
        assert len(edge_changes) == 1
        
        # Quick recovery
        await asyncio.sleep(0.2)
        
        async def quick_success():
            return "quick"
        
        result = await edge_breaker.call(quick_success)
        assert result == "quick"
        assert edge_breaker.state == CircuitBreakerState.CLOSED
        assert len(edge_changes) == 3  # OPEN -> HALF_OPEN -> CLOSED

    # Helper methods
    async def _force_to_open(self):
        """Helper to force circuit breaker to OPEN state."""
        async def failing_operation():
            raise Exception("Force open")
        
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await self.breaker.call(failing_operation)

    async def _force_to_half_open(self):
        """Helper to force circuit breaker to HALF_OPEN state."""
        await self._force_to_open()
        await asyncio.sleep(self.config.recovery_timeout + 0.1)
        
        async def transition_operation():
            return "transition"
        
        result = await self.breaker.call(transition_operation)
        assert result == "transition"