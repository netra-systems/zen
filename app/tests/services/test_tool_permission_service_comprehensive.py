"""
Comprehensive tests for ToolPermissionService with complete coverage
Tests permissions, rate limiting, business requirements, user plans, and tool availability
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import Dict, List, Any, Set

from app.services.tool_permission_service import ToolPermissionService
from app.schemas.ToolPermission import (
    ToolPermission, ToolExecutionContext, PermissionCheckResult,
    ToolAvailability, PermissionLevel, BusinessRequirement, RateLimit
)
from app.schemas.UserPlan import UserPlan, PlanTier, PLAN_DEFINITIONS


class MockRedisClient:
    """Mock Redis client for testing"""
    def __init__(self):
        self.data = {}
        self.expires = {}
    
    async def get(self, key):
        if key in self.expires and datetime.utcnow() > self.expires[key]:
            del self.data[key]
            del self.expires[key]
            return None
        return self.data.get(key)
    
    async def set(self, key, value, ex=None):
        self.data[key] = str(value)
        if ex:
            self.expires[key] = datetime.utcnow() + timedelta(seconds=ex)
        return True
    
    async def incr(self, key):
        current = int(self.data.get(key, "0"))
        self.data[key] = str(current + 1)
        return current + 1
    
    async def expire(self, key, seconds):
        if key in self.data:
            self.expires[key] = datetime.utcnow() + timedelta(seconds=seconds)
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
        assert "create_thread" in basic_perm.tools
        assert "get_thread_history" in basic_perm.tools
        assert basic_perm.business_requirements.plan_tiers == None  # No plan restriction
    
    def test_analytics_permission_configuration(self, service):
        """Test analytics permission configuration"""
        analytics_perm = service._permission_definitions["analytics"]
        
        assert analytics_perm.name == "analytics"
        assert analytics_perm.level == PermissionLevel.READ
        assert "analyze_workload" in analytics_perm.tools
        assert "pro" in analytics_perm.business_requirements.plan_tiers
        assert "enterprise" in analytics_perm.business_requirements.plan_tiers
        assert analytics_perm.rate_limits.per_hour == 100
        assert analytics_perm.rate_limits.per_day == 1000
    
    def test_data_management_permission_configuration(self, service):
        """Test data management permission configuration"""
        data_perm = service._permission_definitions["data_management"]
        
        assert data_perm.name == "data_management"
        assert data_perm.level == PermissionLevel.WRITE
        assert "generate_synthetic_data" in data_perm.tools
        assert "pro" in data_perm.business_requirements.plan_tiers
        assert "data_operations" in data_perm.business_requirements.feature_flags
        assert data_perm.rate_limits.per_hour == 50
        assert data_perm.rate_limits.per_day == 500
    
    def test_advanced_optimization_permission_configuration(self, service):
        """Test advanced optimization permission configuration"""
        adv_perm = service._permission_definitions["advanced_optimization"]
        
        assert adv_perm.name == "advanced_optimization"
        assert adv_perm.level == PermissionLevel.WRITE
        assert "cost_analyzer" in adv_perm.tools
        assert "multi_objective_optimization" in adv_perm.tools
        assert adv_perm.business_requirements.plan_tiers == ["enterprise"]
        assert "advanced_optimization" in adv_perm.business_requirements.feature_flags
        assert adv_perm.rate_limits.per_hour == 20
        assert adv_perm.rate_limits.per_day == 100
    
    def test_system_management_permission_configuration(self, service):
        """Test system management permission configuration"""
        sys_perm = service._permission_definitions["system_management"]
        
        assert sys_perm.name == "system_management"
        assert sys_perm.level == PermissionLevel.ADMIN
        assert "system_configurator" in sys_perm.tools
        assert "user_admin" in sys_perm.tools
        assert sys_perm.business_requirements.plan_tiers == ["enterprise"]
        assert "admin" in sys_perm.business_requirements.role_requirements
        assert "developer" in sys_perm.business_requirements.role_requirements
    
    def test_developer_tools_permission_configuration(self, service):
        """Test developer tools permission configuration"""
        dev_perm = service._permission_definitions["developer_tools"]
        
        assert dev_perm.name == "developer_tools"
        assert dev_perm.level == PermissionLevel.ADMIN
        assert "debug_panel" in dev_perm.tools
        assert "impersonation_tool" in dev_perm.tools
        assert dev_perm.business_requirements.developer_status == True
        assert "development" in dev_perm.business_requirements.environment
        assert "staging" in dev_perm.business_requirements.environment


@pytest.mark.asyncio
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
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.PRO,
            features=PLAN_DEFINITIONS[PlanTier.PRO].features
        )
        
        permissions = service._get_user_permissions(sample_context, user_plan)
        
        assert isinstance(permissions, set)
        # Should include permissions from PRO plan
        plan_permissions = user_plan.features.permissions
        for perm in plan_permissions:
            assert perm in permissions
    
    def test_get_user_permissions_wildcard(self, service, sample_context):
        """Test user permissions with wildcard (*) permission"""
        from app.schemas.UserPlan import PlanFeatures
        
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.ENTERPRISE,
            features=PlanFeatures(permissions={"*"})  # Wildcard permission
        )
        
        permissions = service._get_user_permissions(sample_context, user_plan)
        
        # Should include all permission definitions
        expected_perms = set(service._permission_definitions.keys())
        assert expected_perms.issubset(permissions)
    
    def test_get_user_permissions_developer(self, service, developer_context):
        """Test user permissions for developer"""
        user_plan = UserPlan(
            user_id="dev_user",
            tier=PlanTier.FREE,
            features=PLAN_DEFINITIONS[PlanTier.FREE].features
        )
        
        permissions = service._get_user_permissions(developer_context, user_plan)
        
        # Should include developer_tools permission
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
        # Add a tool to multiple permission definitions for testing
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
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.PRO,
            features=PLAN_DEFINITIONS[PlanTier.PRO].features
        )
        sample_context.user_plan = "pro"
        
        result = service._has_permission("analytics", user_permissions, sample_context, user_plan)
        
        assert result == True
    
    def test_has_permission_no_permission(self, service, sample_context):
        """Test has_permission without required permission"""
        user_permissions = {"basic"}
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.FREE,
            features=PLAN_DEFINITIONS[PlanTier.FREE].features
        )
        
        result = service._has_permission("analytics", user_permissions, sample_context, user_plan)
        
        assert result == False
    
    def test_has_permission_with_business_requirements_failed(self, service, sample_context):
        """Test has_permission with failed business requirements"""
        user_permissions = {"analytics"}
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.FREE,  # Analytics requires PRO or higher
            features=PLAN_DEFINITIONS[PlanTier.FREE].features
        )
        sample_context.user_plan = "free"
        
        result = service._has_permission("analytics", user_permissions, sample_context, user_plan)
        
        assert result == False


class TestBusinessRequirements:
    """Test business requirements checking"""
    
    def test_check_business_requirements_plan_tier_pass(self, service, sample_context):
        """Test business requirements check with valid plan tier"""
        requirements = BusinessRequirement(plan_tiers=["pro", "enterprise"])
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.PRO,
            features=PLAN_DEFINITIONS[PlanTier.PRO].features
        )
        sample_context.user_plan = "pro"
        
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        
        assert result == True
    
    def test_check_business_requirements_plan_tier_fail(self, service, sample_context):
        """Test business requirements check with invalid plan tier"""
        requirements = BusinessRequirement(plan_tiers=["pro", "enterprise"])
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.FREE,
            features=PLAN_DEFINITIONS[PlanTier.FREE].features
        )
        sample_context.user_plan = "free"
        
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        
        assert result == False
    
    def test_check_business_requirements_feature_flags_pass(self, service, sample_context):
        """Test business requirements check with valid feature flags"""
        requirements = BusinessRequirement(feature_flags=["data_operations"])
        
        from app.schemas.UserPlan import PlanFeatures
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.PRO,
            features=PlanFeatures(feature_flags={"data_operations"})
        )
        
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        
        assert result == True
    
    def test_check_business_requirements_feature_flags_fail(self, service, sample_context):
        """Test business requirements check with missing feature flags"""
        requirements = BusinessRequirement(feature_flags=["advanced_optimization"])
        
        from app.schemas.UserPlan import PlanFeatures
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.PRO,
            features=PlanFeatures(feature_flags={"data_operations"})  # Missing advanced_optimization
        )
        
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        
        assert result == False
    
    def test_check_business_requirements_role_pass(self, service, sample_context):
        """Test business requirements check with valid role"""
        requirements = BusinessRequirement(role_requirements=["admin"])
        sample_context.user_roles = ["admin", "user"]
        
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.ENTERPRISE,
            features=PLAN_DEFINITIONS[PlanTier.ENTERPRISE].features
        )
        
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        
        assert result == True
    
    def test_check_business_requirements_role_fail(self, service, sample_context):
        """Test business requirements check with missing role"""
        requirements = BusinessRequirement(role_requirements=["admin"])
        sample_context.user_roles = ["user"]  # Missing admin role
        
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.ENTERPRISE,
            features=PLAN_DEFINITIONS[PlanTier.ENTERPRISE].features
        )
        
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        
        assert result == False
    
    def test_check_business_requirements_developer_status_pass(self, service, developer_context):
        """Test business requirements check with valid developer status"""
        requirements = BusinessRequirement(developer_status=True)
        
        user_plan = UserPlan(
            user_id="dev_user",
            tier=PlanTier.ENTERPRISE,
            features=PLAN_DEFINITIONS[PlanTier.ENTERPRISE].features
        )
        
        result = service._check_business_requirements(requirements, developer_context, user_plan)
        
        assert result == True
    
    def test_check_business_requirements_developer_status_fail(self, service, sample_context):
        """Test business requirements check with invalid developer status"""
        requirements = BusinessRequirement(developer_status=True)
        sample_context.is_developer = False  # Not a developer
        
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.ENTERPRISE,
            features=PLAN_DEFINITIONS[PlanTier.ENTERPRISE].features
        )
        
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        
        assert result == False
    
    def test_check_business_requirements_environment_pass(self, service, developer_context):
        """Test business requirements check with valid environment"""
        requirements = BusinessRequirement(environment=["development", "staging"])
        
        user_plan = UserPlan(
            user_id="dev_user",
            tier=PlanTier.ENTERPRISE,
            features=PLAN_DEFINITIONS[PlanTier.ENTERPRISE].features
        )
        
        result = service._check_business_requirements(requirements, developer_context, user_plan)
        
        assert result == True
    
    def test_check_business_requirements_environment_fail(self, service, sample_context):
        """Test business requirements check with invalid environment"""
        requirements = BusinessRequirement(environment=["development", "staging"])
        sample_context.environment = "production"  # Not in allowed environments
        
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.ENTERPRISE,
            features=PLAN_DEFINITIONS[PlanTier.ENTERPRISE].features
        )
        
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        
        assert result == False
    
    def test_check_business_requirements_all_conditions(self, service, developer_context):
        """Test business requirements check with all conditions"""
        requirements = BusinessRequirement(
            plan_tiers=["enterprise"],
            feature_flags=["advanced_features"],
            role_requirements=["developer"],
            developer_status=True,
            environment=["development"]
        )
        
        from app.schemas.UserPlan import PlanFeatures
        user_plan = UserPlan(
            user_id="dev_user",
            tier=PlanTier.ENTERPRISE,
            features=PlanFeatures(feature_flags={"advanced_features"})
        )
        developer_context.user_plan = "enterprise"
        
        result = service._check_business_requirements(requirements, developer_context, user_plan)
        
        assert result == True


@pytest.mark.asyncio
class TestRateLimiting:
    """Test rate limiting functionality"""
    
    async def test_check_rate_limits_no_limits(self, service, sample_context):
        """Test rate limit check when no limits are defined"""
        result = await service._check_rate_limits(sample_context, [])
        
        assert result["allowed"] == True
        assert result["limits"] == {}
    
    async def test_check_rate_limits_within_limit(self, service_with_redis, sample_context):
        """Test rate limit check within limits"""
        permissions = ["analytics"]  # Has rate limits defined
        
        result = await service_with_redis._check_rate_limits(sample_context, permissions)
        
        assert result["allowed"] == True
        assert "limits" in result
        assert result["limits"]["per_hour"] == 100
        assert result["limits"]["per_day"] == 1000
    
    async def test_check_rate_limits_exceeded(self, service_with_redis, sample_context):
        """Test rate limit check when limit is exceeded"""
        permissions = ["analytics"]
        
        # Simulate usage that exceeds limit
        now = datetime.utcnow()
        hour_key = f"usage:{sample_context.user_id}:{sample_context.tool_name}:{now.strftime('%Y%m%d%H')}"
        
        # Set usage to exceed hourly limit (100)
        await service_with_redis.redis.set(hour_key, "101")
        
        result = await service_with_redis._check_rate_limits(sample_context, permissions)
        
        assert result["allowed"] == False
        assert "Exceeded per_hour limit" in result["message"]
        assert result["current_usage"] == 101
        assert result["limit"] == 100
    
    async def test_check_rate_limits_multiple_periods(self, service_with_redis, sample_context):
        """Test rate limit check across multiple time periods"""
        permissions = ["data_management"]  # Has per_hour=50, per_day=500
        
        # Should check both hourly and daily limits
        result = await service_with_redis._check_rate_limits(sample_context, permissions)
        
        assert result["allowed"] == True
        limits = result["limits"]
        assert limits["per_hour"] == 50
        assert limits["per_day"] == 500
    
    async def test_get_usage_count_minute(self, service_with_redis):
        """Test getting usage count for minute period"""
        now = datetime.utcnow()
        key = f"usage:user123:tool_test:{now.strftime('%Y%m%d%H%M')}"
        await service_with_redis.redis.set(key, "5")
        
        count = await service_with_redis._get_usage_count("user123", "tool_test", "minute")
        
        assert count == 5
    
    async def test_get_usage_count_hour(self, service_with_redis):
        """Test getting usage count for hour period"""
        now = datetime.utcnow()
        key = f"usage:user123:tool_test:{now.strftime('%Y%m%d%H')}"
        await service_with_redis.redis.set(key, "25")
        
        count = await service_with_redis._get_usage_count("user123", "tool_test", "hour")
        
        assert count == 25
    
    async def test_get_usage_count_day(self, service_with_redis):
        """Test getting usage count for day period"""
        now = datetime.utcnow()
        key = f"usage:user123:tool_test:{now.strftime('%Y%m%d')}"
        await service_with_redis.redis.set(key, "150")
        
        count = await service_with_redis._get_usage_count("user123", "tool_test", "day")
        
        assert count == 150
    
    async def test_get_usage_count_no_redis(self, service):
        """Test getting usage count when Redis is not available"""
        count = await service._get_usage_count("user123", "tool_test", "day")
        
        assert count == 0
    
    async def test_get_usage_count_invalid_period(self, service_with_redis):
        """Test getting usage count with invalid period"""
        count = await service_with_redis._get_usage_count("user123", "tool_test", "invalid")
        
        assert count == 0
    
    async def test_get_usage_count_redis_error(self, service_with_redis):
        """Test getting usage count when Redis raises error"""
        # Mock Redis to raise exception
        async def failing_get(key):
            raise Exception("Redis connection failed")
        
        service_with_redis.redis.get = failing_get
        
        count = await service_with_redis._get_usage_count("user123", "tool_test", "day")
        
        assert count == 0  # Should return 0 on error


@pytest.mark.asyncio
class TestRecordToolUsage:
    """Test tool usage recording functionality"""
    
    async def test_record_tool_usage(self, service_with_redis):
        """Test recording tool usage"""
        await service_with_redis.record_tool_usage(
            "user123",
            "test_tool",
            250,  # execution time
            "success"
        )
        
        # Should have updated all period counters
        now = datetime.utcnow()
        minute_key = f"usage:user123:test_tool:{now.strftime('%Y%m%d%H%M')}"
        hour_key = f"usage:user123:test_tool:{now.strftime('%Y%m%d%H')}"
        day_key = f"usage:user123:test_tool:{now.strftime('%Y%m%d')}"
        
        minute_count = await service_with_redis.redis.get(minute_key)
        hour_count = await service_with_redis.redis.get(hour_key)
        day_count = await service_with_redis.redis.get(day_key)
        
        assert minute_count == "1"
        assert hour_count == "1"
        assert day_count == "1"
    
    async def test_record_tool_usage_multiple_calls(self, service_with_redis):
        """Test recording multiple tool usages"""
        for i in range(3):
            await service_with_redis.record_tool_usage(
                "user123",
                "test_tool",
                100 + i * 50,
                "success"
            )
        
        now = datetime.utcnow()
        day_key = f"usage:user123:test_tool:{now.strftime('%Y%m%d')}"
        day_count = await service_with_redis.redis.get(day_key)
        
        assert day_count == "3"
    
    async def test_record_tool_usage_no_redis(self, service):
        """Test recording tool usage when Redis is not available"""
        # Should not raise exception
        await service.record_tool_usage("user123", "test_tool", 100, "success")
    
    async def test_record_tool_usage_redis_error(self, service_with_redis):
        """Test recording tool usage when Redis raises error"""
        # Mock Redis incr to raise exception
        async def failing_incr(key):
            raise Exception("Redis connection failed")
        
        service_with_redis.redis.incr = failing_incr
        
        # Should handle error gracefully
        await service_with_redis.record_tool_usage("user123", "test_tool", 100, "success")


@pytest.mark.asyncio
class TestCheckToolPermission:
    """Test main tool permission checking"""
    
    async def test_check_tool_permission_allowed(self, service):
        """Test tool permission check when allowed"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="create_thread",  # Basic tool
            requested_action="execute",
            user_plan="free",
            user_roles=["user"],
            is_developer=False
        )
        
        with patch.object(service, '_get_user_plan') as mock_get_plan:
            mock_get_plan.return_value = UserPlan(
                user_id="test_user",
                tier=PlanTier.FREE,
                features=PLAN_DEFINITIONS[PlanTier.FREE].features
            )
            
            result = await service.check_tool_permission(context)
        
        assert result.allowed == True
        assert "basic" in result.required_permissions
    
    async def test_check_tool_permission_denied_missing_permissions(self, service):
        """Test tool permission check when permission is missing"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="analyze_workload",  # Requires analytics permission + pro plan
            requested_action="execute",
            user_plan="free",  # Free plan doesn't have analytics
            user_roles=["user"],
            is_developer=False
        )
        
        with patch.object(service, '_get_user_plan') as mock_get_plan:
            mock_get_plan.return_value = UserPlan(
                user_id="test_user",
                tier=PlanTier.FREE,
                features=PLAN_DEFINITIONS[PlanTier.FREE].features
            )
            
            result = await service.check_tool_permission(context)
        
        assert result.allowed == False
        assert "Missing permissions" in result.reason
        assert "analytics" in result.missing_permissions
        assert result.upgrade_path != None
    
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
        
        # Set usage to exceed limit
        now = datetime.utcnow()
        hour_key = f"usage:{context.user_id}:{context.tool_name}:{now.strftime('%Y%m%d%H')}"
        await service_with_redis.redis.set(hour_key, "101")  # Exceeds 100/hour limit
        
        with patch.object(service_with_redis, '_get_user_plan') as mock_get_plan:
            mock_get_plan.return_value = UserPlan(
                user_id="test_user",
                tier=PlanTier.PRO,
                features=PLAN_DEFINITIONS[PlanTier.PRO].features
            )
            
            result = await service_with_redis.check_tool_permission(context)
        
        assert result.allowed == False
        assert "Rate limit exceeded" in result.reason
        assert result.rate_limit_status["allowed"] == False
    
    async def test_check_tool_permission_no_requirements(self, service):
        """Test tool permission check for tool with no requirements"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="unknown_tool",  # No requirements defined
            requested_action="execute",
            user_plan="free",
            user_roles=["user"],
            is_developer=False
        )
        
        result = await service.check_tool_permission(context)
        
        assert result.allowed == True
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
        
        # Mock _get_user_plan to raise exception
        with patch.object(service, '_get_user_plan', side_effect=Exception("Test error")):
            result = await service.check_tool_permission(context)
        
        assert result.allowed == False
        assert "Permission check failed" in result.reason


@pytest.mark.asyncio
class TestGetUserToolAvailability:
    """Test user tool availability functionality"""
    
    async def test_get_user_tool_availability(self, service):
        """Test getting tool availability for user"""
        user_id = "test_user"
        tool_registry = {
            "create_thread": {
                "category": "basic",
                "description": "Create a new thread"
            },
            "analyze_workload": {
                "category": "analytics",
                "description": "Analyze workload performance"
            },
            "debug_panel": {
                "category": "development",
                "description": "Developer debug panel"
            }
        }
        
        with patch.object(service, '_get_user_plan') as mock_get_plan:
            mock_get_plan.return_value = UserPlan(
                user_id=user_id,
                tier=PlanTier.PRO,
                features=PLAN_DEFINITIONS[PlanTier.PRO].features
            )
            
            with patch.object(service, '_get_usage_count', return_value=5):
                availability = await service.get_user_tool_availability(user_id, tool_registry)
        
        assert len(availability) == 3
        
        # Check basic tool (should be available)
        basic_tool = next(tool for tool in availability if tool.tool_name == "create_thread")
        assert basic_tool.available == True
        assert basic_tool.category == "basic"
        
        # Check analytics tool (should be available for PRO user)
        analytics_tool = next(tool for tool in availability if tool.tool_name == "analyze_workload")
        assert analytics_tool.available == True
        assert analytics_tool.usage_today == 5
        
        # Check debug tool (should not be available for non-developer)
        debug_tool = next(tool for tool in availability if tool.tool_name == "debug_panel")
        assert debug_tool.available == False
        assert debug_tool.upgrade_required == None  # No upgrade path for dev tools
    
    async def test_get_user_tool_availability_with_rate_limits(self, service_with_redis):
        """Test tool availability including rate limit information"""
        user_id = "test_user"
        tool_registry = {
            "analyze_workload": {
                "category": "analytics",
                "description": "Analyze workload performance"
            }
        }
        
        with patch.object(service_with_redis, '_get_user_plan') as mock_get_plan:
            mock_get_plan.return_value = UserPlan(
                user_id=user_id,
                tier=PlanTier.PRO,
                features=PLAN_DEFINITIONS[PlanTier.PRO].features
            )
            
            availability = await service_with_redis.get_user_tool_availability(user_id, tool_registry)
        
        assert len(availability) == 1
        tool = availability[0]
        
        assert tool.available == True
        assert tool.rate_limits != None
        assert tool.rate_limits.per_hour == 100
        assert tool.rate_limits.per_day == 1000
    
    async def test_get_user_tool_availability_error_handling(self, service):
        """Test tool availability error handling"""
        user_id = "test_user"
        tool_registry = {"test_tool": {"category": "test"}}
        
        # Mock _get_user_plan to raise exception
        with patch.object(service, '_get_user_plan', side_effect=Exception("Test error")):
            availability = await service.get_user_tool_availability(user_id, tool_registry)
        
        assert availability == []


class TestUpgradePath:
    """Test upgrade path determination"""
    
    def test_get_upgrade_path_pro_required(self, service):
        """Test upgrade path when PRO plan is required"""
        missing_permissions = ["analytics"]
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.FREE,
            features=PLAN_DEFINITIONS[PlanTier.FREE].features
        )
        
        upgrade_path = service._get_upgrade_path(missing_permissions, user_plan)
        
        assert upgrade_path == "Pro"
    
    def test_get_upgrade_path_enterprise_required(self, service):
        """Test upgrade path when Enterprise plan is required"""
        missing_permissions = ["advanced_optimization"]
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.PRO,
            features=PLAN_DEFINITIONS[PlanTier.PRO].features
        )
        
        upgrade_path = service._get_upgrade_path(missing_permissions, user_plan)
        
        assert upgrade_path == "Enterprise"
    
    def test_get_upgrade_path_no_upgrade_available(self, service):
        """Test upgrade path when no upgrade is available"""
        missing_permissions = ["nonexistent_permission"]
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.FREE,
            features=PLAN_DEFINITIONS[PlanTier.FREE].features
        )
        
        upgrade_path = service._get_upgrade_path(missing_permissions, user_plan)
        
        assert upgrade_path == None
    
    def test_get_upgrade_path_already_highest_tier(self, service):
        """Test upgrade path when user already has highest tier"""
        missing_permissions = ["analytics"]
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.DEVELOPER,  # Highest tier
            features=PLAN_DEFINITIONS[PlanTier.DEVELOPER].features
        )
        
        upgrade_path = service._get_upgrade_path(missing_permissions, user_plan)
        
        # Should still suggest appropriate tier
        assert upgrade_path == "Pro"
    
    def test_get_upgrade_path_for_rate_limits_free(self, service):
        """Test upgrade path for rate limits from free plan"""
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.FREE,
            features=PLAN_DEFINITIONS[PlanTier.FREE].features
        )
        
        upgrade_path = service._get_upgrade_path_for_rate_limits(user_plan)
        
        assert upgrade_path == "Pro"
    
    def test_get_upgrade_path_for_rate_limits_pro(self, service):
        """Test upgrade path for rate limits from pro plan"""
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.PRO,
            features=PLAN_DEFINITIONS[PlanTier.PRO].features
        )
        
        upgrade_path = service._get_upgrade_path_for_rate_limits(user_plan)
        
        assert upgrade_path == "Enterprise"
    
    def test_get_upgrade_path_for_rate_limits_enterprise(self, service):
        """Test upgrade path for rate limits from enterprise plan"""
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.ENTERPRISE,
            features=PLAN_DEFINITIONS[PlanTier.ENTERPRISE].features
        )
        
        upgrade_path = service._get_upgrade_path_for_rate_limits(user_plan)
        
        assert upgrade_path == None  # No higher tier available


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple features"""
    
    @pytest.mark.asyncio
    async def test_developer_access_in_production(self, service):
        """Test developer tool access in production environment"""
        context = ToolExecutionContext(
            user_id="dev_user",
            tool_name="debug_panel",
            requested_action="execute",
            user_plan="enterprise",
            user_roles=["developer", "admin"],
            is_developer=True,
            environment="production"  # Production environment
        )
        
        with patch.object(service, '_get_user_plan') as mock_get_plan:
            mock_get_plan.return_value = UserPlan(
                user_id="dev_user",
                tier=PlanTier.ENTERPRISE,
                features=PLAN_DEFINITIONS[PlanTier.ENTERPRISE].features
            )
            
            result = await service.check_tool_permission(context)
        
        # Should be denied because developer tools only allowed in dev/staging
        assert result.allowed == False
        assert "developer_tools" in result.missing_permissions
    
    @pytest.mark.asyncio
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
        
        with patch.object(service, '_get_user_plan') as mock_get_plan:
            mock_get_plan.return_value = UserPlan(
                user_id="free_user",
                tier=PlanTier.FREE,
                features=PLAN_DEFINITIONS[PlanTier.FREE].features
            )
            
            result = await service.check_tool_permission(context)
        
        assert result.allowed == False
        assert "advanced_optimization" in result.missing_permissions
        assert result.upgrade_path == "Enterprise"
    
    @pytest.mark.asyncio
    async def test_pro_user_with_heavy_usage(self, service_with_redis):
        """Test pro user with heavy tool usage"""
        context = ToolExecutionContext(
            user_id="heavy_user",
            tool_name="generate_synthetic_data",
            requested_action="execute",
            user_plan="pro",
            user_roles=["user"],
            is_developer=False
        )
        
        # Set usage near daily limit for data_management (500/day)
        now = datetime.utcnow()
        day_key = f"usage:{context.user_id}:{context.tool_name}:{now.strftime('%Y%m%d')}"
        await service_with_redis.redis.set(day_key, "499")  # Just under limit
        
        with patch.object(service_with_redis, '_get_user_plan') as mock_get_plan:
            mock_get_plan.return_value = UserPlan(
                user_id="heavy_user",
                tier=PlanTier.PRO,
                features=PLAN_DEFINITIONS[PlanTier.PRO].features
            )
            
            result = await service_with_redis.check_tool_permission(context)
        
        # Should be allowed (just under limit)
        assert result.allowed == True
        assert result.rate_limit_status["current_usage"] == 499
        
        # Record one more usage to exceed limit
        await service_with_redis.record_tool_usage("heavy_user", "generate_synthetic_data", 1000, "success")
        
        # Now should be denied
        result2 = await service_with_redis.check_tool_permission(context)
        assert result2.allowed == False
        assert "Rate limit exceeded" in result2.reason


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.asyncio
    async def test_empty_tool_registry(self, service):
        """Test tool availability with empty tool registry"""
        availability = await service.get_user_tool_availability("test_user", {})
        
        assert availability == []
    
    def test_permission_definitions_immutability(self, service):
        """Test that permission definitions cannot be easily modified"""
        original_basic_tools = service._permission_definitions["basic"].tools.copy()
        
        # Attempt to modify
        service._permission_definitions["basic"].tools.append("malicious_tool")
        
        # Create new service instance
        new_service = ToolPermissionService()
        
        # Should have original definitions (not modified ones)
        assert len(new_service._permission_definitions["basic"].tools) == len(original_basic_tools)
    
    def test_business_requirements_edge_cases(self, service):
        """Test business requirements with edge case values"""
        # Empty requirements should always pass
        empty_req = BusinessRequirement()
        context = ToolExecutionContext(
            user_id="test",
            tool_name="test",
            requested_action="test",
            user_plan="free",
            user_roles=[],
            is_developer=False
        )
        user_plan = UserPlan(
            user_id="test",
            tier=PlanTier.FREE,
            features=PLAN_DEFINITIONS[PlanTier.FREE].features
        )
        
        result = service._check_business_requirements(empty_req, context, user_plan)
        assert result == True
    
    @pytest.mark.asyncio
    async def test_rate_limit_key_generation_edge_cases(self, service_with_redis):
        """Test rate limit key generation with edge case inputs"""
        # Test with special characters in user_id and tool_name
        special_user_id = "user@#$%^&*()"
        special_tool_name = "tool-with-dashes_and_underscores.dots"
        
        count = await service_with_redis._get_usage_count(special_user_id, special_tool_name, "day")
        
        # Should not raise exception
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limit_updates(self, service_with_redis):
        """Test concurrent rate limit updates"""
        user_id = "concurrent_user"
        tool_name = "concurrent_tool"
        
        # Simulate concurrent usage recording
        tasks = []
        for i in range(10):
            task = service_with_redis.record_tool_usage(user_id, tool_name, 100, "success")
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Should have recorded all 10 usages
        count = await service_with_redis._get_usage_count(user_id, tool_name, "day")
        assert count == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])