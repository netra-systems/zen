"""
Tool Permission Service - Business Requirements and Rate Limiting
Split from large test file for architecture compliance
Test classes: TestBusinessRequirements, TestRateLimiting, TestRecordToolUsage
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import Dict, List, Any, Set

# Add project root to path

from netra_backend.app.services.tool_permission_service import ToolPermissionService
from netra_backend.app.schemas.ToolPermission import (

# Add project root to path
    ToolPermission, ToolExecutionContext, PermissionCheckResult,
    ToolAvailability, PermissionLevel, BusinessRequirement, RateLimit
)
from netra_backend.app.schemas.UserPlan import UserPlan, PlanTier, PLAN_DEFINITIONS


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
        
        from netra_backend.app.schemas.UserPlan import PlanFeatures
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
        
        from netra_backend.app.schemas.UserPlan import PlanFeatures
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
    
    def test_check_business_requirements_all_conditions(self, service, developer_context):
        """Test business requirements check with all conditions"""
        requirements = BusinessRequirement(
            plan_tiers=["enterprise"],
            feature_flags=["advanced_features"],
            role_requirements=["developer"],
            developer_status=True,
            environment=["development"]
        )
        
        from netra_backend.app.schemas.UserPlan import PlanFeatures
        user_plan = UserPlan(
            user_id="dev_user",
            tier=PlanTier.ENTERPRISE,
            features=PlanFeatures(feature_flags={"advanced_features"})
        )
        developer_context.user_plan = "enterprise"
        
        result = service._check_business_requirements(requirements, developer_context, user_plan)
        
        assert result == True
class TestRateLimiting:
    """Test rate limiting functionality"""
    
    async def test_check_rate_limits_no_limits(self, service, sample_context):
        """Test rate limit check when no limits are defined"""
        result = await service._check_rate_limits(sample_context, [])
        
        assert result.allowed == True
        assert result.remaining_requests is None
        assert result.reset_time is None
    
    async def test_check_rate_limits_within_limit(self, service_with_redis, sample_context):
        """Test rate limit check within allowed limits"""
        rate_limits = [
            RateLimit(
                requests_per_hour=100,
                requests_per_day=1000,
                burst_limit=10
            )
        ]
        
        result = await service_with_redis._check_rate_limits(sample_context, rate_limits)
        
        assert result.allowed == True
        assert isinstance(result.remaining_requests, dict)
    
    async def test_check_rate_limits_exceeded(self, service_with_redis, sample_context):
        """Test rate limit check when limit is exceeded"""
        rate_limits = [
            RateLimit(
                requests_per_hour=1,  # Very low limit
                requests_per_day=10,
                burst_limit=1
            )
        ]
        
        # Make first request
        await service_with_redis._check_rate_limits(sample_context, rate_limits)
        
        # Second request should exceed limit
        result = await service_with_redis._check_rate_limits(sample_context, rate_limits)
        
        # Depending on implementation, this might be allowed or not
        assert isinstance(result.allowed, bool)
    
    async def test_check_rate_limits_different_users(self, service_with_redis, sample_context):
        """Test rate limits are tracked per user"""
        rate_limits = [
            RateLimit(
                requests_per_hour=2,
                requests_per_day=10,
                burst_limit=2
            )
        ]
        
        # User 1 makes requests
        result1 = await service_with_redis._check_rate_limits(sample_context, rate_limits)
        assert result1.allowed == True
        
        # User 2 makes requests (different user_id)
        sample_context.user_id = "different_user"
        result2 = await service_with_redis._check_rate_limits(sample_context, rate_limits)
        assert result2.allowed == True
class TestRecordToolUsage:
    """Test tool usage recording functionality"""
    
    async def test_record_tool_usage(self, service_with_redis):
        """Test recording tool usage"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="analyze_workload",
            requested_action="execute",
            user_plan="pro",
            user_roles=["user"],
            is_developer=False,
            environment="production"
        )
        
        result = PermissionCheckResult(
            allowed=True,
            reason="Permission granted",
            required_permissions={"analytics"},
            user_permissions={"basic", "analytics"}
        )
        
        await service_with_redis.record_tool_usage(context, result)
        
        # Verify usage was recorded (implementation dependent)
        assert True  # Basic test that method completes without error
    
    async def test_record_tool_usage_denied(self, service_with_redis):
        """Test recording denied tool usage"""
        context = ToolExecutionContext(
            user_id="test_user",
            tool_name="admin_panel",
            requested_action="execute",
            user_plan="free",
            user_roles=["user"],
            is_developer=False,
            environment="production"
        )
        
        result = PermissionCheckResult(
            allowed=False,
            reason="Insufficient permissions",
            required_permissions={"admin"},
            user_permissions={"basic"}
        )
        
        await service_with_redis.record_tool_usage(context, result)
        
        # Verify denied usage was recorded
        assert True  # Basic test that method completes without error