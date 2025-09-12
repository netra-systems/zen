"""CRITICAL E2E Test: Agent Quota Management and Fair Usage.

BUSINESS VALUE JUSTIFICATION:
1. Segment: All tiers (Free, Early, Mid, Enterprise) - Direct revenue protection
2. Business Goal: Protect $30K+ MRR from quota abuse and overage issues
3. Value Impact: Prevents revenue loss from service abuse and ensures fair usage
4. Revenue Impact: Maintains sustainable platform growth and conversion funnel

CRITICAL PATH: Request  ->  Quota Check  ->  Execution  ->  Usage Tracking  ->  Limit Enforcement
"""

import pytest
import asyncio
from typing import Dict
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.quota_management_helpers import (
    create_tier_user, simulate_request_burst, check_quota_before_request, check_concurrent_request_limits, simulate_daily_reset, check_overage_notification_trigger, check_rate_limiting_enforcement, assert_quota_enforcement_working, create_high_usage_scenario, TIER_QUOTA_LIMITS,
    create_tier_user, simulate_request_burst, check_quota_before_request,
    check_concurrent_request_limits, simulate_daily_reset,
    check_overage_notification_trigger, check_rate_limiting_enforcement,
    assert_quota_enforcement_working, create_high_usage_scenario,
    TIER_QUOTA_LIMITS
)


@pytest.mark.e2e
class TestQuotaEnforcement:
    """Test core quota enforcement across all tiers."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_free_tier_quota_blocks_abuse(self):
        """Free tier quota strictly enforced to prevent abuse."""
        user = create_tier_user("free", usage_percentage=0.0)
        result = await check_quota_before_request(user, "test_tool")
        assert result["allowed"] is True
        
        # Test abuse prevention
        abuser = create_tier_user("free")
        abuse_results = await simulate_request_burst(abuser, 60)
        blocked_count = sum(1 for r in abuse_results if not r["allowed"])
        assert blocked_count >= 10  # Should block excessive requests

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_enterprise_tier_unlimited_access(self):
        """Enterprise tier has unlimited quota access."""
        user = create_tier_user("enterprise")
        result = await check_quota_before_request(user, "unlimited_tool")
        assert result["allowed"] is True
        assert result["daily_remaining"] == -1  # Unlimited
        assert result["tier"] == "enterprise"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_tier_hierarchy_consistency(self):
        """Higher tiers have progressively higher limits."""
        free_limits = TIER_QUOTA_LIMITS["free"]
        early_limits = TIER_QUOTA_LIMITS["early"]
        mid_limits = TIER_QUOTA_LIMITS["mid"]
        
        assert early_limits["daily_requests"] > free_limits["daily_requests"]
        assert mid_limits["daily_requests"] > early_limits["daily_requests"]
        assert early_limits["cost_limit_cents"] > free_limits["cost_limit_cents"]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_quota_performance_under_load(self):
        """Quota checks maintain performance under concurrent load."""
        users = [create_tier_user("mid") for _ in range(10)]
        tasks = [check_quota_before_request(user, "load_test") for user in users]
        
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        duration = asyncio.get_event_loop().time() - start_time
        
        assert duration < 1.0  # Should complete in under 1 second
        assert len(results) == 10
        for result in results:
            assert "allowed" in result


@pytest.mark.e2e
class TestRateLimiting:
    """Test rate limiting enforcement."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_free_tier_rate_limiting(self):
        """Free tier has strict rate limiting."""
        user = create_tier_user("free")
        result = await check_rate_limiting_enforcement(user, 15)
        assert result["rate_limited"] is True

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_concurrent_request_limits(self):
        """Concurrent request limits prevent resource exhaustion."""
        for tier in ["free", "early", "mid", "enterprise"]:
            user = create_tier_user(tier)
            within_limit = TIER_QUOTA_LIMITS[tier]["concurrent_requests"] - 1
            over_limit = TIER_QUOTA_LIMITS[tier]["concurrent_requests"] + 5
            
            within_result = await check_concurrent_request_limits(user, within_limit)
            over_result = await check_concurrent_request_limits(user, over_limit)
            
            assert within_result["allowed"] is True
            assert over_result["allowed"] is False


@pytest.mark.e2e
class TestQuotaResets:
    """Test quota reset functionality."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_daily_quota_reset_restores_access(self):
        """Daily quota reset restores access for blocked users."""
        user = create_tier_user("free")
        limits = TIER_QUOTA_LIMITS["free"]
        user.current_usage["daily_requests"] = limits["daily_requests"]
        
        blocked_result = await check_quota_before_request(user, "blocked_tool")
        assert blocked_result["allowed"] is False
        
        await simulate_daily_reset(user)
        restored_result = await check_quota_before_request(user, "restored_tool")
        assert restored_result["allowed"] is True

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_quota_reset_timing_accuracy(self):
        """Quota resets maintain timing accuracy."""
        user = create_tier_user("early")
        reset_result = await simulate_daily_reset(user)
        
        assert reset_result["reset_type"] == "daily"
        assert user.current_usage["daily_requests"] == 0


@pytest.mark.e2e
class TestOverageNotifications:
    """Test overage notification system."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_notification_at_80_percent_threshold(self):
        """Overage notifications trigger at 80% usage threshold."""
        user = create_tier_user("free", usage_percentage=0.85)
        notification = check_overage_notification_trigger(user)
        assert notification["should_notify"] is True

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_no_notification_below_threshold(self):
        """No notifications below 80% threshold."""
        user = create_tier_user("early", usage_percentage=0.70)
        notification = check_overage_notification_trigger(user)
        assert notification["should_notify"] is False

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_enterprise_no_standard_notifications(self):
        """Enterprise users don't get standard overage notifications."""
        user = create_tier_user("enterprise", usage_percentage=0.95)
        notification = check_overage_notification_trigger(user)
        assert notification["should_notify"] is False


@pytest.mark.e2e
class TestFairUsageValidation:
    """Test fair usage enforcement across platform."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_abuse_prevention_effectiveness(self):
        """Fair usage prevents system abuse."""
        abuser = create_tier_user("free")
        abuse_results = await simulate_request_burst(abuser, 100)
        
        blocked_count = sum(1 for r in abuse_results if not r["allowed"])
        assert blocked_count >= 50  # Should block once limit reached
        
        for blocked_result in abuse_results[-5:]:
            assert blocked_result["allowed"] is False

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_legitimate_usage_not_impacted(self):
        """Fair usage doesn't impact legitimate patterns."""
        user = create_tier_user("mid")
        
        # Simulate normal usage: 160 requests over 8 hours (20/hour)
        normal_results = []
        for request in range(160):
            result = await check_quota_before_request(user, f"work_tool_{request}")
            normal_results.append(result)
            if result["allowed"]:
                user.current_usage["daily_requests"] += 1
        
        allowed_count = sum(1 for r in normal_results if r["allowed"])
        assert allowed_count == len(normal_results)

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cross_tier_isolation(self):
        """Usage in one tier doesn't affect other tiers."""
        free_user = create_tier_user("free")
        free_user.current_usage["daily_requests"] = TIER_QUOTA_LIMITS["free"]["daily_requests"]
        enterprise_user = create_tier_user("enterprise")
        
        free_result = await check_quota_before_request(free_user, "isolation_test")
        enterprise_result = await check_quota_before_request(enterprise_user, "isolation_test")
        
        assert free_result["allowed"] is False
        assert enterprise_result["allowed"] is True

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_quota_system_reliability(self):
        """Quota system maintains reliability under concurrent load."""
        users = [create_tier_user("early") for _ in range(20)]
        tasks = [check_quota_before_request(user, "reliability_test") for user in users]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == len(users)
        for result in results:
            assert "allowed" in result
            assert "tier" in result

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_upgrade_path_preservation(self):
        """Fair usage preserves clear upgrade incentives."""
        free_user = create_tier_user("free")
        early_user = create_tier_user("early")
        
        free_quota = await check_quota_before_request(free_user, "upgrade_test")
        early_quota = await check_quota_before_request(early_user, "upgrade_test")
        
        # Early tier should have better access than free
        assert early_quota["daily_remaining"] > free_quota["daily_remaining"]
        assert early_quota["cost_remaining_cents"] > free_quota["cost_remaining_cents"]


@pytest.mark.e2e
class TestQuotaIntegration:
    """Test integrated quota management scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_high_usage_user_workflow(self):
        """High usage user experiences appropriate quota management."""
        user = create_high_usage_scenario("free")
        
        # Check current state
        current_check = await check_quota_before_request(user, "high_usage_tool")
        notification = check_overage_notification_trigger(user)
        
        # Should be near limits and get notification
        assert notification["should_notify"] is True
        assert current_check["daily_remaining"] < 10

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mixed_tier_concurrent_usage(self):
        """Mixed tier users can use system concurrently."""
        users = [
            create_tier_user("free"),
            create_tier_user("early"),
            create_tier_user("mid"),
            create_tier_user("enterprise")
        ]
        
        tasks = [check_quota_before_request(user, "mixed_test") for user in users]
        results = await asyncio.gather(*tasks)
        
        # All tiers should get appropriate access
        for i, result in enumerate(results):
            assert result["tier"] == ["free", "early", "mid", "enterprise"][i]
            assert "allowed" in result

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_quota_enforcement_end_to_end(self):
        """End-to-end quota enforcement workflow."""
        user = create_tier_user("free")
        
        # Step 1: Normal usage
        normal_result = await check_quota_before_request(user, "normal_tool")
        assert normal_result["allowed"] is True
        
        # Step 2: Approach limits
        user.current_usage["daily_requests"] = 45  # Near 50 limit
        approaching_result = await check_quota_before_request(user, "approaching_tool")
        notification = check_overage_notification_trigger(user)
        
        assert approaching_result["allowed"] is True
        assert notification["should_notify"] is True
        
        # Step 3: Hit limits
        user.current_usage["daily_requests"] = 50  # At limit
        blocked_result = await check_quota_before_request(user, "blocked_tool")
        assert blocked_result["allowed"] is False
        
        # Step 4: Reset and restore
        await simulate_daily_reset(user)
        restored_result = await check_quota_before_request(user, "restored_tool")
        assert restored_result["allowed"] is True
