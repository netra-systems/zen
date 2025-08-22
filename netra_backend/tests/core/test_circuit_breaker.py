"""Comprehensive tests for circuit breaker implementation.

This module tests the circuit breaker functionality including:
- State transitions (closed/open/half-open)
- Failure threshold handling
- Recovery timeout behavior
- Metrics collection
- Error handling and edge cases
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add project root to path
from app.core.circuit_breaker import (
    # Add project root to path
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitConfig,
    CircuitMetrics,
    CircuitState,
    circuit_registry,
)


class TestCircuitConfig:
    """Test circuit breaker configuration."""
    
    def test_config_creation_with_defaults(self):
        """Test creating config with default values."""
        config = CircuitConfig(name="test")
        
        assert config.name == "test"
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 30.0
        assert config.half_open_max_calls == 3
        assert config.timeout_seconds == 10.0
    
    def test_config_creation_with_custom_values(self):
        """Test creating config with custom values."""
        config = CircuitConfig(
            name="custom",
            failure_threshold=3,
            recovery_timeout=60.0,
            half_open_max_calls=2,
            timeout_seconds=15.0
        )
        
        assert config.name == "custom"
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 60.0
        assert config.half_open_max_calls == 2
        assert config.timeout_seconds == 15.0
    
    def test_config_validation_failure_threshold(self):
        """Test config validation for failure threshold."""
        with pytest.raises(ValueError, match="failure_threshold must be positive"):
            CircuitConfig(name="test", failure_threshold=0)
        
        with pytest.raises(ValueError, match="failure_threshold must be positive"):
            CircuitConfig(name="test", failure_threshold=-1)
    
    def test_config_validation_timeouts(self):
        """Test config validation for timeouts."""
        with pytest.raises(ValueError, match="recovery_timeout must be positive"):
            CircuitConfig(name="test", recovery_timeout=0)
        
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            CircuitConfig(name="test", timeout_seconds=0)
    
    def test_config_validation_half_open(self):
        """Test config validation for half-open calls."""
        with pytest.raises(ValueError, match="half_open_max_calls must be positive"):
            CircuitConfig(name="test", half_open_max_calls=0)


class TestCircuitBreaker:
    """Test circuit breaker core functionality."""
    
    def setup_method(self):
        """Set up test circuit breaker."""
        self.config = CircuitConfig(
            name="test_circuit",
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for testing
            timeout_seconds=1.0
        )
        self.circuit = CircuitBreaker(self.config)
    
    def test_initial_state(self):
        """Test circuit breaker initial state."""
        assert self.circuit.state == CircuitState.CLOSED
        assert self.circuit.metrics.total_calls == 0
        assert self.circuit.metrics.successful_calls == 0
        assert self.circuit.metrics.failed_calls == 0
    
    async def test_successful_call(self):
        """Test successful function call."""
        async def success_func():
            return "success"
        
        result = await self.circuit.call(success_func)
        
        assert result == "success"
        assert self.circuit.state == CircuitState.CLOSED
        assert self.circuit.metrics.successful_calls == 1
        assert self.circuit.metrics.total_calls == 1
    
    async def test_failed_call(self):
        """Test failed function call."""
        async def fail_func():
            raise ValueError("test error")
        
        with pytest.raises(ValueError, match="test error"):
            await self.circuit.call(fail_func)
        
        assert self.circuit.state == CircuitState.CLOSED
        assert self.circuit.metrics.failed_calls == 1
        assert self.circuit.metrics.total_calls == 1
    
    async def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold."""
        async def fail_func():
            raise ValueError("test error")
        
        # Cause failures up to threshold
        for i in range(self.config.failure_threshold):
            with pytest.raises(ValueError):
                await self.circuit.call(fail_func)
        
        assert self.circuit.state == CircuitState.OPEN
        assert self.circuit.metrics.failed_calls == self.config.failure_threshold
    
    async def test_circuit_rejects_when_open(self):
        """Test circuit rejects calls when open."""
        async def fail_func():
            raise ValueError("test error")
        
        # Open the circuit
        for i in range(self.config.failure_threshold):
            with pytest.raises(ValueError):
                await self.circuit.call(fail_func)
        
        assert self.circuit.state == CircuitState.OPEN
        
        # Should reject new calls
        async def success_func():
            return "success"
        
        with pytest.raises(CircuitBreakerOpenError):
            await self.circuit.call(success_func)
        
        assert self.circuit.metrics.rejected_calls == 1
    
    async def test_circuit_recovery_to_half_open(self):
        """Test circuit recovery to half-open state."""
        async def fail_func():
            raise ValueError("test error")
        
        # Open the circuit
        for i in range(self.config.failure_threshold):
            with pytest.raises(ValueError):
                await self.circuit.call(fail_func)
        
        assert self.circuit.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(self.config.recovery_timeout + 0.1)
        
        # Next call should transition to half-open
        async def success_func():
            return "success"
        
        result = await self.circuit.call(success_func)
        
        assert result == "success"
        assert self.circuit.state == CircuitState.CLOSED  # Should close after success
    
    async def test_half_open_state_behavior(self):
        """Test half-open state behavior."""
        # Manually set circuit to half-open
        self.circuit.state = CircuitState.HALF_OPEN
        self.circuit._half_open_calls = 0
        
        async def success_func():
            return "success"
        
        # Should allow limited calls in half-open
        can_execute = await self.circuit._can_execute()
        assert can_execute is True
        
        # Simulate reaching half-open limit
        self.circuit._half_open_calls = self.config.half_open_max_calls
        can_execute = await self.circuit._can_execute()
        assert can_execute is False
    
    async def test_timeout_handling(self):
        """Test timeout handling in circuit breaker."""
        async def slow_func():
            await asyncio.sleep(2.0)  # Longer than timeout
            return "slow"
        
        with pytest.raises(asyncio.TimeoutError):
            await self.circuit.call(slow_func)
        
        assert self.circuit.metrics.timeouts == 1
        assert self.circuit.metrics.failed_calls == 1
    
    async def test_sync_function_call(self):
        """Test calling synchronous functions."""
        def sync_func():
            return "sync_result"
        
        result = await self.circuit.call(sync_func)
        assert result == "sync_result"
    
    def test_get_status(self):
        """Test getting circuit breaker status."""
        status = self.circuit.get_status()
        
        assert status["name"] == self.config.name
        assert status["state"] == CircuitState.CLOSED.value
        assert "config" in status
        assert "metrics" in status
        assert "health" in status
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        # No calls yet
        assert self.circuit._calculate_success_rate() == 1.0
        
        # Add some metrics
        self.circuit.metrics.total_calls = 10
        self.circuit.metrics.successful_calls = 8
        
        assert self.circuit._calculate_success_rate() == 0.8


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry functionality."""
    
    async def test_get_circuit_creates_new(self):
        """Test getting circuit creates new instance."""
        config = CircuitConfig(name="registry_test")
        circuit = await circuit_registry.get_circuit("registry_test", config)
        
        assert circuit.config.name == "registry_test"
        assert isinstance(circuit, CircuitBreaker)
    
    async def test_get_circuit_returns_existing(self):
        """Test getting existing circuit returns same instance."""
        config = CircuitConfig(name="existing_test")
        circuit1 = await circuit_registry.get_circuit("existing_test", config)
        circuit2 = await circuit_registry.get_circuit("existing_test")
        
        assert circuit1 is circuit2
    
    async def test_get_all_status(self):
        """Test getting status of all circuits."""
        config1 = CircuitConfig(name="test1")
        config2 = CircuitConfig(name="test2")
        
        await circuit_registry.get_circuit("test1", config1)
        await circuit_registry.get_circuit("test2", config2)
        
        all_status = await circuit_registry.get_all_status()
        
        assert "test1" in all_status
        assert "test2" in all_status


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker."""
    
    async def test_realistic_failure_recovery_cycle(self):
        """Test realistic failure and recovery cycle."""
        config = CircuitConfig(
            name="integration_test",
            failure_threshold=2,
            recovery_timeout=0.5,
            timeout_seconds=0.5
        )
        circuit = CircuitBreaker(config)
        
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            
            # Fail first 2 calls, then succeed
            if call_count <= 2:
                raise ValueError(f"Failure {call_count}")
            return f"Success {call_count}"
        
        # First two calls should fail and open circuit
        with pytest.raises(ValueError):
            await circuit.call(flaky_func)
        
        with pytest.raises(ValueError):
            await circuit.call(flaky_func)
        
        assert circuit.state == CircuitState.OPEN
        
        # Third call should be rejected immediately
        with pytest.raises(CircuitBreakerOpenError):
            await circuit.call(flaky_func)
        
        # Wait for recovery
        await asyncio.sleep(0.6)
        
        # Fourth call should succeed and close circuit
        result = await circuit.call(flaky_func)
        assert result == "Success 3"
        assert circuit.state == CircuitState.CLOSED
    
    async def test_concurrent_calls(self):
        """Test circuit breaker with concurrent calls."""
        config = CircuitConfig(name="concurrent_test", failure_threshold=5)
        circuit = CircuitBreaker(config)
        
        async def test_func(delay: float):
            await asyncio.sleep(delay)
            return f"result_{delay}"
        
        # Start multiple concurrent calls
        tasks = [
            circuit.call(lambda: test_func(0.1)),
            circuit.call(lambda: test_func(0.2)),
            circuit.call(lambda: test_func(0.3))
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert circuit.metrics.successful_calls == 3
        assert circuit.metrics.total_calls == 3
    
    async def test_error_type_tracking(self):
        """Test tracking of different error types."""
        circuit = CircuitBreaker(CircuitConfig(name="error_tracking"))
        
        async def value_error_func():
            raise ValueError("value error")
        
        async def type_error_func():
            raise TypeError("type error")
        
        with pytest.raises(ValueError):
            await circuit.call(value_error_func)
        
        with pytest.raises(TypeError):
            await circuit.call(type_error_func)
        
        with pytest.raises(ValueError):
            await circuit.call(value_error_func)
        
        failure_types = circuit.metrics.failure_types
        assert failure_types["ValueError"] == 2
        assert failure_types["TypeError"] == 1
class TestCircuitBreakerEdgeCases:
    """Test edge cases and error conditions."""
    
    async def test_recovery_with_immediate_failure(self):
        """Test recovery attempt that immediately fails."""
        config = CircuitConfig(
            name="edge_test",
            failure_threshold=1,
            recovery_timeout=0.1,
            half_open_max_calls=1
        )
        circuit = CircuitBreaker(config)
        
        async def fail_func():
            raise ValueError("always fails")
        
        # Open circuit
        with pytest.raises(ValueError):
            await circuit.call(fail_func)
        
        assert circuit.state == CircuitState.OPEN
        
        # Wait for recovery
        await asyncio.sleep(0.2)
        
        # Recovery attempt should fail and reopen circuit
        with pytest.raises(ValueError):
            await circuit.call(fail_func)
        
        assert circuit.state == CircuitState.OPEN
    
    async def test_multiple_recovery_attempts(self):
        """Test multiple recovery attempts."""
        config = CircuitConfig(
            name="multi_recovery",
            failure_threshold=1,
            recovery_timeout=0.1
        )
        circuit = CircuitBreaker(config)
        
        attempt_count = 0
        
        async def conditional_func():
            nonlocal attempt_count
            attempt_count += 1
            
            # Fail first 3 recovery attempts, succeed on 4th
            if attempt_count <= 3:
                raise ValueError(f"Attempt {attempt_count}")
            return f"Success on attempt {attempt_count}"
        
        # Open circuit
        with pytest.raises(ValueError):
            await circuit.call(conditional_func)
        
        assert circuit.state == CircuitState.OPEN
        
        # Multiple recovery cycles
        for i in range(3):
            await asyncio.sleep(0.15)  # Wait for recovery timeout
            
            with pytest.raises(ValueError):
                await circuit.call(conditional_func)
            
            assert circuit.state == CircuitState.OPEN
        
        # Final successful recovery
        await asyncio.sleep(0.15)
        result = await circuit.call(conditional_func)
        
        assert result == "Success on attempt 4"
        assert circuit.state == CircuitState.CLOSED
    
    async def test_zero_timeout_edge_case(self):
        """Test edge case with very small timeouts."""
        config = CircuitConfig(
            name="zero_timeout",
            timeout_seconds=0.001  # Very small timeout
        )
        circuit = CircuitBreaker(config)
        
        async def instant_func():
            return "instant"
        
        # Should succeed for instant function
        result = await circuit.call(instant_func)
        assert result == "instant"
        
        async def slow_func():
            await asyncio.sleep(0.01)  # 10ms > 1ms timeout
            return "slow"
        
        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            await circuit.call(slow_func)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])