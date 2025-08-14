"""
Comprehensive reliability mechanism test suite for Netra agents.
Tests circuit breakers, retry logic, timeouts, and system resilience patterns.
Architectural compliance: ≤300 lines, ≤8 lines per function.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any

from app.core.reliability import AgentReliabilityWrapper, get_reliability_wrapper
from app.core.reliability_circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState
)
from app.core.reliability_retry import RetryHandler, RetryConfig
from app.core.exceptions_service import ServiceTimeoutError, ServiceError


class TestCircuitBreakerThresholds:
    """Test circuit breaker threshold triggering behavior"""
    
    def test_circuit_breaker_closes_initially(self):
        """Circuit breaker starts in CLOSED state"""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(config)
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.can_execute() == True
    
    def test_circuit_opens_after_threshold(self):
        """Circuit opens after reaching failure threshold"""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker(config)
        cb.record_failure("TestError")
        cb.record_failure("TestError")
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.can_execute() == False
    
    def test_circuit_tracks_failure_metrics(self):
        """Circuit breaker tracks failure metrics correctly"""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(config)
        cb.record_failure("ValueError")
        cb.record_failure("ConnectionError")
        assert cb.metrics.failed_calls == 2
        assert cb.metrics.error_types["ValueError"] == 1
        assert cb.metrics.error_types["ConnectionError"] == 1


class TestCircuitBreakerStateTransitions:
    """Test circuit breaker state transition behavior"""
    
    def test_closed_to_open_transition(self):
        """Test transition from CLOSED to OPEN state"""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker(config)
        cb.record_failure("Error1")
        assert cb.state == CircuitBreakerState.CLOSED
        cb.record_failure("Error2")
        assert cb.state == CircuitBreakerState.OPEN
    
    def test_open_to_half_open_transition(self):
        """Test transition from OPEN to HALF_OPEN after timeout"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.01)
        cb = CircuitBreaker(config)
        cb.record_failure("Error")
        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(0.02)
        assert cb.can_execute() == True
        assert cb.state == CircuitBreakerState.HALF_OPEN
    
    def test_half_open_to_closed_recovery(self):
        """Test successful recovery from HALF_OPEN to CLOSED"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.01)
        cb = CircuitBreaker(config)
        cb.record_failure("Error")
        time.sleep(0.02)
        cb.can_execute()
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
    
    def test_half_open_to_open_on_failure(self):
        """Test failure in HALF_OPEN state returns to OPEN"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.01)
        cb = CircuitBreaker(config)
        cb.record_failure("Error")
        time.sleep(0.02)
        cb.can_execute()
        cb.record_failure("Error2")
        assert cb.state == CircuitBreakerState.OPEN


class TestRetryExponentialBackoff:
    """Test retry handler exponential backoff timing"""
    
    @pytest.mark.asyncio
    async def test_retry_exponential_timing(self):
        """Test exponential backoff timing accuracy"""
        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        handler = RetryHandler(config)
        call_times = []
        
        async def failing_operation():
            call_times.append(time.time())
            raise ValueError("Test failure")
        
        with pytest.raises(ValueError):
            await handler.execute_with_retry(failing_operation)
        
        self._verify_exponential_delays(call_times)
    
    def _verify_exponential_delays(self, call_times):
        """Verify exponential delay progression"""
        assert len(call_times) == 4
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        assert delay1 >= 0.01
        assert delay2 >= 0.02
    
    @pytest.mark.asyncio
    async def test_retry_max_delay_cap(self):
        """Test retry respects maximum delay cap"""
        config = RetryConfig(max_retries=5, base_delay=1.0, max_delay=2.0, jitter=False)
        handler = RetryHandler(config)
        
        delay = handler._calculate_delay(10)
        assert delay <= 2.0
    
    @pytest.mark.asyncio
    async def test_retry_jitter_variation(self):
        """Test jitter adds randomness to delays"""
        config = RetryConfig(base_delay=1.0, jitter=True)
        handler = RetryHandler(config)
        
        delays = [handler._calculate_delay(1) for _ in range(10)]
        unique_delays = set(delays)
        assert len(unique_delays) > 1


class TestRetrySelectiveLogic:
    """Test selective retry logic for different error types"""
    
    @pytest.mark.asyncio
    async def test_non_retryable_errors_fail_immediately(self):
        """Non-retryable errors should fail without retry"""
        config = RetryConfig(max_retries=3, base_delay=0.01)
        handler = RetryHandler(config)
        call_count = 0
        
        async def validation_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Validation failed")
        
        wrapper = AgentReliabilityWrapper("test_agent", retry_config=config)
        
        with pytest.raises(ValueError):
            await wrapper.execute_safely(validation_error, "test_op")
        
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retryable_errors_retry_properly(self):
        """Retryable errors should be retried"""
        config = RetryConfig(max_retries=2, base_delay=0.01)
        handler = RetryHandler(config)
        call_count = 0
        
        async def connection_error():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Network failure")
        
        with pytest.raises(ConnectionError):
            await handler.execute_with_retry(connection_error)
        
        assert call_count == 3


class TestTimeoutHandling:
    """Test timeout handling at various levels"""
    
    @pytest.mark.asyncio
    async def test_operation_timeout_enforcement(self):
        """Test operation timeout is enforced"""
        wrapper = AgentReliabilityWrapper("test_agent")
        
        async def slow_operation():
            await asyncio.sleep(1.0)
            return "completed"
        
        start_time = time.time()
        with pytest.raises(asyncio.TimeoutError):
            await wrapper.execute_safely(slow_operation, "slow_op", timeout=0.1)
        
        elapsed = time.time() - start_time
        assert elapsed < 10.0
    
    @pytest.mark.asyncio
    async def test_cascading_timeout_handling(self):
        """Test timeout handling cascades properly"""
        config = RetryConfig(max_retries=2, base_delay=0.01)
        wrapper = AgentReliabilityWrapper("test_agent", retry_config=config)
        
        async def timeout_operation():
            await asyncio.sleep(0.1)
            return "success"
        
        with pytest.raises(asyncio.TimeoutError):
            await wrapper.execute_safely(timeout_operation, "test_op", timeout=0.01)
    
    @pytest.mark.asyncio
    async def test_timeout_with_fallback(self):
        """Test timeout handling with fallback execution"""
        wrapper = AgentReliabilityWrapper("test_agent")
        
        async def slow_operation():
            await asyncio.sleep(1.0)
            return "slow_result"
        
        async def fast_fallback():
            return "fallback_result"
        
        result = await wrapper.execute_safely(
            slow_operation, "test_op", fallback=fast_fallback, timeout=0.01
        )
        assert result == "fallback_result"


class TestResourceIsolation:
    """Test resource isolation mechanisms"""
    
    def test_agent_isolation_registry(self):
        """Test agents have isolated reliability wrappers"""
        wrapper1 = get_reliability_wrapper("agent1")
        wrapper2 = get_reliability_wrapper("agent2")
        
        wrapper1.circuit_breaker.record_failure("Error")
        
        assert wrapper1.circuit_breaker.failure_count == 1
        assert wrapper2.circuit_breaker.failure_count == 0
    
    def test_error_history_isolation(self):
        """Test error history is isolated per agent"""
        wrapper1 = get_reliability_wrapper("agent1")
        wrapper2 = get_reliability_wrapper("agent2")
        
        wrapper1._track_error("op1", ValueError("Error1"))
        wrapper2._track_error("op2", ConnectionError("Error2"))
        
        assert len(wrapper1.error_history) == 1
        assert len(wrapper2.error_history) == 1
        assert wrapper1.error_history[0]["error_type"] == "ValueError"
        assert wrapper2.error_history[0]["error_type"] == "ConnectionError"


class TestFailureScenarios:
    """Test realistic failure scenarios"""
    
    @pytest.mark.asyncio
    async def test_sustained_high_error_rate(self):
        """Test behavior under sustained high error rate"""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=0.1)
        wrapper = AgentReliabilityWrapper("test_agent", circuit_breaker_config=config)
        
        async def always_fails():
            raise ServiceError("Persistent failure")
        
        for _ in range(5):
            with pytest.raises((ServiceError, RuntimeError)):
                await wrapper.execute_safely(always_fails, "failing_op")
        
        assert wrapper.circuit_breaker.state == CircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_intermittent_failures(self):
        """Test handling of intermittent failures"""
        wrapper = AgentReliabilityWrapper("test_agent")
        call_count = 0
        
        async def intermittent_operation():
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                return "success"
            raise ConnectionError("Intermittent failure")
        
        result = await wrapper.execute_safely(intermittent_operation, "intermittent_op")
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_pattern(self):
        """Test graceful degradation with fallback"""
        wrapper = AgentReliabilityWrapper("test_agent")
        
        async def primary_service():
            raise ServiceError("Primary service down")
        
        async def degraded_service():
            return "degraded_response"
        
        result = await wrapper.execute_safely(
            primary_service, "primary_op", fallback=degraded_service
        )
        assert result == "degraded_response"


class TestSystemHealthMonitoring:
    """Test system health monitoring capabilities"""
    
    def test_health_score_calculation(self):
        """Test health score calculation accuracy"""
        wrapper = AgentReliabilityWrapper("test_agent")
        
        wrapper.circuit_breaker.record_success()
        wrapper.circuit_breaker.record_success()
        wrapper.circuit_breaker.record_failure("Error")
        
        health = wrapper.get_health_status()
        assert health["health_score"] > 0.5
    
    def test_metrics_collection_accuracy(self):
        """Test metrics are collected accurately"""
        wrapper = AgentReliabilityWrapper("test_agent")
        
        wrapper.circuit_breaker.record_success()
        wrapper.circuit_breaker.record_failure("TestError")
        
        status = wrapper.circuit_breaker.get_status()
        metrics = status["metrics"]
        
        assert metrics["total_calls"] == 2
        assert metrics["successful_calls"] == 1
        assert metrics["failed_calls"] == 1
        assert metrics["success_rate"] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])