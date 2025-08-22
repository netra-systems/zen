"""
Tool Permission Service - Main Permission Checking Tests
Functions refactored to ≤8 lines each using helper functions
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.schemas.ToolPermission import ToolExecutionContext
from app.schemas.UserPlan import PLAN_DEFINITIONS, PlanTier, UserPlan

# Add project root to path
from app.services.tool_permission_service import ToolPermissionService
from .tool_permission_helpers import (
    # Add project root to path
    MockRedisClient,
    assert_missing_permissions,
    assert_permission_allowed,
    assert_permission_denied,
    assert_rate_limit_status,
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
class TestCheckToolPermission:
    """Test main tool permission checking"""
    
    async def test_check_tool_permission_allowed(self, service):
        """Test tool permission check when allowed"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="create_thread",
            requested_action="execute",
            user_plan="free",
            user_roles=["user"],
            is_developer=False
        )
        user_plan = create_user_plan(PlanTier.FREE, "test_user")
        with setup_mock_user_plan(service, user_plan):
            result = await service.check_tool_permission(context)
        assert_permission_allowed(result)
        assert "basic" in result.required_permissions
    
    async def test_check_tool_permission_denied_missing_permissions(self, service):
        """Test tool permission check when permission is missing"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="analyze_workload",
            requested_action="execute",
            user_plan="free",
            user_roles=["user"],
            is_developer=False
        )
        user_plan = create_user_plan(PlanTier.FREE, "test_user")
        with setup_mock_user_plan(service, user_plan):
            result = await service.check_tool_permission(context)
        assert_permission_denied(result)
        assert_missing_permissions(result, ["analytics"])
    
    async def test_check_tool_permission_rate_limit_exceeded(self, service_with_redis):
        """Test tool permission check when rate limit is exceeded"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="analyze_workload",
            requested_action="execute",
            user_plan="pro",
            user_roles=["user"],
            is_developer=False
        )
        await setup_redis_usage(service_with_redis.redis, 
                               context.user_id, context.tool_name, 101, "hour")
        user_plan = create_user_plan(PlanTier.PRO, "test_user")
        with setup_mock_user_plan(service_with_redis, user_plan):
            result = await service_with_redis.check_tool_permission(context)
        assert_permission_denied(result)
        assert "Rate limit exceeded" in result.reason
    
    async def test_check_tool_permission_no_requirements(self, service):
        """Test tool permission check for tool with no requirements"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="unknown_tool",
            requested_action="execute",
            user_plan="free",
            user_roles=["user"],
            is_developer=False
        )
        result = await service.check_tool_permission(context)
        assert_permission_allowed(result)
        assert result.required_permissions == []
    
    async def test_check_tool_permission_error_handling(self, service):
        """Test tool permission check error handling"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="test_tool",
            requested_action="execute",
            user_plan="pro",
            user_roles=["user"],
            is_developer=False
        )
        with patch.object(service, '_get_user_plan', side_effect=Exception("Test error")):
            result = await service.check_tool_permission(context)
        assert_permission_denied(result)
        assert "Permission check failed" in result.reason


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])