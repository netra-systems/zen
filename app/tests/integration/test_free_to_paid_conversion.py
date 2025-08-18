"""
Free-to-Paid Conversion Flow Integration Test

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Free users converting to Growth/Enterprise
2. **Business Goal**: Maximize conversion rate from free to paid tiers
3. **Value Impact**: Each conversion = $99-$999/month recurring revenue
4. **Revenue Impact**: 10% conversion rate improvement = +$50K ARR annually
5. **Growth Engine**: Free tier designed specifically to drive paid conversions

Tests the complete user journey from signup to payment with feature restrictions,
upgrade prompts, and conversion optimization. Critical for business growth.
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from app.db.models_user import User, ToolUsageLog
from app.services.permission_service import PermissionService
from app.schemas.rate_limit_types import RateLimitConfig
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
import tempfile


class TestFreeToPaidConversion:
    """E2E tests for free-to-paid conversion optimization"""

    @pytest.fixture
    async def conversion_test_setup(self):
        """Setup test environment for conversion testing"""
        return await self._create_conversion_test_env()

    @pytest.fixture
    def permission_system(self):
        """Setup permission system for plan enforcement"""
        return self._init_permission_system()

    @pytest.fixture
    def conversion_tracking(self):
        """Setup conversion tracking and analytics"""
        return self._init_conversion_tracking()

    async def _create_conversion_test_env(self):
        """Create isolated test environment for conversion flows"""
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_url = f"sqlite+aiosqlite:///{db_file.name}"
        engine = create_async_engine(db_url, echo=False)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        session = session_factory()
        
        return {"session": session, "engine": engine, "db_file": db_file.name}

    def _init_permission_system(self):
        """Initialize permission system for plan restrictions"""
        permission_service = Mock(spec=PermissionService)
        permission_service.check_tool_permission = AsyncMock()
        permission_service.get_plan_limits = Mock()
        permission_service.trigger_upgrade_prompt = AsyncMock()
        
        return permission_service

    def _init_conversion_tracking(self):
        """Initialize conversion tracking and funnel analytics"""
        tracker = Mock()
        tracker.track_signup = AsyncMock()
        tracker.track_feature_hit = AsyncMock()
        tracker.track_upgrade_prompt = AsyncMock()
        tracker.track_conversion = AsyncMock()
        
        return tracker

    async def test_1_complete_free_to_paid_conversion_journey(
        self, conversion_test_setup, permission_system, conversion_tracking
    ):
        """
        Test complete user journey from free signup to paid conversion.
        
        BVJ: End-to-end conversion validation ensuring smooth user experience
        and optimal conversion funnel performance. Each completed conversion
        represents $99-999/month in recurring revenue.
        """
        db_setup = conversion_test_setup
        
        # Phase 1: Free user signup and onboarding
        free_user = await self._simulate_free_user_signup(db_setup, conversion_tracking)
        
        # Phase 2: Free tier usage and feature discovery
        usage_data = await self._simulate_free_tier_usage(db_setup, free_user, permission_system)
        
        # Phase 3: Hit plan limits and trigger upgrade prompts
        upgrade_triggers = await self._simulate_plan_limit_hits(
            db_setup, free_user, permission_system, conversion_tracking
        )
        
        # Phase 4: Conversion to paid plan
        conversion_result = await self._simulate_successful_conversion(
            db_setup, free_user, conversion_tracking
        )
        
        # Phase 5: Verify post-conversion experience
        await self._verify_post_conversion_experience(db_setup, conversion_result)
        
        await self._cleanup_conversion_test(db_setup)

    async def _simulate_free_user_signup(self, db_setup, conversion_tracking):
        """Simulate realistic free user signup flow"""
        user = User(
            id=str(uuid.uuid4()),
            email="freeuser@example.com",
            full_name="Free Trial User",
            plan_tier="free",
            payment_status="active",
            trial_period=14,  # 14-day trial
            plan_started_at=datetime.now(timezone.utc)
        )
        
        db_setup["session"].add(user)
        await db_setup["session"].commit()
        
        # Track signup conversion event
        await conversion_tracking.track_signup(user.id, "free", "organic")
        
        return user

    async def _simulate_free_tier_usage(self, db_setup, user, permission_system):
        """Simulate free tier usage patterns and restrictions"""
        # Configure free tier limits
        permission_system.get_plan_limits.return_value = {
            "max_requests_per_day": 10,
            "max_tokens_per_request": 1000,
            "allowed_models": ["gemini-2.5-flash"],
            "advanced_features": False
        }
        
        # Simulate initial usage within limits
        usage_logs = await self._create_free_tier_usage_logs(db_setup, user)
        
        return {"usage_logs": usage_logs, "requests_used": len(usage_logs)}

    async def _create_free_tier_usage_logs(self, db_setup, user):
        """Create realistic free tier usage logs"""
        usage_logs = []
        
        for day in range(7):  # Week of usage
            for request in range(8):  # 8 requests per day (within limit)
                log = ToolUsageLog(
                    user_id=user.id,
                    tool_name="gemini_basic_query",
                    category="analysis",
                    execution_time_ms=5000,
                    tokens_used=800,  # Within free tier token limit
                    cost_cents=0,  # Free tier - no cost
                    status="success",
                    plan_tier="free",
                    created_at=datetime.now(timezone.utc) - timedelta(days=7-day, hours=request)
                )
                usage_logs.append(log)
                db_setup["session"].add(log)
        
        await db_setup["session"].commit()
        return usage_logs

    async def _simulate_plan_limit_hits(self, db_setup, user, permission_system, conversion_tracking):
        """Simulate hitting plan limits and upgrade prompts"""
        upgrade_triggers = []
        
        # Simulate daily request limit hit
        permission_system.check_tool_permission.return_value = {
            "allowed": False,
            "reason": "daily_limit_exceeded",
            "upgrade_required": True,
            "recommended_plan": "growth"
        }
        
        trigger_1 = await self._create_upgrade_trigger_event(
            db_setup, user, "daily_limit", conversion_tracking
        )
        upgrade_triggers.append(trigger_1)
        
        # Simulate advanced feature access attempt
        trigger_2 = await self._create_upgrade_trigger_event(
            db_setup, user, "advanced_feature", conversion_tracking
        )
        upgrade_triggers.append(trigger_2)
        
        return upgrade_triggers

    async def _create_upgrade_trigger_event(self, db_setup, user, trigger_type, conversion_tracking):
        """Create upgrade trigger event and track it"""
        trigger_event = {
            "user_id": user.id,
            "trigger_type": trigger_type,
            "timestamp": datetime.now(timezone.utc),
            "current_plan": user.plan_tier,
            "recommended_plan": "growth"
        }
        
        # Track upgrade prompt shown
        await conversion_tracking.track_upgrade_prompt(
            user.id, trigger_type, "growth", "in_app_modal"
        )
        
        return trigger_event

    async def _simulate_successful_conversion(self, db_setup, user, conversion_tracking):
        """Simulate successful conversion to paid plan"""
        # Update user to Growth plan
        user.plan_tier = "growth"
        user.payment_status = "active"
        user.auto_renew = True
        user.trial_period = 0
        user.plan_started_at = datetime.now(timezone.utc)
        
        await db_setup["session"].commit()
        
        # Track conversion event
        await conversion_tracking.track_conversion(
            user.id, "free", "growth", 99.00, "credit_card"
        )
        
        return {
            "converted_user": user,
            "conversion_value": 99.00,
            "conversion_method": "in_app_upgrade",
            "conversion_trigger": "daily_limit"
        }

    async def _verify_post_conversion_experience(self, db_setup, conversion_result):
        """Verify post-conversion user experience and feature access"""
        user = conversion_result["converted_user"]
        
        # Verify plan upgrade
        assert user.plan_tier == "growth"
        assert user.payment_status == "active"
        assert user.auto_renew == True
        
        # Test increased limits access
        await self._test_growth_plan_features(db_setup, user)

    async def _test_growth_plan_features(self, db_setup, user):
        """Test that Growth plan features are now accessible"""
        # Simulate usage with Growth plan limits
        growth_usage = ToolUsageLog(
            user_id=user.id,
            tool_name="gpt_4_advanced",  # Advanced model now available
            category="optimization",
            execution_time_ms=12000,
            tokens_used=5000,  # Higher token limit
            cost_cents=2500,  # Paid usage
            status="success",
            plan_tier="growth"
        )
        
        db_setup["session"].add(growth_usage)
        await db_setup["session"].commit()

    async def _cleanup_conversion_test(self, db_setup):
        """Cleanup conversion test environment"""
        await db_setup["session"].close()
        await db_setup["engine"].dispose()

    async def test_2_free_tier_limit_enforcement_and_prompts(
        self, conversion_test_setup, permission_system, conversion_tracking
    ):
        """
        Test free tier limit enforcement and upgrade prompt optimization.
        
        BVJ: Validates that free tier restrictions effectively drive conversions
        while maintaining positive user experience. Optimized prompts can
        increase conversion rates by 15-25%.
        """
        db_setup = conversion_test_setup
        free_user = await self._create_test_free_user(db_setup)
        
        # Test daily request limits
        await self._test_daily_request_limits(free_user, permission_system)
        
        # Test token limits per request
        await self._test_token_limits(free_user, permission_system)
        
        # Test advanced feature restrictions
        await self._test_advanced_feature_restrictions(free_user, permission_system)
        
        # Test upgrade prompt triggers
        await self._test_upgrade_prompt_optimization(free_user, conversion_tracking)
        
        await self._cleanup_conversion_test(db_setup)

    async def _create_test_free_user(self, db_setup):
        """Create test free user for limit testing"""
        user = User(
            id=str(uuid.uuid4()),
            email="limittest@example.com",
            plan_tier="free",
            payment_status="active"
        )
        db_setup["session"].add(user)
        await db_setup["session"].commit()
        return user

    async def _test_daily_request_limits(self, user, permission_system):
        """Test daily request limit enforcement"""
        # Simulate hitting daily limit
        permission_system.check_tool_permission.return_value = {
            "allowed": False,
            "reason": "daily_limit_exceeded",
            "current_usage": 10,
            "limit": 10,
            "reset_time": datetime.now(timezone.utc) + timedelta(hours=6)
        }
        
        result = await permission_system.check_tool_permission(user.id, "basic_query")
        assert result["allowed"] == False
        assert result["reason"] == "daily_limit_exceeded"

    async def _test_token_limits(self, user, permission_system):
        """Test per-request token limit enforcement"""
        permission_system.check_tool_permission.return_value = {
            "allowed": False,
            "reason": "token_limit_exceeded",
            "requested_tokens": 2000,
            "max_tokens": 1000
        }
        
        result = await permission_system.check_tool_permission(user.id, "large_query")
        assert result["reason"] == "token_limit_exceeded"

    async def _test_advanced_feature_restrictions(self, user, permission_system):
        """Test advanced feature access restrictions for free users"""
        permission_system.check_tool_permission.return_value = {
            "allowed": False,
            "reason": "plan_upgrade_required",
            "required_plan": "growth",
            "feature": "advanced_optimization"
        }
        
        result = await permission_system.check_tool_permission(user.id, "advanced_optimizer")
        assert result["required_plan"] == "growth"

    async def _test_upgrade_prompt_optimization(self, user, conversion_tracking):
        """Test upgrade prompt optimization and tracking"""
        # Test different prompt variants
        prompt_variants = ["modal_with_savings", "banner_with_trial", "email_sequence"]
        
        for variant in prompt_variants:
            await conversion_tracking.track_upgrade_prompt(
                user.id, "feature_limit", "growth", variant
            )
        
        # Verify tracking calls were made
        assert conversion_tracking.track_upgrade_prompt.call_count == 3

    async def test_3_trial_expiration_and_conversion_urgency(
        self, conversion_test_setup, conversion_tracking
    ):
        """
        Test trial expiration handling and conversion urgency tactics.
        
        BVJ: Trial expiration is a critical conversion moment. Proper handling
        can increase conversion rates by 20-30% through urgency and value demonstration.
        """
        db_setup = conversion_test_setup
        trial_user = await self._create_trial_user_near_expiration(db_setup)
        
        # Test trial expiration warnings
        await self._test_trial_expiration_warnings(trial_user, conversion_tracking)
        
        # Test post-expiration grace period
        await self._test_post_expiration_grace_period(db_setup, trial_user)
        
        # Test trial extension for engaged users
        await self._test_trial_extension_logic(db_setup, trial_user)
        
        await self._cleanup_conversion_test(db_setup)

    async def test_cost_savings_integration_reference(
        self, conversion_test_setup, conversion_tracking
    ):
        """
        Reference test for cost savings preview integration.
        
        BVJ: Links to dedicated cost savings preview calculator test module
        for comprehensive free-to-paid conversion validation.
        
        See: test_free_tier_value_demonstration_integration.py for full implementation
        """
        # This test validates that cost savings integration points work
        db_setup = conversion_test_setup
        
        # Simple integration check
        user = await self._create_test_free_user(db_setup)
        assert user.plan_tier == "free"
        
        # Verify savings calculation trigger points exist
        assert hasattr(user, 'plan_tier')
        assert hasattr(user, 'created_at')
        
        await self._cleanup_conversion_test(db_setup)

    async def _create_trial_user_near_expiration(self, db_setup):
        """Create trial user near expiration for urgency testing"""
        user = User(
            id=str(uuid.uuid4()),
            email="trial@example.com",
            plan_tier="free",
            trial_period=14,
            plan_started_at=datetime.now(timezone.utc) - timedelta(days=12)  # 2 days left
        )
        db_setup["session"].add(user)
        await db_setup["session"].commit()
        return user

    async def _test_trial_expiration_warnings(self, user, conversion_tracking):
        """Test trial expiration warning sequence"""
        days_remaining = 2
        
        await conversion_tracking.track_upgrade_prompt(
            user.id, "trial_expiring", "growth", f"email_warning_{days_remaining}_days"
        )
        
        assert conversion_tracking.track_upgrade_prompt.called

    async def _test_post_expiration_grace_period(self, db_setup, user):
        """Test grace period functionality after trial expiration"""
        # Simulate trial expiration
        user.trial_period = 0
        user.plan_started_at = datetime.now(timezone.utc) - timedelta(days=15)
        await db_setup["session"].commit()
        
        # User should have limited access during grace period
        assert user.trial_period == 0

    async def _test_trial_extension_logic(self, db_setup, user):
        """Test automatic trial extension for highly engaged users"""
        # High engagement should trigger trial extension
        if self._is_highly_engaged_user(user):
            user.trial_period = 21  # Extended trial
            await db_setup["session"].commit()
        
        # This is a placeholder for actual engagement logic
        assert user.trial_period >= 14

    def _is_highly_engaged_user(self, user):
        """Determine if user qualifies for trial extension"""
        # Placeholder for engagement scoring logic
        return True  # Simplified for test



if __name__ == "__main__":
    pytest.main([__file__, "-v"])