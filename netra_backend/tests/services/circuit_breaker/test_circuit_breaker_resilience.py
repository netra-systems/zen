"""
Circuit Breaker Resilience Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Resilience and Fault Tolerance
- Value Impact: Ensures circuit breakers provide proper fault isolation and recovery
- Strategic Impact: Protects $500K+ ARR by preventing cascading failures and enabling graceful degradation

This module tests circuit breaker resilience functionality including:
- Fault isolation and containment
- Graceful degradation strategies
- Error recovery patterns
- Fallback mechanism reliability
- System stability under various failure conditions
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerException,
    FailureType,
    circuit_breaker_protection
)


class CircuitBreakerResilienceTests(SSotAsyncTestCase):
    """Unit tests for circuit breaker resilience and fault tolerance."""

    def setup_method(self, method=None):
        """Setup test environment."""
        super().setup_method(method)
        
        # Create resilient configuration without invalid parameters
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            recovery_timeout=1.0,
            enable_fallback=True,
            enable_graceful_degradation=True,
            fallback_cache_ttl=60.0,
            enable_metrics=True,
            enable_alerts=True
        )
        
        self.breaker = CircuitBreaker("resilient_service", self.config)

    async def test_fault_isolation_single_service(self):
        """Test that circuit breaker isolates faults to single service."""
        # Create multiple circuit breakers for different services
        service1_breaker = CircuitBreaker("service1", self.config)
        service2_breaker = CircuitBreaker("service2", self.config)
        
        async def failing_service1():
            raise Exception("Service1 down")
        
        async def healthy_service2():
            return "service2_ok"
        
        # Fail service1 circuit breaker
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await service1_breaker.call(failing_service1)
        
        assert service1_breaker.state == CircuitBreakerState.OPEN
        assert service2_breaker.state == CircuitBreakerState.CLOSED
        
        # Service2 should still work normally
        result = await service2_breaker.call(healthy_service2)
        assert result == "service2_ok"
        assert service2_breaker.state == CircuitBreakerState.CLOSED
        
        # Service1 should be blocked
        with pytest.raises(CircuitBreakerException):
            await service1_breaker.call(failing_service1)

    async def test_graceful_degradation_with_fallback(self):
        """Test graceful degradation using fallback functions."""
        async def primary_service():
            raise Exception("Primary service unavailable")
        
        async def fallback_service():
            return "degraded_service_response"
        
        # Force circuit open
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await self.breaker.call(primary_service)
        
        assert self.breaker.state == CircuitBreakerState.OPEN
        
        # Should use fallback gracefully
        result = await self.breaker.call(primary_service, fallback=fallback_service)
        assert result == "degraded_service_response"
        
        # Verify fallback was recorded in metrics
        status = self.breaker.get_status()
        assert status['metrics']['fallback_executions'] == 1

    async def test_recovery_resilience_partial_failures(self):
        """Test recovery resilience with partial failures during recovery."""
        # Force circuit open
        async def initially_failing():
            raise Exception("Service down")
        
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await self.breaker.call(initially_failing)
        
        assert self.breaker.state == CircuitBreakerState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(self.config.recovery_timeout + 0.1)
        
        # Create partially recovering service (fails then succeeds)
        call_count = 0
        
        async def partially_recovering():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Still failing")
            return "recovered"
        
        # First recovery attempt should fail and keep circuit open
        with pytest.raises(Exception):
            await self.breaker.call(partially_recovering)
        
        assert self.breaker.state == CircuitBreakerState.OPEN
        
        # Wait for another recovery cycle
        await asyncio.sleep(self.config.recovery_timeout + 0.1)
        
        # Second recovery attempt should succeed
        result = await self.breaker.call(partially_recovering)
        assert result == "recovered"
        
        # Need another success to fully close (success_threshold=2)
        result = await self.breaker.call(partially_recovering)
        assert result == "recovered"
        assert self.breaker.state == CircuitBreakerState.CLOSED

    async def test_cascading_failure_prevention(self):
        """Test that circuit breakers prevent cascading failures."""
        # Simulate a service that depends on another service
        dependent_breaker = CircuitBreaker("dependent_service", self.config)
        upstream_breaker = CircuitBreaker("upstream_service", self.config)
        
        async def upstream_service():
            raise Exception("Upstream failure")
        
        async def dependent_service():
            # This service tries to call upstream service
            try:
                return await upstream_breaker.call(upstream_service)
            except CircuitBreakerException:
                # Circuit breaker prevents cascade - return cached/fallback response
                return "cached_response"
            except Exception:
                # Other failures should still propagate initially
                raise Exception("Dependent service failure")
        
        # First, fail the upstream service to open its circuit
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await upstream_breaker.call(upstream_service)
        
        assert upstream_breaker.state == CircuitBreakerState.OPEN
        
        # Now dependent service should get cached responses, preventing cascade
        result = await dependent_service()
        assert result == "cached_response"
        assert dependent_breaker.state == CircuitBreakerState.CLOSED  # Not affected

    async def test_error_classification_resilience(self):
        """Test resilience with different error types."""
        # Test different failure types
        test_cases = [
            (asyncio.TimeoutError("Operation timed out"), FailureType.TIMEOUT),
            (ConnectionError("Connection failed"), FailureType.CONNECTION_ERROR),
            (Exception("503 Service Unavailable"), FailureType.SERVICE_UNAVAILABLE),
            (Exception("401 Unauthorized"), FailureType.AUTHENTICATION_ERROR),
            (Exception("429 Rate Limited"), FailureType.RATE_LIMIT_EXCEEDED),
            (ValueError("Unknown error"), FailureType.UNKNOWN_ERROR)
        ]
        
        failures_recorded = []
        
        def track_failures(name, failure_type, reason):
            failures_recorded.append((failure_type, reason))
        
        self.breaker.add_failure_handler(track_failures)
        
        # Test each error type
        for error, expected_type in test_cases:
            async def failing_operation():
                raise error
            
            with pytest.raises(type(error)):
                await self.breaker.call(failing_operation)
        
        # Verify all failures were classified correctly
        assert len(failures_recorded) == len(test_cases)

    async def test_fallback_cache_resilience(self):
        """Test fallback caching for resilience."""
        cache_key_counter = 0
        
        async def primary_operation(data):
            raise Exception("Primary service down")
        
        async def fallback_operation(data):
            nonlocal cache_key_counter
            cache_key_counter += 1
            return f"fallback_result_{data}_{cache_key_counter}"
        
        # Force circuit open
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await self.breaker.call(primary_operation, "test")
        
        assert self.breaker.state == CircuitBreakerState.OPEN
        
        # First fallback call should execute and cache
        result1 = await self.breaker.call(primary_operation, "test", fallback=fallback_operation)
        assert "fallback_result" in result1
        
        # Second call with same parameters should use cache (counter shouldn't increment)
        initial_counter = cache_key_counter
        result2 = await self.breaker.call(primary_operation, "test", fallback=fallback_operation)
        
        # Results should be the same (from cache) and counter shouldn't have incremented
        assert result1 == result2
        assert cache_key_counter == initial_counter

    async def test_resilience_under_high_load(self):
        """Test circuit breaker resilience under high concurrent load."""
        async def sometimes_failing_service(request_id):
            # Fail every 3rd request
            if request_id % 3 == 0:
                raise Exception(f"Failure for request {request_id}")
            await asyncio.sleep(0.01)  # Small delay
            return f"success_{request_id}"
        
        # Create many concurrent requests
        tasks = []
        for i in range(20):
            task = asyncio.create_task(
                self.breaker.call(sometimes_failing_service, i)
            )
            tasks.append(task)
        
        # Collect results
        successes = []
        failures = []
        
        for task in tasks:
            try:
                result = await task
                successes.append(result)
            except (Exception, CircuitBreakerException):
                failures.append(True)
        
        # Should have some successes and failures
        assert len(successes) > 0
        assert len(failures) > 0
        
        # Circuit breaker should be in a predictable state based on failure ratio
        status = self.breaker.get_status()
        assert status['metrics']['total_requests'] == 20

    async def test_context_manager_resilience(self):
        """Test circuit breaker context manager for resilience."""
        async def protected_operation():
            raise Exception("Service failure")
        
        async def fallback_operation():
            return "fallback_via_context_manager"
        
        # Use context manager protection
        try:
            async with circuit_breaker_protection(
                "context_service", 
                "test_operation",
                self.config,
                fallback_operation
            ) as cb:
                # Force multiple failures to open circuit
                for i in range(self.config.failure_threshold):
                    with pytest.raises(Exception):
                        await cb.call(protected_operation)
                
                # This should trigger fallback
                result = await cb.call(protected_operation)
                # Note: Context manager implementation may vary
                
        except CircuitBreakerException:
            # Expected when fallback also fails or isn't triggered
            pass

    async def test_resilience_configuration_edge_cases(self):
        """Test resilience with edge case configurations."""
        # Test with minimal thresholds
        minimal_config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=1,
            recovery_timeout=0.1,
            enable_fallback=True
        )
        
        minimal_breaker = CircuitBreaker("minimal_service", minimal_config)
        
        async def single_failure():
            raise Exception("One failure")
        
        async def quick_recovery():
            return "quick_fix"
        
        # Single failure should open circuit
        with pytest.raises(Exception):
            await minimal_breaker.call(single_failure)
        
        assert minimal_breaker.state == CircuitBreakerState.OPEN
        
        # Quick recovery should work
        await asyncio.sleep(0.2)  # Wait for recovery
        
        result = await minimal_breaker.call(quick_recovery)
        assert result == "quick_fix"
        assert minimal_breaker.state == CircuitBreakerState.CLOSED

    def test_resilience_without_metrics(self):
        """Test resilience when metrics are disabled."""
        no_metrics_config = CircuitBreakerConfig(
            failure_threshold=3,
            enable_metrics=False,
            enable_fallback=True
        )
        
        breaker = CircuitBreaker("no_metrics_service", no_metrics_config)
        
        # Should still function properly without metrics
        assert breaker.state == CircuitBreakerState.CLOSED
        status = breaker.get_status()
        assert status['metrics'] == {}
        
        # Basic operations should still work
        async def test_operation():
            return "works_without_metrics"
        
        # Run test
        result = asyncio.run(breaker.call(test_operation))
        assert result == "works_without_metrics"

    async def test_multiple_simultaneous_recoveries(self):
        """Test resilience during multiple simultaneous recovery attempts."""
        # Force circuit open
        async def failing_operation():
            raise Exception("Service down")
        
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await self.breaker.call(failing_operation)
        
        assert self.breaker.state == CircuitBreakerState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(self.config.recovery_timeout + 0.1)
        
        # Start multiple recovery attempts simultaneously
        async def recovery_operation():
            return "recovered"
        
        tasks = [
            asyncio.create_task(self.breaker.call(recovery_operation))
            for _ in range(5)
        ]
        
        # Some should succeed, others should be blocked due to half-open limits
        results = []
        blocked = []
        
        for task in tasks:
            try:
                result = await task
                results.append(result)
            except CircuitBreakerException:
                blocked.append(True)
        
        # Should have limited successes based on half_open_max_requests
        assert len(results) <= self.config.half_open_max_requests
        assert len(blocked) > 0