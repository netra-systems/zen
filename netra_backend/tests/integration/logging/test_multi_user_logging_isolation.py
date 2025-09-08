"""
Test Multi-User Logging Isolation - Integration Tests for User Context Separation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core platform security
- Business Goal: Ensure user data isolation and prevent cross-user information leakage
- Value Impact: Protects customer data privacy and enables secure multi-tenancy
- Strategic Impact: Foundation for enterprise-grade security and compliance

This test suite validates that logging maintains proper user isolation:
1. User context separation in logs
2. No cross-user data leakage in debugging information
3. User-specific correlation IDs and session tracking
4. Proper isolation under concurrent user operations
"""

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, List, Any, Set
from unittest.mock import MagicMock

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.conftest_real_services import real_services
from shared.logging.unified_logger_factory import get_logger


class TestMultiUserLoggingIsolation(SSotAsyncTestCase):
    """Test multi-user logging isolation and privacy protection."""
    
    def setup_method(self, method=None):
        """Setup for each test."""
        super().setup_method(method)
        
        # Setup test environment for multi-user isolation testing
        self.set_env_var("LOG_LEVEL", "DEBUG")
        self.set_env_var("ENABLE_USER_ISOLATION", "true")
        self.set_env_var("SERVICE_NAME", "multi-user-test-service")
        self.set_env_var("ENABLE_USER_CONTEXT_LOGGING", "true")
        
        # Initialize logger
        self.logger = get_logger("multi_user_isolation_test")
        
        # Capture logs for analysis
        self.captured_logs = []
        self.mock_handler = MagicMock()
        self.mock_handler.emit = lambda record: self.captured_logs.append(record)
        self.logger.addHandler(self.mock_handler)
        
        # Test users for isolation testing
        self.test_users = [
            {
                "user_id": "user_alice_001",
                "email": "alice@enterprise.com",
                "organization_id": "org_enterprise_001",
                "subscription": "enterprise",
                "permissions": ["read", "write", "agent_execute", "admin"],
                "sensitive_data": {
                    "api_key": "sk-alice-1234567890abcdef",
                    "internal_notes": "High-value customer - priority support"
                }
            },
            {
                "user_id": "user_bob_002", 
                "email": "bob@startup.com",
                "organization_id": "org_startup_002",
                "subscription": "professional",
                "permissions": ["read", "write", "agent_execute"],
                "sensitive_data": {
                    "api_key": "sk-bob-fedcba0987654321",
                    "internal_notes": "New customer - monitor usage"
                }
            },
            {
                "user_id": "user_charlie_003",
                "email": "charlie@individual.com", 
                "organization_id": "org_individual_003",
                "subscription": "free",
                "permissions": ["read"],
                "sensitive_data": {
                    "api_key": None,  # Free tier has no API key
                    "internal_notes": "Free tier user - limited features"
                }
            }
        ]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_isolation_in_logs(self, real_services):
        """Test that user context is properly isolated in logs."""
        # Log operations for each user with their specific context
        for user in self.test_users:
            user_correlation = f"corr_{user['user_id']}_{int(time.time())}"
            
            # User-specific operation
            self.logger.info(
                f"User operation: {user['subscription']} tier analysis",
                extra={
                    "user_id": user["user_id"],
                    "correlation_id": user_correlation,
                    "user_email": user["email"],
                    "organization_id": user["organization_id"],
                    "subscription_tier": user["subscription"],
                    "user_permissions": user["permissions"],
                    "operation": "cost_analysis",
                    "user_context_isolated": True,
                    "isolation_boundary": f"user_isolation_{user['user_id']}"
                }
            )
            
            # User-specific sensitive operation (should be filtered)
            self.logger.info(
                "Processing user-specific configuration",
                extra={
                    "user_id": user["user_id"],
                    "correlation_id": user_correlation,
                    "organization_id": user["organization_id"],
                    "operation": "config_update",
                    # Sensitive data that should NOT leak to other users
                    "user_api_key": user["sensitive_data"]["api_key"],
                    "internal_customer_notes": user["sensitive_data"]["internal_notes"],
                    "subscription_details": {
                        "tier": user["subscription"],
                        "monthly_limit": 1000 if user["subscription"] == "free" else 10000,
                        "overage_allowed": user["subscription"] != "free"
                    }
                }
            )
        
        # Validate user isolation in logs
        assert len(self.captured_logs) == len(self.test_users) * 2, f"Expected {len(self.test_users) * 2} logs"
        
        # Group logs by user
        user_logs = {}
        for log in self.captured_logs:
            if hasattr(log, 'user_id'):
                user_id = log.user_id
                if user_id not in user_logs:
                    user_logs[user_id] = []
                user_logs[user_id].append(log)
        
        assert len(user_logs) == len(self.test_users), f"Expected logs for {len(self.test_users)} users"
        
        # Validate each user's logs are isolated
        for user in self.test_users:
            user_id = user["user_id"]
            assert user_id in user_logs, f"No logs found for user {user_id}"
            
            logs = user_logs[user_id]
            assert len(logs) == 2, f"Expected 2 logs for user {user_id}, got {len(logs)}"
            
            # Validate user context consistency
            for log in logs:
                assert log.user_id == user_id, f"User ID mismatch in log: {log.user_id}"
                assert hasattr(log, 'organization_id'), f"Organization ID missing for user {user_id}"
                assert log.organization_id == user["organization_id"], f"Organization ID mismatch for user {user_id}"
                assert hasattr(log, 'subscription_tier'), f"Subscription tier missing for user {user_id}"
                
                # Validate isolation boundary
                if hasattr(log, 'isolation_boundary'):
                    assert user_id in log.isolation_boundary, f"User ID not in isolation boundary for {user_id}"
        
        # Validate no cross-user data leakage
        self._validate_no_cross_user_leakage(user_logs)
        
        self.record_metric("user_context_isolation_test", "PASSED")
        self.record_metric("users_tested", len(self.test_users))
    
    def _validate_no_cross_user_leakage(self, user_logs: Dict[str, List]):
        """Validate that no user data appears in other users' logs."""
        for user_id, logs in user_logs.items():
            # Get this user's data
            user_data = next(u for u in self.test_users if u["user_id"] == user_id)
            
            # Check other users' logs for this user's sensitive data
            for other_user_id, other_logs in user_logs.items():
                if other_user_id == user_id:
                    continue
                
                # Check for data leakage in other user's logs
                for log in other_logs:
                    log_content = str(log.__dict__)
                    
                    # User email should not appear in other users' logs
                    assert user_data["email"] not in log_content, f"User {user_id} email leaked to {other_user_id} logs"
                    
                    # API keys should not appear in other users' logs
                    if user_data["sensitive_data"]["api_key"]:
                        assert user_data["sensitive_data"]["api_key"] not in log_content, f"User {user_id} API key leaked to {other_user_id} logs"
                    
                    # Internal notes should not appear in other users' logs
                    internal_notes = user_data["sensitive_data"]["internal_notes"]
                    # Check for partial matches of internal notes
                    note_words = internal_notes.split()
                    for word in note_words:
                        if len(word) > 5:  # Only check significant words
                            assert word not in log_content, f"User {user_id} internal note word '{word}' leaked to {other_user_id} logs"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_logging_isolation(self, real_services):
        """Test user isolation under concurrent operations."""
        async def user_operation(user: Dict[str, Any], operation_count: int):
            """Simulate concurrent operations for a single user."""
            user_logs = []
            
            for i in range(operation_count):
                correlation_id = f"concurrent_corr_{user['user_id']}_{i}_{int(time.time() * 1000)}"
                
                # Each operation has its own request context
                self.logger.info(
                    f"Concurrent operation {i} for user",
                    extra={
                        "user_id": user["user_id"],
                        "correlation_id": correlation_id,
                        "operation_index": i,
                        "organization_id": user["organization_id"],
                        "subscription_tier": user["subscription"],
                        "operation": "concurrent_test",
                        "thread_isolation": f"thread_{user['user_id']}_{i}",
                        "user_context_isolated": True,
                        "concurrent_operation": True
                    }
                )
                
                # Small delay to simulate real work
                await asyncio.sleep(0.01)
                
                user_logs.append(correlation_id)
            
            return user_logs
        
        # Run concurrent operations for all users
        operation_count = 5
        tasks = []
        for user in self.test_users:
            task = user_operation(user, operation_count)
            tasks.append(task)
        
        # Execute all user operations concurrently
        results = await asyncio.gather(*tasks)
        
        # Validate concurrent isolation
        expected_total_logs = len(self.test_users) * operation_count
        concurrent_logs = [log for log in self.captured_logs if hasattr(log, 'concurrent_operation')]
        
        assert len(concurrent_logs) == expected_total_logs, f"Expected {expected_total_logs} concurrent logs, got {len(concurrent_logs)}"
        
        # Group concurrent logs by user
        concurrent_user_logs = {}
        for log in concurrent_logs:
            user_id = log.user_id
            if user_id not in concurrent_user_logs:
                concurrent_user_logs[user_id] = []
            concurrent_user_logs[user_id].append(log)
        
        # Validate each user has correct number of logs
        for user in self.test_users:
            user_id = user["user_id"]
            assert user_id in concurrent_user_logs, f"No concurrent logs for user {user_id}"
            assert len(concurrent_user_logs[user_id]) == operation_count, f"Wrong log count for user {user_id}"
            
            # Validate thread isolation
            for log in concurrent_user_logs[user_id]:
                assert hasattr(log, 'thread_isolation'), f"Thread isolation missing for user {user_id}"
                assert user_id in log.thread_isolation, f"User ID not in thread isolation for {user_id}"
        
        # Validate no cross-user data leakage under concurrency
        self._validate_no_cross_user_leakage(concurrent_user_logs)
        
        self.record_metric("concurrent_user_isolation_test", "PASSED")
        self.record_metric("concurrent_operations_per_user", operation_count)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_session_correlation_isolation(self, real_services):
        """Test that user session correlations are properly isolated."""
        # Create session for each user
        user_sessions = {}
        for user in self.test_users:
            session_id = f"session_{user['user_id']}_{uuid.uuid4().hex[:8]}"
            session_correlation = f"session_corr_{user['user_id']}_{int(time.time())}"
            
            user_sessions[user["user_id"]] = {
                "session_id": session_id,
                "correlation_id": session_correlation,
                "user": user
            }
            
            # Log session start
            self.logger.info(
                "User session started",
                extra={
                    "user_id": user["user_id"],
                    "session_id": session_id,
                    "correlation_id": session_correlation,
                    "organization_id": user["organization_id"],
                    "subscription_tier": user["subscription"],
                    "operation": "session_start",
                    "session_isolated": True,
                    "session_boundary": f"session_isolation_{user['user_id']}"
                }
            )
        
        # Simulate session activities
        for user_id, session_data in user_sessions.items():
            session_id = session_data["session_id"]
            correlation_id = session_data["correlation_id"]
            user = session_data["user"]
            
            # Multiple activities within the session
            activities = ["authenticate", "load_dashboard", "execute_agent", "save_results"]
            
            for activity in activities:
                self.logger.info(
                    f"Session activity: {activity}",
                    extra={
                        "user_id": user_id,
                        "session_id": session_id,
                        "correlation_id": correlation_id,
                        "organization_id": user["organization_id"],
                        "operation": activity,
                        "session_activity": True,
                        "activity_isolated": True
                    }
                )
        
        # Log session end
        for user_id, session_data in user_sessions.items():
            session_id = session_data["session_id"] 
            correlation_id = session_data["correlation_id"]
            user = session_data["user"]
            
            self.logger.info(
                "User session ended",
                extra={
                    "user_id": user_id,
                    "session_id": session_id,
                    "correlation_id": correlation_id,
                    "organization_id": user["organization_id"],
                    "operation": "session_end",
                    "session_duration_ms": 5000,  # Simulated duration
                    "activities_completed": 4
                }
            )
        
        # Validate session isolation
        session_logs = [log for log in self.captured_logs if hasattr(log, 'session_id')]
        
        # Group by session
        sessions_in_logs = {}
        for log in session_logs:
            session_id = log.session_id
            if session_id not in sessions_in_logs:
                sessions_in_logs[session_id] = []
            sessions_in_logs[session_id].append(log)
        
        # Validate each user has their own session
        assert len(sessions_in_logs) == len(self.test_users), f"Expected {len(self.test_users)} sessions"
        
        for user_id, session_data in user_sessions.items():
            session_id = session_data["session_id"]
            correlation_id = session_data["correlation_id"]
            
            assert session_id in sessions_in_logs, f"Session {session_id} not found in logs"
            
            session_logs_for_user = sessions_in_logs[session_id]
            expected_log_count = 6  # start + 4 activities + end
            assert len(session_logs_for_user) == expected_log_count, f"Expected {expected_log_count} logs for session {session_id}"
            
            # All logs in session should have same user_id and correlation_id
            for log in session_logs_for_user:
                assert log.user_id == user_id, f"User ID mismatch in session {session_id}"
                assert log.correlation_id == correlation_id, f"Correlation ID mismatch in session {session_id}"
        
        # Validate no session cross-contamination
        for session_id, logs in sessions_in_logs.items():
            session_user_id = logs[0].user_id  # All logs in session should have same user_id
            
            for other_session_id, other_logs in sessions_in_logs.items():
                if session_id == other_session_id:
                    continue
                
                # Check that this session's data doesn't appear in other sessions
                for other_log in other_logs:
                    assert other_log.session_id != session_id, f"Session ID leaked between sessions"
                    if hasattr(other_log, 'correlation_id') and hasattr(logs[0], 'correlation_id'):
                        assert other_log.correlation_id != logs[0].correlation_id, f"Correlation ID leaked between sessions"
        
        self.record_metric("session_isolation_test", "PASSED")
        self.record_metric("sessions_tested", len(user_sessions))
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_organization_level_isolation(self, real_services):
        """Test organization-level isolation in logging."""
        # Group users by organization
        orgs = {}
        for user in self.test_users:
            org_id = user["organization_id"]
            if org_id not in orgs:
                orgs[org_id] = []
            orgs[org_id].append(user)
        
        # Log organization-level operations
        for org_id, org_users in orgs.items():
            org_correlation = f"org_corr_{org_id}_{int(time.time())}"
            
            # Organization-wide operation
            self.logger.info(
                "Organization-wide policy update",
                extra={
                    "organization_id": org_id,
                    "correlation_id": org_correlation,
                    "operation": "policy_update",
                    "affected_users": len(org_users),
                    "org_isolated": True,
                    "organization_boundary": f"org_isolation_{org_id}",
                    "policy_type": "security_policy"
                }
            )
            
            # Individual user operations within org context
            for user in org_users:
                self.logger.info(
                    "User operation under org policy",
                    extra={
                        "user_id": user["user_id"],
                        "organization_id": org_id,
                        "correlation_id": org_correlation,  # Shared org correlation
                        "operation": "user_policy_acknowledgment",
                        "subscription_tier": user["subscription"],
                        "org_context": True,
                        "user_in_org_context": True
                    }
                )
        
        # Validate organization isolation
        org_logs = [log for log in self.captured_logs if hasattr(log, 'organization_id')]
        
        # Group by organization
        orgs_in_logs = {}
        for log in org_logs:
            org_id = log.organization_id
            if org_id not in orgs_in_logs:
                orgs_in_logs[org_id] = []
            orgs_in_logs[org_id].append(log)
        
        # Validate each organization has correct logs
        for org_id, org_users in orgs.items():
            assert org_id in orgs_in_logs, f"No logs found for organization {org_id}"
            
            org_logs_list = orgs_in_logs[org_id]
            expected_count = 1 + len(org_users)  # org-wide log + user logs
            assert len(org_logs_list) == expected_count, f"Expected {expected_count} logs for org {org_id}"
            
            # Validate organization boundary
            for log in org_logs_list:
                assert log.organization_id == org_id, f"Organization ID mismatch: {log.organization_id}"
        
        # Validate no cross-organization data leakage
        for org_id, logs in orgs_in_logs.items():
            for other_org_id, other_logs in orgs_in_logs.items():
                if org_id == other_org_id:
                    continue
                
                # Check that this org's data doesn't appear in other orgs
                for other_log in other_logs:
                    # Organization isolation boundary should not leak
                    if hasattr(other_log, 'organization_boundary'):
                        assert org_id not in other_log.organization_boundary, f"Organization boundary leaked from {org_id} to {other_org_id}"
        
        self.record_metric("organization_isolation_test", "PASSED")
        self.record_metric("organizations_tested", len(orgs))
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_subscription_tier_isolation(self, real_services):
        """Test that subscription tier information is properly isolated and protected."""
        # Log operations with subscription-specific data
        for user in self.test_users:
            tier_correlation = f"tier_corr_{user['user_id']}_{int(time.time())}"
            
            # Subscription-specific operation
            self.logger.info(
                f"Subscription tier operation: {user['subscription']}",
                extra={
                    "user_id": user["user_id"],
                    "correlation_id": tier_correlation,
                    "subscription_tier": user["subscription"],
                    "organization_id": user["organization_id"],
                    "operation": "tier_specific_operation",
                    "tier_isolated": True,
                    # Subscription-specific features and limits
                    "features_enabled": self._get_tier_features(user["subscription"]),
                    "usage_limits": self._get_tier_limits(user["subscription"]),
                    "billing_info": {
                        "tier": user["subscription"],
                        "monthly_cost": self._get_tier_cost(user["subscription"]),
                        "billing_cycle": "monthly"
                    }
                }
            )
        
        # Validate subscription tier isolation
        tier_logs = [log for log in self.captured_logs if hasattr(log, 'subscription_tier')]
        
        # Group by subscription tier
        tiers_in_logs = {}
        for log in tier_logs:
            tier = log.subscription_tier
            if tier not in tiers_in_logs:
                tiers_in_logs[tier] = []
            tiers_in_logs[tier].append(log)
        
        # Validate each tier has appropriate isolation
        expected_tiers = set(user["subscription"] for user in self.test_users)
        assert set(tiers_in_logs.keys()) == expected_tiers, f"Tier mismatch in logs"
        
        # Validate no cross-tier information leakage
        for tier, logs in tiers_in_logs.items():
            for other_tier, other_logs in tiers_in_logs.items():
                if tier == other_tier:
                    continue
                
                # Get expected features and limits for each tier
                tier_features = self._get_tier_features(tier)
                tier_limits = self._get_tier_limits(tier)
                tier_cost = self._get_tier_cost(tier)
                
                # Check that this tier's specific data doesn't appear in other tier logs
                for other_log in other_logs:
                    other_log_content = str(other_log.__dict__)
                    
                    # Billing information should not leak between tiers
                    assert str(tier_cost) not in other_log_content, f"Tier {tier} cost leaked to tier {other_tier}"
                    
                    # Features should not leak between tiers (unless they overlap)
                    tier_specific_features = set(tier_features) - set(self._get_tier_features(other_tier))
                    for feature in tier_specific_features:
                        assert feature not in other_log_content, f"Tier {tier} feature '{feature}' leaked to tier {other_tier}"
        
        self.record_metric("subscription_tier_isolation_test", "PASSED")
        self.record_metric("subscription_tiers_tested", len(expected_tiers))
    
    def _get_tier_features(self, tier: str) -> List[str]:
        """Get features enabled for subscription tier."""
        tier_features = {
            "free": ["basic_analysis", "limited_support"],
            "professional": ["basic_analysis", "advanced_analysis", "priority_support", "api_access"],
            "enterprise": ["basic_analysis", "advanced_analysis", "priority_support", "api_access", "custom_models", "dedicated_support"]
        }
        return tier_features.get(tier, [])
    
    def _get_tier_limits(self, tier: str) -> Dict[str, Any]:
        """Get usage limits for subscription tier."""
        tier_limits = {
            "free": {"monthly_requests": 100, "concurrent_agents": 1, "data_retention_days": 30},
            "professional": {"monthly_requests": 1000, "concurrent_agents": 3, "data_retention_days": 90},
            "enterprise": {"monthly_requests": 10000, "concurrent_agents": 10, "data_retention_days": 365}
        }
        return tier_limits.get(tier, {})
    
    def _get_tier_cost(self, tier: str) -> float:
        """Get monthly cost for subscription tier."""
        tier_costs = {
            "free": 0.0,
            "professional": 49.99,
            "enterprise": 199.99
        }
        return tier_costs.get(tier, 0.0)
    
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Remove mock handler
        if hasattr(self, 'logger') and hasattr(self, 'mock_handler'):
            self.logger.removeHandler(self.mock_handler)
        
        # Clear captured logs
        self.captured_logs.clear()
        
        # Call parent teardown
        super().teardown_method(method)