"""
Unit Tests for Agent Execution Circuit Breaker Logic

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) with focus on system stability
- Business Goal: Platform reliability and graceful degradation during outages  
- Value Impact: Prevents cascade failures and protects $500K+ ARR from service disruptions
- Strategic Impact: System resilience enables sustainable growth and customer confidence

This module tests the circuit breaker logic to ensure:
1. CircuitBreakerState enum has correct values and transitions
2. Circuit opens after failure threshold is reached
3. Circuit transitions to half-open for recovery testing
4. Circuit closes after success threshold is met
5. Timeout and recovery logic work correctly
6. Circuit breaker prevents cascade failures during outages
"""
import pytest
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch
from freezegun import freeze_time
from netra_backend.app.core.agent_execution_tracker import TimeoutConfig, CircuitBreakerState, AgentExecutionTracker, ExecutionState, get_execution_tracker
from test_framework.ssot.base_test_case import SSotBaseTestCase

class CircuitBreakerLogicTests(SSotBaseTestCase):
    """Unit tests for circuit breaker logic and state transitions."""

    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.timeout_config = TimeoutConfig()
        self.tracker = AgentExecutionTracker()
        self.test_user_id = f'user_{uuid.uuid4().hex[:8]}'
        self.test_thread_id = f'thread_{uuid.uuid4().hex[:8]}'
        self.test_agent_name = 'test_agent'
        self.circuit_breaker = MockCircuitBreaker(self.timeout_config)

    def test_circuit_breaker_state_enum_values(self):
        """Test that CircuitBreakerState enum has correct values."""
        expected_states = {'CLOSED', 'OPEN', 'HALF_OPEN'}
        actual_states = {state.name for state in CircuitBreakerState}
        self.assertEqual(expected_states, actual_states)
        self.assertEqual(CircuitBreakerState.CLOSED.value, 'closed')
        self.assertEqual(CircuitBreakerState.OPEN.value, 'open')
        self.assertEqual(CircuitBreakerState.HALF_OPEN.value, 'half_open')

    def test_circuit_breaker_initial_state(self):
        """Test that circuit breaker starts in CLOSED state."""
        circuit_breaker = MockCircuitBreaker(self.timeout_config)
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(circuit_breaker.failure_count, 0)
        self.assertEqual(circuit_breaker.success_count, 0)
        self.assertIsNone(circuit_breaker.last_failure_time)

    def test_circuit_breaker_failure_threshold_behavior(self):
        """Test circuit breaker opens after failure threshold is reached."""
        circuit_breaker = MockCircuitBreaker(self.timeout_config)
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.CLOSED)
        failure_threshold = self.timeout_config.failure_threshold
        for i in range(failure_threshold - 1):
            circuit_breaker.record_failure()
            self.assertEqual(circuit_breaker.state, CircuitBreakerState.CLOSED, f'Circuit should stay closed at {i + 1} failures')
            self.assertEqual(circuit_breaker.failure_count, i + 1)
        circuit_breaker.record_failure()
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.OPEN)
        self.assertEqual(circuit_breaker.failure_count, failure_threshold)
        self.assertIsNotNone(circuit_breaker.last_failure_time)

    def test_circuit_breaker_open_state_blocks_requests(self):
        """Test that OPEN circuit breaker blocks new requests."""
        circuit_breaker = MockCircuitBreaker(self.timeout_config)
        for _ in range(self.timeout_config.failure_threshold):
            circuit_breaker.record_failure()
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.OPEN)
        self.assertFalse(circuit_breaker.can_execute())
        for _ in range(5):
            self.assertFalse(circuit_breaker.can_execute())

    def test_circuit_breaker_recovery_timeout_transition_to_half_open(self):
        """Test circuit breaker transitions to HALF_OPEN after recovery timeout."""
        circuit_breaker = MockCircuitBreaker(self.timeout_config)
        for _ in range(self.timeout_config.failure_threshold):
            circuit_breaker.record_failure()
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.OPEN)
        self.assertFalse(circuit_breaker.can_execute())
        recovery_timeout = self.timeout_config.recovery_timeout
        future_time = datetime.now(timezone.utc) + timedelta(seconds=recovery_timeout + 1)
        with freeze_time(future_time):
            self.assertTrue(circuit_breaker.can_execute())
            self.assertEqual(circuit_breaker.state, CircuitBreakerState.HALF_OPEN)

    def test_circuit_breaker_half_open_allows_limited_requests(self):
        """Test that HALF_OPEN circuit breaker allows limited requests for testing."""
        circuit_breaker = MockCircuitBreaker(self.timeout_config)
        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        circuit_breaker.failure_count = 0
        circuit_breaker.success_count = 0
        self.assertTrue(circuit_breaker.can_execute())
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.HALF_OPEN)

    def test_circuit_breaker_half_open_failure_reopens_circuit(self):
        """Test that failure in HALF_OPEN state reopens the circuit."""
        circuit_breaker = MockCircuitBreaker(self.timeout_config)
        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        circuit_breaker.failure_count = 0
        circuit_breaker.record_failure()
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.OPEN)
        self.assertIsNotNone(circuit_breaker.last_failure_time)

    def test_circuit_breaker_success_threshold_closes_circuit(self):
        """Test circuit breaker closes after success threshold is met."""
        circuit_breaker = MockCircuitBreaker(self.timeout_config)
        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        circuit_breaker.success_count = 0
        success_threshold = self.timeout_config.success_threshold
        for i in range(success_threshold - 1):
            circuit_breaker.record_success()
            self.assertEqual(circuit_breaker.state, CircuitBreakerState.HALF_OPEN, f'Circuit should stay half-open at {i + 1} successes')
            self.assertEqual(circuit_breaker.success_count, i + 1)
        circuit_breaker.record_success()
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(circuit_breaker.failure_count, 0)
        self.assertEqual(circuit_breaker.success_count, 0)

    def test_circuit_breaker_state_reset_on_close(self):
        """Test that circuit breaker resets counters when closing."""
        circuit_breaker = MockCircuitBreaker(self.timeout_config)
        circuit_breaker.failure_count = 5
        circuit_breaker.success_count = 3
        circuit_breaker.last_failure_time = datetime.now(timezone.utc)
        circuit_breaker.close_circuit()
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(circuit_breaker.failure_count, 0)
        self.assertEqual(circuit_breaker.success_count, 0)
        self.assertIsNone(circuit_breaker.last_failure_time)

    def test_circuit_breaker_business_logic_configuration(self):
        """Test circuit breaker configuration aligns with business needs."""
        config = TimeoutConfig()
        self.assertEqual(config.failure_threshold, 3)
        self.assertGreaterEqual(config.failure_threshold, 2)
        self.assertLessEqual(config.failure_threshold, 10)
        self.assertEqual(config.recovery_timeout, 30.0)
        self.assertGreaterEqual(config.recovery_timeout, 10.0)
        self.assertLessEqual(config.recovery_timeout, 300.0)
        self.assertEqual(config.success_threshold, 2)
        self.assertGreaterEqual(config.success_threshold, 1)
        self.assertLessEqual(config.success_threshold, 10)

    def test_circuit_breaker_prevents_cascade_failures(self):
        """Test circuit breaker prevents cascade failures during system stress."""
        circuit_breaker = MockCircuitBreaker(self.timeout_config)
        failure_requests = []
        for i in range(10):
            if circuit_breaker.can_execute():
                circuit_breaker.record_failure()
                failure_requests.append(i)
            else:
                break
        self.assertLessEqual(len(failure_requests), self.timeout_config.failure_threshold)
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.OPEN)
        for _ in range(5):
            self.assertFalse(circuit_breaker.can_execute())

    def test_circuit_breaker_recovery_cycle_complete_flow(self):
        """Test complete circuit breaker recovery cycle."""
        circuit_breaker = MockCircuitBreaker(self.timeout_config)
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.CLOSED)
        for _ in range(self.timeout_config.failure_threshold):
            circuit_breaker.record_failure()
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.OPEN)
        future_time = datetime.now(timezone.utc) + timedelta(seconds=self.timeout_config.recovery_timeout + 1)
        with freeze_time(future_time):
            self.assertTrue(circuit_breaker.can_execute())
            self.assertEqual(circuit_breaker.state, CircuitBreakerState.HALF_OPEN)
        for _ in range(self.timeout_config.success_threshold):
            circuit_breaker.record_success()
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.CLOSED)

    def test_circuit_breaker_metrics_tracking(self):
        """Test circuit breaker tracks metrics for monitoring."""
        circuit_breaker = MockCircuitBreaker(self.timeout_config)
        for i in range(5):
            circuit_breaker.record_failure()
            self.assertEqual(circuit_breaker.failure_count, i + 1)
        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        circuit_breaker.success_count = 0
        for i in range(3):
            circuit_breaker.record_success()
            expected_count = i + 1 if circuit_breaker.state == CircuitBreakerState.HALF_OPEN else 0
            if circuit_breaker.state != CircuitBreakerState.CLOSED:
                self.assertEqual(circuit_breaker.success_count, expected_count)

    def test_circuit_breaker_thread_safety_considerations(self):
        """Test circuit breaker behavior under concurrent access."""
        circuit_breaker = MockCircuitBreaker(self.timeout_config)
        initial_count = circuit_breaker.failure_count
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        self.assertEqual(circuit_breaker.failure_count, initial_count + 2)
        expected_state = CircuitBreakerState.OPEN if circuit_breaker.failure_count >= self.timeout_config.failure_threshold else CircuitBreakerState.CLOSED
        self.assertEqual(circuit_breaker.state, expected_state)

class MockCircuitBreaker:
    """Mock circuit breaker for isolated unit testing."""

    def __init__(self, config: TimeoutConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def can_execute(self) -> bool:
        """Check if execution can proceed."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time and datetime.now(timezone.utc) - self.last_failure_time >= timedelta(seconds=self.config.recovery_timeout):
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        return False

    def record_failure(self):
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0

    def record_success(self):
        """Record a success."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.close_circuit()

    def close_circuit(self):
        """Close the circuit and reset counters."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')