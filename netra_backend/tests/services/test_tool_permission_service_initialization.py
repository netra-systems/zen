"""
Tool Permission Service - Service Initialization Tests
Functions refactored to ≤8 lines each using helper functions
"""

import pytest
from netra_backend.app.services.tool_permission_service import ToolPermissionService
from netra_backend.app.schemas.ToolPermission import PermissionLevel
from netra_backend.app.schemas.UserPlan import PlanTier, PLAN_DEFINITIONS
from netra_backend.tests.helpers.tool_permission_helpers import (
    MockRedisClient,
    assert_service_initialization,
    assert_permission_definition_properties,
    get_permission_test_data
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


class TestServiceInitialization:
    """Test service initialization and configuration"""
    
    def test_initialization_without_redis(self):
        """Test initialization without Redis client"""
        service = ToolPermissionService()
        expected_perms = ["basic", "analytics", "data_management", 
                         "advanced_optimization", "system_management", "developer_tools"]
        assert_service_initialization(service, has_redis=False, expected_permissions=expected_perms)
    
    def test_initialization_with_redis(self, mock_redis):
        """Test initialization with Redis client"""
        service = ToolPermissionService(mock_redis)
        assert service.redis == mock_redis
        assert service.permissions_cache == {}
        assert hasattr(service, '_permission_definitions')
    
    def test_permission_definitions_loaded(self, service):
        """Test that permission definitions are loaded correctly"""
        definitions = service._permission_definitions
        expected_perms = ["basic", "analytics", "data_management", 
                         "advanced_optimization", "system_management", "developer_tools"]
        for perm_name in expected_perms:
            assert perm_name in definitions
    
    def test_basic_permission_configuration(self, service):
        """Test basic permission configuration"""
        basic_perm = service._permission_definitions["basic"]
        test_data = get_permission_test_data()
        assert_permission_definition_properties(
            basic_perm, "basic", PermissionLevel.READ, test_data["basic_tools"]
        )
        assert basic_perm.business_requirements.plan_tiers is None
    
    def test_analytics_permission_configuration(self, service):
        """Test analytics permission configuration"""
        analytics_perm = service._permission_definitions["analytics"]
        test_data = get_permission_test_data()
        assert_permission_definition_properties(
            analytics_perm, "analytics", PermissionLevel.READ, 
            test_data["analytics_tools"], ["pro", "enterprise"]
        )
        assert analytics_perm.rate_limits.per_hour == 100
    
    def test_data_management_permission_configuration(self, service):
        """Test data management permission configuration"""
        data_perm = service._permission_definitions["data_management"]
        assert data_perm.name == "data_management"
        assert data_perm.level == PermissionLevel.WRITE
        assert "generate_synthetic_data" in data_perm.tools
        assert "pro" in data_perm.business_requirements.plan_tiers
        assert data_perm.rate_limits.per_hour == 50
    
    def test_advanced_optimization_permission_configuration(self, service):
        """Test advanced optimization permission configuration"""
        adv_perm = service._permission_definitions["advanced_optimization"]
        test_data = get_permission_test_data()
        assert_permission_definition_properties(
            adv_perm, "advanced_optimization", PermissionLevel.WRITE,
            test_data["advanced_tools"], ["enterprise"]
        )
        assert adv_perm.rate_limits.per_hour == 20
    
    def test_system_management_permission_configuration(self, service):
        """Test system management permission configuration"""
        sys_perm = service._permission_definitions["system_management"]
        test_data = get_permission_test_data()
        assert_permission_definition_properties(
            sys_perm, "system_management", PermissionLevel.ADMIN,
            test_data["system_tools"], ["enterprise"]
        )
        assert "admin" in sys_perm.business_requirements.role_requirements
    
    def test_developer_tools_permission_configuration(self, service):
        """Test developer tools permission configuration"""
        dev_perm = service._permission_definitions["developer_tools"]
        test_data = get_permission_test_data()
        assert_permission_definition_properties(
            dev_perm, "developer_tools", PermissionLevel.ADMIN, test_data["dev_tools"]
        )
        assert dev_perm.business_requirements.developer_status == True
        assert "development" in dev_perm.business_requirements.environment


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])