"""
Tests for async timeout and retry functionality
Split from test_async_utils.py for architectural compliance (≤300 lines, ≤8 lines per function)
"""

import pytest
import asyncio
import time

from app.core.async_retry_logic import async_timeout, with_timeout, with_retry
from app.core.exceptions_service import ServiceTimeoutError
from app.tests.helpers.async_utils_helpers import (
    create_quick_operation,
    create_slow_operation,
    create_retry_counter,
    create_eventually_successful,
)


class TestAsyncTimeout:
    """Test async timeout functionality"""
    
    @pytest.mark.asyncio
    async def test_async_timeout_success(self):
        """Test successful operation within timeout"""
        async with async_timeout(1.0):
            result = await create_quick_operation()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_async_timeout_failure(self):
        """Test operation exceeding timeout"""
        with pytest.raises(ServiceTimeoutError):
            async with async_timeout(0.01):
                await create_slow_operation()
    
    @pytest.mark.asyncio
    async def test_with_timeout_decorator_success(self):
        """Test timeout decorator with successful operation"""
        @with_timeout(1.0, "test_operation")
        async def decorated_function():
            return await create_quick_operation()
        result = await decorated_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_with_timeout_decorator_failure(self):
        """Test timeout decorator with timeout"""
        @with_timeout(0.01, "slow_operation")
        async def slow_decorated_function():
            return await create_slow_operation()
        with pytest.raises(ServiceTimeoutError):
            await slow_decorated_function()


class TestWithRetry:
    """Test retry decorator functionality"""
    
    @pytest.mark.asyncio
    async def test_with_retry_success_first_attempt(self):
        """Test retry decorator with success on first attempt"""
        counter, increment = create_retry_counter()
        @with_retry(max_attempts=3, delay=0.01)
        async def successful_function():
            increment()
            return "success"
        result = await successful_function()
        assert result == "success"
        assert counter['value'] == 1
    
    @pytest.mark.asyncio
    async def test_with_retry_success_after_failures(self):
        """Test retry decorator with success after failures"""
        counter, increment = create_retry_counter()
        eventually_successful = create_eventually_successful(increment, 3)
        decorated = with_retry(max_attempts=3, delay=0.01)(eventually_successful)
        result = await decorated()
        assert result == "success_after_retries"
        assert counter['value'] == 3
    
    @pytest.mark.asyncio
    async def test_with_retry_exhausts_attempts(self):
        """Test retry decorator when all attempts fail"""
        counter, increment = create_retry_counter()
        @with_retry(max_attempts=2, delay=0.01)
        async def always_fails():
            attempt = increment()
            raise ValueError(f"Attempt {attempt} failed")
        with pytest.raises(ValueError, match="Attempt 2 failed"):
            await always_fails()
        assert counter['value'] == 2
    
    @pytest.mark.asyncio
    async def test_with_retry_exponential_backoff(self):
        """Test retry decorator with exponential backoff"""
        call_times = []
        @with_retry(max_attempts=3, delay=0.01, backoff_factor=2.0)
        async def failing_function():
            call_times.append(time.time())
            raise ValueError("Always fails")
        with pytest.raises(ValueError):
            await failing_function()
        self._assert_exponential_backoff(call_times)
    
    def _assert_exponential_backoff(self, call_times):
        """Assert proper exponential backoff timing"""
        assert len(call_times) == 3
        assert call_times[1] - call_times[0] >= 0.01
        assert call_times[2] - call_times[1] >= 0.02


if __name__ == "__main__":
    pytest.main([__file__, "-v"])