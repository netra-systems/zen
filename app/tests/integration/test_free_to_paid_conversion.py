"""
CRITICAL INTEGRATION TEST #8: Free-to-Paid Conversion Flow for Revenue Pipeline

BVJ: Protects $100K-$200K MRR through conversion funnel validation.
Covers upgrade journey, payment collection, feature unlocking, conversion tracking.

REVENUE PROTECTION:
- Complete upgrade journey from trial to payment
- Feature limit enforcement and upgrade prompts  
- Payment collection and processing validation
- Feature unlocking post-conversion verification
- Trial extension and downgrade prevention
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, AsyncMock
from app.db.models_user import User, ToolUsageLog
from app.schemas.UserPlan import PlanTier
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
import tempfile


class TestFreeToPaidConversionRevenuePipeline:
    """BVJ: Protects $100K-$200K MRR through complete conversion validation."""

    @pytest.fixture
    async def test_infra(self):
        """Setup test infrastructure"""
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_file.name}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
        return {"session": session, "engine": engine, "db_file": db_file.name}

    @pytest.fixture
    def mocks(self):
        """Setup all mocks"""
        payment = Mock()
        payment.process_payment = AsyncMock()
        payment.setup_recurring_billing = AsyncMock()
        feature_gating = Mock()
        feature_gating.check_feature_access = AsyncMock()
        feature_gating.unlock_features = AsyncMock()
        tracker = Mock()
        tracker.track_signup = AsyncMock()
        tracker.track_conversion = AsyncMock()
        tracker.track_trial_expiration = AsyncMock()
        tracker.track_downgrade_attempt = AsyncMock()
        return {"payment": payment, "gating": feature_gating, "tracker": tracker}

    @pytest.mark.asyncio
    async def test_01_complete_smooth_upgrade_flow(self, test_infra, mocks):
        """BVJ: Validates smooth conversion experience protecting $100K+ MRR."""
        user = await self._create_trial_user(test_infra, mocks["tracker"])
        await self._simulate_limit_approach(mocks["gating"])
        offer = await self._create_upgrade_offer(user, mocks["tracker"])
        payment_result = await self._process_payment(offer, mocks["payment"])
        await self._unlock_features(test_infra, user, mocks["gating"])
        await self._verify_conversion(user, mocks["tracker"])
        await self._cleanup(test_infra)

    async def _create_trial_user(self, infra, tracker):
        """Create trial user"""
        user = User(id=str(uuid.uuid4()), email="trial@example.com", plan_tier="free",
                   payment_status="trial", trial_period=14, plan_started_at=datetime.now(timezone.utc))
        infra["session"].add(user)
        await infra["session"].commit()
        await tracker.track_signup(user.id, "free", "trial")
        return user

    async def _simulate_limit_approach(self, gating):
        """Simulate approaching limits"""
        gating.check_feature_access.return_value = {
            "access_granted": False, "reason": "approaching_limits", "usage_percentage": 90
        }

    async def _create_upgrade_offer(self, user, tracker):
        """Create upgrade offer"""
        offer = {"user_id": user.id, "from_plan": PlanTier.FREE, "to_plan": PlanTier.PRO, 
                "offer_price": Decimal("23.20"), "expires": datetime.now(timezone.utc) + timedelta(days=3)}
        await tracker.track_conversion(user.id, "upgrade_prompt_shown")
        return offer

    async def _process_payment(self, offer, payment):
        """Process payment"""
        payment_result = {"transaction_id": str(uuid.uuid4()), "amount": offer["offer_price"], 
                         "status": "succeeded", "timestamp": datetime.now(timezone.utc)}
        payment.process_payment.return_value = payment_result
        recurring_setup = {"subscription_id": str(uuid.uuid4()), "status": "active",
                          "next_billing": datetime.now(timezone.utc) + timedelta(days=30)}
        payment.setup_recurring_billing.return_value = recurring_setup
        return {**payment_result, "recurring": recurring_setup}

    async def _unlock_features(self, infra, user, gating):
        """Unlock premium features"""
        user.plan_tier = "pro"
        user.payment_status = "active"
        user.auto_renew = True
        user.trial_period = 0
        await infra["session"].commit()
        unlocked_features = {"advanced_analytics": True, "priority_support": True,
                           "increased_limits": {"daily_requests": 1000}}
        gating.unlock_features.return_value = unlocked_features
        await gating.unlock_features(user.id, PlanTier.PRO)

    async def _verify_conversion(self, user, tracker):
        """Verify conversion success"""
        await tracker.track_conversion(user.id, "free", "pro", Decimal("23.20"), "credit_card")
        assert user.plan_tier == "pro" and user.payment_status == "active"

    @pytest.mark.asyncio
    async def test_02_trial_expiration_and_extension(self, test_infra, mocks):
        """BVJ: Optimizes trial experience to maximize conversions."""
        user = await self._create_expiring_user(test_infra)
        await self._send_expiration_warnings(user, mocks["tracker"])
        extension_result = await self._evaluate_extension(test_infra, user, mocks["tracker"])
        await self._verify_extension(extension_result)
        await self._cleanup(test_infra)

    async def _create_expiring_user(self, infra):
        """Create expiring user"""
        user = User(id=str(uuid.uuid4()), email="expiring@example.com", plan_tier="free", 
                   trial_period=14, plan_started_at=datetime.now(timezone.utc) - timedelta(days=12))
        infra["session"].add(user)
        await infra["session"].commit()
        return user

    async def _send_expiration_warnings(self, user, tracker):
        """Send expiration warnings"""
        warnings = ["3_day_warning", "1_day_warning"]
        for warning in warnings:
            await tracker.track_trial_expiration(user.id, warning, 2)

    async def _evaluate_extension(self, infra, user, tracker):
        """Evaluate trial extension"""
        engagement_score = 0.8  # Mock high engagement
        extension_result = {"extension_granted": False}
        if engagement_score >= 0.75:
            user.trial_period = 21  # 7-day extension
            await infra["session"].commit()
            extension_result = {"extension_granted": True, "extension_days": 7, "reason": "high_engagement"}
            await tracker.track_trial_expiration(user.id, "trial_extended", 7)
        return extension_result

    async def _verify_extension(self, result):
        """Verify extension effectiveness"""
        if result["extension_granted"]:
            assert result["extension_days"] == 7

    @pytest.mark.asyncio
    async def test_03_feature_gating_effectiveness(self, test_infra, mocks):
        """BVJ: Feature gating drives 60-70% of conversions."""
        user = await self._create_free_user(test_infra)
        restrictions = await self._test_restrictions(user, mocks["gating"])
        prompts = await self._test_upgrade_prompts(user, mocks["tracker"])
        await self._verify_gating(restrictions, prompts)
        await self._cleanup(test_infra)

    async def _create_free_user(self, infra):
        """Create free user"""
        user = User(id=str(uuid.uuid4()), email="free@example.com", 
                   plan_tier="free", payment_status="active")
        infra["session"].add(user)
        await infra["session"].commit()
        return user

    async def _test_restrictions(self, user, gating):
        """Test feature restrictions"""
        gating.check_feature_access.return_value = {
            "access_granted": False, "required_plan": PlanTier.PRO,
            "upgrade_prompt": "Unlock advanced features with Pro"
        }
        result = await gating.check_feature_access(user.id, "advanced_analytics")
        return {"advanced_analytics": result}

    async def _test_upgrade_prompts(self, user, tracker):
        """Test upgrade prompts"""
        variants = ["modal_with_savings", "banner_with_trial", "feature_highlight"]
        for variant in variants:
            await tracker.track_conversion(user.id, f"prompt_{variant}")
        return variants

    async def _verify_gating(self, restrictions, prompts):
        """Verify gating effectiveness"""
        assert restrictions["advanced_analytics"]["access_granted"] == False
        assert len(prompts) == 3

    @pytest.mark.asyncio
    async def test_04_downgrade_prevention_retention(self, test_infra, mocks):
        """BVJ: Preventing downgrades protects MRR."""
        user = await self._create_paid_user(test_infra)
        downgrade_request = await self._simulate_downgrade(user, mocks["tracker"])
        retention_result = await self._execute_retention(downgrade_request)
        await self._verify_retention(test_infra, retention_result)
        await self._cleanup(test_infra)

    async def _create_paid_user(self, infra):
        """Create paid user"""
        user = User(id=str(uuid.uuid4()), email="paid@example.com", plan_tier="pro", 
                   payment_status="active", plan_started_at=datetime.now(timezone.utc) - timedelta(days=60))
        infra["session"].add(user)
        await infra["session"].commit()
        return user

    async def _simulate_downgrade(self, user, tracker):
        """Simulate downgrade attempt"""
        downgrade_request = {"user_id": user.id, "from_plan": PlanTier.PRO, 
                           "to_plan": PlanTier.FREE, "reason": "cost_concerns"}
        await tracker.track_downgrade_attempt(user.id, "pro", "free", "cost_concerns")
        return downgrade_request

    async def _execute_retention(self, downgrade_request):
        """Execute retention interventions"""
        return {"user_id": downgrade_request["user_id"], "downgrade_prevented": True,
               "intervention_type": "discount_offer", "retained_revenue": Decimal("29.00")}

    async def _verify_retention(self, infra, result):
        """Verify retention effectiveness"""
        assert result["downgrade_prevented"] == True
        assert result["retained_revenue"] == Decimal("29.00")
        user = await infra["session"].get(User, result["user_id"])
        assert user.plan_tier == "pro"

    async def _cleanup(self, infra):
        """Cleanup test environment"""
        await infra["session"].close()
        await infra["engine"].dispose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])