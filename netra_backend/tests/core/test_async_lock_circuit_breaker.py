"""
Tests for AsyncLock and AsyncCircuitBreaker - advanced async patterns
Split from test_async_utils.py for architectural compliance (≤300 lines, ≤8 lines per function)
"""

import pytest
import asyncio

from netra_backend.app.core.async_retry_logic import AsyncLock, AsyncCircuitBreaker
from netra_backend.app.core.exceptions_service import ServiceTimeoutError, ServiceError
from tests.helpers.async_utils_helpers import (
    assert_lock_state,
    create_circuit_breaker_operation,
    assert_circuit_breaker_state,
)


class TestAsyncLock:
    """Test AsyncLock for advanced locking"""
    
    @pytest.fixture
    def async_lock(self):
        return AsyncLock("test_lock")
    async def test_acquire_with_timeout_success(self, async_lock):
        """Test successful lock acquisition with timeout"""
        acquired = await async_lock.acquire_with_timeout(1.0)
        assert acquired == True
        assert_lock_state(async_lock, True, "test_lock")
        async_lock.release()
        assert_lock_state(async_lock, False, "test_lock")
    async def test_acquire_with_timeout_failure(self, async_lock):
        """Test lock acquisition timeout"""
        await async_lock.acquire_with_timeout(1.0)
        acquired = await async_lock.acquire_with_timeout(0.01)
        assert acquired == False
        assert async_lock.is_locked == True
    async def test_acquire_context_manager_success(self, async_lock):
        """Test lock context manager"""
        async with async_lock.acquire(timeout=1.0):
            assert async_lock.is_locked == True
        assert async_lock.is_locked == False
    async def test_acquire_context_manager_timeout(self, async_lock):
        """Test lock context manager timeout"""
        await async_lock.acquire_with_timeout(1.0)
        with pytest.raises(ServiceTimeoutError):
            async with async_lock.acquire(timeout=0.01):
                pass
    
    def test_lock_info(self, async_lock):
        """Test lock information"""
        info = async_lock.lock_info
        assert info["name"] == "test_lock"
        assert info["locked"] == False
        assert info["acquired_at"] == None


class TestAsyncCircuitBreaker:
    """Test AsyncCircuitBreaker pattern"""
    
    @pytest.fixture
    def circuit_breaker(self):
        return AsyncCircuitBreaker(
            failure_threshold=3,
            timeout=0.1,
            expected_exception=(ValueError,)
        )
    async def test_successful_calls(self, circuit_breaker):
        """Test successful calls keep circuit closed"""
        operation = create_circuit_breaker_operation(False)
        for _ in range(5):
            result = await circuit_breaker.call(operation)
            assert result == "success"
        assert_circuit_breaker_state(circuit_breaker, "CLOSED", 0)
    async def test_circuit_opens_after_failures(self, circuit_breaker):
        """Test circuit opens after failure threshold"""
        operation = create_circuit_breaker_operation(True)
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(operation)
        assert_circuit_breaker_state(circuit_breaker, "OPEN", 3)
        with pytest.raises(ServiceError, match="Circuit breaker is OPEN"):
            await circuit_breaker.call(operation)
    async def test_circuit_half_open_recovery(self, circuit_breaker):
        """Test circuit moves to half-open and recovers"""
        await self._open_circuit(circuit_breaker)
        assert_circuit_breaker_state(circuit_breaker, "OPEN", 3)
        await asyncio.sleep(0.11)
        success_operation = create_circuit_breaker_operation(False)
        result = await circuit_breaker.call(success_operation)
        assert result == "success"
        assert_circuit_breaker_state(circuit_breaker, "CLOSED", 0)
    
    async def _open_circuit(self, circuit_breaker):
        """Helper to open circuit breaker"""
        failing_operation = create_circuit_breaker_operation(True)
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_operation)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])