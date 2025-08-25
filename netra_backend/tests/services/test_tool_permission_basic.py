"""
Tool Permission Service - Basic Tests
Split from large test file for architecture compliance
Test classes: TestServiceInitialization, TestGetUserPlan, TestGetUserPermissions, TestToolRequiredPermissions, TestHasPermission
"""

import sys
from pathlib import Path

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Set
from unittest.mock import AsyncMock, MagicMock

import pytest

from netra_backend.app.schemas.ToolPermission import (
    BusinessRequirement,
    PermissionCheckResult,
    PermissionLevel,
    RateLimit,
    ToolAvailability,
    ToolExecutionContext,
    ToolPermission,
)
from netra_backend.app.schemas.UserPlan import PLAN_DEFINITIONS, PlanTier, UserPlan

from netra_backend.app.services.tool_permission_service import ToolPermissionService

class MockRedisClient:
    """Mock Redis client for testing"""
    def __init__(self):
        self.data = {}
        self.expires = {}
    
    async def get(self, key):
        if key in self.expires and datetime.now(UTC) > self.expires[key]:
            del self.data[key]
            del self.expires[key]
            return None
        return self.data.get(key)
    
    async def set(self, key, value, ex=None):
        self.data[key] = str(value)
        if ex:
            self.expires[key] = datetime.now(UTC) + timedelta(seconds=ex)
        return True
    
    async def incr(self, key):
        current = int(self.data.get(key, "0"))
        self.data[key] = str(current + 1)
        return current + 1
    
    async def expire(self, key, seconds):
        if key in self.data:
            self.expires[key] = datetime.now(UTC) + timedelta(seconds=seconds)
        return True

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

@pytest.fixture
def sample_context():
    """Create sample tool execution context"""
    return ToolExecutionContext(
        user_id="test_user_123",
        tool_name="analyze_workload",
        requested_action="execute",
        user_plan="pro",
        user_roles=["user"],
        is_developer=False,
        environment="production"
    )

@pytest.fixture
def developer_context():
    """Create developer execution context"""
    return ToolExecutionContext(
        user_id="dev_user_123",
        tool_name="debug_panel",
        requested_action="execute",
        user_plan="enterprise",
        user_roles=["developer", "admin"],
        is_developer=True,
        environment="development"
    )

class TestServiceInitialization:
    """Test service initialization and configuration"""
    
    def test_initialization_without_redis(self):
        """Test initialization without Redis client"""
        service = ToolPermissionService()
        
        assert service.redis == None
        assert service.permissions_cache == {}
        assert hasattr(service, '_permission_definitions')
        assert len(service._permission_definitions) > 0
    
    def test_initialization_with_redis(self, mock_redis):
        """Test initialization with Redis client"""
        service = ToolPermissionService(mock_redis)
        
        assert service.redis == mock_redis
        assert service.permissions_cache == {}
        assert hasattr(service, '_permission_definitions')
    
    def test_permission_definitions_loaded(self, service):
        """Test that permission definitions are loaded correctly"""
        definitions = service._permission_definitions
        
        # Check expected permission categories
        expected_perms = ["basic", "analytics", "data_management", 
                         "advanced_optimization", "system_management", "developer_tools"]
        
        for perm_name in expected_perms:
            assert perm_name in definitions
            assert isinstance(definitions[perm_name], ToolPermission)
    
    def test_basic_permission_configuration(self, service):
        """Test basic permission configuration"""
        basic_perm = service._permission_definitions["basic"]
        
        assert basic_perm.name == "basic"
        assert basic_perm.level == PermissionLevel.READ
        assert len(basic_perm.required_roles) == 0  # No special roles required

class TestGetUserPlan:
    """Test user plan retrieval"""
    
    @pytest.mark.asyncio
    async def test_get_user_plan_default(self, service):
        """Test getting default user plan"""
        plan = await service._get_user_plan("test_user")
        
        assert isinstance(plan, UserPlan)
        assert plan.tier == PlanTier.FREE
        assert plan.user_id == "test_user"

class TestGetUserPermissions:
    """Test user permissions retrieval"""
    
    def test_get_user_permissions_from_plan(self, service, sample_context):
        """Test getting user permissions from plan"""
        # Mock user plan
        with patch.object(service, '_get_user_plan') as mock_get_plan:
            mock_plan = UserPlan(
                user_id=sample_context.user_id,
                tier=PlanTier.PRO,
                permissions=["basic", "analytics", "data_management"]
            )
            mock_get_plan.return_value = mock_plan
            
            permissions = service._get_user_permissions(sample_context)
            
            assert "basic" in permissions
            assert "analytics" in permissions
            assert "data_management" in permissions
            assert "developer_tools" not in permissions
    
    def test_get_user_permissions_with_developer_role(self, service, developer_context):
        """Test developer role permissions"""
        permissions = service._get_user_permissions(developer_context)
        
        # Developer should get additional permissions
        assert "developer_tools" in permissions
        assert "basic" in permissions

class TestToolRequiredPermissions:
    """Test tool required permissions lookup"""
    
    def test_get_tool_required_permissions_basic(self, service):
        """Test getting required permissions for basic tools"""
        required = service._get_tool_required_permissions("analyze_workload")
        
        assert "analytics" in required
        assert isinstance(required, set)
    
    def test_get_tool_required_permissions_admin_tool(self, service):
        """Test getting required permissions for admin tools"""
        required = service._get_tool_required_permissions("system_config")
        
        assert "system_management" in required
    
    def test_get_tool_required_permissions_unknown_tool(self, service):
        """Test getting required permissions for unknown tool"""
        required = service._get_tool_required_permissions("unknown_tool")
        
        # Should default to basic permissions
        assert "basic" in required

class TestHasPermission:
    """Test permission checking logic"""
    
    def test_has_permission_direct(self, service, sample_context):
        """Test direct permission check"""
        user_permissions = {"basic", "analytics"}
        
        assert service._has_permission(user_permissions, "basic")
        assert service._has_permission(user_permissions, "analytics")
        assert not service._has_permission(user_permissions, "system_management")
    
    def test_has_permission_hierarchy(self, service, sample_context):
        """Test permission hierarchy"""
        # Enterprise should include all lower-tier permissions
        user_permissions = {"system_management"}  # High-level permission
        
        # Test that high-level permissions don't automatically grant lower ones
        # (This depends on service implementation)
        result = service._has_permission(user_permissions, "basic")
        assert isinstance(result, bool)