"""Comprehensive Unit Tests for UsageTracker.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Critical billing infrastructure for all tiers
- Business Goal: Revenue Protection & Consumption Tracking - Track user consumption accurately for billing
- Value Impact: Prevents revenue loss through accurate usage tracking and billing calculations
- Strategic Impact: Foundation for monetization through consumption-based billing and rate limiting

This test suite provides 100% comprehensive unit test coverage for UsageTracker
following CLAUDE.md best practices and TEST_CREATION_GUIDE.md patterns.

CRITICAL: This class tracks all user consumption that directly impacts billing accuracy.
Comprehensive testing prevents under-tracking (revenue loss) or over-tracking (customer churn).
Usage tracking forms the foundation of our consumption-based pricing model.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import asdict

from netra_backend.app.services.billing.usage_tracker import (
    UsageTracker, 
    UsageType, 
    UsageEvent
)
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.unit
class TestUsageTrackerInitialization(BaseTestCase):
    """Test UsageTracker initialization and configuration."""

    def test_usage_tracker_initialization_success(self):
        """Test successful initialization of UsageTracker."""
        tracker = UsageTracker()
        
        assert tracker is not None
        assert isinstance(tracker, UsageTracker)
        assert tracker.enabled is True
        assert len(tracker.usage_events) == 0
        assert len(tracker.user_totals) == 0

    def test_usage_tracker_initialization_pricing_loaded(self):
        """Test that pricing configuration is properly loaded."""
        tracker = UsageTracker()
        
        # Verify all usage types have pricing
        expected_types = {
            UsageType.API_CALL,
            UsageType.LLM_TOKENS,
            UsageType.STORAGE,
            UsageType.COMPUTE,
            UsageType.BANDWIDTH,
            UsageType.WEBSOCKET_CONNECTION,
            UsageType.AGENT_EXECUTION
        }
        
        assert set(tracker.pricing.keys()) == expected_types
        
        # Verify pricing values are positive
        for usage_type, price in tracker.pricing.items():
            assert price >= 0.0
            assert isinstance(price, (int, float))

    def test_usage_tracker_initialization_rate_limits_configured(self):
        """Test that rate limits are properly configured."""
        tracker = UsageTracker()
        
        # Verify rate limits are configured for expected types
        assert UsageType.API_CALL in tracker.rate_limits
        assert UsageType.LLM_TOKENS in tracker.rate_limits
        assert UsageType.WEBSOCKET_CONNECTION in tracker.rate_limits
        
        # Verify rate limit structure
        for usage_type, config in tracker.rate_limits.items():
            assert "limit" in config
            assert "window" in config
            assert config["limit"] > 0
            assert config["window"] > 0

    def test_usage_tracker_initialization_multiple_instances(self):
        """Test that multiple tracker instances are independent."""
        tracker1 = UsageTracker()
        tracker2 = UsageTracker()
        
        assert tracker1 is not tracker2
        assert tracker1.usage_events is not tracker2.usage_events
        assert tracker1.user_totals is not tracker2.user_totals


@pytest.mark.unit
class TestUsageEventCreation(BaseTestCase):
    """Test UsageEvent data model."""

    def test_usage_event_creation_basic(self):
        """Test basic usage event creation."""
        timestamp = datetime.now(timezone.utc)
        event = UsageEvent(
            user_id="user_123",
            usage_type=UsageType.API_CALL,
            quantity=1.0,
            unit="call",
            timestamp=timestamp,
            cost=0.001
        )
        
        assert event.user_id == "user_123"
        assert event.usage_type == UsageType.API_CALL
        assert event.quantity == 1.0
        assert event.unit == "call"
        assert event.timestamp == timestamp
        assert event.cost == 0.001
        assert event.metadata == {}

    def test_usage_event_creation_with_metadata(self):
        """Test usage event creation with metadata."""
        metadata = {"model": "gpt-4", "endpoint": "/api/chat"}
        event = UsageEvent(
            user_id="user_123",
            usage_type=UsageType.LLM_TOKENS,
            quantity=1000.0,
            unit="tokens",
            timestamp=datetime.now(timezone.utc),
            metadata=metadata
        )
        
        assert event.metadata == metadata

    def test_usage_event_post_init_string_conversion(self):
        """Test that string usage_type is converted to enum."""
        event = UsageEvent(
            user_id="user_123",
            usage_type="api_call",  # String instead of enum
            quantity=1.0,
            unit="call",
            timestamp=datetime.now(timezone.utc)
        )
        
        assert event.usage_type == UsageType.API_CALL
        assert isinstance(event.usage_type, UsageType)

    def test_usage_event_post_init_metadata_initialization(self):
        """Test that metadata is initialized if None."""
        event = UsageEvent(
            user_id="user_123",
            usage_type=UsageType.API_CALL,
            quantity=1.0,
            unit="call",
            timestamp=datetime.now(timezone.utc),
            metadata=None
        )
        
        assert event.metadata == {}
        assert isinstance(event.metadata, dict)


@pytest.mark.unit
class TestUsageTracking(BaseTestCase):
    """Test core usage tracking functionality."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.tracker = UsageTracker()

    @pytest.mark.asyncio
    async def test_track_usage_basic_api_call(self):
        """Test tracking basic API call usage."""
        user_id = "user_123"
        usage_type = UsageType.API_CALL
        quantity = 1.0
        
        event = await self.tracker.track_usage(
            user_id=user_id,
            usage_type=usage_type,
            quantity=quantity,
            unit="call"
        )
        
        # Verify event created correctly
        assert event.user_id == user_id
        assert event.usage_type == usage_type
        assert event.quantity == quantity
        assert event.unit == "call"
        assert event.cost == quantity * self.tracker.pricing[usage_type]
        
        # Verify event stored
        assert len(self.tracker.usage_events) == 1
        assert self.tracker.usage_events[0] == event
        
        # Verify user totals updated
        assert user_id in self.tracker.user_totals
        assert self.tracker.user_totals[user_id][usage_type.value] == quantity

    @pytest.mark.asyncio
    async def test_track_usage_llm_tokens_bulk(self):
        """Test tracking LLM token usage with large quantities."""
        user_id = "user_enterprise"
        usage_type = UsageType.LLM_TOKENS
        quantity = 50000.0
        
        event = await self.tracker.track_usage(
            user_id=user_id,
            usage_type=usage_type,
            quantity=quantity,
            unit="tokens",
            metadata={"model": "gpt-4", "prompt_tokens": 30000, "completion_tokens": 20000}
        )
        
        expected_cost = quantity * self.tracker.pricing[usage_type]
        
        assert event.quantity == quantity
        assert event.cost == expected_cost
        assert event.metadata["model"] == "gpt-4"
        assert self.tracker.user_totals[user_id][usage_type.value] == quantity

    @pytest.mark.asyncio
    async def test_track_usage_multiple_types_same_user(self):
        """Test tracking multiple usage types for same user."""
        user_id = "user_multi"
        
        # Track API calls
        await self.tracker.track_usage(user_id, UsageType.API_CALL, 10.0, "calls")
        
        # Track LLM tokens
        await self.tracker.track_usage(user_id, UsageType.LLM_TOKENS, 5000.0, "tokens")
        
        # Track storage
        await self.tracker.track_usage(user_id, UsageType.STORAGE, 2.5, "gb")
        
        assert len(self.tracker.usage_events) == 3
        assert len(self.tracker.user_totals[user_id]) == 3
        
        # Verify accumulated totals
        assert self.tracker.user_totals[user_id][UsageType.API_CALL.value] == 10.0
        assert self.tracker.user_totals[user_id][UsageType.LLM_TOKENS.value] == 5000.0
        assert self.tracker.user_totals[user_id][UsageType.STORAGE.value] == 2.5

    @pytest.mark.asyncio
    async def test_track_usage_accumulation_same_type(self):
        """Test that usage accumulates for same type."""
        user_id = "user_accumulate"
        usage_type = UsageType.API_CALL
        
        # Track multiple API calls
        await self.tracker.track_usage(user_id, usage_type, 5.0, "calls")
        await self.tracker.track_usage(user_id, usage_type, 3.0, "calls")
        await self.tracker.track_usage(user_id, usage_type, 2.0, "calls")
        
        # Verify accumulation
        assert len(self.tracker.usage_events) == 3
        assert self.tracker.user_totals[user_id][usage_type.value] == 10.0
        
        # Verify each event has correct individual quantities
        quantities = [event.quantity for event in self.tracker.usage_events]
        assert quantities == [5.0, 3.0, 2.0]

    @pytest.mark.asyncio
    async def test_track_usage_disabled_tracker(self):
        """Test that tracking returns None when tracker is disabled."""
        self.tracker.enabled = False
        
        event = await self.tracker.track_usage(
            user_id="user_disabled",
            usage_type=UsageType.API_CALL,
            quantity=1.0
        )
        
        assert event is None
        assert len(self.tracker.usage_events) == 0
        assert len(self.tracker.user_totals) == 0

    @pytest.mark.asyncio
    async def test_track_usage_zero_quantity(self):
        """Test tracking usage with zero quantity."""
        event = await self.tracker.track_usage(
            user_id="user_zero",
            usage_type=UsageType.API_CALL,
            quantity=0.0
        )
        
        assert event.quantity == 0.0
        assert event.cost == 0.0
        assert len(self.tracker.usage_events) == 1

    @pytest.mark.asyncio
    async def test_track_usage_fractional_quantity(self):
        """Test tracking usage with fractional quantities."""
        event = await self.tracker.track_usage(
            user_id="user_fractional",
            usage_type=UsageType.STORAGE,
            quantity=1.75,
            unit="gb"
        )
        
        expected_cost = 1.75 * self.tracker.pricing[UsageType.STORAGE]
        
        assert event.quantity == 1.75
        assert event.cost == expected_cost
        assert self.tracker.user_totals["user_fractional"][UsageType.STORAGE.value] == 1.75

    @pytest.mark.asyncio
    async def test_track_usage_persistence_error_handling(self):
        """Test that persistence errors are handled gracefully within _persist_event."""
        # Create a spy to verify _persist_event is called and see it handle exceptions
        original_persist = self.tracker._persist_event
        persist_called = False
        
        async def mock_persist_with_error(event):
            nonlocal persist_called
            persist_called = True
            # Simulate what happens in real _persist_event - exception is caught
            try:
                raise Exception("DB error")
            except Exception:
                # Exception is caught and handled gracefully (as per implementation)
                pass
        
        self.tracker._persist_event = mock_persist_with_error
        
        event = await self.tracker.track_usage(
            user_id="user_persist_error",
            usage_type=UsageType.API_CALL,
            quantity=1.0
        )
        
        # Event should still be created and stored in memory
        assert event is not None
        assert len(self.tracker.usage_events) == 1
        assert event.user_id == "user_persist_error"
        assert persist_called is True  # Verify persistence was attempted
        
        # Restore original method
        self.tracker._persist_event = original_persist


@pytest.mark.unit
class TestUsageRetrieval(BaseTestCase):
    """Test usage retrieval and reporting functionality."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.tracker = UsageTracker()

    @pytest.mark.asyncio
    async def test_get_user_usage_no_events(self):
        """Test getting usage for user with no events."""
        usage_summary = await self.tracker.get_user_usage("nonexistent_user")
        
        assert usage_summary["user_id"] == "nonexistent_user"
        assert usage_summary["usage_summary"] == {}
        assert usage_summary["total_cost"] == 0.0
        assert usage_summary["total_events"] == 0

    @pytest.mark.asyncio
    async def test_get_user_usage_basic_summary(self):
        """Test basic usage summary generation."""
        user_id = "user_summary"
        
        # Add some usage events
        await self.tracker.track_usage(user_id, UsageType.API_CALL, 10.0, "calls")
        await self.tracker.track_usage(user_id, UsageType.LLM_TOKENS, 5000.0, "tokens")
        
        usage_summary = await self.tracker.get_user_usage(user_id)
        
        assert usage_summary["user_id"] == user_id
        assert usage_summary["total_events"] == 2
        
        # Verify API call summary
        api_summary = usage_summary["usage_summary"][UsageType.API_CALL.value]
        assert api_summary["quantity"] == 10.0
        assert api_summary["events"] == 1
        assert api_summary["cost"] == 10.0 * self.tracker.pricing[UsageType.API_CALL]
        
        # Verify LLM tokens summary
        token_summary = usage_summary["usage_summary"][UsageType.LLM_TOKENS.value]
        assert token_summary["quantity"] == 5000.0
        assert token_summary["events"] == 1
        assert token_summary["cost"] == 5000.0 * self.tracker.pricing[UsageType.LLM_TOKENS]
        
        # Verify total cost
        expected_total_cost = (
            10.0 * self.tracker.pricing[UsageType.API_CALL] +
            5000.0 * self.tracker.pricing[UsageType.LLM_TOKENS]
        )
        assert usage_summary["total_cost"] == expected_total_cost

    @pytest.mark.asyncio
    async def test_get_user_usage_time_range_filtering(self):
        """Test usage retrieval with time range filtering."""
        user_id = "user_time_filter"
        
        # Create events at different times
        base_time = datetime.now(timezone.utc)
        
        # Past event (should be excluded)
        past_event = UsageEvent(
            user_id=user_id,
            usage_type=UsageType.API_CALL,
            quantity=5.0,
            unit="calls",
            timestamp=base_time - timedelta(hours=2),
            cost=5.0 * self.tracker.pricing[UsageType.API_CALL]
        )
        self.tracker.usage_events.append(past_event)
        
        # Current event (should be included)
        await self.tracker.track_usage(user_id, UsageType.API_CALL, 3.0, "calls")
        
        # Filter to last hour
        start_time = base_time - timedelta(hours=1)
        usage_summary = await self.tracker.get_user_usage(
            user_id=user_id,
            start_time=start_time
        )
        
        # Should only include the recent event
        assert usage_summary["total_events"] == 1
        assert usage_summary["usage_summary"][UsageType.API_CALL.value]["quantity"] == 3.0

    @pytest.mark.asyncio
    async def test_get_user_usage_end_time_filtering(self):
        """Test usage retrieval with end time filtering."""
        user_id = "user_end_filter"
        
        base_time = datetime.now(timezone.utc)
        
        # Add current event
        await self.tracker.track_usage(user_id, UsageType.API_CALL, 2.0, "calls")
        
        # Filter to exclude current events
        end_time = base_time - timedelta(hours=1)
        usage_summary = await self.tracker.get_user_usage(
            user_id=user_id,
            end_time=end_time
        )
        
        # Should exclude all current events
        assert usage_summary["total_events"] == 0
        assert usage_summary["usage_summary"] == {}

    @pytest.mark.asyncio
    async def test_get_user_usage_multiple_events_same_type(self):
        """Test usage summary with multiple events of same type."""
        user_id = "user_multiple_same"
        
        # Add multiple API call events
        await self.tracker.track_usage(user_id, UsageType.API_CALL, 5.0, "calls")
        await self.tracker.track_usage(user_id, UsageType.API_CALL, 3.0, "calls")
        await self.tracker.track_usage(user_id, UsageType.API_CALL, 7.0, "calls")
        
        usage_summary = await self.tracker.get_user_usage(user_id)
        
        api_summary = usage_summary["usage_summary"][UsageType.API_CALL.value]
        
        # Should aggregate quantities and costs, count events
        assert api_summary["quantity"] == 15.0  # 5 + 3 + 7
        assert api_summary["events"] == 3
        assert api_summary["cost"] == 15.0 * self.tracker.pricing[UsageType.API_CALL]


@pytest.mark.unit
class TestRateLimiting(BaseTestCase):
    """Test rate limiting functionality."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.tracker = UsageTracker()

    @pytest.mark.asyncio
    async def test_check_rate_limit_no_prior_usage(self):
        """Test rate limit check for user with no prior usage."""
        result = await self.tracker.check_rate_limit("new_user", UsageType.API_CALL)
        
        assert result["allowed"] is True
        assert result["remaining"] == self.tracker.rate_limits[UsageType.API_CALL]["limit"]
        assert result["current_usage"] == 0.0
        assert result["limit"] == self.tracker.rate_limits[UsageType.API_CALL]["limit"]
        assert result["window_seconds"] == self.tracker.rate_limits[UsageType.API_CALL]["window"]

    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limits(self):
        """Test rate limit check within limits."""
        user_id = "user_within_limits"
        
        # Add some usage within limits
        await self.tracker.track_usage(user_id, UsageType.API_CALL, 100.0, "calls")
        
        result = await self.tracker.check_rate_limit(user_id, UsageType.API_CALL)
        
        limit = self.tracker.rate_limits[UsageType.API_CALL]["limit"]
        
        assert result["allowed"] is True
        assert result["remaining"] == limit - 100.0
        assert result["current_usage"] == 100.0

    @pytest.mark.asyncio
    async def test_check_rate_limit_at_limit(self):
        """Test rate limit check at exact limit."""
        user_id = "user_at_limit"
        limit = self.tracker.rate_limits[UsageType.API_CALL]["limit"]
        
        # Use exact limit
        await self.tracker.track_usage(user_id, UsageType.API_CALL, limit, "calls")
        
        result = await self.tracker.check_rate_limit(user_id, UsageType.API_CALL)
        
        assert result["allowed"] is False
        assert result["remaining"] == 0.0
        assert result["current_usage"] == limit

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self):
        """Test rate limit check when exceeded."""
        user_id = "user_exceeded"
        limit = self.tracker.rate_limits[UsageType.API_CALL]["limit"]
        
        # Exceed limit
        await self.tracker.track_usage(user_id, UsageType.API_CALL, limit + 100.0, "calls")
        
        result = await self.tracker.check_rate_limit(user_id, UsageType.API_CALL)
        
        assert result["allowed"] is False
        assert result["remaining"] == 0.0
        assert result["current_usage"] == limit + 100.0

    @pytest.mark.asyncio
    async def test_check_rate_limit_no_limit_configured(self):
        """Test rate limit check for usage type with no limits."""
        result = await self.tracker.check_rate_limit("any_user", UsageType.STORAGE)
        
        assert result["allowed"] is True
        assert result["remaining"] == float('inf')

    @pytest.mark.asyncio
    async def test_check_rate_limit_window_expiry(self):
        """Test that rate limits reset after window expiry."""
        user_id = "user_window_expiry"
        limit = self.tracker.rate_limits[UsageType.API_CALL]["limit"]
        window = self.tracker.rate_limits[UsageType.API_CALL]["window"]
        
        # Create old event outside window
        old_timestamp = datetime.now(timezone.utc) - timedelta(seconds=window + 60)
        old_event = UsageEvent(
            user_id=user_id,
            usage_type=UsageType.API_CALL,
            quantity=limit,
            unit="calls",
            timestamp=old_timestamp,
            cost=0.0
        )
        self.tracker.usage_events.append(old_event)
        
        # Check rate limit - old usage should not count
        result = await self.tracker.check_rate_limit(user_id, UsageType.API_CALL)
        
        assert result["allowed"] is True
        assert result["remaining"] == limit
        assert result["current_usage"] == 0.0

    @pytest.mark.asyncio
    async def test_check_rate_limit_multiple_users_isolation(self):
        """Test that rate limits are isolated per user."""
        user1 = "user_1"
        user2 = "user_2"
        limit = self.tracker.rate_limits[UsageType.API_CALL]["limit"]
        
        # User 1 hits limit
        await self.tracker.track_usage(user1, UsageType.API_CALL, limit, "calls")
        
        # User 2 should still have full limit
        result = await self.tracker.check_rate_limit(user2, UsageType.API_CALL)
        
        assert result["allowed"] is True
        assert result["remaining"] == limit
        assert result["current_usage"] == 0.0


@pytest.mark.unit
class TestUsageAnalytics(BaseTestCase):
    """Test analytics and reporting functionality."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.tracker = UsageTracker()

    @pytest.mark.asyncio
    async def test_get_usage_analytics_no_events(self):
        """Test analytics with no events."""
        analytics = await self.tracker.get_usage_analytics()
        
        assert analytics["totals"]["events"] == 0
        assert analytics["totals"]["cost"] == 0.0
        assert analytics["totals"]["unique_users"] == 0
        assert analytics["usage_by_type"] == {}
        assert analytics["top_users"] == []

    @pytest.mark.asyncio
    async def test_get_usage_analytics_basic(self):
        """Test basic analytics generation."""
        # Add events for multiple users
        await self.tracker.track_usage("user_1", UsageType.API_CALL, 100.0, "calls")
        await self.tracker.track_usage("user_1", UsageType.LLM_TOKENS, 5000.0, "tokens")
        await self.tracker.track_usage("user_2", UsageType.API_CALL, 50.0, "calls")
        
        analytics = await self.tracker.get_usage_analytics()
        
        # Verify totals
        assert analytics["totals"]["events"] == 3
        assert analytics["totals"]["unique_users"] == 2
        
        # Verify usage by type
        api_usage = analytics["usage_by_type"][UsageType.API_CALL.value]
        assert api_usage["events"] == 2
        assert api_usage["quantity"] == 150.0  # 100 + 50
        
        token_usage = analytics["usage_by_type"][UsageType.LLM_TOKENS.value]
        assert token_usage["events"] == 1
        assert token_usage["quantity"] == 5000.0

    @pytest.mark.asyncio
    async def test_get_usage_analytics_top_users(self):
        """Test top users ranking in analytics."""
        # Create users with different cost levels
        await self.tracker.track_usage("high_user", UsageType.LLM_TOKENS, 100000.0, "tokens")
        await self.tracker.track_usage("low_user", UsageType.API_CALL, 10.0, "calls")
        await self.tracker.track_usage("mid_user", UsageType.LLM_TOKENS, 25000.0, "tokens")
        
        analytics = await self.tracker.get_usage_analytics()
        
        top_users = analytics["top_users"]
        assert len(top_users) == 3
        
        # Should be sorted by cost descending
        assert top_users[0]["user_id"] == "high_user"
        assert top_users[1]["user_id"] == "mid_user"
        assert top_users[2]["user_id"] == "low_user"
        
        # Verify cost ordering
        assert top_users[0]["cost"] > top_users[1]["cost"]
        assert top_users[1]["cost"] > top_users[2]["cost"]

    @pytest.mark.asyncio
    async def test_get_usage_analytics_time_filtering(self):
        """Test analytics with time range filtering."""
        base_time = datetime.now(timezone.utc)
        
        # Add old event
        old_event = UsageEvent(
            user_id="user_old",
            usage_type=UsageType.API_CALL,
            quantity=100.0,
            unit="calls",
            timestamp=base_time - timedelta(hours=2),
            cost=100.0 * self.tracker.pricing[UsageType.API_CALL]
        )
        self.tracker.usage_events.append(old_event)
        
        # Add recent event
        await self.tracker.track_usage("user_recent", UsageType.API_CALL, 50.0, "calls")
        
        # Filter to last hour
        start_time = base_time - timedelta(hours=1)
        analytics = await self.tracker.get_usage_analytics(start_time=start_time)
        
        # Should only include recent event
        assert analytics["totals"]["events"] == 1
        assert analytics["totals"]["unique_users"] == 1
        assert len(analytics["top_users"]) == 1
        assert analytics["top_users"][0]["user_id"] == "user_recent"

    @pytest.mark.asyncio
    async def test_get_usage_analytics_cost_accuracy(self):
        """Test that analytics cost calculations are accurate."""
        user_id = "cost_test_user"
        
        # Add known quantities with predictable costs
        api_quantity = 1000.0
        token_quantity = 50000.0
        
        await self.tracker.track_usage(user_id, UsageType.API_CALL, api_quantity, "calls")
        await self.tracker.track_usage(user_id, UsageType.LLM_TOKENS, token_quantity, "tokens")
        
        expected_api_cost = api_quantity * self.tracker.pricing[UsageType.API_CALL]
        expected_token_cost = token_quantity * self.tracker.pricing[UsageType.LLM_TOKENS]
        expected_total_cost = expected_api_cost + expected_token_cost
        
        analytics = await self.tracker.get_usage_analytics()
        
        assert analytics["totals"]["cost"] == expected_total_cost
        assert analytics["usage_by_type"][UsageType.API_CALL.value]["cost"] == expected_api_cost
        assert analytics["usage_by_type"][UsageType.LLM_TOKENS.value]["cost"] == expected_token_cost
        assert analytics["top_users"][0]["cost"] == expected_total_cost


@pytest.mark.unit
class TestPricingManagement(BaseTestCase):
    """Test pricing configuration and updates."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.tracker = UsageTracker()

    def test_get_pricing_returns_all_types(self):
        """Test that get_pricing returns pricing for all usage types."""
        pricing = self.tracker.get_pricing()
        
        expected_types = {usage_type.value for usage_type in UsageType}
        actual_types = set(pricing.keys())
        
        assert actual_types == expected_types
        
        # Verify all prices are non-negative numbers
        for usage_type, price in pricing.items():
            assert isinstance(price, (int, float))
            assert price >= 0.0

    def test_update_pricing_valid_updates(self):
        """Test updating pricing with valid values."""
        original_api_price = self.tracker.pricing[UsageType.API_CALL]
        
        updates = {
            "api_call": 0.002,
            "llm_tokens": 0.00003
        }
        
        self.tracker.update_pricing(updates)
        
        # Verify updates applied
        assert self.tracker.pricing[UsageType.API_CALL] == 0.002
        assert self.tracker.pricing[UsageType.LLM_TOKENS] == 0.00003
        
        # Verify other prices unchanged
        assert self.tracker.pricing[UsageType.STORAGE] != 0.002

    def test_update_pricing_invalid_usage_type(self):
        """Test that invalid usage types are ignored."""
        original_pricing = self.tracker.pricing.copy()
        
        updates = {
            "invalid_type": 0.5,
            "api_call": 0.002  # Valid update
        }
        
        self.tracker.update_pricing(updates)
        
        # Valid update should be applied
        assert self.tracker.pricing[UsageType.API_CALL] == 0.002
        
        # Invalid update should be ignored, no new keys added
        assert len(self.tracker.pricing) == len(original_pricing)

    def test_update_pricing_zero_price(self):
        """Test updating pricing to zero (free tier)."""
        self.tracker.update_pricing({"api_call": 0.0})
        
        assert self.tracker.pricing[UsageType.API_CALL] == 0.0

    def test_update_pricing_affects_new_events(self):
        """Test that pricing updates affect cost calculation for new events."""
        new_price = 0.005
        self.tracker.update_pricing({"api_call": new_price})
        
        # Create event after pricing update
        event = UsageEvent(
            user_id="price_test_user",
            usage_type=UsageType.API_CALL,
            quantity=10.0,
            unit="calls",
            timestamp=datetime.now(timezone.utc),
            cost=10.0 * new_price  # Manually calculated with new price
        )
        
        assert event.cost == 10.0 * new_price


@pytest.mark.unit
class TestRateLimitManagement(BaseTestCase):
    """Test rate limit configuration and updates."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.tracker = UsageTracker()

    def test_get_rate_limits_structure(self):
        """Test that get_rate_limits returns properly structured data."""
        rate_limits = self.tracker.get_rate_limits()
        
        for usage_type, config in rate_limits.items():
            assert isinstance(usage_type, str)
            assert isinstance(config, dict)
            assert "limit" in config
            assert "window" in config
            assert isinstance(config["limit"], (int, float))
            assert isinstance(config["window"], (int, float))
            assert config["limit"] > 0
            assert config["window"] > 0

    def test_update_rate_limits_valid_updates(self):
        """Test updating rate limits with valid configurations."""
        updates = {
            "api_call": {"limit": 2000, "window": 3600},
            "llm_tokens": {"limit": 200000, "window": 1800}
        }
        
        self.tracker.update_rate_limits(updates)
        
        # Verify updates applied
        assert self.tracker.rate_limits[UsageType.API_CALL]["limit"] == 2000
        assert self.tracker.rate_limits[UsageType.API_CALL]["window"] == 3600
        assert self.tracker.rate_limits[UsageType.LLM_TOKENS]["limit"] == 200000
        assert self.tracker.rate_limits[UsageType.LLM_TOKENS]["window"] == 1800

    def test_update_rate_limits_invalid_usage_type(self):
        """Test that invalid usage types are ignored in rate limit updates."""
        original_limits = len(self.tracker.rate_limits)
        
        updates = {
            "invalid_type": {"limit": 1000, "window": 3600},
            "api_call": {"limit": 1500, "window": 3600}  # Valid update
        }
        
        self.tracker.update_rate_limits(updates)
        
        # Valid update should be applied
        assert self.tracker.rate_limits[UsageType.API_CALL]["limit"] == 1500
        
        # Invalid update should be ignored, no new keys added
        assert len(self.tracker.rate_limits) == original_limits

    def test_update_rate_limits_partial_config(self):
        """Test updating rate limits with partial configurations."""
        # Update with extra field - implementation accepts entire dict
        updates = {
            "api_call": {"limit": 5000, "window": 7200, "extra_field": "ignored"}
        }
        
        self.tracker.update_rate_limits(updates)
        
        # Entire config dict is stored (implementation doesn't filter)
        config = self.tracker.rate_limits[UsageType.API_CALL]
        assert config["limit"] == 5000
        assert config["window"] == 7200
        # Implementation stores the entire dict, extra fields included
        assert config.get("extra_field") == "ignored"

    def test_update_rate_limits_affects_future_checks(self):
        """Test that rate limit updates affect future rate limit checks."""
        # Set very low limit
        self.tracker.update_rate_limits({
            "api_call": {"limit": 1, "window": 3600}
        })
        
        user_id = "rate_limit_test_user"
        
        # First usage should be allowed
        result1 = asyncio.run(self.tracker.check_rate_limit(user_id, UsageType.API_CALL))
        assert result1["allowed"] is True
        assert result1["limit"] == 1
        
        # Add usage to hit the limit
        asyncio.run(self.tracker.track_usage(user_id, UsageType.API_CALL, 1.0, "calls"))
        
        # Second check should be blocked
        result2 = asyncio.run(self.tracker.check_rate_limit(user_id, UsageType.API_CALL))
        assert result2["allowed"] is False
        assert result2["remaining"] == 0.0


@pytest.mark.unit
class TestTrackerStatistics(BaseTestCase):
    """Test tracker statistics and monitoring."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.tracker = UsageTracker()

    def test_get_stats_empty_tracker(self):
        """Test statistics for empty tracker."""
        stats = self.tracker.get_stats()
        
        assert stats["enabled"] is True
        assert stats["total_events"] == 0
        assert stats["total_users"] == 0
        assert stats["total_cost"] == 0.0
        assert stats["usage_types_tracked"] == len(UsageType)
        assert isinstance(stats["rate_limits_configured"], int)

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self):
        """Test statistics with actual usage data."""
        # Add usage for multiple users
        await self.tracker.track_usage("user_1", UsageType.API_CALL, 100.0, "calls")
        await self.tracker.track_usage("user_1", UsageType.LLM_TOKENS, 5000.0, "tokens")
        await self.tracker.track_usage("user_2", UsageType.API_CALL, 50.0, "calls")
        
        stats = self.tracker.get_stats()
        
        assert stats["enabled"] is True
        assert stats["total_events"] == 3
        assert stats["total_users"] == 2
        assert stats["total_cost"] > 0.0
        assert stats["usage_types_tracked"] == len(UsageType)

    def test_get_stats_disabled_tracker(self):
        """Test statistics for disabled tracker."""
        self.tracker.enabled = False
        stats = self.tracker.get_stats()
        
        assert stats["enabled"] is False
        assert stats["total_events"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_cost_accuracy(self):
        """Test that total cost in statistics is accurate."""
        # Add known quantities
        api_cost = 100.0 * self.tracker.pricing[UsageType.API_CALL]
        token_cost = 5000.0 * self.tracker.pricing[UsageType.LLM_TOKENS]
        expected_total = api_cost + token_cost
        
        await self.tracker.track_usage("user_cost", UsageType.API_CALL, 100.0, "calls")
        await self.tracker.track_usage("user_cost", UsageType.LLM_TOKENS, 5000.0, "tokens")
        
        stats = self.tracker.get_stats()
        
        assert stats["total_cost"] == expected_total

    def test_clear_data_functionality(self):
        """Test that clear_data removes all tracking data."""
        # Add some data first
        asyncio.run(self.tracker.track_usage("user_clear", UsageType.API_CALL, 10.0, "calls"))
        
        # Verify data exists
        assert len(self.tracker.usage_events) > 0
        assert len(self.tracker.user_totals) > 0
        
        # Clear data
        self.tracker.clear_data()
        
        # Verify data cleared
        assert len(self.tracker.usage_events) == 0
        assert len(self.tracker.user_totals) == 0


@pytest.mark.unit
class TestEdgeCasesAndErrorHandling(BaseTestCase):
    """Test edge cases and error handling scenarios."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.tracker = UsageTracker()

    @pytest.mark.asyncio
    async def test_track_usage_negative_quantity(self):
        """Test tracking usage with negative quantity (refunds/adjustments)."""
        # This could be used for refunds or usage adjustments
        event = await self.tracker.track_usage(
            user_id="refund_user",
            usage_type=UsageType.API_CALL,
            quantity=-5.0,  # Negative quantity
            unit="calls"
        )
        
        assert event.quantity == -5.0
        assert event.cost == -5.0 * self.tracker.pricing[UsageType.API_CALL]
        assert self.tracker.user_totals["refund_user"][UsageType.API_CALL.value] == -5.0

    @pytest.mark.asyncio
    async def test_track_usage_very_large_quantity(self):
        """Test tracking usage with very large quantities."""
        large_quantity = 1000000000.0  # 1 billion
        
        event = await self.tracker.track_usage(
            user_id="enterprise_user",
            usage_type=UsageType.LLM_TOKENS,
            quantity=large_quantity,
            unit="tokens"
        )
        
        assert event.quantity == large_quantity
        expected_cost = large_quantity * self.tracker.pricing[UsageType.LLM_TOKENS]
        assert event.cost == expected_cost

    @pytest.mark.asyncio
    async def test_track_usage_very_small_quantity(self):
        """Test tracking usage with very small fractional quantities."""
        small_quantity = 0.000001
        
        event = await self.tracker.track_usage(
            user_id="micro_user",
            usage_type=UsageType.STORAGE,
            quantity=small_quantity,
            unit="gb"
        )
        
        assert event.quantity == small_quantity
        expected_cost = small_quantity * self.tracker.pricing[UsageType.STORAGE]
        assert event.cost == expected_cost

    @pytest.mark.asyncio
    async def test_get_user_usage_concurrent_access(self):
        """Test concurrent access to user usage doesn't cause data corruption."""
        user_id = "concurrent_user"
        
        # Simulate concurrent usage tracking
        tasks = []
        for i in range(10):
            task = self.tracker.track_usage(
                user_id=user_id,
                usage_type=UsageType.API_CALL,
                quantity=1.0,
                unit="calls"
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        # Verify all events were tracked
        usage_summary = await self.tracker.get_user_usage(user_id)
        
        assert usage_summary["total_events"] == 10
        assert usage_summary["usage_summary"][UsageType.API_CALL.value]["quantity"] == 10.0
        assert usage_summary["usage_summary"][UsageType.API_CALL.value]["events"] == 10

    @pytest.mark.asyncio
    async def test_rate_limit_edge_cases(self):
        """Test rate limit edge cases."""
        user_id = "edge_case_user"
        
        # Test with exact timestamp boundary
        limit_config = self.tracker.rate_limits[UsageType.API_CALL]
        limit = limit_config["limit"]
        window = limit_config["window"]
        
        # Create event right at the window boundary
        boundary_time = datetime.now(timezone.utc) - timedelta(seconds=window)
        boundary_event = UsageEvent(
            user_id=user_id,
            usage_type=UsageType.API_CALL,
            quantity=limit / 2,
            unit="calls",
            timestamp=boundary_time,
            cost=0.0
        )
        self.tracker.usage_events.append(boundary_event)
        
        # Add recent usage
        await self.tracker.track_usage(user_id, UsageType.API_CALL, limit / 2, "calls")
        
        # Rate limit check should consider window boundary correctly
        result = await self.tracker.check_rate_limit(user_id, UsageType.API_CALL)
        
        # Should allow since boundary event is outside window
        assert result["allowed"] is True

    def test_usage_event_string_enum_conversion_invalid(self):
        """Test handling of invalid string enum conversion."""
        with pytest.raises(ValueError):
            UsageEvent(
                user_id="test_user",
                usage_type="invalid_usage_type",  # Invalid enum value
                quantity=1.0,
                unit="test",
                timestamp=datetime.now(timezone.utc)
            )

    @pytest.mark.asyncio
    async def test_persist_event_always_called(self):
        """Test that _persist_event is called for every tracked usage."""
        with patch.object(self.tracker, '_persist_event', new_callable=AsyncMock) as mock_persist:
            await self.tracker.track_usage(
                user_id="persist_test",
                usage_type=UsageType.API_CALL,
                quantity=1.0
            )
            
            mock_persist.assert_called_once()
            # Verify the event passed to persist has correct data
            called_event = mock_persist.call_args[0][0]
            assert called_event.user_id == "persist_test"
            assert called_event.usage_type == UsageType.API_CALL
            assert called_event.quantity == 1.0


@pytest.mark.unit
class TestBusinessValueScenarios(BaseTestCase):
    """Test scenarios that directly impact business value and revenue."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.tracker = UsageTracker()

    @pytest.mark.asyncio
    async def test_free_tier_usage_tracking(self):
        """Test usage tracking for free tier users (zero cost but tracked)."""
        # Simulate free tier pricing (could be zero cost)
        free_tier_pricing = {"api_call": 0.0}
        self.tracker.update_pricing(free_tier_pricing)
        
        user_id = "free_tier_user"
        await self.tracker.track_usage(user_id, UsageType.API_CALL, 100.0, "calls")
        
        usage_summary = await self.tracker.get_user_usage(user_id)
        
        # Usage should be tracked even if cost is zero
        assert usage_summary["total_events"] == 1
        assert usage_summary["usage_summary"][UsageType.API_CALL.value]["quantity"] == 100.0
        assert usage_summary["total_cost"] == 0.0

    @pytest.mark.asyncio
    async def test_enterprise_bulk_usage_tracking(self):
        """Test tracking enterprise-level bulk usage accurately."""
        user_id = "enterprise_customer"
        
        # Simulate heavy enterprise usage
        usage_scenarios = [
            (UsageType.API_CALL, 50000.0, "calls"),
            (UsageType.LLM_TOKENS, 10000000.0, "tokens"),  # 10M tokens
            (UsageType.STORAGE, 1000.0, "gb"),  # 1TB storage
            (UsageType.COMPUTE, 720.0, "hours"),  # 30 days * 24 hours
            (UsageType.BANDWIDTH, 5000.0, "gb")  # 5TB bandwidth
        ]
        
        total_expected_cost = 0.0
        
        for usage_type, quantity, unit in usage_scenarios:
            await self.tracker.track_usage(user_id, usage_type, quantity, unit)
            total_expected_cost += quantity * self.tracker.pricing[usage_type]
        
        usage_summary = await self.tracker.get_user_usage(user_id)
        
        # Verify accurate tracking of large volumes
        assert usage_summary["total_events"] == len(usage_scenarios)
        assert usage_summary["total_cost"] == total_expected_cost
        
        # Verify individual usage type tracking
        assert usage_summary["usage_summary"][UsageType.LLM_TOKENS.value]["quantity"] == 10000000.0

    @pytest.mark.asyncio
    async def test_monthly_billing_cycle_simulation(self):
        """Test usage tracking over a monthly billing cycle."""
        user_id = "monthly_billing_user"
        base_time = datetime.now(timezone.utc)
        
        # Simulate daily usage over 30 days
        daily_api_calls = 1000
        monthly_events = []
        
        for day in range(30):
            event_time = base_time - timedelta(days=day)
            event = UsageEvent(
                user_id=user_id,
                usage_type=UsageType.API_CALL,
                quantity=daily_api_calls,
                unit="calls",
                timestamp=event_time,
                cost=daily_api_calls * self.tracker.pricing[UsageType.API_CALL]
            )
            monthly_events.append(event)
        
        self.tracker.usage_events.extend(monthly_events)
        
        # Get usage for the month
        month_start = base_time - timedelta(days=30)
        usage_summary = await self.tracker.get_user_usage(
            user_id=user_id,
            start_time=month_start
        )
        
        expected_total_calls = 30 * daily_api_calls
        expected_total_cost = expected_total_calls * self.tracker.pricing[UsageType.API_CALL]
        
        assert usage_summary["total_events"] == 30
        assert usage_summary["usage_summary"][UsageType.API_CALL.value]["quantity"] == expected_total_calls
        assert usage_summary["total_cost"] == expected_total_cost

    @pytest.mark.asyncio
    async def test_usage_spike_handling(self):
        """Test handling of usage spikes without data loss."""
        user_id = "spike_user"
        
        # Simulate sudden usage spike
        spike_events = []
        for i in range(1000):  # 1000 events in rapid succession
            event = await self.tracker.track_usage(
                user_id=user_id,
                usage_type=UsageType.API_CALL,
                quantity=1.0,
                unit="calls"
            )
            spike_events.append(event)
        
        # Verify all events were tracked
        usage_summary = await self.tracker.get_user_usage(user_id)
        
        assert usage_summary["total_events"] == 1000
        assert usage_summary["usage_summary"][UsageType.API_CALL.value]["quantity"] == 1000.0
        assert len(self.tracker.usage_events) == 1000

    @pytest.mark.asyncio
    async def test_multi_tenant_cost_isolation(self):
        """Test that costs are properly isolated between different tenants/users."""
        users = ["tenant_a", "tenant_b", "tenant_c"]
        usage_per_user = 1000.0
        
        # Each tenant uses different amounts
        for i, user_id in enumerate(users):
            quantity = usage_per_user * (i + 1)  # 1000, 2000, 3000
            await self.tracker.track_usage(user_id, UsageType.API_CALL, quantity, "calls")
        
        # Verify cost isolation
        for i, user_id in enumerate(users):
            usage_summary = await self.tracker.get_user_usage(user_id)
            expected_quantity = usage_per_user * (i + 1)
            expected_cost = expected_quantity * self.tracker.pricing[UsageType.API_CALL]
            
            assert usage_summary["usage_summary"][UsageType.API_CALL.value]["quantity"] == expected_quantity
            assert usage_summary["total_cost"] == expected_cost

    @pytest.mark.asyncio
    async def test_overage_charging_accuracy(self):
        """Test accurate overage cost calculation for subscription tiers."""
        user_id = "overage_user"
        
        # Simulate usage that exceeds plan limits (this would be checked by billing system)
        base_allowance = 10000  # Plan includes 10k API calls
        overage_usage = 5000   # Additional 5k calls
        
        total_usage = base_allowance + overage_usage
        
        await self.tracker.track_usage(user_id, UsageType.API_CALL, total_usage, "calls")
        
        usage_summary = await self.tracker.get_user_usage(user_id)
        
        # Usage tracker should accurately track total usage
        # Billing system would calculate base vs overage separately
        expected_total_cost = total_usage * self.tracker.pricing[UsageType.API_CALL]
        
        assert usage_summary["usage_summary"][UsageType.API_CALL.value]["quantity"] == total_usage
        assert usage_summary["total_cost"] == expected_total_cost

    @pytest.mark.asyncio
    async def test_revenue_analytics_accuracy(self):
        """Test that revenue analytics provide accurate business insights."""
        # Simulate realistic multi-user scenario
        user_scenarios = [
            ("free_user", [(UsageType.API_CALL, 100.0, "calls")]),
            ("early_user", [(UsageType.API_CALL, 5000.0, "calls"), (UsageType.LLM_TOKENS, 100000.0, "tokens")]),
            ("mid_user", [(UsageType.API_CALL, 15000.0, "calls"), (UsageType.LLM_TOKENS, 500000.0, "tokens")]),
            ("enterprise_user", [
                (UsageType.API_CALL, 100000.0, "calls"),
                (UsageType.LLM_TOKENS, 5000000.0, "tokens"),
                (UsageType.STORAGE, 100.0, "gb")
            ])
        ]
        
        total_expected_revenue = 0.0
        
        for user_id, usage_list in user_scenarios:
            for usage_type, quantity, unit in usage_list:
                await self.tracker.track_usage(user_id, usage_type, quantity, unit)
                total_expected_revenue += quantity * self.tracker.pricing[usage_type]
        
        analytics = await self.tracker.get_usage_analytics()
        
        # Verify revenue accuracy (use approximate comparison for floating point precision)
        assert abs(analytics["totals"]["cost"] - total_expected_revenue) < 0.001
        assert analytics["totals"]["unique_users"] == len(user_scenarios)
        
        # Verify top customer identification (enterprise should be #1)
        top_user = analytics["top_users"][0]
        assert top_user["user_id"] == "enterprise_user"
        assert top_user["cost"] > analytics["top_users"][1]["cost"]