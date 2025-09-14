"""Unit tests for UnifiedToolPermissionLayer - Centralized tool security and access control.

Business Value Justification (BVJ):
- Segment: Platform/Security - Access Control & Rate Limiting
- Business Goal: Security Compliance & System Protection
- Value Impact: Ensures secure tool access with proper authorization and resource limits
- Strategic Impact: Protects $500K+ ARR by preventing abuse and ensuring stable service

CRITICAL: Tests validate comprehensive tool permission system including RBAC, rate limiting,
quota enforcement, and security policy validation. All tests use SSOT patterns.
"""

import asyncio
import time
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Set
from unittest.mock import MagicMock, Mock, patch

from netra_backend.app.agents.tool_permission_layer import (
    UnifiedToolPermissionLayer,
    ToolPermissionPolicy,
    UserContext,
    PermissionCheckResult,
    PermissionResult,
    SecurityLevel,
    RateLimitTracker,
    ConcurrencyTracker,
    get_global_permission_layer,
    create_request_scoped_permission_layer
)
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestToolPermissionPolicy(SSotAsyncTestCase):
    """Unit tests for ToolPermissionPolicy."""
    
    def test_policy_creation_defaults(self):
        """Test policy creation with default values."""
        policy = ToolPermissionPolicy(tool_name="test_tool")
        
        assert policy.tool_name == "test_tool"
        assert policy.security_level == SecurityLevel.BASIC
        assert policy.required_roles == set()
        assert policy.required_features == set()
        assert "free" in policy.allowed_plans
        assert policy.max_calls_per_minute is None
        assert policy.created_by == "system"
        assert isinstance(policy.created_at, datetime)
        
    def test_policy_creation_custom(self):
        """Test policy creation with custom values."""
        policy = ToolPermissionPolicy(
            tool_name="premium_tool",
            security_level=SecurityLevel.PREMIUM,
            required_roles={"admin", "power_user"},
            required_features={"advanced_analytics"},
            allowed_plans={"premium", "enterprise"},
            max_calls_per_minute=10,
            max_calls_per_hour=100,
            max_calls_per_day=1000,
            max_concurrent_executions=3,
            max_execution_time_seconds=300,
            max_memory_mb=512,
            created_by="admin"
        )
        
        assert policy.tool_name == "premium_tool"
        assert policy.security_level == SecurityLevel.PREMIUM
        assert policy.required_roles == {"admin", "power_user"}
        assert policy.required_features == {"advanced_analytics"}
        assert policy.allowed_plans == {"premium", "enterprise"}
        assert policy.max_calls_per_minute == 10
        assert policy.max_calls_per_hour == 100
        assert policy.max_calls_per_day == 1000
        assert policy.max_concurrent_executions == 3
        assert policy.max_execution_time_seconds == 300
        assert policy.max_memory_mb == 512
        assert policy.created_by == "admin"
        
    def test_policy_to_dict(self):
        """Test policy serialization to dictionary."""
        policy = ToolPermissionPolicy(
            tool_name="test_tool",
            security_level=SecurityLevel.STANDARD,
            required_roles={"user"},
            max_calls_per_minute=60
        )
        
        policy_dict = policy.to_dict()
        
        assert policy_dict['tool_name'] == "test_tool"
        assert policy_dict['security_level'] == "STANDARD"
        assert policy_dict['required_roles'] == ["user"]
        assert policy_dict['max_calls_per_minute'] == 60
        assert 'created_at' in policy_dict
        assert policy_dict['created_by'] == "system"


class TestUserContext(SSotAsyncTestCase):
    """Unit tests for UserContext."""
    
    def test_user_context_defaults(self):
        """Test UserContext creation with defaults."""
        context = UserContext(user_id="test_user")
        
        assert context.user_id == "test_user"
        assert context.plan_tier == "free"
        assert context.roles == set()
        assert context.feature_flags == {}
        assert context.is_developer is False
        assert context.is_admin is False
        
    def test_user_context_custom(self):
        """Test UserContext creation with custom values."""
        context = UserContext(
            user_id="power_user",
            plan_tier="premium",
            roles={"admin", "developer"},
            feature_flags={"beta_features": True, "advanced_tools": True},
            is_developer=True,
            is_admin=True
        )
        
        assert context.user_id == "power_user"
        assert context.plan_tier == "premium"
        assert context.roles == {"admin", "developer"}
        assert context.feature_flags == {"beta_features": True, "advanced_tools": True}
        assert context.is_developer is True
        assert context.is_admin is True
        
    def test_security_clearance_admin(self):
        """Test security clearance for admin user."""
        context = UserContext(user_id="admin", is_admin=True)
        assert context.security_clearance == SecurityLevel.ADMIN
        
    def test_security_clearance_premium(self):
        """Test security clearance for premium user."""
        context = UserContext(user_id="user", plan_tier="premium")
        assert context.security_clearance == SecurityLevel.PREMIUM
        
    def test_security_clearance_basic_plan(self):
        """Test security clearance for basic plan user."""
        context = UserContext(user_id="user", plan_tier="basic")
        assert context.security_clearance == SecurityLevel.STANDARD
        
    def test_security_clearance_free(self):
        """Test security clearance for free user.""" 
        context = UserContext(user_id="user", plan_tier="free")
        assert context.security_clearance == SecurityLevel.BASIC


class TestPermissionCheckResult(SSotAsyncTestCase):
    """Unit tests for PermissionCheckResult."""
    
    def test_permission_result_allowed(self):
        """Test permission check result for allowed access."""
        result = PermissionCheckResult(
            allowed=True,
            result=PermissionResult.ALLOWED,
            reason="All checks passed",
            calls_remaining=50,
            policy_applied="test_policy"
        )
        
        assert result.allowed is True
        assert result.result == PermissionResult.ALLOWED
        assert result.reason == "All checks passed"
        assert result.calls_remaining == 50
        assert result.policy_applied == "test_policy"
        
    def test_permission_result_denied(self):
        """Test permission check result for denied access."""
        result = PermissionCheckResult(
            allowed=False,
            result=PermissionResult.INSUFFICIENT_PLAN,
            reason="Premium plan required",
            security_level_required=SecurityLevel.PREMIUM
        )
        
        assert result.allowed is False
        assert result.result == PermissionResult.INSUFFICIENT_PLAN
        assert result.reason == "Premium plan required"
        assert result.security_level_required == SecurityLevel.PREMIUM
        
    def test_permission_result_to_dict(self):
        """Test permission result serialization."""
        result = PermissionCheckResult(
            allowed=True,
            result=PermissionResult.ALLOWED,
            reason="Test",
            calls_remaining=10,
            reset_time=datetime.now(timezone.utc),
            security_level_required=SecurityLevel.BASIC
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['allowed'] is True
        assert result_dict['result'] == "allowed"
        assert result_dict['reason'] == "Test"
        assert result_dict['calls_remaining'] == 10
        assert 'reset_time' in result_dict
        assert result_dict['security_level_required'] == "BASIC"


class TestRateLimitTracker(SSotAsyncTestCase):
    """Unit tests for RateLimitTracker."""
    
    def setup_method(self, method=None):
        """Setup test fixtures."""
        super().setup_method(method)
        self.tracker = RateLimitTracker()
        
    def test_rate_limit_within_limits(self):
        """Test rate limiting within allowed limits."""
        is_allowed, remaining, reset_time = self.tracker.check_rate_limit(
            user_id="test_user",
            tool_name="test_tool", 
            max_per_minute=10
        )
        
        assert is_allowed is True
        assert remaining == 10
        
    def test_rate_limit_record_call(self):
        """Test recording calls for rate limiting."""
        # Record a call
        self.tracker.record_call("test_user", "test_tool")
        
        # Check limits - should have 9 remaining out of 10
        is_allowed, remaining, reset_time = self.tracker.check_rate_limit(
            user_id="test_user",
            tool_name="test_tool",
            max_per_minute=10
        )
        
        assert is_allowed is True
        assert remaining == 9
        
    def test_rate_limit_exceeded_per_minute(self):
        """Test rate limit exceeded per minute."""
        # Record 10 calls (max limit)
        for _ in range(10):
            self.tracker.record_call("test_user", "test_tool")
            
        # Next check should be denied
        is_allowed, remaining, reset_time = self.tracker.check_rate_limit(
            user_id="test_user", 
            tool_name="test_tool",
            max_per_minute=10
        )
        
        assert is_allowed is False
        assert remaining == 0
        assert reset_time is not None
        
    def test_rate_limit_per_hour(self):
        """Test hourly rate limiting."""
        # Record calls up to hourly limit
        for _ in range(5):
            self.tracker.record_call("test_user", "test_tool")
            
        is_allowed, remaining, reset_time = self.tracker.check_rate_limit(
            user_id="test_user",
            tool_name="test_tool", 
            max_per_hour=5
        )
        
        assert is_allowed is False  # At limit
        assert remaining == 0
        
    def test_rate_limit_per_day(self):
        """Test daily rate limiting."""
        # Record calls up to daily limit
        for _ in range(3):
            self.tracker.record_call("test_user", "test_tool")
            
        is_allowed, remaining, reset_time = self.tracker.check_rate_limit(
            user_id="test_user",
            tool_name="test_tool",
            max_per_day=3
        )
        
        assert is_allowed is False  # At limit
        assert remaining == 0
        
    def test_rate_limit_different_users(self):
        """Test rate limiting for different users."""
        # User 1 makes calls
        for _ in range(5):
            self.tracker.record_call("user1", "test_tool")
            
        # User 2 should have separate limits
        is_allowed, remaining, reset_time = self.tracker.check_rate_limit(
            user_id="user2",
            tool_name="test_tool",
            max_per_minute=10
        )
        
        assert is_allowed is True
        assert remaining == 10
        
    def test_rate_limit_different_tools(self):
        """Test rate limiting for different tools."""
        # Make calls for tool1
        for _ in range(5):
            self.tracker.record_call("test_user", "tool1")
            
        # tool2 should have separate limits
        is_allowed, remaining, reset_time = self.tracker.check_rate_limit(
            user_id="test_user",
            tool_name="tool2",
            max_per_minute=10
        )
        
        assert is_allowed is True
        assert remaining == 10
        
    def test_cleanup_old_entries(self):
        """Test cleanup of old rate limit entries."""
        # Mock time to simulate old entries
        with patch('time.time', return_value=time.time() - 86500):  # 24+ hours ago
            self.tracker.record_call("test_user", "test_tool")
            
        # Trigger cleanup
        self.tracker._cleanup_old_entries()
        
        # Old entries should be removed
        assert len(self.tracker.call_history) == 0


class TestConcurrencyTracker(SSotAsyncTestCase):
    """Unit tests for ConcurrencyTracker."""
    
    def setup_method(self, method=None):
        """Setup test fixtures."""
        super().setup_method(method)
        self.tracker = ConcurrencyTracker()
        
    def test_start_execution(self):
        """Test starting execution tracking."""
        self.tracker.start_execution("user1", "exec1")
        
        assert self.tracker.get_concurrent_count("user1") == 1
        assert "exec1" in self.tracker.active_executions["user1"]
        
    def test_end_execution(self):
        """Test ending execution tracking."""
        self.tracker.start_execution("user1", "exec1")
        self.tracker.end_execution("user1", "exec1")
        
        assert self.tracker.get_concurrent_count("user1") == 0
        assert "user1" not in self.tracker.active_executions
        
    def test_multiple_executions(self):
        """Test tracking multiple concurrent executions."""
        self.tracker.start_execution("user1", "exec1")
        self.tracker.start_execution("user1", "exec2")
        self.tracker.start_execution("user1", "exec3")
        
        assert self.tracker.get_concurrent_count("user1") == 3
        
    def test_check_concurrency_limit(self):
        """Test concurrency limit checking."""
        self.tracker.start_execution("user1", "exec1")
        self.tracker.start_execution("user1", "exec2")
        
        # Within limit of 3
        assert self.tracker.check_concurrency_limit("user1", 3) is True
        
        # At limit 
        assert self.tracker.check_concurrency_limit("user1", 2) is False
        
    def test_different_users_isolation(self):
        """Test that different users have isolated concurrency tracking."""
        self.tracker.start_execution("user1", "exec1")
        self.tracker.start_execution("user2", "exec1")
        
        assert self.tracker.get_concurrent_count("user1") == 1
        assert self.tracker.get_concurrent_count("user2") == 1


class TestUnifiedToolPermissionLayer(SSotAsyncTestCase):
    """Unit tests for UnifiedToolPermissionLayer."""
    
    def setup_method(self, method=None):
        """Setup test fixtures."""
        super().setup_method(method)
        self.layer = UnifiedToolPermissionLayer("test_layer")
        
        # Sample user contexts
        self.free_user = UserContext(user_id="free_user", plan_tier="free")
        self.premium_user = UserContext(user_id="premium_user", plan_tier="premium")
        self.admin_user = UserContext(user_id="admin_user", is_admin=True)
        
    def test_initialization(self):
        """Test permission layer initialization."""
        assert self.layer.layer_id == "test_layer"
        assert isinstance(self.layer.created_at, datetime)
        assert len(self.layer.policies) > 0  # Should have default policies
        assert isinstance(self.layer.rate_limiter, RateLimitTracker)
        assert isinstance(self.layer.concurrency_tracker, ConcurrencyTracker)
        assert isinstance(self.layer.audit_log, list)
        assert self.layer._metrics['permissions_checked'] == 0
        
    def test_default_policies_initialization(self):
        """Test that default policies are properly initialized."""
        # Check public tools
        assert "health_check" in self.layer.policies
        health_policy = self.layer.policies["health_check"]
        assert health_policy.security_level == SecurityLevel.PUBLIC
        assert health_policy.max_calls_per_minute == 100
        
        # Check basic tools
        assert "search_corpus" in self.layer.policies
        search_policy = self.layer.policies["search_corpus"]
        assert search_policy.security_level == SecurityLevel.BASIC
        assert search_policy.max_calls_per_minute == 30
        
        # Check premium tools
        assert "generate_synthetic_data_batch" in self.layer.policies
        premium_policy = self.layer.policies["generate_synthetic_data_batch"]
        assert premium_policy.security_level == SecurityLevel.PREMIUM
        assert "premium" in premium_policy.allowed_plans
        assert "free" not in premium_policy.allowed_plans
        
        # Check admin tools
        assert "delete_corpus" in self.layer.policies
        admin_policy = self.layer.policies["delete_corpus"]
        assert admin_policy.security_level == SecurityLevel.ADMIN
        assert "admin" in admin_policy.required_roles
        
    def test_add_policy(self):
        """Test adding custom tool policy."""
        policy = ToolPermissionPolicy(
            tool_name="custom_tool",
            security_level=SecurityLevel.STANDARD,
            max_calls_per_minute=5
        )
        
        success = self.layer.add_policy(policy)
        
        assert success is True
        assert "custom_tool" in self.layer.policies
        assert self.layer.policies["custom_tool"].max_calls_per_minute == 5
        
    def test_get_policy_existing(self):
        """Test getting existing policy."""
        policy = self.layer.get_policy("health_check")
        
        assert policy.tool_name == "health_check"
        assert policy.security_level == SecurityLevel.PUBLIC
        
    def test_get_policy_nonexistent(self):
        """Test getting non-existent policy returns default."""
        policy = self.layer.get_policy("nonexistent_tool")
        
        assert policy.tool_name == "default"
        assert policy.security_level == SecurityLevel.BASIC
        
    def test_remove_policy(self):
        """Test removing tool policy."""
        # Add a custom policy first
        custom_policy = ToolPermissionPolicy(tool_name="temp_tool")
        self.layer.add_policy(custom_policy)
        
        # Remove it
        success = self.layer.remove_policy("temp_tool")
        
        assert success is True
        assert "temp_tool" not in self.layer.policies
        
    def test_remove_policy_nonexistent(self):
        """Test removing non-existent policy."""
        success = self.layer.remove_policy("nonexistent_tool")
        assert success is False
        
    def test_list_policies(self):
        """Test listing all policy names."""
        policies = self.layer.list_policies()
        
        assert isinstance(policies, list)
        assert "health_check" in policies
        assert "search_corpus" in policies
        assert len(policies) > 0
        
    def test_get_all_policies(self):
        """Test getting all policies as dictionaries."""
        all_policies = self.layer.get_all_policies()
        
        assert isinstance(all_policies, dict)
        assert "health_check" in all_policies
        assert isinstance(all_policies["health_check"], dict)
        assert all_policies["health_check"]["security_level"] == "PUBLIC"
        
    async def test_check_permission_allowed_public(self):
        """Test permission check for public tool - should be allowed."""
        result = await self.layer.check_permission(
            user_context=self.free_user,
            tool_name="health_check"
        )
        
        assert result.allowed is True
        assert result.result == PermissionResult.ALLOWED
        assert result.policy_applied == "health_check"
        
    async def test_check_permission_denied_insufficient_plan(self):
        """Test permission check denied due to insufficient plan."""
        result = await self.layer.check_permission(
            user_context=self.free_user,
            tool_name="generate_synthetic_data_batch"  # Premium tool
        )
        
        assert result.allowed is False
        assert result.result == PermissionResult.INSUFFICIENT_PLAN
        assert "free" in result.reason.lower()
        assert result.policy_applied == "generate_synthetic_data_batch"
        
    async def test_check_permission_allowed_premium(self):
        """Test permission check allowed for premium user."""
        result = await self.layer.check_permission(
            user_context=self.premium_user,
            tool_name="generate_synthetic_data_batch"
        )
        
        assert result.allowed is True
        assert result.result == PermissionResult.ALLOWED
        
    async def test_check_permission_denied_insufficient_role(self):
        """Test permission check denied due to insufficient role."""
        result = await self.layer.check_permission(
            user_context=self.premium_user,  # Premium but not admin
            tool_name="delete_corpus"  # Admin tool
        )
        
        assert result.allowed is False
        assert result.result == PermissionResult.POLICY_VIOLATION
        assert "role" in result.reason.lower()
        
    async def test_check_permission_allowed_admin(self):
        """Test permission check allowed for admin user."""
        result = await self.layer.check_permission(
            user_context=self.admin_user,
            tool_name="delete_corpus"
        )
        
        assert result.allowed is True
        assert result.result == PermissionResult.ALLOWED
        
    async def test_check_permission_denied_missing_feature(self):
        """Test permission check denied due to missing feature flag."""
        # Create policy requiring feature flag
        policy = ToolPermissionPolicy(
            tool_name="beta_tool",
            required_features={"beta_access"}
        )
        self.layer.add_policy(policy)
        
        result = await self.layer.check_permission(
            user_context=self.free_user,
            tool_name="beta_tool"
        )
        
        assert result.allowed is False
        assert result.result == PermissionResult.MISSING_FEATURE
        assert "beta_access" in result.reason
        
    async def test_check_permission_allowed_with_feature(self):
        """Test permission check allowed with required feature flag."""
        # Create policy requiring feature flag
        policy = ToolPermissionPolicy(
            tool_name="beta_tool",
            required_features={"beta_access"}
        )
        self.layer.add_policy(policy)
        
        # User with feature flag
        user_with_feature = UserContext(
            user_id="beta_user",
            feature_flags={"beta_access": True}
        )
        
        result = await self.layer.check_permission(
            user_context=user_with_feature,
            tool_name="beta_tool"
        )
        
        assert result.allowed is True
        assert result.result == PermissionResult.ALLOWED
        
    async def test_check_permission_rate_limited(self):
        """Test permission check denied due to rate limiting."""
        # Create policy with strict rate limit
        policy = ToolPermissionPolicy(
            tool_name="limited_tool",
            max_calls_per_minute=1
        )
        self.layer.add_policy(policy)
        
        # First call should succeed
        result1 = await self.layer.check_permission(
            user_context=self.free_user,
            tool_name="limited_tool"
        )
        assert result1.allowed is True
        
        # Second call should be rate limited
        result2 = await self.layer.check_permission(
            user_context=self.free_user,
            tool_name="limited_tool"
        )
        assert result2.allowed is False
        assert result2.result == PermissionResult.RATE_LIMITED
        
    async def test_check_permission_concurrency_limited(self):
        """Test permission check denied due to concurrency limits."""
        # Create policy with concurrency limit
        policy = ToolPermissionPolicy(
            tool_name="concurrent_tool",
            max_concurrent_executions=1
        )
        self.layer.add_policy(policy)
        
        # Start one execution
        result1 = await self.layer.check_permission(
            user_context=self.free_user,
            tool_name="concurrent_tool",
            execution_id="exec1"
        )
        assert result1.allowed is True
        
        # Second concurrent execution should be denied
        result2 = await self.layer.check_permission(
            user_context=self.free_user,
            tool_name="concurrent_tool", 
            execution_id="exec2"
        )
        assert result2.allowed is False
        assert result2.result == PermissionResult.QUOTA_EXCEEDED
        
    async def test_check_permission_validation_rule_success(self):
        """Test permission check with successful parameter validation."""
        # Create policy with validation rule
        def validate_params(params):
            return params.get("required_field") == "expected_value"
            
        policy = ToolPermissionPolicy(
            tool_name="validated_tool",
            validation_rules=[validate_params]
        )
        self.layer.add_policy(policy)
        
        result = await self.layer.check_permission(
            user_context=self.free_user,
            tool_name="validated_tool",
            parameters={"required_field": "expected_value"}
        )
        
        assert result.allowed is True
        assert result.result == PermissionResult.ALLOWED
        
    async def test_check_permission_validation_rule_failure(self):
        """Test permission check with failed parameter validation."""
        # Create policy with validation rule
        def validate_params(params):
            return params.get("required_field") == "expected_value"
            
        policy = ToolPermissionPolicy(
            tool_name="validated_tool",
            validation_rules=[validate_params]
        )
        self.layer.add_policy(policy)
        
        result = await self.layer.check_permission(
            user_context=self.free_user,
            tool_name="validated_tool",
            parameters={"required_field": "wrong_value"}
        )
        
        assert result.allowed is False
        assert result.result == PermissionResult.POLICY_VIOLATION
        assert "validation" in result.reason.lower()
        
    async def test_check_permission_validation_rule_exception(self):
        """Test permission check with validation rule exception."""
        # Create policy with validation rule that raises exception
        def failing_validator(params):
            raise ValueError("Validation error")
            
        policy = ToolPermissionPolicy(
            tool_name="failing_tool",
            validation_rules=[failing_validator]
        )
        self.layer.add_policy(policy)
        
        result = await self.layer.check_permission(
            user_context=self.free_user,
            tool_name="failing_tool",
            parameters={"test": "data"}
        )
        
        assert result.allowed is False
        assert result.result == PermissionResult.POLICY_VIOLATION
        assert "validation error" in result.reason.lower()
        
    def test_end_execution(self):
        """Test ending execution tracking."""
        # Start tracking
        self.layer.concurrency_tracker.start_execution("test_user", "exec1")
        assert self.layer.concurrency_tracker.get_concurrent_count("test_user") == 1
        
        # End tracking
        self.layer.end_execution("test_user", "exec1")
        assert self.layer.concurrency_tracker.get_concurrent_count("test_user") == 0
        
    async def test_audit_logging(self):
        """Test audit log recording."""
        initial_count = len(self.layer.audit_log)
        
        # Make a permission check
        await self.layer.check_permission(
            user_context=self.free_user,
            tool_name="health_check"
        )
        
        # Should have recorded audit entry
        assert len(self.layer.audit_log) > initial_count
        
        # Check audit entry content
        latest_entry = self.layer.audit_log[-1]
        assert latest_entry['action'] == 'permission_granted'
        assert latest_entry['user_id'] == 'free_user'
        assert latest_entry['tool_name'] == 'health_check'
        assert latest_entry['layer_id'] == 'test_layer'
        assert 'timestamp' in latest_entry
        
    def test_get_audit_log_unfiltered(self):
        """Test getting unfiltered audit log."""
        # Record some audit entries
        self.layer._record_audit("test_action", "user1", "tool1", "test details")
        self.layer._record_audit("test_action", "user2", "tool2", "test details")
        
        audit_entries = self.layer.get_audit_log()
        
        assert len(audit_entries) >= 2
        assert any(entry['user_id'] == 'user1' for entry in audit_entries)
        assert any(entry['user_id'] == 'user2' for entry in audit_entries)
        
    def test_get_audit_log_filtered_by_user(self):
        """Test getting audit log filtered by user."""
        # Record entries for different users
        self.layer._record_audit("action1", "target_user", "tool1", "details")
        self.layer._record_audit("action2", "other_user", "tool2", "details")
        
        audit_entries = self.layer.get_audit_log(user_id="target_user")
        
        assert len(audit_entries) >= 1
        assert all(entry['user_id'] == 'target_user' for entry in audit_entries)
        
    def test_get_audit_log_filtered_by_tool(self):
        """Test getting audit log filtered by tool."""
        # Record entries for different tools
        self.layer._record_audit("action1", "user1", "target_tool", "details")
        self.layer._record_audit("action2", "user2", "other_tool", "details")
        
        audit_entries = self.layer.get_audit_log(tool_name="target_tool")
        
        assert len(audit_entries) >= 1
        assert all(entry['tool_name'] == 'target_tool' for entry in audit_entries)
        
    def test_get_audit_log_with_limit(self):
        """Test getting audit log with limit."""
        # Record multiple entries
        for i in range(5):
            self.layer._record_audit(f"action{i}", f"user{i}", f"tool{i}", "details")
            
        audit_entries = self.layer.get_audit_log(limit=3)
        
        assert len(audit_entries) == 3
        
    def test_clear_audit_log(self):
        """Test clearing audit log."""
        # Add some entries
        self.layer._record_audit("test", "user", "tool", "details")
        assert len(self.layer.audit_log) > 0
        
        # Clear log
        self.layer.clear_audit_log()
        assert len(self.layer.audit_log) == 0
        
    async def test_permission_metrics(self):
        """Test permission metrics collection."""
        initial_metrics = self.layer.get_permission_metrics()
        initial_checked = initial_metrics['permissions_checked']
        
        # Make some permission checks
        await self.layer.check_permission(self.free_user, "health_check")
        await self.layer.check_permission(self.free_user, "generate_synthetic_data_batch")  # Will be denied
        
        updated_metrics = self.layer.get_permission_metrics()
        
        assert updated_metrics['permissions_checked'] == initial_checked + 2
        assert updated_metrics['permissions_granted'] >= 1
        assert updated_metrics['permissions_denied'] >= 1
        assert updated_metrics['layer_id'] == 'test_layer'
        assert 'uptime_seconds' in updated_metrics
        assert 'success_rate' in updated_metrics
        
    def test_get_user_usage_summary(self):
        """Test getting user usage summary."""
        # Record some audit entries for user
        self.layer._record_audit("permission_granted", "test_user", "tool1", "granted")
        self.layer._record_audit("permission_denied", "test_user", "tool2", "denied")
        
        summary = self.layer.get_user_usage_summary("test_user")
        
        assert summary['user_id'] == 'test_user'
        assert summary['total_actions'] >= 2
        assert 'tool_usage' in summary
        assert 'action_breakdown' in summary
        assert 'current_concurrent_executions' in summary
        assert 'current_rate_limits' in summary
        
    def test_validate_layer_health_healthy(self):
        """Test layer health validation when healthy."""
        health = self.layer.validate_layer_health()
        
        assert health['status'] == 'healthy'  # Should be healthy initially
        assert 'timestamp' in health
        assert 'issues' in health
        assert 'metrics' in health
        
    def test_validate_layer_health_high_denial_rate(self):
        """Test layer health validation with high denial rate."""
        # Simulate high denial rate
        self.layer._metrics['permissions_checked'] = 200
        self.layer._metrics['permissions_denied'] = 120  # >50% denial rate
        
        health = self.layer.validate_layer_health()
        
        assert health['status'] == 'degraded'
        assert any('denial rate' in issue.lower() for issue in health['issues'])
        
    def test_validate_layer_health_low_policy_count(self):
        """Test layer health validation with few policies."""
        # Remove most policies to simulate low count
        self.layer.policies = {"single_policy": self.layer.default_policy}
        
        health = self.layer.validate_layer_health()
        
        assert health['status'] == 'warning'
        assert any('policy count' in issue.lower() for issue in health['issues'])
        
    def test_validate_layer_health_audit_log_capacity(self):
        """Test layer health validation with audit log near capacity."""
        # Fill audit log near capacity
        near_capacity = int(self.layer.max_audit_entries * 0.95)
        self.layer.audit_log = [{'dummy': 'entry'} for _ in range(near_capacity)]
        
        health = self.layer.validate_layer_health()
        
        assert health['status'] == 'warning'
        assert any('audit log' in issue.lower() for issue in health['issues'])


class TestGlobalAndFactoryFunctions(SSotAsyncTestCase):
    """Unit tests for global instance and factory functions."""
    
    def test_get_global_permission_layer(self):
        """Test getting global permission layer instance."""
        layer1 = get_global_permission_layer()
        layer2 = get_global_permission_layer()
        
        # Should return same instance
        assert layer1 is layer2
        assert layer1.layer_id == "global"
        
    def test_create_request_scoped_permission_layer(self):
        """Test creating request-scoped permission layer."""
        layer1 = create_request_scoped_permission_layer("request1")
        layer2 = create_request_scoped_permission_layer("request2")
        
        # Should be different instances
        assert layer1 is not layer2
        assert layer1.layer_id == "request1"
        assert layer2.layer_id == "request2"
        
    def test_create_request_scoped_permission_layer_auto_id(self):
        """Test creating request-scoped layer with auto-generated ID."""
        layer = create_request_scoped_permission_layer()
        
        assert isinstance(layer, UnifiedToolPermissionLayer)
        assert layer.layer_id.startswith("permlayer_")


class TestSecurityLevelEnum(SSotAsyncTestCase):
    """Unit tests for SecurityLevel enum."""
    
    def test_security_level_values(self):
        """Test SecurityLevel enum values."""
        assert SecurityLevel.PUBLIC.value == 0
        assert SecurityLevel.BASIC.value == 1
        assert SecurityLevel.STANDARD.value == 2
        assert SecurityLevel.PREMIUM.value == 3
        assert SecurityLevel.ADMIN.value == 4
        assert SecurityLevel.SYSTEM.value == 5
        
    def test_security_level_ordering(self):
        """Test SecurityLevel ordering for comparisons."""
        assert SecurityLevel.PUBLIC < SecurityLevel.BASIC
        assert SecurityLevel.BASIC < SecurityLevel.STANDARD
        assert SecurityLevel.STANDARD < SecurityLevel.PREMIUM
        assert SecurityLevel.PREMIUM < SecurityLevel.ADMIN
        assert SecurityLevel.ADMIN < SecurityLevel.SYSTEM


class TestPermissionResultEnum(SSotAsyncTestCase):
    """Unit tests for PermissionResult enum."""
    
    def test_permission_result_values(self):
        """Test PermissionResult enum values."""
        assert PermissionResult.ALLOWED.value == "allowed"
        assert PermissionResult.DENIED.value == "denied"
        assert PermissionResult.RATE_LIMITED.value == "rate_limited"
        assert PermissionResult.QUOTA_EXCEEDED.value == "quota_exceeded"
        assert PermissionResult.INSUFFICIENT_PLAN.value == "insufficient_plan"
        assert PermissionResult.MISSING_FEATURE.value == "missing_feature"
        assert PermissionResult.POLICY_VIOLATION.value == "policy_violation"


if __name__ == "__main__":
    pytest.main([__file__])