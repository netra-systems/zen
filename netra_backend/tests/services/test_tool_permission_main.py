"""
Tool Permission Service - Main Permission Checking and Tool Availability
Split from large test file for architecture compliance
Test classes: TestCheckToolPermission, TestGetUserToolAvailability, TestUpgradePath
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
def admin_context():
    """Create admin execution context"""
    return ToolExecutionContext(
        user_id="admin_user_123",
        tool_name="system_config",
        requested_action="execute",
        user_plan="enterprise",
        user_roles=["admin", "user"],
        is_developer=False,
        environment="production"
    )
class TestCheckToolPermission:
    """Test main tool permission checking"""
    
    @pytest.mark.asyncio
    async def test_check_tool_permission_allowed(self, service):
        """Test tool permission check when access is allowed"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="analyze_workload",
            requested_action="execute",
            user_plan="pro",
            user_roles=["user"],
            is_developer=False,
            environment="production"
        )
        
        with patch.object(service, '_get_user_plan') as mock_get_plan:
            mock_plan = UserPlan(
                user_id="test_user",
                tier=PlanTier.PRO,
                permissions=["basic", "analytics", "data_management"]
            )
            mock_get_plan.return_value = mock_plan
            
            result = await service.check_tool_permission(context)
            
            assert isinstance(result, PermissionCheckResult)
            assert result.allowed == True
            assert "analytics" in result.required_permissions
            assert result.reason is not None
    
    @pytest.mark.asyncio
    async def test_check_tool_permission_denied_insufficient_plan(self, service):
        """Test tool permission check with insufficient plan"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="advanced_optimization",
            requested_action="execute",
            user_plan="free",
            user_roles=["user"],
            is_developer=False,
            environment="production"
        )
        
        with patch.object(service, '_get_user_plan') as mock_get_plan:
            mock_plan = UserPlan(
                user_id="test_user",
                tier=PlanTier.FREE,
                permissions=["basic"]
            )
            mock_get_plan.return_value = mock_plan
            
            result = await service.check_tool_permission(context)
            
            assert result.allowed == False
            assert "advanced_optimization" in result.required_permissions
            assert "insufficient" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_check_tool_permission_denied_missing_role(self, service):
        """Test tool permission check with missing role"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="admin_panel",
            requested_action="execute",
            user_plan="enterprise",
            user_roles=["user"],  # Missing admin role
            is_developer=False,
            environment="production"
        )
        
        result = await service.check_tool_permission(context)
        
        assert result.allowed == False
        assert "admin" in result.required_permissions or "system_management" in result.required_permissions
    
    @pytest.mark.asyncio
    async def test_check_tool_permission_with_business_requirements(self, service, admin_context):
        """Test tool permission check with business requirements"""
        with patch.object(service, '_get_user_plan') as mock_get_plan:
            mock_plan = UserPlan(
                user_id="admin_user_123",
                tier=PlanTier.ENTERPRISE,
                permissions=["basic", "analytics", "system_management"]
            )
            mock_get_plan.return_value = mock_plan
            
            result = await service.check_tool_permission(admin_context)
            
            assert isinstance(result, PermissionCheckResult)
            # Result depends on implementation
    
    @pytest.mark.asyncio
    async def test_check_tool_permission_with_rate_limiting(self, service_with_redis, sample_context):
        """Test tool permission check with rate limiting"""
        with patch.object(service_with_redis, '_get_user_plan') as mock_get_plan:
            mock_plan = UserPlan(
                user_id="test_user_123",
                tier=PlanTier.PRO,
                permissions=["basic", "analytics"]
            )
            mock_get_plan.return_value = mock_plan
            
            result = await service_with_redis.check_tool_permission(sample_context)
            
            assert isinstance(result, PermissionCheckResult)
            # Should include rate limit information
class TestGetUserToolAvailability:
    """Test user tool availability functionality"""
    
    @pytest.mark.asyncio
    async def test_get_user_tool_availability(self, service):
        """Test getting user tool availability"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="",  # Not specific tool
            requested_action="list",
            user_plan="pro",
            user_roles=["user"],
            is_developer=False,
            environment="production"
        )
        
        with patch.object(service, '_get_user_plan') as mock_get_plan:
            mock_plan = UserPlan(
                user_id="test_user",
                tier=PlanTier.PRO,
                permissions=["basic", "analytics", "data_management"]
            )
            mock_get_plan.return_value = mock_plan
            
            availability = await service.get_user_tool_availability(context)
            
            assert isinstance(availability, dict)
            assert "available_tools" in availability
            assert "restricted_tools" in availability
            assert isinstance(availability["available_tools"], list)
            assert isinstance(availability["restricted_tools"], list)
    
    @pytest.mark.asyncio
    async def test_get_user_tool_availability_free_user(self, service):
        """Test tool availability for free tier user"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="",
            requested_action="list",
            user_plan="free",
            user_roles=["user"],
            is_developer=False,
            environment="production"
        )
        
        with patch.object(service, '_get_user_plan') as mock_get_plan:
            mock_plan = UserPlan(
                user_id="test_user",
                tier=PlanTier.FREE,
                permissions=["basic"]
            )
            mock_get_plan.return_value = mock_plan
            
            availability = await service.get_user_tool_availability(context)
            
            assert len(availability["restricted_tools"]) > 0
            # Free users should have many restricted tools
    
    @pytest.mark.asyncio
    async def test_get_user_tool_availability_enterprise(self, service):
        """Test tool availability for enterprise user"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="",
            requested_action="list",
            user_plan="enterprise",
            user_roles=["user", "admin"],
            is_developer=False,
            environment="production"
        )
        
        with patch.object(service, '_get_user_plan') as mock_get_plan:
            mock_plan = UserPlan(
                user_id="test_user",
                tier=PlanTier.ENTERPRISE,
                permissions=["basic", "analytics", "data_management", "system_management"]
            )
            mock_get_plan.return_value = mock_plan
            
            availability = await service.get_user_tool_availability(context)
            
            assert len(availability["available_tools"]) > 0
            # Enterprise users should have access to most tools

class TestUpgradePath:
    """Test upgrade path determination"""
    
    def test_get_upgrade_path_pro_required(self, service):
        """Test upgrade path when Pro is required"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="advanced_analytics",
            requested_action="execute",
            user_plan="free",
            user_roles=["user"],
            is_developer=False,
            environment="production"
        )
        
        upgrade_path = service.get_upgrade_path(context, ["analytics"])
        
        assert isinstance(upgrade_path, dict)
        assert "recommended_plan" in upgrade_path
        assert "missing_features" in upgrade_path
        assert upgrade_path["recommended_plan"] in ["pro", "enterprise"]
    
    def test_get_upgrade_path_enterprise_required(self, service):
        """Test upgrade path when Enterprise is required"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="system_management",
            requested_action="execute",
            user_plan="pro",
            user_roles=["user"],
            is_developer=False,
            environment="production"
        )
        
        upgrade_path = service.get_upgrade_path(context, ["system_management"])
        
        assert upgrade_path["recommended_plan"] == "enterprise"
    
    def test_get_upgrade_path_role_required(self, service):
        """Test upgrade path when specific role is required"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="admin_panel",
            requested_action="execute",
            user_plan="enterprise",
            user_roles=["user"],  # Missing admin role
            is_developer=False,
            environment="production"
        )
        
        upgrade_path = service.get_upgrade_path(context, ["system_management"])
        
        assert "required_roles" in upgrade_path
        assert "admin" in upgrade_path.get("required_roles", [])
    
    def test_get_upgrade_path_no_upgrade_needed(self, service):
        """Test upgrade path when no upgrade is needed"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="basic_tool",
            requested_action="execute",
            user_plan="pro",
            user_roles=["user"],
            is_developer=False,
            environment="production"
        )
        
        upgrade_path = service.get_upgrade_path(context, ["basic"])
        
        assert upgrade_path["recommended_plan"] is None or upgrade_path["recommended_plan"] == context.user_plan