"""
Tool Permission Test Helper Functions
Extract common setup, assertion, and teardown logic for  <= 8 line functions
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Set
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.schemas.tool_permission import (
    BusinessRequirement,
    PermissionCheckResult,
    PermissionLevel,
    RateLimit,
    ToolAvailability,
    ToolExecutionContext,
    ToolPermission,
)
from netra_backend.app.schemas.user_plan import PLAN_DEFINITIONS, PlanTier, UserPlan
from netra_backend.app.services.tool_permission_service import ToolPermissionService
# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

# MockRedisClient now imported from canonical test_framework location
# OLD class MockRedisClient:
# Removed - using canonical MockRedisClient from test_framework.mocks

# Setup Helpers
def create_sample_context():
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

def create_developer_context():
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

def create_user_plan(tier=PlanTier.FREE, user_id="test_user"):
    """Create UserPlan with specified tier"""
    return UserPlan(
        user_id=user_id,
        tier=tier,
        features=PLAN_DEFINITIONS[tier].features
    )

def create_business_requirements(plan_tiers=None, feature_flags=None, role_requirements=None,
                               developer_status=None, environment=None):
    """Create BusinessRequirement object with specified values"""
    return BusinessRequirement(
        plan_tiers=plan_tiers,
        feature_flags=feature_flags,
        role_requirements=role_requirements,
        developer_status=developer_status,
        environment=environment
    )

def create_tool_registry_sample():
    """Create sample tool registry for testing"""
    return {
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

def setup_mock_user_plan(service, user_plan):
    """Setup mock for _get_user_plan method"""
    return patch.object(service, '_get_user_plan', return_value=user_plan)

def setup_mock_usage_count(service, count):
    """Setup mock for _get_usage_count method"""
    return patch.object(service, '_get_usage_count', return_value=count)

async def setup_redis_usage(redis_client, user_id, tool_name, usage_count, period="day"):
    """Setup Redis usage count for testing"""
    now = datetime.now(UTC)
    if period == "minute":
        key = f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d%H%M')}"
    elif period == "hour":
        key = f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d%H')}"
    else:  # day
        key = f"usage:{user_id}:{tool_name}:{now.strftime('%Y%m%d')}"
    
    await redis_client.set(key, str(usage_count))
    return key

def create_failing_redis_method(method_name, error_message="Redis connection failed"):
    """Create failing Redis method for error testing"""
    async def failing_method(*method_args, **method_kwargs):
        raise Exception(error_message)
    return failing_method

# Assertion Helpers
def assert_permission_allowed(result):
    """Assert permission check result is allowed"""
    assert result.allowed == True

def assert_permission_denied(result):
    """Assert permission check result is denied"""
    assert result.allowed == False

def assert_permission_has_upgrade_path(result, expected_path):
    """Assert permission result has expected upgrade path"""
    assert result.upgrade_path == expected_path

def assert_missing_permissions(result, expected_permissions):
    """Assert result has expected missing permissions"""
    for perm in expected_permissions:
        assert perm in result.missing_permissions

def assert_rate_limit_status(result, expected_allowed, expected_usage=None):
    """Assert rate limit status in permission result"""
    assert result.rate_limit_status["allowed"] == expected_allowed
    if expected_usage is not None:
        assert result.rate_limit_status["current_usage"] == expected_usage

def assert_tool_availability(availability, tool_name, expected_available):
    """Assert tool availability status"""
    tool = next(t for t in availability if t.tool_name == tool_name)
    assert tool.available == expected_available

def assert_service_initialization(service, has_redis=False, expected_permissions=None):
    """Assert service initialization state"""
    if has_redis:
        assert service.redis is not None
    else:
        assert service.redis is None
    
    assert service.permissions_cache == {}
    assert hasattr(service, '_permission_definitions')
    assert len(service._permission_definitions) > 0
    
    if expected_permissions:
        for perm_name in expected_permissions:
            assert perm_name in service._permission_definitions

def assert_business_requirements_result(result, expected):
    """Assert business requirements check result"""
    assert result == expected

def assert_permission_definition_properties(definition, name, level, tools, plan_tiers=None):
    """Assert permission definition properties"""
    assert definition.name == name
    assert definition.level == level
    for tool in tools:
        assert tool in definition.tools
    if plan_tiers:
        assert definition.business_requirements.plan_tiers == plan_tiers

def assert_redis_usage_count(count, expected):
    """Assert Redis usage count matches expected"""
    assert count == expected

def assert_rate_limits_within_bounds(result, hourly_limit, daily_limit):
    """Assert rate limits are within expected bounds"""
    limits = result["limits"]
    assert limits["per_hour"] == hourly_limit
    assert limits["per_day"] == daily_limit

def assert_tool_registry_availability(availability, expected_count):
    """Assert tool availability count matches expected"""
    assert len(availability) == expected_count

# Test Data Helpers
def get_permission_test_data():
    """Get standard permission test data"""
    return {
        "basic_tools": ["create_thread", "get_thread_history"],
        "analytics_tools": ["analyze_workload"],
        "data_mgmt_tools": ["generate_synthetic_data"],
        "advanced_tools": ["cost_analyzer", "multi_objective_optimization"],
        "system_tools": ["system_configurator", "user_admin"],
        "dev_tools": ["debug_panel", "impersonation_tool"]
    }

def get_rate_limit_test_data():
    """Get rate limit test data"""
    return {
        "analytics": {"per_hour": 100, "per_day": 1000},
        "data_management": {"per_hour": 50, "per_day": 500},
        "advanced_optimization": {"per_hour": 20, "per_day": 100}
    }

# Complex Setup Helpers
async def setup_rate_limit_test(service_with_redis, context, usage_count, period="hour"):
    """Setup rate limit test with specified usage"""
    now = datetime.now(UTC)
    if period == "hour":
        key = f"usage:{context.user_id}:{context.tool_name}:{now.strftime('%Y%m%d%H')}"
    else:  # day
        key = f"usage:{context.user_id}:{context.tool_name}:{now.strftime('%Y%m%d')}"
    
    await service_with_redis.redis.set(key, str(usage_count))
    return key

async def run_concurrent_usage_recording(service, user_id, tool_name, count=10):
    """Run concurrent tool usage recording for testing"""
    tasks = []
    for i in range(count):
        task = service.record_tool_usage(user_id, tool_name, 100, "success")
        tasks.append(task)
    
    await asyncio.gather(*tasks)

def create_context_with_special_chars():
    """Create context with special characters for edge case testing"""
    return ToolExecutionContext(
        user_id="user@#$%^&*()",
        tool_name="tool-with-dashes_and_underscores.dots",
        requested_action="execute",
        user_plan="pro",
        user_roles=["user"],
        is_developer=False,
        environment="production"
    )

def create_heavy_usage_context():
    """Create context for heavy usage testing"""
    return ToolExecutionContext(
        user_id="heavy_user",
        tool_name="generate_synthetic_data",
        requested_action="execute",
        user_plan="pro",
        user_roles=["user"],
        is_developer=False,
        environment="production"
    )