"""
Tests for Redis Manager retry logic and failover mechanisms
Tests transient failures, retry exhaustion, exponential backoff, and failover
"""

import pytest
import time
import redis.asyncio as redis

from app.tests.helpers.redis_test_fixtures import enhanced_redis_manager_with_retry, MockRedisClient
from app.tests.helpers.redis_test_helpers import (
    setup_transient_failure_mock, setup_persistent_failure_mock, setup_timing_failure_mock,
    verify_exponential_backoff, setup_fallback_cache, create_fallback_operations
)


class TestRedisManagerRetryAndFailover:
    """Test Redis retry logic and failover mechanisms"""
    async def test_retry_on_transient_failure(self, enhanced_redis_manager_with_retry):
        """Test retry logic on transient failures"""
        mock_client = MockRedisClient()
        enhanced_redis_manager_with_retry.redis_client = mock_client
        
        failing_get, get_attempt_count = setup_transient_failure_mock(2)
        mock_client.get = failing_get
        
        result = await enhanced_redis_manager_with_retry.get_with_retry("test_key")
        
        assert result == "success_test_key"
        assert get_attempt_count() == 3
    async def test_retry_exhaustion(self, enhanced_redis_manager_with_retry):
        """Test behavior when retry attempts are exhausted"""
        mock_client = MockRedisClient()
        enhanced_redis_manager_with_retry.redis_client = mock_client
        
        always_failing_get = setup_persistent_failure_mock()
        mock_client.get = always_failing_get
        
        with pytest.raises(redis.ConnectionError):
            await enhanced_redis_manager_with_retry.get_with_retry("test_key", max_retries=2)
        
        metrics = enhanced_redis_manager_with_retry.get_metrics()
        assert metrics['failed_operations'] == 3
    async def test_exponential_backoff_timing(self, enhanced_redis_manager_with_retry):
        """Test exponential backoff timing"""
        mock_client = MockRedisClient()
        enhanced_redis_manager_with_retry.redis_client = mock_client
        
        timing_failing_get, retry_times = setup_timing_failure_mock(2)
        mock_client.get = timing_failing_get
        
        result = await enhanced_redis_manager_with_retry.get_with_retry("test_key")
        
        assert result == "success"
        assert len(retry_times) == 3
        expected_delays = [(0.05, 0.15), (0.15, 0.25)]
        assert verify_exponential_backoff(retry_times, expected_delays)
    async def test_set_operation_retry(self, enhanced_redis_manager_with_retry):
        """Test retry logic for SET operations"""
        mock_client = MockRedisClient()
        enhanced_redis_manager_with_retry.redis_client = mock_client
        
        attempt_count = 0
        async def failing_set(key, value, ex=None):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise redis.ConnectionError("First attempt fails")
            return True
        
        mock_client.set = failing_set
        result = await enhanced_redis_manager_with_retry.set_with_retry("test_key", "test_value")
        
        assert result == True
        assert attempt_count == 2
    async def test_failover_to_backup_strategy(self, enhanced_redis_manager_with_retry):
        """Test failover to backup caching strategy"""
        enhanced_redis_manager_with_retry.redis_client = None
        fallback_cache = setup_fallback_cache()
        
        fallback_get, fallback_set = create_fallback_operations(
            enhanced_redis_manager_with_retry, fallback_cache
        )
        
        await fallback_set("fallback_key", "fallback_value")
        result = await fallback_get("fallback_key")
        
        assert result == "fallback_value"
        assert "fallback_key" in fallback_cache