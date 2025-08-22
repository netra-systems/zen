"""
Tests for AsyncRateLimiter - rate limiting functionality
Split from test_async_utils.py for architectural compliance (≤300 lines, ≤8 lines per function)
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import time
from unittest.mock import patch

import pytest

# Add project root to path
from netra_backend.app.core.async_rate_limiter import AsyncRateLimiter
from netra_backend.tests.async_utils_helpers import (
    # Add project root to path
    assert_rate_limiter_state,
    assert_timing_constraint,
)


class TestAsyncRateLimiter:
    """Test AsyncRateLimiter for rate limiting functionality"""
    
    @pytest.fixture
    def rate_limiter(self):
        return AsyncRateLimiter(max_calls=3, time_window=1.0)
    
    def test_initialization(self, rate_limiter):
        """Test rate limiter initialization"""
        assert_rate_limiter_state(rate_limiter, 3, 1.0, 0)
    async def test_acquire_under_limit(self, rate_limiter):
        """Test acquiring under rate limit"""
        start_time = time.time()
        await rate_limiter.acquire()
        await rate_limiter.acquire()
        await rate_limiter.acquire()
        end_time = time.time()
        assert end_time - start_time < 0.1
        assert_rate_limiter_state(rate_limiter, 3, 1.0, 3)
    async def test_acquire_over_limit(self, rate_limiter):
        """Test acquiring over rate limit causes delay"""
        await self._fill_rate_limiter(rate_limiter)
        start_time = time.time()
        await rate_limiter.acquire()
        end_time = time.time()
        assert_timing_constraint(start_time, end_time, 1.0)
    
    async def _fill_rate_limiter(self, rate_limiter):
        """Helper to fill rate limiter to capacity"""
        await rate_limiter.acquire()
        await rate_limiter.acquire()
        await rate_limiter.acquire()
    async def test_time_window_cleanup(self, rate_limiter):
        """Test that old calls are cleaned up"""
        with patch('time.time', side_effect=[0, 0, 0, 2.0]):
            await rate_limiter.acquire()
            await rate_limiter.acquire()
            await rate_limiter.acquire()
            await rate_limiter.acquire()
        assert_rate_limiter_state(rate_limiter, 3, 1.0, 1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])