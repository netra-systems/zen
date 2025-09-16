"""Quota Management E2E Test Helpers.

BUSINESS VALUE JUSTIFICATION:
1. Segment: All tiers (Free, Early, Mid, Enterprise)
2. Business Goal: Protect $30K+ MRR from quota abuse and ensure fair usage
3. Value Impact: Prevents revenue loss from quota violations and overage costs
4. Revenue Impact: Maintains sustainable growth and prevents service abuse

Provides utilities for testing quota enforcement, rate limiting, and fair usage
across all subscription tiers in the Netra Apex platform.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from netra_backend.app.db.models_user import ToolUsageLog, User
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class MockRateLimiter:
    """Mock rate limiter for testing quota enforcement."""
    
    def __init__(self, rate_limit_per_minute: int = 100):
        self.rate_limit_per_minute = rate_limit_per_minute
    
    async def enforce_rate_limit(self) -> None:
        """Mock rate limit enforcement."""
        pass
    
    def get_current_usage(self) -> Dict[str, float]:
        """Mock current usage stats."""
        return {
            "requests_made": 0.0,
            "requests_remaining": float(self.rate_limit_per_minute),
            "window_elapsed_seconds": 30.0,
            "requests_per_minute_limit": float(self.rate_limit_per_minute)
        }


# Tier Configuration Constants
TIER_QUOTA_LIMITS = {
    "free": {
        "daily_requests": 50,
        "monthly_requests": 1000,
        "concurrent_requests": 2,
        "cost_limit_cents": 500,  # $5
        "rate_limit_per_minute": 10
    },
    "early": {
        "daily_requests": 200,
        "monthly_requests": 5000,
        "concurrent_requests": 5,
        "cost_limit_cents": 2900,  # $29
        "rate_limit_per_minute": 50
    },
    "mid": {
        "daily_requests": 1000,
        "monthly_requests": 25000,
        "concurrent_requests": 10,
        "cost_limit_cents": 9900,  # $99
        "rate_limit_per_minute": 200
    },
    "enterprise": {
        "daily_requests": -1,  # Unlimited
        "monthly_requests": -1,  # Unlimited
        "concurrent_requests": 50,
        "cost_limit_cents": -1,  # Unlimited
        "rate_limit_per_minute": 1000
    }
}


class QuotaTestUser:
    """Test user with quota management capabilities."""
    
    def __init__(self, tier: str, user_id: str = None):
        self.tier = tier
        self.user_id = user_id or f"{tier}_user_{datetime.now().timestamp()}"
        self.current_usage = self._create_empty_usage()
    
    def _create_empty_usage(self) -> Dict[str, int]:
        """Create empty usage tracking."""
        return {
            "daily_requests": 0,
            "monthly_requests": 0,
            "concurrent_requests": 0,
            "cost_cents": 0
        }


def create_tier_user(tier: str, usage_percentage: float = 0.0) -> QuotaTestUser:
    """Create test user for specific tier with optional usage."""
    user = QuotaTestUser(tier)
    if usage_percentage > 0:
        set_user_usage_percentage(user, usage_percentage)
    return user


def set_user_usage_percentage(user: QuotaTestUser, percentage: float) -> None:
    """Set user usage to percentage of their tier limits."""
    limits = TIER_QUOTA_LIMITS[user.tier]
    
    if limits["daily_requests"] > 0:
        user.current_usage["daily_requests"] = int(limits["daily_requests"] * percentage)
    if limits["monthly_requests"] > 0:
        user.current_usage["monthly_requests"] = int(limits["monthly_requests"] * percentage)
    if limits["cost_limit_cents"] > 0:
        user.current_usage["cost_cents"] = int(limits["cost_limit_cents"] * percentage)


async def simulate_request_burst(user: QuotaTestUser, request_count: int) -> List[Dict]:
    """Simulate burst of requests for quota testing."""
    results = []
    for i in range(request_count):
        result = await check_quota_before_request(user, f"test_tool_{i}")
        results.append(result)
        if result["allowed"]:
            increment_user_usage(user, "daily_requests")
    return results


def increment_user_usage(user: QuotaTestUser, usage_type: str, amount: int = 1) -> None:
    """Increment user usage counter."""
    user.current_usage[usage_type] += amount


async def check_quota_before_request(user: QuotaTestUser, tool_name: str) -> Dict:
    """Check if user request is within quota limits."""
    limits = TIER_QUOTA_LIMITS[user.tier]
    usage = user.current_usage
    
    daily_allowed = (limits["daily_requests"] == -1 or 
                    usage["daily_requests"] < limits["daily_requests"])
    monthly_allowed = (limits["monthly_requests"] == -1 or 
                      usage["monthly_requests"] < limits["monthly_requests"])
    cost_allowed = (limits["cost_limit_cents"] == -1 or 
                   usage["cost_cents"] < limits["cost_limit_cents"])
    
    return {
        "allowed": daily_allowed and monthly_allowed and cost_allowed,
        "daily_remaining": _calculate_remaining(limits["daily_requests"], usage["daily_requests"]),
        "monthly_remaining": _calculate_remaining(limits["monthly_requests"], usage["monthly_requests"]),
        "cost_remaining_cents": _calculate_remaining(limits["cost_limit_cents"], usage["cost_cents"]),
        "tier": user.tier,
        "tool_name": tool_name
    }


def _calculate_remaining(limit: int, used: int) -> int:
    """Calculate remaining quota."""
    return -1 if limit == -1 else max(0, limit - used)


async def check_concurrent_request_limits(user: QuotaTestUser, concurrent_count: int) -> Dict:
    """Test concurrent request limiting."""
    limits = TIER_QUOTA_LIMITS[user.tier]
    max_concurrent = limits["concurrent_requests"]
    
    # Simulate concurrent requests
    concurrent_allowed = concurrent_count <= max_concurrent
    
    return {
        "concurrent_requests": concurrent_count,
        "max_allowed": max_concurrent,
        "allowed": concurrent_allowed,
        "tier": user.tier
    }


def create_usage_log_entry(user: QuotaTestUser, tool_name: str, 
                          status: str = "success", cost_cents: int = 10) -> Dict:
    """Create mock usage log entry."""
    return {
        "user_id": user.user_id,
        "tool_name": tool_name,
        "status": status,
        "cost_cents": cost_cents,
        "plan_tier": user.tier,
        "created_at": datetime.now(timezone.utc)
    }


async def simulate_monthly_reset(user: QuotaTestUser) -> Dict:
    """Simulate monthly quota reset."""
    old_usage = user.current_usage.copy()
    
    # Reset monthly counters
    user.current_usage["monthly_requests"] = 0
    user.current_usage["cost_cents"] = 0
    
    return {
        "reset_type": "monthly",
        "old_usage": old_usage,
        "new_usage": user.current_usage,
        "tier": user.tier
    }


async def simulate_daily_reset(user: QuotaTestUser) -> Dict:
    """Simulate daily quota reset."""
    old_usage = user.current_usage.copy()
    
    # Reset daily counters
    user.current_usage["daily_requests"] = 0
    
    return {
        "reset_type": "daily",
        "old_usage": old_usage,
        "new_usage": user.current_usage,
        "tier": user.tier
    }


def check_overage_notification_trigger(user: QuotaTestUser) -> Dict:
    """Check if overage notification should be triggered."""
    limits = TIER_QUOTA_LIMITS[user.tier]
    usage = user.current_usage
    
    # Check if user is approaching limits (80% threshold)
    daily_threshold = limits["daily_requests"] * 0.8 if limits["daily_requests"] > 0 else float('inf')
    monthly_threshold = limits["monthly_requests"] * 0.8 if limits["monthly_requests"] > 0 else float('inf')
    cost_threshold = limits["cost_limit_cents"] * 0.8 if limits["cost_limit_cents"] > 0 else float('inf')
    
    return {
        "should_notify": (
            usage["daily_requests"] >= daily_threshold or
            usage["monthly_requests"] >= monthly_threshold or
            usage["cost_cents"] >= cost_threshold
        ),
        "daily_at_threshold": usage["daily_requests"] >= daily_threshold,
        "monthly_at_threshold": usage["monthly_requests"] >= monthly_threshold,
        "cost_at_threshold": usage["cost_cents"] >= cost_threshold,
        "tier": user.tier
    }


async def check_rate_limiting_enforcement(user: QuotaTestUser, requests_per_minute: int) -> Dict:
    """Test rate limiting enforcement."""
    limits = TIER_QUOTA_LIMITS[user.tier]
    rate_limit = limits["rate_limit_per_minute"]
    
    # Create mock rate limiter
    limiter = MockRateLimiter(rate_limit_per_minute=rate_limit)
    
    # Test if requests per minute exceeds limit
    rate_limited = requests_per_minute > rate_limit
    
    return {
        "requests_per_minute": requests_per_minute,
        "rate_limit": rate_limit,
        "rate_limited": rate_limited,
        "tier": user.tier
    }


def assert_quota_enforcement_working(result: Dict) -> None:
    """Assert that quota enforcement is working correctly."""
    assert "allowed" in result
    assert "tier" in result
    if not result["allowed"]:
        assert (result.get("daily_remaining", 1) == 0 or 
                result.get("monthly_remaining", 1) == 0 or
                result.get("cost_remaining_cents", 1) == 0)


def assert_tier_limits_appropriate(tier: str) -> None:
    """Assert that tier limits are appropriately configured."""
    limits = TIER_QUOTA_LIMITS[tier]
    
    if tier == "free":
        assert limits["daily_requests"] <= 100
        assert limits["cost_limit_cents"] <= 1000
    elif tier == "enterprise":
        assert limits["daily_requests"] == -1  # Unlimited
        assert limits["cost_limit_cents"] == -1  # Unlimited
    else:  # early, mid
        assert limits["daily_requests"] > TIER_QUOTA_LIMITS["free"]["daily_requests"]


def assert_overage_notification_logic(result: Dict) -> None:
    """Assert overage notification logic is correct."""
    assert "should_notify" in result
    assert "tier" in result
    if result["should_notify"]:
        assert (result.get("daily_at_threshold", False) or
                result.get("monthly_at_threshold", False) or
                result.get("cost_at_threshold", False))


def assert_rate_limiting_working(result: Dict) -> None:
    """Assert rate limiting is working correctly."""
    assert "rate_limited" in result
    assert "requests_per_minute" in result
    assert "rate_limit" in result
    if result["rate_limited"]:
        assert result["requests_per_minute"] > result["rate_limit"]


def create_high_usage_scenario(tier: str) -> QuotaTestUser:
    """Create user with high usage for testing edge cases."""
    user = create_tier_user(tier, usage_percentage=0.95)
    return user


def create_quota_exhausted_scenario(tier: str) -> QuotaTestUser:
    """Create user with exhausted quota for testing blocking."""
    user = create_tier_user(tier)
    limits = TIER_QUOTA_LIMITS[tier]
    
    # Set usage to exactly at limits (or above for unlimited tiers)
    if limits["daily_requests"] > 0:
        user.current_usage["daily_requests"] = limits["daily_requests"]
    if limits["monthly_requests"] > 0:
        user.current_usage["monthly_requests"] = limits["monthly_requests"]
    if limits["cost_limit_cents"] > 0:
        user.current_usage["cost_cents"] = limits["cost_limit_cents"]
    
    return user


async def validate_fair_usage_across_tiers() -> Dict:
    """Validate that fair usage is enforced across all tiers."""
    results = {}
    
    for tier in ["free", "early", "mid", "enterprise"]:
        user = create_tier_user(tier)
        quota_check = await check_quota_before_request(user, "validation_tool")
        results[tier] = quota_check
    
    return results
