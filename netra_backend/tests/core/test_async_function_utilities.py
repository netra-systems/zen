"""
Focused tests for Async Function Utilities
Tests timeout functions, retry decorators, and global utility functions
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.core.async_utils import (
    async_timeout,
    shutdown_async_utils,
    with_retry,
    with_timeout,
)
from netra_backend.app.core.exceptions_service import ServiceError, ServiceTimeoutError

class TestTimeoutFunctionsComplete:
    """Complete tests for timeout functions."""
    async def test_async_timeout_context_manager(self):
        """Test async_timeout context manager."""
        # Should complete within timeout
        async with async_timeout(1.0):
            await asyncio.sleep(0.1)
        
        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            async with async_timeout(0.1):
                await asyncio.sleep(0.5)
    async def test_with_timeout_decorator(self):
        """Test with_timeout decorator."""
        @with_timeout(0.5)
        async def fast_operation():
            await asyncio.sleep(0.1)
            return "completed"
        
        @with_timeout(0.1)
        async def slow_operation():
            await asyncio.sleep(0.5)
            return "should not complete"
        
        # Fast operation should succeed
        result = await fast_operation()
        assert result == "completed"
        
        # Slow operation should timeout
        with pytest.raises(ServiceTimeoutError):
            await slow_operation()
    async def test_timeout_with_custom_timeout_values(self):
        """Test timeout with various timeout values."""
        @with_timeout(0.2)
        async def operation_with_short_timeout():
            await asyncio.sleep(0.1)
            return "short_success"
        
        @with_timeout(1.0)
        async def operation_with_long_timeout():
            await asyncio.sleep(0.1)
            return "long_success"
        
        # Both should succeed with appropriate timeouts
        result1 = await operation_with_short_timeout()
        result2 = await operation_with_long_timeout()
        
        assert result1 == "short_success"
        assert result2 == "long_success"
    async def test_timeout_cancellation_behavior(self):
        """Test timeout cancellation behavior."""
        cancelled_operations = []
        
        @with_timeout(0.2)
        async def cancellable_operation():
            try:
                await asyncio.sleep(1.0)
                return "should not complete"
            except asyncio.CancelledError:
                cancelled_operations.append("cancelled")
                raise
        
        with pytest.raises(ServiceTimeoutError):
            await cancellable_operation()
        
        # Should have been cancelled
        assert len(cancelled_operations) == 1
    async def test_nested_timeout_operations(self):
        """Test nested timeout operations."""
        @with_timeout(0.5)
        async def outer_operation():
            @with_timeout(0.2)
            async def inner_operation():
                await asyncio.sleep(0.1)
                return "inner_success"
            
            inner_result = await inner_operation()
            await asyncio.sleep(0.1)
            return f"outer_{inner_result}"
        
        result = await outer_operation()
        assert result == "outer_inner_success"
    async def test_timeout_precision(self):
        """Test timeout precision and timing."""
        start_time = time.time()
        
        @with_timeout(0.3)
        async def timed_operation():
            await asyncio.sleep(0.5)
            return "should timeout"
        
        with pytest.raises(ServiceTimeoutError):
            await timed_operation()
        
        execution_time = time.time() - start_time
        # Should timeout close to the specified time (with some tolerance)
        assert 0.25 <= execution_time <= 0.4

class TestRetryDecoratorComplete:
    """Complete tests for retry decorator."""
    async def test_retry_basic_functionality(self):
        """Test basic retry functionality."""
        attempt_count = 0
        
        @with_retry(max_attempts=3, delay=0.1)
        async def sometimes_failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ServiceError(f"Attempt {attempt_count} failed")
            return f"Success on attempt {attempt_count}"
        
        result = await sometimes_failing_operation()
        assert result == "Success on attempt 3"
        assert attempt_count == 3
    async def test_retry_max_attempts_exceeded(self):
        """Test retry when max attempts are exceeded."""
        attempt_count = 0
        
        @with_retry(max_attempts=2, delay=0.05)
        async def always_failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            raise ServiceError(f"Failure {attempt_count}")
        
        with pytest.raises(ServiceError, match="Failure 2"):
            await always_failing_operation()
        
        assert attempt_count == 2
    async def test_retry_with_different_exceptions(self):
        """Test retry with different exception types."""
        attempt_count = 0
        
        @with_retry(max_attempts=3, delay=0.05, exceptions=(ServiceError, ValueError))
        async def multi_exception_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise ServiceError("Service error")
            elif attempt_count == 2:
                raise ValueError("Value error")
            return "success"
        
        result = await multi_exception_operation()
        assert result == "success"
        assert attempt_count == 3
    async def test_retry_with_non_retryable_exception(self):
        """Test retry with non-retryable exceptions."""
        attempt_count = 0
        
        @with_retry(max_attempts=3, delay=0.05, exceptions=(ServiceError,))
        async def mixed_exception_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise ServiceError("Retryable error")
            else:
                raise TypeError("Non-retryable error")  # Not in exceptions list
        
        with pytest.raises(TypeError, match="Non-retryable error"):
            await mixed_exception_operation()
        
        assert attempt_count == 2  # Should retry ServiceError, then fail on TypeError
    async def test_retry_exponential_backoff(self):
        """Test retry with exponential backoff."""
        attempt_times = []
        
        @with_retry(max_attempts=3, delay=0.1, backoff_factor=2.0)
        async def backoff_operation():
            attempt_times.append(time.time())
            if len(attempt_times) < 3:
                raise ServiceError("Retry needed")
            return "success"
        
        result = await backoff_operation()
        assert result == "success"
        
        # Check delay intervals (with tolerance for timing variations)
        if len(attempt_times) >= 3:
            delay1 = attempt_times[1] - attempt_times[0]
            delay2 = attempt_times[2] - attempt_times[1]
            assert 0.08 <= delay1 <= 0.15  # ~0.1 seconds
            assert 0.18 <= delay2 <= 0.25  # ~0.2 seconds (2x backoff)
    async def test_retry_immediate_success(self):
        """Test retry when operation succeeds immediately."""
        attempt_count = 0
        
        @with_retry(max_attempts=3, delay=0.1)
        async def immediate_success_operation():
            nonlocal attempt_count
            attempt_count += 1
            return f"Success on first attempt {attempt_count}"
        
        result = await immediate_success_operation()
        assert result == "Success on first attempt 1"
        assert attempt_count == 1
    async def test_retry_timing_accuracy(self):
        """Test retry timing accuracy."""
        start_time = time.time()
        attempt_count = 0
        
        @with_retry(max_attempts=2, delay=0.2)
        async def timed_retry_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise ServiceError("First attempt fails")
            return "success"
        
        result = await timed_retry_operation()
        total_time = time.time() - start_time
        
        assert result == "success"
        assert 0.18 <= total_time <= 0.3  # Should include delay

class TestGlobalFunctionsComplete:
    """Complete tests for global utility functions."""
    async def test_shutdown_async_utils(self):
        """Test shutdown_async_utils function."""
        # This should complete without errors
        await shutdown_async_utils()
        
        # Should be idempotent
        await shutdown_async_utils()
    async def test_global_utilities_integration(self):
        """Test integration of global utilities."""
        # Test combining timeout and retry
        attempt_count = 0
        
        @with_timeout(1.0)
        @with_retry(max_attempts=2, delay=0.1)
        async def combined_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise ServiceError("First attempt fails")
            await asyncio.sleep(0.1)
            return "combined_success"
        
        result = await combined_operation()
        assert result == "combined_success"
        assert attempt_count == 2
    async def test_utility_functions_with_exceptions(self):
        """Test utility functions with various exception scenarios."""
        @with_timeout(0.5)
        @with_retry(max_attempts=2, delay=0.1)
        async def exception_test_operation(exception_type):
            if exception_type == "timeout":
                await asyncio.sleep(1.0)  # Will timeout
            elif exception_type == "service_error":
                raise ServiceError("Service error")
            elif exception_type == "value_error":
                raise ValueError("Value error")
            return "success"
        
        # Test timeout
        with pytest.raises(ServiceTimeoutError):
            await exception_test_operation("timeout")
        
        # Test retryable error that eventually fails
        with pytest.raises(ServiceError):
            await exception_test_operation("service_error")
        
        # Test non-retryable error
        with pytest.raises(ValueError):
            await exception_test_operation("value_error")
    async def test_decorator_composition_order(self):
        """Test different orders of decorator composition."""
        results = []
        
        # Timeout outside retry
        @with_timeout(0.5)
        @with_retry(max_attempts=2, delay=0.1)
        async def timeout_outside():
            results.append("timeout_outside")
            return "timeout_outside_success"
        
        # Retry outside timeout
        @with_retry(max_attempts=2, delay=0.1)
        @with_timeout(0.5)
        async def retry_outside():
            results.append("retry_outside")
            return "retry_outside_success"
        
        result1 = await timeout_outside()
        result2 = await retry_outside()
        
        assert result1 == "timeout_outside_success"
        assert result2 == "retry_outside_success"
        assert len(results) == 2
    async def test_concurrent_utility_operations(self):
        """Test concurrent operations using utilities."""
        @with_timeout(0.5)
        @with_retry(max_attempts=2, delay=0.05)
        async def concurrent_operation(op_id):
            await asyncio.sleep(0.1)
            return f"concurrent_{op_id}"
        
        # Run multiple operations concurrently
        tasks = [concurrent_operation(i) for i in range(3)]
        results = await asyncio.gather(*tasks)
        
        expected = [f"concurrent_{i}" for i in range(3)]
        assert results == expected