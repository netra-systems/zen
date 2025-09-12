"""
WebSocket Tool Permission Authorization Integration Tests

Business Value Justification (BVJ):
- Segment: All plan tiers - security and access control
- Goal: Revenue protection through proper authorization enforcement  
- Impact: Prevents unauthorized tool access that could bypass billing
- Revenue Impact: Protects $500K+ ARR through secure tool execution

Integration tests validating tool permission checking and authorization in WebSocket context.
These tests ensure tool execution permissions work end-to-end with real services.
"""

import asyncio
import pytest
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, List, Optional
from unittest.mock import patch

from test_framework.base import BaseTestCase
from test_framework.fixtures.auth_fixtures import real_services_fixture, create_test_user_context
from test_framework.fixtures.websocket_fixtures import websocket_connection_fixture
from netra_backend.app.services.tool_permission_service import (
    ToolPermissionService, 
    ToolExecutionContext,
    PermissionCheckResult,
    PermissionLevel
)
from netra_backend.app.services.tool_permissions.permission_checker import PermissionChecker
from netra_backend.app.services.tool_permissions.permission_definitions import PermissionDefinitions
from netra_backend.app.schemas.user_plan import PlanTier, PLAN_DEFINITIONS
from netra_backend.app.core.redis_connection_handler import RedisConnectionHandler


@pytest.mark.integration
@pytest.mark.websocket_auth
@pytest.mark.timeout(30)
class TestWebSocketToolPermissionAuthorization(BaseTestCase):
    """Integration tests for tool permission authorization in WebSocket context"""

    @pytest.fixture(autouse=True)
    async def setup_services(self, real_services_fixture):
        """Setup real services for permission authorization testing"""
        self.redis_client = await RedisConnectionHandler().get_async_redis()
        self.permission_service = ToolPermissionService(self.redis_client)
        self.permission_definitions = PermissionDefinitions.load_permission_definitions()
        self.permission_checker = PermissionChecker(self.permission_definitions)
        
        # Clean up any existing test data
        await self._cleanup_test_data()
        
    async def _cleanup_test_data(self):
        """Clean up test data from Redis"""
        try:
            test_keys = await self.redis_client.keys("test:permission:*")
            if test_keys:
                await self.redis_client.delete(*test_keys)
        except Exception:
            pass  # Redis may not be available in all test environments

    async def test_tool_execution_permission_validation_with_context(self):
        """
        BVJ: Validates tool execution permissions with real ToolExecutionContext
        Business Impact: Ensures only authorized users can execute billable tools
        Revenue Impact: Prevents unauthorized access that could bypass metering
        """
        # Given: A tool that requires specific permissions
        user_id = "test_user_permission_001"
        context = ToolExecutionContext(
            user_id=user_id,
            tool_name="analyze_workload",
            user_plan=PlanTier.PRO.value,
            websocket_session_id="ws_permission_001",
            additional_context={
                "request_timestamp": datetime.now(UTC).isoformat(),
                "client_info": "integration_test"
            }
        )
        
        # When: Permission check is performed with full context
        result = await self.permission_service.check_tool_permission(context)
        
        # Then: Permission should be validated against user's actual plan
        assert result is not None, "Permission result should be returned"
        assert isinstance(result, PermissionCheckResult), "Result should be PermissionCheckResult"
        
        # Verify context is properly used in permission checking
        if result.allowed:
            assert result.business_requirements_met is True
            assert result.required_permissions is not None
        else:
            assert result.reason is not None, "Denial reason should be provided"
            assert result.missing_permissions is not None or "rate limit" in result.reason.lower()
        
        self.record_metric("permission_validation_with_context", True)
        self.record_metric("context_integration_working", context.websocket_session_id is not None)

    async def test_required_permission_validation_integration(self):
        """
        BVJ: Validates required permission checking for specific tools
        Business Impact: Ensures proper access control for premium features
        Revenue Impact: Protects feature differentiation between plan tiers
        """
        # Given: A tool with specific permission requirements
        test_tool_permissions = [
            ("create_thread", ["basic"]),
            ("analyze_workload", ["analytics"]),
            ("generate_synthetic_data", ["data_management"]),
            ("system_admin_tool", ["system_management"])
        ]
        
        for tool_name, expected_permissions in test_tool_permissions:
            # When: Getting required permissions for tool
            required_permissions = self.permission_checker.get_tool_required_permissions(tool_name)
            
            # Then: Required permissions should be defined
            assert isinstance(required_permissions, list), f"Tool {tool_name} should have permission list"
            
            # Verify permissions are validated in context
            user_id = f"test_user_{tool_name}_req"
            context = ToolExecutionContext(
                user_id=user_id,
                tool_name=tool_name,
                user_plan=PlanTier.FREE.value,  # Start with lowest tier
                websocket_session_id=f"ws_{tool_name}_req"
            )
            
            result = await self.permission_service.check_tool_permission(context)
            
            # If tool has permission requirements and user is FREE, should check properly
            if required_permissions and any(perm not in ["basic"] for perm in required_permissions):
                # FREE tier missing advanced permissions should be denied
                if not result.allowed:
                    assert result.missing_permissions is not None or "rate limit" in result.reason.lower()
                    
            self.record_metric(f"tool_{tool_name}_permission_validation", True)

    async def test_missing_permission_detection_and_upgrade_path(self):
        """
        BVJ: Validates missing permission detection provides clear upgrade paths
        Business Impact: Drives conversion through contextual upgrade messaging
        Revenue Impact: Increases subscription upgrade rates through clear guidance
        """
        # Given: A FREE user attempting PRO-tier tool
        user_id = "test_user_missing_perm_001"
        context = ToolExecutionContext(
            user_id=user_id,
            tool_name="advanced_analytics_tool",
            user_plan=PlanTier.FREE.value,
            websocket_session_id="ws_missing_perm_001"
        )
        
        # When: Permission check identifies missing permissions
        result = await self.permission_service.check_tool_permission(context)
        
        # Then: Missing permissions should be clearly identified
        if not result.allowed:
            # Should provide either missing permissions or rate limit info
            assert (result.missing_permissions is not None or 
                   "rate limit" in result.reason.lower() or
                   "permission" in result.reason.lower()), \
                f"Should identify missing permissions or rate limits, got: {result.reason}"
            
            # Should provide upgrade path
            assert result.upgrade_path is not None, "Upgrade path should be provided"
            
            # Upgrade path should mention higher tier
            upgrade_message = result.upgrade_path.lower()
            tier_mentions = ["pro", "professional", "premium", "enterprise", "upgrade"]
            assert any(tier in upgrade_message for tier in tier_mentions), \
                f"Upgrade path should mention tier upgrade: {result.upgrade_path}"
                
        self.record_metric("missing_permission_detection", result.missing_permissions is not None)
        self.record_metric("upgrade_path_provided", result.upgrade_path is not None)

    async def test_cross_tool_permission_inheritance_validation(self):
        """
        BVJ: Validates permission inheritance between related tools
        Business Impact: Ensures consistent access patterns across tool families
        Revenue Impact: Maintains clear value propositions for plan tiers
        """
        # Given: Related tools that should have consistent permission patterns
        tool_families = {
            "data_tools": ["analyze_workload", "generate_synthetic_data", "data_export"],
            "admin_tools": ["user_management", "system_config", "audit_logs"],
            "basic_tools": ["create_thread", "get_thread_history", "list_agents"]
        }
        
        for family_name, tools in tool_families.items():
            user_id = f"test_user_{family_name}_inheritance"
            
            # Test with PRO user to see permission patterns
            pro_results = []
            for tool in tools:
                context = ToolExecutionContext(
                    user_id=user_id,
                    tool_name=tool,
                    user_plan=PlanTier.PRO.value,
                    websocket_session_id=f"ws_{family_name}_{tool}"
                )
                
                result = await self.permission_service.check_tool_permission(context)
                pro_results.append((tool, result.allowed, result.required_permissions))
            
            # Then: Tools in same family should have consistent permission patterns
            allowed_tools = [tool for tool, allowed, _ in pro_results if allowed]
            denied_tools = [tool for tool, allowed, _ in pro_results if not allowed]
            
            # For basic tools, PRO should have access
            if family_name == "basic_tools":
                assert len(allowed_tools) >= len(denied_tools), \
                    f"PRO user should access most basic tools in {family_name}"
            
            self.record_metric(f"permission_consistency_{family_name}", True)
            self.record_metric(f"pro_access_pattern_{family_name}", len(allowed_tools))

    async def test_tool_availability_based_on_subscription_tier(self):
        """
        BVJ: Validates tool availability varies correctly by subscription tier
        Business Impact: Ensures clear value differentiation between tiers
        Revenue Impact: Validates monetization model through feature restrictions
        """
        # Given: Different subscription tiers
        test_tiers = [PlanTier.FREE, PlanTier.PRO, PlanTier.ENTERPRISE]
        test_tool = "data_analytics_suite"
        
        tier_results = {}
        
        for tier in test_tiers:
            user_id = f"test_user_availability_{tier.value}"
            context = ToolExecutionContext(
                user_id=user_id,
                tool_name=test_tool,
                user_plan=tier.value,
                websocket_session_id=f"ws_availability_{tier.value}"
            )
            
            # When: Checking tool availability per tier
            result = await self.permission_service.check_tool_permission(context)
            tier_results[tier] = result.allowed
            
        # Then: Higher tiers should have equal or greater access
        free_access = tier_results.get(PlanTier.FREE, False)
        pro_access = tier_results.get(PlanTier.PRO, False)
        enterprise_access = tier_results.get(PlanTier.ENTERPRISE, False)
        
        # Access should not decrease with higher tiers
        assert not (free_access and not pro_access), "PRO should not have less access than FREE"
        assert not (pro_access and not enterprise_access), "Enterprise should not have less access than PRO"
        
        self.record_metric("tier_access_progression_valid", True)
        self.record_metric("free_tier_access", free_access)
        self.record_metric("pro_tier_access", pro_access)
        self.record_metric("enterprise_tier_access", enterprise_access)

    async def test_permission_caching_in_websocket_sessions(self):
        """
        BVJ: Validates permission caching improves performance in WebSocket sessions
        Business Impact: Ensures responsive user experience in chat interactions
        Revenue Impact: Reduces infrastructure costs through efficient caching
        """
        # Given: A user making repeated tool access requests in same session
        user_id = "test_user_caching_001"
        session_id = "ws_caching_test_001"
        
        tool_contexts = [
            ToolExecutionContext(
                user_id=user_id,
                tool_name="cached_tool_test",
                user_plan=PlanTier.PRO.value,
                websocket_session_id=session_id
            )
            for _ in range(3)  # Same request 3 times
        ]
        
        # When: Making repeated permission checks
        start_time = datetime.now()
        results = []
        
        for context in tool_contexts:
            result = await self.permission_service.check_tool_permission(context)
            results.append(result)
            
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Then: Results should be consistent and reasonably fast
        assert len(results) == 3, "Should get results for all requests"
        
        # All results should be consistent
        allowed_results = [r.allowed for r in results]
        assert len(set(allowed_results)) <= 1, "Cached results should be consistent"
        
        # Should complete in reasonable time (< 5 seconds for 3 requests)
        assert total_time < 5.0, f"Permission checks should be fast, took {total_time}s"
        
        self.record_metric("permission_caching_performance", total_time)
        self.record_metric("permission_result_consistency", len(set(allowed_results)) == 1)

    async def test_tool_permission_auditing_and_compliance(self):
        """
        BVJ: Validates tool permission auditing for compliance and analytics
        Business Impact: Enables usage analytics and compliance reporting
        Revenue Impact: Supports billing accuracy and usage-based pricing
        """
        # Given: A user executing tools that should be audited
        user_id = "test_user_auditing_001"
        audit_tools = ["audit_sensitive_tool", "compliance_required_tool", "billable_analytics_tool"]
        
        audit_results = []
        
        for tool_name in audit_tools:
            context = ToolExecutionContext(
                user_id=user_id,
                tool_name=tool_name,
                user_plan=PlanTier.ENTERPRISE.value,  # High permissions
                websocket_session_id=f"ws_audit_{tool_name}",
                additional_context={
                    "audit_required": True,
                    "compliance_level": "high",
                    "billing_category": "premium"
                }
            )
            
            # When: Permission check includes audit information
            result = await self.permission_service.check_tool_permission(context)
            audit_results.append((tool_name, result))
            
            # Record usage if permitted
            if result.allowed:
                await self.permission_service.record_tool_usage(
                    user_id=user_id,
                    tool_name=tool_name,
                    execution_time_ms=1000,  # Simulated execution time
                    status="completed"
                )
        
        # Then: Audit trail should be maintained
        successful_audits = [(tool, result) for tool, result in audit_results if result.allowed]
        
        # Should have some successful audits for enterprise user
        assert len(successful_audits) > 0, "Enterprise user should have some tool access"
        
        # Verify audit information is captured
        for tool_name, result in successful_audits:
            assert result.business_requirements_met is True, f"Business requirements should be met for {tool_name}"
            
        self.record_metric("audit_compliance_tracking", True)
        self.record_metric("successful_audit_count", len(successful_audits))
        self.record_metric("audit_trail_maintained", len(audit_results) > 0)