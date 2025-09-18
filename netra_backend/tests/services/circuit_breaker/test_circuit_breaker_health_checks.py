"""
Circuit Breaker Health Checks Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Health Monitoring and Reliability
- Value Impact: Ensures circuit breaker health monitoring works correctly
- Strategic Impact: Protects $500K+ ARR by providing early warning of system issues

This module tests circuit breaker health check functionality including:
- Health status monitoring
- State transition detection
- Performance metrics collection
- Alert generation
- Health summary reporting
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitBreakerState,
    FailureType,
    get_circuit_breaker_manager
)


class CircuitBreakerHealthCheckTests(SSotAsyncTestCase):
    """Unit tests for circuit breaker health check functionality."""

    def setup_method(self, method=None):
        """Setup test environment."""
        super().setup_method(method)
        
        # Create test configurations without invalid parameters
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            enable_metrics=True,
            enable_alerts=True
        )
        
        self.breaker = CircuitBreaker("test_service", self.config)
        self.manager = CircuitBreakerManager()

    def test_healthy_circuit_breaker_status(self):
        """Test health status of a healthy circuit breaker."""
        status = self.breaker.get_status()
        
        assert status['name'] == 'test_service'
        assert status['state'] == CircuitBreakerState.CLOSED.value
        assert status['failure_count'] == 0
        assert status['success_count'] == 0
        assert status['last_failure_time'] is None
        assert status['last_success_time'] is None
        assert status['last_failure_reason'] is None
        
        # Check metrics are included when enabled
        assert 'metrics' in status
        metrics = status['metrics']
        assert metrics['total_requests'] == 0
        assert metrics['success_rate'] == 0.0
        assert metrics['failure_rate'] == 0.0
        assert metrics['fallback_executions'] == 0
        assert metrics['circuit_breaker_opens'] == 0

    async def test_circuit_breaker_health_after_success(self):
        """Test health status after successful operations."""
        # Simulate successful operation
        async def mock_operation():
            return "success"
        
        result = await self.breaker.call(mock_operation)
        assert result == "success"
        
        status = self.breaker.get_status()
        assert status['state'] == CircuitBreakerState.CLOSED.value
        assert status['success_count'] == 1
        assert status['failure_count'] == 0
        assert status['last_success_time'] is not None
        
        metrics = status['metrics']
        assert metrics['total_requests'] == 1
        assert metrics['successful_requests'] == 1
        assert metrics['failed_requests'] == 0
        assert metrics['success_rate'] == 100.0
        assert metrics['failure_rate'] == 0.0

    async def test_circuit_breaker_health_after_failures(self):
        """Test health status after multiple failures."""
        # Simulate multiple failures
        async def failing_operation():
            raise Exception("Service unavailable")
        
        # Fail multiple times but not enough to open circuit
        for i in range(2):
            with pytest.raises(Exception):
                await self.breaker.call(failing_operation)
        
        status = self.breaker.get_status()
        assert status['state'] == CircuitBreakerState.CLOSED.value
        assert status['failure_count'] == 2
        assert status['success_count'] == 0
        assert status['last_failure_time'] is not None
        assert status['last_failure_reason'] == "Service unavailable"
        
        metrics = status['metrics']
        assert metrics['total_requests'] == 2
        assert metrics['successful_requests'] == 0
        assert metrics['failed_requests'] == 2
        assert metrics['success_rate'] == 0.0
        assert metrics['failure_rate'] == 1.0

    async def test_circuit_breaker_health_when_open(self):
        """Test health status when circuit breaker is open."""
        # Force circuit to open by exceeding failure threshold
        async def failing_operation():
            raise Exception("Service down")
        
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await self.breaker.call(failing_operation)
        
        status = self.breaker.get_status()
        assert status['state'] == CircuitBreakerState.OPEN.value
        assert status['failure_count'] == self.config.failure_threshold
        assert status['last_failure_time'] is not None
        assert status['last_failure_reason'] == "Service down"
        
        metrics = status['metrics']
        assert metrics['circuit_breaker_opens'] == 1
        assert metrics['total_requests'] == self.config.failure_threshold

    def test_manager_health_summary_all_healthy(self):
        """Test health summary when all circuit breakers are healthy."""
        # Add multiple healthy circuit breakers
        self.manager.get_circuit_breaker("service1", self.config)
        self.manager.get_circuit_breaker("service2", self.config)
        self.manager.get_circuit_breaker("service3", self.config)
        
        summary = self.manager.get_health_summary()
        
        assert summary['overall_health'] == 'healthy'
        assert summary['total_circuit_breakers'] == 3
        assert summary['closed_breakers'] == 3
        assert summary['open_breakers'] == 0
        assert summary['half_open_breakers'] == 0
        assert summary['open_breaker_names'] == []
        assert summary['half_open_breaker_names'] == []
        assert 'timestamp' in summary

    async def test_manager_health_summary_with_failures(self):
        """Test health summary when some circuit breakers have failed."""
        # Create circuit breakers with different states
        breaker1 = self.manager.get_circuit_breaker("healthy_service", self.config)
        breaker2 = self.manager.get_circuit_breaker("failing_service", self.config)
        
        # Force one circuit breaker to open
        async def failing_operation():
            raise Exception("Service failed")
        
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await breaker2.call(failing_operation)
        
        summary = self.manager.get_health_summary()
        
        assert summary['overall_health'] == 'degraded'  # 50% of services failed
        assert summary['total_circuit_breakers'] == 2
        assert summary['closed_breakers'] == 1
        assert summary['open_breakers'] == 1
        assert summary['half_open_breakers'] == 0
        assert summary['open_breaker_names'] == ['failing_service']
        assert summary['half_open_breaker_names'] == []

    async def test_performance_metrics_collection(self):
        """Test that performance metrics are collected correctly."""
        async def slow_operation():
            await asyncio.sleep(0.1)  # Simulate slow operation
            return "result"
        
        async def fast_operation():
            return "result"
        
        # Execute operations with different performance characteristics
        await self.breaker.call(slow_operation)
        await self.breaker.call(fast_operation)
        
        status = self.breaker.get_status()
        metrics = status['metrics']
        
        assert metrics['total_requests'] == 2
        assert metrics['successful_requests'] == 2
        assert metrics['average_execution_time'] > 0.0
        assert metrics['recent_average_execution_time'] > 0.0

    def test_health_checks_with_disabled_metrics(self):
        """Test health checks when metrics are disabled."""
        config_no_metrics = CircuitBreakerConfig(
            failure_threshold=3,
            enable_metrics=False
        )
        
        breaker = CircuitBreaker("no_metrics_service", config_no_metrics)
        status = breaker.get_status()
        
        assert status['name'] == 'no_metrics_service'
        assert status['state'] == CircuitBreakerState.CLOSED.value
        assert status['metrics'] == {}  # No metrics when disabled

    def test_circuit_breaker_reset_health(self):
        """Test health status after circuit breaker reset."""
        # Set some state
        self.breaker._failure_count = 5
        self.breaker._success_count = 3
        
        # Reset circuit breaker
        self.breaker.reset()
        
        status = self.breaker.get_status()
        assert status['state'] == CircuitBreakerState.CLOSED.value
        assert status['failure_count'] == 0
        assert status['success_count'] == 0
        assert status['last_failure_time'] is None
        assert status['last_success_time'] is None
        assert status['last_failure_reason'] is None

    async def test_health_check_state_transitions(self):
        """Test health monitoring during state transitions."""
        state_changes = []
        
        def track_state_changes(name, old_state, new_state, reason):
            state_changes.append({
                'name': name,
                'old_state': old_state,
                'new_state': new_state,
                'reason': reason
            })
        
        self.breaker.add_state_change_handler(track_state_changes)
        
        # Force state transitions
        async def failing_operation():
            raise Exception("Test failure")
        
        # Transition to OPEN
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await self.breaker.call(failing_operation)
        
        assert len(state_changes) == 1
        assert state_changes[0]['old_state'] == CircuitBreakerState.CLOSED
        assert state_changes[0]['new_state'] == CircuitBreakerState.OPEN
        assert state_changes[0]['reason'].startswith("Failure threshold exceeded")

    def test_all_circuit_breakers_status(self):
        """Test getting status of all circuit breakers."""
        # Create multiple circuit breakers
        breaker1 = self.manager.get_circuit_breaker("service1", self.config)
        breaker2 = self.manager.get_circuit_breaker("service2", self.config)
        
        all_statuses = self.manager.get_all_statuses()
        
        assert len(all_statuses) == 2
        assert 'service1' in all_statuses
        assert 'service2' in all_statuses
        assert all_statuses['service1']['name'] == 'service1'
        assert all_statuses['service2']['name'] == 'service2'
        assert all_statuses['service1']['state'] == CircuitBreakerState.CLOSED.value
        assert all_statuses['service2']['state'] == CircuitBreakerState.CLOSED.value

    def test_global_circuit_breaker_manager_health(self):
        """Test health checks using global circuit breaker manager."""
        from netra_backend.app.resilience.circuit_breaker import get_circuit_breaker_manager
        
        global_manager = get_circuit_breaker_manager()
        
        # Create some circuit breakers through global manager
        global_manager.get_circuit_breaker("global_service1", self.config)
        global_manager.get_circuit_breaker("global_service2", self.config)
        
        summary = global_manager.get_health_summary()
        assert summary['total_circuit_breakers'] >= 2
        assert summary['overall_health'] in ['healthy', 'degraded', 'critical', 'recovering']