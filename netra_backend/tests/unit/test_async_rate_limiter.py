"""Comprehensive tests for AsyncRateLimiter core functionality.

BUSINESS VALUE: Prevents runaway AI costs by controlling operation frequency,
directly protecting customer AI spend and ensuring fair resource usage.

Tests critical paths including rate limiting, time windows, concurrent access,
and edge cases that could lead to cost overruns.
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import time

import pytest

from netra_backend.app.core.async_rate_limiter import AsyncRateLimiter

# Test fixtures for setup
@pytest.fixture
def rate_limiter():
    """Use real service instance."""
    # TODO: Initialize real service
    """Standard rate limiter with reasonable limits."""
    return AsyncRateLimiter(max_calls=3, time_window=1.0)

@pytest.fixture
def strict_limiter():
    """Use real service instance."""
    # TODO: Initialize real service
    """Strict rate limiter for testing edge cases."""
    return AsyncRateLimiter(max_calls=1, time_window=0.5)

@pytest.fixture
def fast_limiter():
    """Use real service instance."""
    # TODO: Initialize real service
    """Fast rate limiter for timing tests."""
    return AsyncRateLimiter(max_calls=10, time_window=0.1)

# Helper functions for 25-line compliance
async def acquire_calls(limiter, count):
    """Acquire multiple calls from limiter."""
    for _ in range(count):
        await limiter.acquire()

def assert_current_calls(limiter, expected):
    """Assert current call count matches expected."""
    assert limiter.current_calls == expected

def assert_remaining_calls(limiter, expected):
    """Assert remaining calls matches expected."""
    assert limiter.remaining_calls == expected

def assert_max_calls(limiter, expected):
    """Assert max calls matches expected."""
    assert limiter.max_calls == expected

def assert_time_window(limiter, expected):
    """Assert time window matches expected."""
    assert limiter.time_window == expected

async def wait_for_window_reset(limiter):
    """Wait for time window to reset."""
    await asyncio.sleep(limiter.time_window + 0.01)

def create_expired_calls(limiter, count):
    """Create expired calls in the limiter."""
    old_time = time.time() - limiter.time_window - 1
    limiter._calls = [old_time] * count

# Core rate limiter functionality tests
class TestRateLimiterInitialization:
    """Test rate limiter initialization and properties."""

    def test_rate_limiter_stores_max_calls(self, rate_limiter):
        """Rate limiter stores max calls correctly."""
        assert_max_calls(rate_limiter, 3)

    def test_rate_limiter_stores_time_window(self, rate_limiter):
        """Rate limiter stores time window correctly."""
        assert_time_window(rate_limiter, 1.0)

    def test_rate_limiter_starts_empty(self, rate_limiter):
        """Rate limiter starts with no calls."""
        assert_current_calls(rate_limiter, 0)
        assert_remaining_calls(rate_limiter, 3)

    def test_rate_limiter_has_lock(self, rate_limiter):
        """Rate limiter has async lock for thread safety."""
        assert hasattr(rate_limiter, '_lock')
        assert rate_limiter._lock is not None

    def test_strict_limiter_configuration(self, strict_limiter):
        """Strict limiter has correct configuration."""
        assert_max_calls(strict_limiter, 1)
        assert_time_window(strict_limiter, 0.5)

class TestCallAcquisition:
    """Test call acquisition and tracking."""

    @pytest.mark.asyncio
    async def test_acquire_single_call(self, rate_limiter):
        """Single call acquisition works."""
        await rate_limiter.acquire()
        assert_current_calls(rate_limiter, 1)
        assert_remaining_calls(rate_limiter, 2)

    @pytest.mark.asyncio
    async def test_acquire_multiple_calls(self, rate_limiter):
        """Multiple call acquisitions work."""
        await acquire_calls(rate_limiter, 3)
        assert_current_calls(rate_limiter, 3)
        assert_remaining_calls(rate_limiter, 0)

    @pytest.mark.asyncio
    async def test_acquire_beyond_limit_waits(self, strict_limiter):
        """Acquiring beyond limit causes wait."""
        await strict_limiter.acquire()  # Use up the limit
        
        start_time = time.time()
        await strict_limiter.acquire()  # This should wait
        elapsed = time.time() - start_time
        
        assert elapsed >= strict_limiter.time_window * 0.8  # Account for timing variance

    @pytest.mark.asyncio
    async def test_can_make_call_check(self, rate_limiter):
        """can_make_call correctly reports availability."""
        assert await rate_limiter.can_make_call() is True
        await acquire_calls(rate_limiter, 3)
        assert await rate_limiter.can_make_call() is False

    @pytest.mark.asyncio
    async def test_acquire_updates_call_list(self, rate_limiter):
        """Acquire updates internal call list."""
        initial_length = len(rate_limiter._calls)
        await rate_limiter.acquire()
        assert len(rate_limiter._calls) == initial_length + 1

class TestTimeWindowBehavior:
    """Test time window and call expiration."""

    @pytest.mark.asyncio
    async def test_old_calls_expire(self, fast_limiter):
        """Old calls outside time window expire."""
        create_expired_calls(fast_limiter, 5)
        await fast_limiter.acquire()  # This should clean up old calls
        assert_current_calls(fast_limiter, 1)

    @pytest.mark.asyncio
    async def test_calls_reset_after_window(self, fast_limiter):
        """Calls reset after time window passes."""
        await acquire_calls(fast_limiter, 10)  # Fill to limit
        await wait_for_window_reset(fast_limiter)
        assert_current_calls(fast_limiter, 0)
        assert_remaining_calls(fast_limiter, 10)

    @pytest.mark.asyncio
    async def test_partial_window_expiration(self, rate_limiter):
        """Calls partially expire as time passes."""
        # Add calls at different times
        await rate_limiter.acquire()
        await asyncio.sleep(0.3)
        await rate_limiter.acquire()
        
        # Wait for first call to expire
        await asyncio.sleep(0.8)
        assert_current_calls(rate_limiter, 1)

    def test_cleanup_old_calls_method(self, rate_limiter):
        """_cleanup_old_calls removes expired entries."""
        create_expired_calls(rate_limiter, 3)
        now = time.time()
        rate_limiter._cleanup_old_calls(now)
        assert len(rate_limiter._calls) == 0

    def test_wait_time_calculation(self, rate_limiter):
        """Wait time calculation works correctly."""
        old_time = time.time() - 0.5  # Half window ago
        wait_time = rate_limiter._calculate_wait_time(old_time)
        assert 0.4 <= wait_time <= 0.6  # Account for timing variance

class TestConcurrentAccess:
    """Test thread safety and concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_acquisitions(self, rate_limiter):
        """Concurrent acquisitions work correctly."""
        tasks = [rate_limiter.acquire() for _ in range(3)]
        await asyncio.gather(*tasks)
        assert_current_calls(rate_limiter, 3)

    @pytest.mark.asyncio
    async def test_lock_prevents_race_conditions(self, rate_limiter):
        """Lock prevents race conditions in call counting."""
        # This test ensures internal consistency under concurrent load
        async def rapid_acquire():
            await rate_limiter.acquire()
        
        tasks = [rapid_acquire() for _ in range(3)]
        await asyncio.gather(*tasks)
        # Should have exactly 3 calls, no more, no less
        assert_current_calls(rate_limiter, 3)

    @pytest.mark.asyncio
    async def test_can_make_call_under_concurrency(self, strict_limiter):
        """can_make_call works correctly under concurrent access."""
        # Fill limiter
        await strict_limiter.acquire()
        
        # Multiple concurrent checks should all return False
        checks = [strict_limiter.can_make_call() for _ in range(5)]
        results = await asyncio.gather(*checks)
        assert all(result is False for result in results)

class TestResetFunctionality:
    """Test reset and cleanup functionality."""

    @pytest.mark.asyncio
    async def test_reset_clears_calls(self, rate_limiter):
        """Reset clears all call history."""
        await acquire_calls(rate_limiter, 3)
        await rate_limiter.reset()
        assert_current_calls(rate_limiter, 0)
        assert_remaining_calls(rate_limiter, 3)

    @pytest.mark.asyncio
    async def test_reset_allows_immediate_calls(self, rate_limiter):
        """Reset allows immediate call acquisition."""
        await acquire_calls(rate_limiter, 3)  # Fill to limit
        await rate_limiter.reset()
        # Should be able to acquire immediately
        await rate_limiter.acquire()
        assert_current_calls(rate_limiter, 1)

    @pytest.mark.asyncio
    async def test_reset_thread_safety(self, rate_limiter):
        """Reset is thread-safe."""
        # Fill limiter and reset concurrently
        await acquire_calls(rate_limiter, 2)
        
        async def concurrent_reset():
            await rate_limiter.reset()
        
        await asyncio.gather(
            concurrent_reset(),
            concurrent_reset(),
            concurrent_reset()
        )
        assert_current_calls(rate_limiter, 0)

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_time_window_limiter(self):
        """Zero time window limiter works."""
        limiter = AsyncRateLimiter(max_calls=5, time_window=0.0)
        assert_time_window(limiter, 0.0)
        # Calls should expire immediately
        assert limiter.current_calls == 0

    def test_single_call_limiter(self):
        """Single call limiter works."""
        limiter = AsyncRateLimiter(max_calls=1, time_window=1.0)
        assert_max_calls(limiter, 1)
        assert_remaining_calls(limiter, 1)

    @pytest.mark.asyncio
    async def test_large_time_window(self):
        """Large time window works correctly."""
        limiter = AsyncRateLimiter(max_calls=2, time_window=10.0)
        await acquire_calls(limiter, 2)
        assert_current_calls(limiter, 2)
        assert_remaining_calls(limiter, 0)

    @pytest.mark.asyncio  
    async def test_many_expired_calls_cleanup(self, rate_limiter):
        """Many expired calls are cleaned up efficiently."""
        # Create many expired calls
        create_expired_calls(rate_limiter, 1000)
        await rate_limiter.acquire()
        # Should clean up efficiently
        assert_current_calls(rate_limiter, 1)
        assert len(rate_limiter._calls) == 1

    @pytest.mark.asyncio
    async def test_recursive_acquire_handling(self, strict_limiter):
        """Recursive acquire calls are handled correctly."""
        # Fill the limiter
        await strict_limiter.acquire()
        
        # The next acquire will trigger _wait_and_retry which calls acquire recursively
        start_time = time.time()
        await strict_limiter.acquire()
        elapsed = time.time() - start_time
        
        # Should have waited for the window
        assert elapsed >= strict_limiter.time_window * 0.8

class TestPropertiesAndState:
    """Test property getters and state management."""

    def test_current_calls_property(self, rate_limiter):
        """current_calls property calculates correctly."""
        # Manually add calls to test calculation
        now = time.time()
        rate_limiter._calls = [now - 0.5, now - 0.1, now - 2.0]  # One expired
        assert rate_limiter.current_calls == 2

    def test_remaining_calls_property(self, rate_limiter):
        """remaining_calls property calculates correctly."""
        # Fill partially
        now = time.time()
        rate_limiter._calls = [now - 0.1]
        assert_remaining_calls(rate_limiter, 2)

    def test_remaining_calls_never_negative(self, rate_limiter):
        """remaining_calls never goes below zero."""
        # Manually create more calls than limit
        now = time.time()
        rate_limiter._calls = [now - 0.1] * 10
        assert rate_limiter.remaining_calls == 0

    @pytest.mark.asyncio
    async def test_property_consistency(self, rate_limiter):
        """Properties remain consistent after operations."""
        await acquire_calls(rate_limiter, 2)
        current = rate_limiter.current_calls
        remaining = rate_limiter.remaining_calls
        max_calls = rate_limiter.max_calls
        
        assert current + remaining == max_calls