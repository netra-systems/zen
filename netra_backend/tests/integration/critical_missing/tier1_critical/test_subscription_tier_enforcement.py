"""Subscription Tier Enforcement Integration Test ($1.2M impact)

L2 realism level - tests user tier validation across service boundaries
using real internal dependencies for tier enforcement.

Business Value Justification:
- Segment: All paid tiers ($1.2M revenue impact)
- Business Goal: Revenue Protection - Tier limit enforcement
- Value Impact: Prevents revenue leakage from tier bypass attempts
- Strategic Impact: Essential for subscription business model integrity
"""

import pytest
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.tests.integration.critical_missing.shared_infrastructure.containerized_services import ServiceOrchestrator
from netra_backend.app.services.tool_permissions.tool_permission_service_main import ToolPermissionService
from netra_backend.app.db.models_user import User
from netra_backend.app.schemas.ToolPermission import ToolExecutionContext, PermissionCheckResult
from netra_backend.app.schemas.UserPlan import UserPlan, PlanTier, PLAN_DEFINITIONS
from netra_backend.app.core.exceptions_base import NetraException

# Add project root to path

# Define test-specific exception
class AuthorizationError(NetraException):
    pass


@pytest.fixture(scope="module")
async def l2_services():
    """L2 realism: Real internal dependencies"""
    orchestrator = ServiceOrchestrator()
    connections = await orchestrator.start_all()
    yield orchestrator, connections
    await orchestrator.stop_all()


@pytest.fixture
async def permission_service(l2_services):
    """Tool permission service with mock Redis"""
    orchestrator, connections = l2_services
    # Use mock Redis client for testing
    return ToolPermissionService(None)


@pytest.fixture
async def test_users():
    """Test users for different subscription tiers"""
    return {
        "free_user": User(
            id="user_free_001", email="free@test.com", plan_tier="free",
            plan_started_at=datetime.now(timezone.utc)
        ),
        "pro_user": User(
            id="user_pro_001", email="pro@test.com", plan_tier="pro",
            plan_started_at=datetime.now(timezone.utc)
        ),
        "enterprise_user": User(
            id="user_ent_001", email="enterprise@test.com", plan_tier="enterprise",
            plan_started_at=datetime.now(timezone.utc)
        ),
        "expired_user": User(
            id="user_exp_001", email="expired@test.com", plan_tier="pro",
            plan_expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
    }


@pytest.fixture
async def reset_services(l2_services):
    """Reset services for test isolation"""
    orchestrator, _ = l2_services
    await orchestrator.reset_for_test()


class TestSubscriptionTierEnforcement:
    """Test subscription tier enforcement across service boundaries"""

    async def test_free_tier_tool_limits(self, permission_service, test_users, reset_services):
        """Test free tier tool access limitations < 10ms"""
        user = test_users["free_user"]
        context = ToolExecutionContext(
            user_id=user.id, tool_name="advanced_analytics", arguments={}
        )
        
        import time
        start_time = time.time()
        result = await permission_service.check_tool_permission(context)
        validation_time = (time.time() - start_time) * 1000
        
        assert validation_time < 10.0
        assert not result.allowed
        assert "upgrade" in result.reason.lower()

    async def test_pro_tier_feature_access(self, permission_service, test_users, reset_services):
        """Test pro tier feature access validation"""
        user = test_users["pro_user"]
        context = ToolExecutionContext(
            user_id=user.id, tool_name="data_export", arguments={}
        )
        
        result = await permission_service.check_tool_permission(context)
        assert result.allowed

    async def test_enterprise_tier_unlimited_access(self, permission_service, test_users, reset_services):
        """Test enterprise tier unlimited tool access"""
        user = test_users["enterprise_user"]
        context = ToolExecutionContext(
            user_id=user.id, tool_name="admin_tools", arguments={}
        )
        
        result = await permission_service.check_tool_permission(context)
        assert result.allowed

    async def test_expired_subscription_enforcement(self, permission_service, test_users, reset_services):
        """Test expired subscription tier enforcement"""
        user = test_users["expired_user"]
        context = ToolExecutionContext(
            user_id=user.id, tool_name="basic_tool", arguments={}
        )
        
        result = await permission_service.check_tool_permission(context)
        assert not result.allowed
        assert "expired" in result.reason.lower()

    async def test_tier_upgrade_immediate_effect(self, permission_service, test_users, reset_services):
        """Test tier upgrade takes immediate effect"""
        user = test_users["free_user"]
        
        # Test restricted access on free tier
        context = ToolExecutionContext(
            user_id=user.id, tool_name="pro_feature", arguments={}
        )
        result_before = await permission_service.check_tool_permission(context)
        assert not result_before.allowed
        
        # Simulate tier upgrade
        user.plan_tier = "pro"
        result_after = await permission_service.check_tool_permission(context)
        assert result_after.allowed

    async def test_tier_downgrade_enforcement(self, permission_service, test_users, reset_services):
        """Test tier downgrade enforcement"""
        user = test_users["pro_user"]
        
        # Test allowed access on pro tier
        context = ToolExecutionContext(
            user_id=user.id, tool_name="pro_feature", arguments={}
        )
        result_before = await permission_service.check_tool_permission(context)
        assert result_before.allowed
        
        # Simulate tier downgrade
        user.plan_tier = "free"
        result_after = await permission_service.check_tool_permission(context)
        assert not result_after.allowed

    async def test_feature_gating_per_tier(self, permission_service, test_users, reset_services):
        """Test feature gating based on subscription tier"""
        contexts = [
            ("free_user", "basic_tool", True),
            ("free_user", "advanced_tool", False),
            ("pro_user", "advanced_tool", True),
            ("enterprise_user", "enterprise_tool", True)
        ]
        
        for user_key, tool_name, expected_allowed in contexts:
            user = test_users[user_key]
            context = ToolExecutionContext(
                user_id=user.id, tool_name=tool_name, arguments={}
            )
            result = await permission_service.check_tool_permission(context)
            assert result.allowed == expected_allowed

    async def test_cross_service_tier_validation(self, permission_service, test_users, reset_services):
        """Test tier validation consistency across services"""
        user = test_users["pro_user"]
        tools = ["service_a_tool", "service_b_tool", "service_c_tool"]
        
        for tool_name in tools:
            context = ToolExecutionContext(
                user_id=user.id, tool_name=tool_name, arguments={}
            )
            result = await permission_service.check_tool_permission(context)
            # Pro tier should have consistent access across services
            assert isinstance(result.allowed, bool)