"""
Test Agent Execution Context Management Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure proper context isolation and state management across agent executions
- Value Impact: Enables reliable multi-user concurrent agent operations without data leakage
- Strategic Impact: Foundation for scalable multi-tenant architecture

Tests the agent execution context management including state transitions,
context isolation, and proper cleanup of execution contexts.
"""

import asyncio
import pytest
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.supervisor.agent_execution_context_manager import (
    AgentExecutionContextManager
)
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    ExecutionStatus
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.state import DeepAgentState


class TestAgentExecutionContextManagement(BaseIntegrationTest):
    """Integration tests for agent execution context management."""

    @pytest.mark.integration
    @pytest.mark.context_management
    async def test_execution_context_lifecycle_management(self, real_services_fixture):
        """Test complete execution context lifecycle from creation to cleanup."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_200",
            thread_id="thread_500", 
            session_id="session_800",
            workspace_id="workspace_100"
        )
        
        context_manager = AgentExecutionContextManager()
        
        # Act - Create execution context
        execution_id = str(uuid4())
        execution_context = await context_manager.create_execution_context(
            execution_id=execution_id,
            user_context=user_context,
            agent_type="triage_agent",
            message="Test message"
        )
        
        # Verify creation
        assert execution_context is not None
        assert execution_context.execution_id == execution_id
        assert execution_context.user_context.user_id == user_context.user_id
        assert execution_context.status == ExecutionStatus.CREATED
        
        # Update context status
        await context_manager.update_execution_status(
            execution_id=execution_id,
            status=ExecutionStatus.RUNNING
        )
        
        updated_context = await context_manager.get_execution_context(execution_id)
        assert updated_context.status == ExecutionStatus.RUNNING
        
        # Complete execution
        result = AgentExecutionResult(
            execution_id=execution_id,
            status="success",
            result={"analysis": "completed"},
            execution_time_ms=150
        )
        
        await context_manager.complete_execution(execution_id, result)
        
        # Verify completion and cleanup
        final_context = await context_manager.get_execution_context(execution_id)
        assert final_context.status == ExecutionStatus.COMPLETED
        assert final_context.result is not None

    @pytest.mark.integration
    @pytest.mark.context_management
    async def test_concurrent_context_isolation(self, real_services_fixture):
        """Test isolation between concurrent execution contexts for different users."""
        # Arrange
        user1_context = UserExecutionContext(
            user_id="user_001",
            thread_id="thread_001",
            session_id="session_001", 
            workspace_id="workspace_001"
        )
        
        user2_context = UserExecutionContext(
            user_id="user_002", 
            thread_id="thread_002",
            session_id="session_002",
            workspace_id="workspace_002"
        )
        
        context_manager = AgentExecutionContextManager()
        
        # Act - Create concurrent executions
        execution_id_1 = str(uuid4())
        execution_id_2 = str(uuid4()) 
        
        context_1 = await context_manager.create_execution_context(
            execution_id=execution_id_1,
            user_context=user1_context,
            agent_type="data_helper",
            message="User 1 query"
        )
        
        context_2 = await context_manager.create_execution_context(
            execution_id=execution_id_2,
            user_context=user2_context,
            agent_type="data_helper", 
            message="User 2 query"
        )
        
        # Modify one context
        await context_manager.update_execution_data(
            execution_id=execution_id_1,
            data={"user_1_data": "sensitive_info"}
        )
        
        # Assert - Verify isolation
        context_1_retrieved = await context_manager.get_execution_context(execution_id_1)
        context_2_retrieved = await context_manager.get_execution_context(execution_id_2)
        
        assert context_1_retrieved.user_context.user_id == "user_001"
        assert context_2_retrieved.user_context.user_id == "user_002"
        
        # User 1's data should not be visible to User 2's context
        assert "user_1_data" in context_1_retrieved.execution_data
        assert "user_1_data" not in context_2_retrieved.execution_data
        
        # Verify complete separation
        assert context_1_retrieved.execution_id != context_2_retrieved.execution_id
        assert context_1_retrieved.user_context.workspace_id != context_2_retrieved.user_context.workspace_id

    @pytest.mark.integration
    @pytest.mark.context_management
    async def test_context_state_persistence_and_recovery(self, real_services_fixture):
        """Test context state persistence and recovery after system restart simulation."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_202",
            thread_id="thread_502",
            session_id="session_802", 
            workspace_id="workspace_102"
        )
        
        context_manager = AgentExecutionContextManager(
            persistent_storage=real_services_fixture.get("redis", MagicMock())
        )
        
        execution_id = str(uuid4())
        
        # Act - Create and persist context
        execution_context = await context_manager.create_execution_context(
            execution_id=execution_id,
            user_context=user_context,
            agent_type="apex_optimizer",
            message="Optimize infrastructure costs"
        )
        
        # Add execution data
        execution_data = {
            "analysis_progress": 0.6,
            "intermediate_results": {"cost_analysis": "in_progress"},
            "tools_used": ["cost_analyzer", "resource_optimizer"]
        }
        
        await context_manager.update_execution_data(execution_id, execution_data)
        await context_manager.persist_context_state(execution_id)
        
        # Simulate system restart - create new manager
        new_context_manager = AgentExecutionContextManager(
            persistent_storage=real_services_fixture.get("redis", MagicMock())
        )
        
        # Recovery
        recovered_context = await new_context_manager.recover_execution_context(execution_id)
        
        # Assert - Verify recovery
        assert recovered_context is not None
        assert recovered_context.execution_id == execution_id
        assert recovered_context.user_context.user_id == user_context.user_id
        assert recovered_context.execution_data["analysis_progress"] == 0.6
        assert "cost_analyzer" in recovered_context.execution_data["tools_used"]

    @pytest.mark.integration
    @pytest.mark.context_management 
    async def test_context_timeout_and_cleanup(self, real_services_fixture):
        """Test context timeout handling and automatic cleanup."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_203", 
            thread_id="thread_503",
            session_id="session_803",
            workspace_id="workspace_103"
        )
        
        context_manager = AgentExecutionContextManager(
            default_timeout_seconds=2  # Short timeout for testing
        )
        
        execution_id = str(uuid4())
        
        # Act - Create context that will timeout
        execution_context = await context_manager.create_execution_context(
            execution_id=execution_id,
            user_context=user_context,
            agent_type="slow_agent",
            message="Long running task"
        )
        
        # Start execution but don't complete
        await context_manager.update_execution_status(execution_id, ExecutionStatus.RUNNING)
        
        # Wait for timeout
        await asyncio.sleep(3)
        
        # Trigger timeout cleanup
        await context_manager.cleanup_timed_out_contexts()
        
        # Assert - Context should be marked as timed out
        context_after_timeout = await context_manager.get_execution_context(execution_id)
        assert context_after_timeout.status == ExecutionStatus.TIMEOUT
        assert context_after_timeout.error_message is not None
        assert "timeout" in context_after_timeout.error_message.lower()

    @pytest.mark.integration
    @pytest.mark.context_management
    async def test_context_memory_management_and_limits(self, real_services_fixture):
        """Test memory management and resource limits for execution contexts."""
        # Arrange  
        context_manager = AgentExecutionContextManager(
            max_concurrent_contexts=3,  # Low limit for testing
            memory_limit_mb=50
        )
        
        execution_ids = []
        user_contexts = []
        
        # Create multiple contexts to test limits
        for i in range(5):  # More than max_concurrent_contexts
            user_context = UserExecutionContext(
                user_id=f"user_{i:03d}",
                thread_id=f"thread_{i:03d}",
                session_id=f"session_{i:03d}",
                workspace_id=f"workspace_{i:03d}"
            )
            user_contexts.append(user_context)
            execution_ids.append(str(uuid4()))
        
        # Act - Create contexts up to and beyond limit
        created_contexts = []
        for i, (execution_id, user_context) in enumerate(zip(execution_ids, user_contexts)):
            try:
                context = await context_manager.create_execution_context(
                    execution_id=execution_id,
                    user_context=user_context,
                    agent_type="memory_intensive_agent",
                    message=f"Task {i}"
                )
                created_contexts.append(context)
            except Exception as e:
                # Expected to fail after limit reached
                if "limit" in str(e).lower() or "capacity" in str(e).lower():
                    break
                else:
                    raise
        
        # Assert - Should only create up to limit
        assert len(created_contexts) <= 3  # Should respect max_concurrent_contexts
        
        # Verify active context tracking
        active_count = await context_manager.get_active_context_count()
        assert active_count <= 3
        
        # Cleanup one context to make room
        if created_contexts:
            await context_manager.complete_execution(
                created_contexts[0].execution_id,
                AgentExecutionResult(
                    execution_id=created_contexts[0].execution_id,
                    status="success", 
                    result={"completed": True},
                    execution_time_ms=100
                )
            )
            
            # Should now be able to create another
            new_context = await context_manager.create_execution_context(
                execution_id=str(uuid4()),
                user_context=user_contexts[-1],
                agent_type="test_agent",
                message="New task"
            )
            assert new_context is not None