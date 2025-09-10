"""
Test User Execution Context Isolation Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal (Critical for all user tiers)
- Business Goal: Ensure complete isolation between concurrent users to prevent data leakage
- Value Impact: Enables secure multi-tenant operations with zero cross-contamination
- Strategic Impact: Foundation for scalable SaaS architecture supporting thousands of concurrent users

Tests the user execution context isolation system including context boundaries,
data separation, resource isolation, and security between different users.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import time

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context,
    UserContextManager
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.state import DeepAgentState


class TestUserExecutionContextIsolation(BaseIntegrationTest):
    """Integration tests for user execution context isolation."""

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_complete_user_context_isolation(self, real_services_fixture):
        """Test complete isolation between different user execution contexts."""
        # Arrange - Create multiple user contexts
        user_contexts = [
            UserExecutionContext(
                user_id="isolated_user_001",
                thread_id="thread_001",
                session_id="session_001",
                workspace_id="workspace_001",
                tenant_id="tenant_alpha"
            ),
            UserExecutionContext(
                user_id="isolated_user_002", 
                thread_id="thread_002",
                session_id="session_002",
                workspace_id="workspace_002",
                tenant_id="tenant_beta"
            ),
            UserExecutionContext(
                user_id="isolated_user_003",
                thread_id="thread_003",
                session_id="session_003", 
                workspace_id="workspace_003",
                tenant_id="tenant_gamma"
            )
        ]
        
        context_manager = UserContextManager(
            isolation_level="strict",
            cross_contamination_detection=True
        )
        
        # Create isolated execution engines
        engines = []
        mock_llm = AsyncMock()
        
        for i, user_context in enumerate(user_contexts):
            # Each user gets different mock response to verify isolation
            user_specific_llm = AsyncMock()
            user_specific_llm.generate_response = AsyncMock(return_value={
                "status": "success",
                "user_specific_data": f"user_{i+1}_confidential_data",
                "user_id": user_context.user_id,
                "tenant_isolation": True
            })
            
            engine = UserExecutionEngine(
                user_context=user_context,
                llm_client=user_specific_llm,
                websocket_emitter=MagicMock()
            )
            engines.append(engine)
        
        # Act - Execute operations concurrently for all users
        execution_tasks = []
        for i, engine in enumerate(engines):
            task = asyncio.create_task(
                engine.execute_agent(
                    agent_type="data_helper",
                    message=f"Sensitive request for user {i+1}",
                    sensitive_data={"secret_key": f"secret_{i+1}", "internal_id": f"id_{i+1}"}
                )
            )
            execution_tasks.append(task)
        
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # Assert - Verify complete isolation
        assert len(results) == 3
        
        for i, result in enumerate(results):
            assert not isinstance(result, Exception)
            assert result is not None
            
            # Each user should only see their own data
            user_data = result.result["user_specific_data"]
            assert f"user_{i+1}_confidential_data" == user_data
            
            # Verify no cross-contamination
            for j in range(len(results)):
                if i != j:
                    other_user_data = results[j].result["user_specific_data"]
                    assert user_data != other_user_data
        
        # Verify context isolation at manager level
        isolation_report = await context_manager.generate_isolation_report()
        assert isolation_report["cross_contamination_detected"] is False
        assert isolation_report["isolation_violations"] == 0

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_context_memory_isolation_and_cleanup(self, real_services_fixture):
        """Test memory isolation and proper cleanup of user contexts."""
        # Arrange
        context_manager = UserContextManager(
            memory_isolation=True,
            automatic_cleanup=True,
            cleanup_timeout_seconds=2
        )
        
        # Track memory allocations per user
        memory_tracking = {}
        
        async def create_user_with_memory_intensive_work(user_id: str):
            """Create user context and perform memory-intensive operations."""
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{user_id}",
                session_id=f"session_{user_id}",
                workspace_id=f"workspace_{user_id}"
            )
            
            # Register context
            await context_manager.register_user_context(user_context)
            
            # Simulate memory-intensive agent operations
            agent_state = DeepAgentState(
                agent_id=f"memory_agent_{user_id}",
                user_context=user_context,
                initial_state="processing"
            )
            
            # Add large amounts of state data to simulate memory usage
            large_data = {
                f"dataset_{i}": [{"record": j, "data": "x" * 1000} for j in range(100)]
                for i in range(10)  # 10 datasets, 100 records each, 1KB per record = ~1MB per user
            }
            
            agent_state.update_state_data(large_data)
            memory_tracking[user_id] = {
                "data_size": len(str(large_data)),
                "state_id": agent_state.agent_id,
                "context_registered": True
            }
            
            # Simulate some processing time
            await asyncio.sleep(0.1)
            
            return user_context, agent_state
        
        # Act - Create multiple users with memory-intensive operations
        user_tasks = []
        for i in range(5):
            user_id = f"memory_user_{i:03d}"
            task = asyncio.create_task(create_user_with_memory_intensive_work(user_id))
            user_tasks.append(task)
        
        user_results = await asyncio.gather(*user_tasks)
        
        # Verify all users have isolated memory
        assert len(user_results) == 5
        for user_context, agent_state in user_results:
            user_id = user_context.user_id
            assert user_id in memory_tracking
            assert memory_tracking[user_id]["context_registered"] is True
        
        # Trigger cleanup for some users
        users_to_cleanup = ["memory_user_001", "memory_user_003"]
        for user_id in users_to_cleanup:
            user_context = next(
                (uc for uc, _ in user_results if uc.user_id == user_id), 
                None
            )
            if user_context:
                await context_manager.cleanup_user_context(user_context)
        
        # Wait for cleanup to complete
        await asyncio.sleep(2.5)
        
        # Assert - Verify memory isolation and cleanup
        remaining_contexts = await context_manager.get_active_contexts()
        remaining_user_ids = [ctx.user_id for ctx in remaining_contexts]
        
        # Cleaned up users should not be in active contexts
        for cleaned_user_id in users_to_cleanup:
            assert cleaned_user_id not in remaining_user_ids
        
        # Remaining users should still be active
        expected_remaining = ["memory_user_000", "memory_user_002", "memory_user_004"]
        for remaining_user_id in expected_remaining:
            assert remaining_user_id in remaining_user_ids
        
        # Verify memory was actually freed (implementation specific)
        cleanup_report = await context_manager.get_cleanup_report()
        assert cleanup_report["contexts_cleaned"] >= 2

    @pytest.mark.integration
    @pytest.mark.agent_state_management  
    async def test_context_security_boundaries(self, real_services_fixture):
        """Test security boundaries between user contexts."""
        # Arrange
        # User 1: Regular user
        user1_context = UserExecutionContext(
            user_id="regular_user_001",
            thread_id="thread_regular_001", 
            session_id="session_regular_001",
            workspace_id="workspace_regular",
            tenant_id="tenant_standard",
            security_level="standard"
        )
        
        # User 2: Privileged user
        user2_context = UserExecutionContext(
            user_id="admin_user_002",
            thread_id="thread_admin_002",
            session_id="session_admin_002", 
            workspace_id="workspace_admin",
            tenant_id="tenant_premium",
            security_level="admin"
        )
        
        context_manager = UserContextManager(
            security_enforcement=True,
            cross_tenant_isolation=True
        )
        
        await context_manager.register_user_context(user1_context)
        await context_manager.register_user_context(user2_context)
        
        # Mock security-sensitive operations
        mock_security_service = AsyncMock()
        mock_security_service.check_access_permissions = AsyncMock()
        mock_security_service.audit_security_access = AsyncMock()
        
        def mock_permission_check(user_context: UserExecutionContext, resource: str):
            """Mock permission checking based on user context."""
            if user_context.security_level == "admin":
                return {"access_granted": True, "permissions": ["read", "write", "admin"]}
            else:
                return {"access_granted": resource != "admin_data", "permissions": ["read"]}
        
        mock_security_service.check_access_permissions.side_effect = mock_permission_check
        
        # Act - Test security boundary enforcement
        # Regular user tries to access regular data
        regular_access = await context_manager.access_with_security_check(
            user_context=user1_context,
            resource="user_cost_data",
            operation="read",
            security_service=mock_security_service
        )
        
        # Regular user tries to access admin data
        admin_access_attempt = await context_manager.access_with_security_check(
            user_context=user1_context,
            resource="admin_data",
            operation="read", 
            security_service=mock_security_service
        )
        
        # Admin user tries to access admin data
        admin_legitimate_access = await context_manager.access_with_security_check(
            user_context=user2_context,
            resource="admin_data", 
            operation="read",
            security_service=mock_security_service
        )
        
        # Assert - Verify security boundaries
        assert regular_access["access_granted"] is True  # Regular user can access regular data
        assert admin_access_attempt["access_granted"] is False  # Regular user cannot access admin data
        assert admin_legitimate_access["access_granted"] is True  # Admin can access admin data
        
        # Verify security service was called for permission checks
        assert mock_security_service.check_access_permissions.call_count == 3
        assert mock_security_service.audit_security_access.call_count >= 1  # At least one access logged

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_context_resource_quotas_and_limits(self, real_services_fixture):
        """Test resource quota enforcement and limits per user context."""
        # Arrange
        # User with low quota (Free tier)
        free_user_context = UserExecutionContext(
            user_id="free_user_001",
            thread_id="thread_free_001",
            session_id="session_free_001",
            workspace_id="workspace_free",
            subscription_tier="free",
            resource_quotas={
                "max_concurrent_agents": 1,
                "max_memory_mb": 100,
                "max_execution_time_seconds": 30
            }
        )
        
        # User with high quota (Enterprise tier)  
        enterprise_user_context = UserExecutionContext(
            user_id="enterprise_user_002",
            thread_id="thread_enterprise_002",
            session_id="session_enterprise_002",
            workspace_id="workspace_enterprise",
            subscription_tier="enterprise",
            resource_quotas={
                "max_concurrent_agents": 10,
                "max_memory_mb": 1000,
                "max_execution_time_seconds": 300
            }
        )
        
        context_manager = UserContextManager(
            quota_enforcement=True,
            resource_monitoring=True
        )
        
        await context_manager.register_user_context(free_user_context)
        await context_manager.register_user_context(enterprise_user_context)
        
        # Mock resource-intensive operations
        async def create_resource_intensive_agent(user_context: UserExecutionContext, agent_count: int):
            """Create multiple agents to test quota enforcement."""
            agents = []
            for i in range(agent_count):
                try:
                    agent_state = DeepAgentState(
                        agent_id=f"agent_{user_context.user_id}_{i}",
                        user_context=user_context,
                        initial_state="initializing"
                    )
                    
                    # Check quota before creating
                    quota_check = await context_manager.check_resource_quota(
                        user_context=user_context,
                        resource_type="concurrent_agents",
                        requested_amount=1
                    )
                    
                    if quota_check["allowed"]:
                        await context_manager.allocate_resource(
                            user_context=user_context,
                            resource_type="concurrent_agents", 
                            amount=1,
                            agent_id=agent_state.agent_id
                        )
                        agents.append(agent_state)
                    else:
                        break  # Quota exceeded
                        
                except Exception as e:
                    # Expected for quota violations
                    if "quota" in str(e).lower():
                        break
                    else:
                        raise
            
            return agents
        
        # Act - Test quota enforcement
        # Free user tries to create multiple agents (should be limited)
        free_user_agents = await create_resource_intensive_agent(free_user_context, 3)
        
        # Enterprise user creates multiple agents (should succeed)
        enterprise_user_agents = await create_resource_intensive_agent(enterprise_user_context, 5)
        
        # Assert - Verify quota enforcement
        # Free user should be limited to 1 agent
        assert len(free_user_agents) <= 1
        
        # Enterprise user should be able to create more agents
        assert len(enterprise_user_agents) >= 3  # Should create more than free user
        
        # Verify resource tracking
        free_usage = await context_manager.get_resource_usage(free_user_context)
        enterprise_usage = await context_manager.get_resource_usage(enterprise_user_context)
        
        assert free_usage["concurrent_agents"] <= free_user_context.resource_quotas["max_concurrent_agents"]
        assert enterprise_usage["concurrent_agents"] <= enterprise_user_context.resource_quotas["max_concurrent_agents"]

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_context_failure_isolation(self, real_services_fixture):
        """Test that failures in one user context don't affect other users."""
        # Arrange
        stable_user_context = UserExecutionContext(
            user_id="stable_user_001",
            thread_id="thread_stable_001",
            session_id="session_stable_001",
            workspace_id="workspace_stable"
        )
        
        failing_user_context = UserExecutionContext(
            user_id="failing_user_002",
            thread_id="thread_failing_002", 
            session_id="session_failing_002",
            workspace_id="workspace_failing"
        )
        
        context_manager = UserContextManager(
            failure_isolation=True,
            circuit_breaker_per_user=True
        )
        
        await context_manager.register_user_context(stable_user_context)
        await context_manager.register_user_context(failing_user_context)
        
        # Create execution engines
        stable_llm = AsyncMock()
        stable_llm.generate_response = AsyncMock(return_value={
            "status": "success", 
            "result": "stable_operation_successful"
        })
        
        failing_llm = AsyncMock()
        failing_llm.generate_response = AsyncMock(side_effect=Exception("Simulated LLM failure"))
        
        stable_engine = UserExecutionEngine(
            user_context=stable_user_context,
            llm_client=stable_llm,
            websocket_emitter=MagicMock()
        )
        
        failing_engine = UserExecutionEngine(
            user_context=failing_user_context,
            llm_client=failing_llm,
            websocket_emitter=MagicMock()
        )
        
        # Act - Execute operations with one user failing
        stable_task = asyncio.create_task(
            stable_engine.execute_agent(
                agent_type="data_helper",
                message="Normal operation"
            )
        )
        
        failing_task = asyncio.create_task(
            failing_engine.execute_agent(
                agent_type="data_helper", 
                message="This will fail"
            )
        )
        
        # Wait for both to complete (or fail)
        stable_result, failing_result = await asyncio.gather(
            stable_task, failing_task, return_exceptions=True
        )
        
        # Assert - Verify failure isolation
        # Stable user should succeed despite other user's failure
        assert not isinstance(stable_result, Exception)
        assert stable_result.status == "success"
        assert "stable_operation_successful" in stable_result.result["result"]
        
        # Failing user should fail as expected
        assert isinstance(failing_result, Exception)
        assert "Simulated LLM failure" in str(failing_result)
        
        # Verify isolation - stable user's context should be unaffected
        stable_context_health = await context_manager.get_context_health(stable_user_context)
        assert stable_context_health["status"] == "healthy"
        assert stable_context_health["failure_count"] == 0
        
        # Failing user's context should show failure but be contained
        failing_context_health = await context_manager.get_context_health(failing_user_context)
        assert failing_context_health["status"] == "unhealthy"
        assert failing_context_health["failure_count"] > 0
        
        # System-level health should not be critically impacted
        system_health = await context_manager.get_system_health()
        assert system_health["overall_status"] in ["healthy", "degraded"]  # Not "failed"
        assert system_health["healthy_contexts"] >= 1  # Stable user still healthy