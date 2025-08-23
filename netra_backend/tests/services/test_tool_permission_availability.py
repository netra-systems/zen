"""
Tool Permission Service - Tool Availability and Upgrade Path Tests
Functions refactored to ≤8 lines each using helper functions
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

from unittest.mock import patch

import pytest

from netra_backend.app.schemas.UserPlan import PLAN_DEFINITIONS, PlanTier, UserPlan

from netra_backend.app.services.tool_permission_service import ToolPermissionService
from netra_backend.tests.helpers.tool_permission_helpers import (
    MockRedisClient,
    assert_tool_availability,
    assert_tool_registry_availability,
    create_tool_registry_sample,
    create_user_plan,
    setup_mock_usage_count,
    setup_mock_user_plan,
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
class TestGetUserToolAvailability:
    """Test user tool availability functionality"""
    
    async def test_get_user_tool_availability(self, service):
        """Test getting tool availability for user"""
        user_id = "test_user"
        tool_registry = create_tool_registry_sample()
        user_plan = create_user_plan(PlanTier.PRO, user_id)
        with setup_mock_user_plan(service, user_plan):
            with setup_mock_usage_count(service, 5):
                availability = await service.get_user_tool_availability(user_id, tool_registry)
        assert_tool_registry_availability(availability, 3)
        assert_tool_availability(availability, "create_thread", True)
        assert_tool_availability(availability, "analyze_workload", True)
    
    async def test_get_user_tool_availability_with_rate_limits(self, service_with_redis):
        """Test tool availability including rate limit information"""
        user_id = "test_user"
        tool_registry = {
            "analyze_workload": {
                "category": "analytics",
                "description": "Analyze workload performance"
            }
        }
        user_plan = create_user_plan(PlanTier.PRO, user_id)
        with setup_mock_user_plan(service_with_redis, user_plan):
            availability = await service_with_redis.get_user_tool_availability(user_id, tool_registry)
        assert_tool_registry_availability(availability, 1)
        tool = availability[0]
        assert tool.available == True
        assert tool.rate_limits.per_hour == 100
    
    async def test_get_user_tool_availability_error_handling(self, service):
        """Test tool availability error handling"""
        user_id = "test_user"
        tool_registry = {"test_tool": {"category": "test"}}
        with patch.object(service, '_get_user_plan', side_effect=Exception("Test error")):
            availability = await service.get_user_tool_availability(user_id, tool_registry)
        assert availability == []
    
    async def test_empty_tool_registry(self, service):
        """Test tool availability with empty tool registry"""
        availability = await service.get_user_tool_availability("test_user", {})
        assert availability == []

class TestUpgradePath:
    """Test upgrade path determination"""
    
    def test_get_upgrade_path_pro_required(self, service):
        """Test upgrade path when PRO plan is required"""
        missing_permissions = ["analytics"]
        user_plan = create_user_plan(PlanTier.FREE)
        upgrade_path = service._get_upgrade_path(missing_permissions, user_plan)
        assert upgrade_path == "Pro"
    
    def test_get_upgrade_path_enterprise_required(self, service):
        """Test upgrade path when Enterprise plan is required"""
        missing_permissions = ["advanced_optimization"]
        user_plan = create_user_plan(PlanTier.PRO)
        upgrade_path = service._get_upgrade_path(missing_permissions, user_plan)
        assert upgrade_path == "Enterprise"
    
    def test_get_upgrade_path_no_upgrade_available(self, service):
        """Test upgrade path when no upgrade is available"""
        missing_permissions = ["nonexistent_permission"]
        user_plan = create_user_plan(PlanTier.FREE)
        upgrade_path = service._get_upgrade_path(missing_permissions, user_plan)
        assert upgrade_path is None
    
    def test_get_upgrade_path_already_highest_tier(self, service):
        """Test upgrade path when user already has highest tier"""
        missing_permissions = ["analytics"]
        user_plan = create_user_plan(PlanTier.DEVELOPER)
        upgrade_path = service._get_upgrade_path(missing_permissions, user_plan)
        assert upgrade_path is None
    
    def test_get_upgrade_path_for_rate_limits_free(self, service):
        """Test upgrade path for rate limits from free plan"""
        user_plan = create_user_plan(PlanTier.FREE)
        upgrade_path = service._get_upgrade_path_for_rate_limits(user_plan)
        assert upgrade_path == "Pro"
    
    def test_get_upgrade_path_for_rate_limits_pro(self, service):
        """Test upgrade path for rate limits from pro plan"""
        user_plan = create_user_plan(PlanTier.PRO)
        upgrade_path = service._get_upgrade_path_for_rate_limits(user_plan)
        assert upgrade_path == "Enterprise"
    
    def test_get_upgrade_path_for_rate_limits_enterprise(self, service):
        """Test upgrade path for rate limits from enterprise plan"""
        user_plan = create_user_plan(PlanTier.ENTERPRISE)
        upgrade_path = service._get_upgrade_path_for_rate_limits(user_plan)
        assert upgrade_path is None

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])