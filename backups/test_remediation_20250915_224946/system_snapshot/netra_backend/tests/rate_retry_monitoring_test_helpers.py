"""
Test helpers for rate limiting, retry, and monitoring utilities testing.
Provides setup, assertion, and fixture functions for rate limiting, retry, and monitoring utility tests.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Tuple

class RateLimiterTestHelpers:
    """Helper functions for rate limiter testing."""
    
    @staticmethod
    async def assert_burst_allowed(limiter, count: int):
        """Assert burst requests are allowed."""
        for _ in range(count):
            assert await limiter.allow_request() == True
    
    @staticmethod
    async def assert_request_blocked(limiter):
        """Assert request is blocked."""
        assert await limiter.allow_request() == False

class RetryTestHelpers:
    """Helper functions for retry utility testing."""
    
    @staticmethod
    def create_failing_function(success_on_attempt: int) -> Tuple[Callable, Callable]:
        """Create function that fails then succeeds."""
        attempt_count = 0
        
        async def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < success_on_attempt:
                raise ValueError("Temporary error")
            return "Success"
        
        return failing_function, lambda: attempt_count
    
    @staticmethod
    async def always_fails():
        """Function that always fails."""
        raise ValueError("Permanent error")

class MonitoringTestHelpers:
    """Helper functions for monitoring utility testing."""
    
    @staticmethod
    def record_test_metrics(utils):
        """Record test metrics for validation."""
        utils.increment_counter("api_requests")
        utils.increment_counter("api_requests")
        utils.set_gauge("memory_usage", 75.5)
        
        for value in [10, 20, 30, 40, 50]:
            utils.record_histogram("response_time", value)
    
    @staticmethod
    def assert_counter_value(utils, name: str, expected: int):
        """Assert counter has expected value."""
        assert utils.get_counter(name) == expected