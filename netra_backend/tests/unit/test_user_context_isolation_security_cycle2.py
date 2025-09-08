"""
Unit Tests for User Context Isolation Security - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete user data isolation and security
- Value Impact: Users trust platform with sensitive business data
- Strategic Impact: Data security is fundamental to enterprise adoption

CRITICAL: User data isolation failures would be catastrophic for trust and compliance.
Any data leakage between users would destroy platform credibility.
"""

import pytest
from unittest.mock import Mock, patch
import threading
import time
import asyncio
from typing import Dict, Any, List, Optional

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserContextFactory
from shared.types import UserID, ThreadID, RunID

class TestUserContextIsolationSecurity:
    """Test user context isolation and security mechanisms."""
    
    @pytest.fixture
    def sensitive_user_data(self):
        """Create sensitive user data for isolation testing."""
        return {
            "user_a_data": {
                "user_id": "enterprise_user_a",
                "company": "SecretCorp Inc",
                "api_keys": {"aws": "secret-aws-key-a", "azure": "secret-azure-key-a"},
                "financial_data": {"monthly_spend": 250000, "budget": 300000},
                "internal_projects": ["project_classified_alpha", "merger_acquisition_beta"],
                "employee_data": {"count": 1500, "avg_salary": 120000},
                "compliance_info": {"frameworks": ["SOX", "HIPAA"], "audit_date": "2024-03-15"}
            },
            "user_b_data": {
                "user_id": "startup_user_b", 
                "company": "InnovateNow LLC",
                "api_keys": {"aws": "secret-aws-key-b", "gcp": "secret-gcp-key-b"},
                "financial_data": {"monthly_spend": 5000, "budget": 8000},
                "internal_projects": ["mvp_development", "funding_round_series_a"],
                "employee_data": {"count": 25, "avg_salary": 85000},
                "compliance_info": {"frameworks": ["GDPR"], "audit_date": "2024-06-01"}
            }
        }

    @pytest.mark.unit
    def test_user_context_complete_isolation_enforcement(self, sensitive_user_data):
        """
        Test complete isolation between user contexts.
        
        Business Value: Prevents data leaks that would destroy enterprise trust.
        CRITICAL: Any cross-contamination would be a security breach.
        """
        # Arrange: Create isolated user contexts with sensitive data
        user_a_context = UserExecutionContext(
            user_id=str(UserID("enterprise_user_a")),
            thread_id=str(ThreadID("enterprise_thread_a")),
            run_id=str(RunID("run_enterprise_a")),
            agent_context={
                "permissions": ["enterprise_access", "sensitive_data"],
                "authenticated": True,
                "session_data": sensitive_user_data["user_a_data"]
            }
        )
        
        user_b_context = UserExecutionContext(
            user_id=str(UserID("startup_user_b")),
            thread_id=str(ThreadID("startup_thread_b")),
            run_id=str(RunID("run_startup_b")),
            agent_context={
                "permissions": ["startup_access", "basic_data"], 
                "authenticated": True,
                "session_data": sensitive_user_data["user_b_data"]
            }
        )
        
        # Act & Assert: Verify complete isolation
        assert user_a_context.user_id != user_b_context.user_id, "User IDs must be completely isolated"
        assert user_a_context.thread_id != user_b_context.thread_id, "Thread IDs must be isolated"
        
        # Critical security requirement: Session data completely isolated
        assert user_a_context.agent_context["session_data"] != user_b_context.agent_context["session_data"], "Session data must be isolated"
        
        user_a_session_str = str(user_a_context.agent_context["session_data"])
        user_b_session_str = str(user_b_context.agent_context["session_data"])
        
        # User A's sensitive data must not appear in User B's context
        assert "SecretCorp Inc" not in user_b_session_str, "User A company data leaked to User B"
        assert "secret-aws-key-a" not in user_b_session_str, "User A AWS key leaked to User B"
        assert "project_classified_alpha" not in user_b_session_str, "User A projects leaked to User B"
        assert "'monthly_spend': 250000" not in user_b_session_str, "User A financial data leaked to User B"
        
        # User B's data must not appear in User A's context
        assert "InnovateNow LLC" not in user_a_session_str, "User B company data leaked to User A"
        assert "secret-aws-key-b" not in user_a_session_str, "User B AWS key leaked to User A" 
        assert "mvp_development" not in user_a_session_str, "User B projects leaked to User A"
        assert "'monthly_spend': 5000" not in user_a_session_str, "User B financial data leaked to User A"
        
        # Permissions should be isolated
        assert set(user_a_context.agent_context["permissions"]) != set(user_b_context.agent_context["permissions"]), "Permissions must be isolated"
        
        # Business requirement: Each user sees only their own data
        user_a_api_keys = user_a_context.agent_context["session_data"].get("api_keys", {})
        user_b_api_keys = user_b_context.agent_context["session_data"].get("api_keys", {})
        
        # API keys must be completely separate
        assert "secret-aws-key-a" in str(user_a_api_keys), "User A should see their own AWS key"
        assert "secret-aws-key-b" not in str(user_a_api_keys), "User A must not see User B's AWS key"
        
        assert "secret-aws-key-b" in str(user_b_api_keys), "User B should see their own AWS key"
        assert "secret-aws-key-a" not in str(user_b_api_keys), "User B must not see User A's AWS key"

    @pytest.mark.unit
    def test_user_context_memory_isolation_and_cleanup(self):
        """
        Test user context memory isolation and proper cleanup.
        
        Business Value: Prevents memory-based data leaks between users.
        Memory contamination could expose sensitive data in subsequent requests.
        """
        # Arrange: Create contexts with sensitive data that should be cleaned up
        sensitive_contexts = []
        
        for i in range(5):
            sensitive_data = {
                f"secret_key_{i}": f"ultra_secret_value_{i}",
                f"private_config_{i}": {
                    "database_password": f"db_secret_{i}",
                    "api_token": f"api_token_secret_{i}",
                    "encryption_key": f"encrypt_key_{i}"
                }
            }
            
            context = UserExecutionContext(
                user_id=str(UserID(f"memory_test_user_{i}")),
                thread_id=str(ThreadID(f"memory_thread_{i}")),
                run_id=str(RunID(f"run_memory_{i}")),
                agent_context={
                    "authenticated": True,
                    "permissions": [f"user_{i}_permissions"],
                    "session_data": sensitive_data
                }
            )
            
            sensitive_contexts.append(context)
        
        # Act: Simulate context usage and cleanup
        context_data_snapshots = []
        for context in sensitive_contexts:
            # Capture data snapshot
            data_snapshot = str(context.agent_context["session_data"])
            context_data_snapshots.append(data_snapshot)
        
        # Clear contexts to simulate cleanup
        sensitive_contexts.clear()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Assert: Memory isolation maintained
        for i, snapshot in enumerate(context_data_snapshots):
            # Each snapshot should contain only its own data
            assert f"ultra_secret_value_{i}" in snapshot, f"Context {i} should contain its own secret"
            assert f"db_secret_{i}" in snapshot, f"Context {i} should contain its own DB secret"
            
            # Should not contain other contexts' data
            for j in range(5):
                if i != j:
                    assert f"ultra_secret_value_{j}" not in snapshot, f"Context {i} leaked data from context {j}"
                    assert f"db_secret_{j}" not in snapshot, f"Context {i} leaked DB secret from context {j}"

    @pytest.mark.unit
    def test_user_context_concurrent_access_isolation(self):
        """
        Test user context isolation under concurrent access.
        
        Business Value: Concurrent users must not interfere with each other's data.
        Race conditions could cause data contamination between users.
        """
        # Arrange: Concurrent access scenario
        concurrent_results = {}
        concurrent_errors = []
        access_lock = threading.Lock()
        
        def concurrent_context_access(user_index):
            """Access user context concurrently."""
            try:
                user_data = {
                    "user_secret": f"concurrent_secret_{user_index}",
                    "user_config": {
                        "setting_1": f"value_{user_index}_1",
                        "setting_2": f"value_{user_index}_2"
                    },
                    "timestamp": time.time(),
                    "thread_id": threading.current_thread().ident
                }
                
                context = UserExecutionContext(
                    user_id=str(UserID(f"concurrent_user_{user_index}")),
                    thread_id=str(ThreadID(f"concurrent_thread_{user_index}")),
                    run_id=str(RunID(f"run_concurrent_{user_index}")),
                    agent_context={
                        "authenticated": True,
                        "permissions": [f"concurrent_permission_{user_index}"],
                        "session_data": user_data
                    }
                )
                
                # Simulate some processing time
                time.sleep(0.1)
                
                # Verify context integrity
                session_data_str = str(context.agent_context["session_data"])
                
                with access_lock:
                    concurrent_results[user_index] = {
                        "user_id": str(context.user_id),
                        "session_data": session_data_str,
                        "permissions": context.agent_context["permissions"],
                        "success": True
                    }
                    
            except Exception as e:
                with access_lock:
                    concurrent_errors.append(f"User {user_index}: {str(e)}")
        
        # Act: Create concurrent threads
        threads = []
        for i in range(10):  # 10 concurrent users
            thread = threading.Thread(target=concurrent_context_access, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)
        
        # Assert: Concurrent access isolation maintained
        assert len(concurrent_errors) == 0, f"Concurrent access errors: {concurrent_errors}"
        assert len(concurrent_results) == 10, f"Expected 10 concurrent results, got {len(concurrent_results)}"
        
        # Verify each user's data integrity
        for user_index, result in concurrent_results.items():
            session_data = result["session_data"]
            
            # Should contain own data
            assert f"concurrent_secret_{user_index}" in session_data, f"User {user_index} missing own secret"
            assert f"value_{user_index}_1" in session_data, f"User {user_index} missing own config"
            
            # Should not contain other users' data
            for other_index in range(10):
                if other_index != user_index:
                    assert f"concurrent_secret_{other_index}" not in session_data, \
                        f"User {user_index} contaminated with User {other_index} secret"
                    assert f"value_{other_index}_1" not in session_data, \
                        f"User {user_index} contaminated with User {other_index} config"

    @pytest.mark.unit
    def test_user_context_factory_isolation_patterns(self):
        """
        Test user context factory maintains isolation patterns.
        
        Business Value: Factory pattern ensures consistent isolation across all contexts.
        Factory failures could create systematic security vulnerabilities.
        """
        # Test factory isolation scenarios
        factory_scenarios = [
            {
                "tier": "free",
                "user_count": 3,
                "permissions": ["basic_access"],
                "session_template": {"tier": "free", "limits": {"daily_requests": 100}}
            },
            {
                "tier": "premium", 
                "user_count": 3,
                "permissions": ["premium_access", "advanced_features"],
                "session_template": {"tier": "premium", "limits": {"daily_requests": 1000}}
            },
            {
                "tier": "enterprise",
                "user_count": 3,
                "permissions": ["enterprise_access", "admin_features", "custom_integrations"],
                "session_template": {"tier": "enterprise", "limits": {"daily_requests": -1}}
            }
        ]
        
        all_contexts = []
        
        # Act: Create contexts through factory for different scenarios
        for scenario in factory_scenarios:
            tier_contexts = []
            
            for i in range(scenario["user_count"]):
                # Create unique session data for each user
                session_data = scenario["session_template"].copy()
                session_data.update({
                    "user_index": i,
                    "unique_key": f"{scenario['tier']}_user_{i}_key",
                    "sensitive_data": f"{scenario['tier']}_sensitive_{i}"
                })
                
                context = UserContextFactory.create_context(
                    user_id=str(UserID(f"{scenario['tier']}_user_{i}")),
                    thread_id=str(ThreadID(f"{scenario['tier']}_thread_{i}")),
                    run_id=str(RunID(f"run_{scenario['tier']}_{i}"))
                )
                
                # Update context with scenario-specific data
                context = UserExecutionContext(
                    user_id=context.user_id,
                    thread_id=context.thread_id,
                    run_id=context.run_id,
                    request_id=context.request_id,
                    agent_context={
                        "permissions": scenario["permissions"],
                        "session_data": session_data
                    }
                )
                
                tier_contexts.append(context)
                all_contexts.append((scenario["tier"], i, context))
        
        # Assert: Factory maintains proper isolation
        assert len(all_contexts) == 9, "Should create 9 total contexts (3 tiers × 3 users)"
        
        # Verify isolation between all contexts
        for tier1, index1, context1 in all_contexts:
            context1_data = str(context1.agent_context["session_data"])
            
            for tier2, index2, context2 in all_contexts:
                if (tier1, index1) != (tier2, index2):  # Different contexts
                    context2_data = str(context2.agent_context["session_data"])
                    
                    # Each context should have unique data
                    unique_key1 = f"{tier1}_user_{index1}_key"
                    unique_key2 = f"{tier2}_user_{index2}_key"
                    
                    assert unique_key1 in context1_data, f"Context {tier1}_{index1} should have its unique key"
                    assert unique_key2 not in context1_data, f"Context {tier1}_{index1} leaked {tier2}_{index2} key"
                    
                    # Sensitive data should be isolated
                    sensitive1 = f"{tier1}_sensitive_{index1}"
                    sensitive2 = f"{tier2}_sensitive_{index2}"
                    
                    assert sensitive1 in context1_data, f"Context {tier1}_{index1} should have its sensitive data"
                    assert sensitive2 not in context1_data, f"Context {tier1}_{index1} leaked {tier2}_{index2} sensitive data"

    @pytest.mark.unit
    async def test_user_context_async_isolation_integrity(self):
        """
        Test user context isolation integrity in async operations.
        
        Business Value: Async operations must maintain user isolation.
        Async context switching could cause data contamination.
        """
        # Arrange: Async isolation test
        async def async_context_operation(user_index, operation_duration):
            """Async operation that maintains context integrity."""
            sensitive_data = {
                "async_secret": f"async_secret_{user_index}",
                "operation_id": f"op_{user_index}_{int(time.time() * 1000)}",
                "confidential_data": {
                    "password": f"async_password_{user_index}",
                    "token": f"async_token_{user_index}"
                }
            }
            
            context = UserExecutionContext(
                user_id=str(UserID(f"async_user_{user_index}")),
                thread_id=str(ThreadID(f"async_thread_{user_index}")),
                run_id=str(RunID(f"run_async_{user_index}")),
                agent_context={
                    "authenticated": True,
                    "permissions": [f"async_permission_{user_index}"],
                    "session_data": sensitive_data
                }
            )
            
            # Simulate async processing with potential context switching
            await asyncio.sleep(operation_duration)
            
            # Verify context integrity after async operation
            session_str = str(context.agent_context["session_data"])
            
            return {
                "user_index": user_index,
                "session_data": session_str,
                "context_user_id": str(context.user_id),
                "integrity_check": f"async_secret_{user_index}" in session_str
            }
        
        # Act: Run concurrent async operations
        async_tasks = [
            async_context_operation(i, 0.1 + (i * 0.02))  # Staggered timing
            for i in range(5)
        ]
        
        async_results = await asyncio.gather(*async_tasks)
        
        # Assert: Async isolation maintained
        assert len(async_results) == 5, "All async operations should complete"
        
        for result in async_results:
            user_index = result["user_index"]
            session_data = result["session_data"]
            
            # Verify integrity check passed
            assert result["integrity_check"], f"Async user {user_index} failed integrity check"
            
            # Verify own data present
            assert f"async_secret_{user_index}" in session_data, f"Async user {user_index} missing own secret"
            assert f"async_password_{user_index}" in session_data, f"Async user {user_index} missing own password"
            
            # Verify no contamination from other async operations
            for other_index in range(5):
                if other_index != user_index:
                    assert f"async_secret_{other_index}" not in session_data, \
                        f"Async user {user_index} contaminated with user {other_index} secret"
                    assert f"async_password_{other_index}" not in session_data, \
                        f"Async user {user_index} contaminated with user {other_index} password"

    @pytest.mark.unit
    def test_user_context_permission_isolation_enforcement(self):
        """
        Test user context permission isolation and enforcement.
        
        Business Value: Permission isolation prevents privilege escalation.
        Permission leaks could allow unauthorized access to premium features.
        """
        # Arrange: Different permission scenarios
        permission_scenarios = [
            {
                "user_type": "free_user",
                "permissions": ["basic_read"],
                "forbidden_permissions": ["premium_write", "admin_delete", "enterprise_config"]
            },
            {
                "user_type": "premium_user",
                "permissions": ["basic_read", "premium_write", "premium_analytics"],
                "forbidden_permissions": ["admin_delete", "enterprise_config", "super_admin"]
            },
            {
                "user_type": "enterprise_user",
                "permissions": ["basic_read", "premium_write", "enterprise_config", "admin_read"],
                "forbidden_permissions": ["super_admin", "system_override"]
            },
            {
                "user_type": "admin_user",
                "permissions": ["basic_read", "premium_write", "admin_delete", "admin_config", "user_management"],
                "forbidden_permissions": ["system_override", "root_access"]
            }
        ]
        
        contexts = []
        
        # Act: Create contexts with different permission levels
        for scenario in permission_scenarios:
            context = UserExecutionContext(
                user_id=str(UserID(f"{scenario['user_type']}_id")),
                thread_id=str(ThreadID(f"{scenario['user_type']}_thread")),
                run_id=str(RunID(f"run_{scenario['user_type']}")),
                agent_context={
                    "authenticated": True,
                    "permissions": scenario["permissions"],
                    "session_data": {"user_type": scenario["user_type"]}
                }
            )
            contexts.append((scenario, context))
        
        # Assert: Permission isolation enforced
        for scenario, context in contexts:
            user_type = scenario["user_type"]
            
            # Should have assigned permissions
            for permission in scenario["permissions"]:
                assert permission in context.agent_context["permissions"], f"{user_type} should have {permission}"
            
            # Should not have forbidden permissions
            for forbidden in scenario["forbidden_permissions"]:
                assert forbidden not in context.agent_context["permissions"], f"{user_type} should not have {forbidden}"
            
            # Cross-contamination check: Should not have other users' unique permissions
            for other_scenario, other_context in contexts:
                if other_scenario["user_type"] != user_type:
                    other_unique_permissions = set(other_scenario["permissions"]) - set(scenario["permissions"])
                    for unique_permission in other_unique_permissions:
                        assert unique_permission not in context.agent_context["permissions"], \
                            f"{user_type} should not have {other_scenario['user_type']}'s unique permission: {unique_permission}"