"""
Tool Permission Service - Rate Limiting Tests
Functions refactored to ≤8 lines each using helper functions
"""

import pytest
import asyncio
from datetime import datetime, UTC
from netra_backend.app.services.tool_permission_service import ToolPermissionService
from netra_backend.app.tests.helpers.tool_permission_helpers import (
    MockRedisClient,
    create_sample_context,
    setup_redis_usage,
    create_failing_redis_method,
    assert_redis_usage_count,
    assert_rate_limits_within_bounds,
    run_concurrent_usage_recording,
    create_context_with_special_chars,
    get_rate_limit_test_data
)


@pytest.fixture
def mock_redis():
    """Create mock Redis client"""
    return MockRedisClient()


@pytest.fixture
def service():
    """Create ToolPermissionService without Redis"""
    return ToolPermissionService()


@pytest.fixture
def service_with_redis(mock_redis):
    """Create ToolPermissionService with Redis"""
    return ToolPermissionService(mock_redis)


@pytest.fixture
def sample_context():
    """Create sample tool execution context"""
    return create_sample_context()
class TestRateLimiting:
    """Test rate limiting functionality"""
    
    async def test_check_rate_limits_no_limits(self, service, sample_context):
        """Test rate limit check when no limits are defined"""
        result = await service._check_rate_limits(sample_context, [])
        assert result["allowed"] == True
        assert result["limits"] == {}
    
    async def test_check_rate_limits_within_limit(self, service_with_redis, sample_context):
        """Test rate limit check within limits"""
        permissions = ["analytics"]
        result = await service_with_redis._check_rate_limits(sample_context, permissions)
        assert result["allowed"] == True
        assert "limits" in result
        rate_limits = get_rate_limit_test_data()["analytics"]
        assert_rate_limits_within_bounds(result, rate_limits["per_hour"], rate_limits["per_day"])
    
    async def test_check_rate_limits_exceeded(self, service_with_redis, sample_context):
        """Test rate limit check when limit is exceeded"""
        permissions = ["analytics"]
        await setup_redis_usage(service_with_redis.redis, 
                               sample_context.user_id, sample_context.tool_name, 101, "hour")
        result = await service_with_redis._check_rate_limits(sample_context, permissions)
        assert result["allowed"] == False
        assert "Exceeded per_hour limit" in result["message"]
        assert result["current_usage"] == 101
    
    async def test_check_rate_limits_multiple_periods(self, service_with_redis, sample_context):
        """Test rate limit check across multiple time periods"""
        permissions = ["data_management"]
        result = await service_with_redis._check_rate_limits(sample_context, permissions)
        assert result["allowed"] == True
        limits = result["limits"]
        rate_limits = get_rate_limit_test_data()["data_management"]
        assert_rate_limits_within_bounds(result, rate_limits["per_hour"], rate_limits["per_day"])
    
    async def test_get_usage_count_minute(self, service_with_redis):
        """Test getting usage count for minute period"""
        await setup_redis_usage(service_with_redis.redis, "user123", "tool_test", 5, "minute")
        count = await service_with_redis._get_usage_count("user123", "tool_test", "minute")
        assert_redis_usage_count(count, 5)
    
    async def test_get_usage_count_hour(self, service_with_redis):
        """Test getting usage count for hour period"""
        await setup_redis_usage(service_with_redis.redis, "user123", "tool_test", 25, "hour")
        count = await service_with_redis._get_usage_count("user123", "tool_test", "hour")
        assert_redis_usage_count(count, 25)
    
    async def test_get_usage_count_day(self, service_with_redis):
        """Test getting usage count for day period"""
        await setup_redis_usage(service_with_redis.redis, "user123", "tool_test", 150, "day")
        count = await service_with_redis._get_usage_count("user123", "tool_test", "day")
        assert_redis_usage_count(count, 150)
    
    async def test_get_usage_count_no_redis(self, service):
        """Test getting usage count when Redis is not available"""
        count = await service._get_usage_count("user123", "tool_test", "day")
        assert_redis_usage_count(count, 0)
    
    async def test_get_usage_count_invalid_period(self, service_with_redis):
        """Test getting usage count with invalid period"""
        count = await service_with_redis._get_usage_count("user123", "tool_test", "invalid")
        assert_redis_usage_count(count, 0)
    
    async def test_get_usage_count_redis_error(self, service_with_redis):
        """Test getting usage count when Redis raises error"""
        service_with_redis.redis.get = create_failing_redis_method("get")
        count = await service_with_redis._get_usage_count("user123", "tool_test", "day")
        assert_redis_usage_count(count, 0)
class TestRecordToolUsage:
    """Test tool usage recording functionality"""
    
    async def test_record_tool_usage(self, service_with_redis):
        """Test recording tool usage"""
        await service_with_redis.record_tool_usage("user123", "test_tool", 250, "success")
        now = datetime.now(UTC)
        day_key = f"usage:user123:test_tool:{now.strftime('%Y%m%d')}"
        day_count = await service_with_redis.redis.get(day_key)
        assert day_count == "1"
    
    async def test_record_tool_usage_multiple_calls(self, service_with_redis):
        """Test recording multiple tool usages"""
        for i in range(3):
            await service_with_redis.record_tool_usage("user123", "test_tool", 100 + i * 50, "success")
        now = datetime.now(UTC)
        day_key = f"usage:user123:test_tool:{now.strftime('%Y%m%d')}"
        day_count = await service_with_redis.redis.get(day_key)
        assert day_count == "3"
    
    async def test_record_tool_usage_no_redis(self, service):
        """Test recording tool usage when Redis is not available"""
        await service.record_tool_usage("user123", "test_tool", 100, "success")
    
    async def test_record_tool_usage_redis_error(self, service_with_redis):
        """Test recording tool usage when Redis raises error"""
        service_with_redis.redis.incr = create_failing_redis_method("incr")
        await service_with_redis.record_tool_usage("user123", "test_tool", 100, "success")
class TestRateLimitEdgeCases:
    """Test rate limiting edge cases"""
    
    async def test_rate_limit_key_generation_edge_cases(self, service_with_redis):
        """Test rate limit key generation with edge case inputs"""
        special_context = create_context_with_special_chars()
        count = await service_with_redis._get_usage_count(
            special_context.user_id, special_context.tool_name, "day")
        assert_redis_usage_count(count, 0)
    
    async def test_concurrent_rate_limit_updates(self, service_with_redis):
        """Test concurrent rate limit updates"""
        user_id = "concurrent_user"
        tool_name = "concurrent_tool"
        await run_concurrent_usage_recording(service_with_redis, user_id, tool_name, 10)
        count = await service_with_redis._get_usage_count(user_id, tool_name, "day")
        assert_redis_usage_count(count, 10)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])