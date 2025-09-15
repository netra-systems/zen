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
from netra_backend.app.agents.tool_permission_layer import UnifiedToolPermissionLayer, ToolPermissionPolicy, UserContext, PermissionCheckResult, PermissionResult, SecurityLevel, RateLimitTracker, ConcurrencyTracker, get_global_permission_layer, create_request_scoped_permission_layer
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class ToolPermissionPolicyTests(SSotAsyncTestCase):
    """Unit tests for ToolPermissionPolicy."""

    def test_policy_creation_defaults(self):
        """Test policy creation with default values."""
        policy = ToolPermissionPolicy(tool_name='test_tool')
        assert policy.tool_name == 'test_tool'
        assert policy.security_level == SecurityLevel.BASIC
        assert policy.required_roles == set()
        assert policy.required_features == set()
        assert 'free' in policy.allowed_plans
        assert policy.max_calls_per_minute is None
        assert policy.created_by == 'system'
        assert isinstance(policy.created_at, datetime)

    def test_policy_creation_custom(self):
        """Test policy creation with custom values."""
        policy = ToolPermissionPolicy(tool_name='premium_tool', security_level=SecurityLevel.PREMIUM, required_roles={'admin', 'power_user'}, required_features={'advanced_analytics'}, allowed_plans={'premium', 'enterprise'}, max_calls_per_minute=10, created_by='admin')
        assert policy.tool_name == 'premium_tool'
        assert policy.security_level == SecurityLevel.PREMIUM
        assert policy.required_roles == {'admin', 'power_user'}
        assert policy.required_features == {'advanced_analytics'}
        assert policy.allowed_plans == {'premium', 'enterprise'}
        assert policy.max_calls_per_minute == 10
        assert policy.created_by == 'admin'

    def test_policy_to_dict(self):
        """Test policy serialization to dictionary."""
        policy = ToolPermissionPolicy(tool_name='test_tool', security_level=SecurityLevel.STANDARD, required_roles={'user'}, max_calls_per_minute=60)
        policy_dict = policy.to_dict()
        assert policy_dict['tool_name'] == 'test_tool'
        assert policy_dict['security_level'] == 'STANDARD'
        assert policy_dict['required_roles'] == ['user']
        assert policy_dict['max_calls_per_minute'] == 60
        assert 'created_at' in policy_dict

class UserContextTests(SSotAsyncTestCase):
    """Unit tests for UserContext."""

    def test_user_context_defaults(self):
        """Test UserContext creation with defaults."""
        context = UserContext(user_id='test_user')
        assert context.user_id == 'test_user'
        assert context.plan_tier == 'free'
        assert context.roles == set()
        assert context.feature_flags == {}
        assert context.is_developer is False
        assert context.is_admin is False

    def test_security_clearance_admin(self):
        """Test security clearance for admin user."""
        context = UserContext(user_id='admin', is_admin=True)
        assert context.security_clearance == SecurityLevel.ADMIN

    def test_security_clearance_premium(self):
        """Test security clearance for premium user."""
        context = UserContext(user_id='user', plan_tier='premium')
        assert context.security_clearance == SecurityLevel.PREMIUM

    def test_security_clearance_basic_plan(self):
        """Test security clearance for basic plan user."""
        context = UserContext(user_id='user', plan_tier='basic')
        assert context.security_clearance == SecurityLevel.STANDARD

    def test_security_clearance_free(self):
        """Test security clearance for free user."""
        context = UserContext(user_id='user', plan_tier='free')
        assert context.security_clearance == SecurityLevel.BASIC

class RateLimitTrackerTests(SSotAsyncTestCase):
    """Unit tests for RateLimitTracker."""

    def setup_method(self, method=None):
        """Setup test fixtures."""
        super().setup_method(method)
        self.tracker = RateLimitTracker()

    def test_rate_limit_within_limits(self):
        """Test rate limiting within allowed limits."""
        is_allowed, remaining, reset_time = self.tracker.check_rate_limit(user_id='test_user', tool_name='test_tool', max_per_minute=10)
        assert is_allowed is True
        assert remaining == 10

    def test_rate_limit_record_call(self):
        """Test recording calls for rate limiting."""
        self.tracker.record_call('test_user', 'test_tool')
        is_allowed, remaining, reset_time = self.tracker.check_rate_limit(user_id='test_user', tool_name='test_tool', max_per_minute=10)
        assert is_allowed is True
        assert remaining == 9

    def test_rate_limit_exceeded_per_minute(self):
        """Test rate limit exceeded per minute."""
        for _ in range(10):
            self.tracker.record_call('test_user', 'test_tool')
        is_allowed, remaining, reset_time = self.tracker.check_rate_limit(user_id='test_user', tool_name='test_tool', max_per_minute=10)
        assert is_allowed is False
        assert remaining == 0
        assert reset_time is not None

class ConcurrencyTrackerTests(SSotAsyncTestCase):
    """Unit tests for ConcurrencyTracker."""

    def setup_method(self, method=None):
        """Setup test fixtures."""
        super().setup_method(method)
        self.tracker = ConcurrencyTracker()

    def test_start_execution(self):
        """Test starting execution tracking."""
        self.tracker.start_execution('user1', 'exec1')
        assert self.tracker.get_concurrent_count('user1') == 1
        assert 'exec1' in self.tracker.active_executions['user1']

    def test_end_execution(self):
        """Test ending execution tracking."""
        self.tracker.start_execution('user1', 'exec1')
        self.tracker.end_execution('user1', 'exec1')
        assert self.tracker.get_concurrent_count('user1') == 0
        assert 'user1' not in self.tracker.active_executions

class UnifiedToolPermissionLayerTests(SSotAsyncTestCase):
    """Unit tests for UnifiedToolPermissionLayer."""

    def setup_method(self, method=None):
        """Setup test fixtures."""
        super().setup_method(method)
        self.layer = UnifiedToolPermissionLayer('test_layer')
        self.free_user = UserContext(user_id='free_user', plan_tier='free')
        self.premium_user = UserContext(user_id='premium_user', plan_tier='premium')
        self.admin_user = UserContext(user_id='admin_user', is_admin=True)

    def test_initialization(self):
        """Test permission layer initialization."""
        assert self.layer.layer_id == 'test_layer'
        assert isinstance(self.layer.created_at, datetime)
        assert len(self.layer.policies) > 0
        assert isinstance(self.layer.rate_limiter, RateLimitTracker)
        assert isinstance(self.layer.concurrency_tracker, ConcurrencyTracker)
        assert isinstance(self.layer.audit_log, list)
        assert self.layer._metrics['permissions_checked'] == 0

    def test_default_policies_initialization(self):
        """Test that default policies are properly initialized."""
        assert 'health_check' in self.layer.policies
        health_policy = self.layer.policies['health_check']
        assert health_policy.security_level == SecurityLevel.PUBLIC
        assert 'search_corpus' in self.layer.policies
        search_policy = self.layer.policies['search_corpus']
        assert search_policy.security_level == SecurityLevel.BASIC
        assert 'generate_synthetic_data_batch' in self.layer.policies
        premium_policy = self.layer.policies['generate_synthetic_data_batch']
        assert premium_policy.security_level == SecurityLevel.PREMIUM
        assert 'premium' in premium_policy.allowed_plans
        assert 'free' not in premium_policy.allowed_plans

    def test_add_policy(self):
        """Test adding custom tool policy."""
        policy = ToolPermissionPolicy(tool_name='custom_tool', security_level=SecurityLevel.STANDARD, max_calls_per_minute=5)
        success = self.layer.add_policy(policy)
        assert success is True
        assert 'custom_tool' in self.layer.policies
        assert self.layer.policies['custom_tool'].max_calls_per_minute == 5

    def test_get_policy_existing(self):
        """Test getting existing policy."""
        policy = self.layer.get_policy('health_check')
        assert policy.tool_name == 'health_check'
        assert policy.security_level == SecurityLevel.PUBLIC

    def test_get_policy_nonexistent(self):
        """Test getting non-existent policy returns default."""
        policy = self.layer.get_policy('nonexistent_tool')
        assert policy.tool_name == 'default'
        assert policy.security_level == SecurityLevel.BASIC

    async def test_check_permission_allowed_public(self):
        """Test permission check for public tool - should be allowed."""
        result = await self.layer.check_permission(user_context=self.free_user, tool_name='health_check')
        assert result.allowed is True
        assert result.result == PermissionResult.ALLOWED
        assert result.policy_applied == 'health_check'

    async def test_check_permission_denied_insufficient_plan(self):
        """Test permission check denied due to insufficient plan."""
        result = await self.layer.check_permission(user_context=self.free_user, tool_name='generate_synthetic_data_batch')
        assert result.allowed is False
        assert result.result == PermissionResult.INSUFFICIENT_PLAN
        assert 'free' in result.reason.lower()

    async def test_check_permission_allowed_premium(self):
        """Test permission check allowed for premium user."""
        result = await self.layer.check_permission(user_context=self.premium_user, tool_name='generate_synthetic_data_batch')
        assert result.allowed is True
        assert result.result == PermissionResult.ALLOWED

    async def test_check_permission_rate_limited(self):
        """Test permission check denied due to rate limiting."""
        policy = ToolPermissionPolicy(tool_name='limited_tool', max_calls_per_minute=1)
        self.layer.add_policy(policy)
        result1 = await self.layer.check_permission(user_context=self.free_user, tool_name='limited_tool')
        assert result1.allowed is True
        result2 = await self.layer.check_permission(user_context=self.free_user, tool_name='limited_tool')
        assert result2.allowed is False
        assert result2.result == PermissionResult.RATE_LIMITED

    async def test_audit_logging(self):
        """Test audit log recording."""
        initial_count = len(self.layer.audit_log)
        await self.layer.check_permission(user_context=self.free_user, tool_name='health_check')
        assert len(self.layer.audit_log) > initial_count
        latest_entry = self.layer.audit_log[-1]
        assert latest_entry['action'] == 'permission_granted'
        assert latest_entry['user_id'] == 'free_user'
        assert latest_entry['tool_name'] == 'health_check'
        assert latest_entry['layer_id'] == 'test_layer'

class GlobalAndFactoryFunctionsTests(SSotAsyncTestCase):
    """Unit tests for global instance and factory functions."""

    def test_get_global_permission_layer(self):
        """Test getting global permission layer instance."""
        layer1 = get_global_permission_layer()
        layer2 = get_global_permission_layer()
        assert layer1 is layer2
        assert layer1.layer_id == 'global'

    def test_create_request_scoped_permission_layer(self):
        """Test creating request-scoped permission layer."""
        layer1 = create_request_scoped_permission_layer('request1')
        layer2 = create_request_scoped_permission_layer('request2')
        assert layer1 is not layer2
        assert layer1.layer_id == 'request1'
        assert layer2.layer_id == 'request2'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')