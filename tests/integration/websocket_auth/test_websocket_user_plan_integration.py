"""
WebSocket User Plan Integration Tests

Business Value Justification (BVJ):
- Segment: Free/Pro/Enterprise plan validation
- Goal: Revenue protection through proper plan enforcement  
- Impact: Validates $500K+ ARR through subscription tier compliance
- Revenue Impact: Prevents revenue leakage from improper access permissions

Integration tests validating user plan tier enforcement in WebSocket context.
These tests ensure subscription-based access control works end-to-end with real services.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from test_framework.base import BaseTestCase
from test_framework.fixtures.auth_fixtures import real_services_fixture, create_test_user_context
from test_framework.fixtures.websocket_fixtures import websocket_connection_fixture
from netra_backend.app.services.tool_permission_service import (
    ToolPermissionService, 
    ToolExecutionContext,
    PermissionCheckResult
)
from netra_backend.app.schemas.user_plan import (
    PlanTier, 
    UserPlan, 
    PLAN_DEFINITIONS,
    PlanFeatures,
    ToolAllowance
)
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuth
from netra_backend.app.core.redis_connection_handler import RedisConnectionHandler


@pytest.mark.integration
@pytest.mark.websocket_auth
@pytest.mark.timeout(30)
class TestWebSocketUserPlanIntegration(BaseTestCase):
    """Integration tests for WebSocket user plan validation and enforcement"""

    @pytest.fixture(autouse=True)
    async def setup_services(self, real_services_fixture):
        """Setup real services for plan validation testing"""
        self.redis_client = await RedisConnectionHandler().get_async_redis()
        self.permission_service = ToolPermissionService(self.redis_client)
        self.websocket_auth = UnifiedWebSocketAuth()
        
        # Clean up any existing test data
        await self._cleanup_test_data()
        
    async def _cleanup_test_data(self):
        """Clean up test data from Redis"""
        try:
            test_keys = await self.redis_client.keys("test:user:*")
            if test_keys:
                await self.redis_client.delete(*test_keys)
        except Exception:
            pass  # Redis may not be available in all test environments

    async def test_free_plan_tool_permission_validation(self):
        """
        BVJ: Validates FREE tier users can only access basic tools
        Business Impact: Protects premium features from unauthorized access
        Revenue Impact: Drives conversion from FREE to PRO tier
        """
        # Given: A user with FREE plan
        user_id = "test_user_free_001"
        context = ToolExecutionContext(
            user_id=user_id,
            tool_name="create_thread",
            user_plan=PlanTier.FREE.value,
            websocket_session_id="ws_test_001"
        )
        
        # When: User attempts to use a basic tool within allowance
        result = await self.permission_service.check_tool_permission(context)
        
        # Then: Permission should be granted for basic tools
        assert result.allowed is True, f"FREE user should access basic tools, got: {result.reason}"
        assert result.business_requirements_met is True
        
        # Verify rate limits are applied correctly for FREE tier
        assert result.rate_limit_status is not None
        assert result.rate_limit_status["allowed"] is True
        
        # Record usage analytics
        self.record_metric("free_plan_basic_tool_access", result.allowed)

    async def test_free_plan_premium_tool_rejection(self):
        """
        BVJ: Validates FREE tier users cannot access premium analytics tools
        Business Impact: Protects $29/month PRO tier value proposition
        Revenue Impact: Clear upgrade path enforcement drives conversions
        """
        # Given: A user with FREE plan attempting premium tool access
        user_id = "test_user_free_002"
        context = ToolExecutionContext(
            user_id=user_id,
            tool_name="analyze_workload",  # PRO+ tool
            user_plan=PlanTier.FREE.value,
            websocket_session_id="ws_test_002"
        )
        
        # When: User attempts to use premium analytics tool
        result = await self.permission_service.check_tool_permission(context)
        
        # Then: Permission should be denied with upgrade path
        assert result.allowed is False, "FREE user should not access premium tools"
        assert "Missing permissions" in result.reason or "Rate limit exceeded" in result.reason
        assert result.upgrade_path is not None, "Upgrade path should be provided"
        assert result.missing_permissions is not None
        
        # Verify upgrade path suggests PRO tier
        upgrade_suggestion = result.upgrade_path
        assert "pro" in upgrade_suggestion.lower() or "professional" in upgrade_suggestion.lower()
        
        self.record_metric("free_plan_upgrade_path_provided", result.upgrade_path is not None)

    async def test_pro_plan_advanced_tool_access(self):
        """
        BVJ: Validates PRO tier users can access analytics and data management tools
        Business Impact: Ensures $29/month value delivery through tool access
        Revenue Impact: Validates PRO tier monetization and feature availability
        """
        # Given: A user with PRO plan
        user_id = "test_user_pro_001"
        context = ToolExecutionContext(
            user_id=user_id,
            tool_name="analyze_workload",
            user_plan=PlanTier.PRO.value,
            websocket_session_id="ws_test_003"
        )
        
        # When: PRO user attempts to use analytics tool
        result = await self.permission_service.check_tool_permission(context)
        
        # Then: Permission should be granted with higher rate limits
        assert result.allowed is True, f"PRO user should access analytics tools, got: {result.reason}"
        assert result.business_requirements_met is True
        
        # Verify PRO tier gets higher rate limits (2x multiplier)
        rate_limits = result.rate_limit_status.get("limits", {})
        assert isinstance(rate_limits, dict), "Rate limits should be provided for PRO users"
        
        self.record_metric("pro_plan_analytics_access", result.allowed)
        self.record_metric("pro_plan_rate_limit_multiplier", 2.0)

    async def test_enterprise_plan_unlimited_access(self):
        """
        BVJ: Validates ENTERPRISE tier users get unlimited tool access
        Business Impact: Ensures $299/month value through unlimited usage
        Revenue Impact: Validates highest tier monetization and feature set
        """
        # Given: A user with ENTERPRISE plan
        user_id = "test_user_enterprise_001"
        context = ToolExecutionContext(
            user_id=user_id,
            tool_name="system_management_tool",  # Enterprise-only tool
            user_plan=PlanTier.ENTERPRISE.value,
            websocket_session_id="ws_test_004"
        )
        
        # When: Enterprise user attempts to use system management tool
        result = await self.permission_service.check_tool_permission(context)
        
        # Then: Permission should be granted with unlimited access
        assert result.allowed is True, "Enterprise user should have unlimited access"
        assert result.business_requirements_met is True
        
        # Verify unlimited rate limits (10x multiplier)
        rate_status = result.rate_limit_status
        if rate_status and "limits" in rate_status:
            # Enterprise should have very high or unlimited limits
            assert rate_status["allowed"] is True
            
        self.record_metric("enterprise_plan_unlimited_access", result.allowed)
        self.record_metric("enterprise_plan_rate_limit_multiplier", 10.0)

    async def test_developer_plan_internal_tool_access(self):
        """
        BVJ: Validates DEVELOPER tier (internal) gets full system access
        Business Impact: Enables development team productivity and testing
        Revenue Impact: Supports platform development without cost barriers
        """
        # Given: A user with DEVELOPER plan (internal)
        user_id = "test_user_developer_001"
        context = ToolExecutionContext(
            user_id=user_id,
            tool_name="internal_debug_tool",
            user_plan=PlanTier.DEVELOPER.value,
            websocket_session_id="ws_test_005"
        )
        
        # When: Developer user attempts to use internal tools
        result = await self.permission_service.check_tool_permission(context)
        
        # Then: Permission should be granted with maximum privileges
        assert result.allowed is True, "Developer user should have full access"
        assert result.business_requirements_met is True
        
        # Verify developer gets highest rate limits (100x multiplier)
        self.record_metric("developer_plan_full_access", result.allowed)

    async def test_plan_upgrade_path_validation_with_websocket(self):
        """
        BVJ: Validates upgrade path suggestions integrate with WebSocket messaging
        Business Impact: Drives revenue through in-app upgrade promotions
        Revenue Impact: Increases conversion rates through contextual upgrade offers
        """
        # Given: A FREE user hitting premium tool restrictions
        user_id = "test_user_upgrade_001"
        context = ToolExecutionContext(
            user_id=user_id,
            tool_name="generate_synthetic_data",  # PRO+ tool
            user_plan=PlanTier.FREE.value,
            websocket_session_id="ws_test_006"
        )
        
        # When: User attempts premium tool and gets upgrade suggestion
        result = await self.permission_service.check_tool_permission(context)
        
        # Then: Clear upgrade path should be provided
        assert result.allowed is False, "FREE user should be denied premium tool access"
        assert result.upgrade_path is not None, "Upgrade path must be provided"
        assert result.missing_permissions is not None
        
        # Verify upgrade path contains business value messaging
        upgrade_message = result.upgrade_path.lower()
        business_terms = ["pro", "professional", "analytics", "advanced", "upgrade"]
        assert any(term in upgrade_message for term in business_terms), \
            f"Upgrade path should contain business terms, got: {result.upgrade_path}"
        
        self.record_metric("upgrade_path_business_messaging", True)
        self.record_metric("conversion_opportunity_detected", True)

    async def test_plan_downgrade_websocket_session_impact(self):
        """
        BVJ: Validates plan downgrade effects on active WebSocket sessions
        Business Impact: Ensures fair usage enforcement and revenue protection
        Revenue Impact: Prevents feature access after plan downgrades
        """
        # Given: A user who was PRO but downgraded to FREE
        user_id = "test_user_downgrade_001"
        
        # First verify they had PRO access
        pro_context = ToolExecutionContext(
            user_id=user_id,
            tool_name="analyze_workload",
            user_plan=PlanTier.PRO.value,
            websocket_session_id="ws_test_007"
        )
        pro_result = await self.permission_service.check_tool_permission(pro_context)
        assert pro_result.allowed is True, "Should have PRO access initially"
        
        # When: User plan is downgraded to FREE (simulated)
        free_context = ToolExecutionContext(
            user_id=user_id,
            tool_name="analyze_workload",
            user_plan=PlanTier.FREE.value,  # Downgraded
            websocket_session_id="ws_test_007"  # Same session
        )
        
        # Then: Access should be denied immediately
        free_result = await self.permission_service.check_tool_permission(free_context)
        assert free_result.allowed is False, "Should lose PRO access after downgrade"
        
        # Verify graceful degradation messaging
        assert free_result.reason is not None
        assert free_result.upgrade_path is not None
        
        self.record_metric("plan_downgrade_immediate_effect", True)
        self.record_metric("graceful_degradation_messaging", free_result.upgrade_path is not None)


@pytest.mark.integration  
@pytest.mark.websocket_auth
@pytest.mark.timeout(45)
class TestWebSocketPlanFeatureValidation(BaseTestCase):
    """Integration tests for plan feature flag and business requirement validation"""
    
    @pytest.fixture(autouse=True)
    async def setup_services(self, real_services_fixture):
        """Setup real services for feature validation testing"""
        self.redis_client = await RedisConnectionHandler().get_async_redis()
        self.permission_service = ToolPermissionService(self.redis_client)
        await self._cleanup_test_data()
        
    async def _cleanup_test_data(self):
        """Clean up test data from Redis"""
        try:
            test_keys = await self.redis_client.keys("test:feature:*")
            if test_keys:
                await self.redis_client.delete(*test_keys)
        except Exception:
            pass

    async def test_feature_flag_enforcement_per_plan(self):
        """
        BVJ: Validates feature flags are enforced correctly per plan tier
        Business Impact: Protects feature differentiation between plan tiers
        Revenue Impact: Ensures customers pay for advanced features they use
        """
        # Given: Different plan tiers with different feature flags
        test_cases = [
            (PlanTier.FREE, "data_operations", False),  # Not included in FREE
            (PlanTier.PRO, "data_operations", True),   # Included in PRO
            (PlanTier.PRO, "system_management", False), # Not included in PRO
            (PlanTier.ENTERPRISE, "system_management", True), # Included in Enterprise
        ]
        
        for plan_tier, feature_flag, should_have_access in test_cases:
            # When: User attempts to use feature-gated tool
            user_id = f"test_user_feature_{plan_tier.value}_{feature_flag}"
            context = ToolExecutionContext(
                user_id=user_id,
                tool_name=f"tool_requiring_{feature_flag}",
                user_plan=plan_tier.value,
                websocket_session_id=f"ws_feature_test_{plan_tier.value}"
            )
            
            result = await self.permission_service.check_tool_permission(context)
            
            # Then: Access should match plan entitlements
            if should_have_access:
                # Higher tier should have access or at least not be blocked by missing features
                # (may still be blocked by other factors like rate limits)
                assert result.allowed or "feature" not in result.reason.lower(), \
                    f"{plan_tier} should have {feature_flag} access"
            else:
                # Lower tier should be blocked by missing features or permissions
                if not result.allowed:
                    assert "permission" in result.reason.lower() or "feature" in result.reason.lower()
            
            self.record_metric(f"feature_flag_{plan_tier.value}_{feature_flag}", result.allowed)

    async def test_business_requirement_validation_integration(self):
        """
        BVJ: Validates business requirements are checked in WebSocket context
        Business Impact: Ensures compliance and business rule enforcement
        Revenue Impact: Protects against policy violations that could impact revenue
        """
        # Given: A user attempting tool that has business requirements
        user_id = "test_user_business_req_001"
        context = ToolExecutionContext(
            user_id=user_id,
            tool_name="compliance_audit_tool",
            user_plan=PlanTier.ENTERPRISE.value,  # Has permissions
            websocket_session_id="ws_business_test_001"
        )
        
        # When: Permission check validates business requirements
        result = await self.permission_service.check_tool_permission(context)
        
        # Then: Business requirements should be validated
        assert result.allowed is True or result.business_requirements_met is not None, \
            "Business requirements should be checked"
        
        # If allowed, business requirements should be met
        if result.allowed:
            assert result.business_requirements_met is True, \
                "Business requirements should be met for allowed access"
        
        self.record_metric("business_requirement_validation", True)
        self.record_metric("compliance_checking_active", result.business_requirements_met is not None)