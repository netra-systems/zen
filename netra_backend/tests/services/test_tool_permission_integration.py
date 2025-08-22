"""
Tool Permission Service - Integration Scenarios and Edge Cases Tests
Functions refactored to ≤8 lines each using helper functions
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from netra_backend.app.schemas.ToolPermission import (
    BusinessRequirement,
    ToolExecutionContext,
)
from netra_backend.app.schemas.UserPlan import PLAN_DEFINITIONS, PlanTier, UserPlan

from netra_backend.app.services.tool_permission_service import ToolPermissionService
from netra_backend.tests.services.helpers.shared_test_types import (
    TestIntegrationScenarios as SharedTestIntegrationScenarios,
)
from netra_backend.tests.tool_permission_helpers import (
    MockRedisClient,
    assert_business_requirements_result,
    assert_missing_permissions,
    assert_permission_allowed,
    assert_permission_denied,
    create_heavy_usage_context,
    create_user_plan,
    setup_mock_user_plan,
    setup_redis_usage,
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

class TestIntegrationScenarios(SharedTestIntegrationScenarios):
    """Test integration scenarios combining multiple features"""
    async def test_developer_access_in_production(self, service):
        """Test developer tool access in production environment"""
        context = ToolExecutionContext(
            user_id="dev_user",
            tool_name="debug_panel",
            requested_action="execute",
            user_plan="enterprise",
            user_roles=["developer", "admin"],
            is_developer=True,
            environment="production"
        )
        user_plan = create_user_plan(PlanTier.ENTERPRISE, "dev_user")
        with setup_mock_user_plan(service, user_plan):
            result = await service.check_tool_permission(context)
        assert_permission_denied(result)
        assert_missing_permissions(result, ["developer_tools"])
    async def test_free_user_enterprise_tool(self, service):
        """Test free user trying to access enterprise tool"""
        context = ToolExecutionContext(
            user_id="free_user",
            tool_name="multi_objective_optimization",
            requested_action="execute",
            user_plan="free",
            user_roles=["user"],
            is_developer=False
        )
        user_plan = create_user_plan(PlanTier.FREE, "free_user")
        with setup_mock_user_plan(service, user_plan):
            result = await service.check_tool_permission(context)
        assert_permission_denied(result)
        assert_missing_permissions(result, ["advanced_optimization"])
        assert result.upgrade_path == "Enterprise"
    async def test_pro_user_with_heavy_usage(self, service_with_redis):
        """Test pro user with heavy tool usage"""
        context = create_heavy_usage_context()
        await setup_redis_usage(service_with_redis.redis, 
                               context.user_id, context.tool_name, 499, "day")
        user_plan = create_user_plan(PlanTier.PRO, "heavy_user")
        with setup_mock_user_plan(service_with_redis, user_plan):
            result = await service_with_redis.check_tool_permission(context)
        assert_permission_allowed(result)
        assert result.rate_limit_status["current_usage"] == 499

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_permission_definitions_immutability(self, service):
        """Test that permission definitions cannot be easily modified"""
        original_basic_tools = service._permission_definitions["basic"].tools.copy()
        service._permission_definitions["basic"].tools.append("malicious_tool")
        new_service = ToolPermissionService()
        assert len(new_service._permission_definitions["basic"].tools) == len(original_basic_tools)
    
    def test_business_requirements_edge_cases(self, service):
        """Test business requirements with edge case values"""
        empty_req = BusinessRequirement()
        context = ToolExecutionContext(
            user_id="test",
            tool_name="test",
            requested_action="test",
            user_plan="free",
            user_roles=[],
            is_developer=False
        )
        user_plan = create_user_plan(PlanTier.FREE, "test")
        result = service._check_business_requirements(empty_req, context, user_plan)
        assert_business_requirements_result(result, True)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])