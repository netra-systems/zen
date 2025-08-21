"""Comprehensive unit tests for ToolPermissionRateLimiter - FREE TIER CRITICAL.

BUSINESS VALUE JUSTIFICATION:
1. Segment: Free tier users (100% of new users start here)
2. Business Goal: Enforce rate limits to encourage upgrades to paid tiers
3. Value Impact: Proper rate limiting drives 20-30% conversion to paid
4. Revenue Impact: Each converted user = $29-299/month revenue
5. CRITICAL: Rate limit bugs = lost conversion opportunities and runaway costs

Tests the ToolPermissionRateLimiter that enforces free tier rate limits,
usage tracking, and upgrade prompts. Critical for conversion funnel and cost control.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, UTC
import redis

from netra_backend.app.services.tool_permissions.rate_limiter import ToolPermissionRateLimiter
from netra_backend.app.schemas.ToolPermission import ToolExecutionContext


# Test fixtures for setup
@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock(spec=redis.Redis)
    return redis_mock


@pytest.fixture
def rate_limiter(mock_redis):
    """Rate limiter with mock Redis."""
    return ToolPermissionRateLimiter(redis_client=mock_redis)


@pytest.fixture
def rate_limiter_no_redis():
    """Rate limiter without Redis client."""
    return ToolPermissionRateLimiter(redis_client=None)


@pytest.fixture
def free_tier_context():
    """Free tier execution context."""
    context = Mock(spec=ToolExecutionContext)
    context.user_id = "free_user_123"
    context.tool_name = "data_analyzer"
    context.plan_tier = "free"
    return context


@pytest.fixture
def pro_tier_context():
    """Pro tier execution context."""
    context = Mock(spec=ToolExecutionContext)
    context.user_id = "pro_user_456"
    context.tool_name = "advanced_analyzer"
    context.plan_tier = "pro"
    return context


@pytest.fixture
def free_tier_permission_definitions():
    """Free tier permission definitions with strict limits."""
    rate_limits = Mock()
    rate_limits.per_minute = 5
    rate_limits.per_hour = 50
    rate_limits.per_day = 100
    
    permission_def = Mock()
    permission_def.rate_limits = rate_limits
    
    return {
        "free_tool_access": permission_def
    }


@pytest.fixture
def pro_tier_permission_definitions():
    """Pro tier permission definitions with higher limits."""
    rate_limits = Mock()
    rate_limits.per_minute = 50
    rate_limits.per_hour = 500
    rate_limits.per_day = 2000
    
    permission_def = Mock()
    permission_def.rate_limits = rate_limits
    
    return {
        "pro_tool_access": permission_def
    }


@pytest.fixture
def unlimited_permission_definitions():
    """Unlimited permission definitions."""
    rate_limits = Mock()
    rate_limits.per_minute = None
    rate_limits.per_hour = None
    rate_limits.per_day = None
    
    permission_def = Mock()
    permission_def.rate_limits = rate_limits
    
    return {
        "unlimited_access": permission_def
    }


# Helper functions for 25-line compliance
def create_mock_permission_def(per_minute=None, per_hour=None, per_day=None):
    """Create mock permission definition with rate limits."""
    rate_limits = Mock()
    rate_limits.per_minute = per_minute
    rate_limits.per_hour = per_hour
    rate_limits.per_day = per_day
    permission_def = Mock()
    permission_def.rate_limits = rate_limits
    return permission_def


def assert_rate_limit_allowed(result):
    """Assert rate limit check result is allowed."""
    assert result["allowed"] is True
    assert "limits" in result


def assert_rate_limit_exceeded(result, expected_limit):
    """Assert rate limit check result shows exceeded limit."""
    assert result["allowed"] is False
    assert result["limit"] == expected_limit
    assert "message" in result


def assert_usage_key_format(key, user_id, tool_name, pattern):
    """Assert usage key has correct format."""
    assert user_id in key
    assert tool_name in key
    assert pattern in key


def setup_redis_usage_count(mock_redis, count):
    """Setup Redis to return specific usage count."""
    mock_redis.get.return_value = str(count) if count else None


def setup_redis_error(mock_redis, error_message):
    """Setup Redis to raise error."""
    mock_redis.get.side_effect = Exception(error_message)


# Core rate limiting functionality tests
class TestRateLimitChecking:
    """Test core rate limit checking functionality."""

    @pytest.mark.asyncio
    async def test_no_rate_limits_always_allowed(self, rate_limiter, free_tier_context):
        """No rate limits always allows requests."""
        result = await rate_limiter.check_rate_limits(
            free_tier_context, ["no_limits"], {}
        )
        assert_rate_limit_allowed(result)

    @pytest.mark.asyncio
    async def test_under_minute_limit_allowed(self, rate_limiter, free_tier_context, 
                                              free_tier_permission_definitions):
        """Under minute limit allows request."""
        setup_redis_usage_count(rate_limiter.redis, 3)  # Under limit of 5
        result = await rate_limiter.check_rate_limits(
            free_tier_context, ["free_tool_access"], free_tier_permission_definitions
        )
        assert_rate_limit_allowed(result)

    @pytest.mark.asyncio
    async def test_exceed_minute_limit_blocked(self, rate_limiter, free_tier_context,
                                               free_tier_permission_definitions):
        """Exceeding minute limit blocks request."""
        setup_redis_usage_count(rate_limiter.redis, 5)  # At limit of 5
        result = await rate_limiter.check_rate_limits(
            free_tier_context, ["free_tool_access"], free_tier_permission_definitions
        )
        assert_rate_limit_exceeded(result, 5)

    @pytest.mark.asyncio
    async def test_exceed_hour_limit_blocked(self, rate_limiter, free_tier_context,
                                             free_tier_permission_definitions):
        """Exceeding hour limit blocks request."""
        # Mock to return different values for different periods
        async def mock_get_usage(user_id, tool_name, period):
            if period == "minute":
                return 3  # Under minute limit
            elif period == "hour":
                return 50  # At hour limit
            elif period == "day":
                return 30  # Under day limit
            return 0
        
        rate_limiter._get_usage_count = mock_get_usage
        result = await rate_limiter.check_rate_limits(
            free_tier_context, ["free_tool_access"], free_tier_permission_definitions
        )
        assert_rate_limit_exceeded(result, 50)

    @pytest.mark.asyncio
    async def test_exceed_day_limit_blocked(self, rate_limiter, free_tier_context,
                                            free_tier_permission_definitions):
        """Exceeding day limit blocks request."""
        # Mock to return different values for different periods
        async def mock_get_usage(user_id, tool_name, period):
            if period == "minute":
                return 3  # Under minute limit
            elif period == "hour":
                return 30  # Under hour limit
            elif period == "day":
                return 100  # At day limit
            return 0
        
        rate_limiter._get_usage_count = mock_get_usage
        result = await rate_limiter.check_rate_limits(
            free_tier_context, ["free_tool_access"], free_tier_permission_definitions
        )
        assert_rate_limit_exceeded(result, 100)

    @pytest.mark.asyncio
    async def test_unlimited_permission_always_allowed(self, rate_limiter, free_tier_context,
                                                        unlimited_permission_definitions):
        """Unlimited permissions always allow requests."""
        setup_redis_usage_count(rate_limiter.redis, 9999)  # Very high usage
        result = await rate_limiter.check_rate_limits(
            free_tier_context, ["unlimited_access"], unlimited_permission_definitions
        )
        assert_rate_limit_allowed(result)

    @pytest.mark.asyncio
    async def test_multiple_permissions_uses_most_restrictive(self, rate_limiter, 
                                                              free_tier_context):
        """Multiple permissions use most restrictive limits."""
        strict_def = create_mock_permission_def(per_minute=1, per_hour=10, per_day=50)
        loose_def = create_mock_permission_def(per_minute=100, per_hour=1000, per_day=5000)
        
        permission_defs = {
            "strict_access": strict_def,
            "loose_access": loose_def
        }
        
        setup_redis_usage_count(rate_limiter.redis, 2)  # Over strict limit
        result = await rate_limiter.check_rate_limits(
            free_tier_context, ["strict_access", "loose_access"], permission_defs
        )
        # Should be blocked by strict limit
        assert_rate_limit_exceeded(result, 1)


class TestUsageKeyGeneration:
    """Test usage key generation for different time periods."""

    def test_minute_key_format(self, rate_limiter):
        """Minute usage key has correct format."""
        now = datetime(2025, 1, 15, 14, 30, 45, tzinfo=UTC)
        key = rate_limiter._build_usage_key("user123", "tool_name", "minute", now)
        assert_usage_key_format(key, "user123", "tool_name", "202501151430")

    def test_hour_key_format(self, rate_limiter):
        """Hour usage key has correct format."""
        now = datetime(2025, 1, 15, 14, 30, 45, tzinfo=UTC)
        key = rate_limiter._build_usage_key("user123", "tool_name", "hour", now)
        assert_usage_key_format(key, "user123", "tool_name", "2025011514")

    def test_day_key_format(self, rate_limiter):
        """Day usage key has correct format."""
        now = datetime(2025, 1, 15, 14, 30, 45, tzinfo=UTC)
        key = rate_limiter._build_usage_key("user123", "tool_name", "day", now)
        assert_usage_key_format(key, "user123", "tool_name", "20250115")

    def test_invalid_period_returns_none(self, rate_limiter):
        """Invalid period returns None."""
        now = datetime.now(UTC)
        key = rate_limiter._build_usage_key("user123", "tool_name", "invalid", now)
        assert key is None

    def test_key_contains_usage_prefix(self, rate_limiter):
        """Usage keys contain proper prefix."""
        now = datetime.now(UTC)
        key = rate_limiter._build_usage_key("user123", "tool_name", "day", now)
        assert key.startswith("usage:")


class TestUsageTracking:
    """Test usage tracking and recording."""

    @pytest.mark.asyncio
    async def test_get_usage_count_with_redis(self, rate_limiter):
        """Get usage count works with Redis."""
        setup_redis_usage_count(rate_limiter.redis, 42)
        count = await rate_limiter._get_usage_count("user123", "tool", "day")
        assert count == 42

    @pytest.mark.asyncio
    async def test_get_usage_count_no_data(self, rate_limiter):
        """Get usage count returns 0 when no data."""
        setup_redis_usage_count(rate_limiter.redis, None)
        count = await rate_limiter._get_usage_count("user123", "tool", "day")
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_usage_count_without_redis(self, rate_limiter_no_redis):
        """Get usage count returns 0 without Redis."""
        count = await rate_limiter_no_redis._get_usage_count("user123", "tool", "day")
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_usage_count_redis_error(self, rate_limiter):
        """Get usage count handles Redis errors gracefully."""
        setup_redis_error(rate_limiter.redis, "Connection failed")
        count = await rate_limiter._get_usage_count("user123", "tool", "day")
        assert count == 0

    @pytest.mark.asyncio
    async def test_record_tool_usage_increments_counters(self, rate_limiter):
        """Record tool usage increments all period counters."""
        await rate_limiter.record_tool_usage("user123", "tool", 500, "success")
        
        # Should call incr for minute, hour, and day keys
        assert rate_limiter.redis.incr.call_count == 3
        assert rate_limiter.redis.expire.call_count == 3

    @pytest.mark.asyncio
    async def test_record_tool_usage_sets_expiry(self, rate_limiter):
        """Record tool usage sets appropriate expiry times."""
        await rate_limiter.record_tool_usage("user123", "tool", 500, "success")
        
        # Check that expire was called with correct TTL values
        expire_calls = rate_limiter.redis.expire.call_args_list
        ttl_values = [call[0][1] for call in expire_calls]
        assert 60 in ttl_values      # minute TTL
        assert 3600 in ttl_values    # hour TTL
        assert 86400 in ttl_values   # day TTL

    @pytest.mark.asyncio
    async def test_record_tool_usage_without_redis(self, rate_limiter_no_redis):
        """Record tool usage handles missing Redis gracefully."""
        # Should not raise exception
        await rate_limiter_no_redis.record_tool_usage("user123", "tool", 500, "success")

    @pytest.mark.asyncio
    async def test_record_tool_usage_redis_error(self, rate_limiter):
        """Record tool usage handles Redis errors gracefully."""
        rate_limiter.redis.incr.side_effect = Exception("Redis error")
        # Should not raise exception
        await rate_limiter.record_tool_usage("user123", "tool", 500, "success")


class TestPermissionDefinitionProcessing:
    """Test permission definition processing and rate limit extraction."""

    def test_get_applicable_rate_limits_single_permission(self, rate_limiter):
        """Get applicable rate limits for single permission."""
        permission_def = create_mock_permission_def(
            per_minute=10, per_hour=100, per_day=1000
        )
        permission_defs = {"test_perm": permission_def}
        
        limits = rate_limiter._get_applicable_rate_limits(["test_perm"], permission_defs)
        assert limits["per_minute"] == 10
        assert limits["per_hour"] == 100
        assert limits["per_day"] == 1000

    def test_get_applicable_rate_limits_multiple_permissions(self, rate_limiter):
        """Get applicable rate limits merges multiple permissions."""
        perm1 = create_mock_permission_def(per_minute=5, per_hour=50, per_day=500)
        perm2 = create_mock_permission_def(per_minute=10, per_hour=100, per_day=1000)
        
        permission_defs = {"perm1": perm1, "perm2": perm2}
        
        limits = rate_limiter._get_applicable_rate_limits(
            ["perm1", "perm2"], permission_defs
        )
        # Should use the last permission's limits (update behavior)
        assert limits["per_minute"] == 10
        assert limits["per_hour"] == 100
        assert limits["per_day"] == 1000

    def test_get_applicable_rate_limits_no_rate_limits(self, rate_limiter):
        """Get applicable rate limits handles permissions without rate limits."""
        permission_def = Mock()
        permission_def.rate_limits = None
        permission_defs = {"no_limits": permission_def}
        
        limits = rate_limiter._get_applicable_rate_limits(["no_limits"], permission_defs)
        assert limits == {}

    def test_get_applicable_rate_limits_missing_permission(self, rate_limiter):
        """Get applicable rate limits handles missing permissions."""
        limits = rate_limiter._get_applicable_rate_limits(
            ["nonexistent"], {}
        )
        assert limits == {}


class TestResponseBuilding:
    """Test response building for allowed and exceeded scenarios."""

    def test_build_limit_exceeded_response_structure(self, rate_limiter):
        """Build limit exceeded response has correct structure."""
        rate_limits = {"per_minute": 5, "per_hour": 50}
        response = rate_limiter._build_limit_exceeded_response(
            "per_minute", 5, 6, rate_limits
        )
        
        assert response["allowed"] is False
        assert "Exceeded per_minute limit of 5" in response["message"]
        assert response["current_usage"] == 6
        assert response["limit"] == 5
        assert response["limits"] == rate_limits

    @pytest.mark.asyncio
    async def test_build_allowed_response_structure(self, rate_limiter, free_tier_context):
        """Build allowed response has correct structure."""
        setup_redis_usage_count(rate_limiter.redis, 10)
        rate_limits = {"per_minute": 5, "per_hour": 50}
        
        response = await rate_limiter._build_allowed_response(rate_limits, free_tier_context)
        
        assert response["allowed"] is True
        assert response["limits"] == rate_limits
        assert response["current_usage"] == 10

    @pytest.mark.asyncio
    async def test_build_allowed_response_gets_day_usage(self, rate_limiter, free_tier_context):
        """Build allowed response gets daily usage count."""
        setup_redis_usage_count(rate_limiter.redis, 25)
        rate_limits = {}
        
        response = await rate_limiter._build_allowed_response(rate_limits, free_tier_context)
        
        # Should call _get_usage_count with "day" period
        rate_limiter._get_usage_count.assert_called_with(
            free_tier_context.user_id, free_tier_context.tool_name, "day"
        )


class TestPeriodKeyAndTTL:
    """Test period key and TTL generation."""

    def test_get_period_key_and_ttl_minute(self, rate_limiter):
        """Get period key and TTL for minute period."""
        now = datetime(2025, 1, 15, 14, 30, 45, tzinfo=UTC)
        key, ttl = rate_limiter._get_period_key_and_ttl("user123", "tool", "minute", now)
        
        assert "usage:user123:tool:202501151430" == key
        assert ttl == 60

    def test_get_period_key_and_ttl_hour(self, rate_limiter):
        """Get period key and TTL for hour period."""
        now = datetime(2025, 1, 15, 14, 30, 45, tzinfo=UTC)
        key, ttl = rate_limiter._get_period_key_and_ttl("user123", "tool", "hour", now)
        
        assert "usage:user123:tool:2025011514" == key
        assert ttl == 3600

    def test_get_period_key_and_ttl_day(self, rate_limiter):
        """Get period key and TTL for day period."""
        now = datetime(2025, 1, 15, 14, 30, 45, tzinfo=UTC)
        key, ttl = rate_limiter._get_period_key_and_ttl("user123", "tool", "day", now)
        
        assert "usage:user123:tool:20250115" == key
        assert ttl == 86400

    def test_get_period_key_and_ttl_invalid(self, rate_limiter):
        """Get period key and TTL for invalid period returns None."""
        now = datetime.now(UTC)
        key, ttl = rate_limiter._get_period_key_and_ttl("user123", "tool", "invalid", now)
        
        assert key is None
        assert ttl is None


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""

    @pytest.mark.asyncio
    async def test_none_rate_limits_in_definition(self, rate_limiter, free_tier_context):
        """None rate limits in definition are handled correctly."""
        permission_def = create_mock_permission_def(
            per_minute=None, per_hour=10, per_day=100
        )
        permission_defs = {"mixed_limits": permission_def}
        
        setup_redis_usage_count(rate_limiter.redis, 5)
        result = await rate_limiter.check_rate_limits(
            free_tier_context, ["mixed_limits"], permission_defs
        )
        # Should be allowed since minute limit is None
        assert_rate_limit_allowed(result)

    @pytest.mark.asyncio
    async def test_invalid_usage_key_returns_zero(self, rate_limiter):
        """Invalid usage key returns zero count."""
        with patch.object(rate_limiter, '_build_usage_key', return_value=None):
            count = await rate_limiter._get_usage_count("user", "tool", "invalid")
            assert count == 0

    @pytest.mark.asyncio
    async def test_redis_connection_failure_graceful(self, rate_limiter, free_tier_context,
                                                     free_tier_permission_definitions):
        """Redis connection failure is handled gracefully."""
        setup_redis_error(rate_limiter.redis, "Connection timeout")
        
        result = await rate_limiter.check_rate_limits(
            free_tier_context, ["free_tool_access"], free_tier_permission_definitions
        )
        # Should allow when Redis fails (fail-open for availability)
        assert_rate_limit_allowed(result)

    @pytest.mark.asyncio
    async def test_empty_permissions_list(self, rate_limiter, free_tier_context):
        """Empty permissions list returns allowed."""
        result = await rate_limiter.check_rate_limits(
            free_tier_context, [], {}
        )
        assert_rate_limit_allowed(result)

    @pytest.mark.asyncio
    async def test_malformed_redis_data(self, rate_limiter):
        """Malformed Redis data is handled gracefully."""
        rate_limiter.redis.get.return_value = "not_a_number"
        
        # Should handle ValueError when converting to int
        count = await rate_limiter._get_usage_count("user", "tool", "day")
        assert count == 0  # Should default to 0 on conversion error

    @pytest.mark.asyncio
    async def test_very_high_usage_count(self, rate_limiter, free_tier_context,
                                         free_tier_permission_definitions):
        """Very high usage count is handled correctly."""
        setup_redis_usage_count(rate_limiter.redis, 999999)
        
        result = await rate_limiter.check_rate_limits(
            free_tier_context, ["free_tool_access"], free_tier_permission_definitions
        )
        assert_rate_limit_exceeded(result, 5)  # Should be blocked
        assert result["current_usage"] == 999999


class TestIntegrationScenarios:
    """Test realistic integration scenarios for business cases."""

    @pytest.mark.asyncio
    async def test_free_tier_user_conversion_scenario(self, rate_limiter, free_tier_context):
        """Free tier user hitting limits should get upgrade prompt."""
        # Free tier: 5 per minute, 50 per hour, 100 per day
        strict_free_def = create_mock_permission_def(
            per_minute=5, per_hour=50, per_day=100
        )
        permission_defs = {"free_tier": strict_free_def}
        
        # User hits daily limit
        setup_redis_usage_count(rate_limiter.redis, 100)
        
        result = await rate_limiter.check_rate_limits(
            free_tier_context, ["free_tier"], permission_defs
        )
        
        assert_rate_limit_exceeded(result, 100)
        assert "day" in result["message"]  # Should indicate which limit hit

    @pytest.mark.asyncio
    async def test_pro_tier_user_higher_limits(self, rate_limiter, pro_tier_context,
                                               pro_tier_permission_definitions):
        """Pro tier user has much higher limits."""
        # Usage that would block free tier but not pro tier
        setup_redis_usage_count(rate_limiter.redis, 150)  # Would block free tier
        
        result = await rate_limiter.check_rate_limits(
            pro_tier_context, ["pro_tool_access"], pro_tier_permission_definitions
        )
        
        assert_rate_limit_allowed(result)  # Pro tier should be allowed

    @pytest.mark.asyncio
    async def test_burst_usage_blocked_appropriately(self, rate_limiter, free_tier_context,
                                                     free_tier_permission_definitions):
        """Burst usage is blocked to prevent abuse."""
        # User tries to burst beyond minute limit
        setup_redis_usage_count(rate_limiter.redis, 5)  # At minute limit
        
        result = await rate_limiter.check_rate_limits(
            free_tier_context, ["free_tool_access"], free_tier_permission_definitions
        )
        
        assert_rate_limit_exceeded(result, 5)
        assert "minute" in result["message"]  # Should be minute limit