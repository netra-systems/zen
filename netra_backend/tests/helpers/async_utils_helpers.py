"""
Helper functions and fixtures for async_utils tests
Supports 25-line function limit and reduces code duplication
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock

import pytest

from netra_backend.app.core.async_batch_processor import AsyncBatchProcessor
from netra_backend.app.core.async_connection_pool import AsyncConnectionPool
from netra_backend.app.core.async_rate_limiter import AsyncRateLimiter
from netra_backend.app.core.async_resource_manager import (
    AsyncResourceManager,
    AsyncTaskPool,
)
from netra_backend.app.core.async_retry_logic import AsyncCircuitBreaker, AsyncLock

# Setup helpers (≤8 lines each)
def create_mock_resources():
    """Create mock resources for testing"""
    callback1 = AsyncMock()
    callback2 = AsyncMock()
    resource1 = Mock()
    resource2 = Mock()
    return callback1, callback2, resource1, resource2

def register_test_resources(manager, callback1, callback2, resource1, resource2):
    """Register test resources with manager"""
    manager.register_resource(resource1, callback1)
    manager.register_resource(resource2, callback2)

def create_failing_callback():
    """Create callback that raises exception"""
    return AsyncMock(side_effect=Exception("Cleanup failed"))

def setup_task_pool_mocks():
    """Setup mocks for task pool tests"""
    return Mock(), Mock()

# Assertion helpers (≤8 lines each)
def assert_resource_manager_state(manager, is_shutting_down=True, callback_count=0):
    """Assert resource manager state"""
    assert manager._shutting_down == is_shutting_down
    assert len(manager._cleanup_callbacks) == callback_count

def assert_task_pool_state(pool, max_concurrent, is_shutting_down=False, active_count=0):
    """Assert task pool state"""
    assert pool._max_concurrent == max_concurrent
    assert pool._shutting_down == is_shutting_down
    assert len(pool._active_tasks) == active_count

def assert_rate_limiter_state(limiter, max_calls, time_window, call_count):
    """Assert rate limiter state"""
    assert limiter._max_calls == max_calls
    assert limiter._time_window == time_window
    assert len(limiter._calls) == call_count

def assert_callbacks_called(callback1, callback2):
    """Assert callbacks were called once"""
    callback1.assert_called_once()
    callback2.assert_called_once()

# Test operation factories (≤8 lines each)
async def create_quick_operation():
    """Create quick async operation"""
    await asyncio.sleep(0.01)
    return "success"

async def create_slow_operation():
    """Create slow async operation
    
    CRITICAL: Uses 0.2s delay for unit test compatibility.
    Longer than quick operations but still fast enough for unit tests.
    """
    await asyncio.sleep(0.2)  # Reduced from 1.0s to 0.2s for unit test speed
    return "should not reach here"

async def create_failing_operation():
    """Create operation that always fails"""
    raise ValueError("Operation failed")

def create_dummy_processor():
    """Create dummy batch processor function"""
    async def processor(items):
        return f"processed_{len(items)}"
    return processor

# Progress callback helpers (≤8 lines each)
def create_progress_tracker():
    """Create progress tracking callback"""
    progress_calls = []
    def callback(completed, total):
        progress_calls.append((completed, total))
    return progress_calls, callback

def assert_progress_tracking(progress_calls, expected_calls):
    """Assert progress was tracked correctly"""
    assert len(progress_calls) == len(expected_calls)
    for expected in expected_calls:
        assert expected in progress_calls

# Circuit breaker helpers (≤8 lines each)
def create_circuit_breaker_operation(should_fail=True):
    """Create circuit breaker test operation"""
    async def operation():
        if should_fail:
            raise ValueError("Failing")
        return "success"
    return operation

def assert_circuit_breaker_state(breaker, state, failure_count):
    """Assert circuit breaker state"""
    assert breaker.state == state
    assert breaker.failure_count == failure_count

# Connection pool helpers (≤8 lines each)
def create_connection_counter():
    """Create connection counter for pool tests"""
    counter = {'value': 0}
    async def create_connection():
        counter['value'] += 1
        return Mock(id=counter['value'])
    return counter, create_connection

async def create_close_connection():
    """Create connection close function"""
    async def close_connection(conn):
        conn.closed = True
    return close_connection

def create_slow_connection_factory():
    """Create slow connection factory for timeout tests
    
    CRITICAL: Uses 0.1s delay to simulate slow connections without blocking unit tests.
    Unit tests must complete quickly (CLAUDE.MD compliance).
    For actual timeout testing, use test-specific timeouts, not long sleeps.
    """
    async def create_connection():
        await asyncio.sleep(0.1)  # Reduced from 10s to 0.1s for unit test stability
        return "connection"
    return create_connection

# Timing helpers (≤8 lines each)
def assert_timing_constraint(start_time, end_time, min_duration):
    """Assert operation took at least minimum duration"""
    duration = end_time - start_time
    assert duration >= min_duration

def measure_timing(operation_func):
    """Decorator to measure operation timing"""
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await operation_func(*args, **kwargs)
        end = time.time()
        return result, end - start
    return wrapper

# Batch processing helpers (≤8 lines each)
def create_sum_processor():
    """Create sum processor for batch tests"""
    async def processor(batch):
        await asyncio.sleep(0.01)
        return sum(batch)
    return processor

def assert_batch_results(results, expected_sums):
    """Assert batch processing results"""
    assert len(results) == len(expected_sums)
    for i, expected in enumerate(expected_sums):
        assert results[i] == expected

# Lock helpers (≤8 lines each)
def assert_lock_state(lock, is_locked, name):
    """Assert lock state"""
    assert lock.is_locked == is_locked
    info = lock.lock_info
    assert info["name"] == name
    assert info["locked"] == is_locked

# Retry helpers (≤8 lines each)
def create_retry_counter():
    """Create counter for retry tests"""
    counter = {'value': 0}
    def increment():
        counter['value'] += 1
        return counter['value']
    return counter, increment

def create_eventually_successful(counter_func, success_on_attempt=3):
    """Create function that succeeds after N attempts"""
    async def function():
        attempt = counter_func()
        if attempt < success_on_attempt:
            raise ValueError(f"Attempt {attempt} failed")
        return "success_after_retries"
    return function