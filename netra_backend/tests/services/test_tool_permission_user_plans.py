"""
Tool Permission Service - User Plans and Permissions Tests
Functions refactored to ≤8 lines each using helper functions
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import pytest

from netra_backend.app.schemas.UserPlan import (
    PLAN_DEFINITIONS,
    PlanFeatures,
    PlanTier,
    UserPlan,
)

# Add project root to path
from netra_backend.app.services.tool_permission_service import ToolPermissionService
from netra_backend.tests.helpers.tool_permission_helpers import (
    # Add project root to path
    MockRedisClient,
    create_developer_context,
    create_sample_context,
    create_user_plan,
)


@pytest.fixture
def service():
    """Create ToolPermissionService without Redis"""
    return ToolPermissionService()


@pytest.fixture
def sample_context():
    """Create sample tool execution context"""
    return create_sample_context()


@pytest.fixture
def developer_context():
    """Create developer execution context"""
    return create_developer_context()
class TestGetUserPlan:
    """Test user plan retrieval"""
    
    async def test_get_user_plan_default(self, service):
        """Test getting user plan returns default free plan"""
        user_plan = await service._get_user_plan("test_user")
        assert isinstance(user_plan, UserPlan)
        assert user_plan.user_id == "test_user"
        assert user_plan.tier == PlanTier.FREE
        assert user_plan.features == PLAN_DEFINITIONS[PlanTier.FREE].features


class TestGetUserPermissions:
    """Test user permissions retrieval"""
    
    def test_get_user_permissions_from_plan(self, service, sample_context):
        """Test getting user permissions from plan"""
        user_plan = create_user_plan(PlanTier.PRO, "test_user")
        permissions = service._get_user_permissions(sample_context, user_plan)
        assert isinstance(permissions, set)
        plan_permissions = user_plan.features.permissions
        for perm in plan_permissions:
            assert perm in permissions
    
    def test_get_user_permissions_wildcard(self, service, sample_context):
        """Test user permissions with wildcard (*) permission"""
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.ENTERPRISE,
            features=PlanFeatures(permissions=["*"], tool_allowances=[])
        )
        permissions = service._get_user_permissions(sample_context, user_plan)
        expected_perms = set(service._permission_definitions.keys())
        assert expected_perms.issubset(permissions)
    
    def test_get_user_permissions_developer(self, service, developer_context):
        """Test user permissions for developer"""
        user_plan = create_user_plan(PlanTier.FREE, "dev_user")
        permissions = service._get_user_permissions(developer_context, user_plan)
        assert "developer_tools" in permissions


class TestToolRequiredPermissions:
    """Test tool required permissions lookup"""
    
    def test_get_tool_required_permissions_basic(self, service):
        """Test getting required permissions for basic tool"""
        required = service._get_tool_required_permissions("create_thread")
        assert "basic" in required
    
    def test_get_tool_required_permissions_analytics(self, service):
        """Test getting required permissions for analytics tool"""
        required = service._get_tool_required_permissions("analyze_workload")
        assert "analytics" in required
    
    def test_get_tool_required_permissions_multiple(self, service):
        """Test tool that might require multiple permissions"""
        service._permission_definitions["basic"].tools.append("shared_tool")
        service._permission_definitions["analytics"].tools.append("shared_tool")
        required = service._get_tool_required_permissions("shared_tool")
        assert "basic" in required
        assert "analytics" in required
    
    def test_get_tool_required_permissions_unknown(self, service):
        """Test getting required permissions for unknown tool"""
        required = service._get_tool_required_permissions("unknown_tool")
        assert len(required) == 0


class TestHasPermission:
    """Test permission checking logic"""
    
    def test_has_permission_direct(self, service, sample_context):
        """Test has_permission with direct permission"""
        user_permissions = {"analytics"}
        user_plan = create_user_plan(PlanTier.PRO)
        sample_context.user_plan = "pro"
        result = service._has_permission("analytics", user_permissions, sample_context, user_plan)
        assert result == True
    
    def test_has_permission_no_permission(self, service, sample_context):
        """Test has_permission without required permission"""
        user_permissions = {"basic"}
        user_plan = create_user_plan(PlanTier.FREE)
        result = service._has_permission("analytics", user_permissions, sample_context, user_plan)
        assert result == False
    
    def test_has_permission_with_business_requirements_failed(self, service, sample_context):
        """Test has_permission with failed business requirements"""
        user_permissions = {"analytics"}
        user_plan = create_user_plan(PlanTier.FREE)
        sample_context.user_plan = "free"
        result = service._has_permission("analytics", user_permissions, sample_context, user_plan)
        assert result == False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])