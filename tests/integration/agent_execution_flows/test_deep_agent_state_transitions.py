"""
Test Deep Agent State Transitions Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable agent state management for consistent user experience
- Value Impact: Prevents state corruption that could cause failed AI interactions 
- Strategic Impact: Foundation for reliable multi-step agent workflows that deliver business value

Tests the deep agent state management system including state transitions,
persistence, recovery, and consistency across complex agent execution flows.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from enum import Enum

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.agent_state_tracker import AgentStateTracker
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    ExecutionStatus
)


class AgentStateType(Enum):
    """Agent state types for testing."""
    INITIALIZING = "initializing"
    COLLECTING_DATA = "collecting_data"
    ANALYZING = "analyzing"
    OPTIMIZING = "optimizing"
    REPORTING = "reporting"
    COMPLETED = "completed"
    ERROR = "error"


class TestDeepAgentStateTransitions(BaseIntegrationTest):
    """Integration tests for deep agent state transitions."""

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_state_transition_validation_and_consistency(self, real_services_fixture):
        """Test validation and consistency of agent state transitions."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="state_user_1000",
            thread_id="thread_1300",
            session_id="session_1600",
            workspace_id="state_workspace_900"
        )
        
        state_tracker = AgentStateTracker(
            user_context=user_context,
            persistence_enabled=True
        )
        
        # Define valid state transition rules
        valid_transitions = {
            AgentStateType.INITIALIZING: [AgentStateType.COLLECTING_DATA, AgentStateType.ERROR],
            AgentStateType.COLLECTING_DATA: [AgentStateType.ANALYZING, AgentStateType.ERROR],
            AgentStateType.ANALYZING: [AgentStateType.OPTIMIZING, AgentStateType.REPORTING, AgentStateType.ERROR],
            AgentStateType.OPTIMIZING: [AgentStateType.REPORTING, AgentStateType.ERROR],
            AgentStateType.REPORTING: [AgentStateType.COMPLETED, AgentStateType.ERROR],
            AgentStateType.COMPLETED: [],  # Terminal state
            AgentStateType.ERROR: [AgentStateType.INITIALIZING]  # Can retry
        }
        
        agent_state = DeepAgentState(
            agent_id="test_agent_001",
            user_context=user_context,
            initial_state=AgentStateType.INITIALIZING.value
        )
        
        # Act & Assert - Test valid transitions
        valid_sequence = [
            AgentStateType.INITIALIZING,
            AgentStateType.COLLECTING_DATA,
            AgentStateType.ANALYZING,
            AgentStateType.OPTIMIZING,
            AgentStateType.REPORTING,
            AgentStateType.COMPLETED
        ]
        
        for i in range(len(valid_sequence) - 1):
            current_state = valid_sequence[i]
            next_state = valid_sequence[i + 1]
            
            # Transition should be valid
            transition_result = await state_tracker.transition_agent_state(
                agent_state=agent_state,
                from_state=current_state.value,
                to_state=next_state.value,
                validate_transition=True
            )
            
            assert transition_result.success is True
            assert agent_state.current_state == next_state.value
            
        # Test invalid transition
        agent_state.current_state = AgentStateType.COMPLETED.value
        
        invalid_transition = await state_tracker.transition_agent_state(
            agent_state=agent_state,
            from_state=AgentStateType.COMPLETED.value,
            to_state=AgentStateType.COLLECTING_DATA.value,  # Invalid from completed
            validate_transition=True
        )
        
        assert invalid_transition.success is False
        assert "invalid transition" in invalid_transition.error_message.lower()

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_concurrent_state_modification_consistency(self, real_services_fixture):
        """Test state consistency under concurrent modifications."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="concurrent_user_1001",
            thread_id="thread_1301",
            session_id="session_1601",
            workspace_id="concurrent_workspace_901"
        )
        
        state_tracker = AgentStateTracker(
            user_context=user_context,
            concurrency_control=True,
            locking_enabled=True
        )
        
        agent_state = DeepAgentState(
            agent_id="concurrent_agent_002",
            user_context=user_context,
            initial_state=AgentStateType.INITIALIZING.value
        )
        
        # Mock concurrent operations
        operation_results = []
        
        async def concurrent_state_operation(operation_id: int, delay: float):
            """Simulate concurrent state operations."""
            await asyncio.sleep(delay)
            
            try:
                if operation_id % 2 == 0:
                    # Even operations: try to advance state
                    result = await state_tracker.transition_agent_state(
                        agent_state=agent_state,
                        from_state=agent_state.current_state,
                        to_state=AgentStateType.COLLECTING_DATA.value,
                        operation_id=f"op_{operation_id}"
                    )
                else:
                    # Odd operations: try to update state data
                    result = await state_tracker.update_agent_state_data(
                        agent_state=agent_state,
                        data_update={"progress": f"operation_{operation_id}", "timestamp": asyncio.get_event_loop().time()},
                        operation_id=f"op_{operation_id}"
                    )
                
                operation_results.append((operation_id, result.success, result.error_message))
                
            except Exception as e:
                operation_results.append((operation_id, False, str(e)))
        
        # Act - Execute concurrent operations
        concurrent_tasks = []
        for i in range(5):
            task = asyncio.create_task(
                concurrent_state_operation(i, delay=0.1 * (i % 3))  # Varying delays
            )
            concurrent_tasks.append(task)
        
        await asyncio.gather(*concurrent_tasks)
        
        # Assert - Verify consistency
        assert len(operation_results) == 5
        
        # At least some operations should succeed (the system handles concurrency)
        successful_operations = [result for result in operation_results if result[1] is True]
        assert len(successful_operations) > 0
        
        # State should be consistent (not corrupted)
        final_state = agent_state.current_state
        assert final_state in [state.value for state in AgentStateType]
        
        # Verify state history is consistent
        state_history = await state_tracker.get_state_history(agent_state.agent_id)
        assert len(state_history) >= 1  # At least initial state

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_state_persistence_and_recovery(self, real_services_fixture):
        """Test state persistence and recovery across system restarts."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="persistence_user_1002",
            thread_id="thread_1302", 
            session_id="session_1602",
            workspace_id="persistence_workspace_902"
        )
        
        # First state tracker instance (before "restart")
        state_tracker_1 = AgentStateTracker(
            user_context=user_context,
            persistence_enabled=True,
            storage_backend=real_services_fixture.get("redis", MagicMock())
        )
        
        agent_state = DeepAgentState(
            agent_id="persistent_agent_003",
            user_context=user_context,
            initial_state=AgentStateType.INITIALIZING.value
        )
        
        # Build up complex state
        state_changes = [
            (AgentStateType.COLLECTING_DATA.value, {"data_sources": ["aws", "azure"], "progress": 0.3}),
            (AgentStateType.ANALYZING.value, {"analysis_type": "cost_optimization", "progress": 0.7}),
            (AgentStateType.OPTIMIZING.value, {"optimization_focus": "compute", "recommendations": 3})
        ]
        
        for new_state, state_data in state_changes:
            await state_tracker_1.transition_agent_state(
                agent_state=agent_state,
                from_state=agent_state.current_state,
                to_state=new_state
            )
            
            await state_tracker_1.update_agent_state_data(
                agent_state=agent_state,
                data_update=state_data
            )
        
        # Persist final state
        await state_tracker_1.persist_agent_state(agent_state)
        original_state_snapshot = {
            "current_state": agent_state.current_state,
            "state_data": agent_state.get_all_state_data(),
            "transition_history": len(agent_state.state_history)
        }
        
        # Simulate system restart - create new state tracker instance
        state_tracker_2 = AgentStateTracker(
            user_context=user_context,
            persistence_enabled=True,
            storage_backend=real_services_fixture.get("redis", MagicMock())
        )
        
        # Act - Recover state
        recovered_state = await state_tracker_2.recover_agent_state(
            agent_id="persistent_agent_003",
            user_context=user_context
        )
        
        # Assert - Verify recovery
        assert recovered_state is not None
        assert recovered_state.current_state == original_state_snapshot["current_state"]
        assert recovered_state.agent_id == agent_state.agent_id
        
        # Verify state data is preserved
        recovered_data = recovered_state.get_all_state_data()
        assert "optimization_focus" in recovered_data
        assert recovered_data["recommendations"] == 3
        
        # Verify can continue with recovered state
        continue_result = await state_tracker_2.transition_agent_state(
            agent_state=recovered_state,
            from_state=recovered_state.current_state,
            to_state=AgentStateType.REPORTING.value
        )
        
        assert continue_result.success is True
        assert recovered_state.current_state == AgentStateType.REPORTING.value

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_hierarchical_state_management(self, real_services_fixture):
        """Test hierarchical state management for complex agent workflows."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="hierarchy_user_1003",
            thread_id="thread_1303",
            session_id="session_1603",
            workspace_id="hierarchy_workspace_903"
        )
        
        state_tracker = AgentStateTracker(
            user_context=user_context,
            hierarchical_states=True
        )
        
        # Create parent agent state (supervisor)
        supervisor_state = DeepAgentState(
            agent_id="supervisor_agent",
            user_context=user_context,
            initial_state="orchestrating",
            agent_type="supervisor"
        )
        
        # Create child agent states
        child_agents = [
            DeepAgentState(
                agent_id="data_helper_child",
                user_context=user_context,
                initial_state="collecting",
                agent_type="data_helper",
                parent_agent_id="supervisor_agent"
            ),
            DeepAgentState(
                agent_id="optimizer_child", 
                user_context=user_context,
                initial_state="waiting",
                agent_type="apex_optimizer",
                parent_agent_id="supervisor_agent"
            )
        ]
        
        # Act - Test hierarchical state coordination
        # Parent initiates workflow
        await state_tracker.transition_agent_state(
            agent_state=supervisor_state,
            from_state="orchestrating",
            to_state="coordinating_children"
        )
        
        # Child 1 completes data collection
        await state_tracker.transition_agent_state(
            agent_state=child_agents[0],
            from_state="collecting",
            to_state="data_ready",
            notify_parent=True
        )
        
        # This should trigger parent state update and child 2 activation
        parent_notification = await state_tracker.check_parent_notifications(supervisor_state.agent_id)
        assert parent_notification is not None
        
        # Activate child 2 based on child 1 completion
        await state_tracker.transition_agent_state(
            agent_state=child_agents[1],
            from_state="waiting", 
            to_state="optimizing",
            triggered_by="data_helper_child"
        )
        
        # Child 2 completes optimization
        await state_tracker.transition_agent_state(
            agent_state=child_agents[1],
            from_state="optimizing",
            to_state="optimization_complete",
            notify_parent=True
        )
        
        # Parent should transition to completion
        await state_tracker.process_child_completion(
            parent_agent_id="supervisor_agent",
            child_agent_id="optimizer_child",
            completion_result={"optimizations": 3, "savings": 15000}
        )
        
        # Assert - Verify hierarchical coordination
        assert supervisor_state.current_state in ["coordinating_children", "workflow_complete"]
        assert child_agents[0].current_state == "data_ready"
        assert child_agents[1].current_state == "optimization_complete"
        
        # Verify parent-child relationships
        hierarchy_info = await state_tracker.get_agent_hierarchy(supervisor_state.agent_id)
        assert len(hierarchy_info["children"]) == 2
        assert "data_helper_child" in hierarchy_info["children"]
        assert "optimizer_child" in hierarchy_info["children"]

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_state_rollback_and_checkpoint_management(self, real_services_fixture):
        """Test state rollback capabilities and checkpoint management."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="rollback_user_1004",
            thread_id="thread_1304",
            session_id="session_1604",
            workspace_id="rollback_workspace_904"
        )
        
        state_tracker = AgentStateTracker(
            user_context=user_context,
            checkpointing_enabled=True,
            rollback_enabled=True
        )
        
        agent_state = DeepAgentState(
            agent_id="rollback_agent_004",
            user_context=user_context,
            initial_state=AgentStateType.INITIALIZING.value
        )
        
        # Build up state with checkpoints
        state_progression = [
            (AgentStateType.COLLECTING_DATA.value, {"data_collected": 100, "checkpoint": "data_complete"}),
            (AgentStateType.ANALYZING.value, {"analysis_progress": 0.5, "checkpoint": "analysis_halfway"}),
            (AgentStateType.ANALYZING.value, {"analysis_progress": 1.0, "results": ["finding_1", "finding_2"], "checkpoint": "analysis_complete"}),
            (AgentStateType.OPTIMIZING.value, {"optimization_started": True})  # No checkpoint here
        ]
        
        checkpoints = []
        
        for new_state, state_data in state_progression:
            # Transition state
            await state_tracker.transition_agent_state(
                agent_state=agent_state,
                from_state=agent_state.current_state,
                to_state=new_state
            )
            
            # Update state data
            await state_tracker.update_agent_state_data(
                agent_state=agent_state,
                data_update=state_data
            )
            
            # Create checkpoint if specified
            if "checkpoint" in state_data:
                checkpoint_id = await state_tracker.create_checkpoint(
                    agent_state=agent_state,
                    checkpoint_name=state_data["checkpoint"]
                )
                checkpoints.append(checkpoint_id)
        
        # Simulate error during optimization
        await state_tracker.transition_agent_state(
            agent_state=agent_state,
            from_state=AgentStateType.OPTIMIZING.value,
            to_state=AgentStateType.ERROR.value,
            error_details={"error": "optimization_failed", "reason": "invalid_parameters"}
        )
        
        # Act - Rollback to last stable checkpoint
        rollback_result = await state_tracker.rollback_to_checkpoint(
            agent_state=agent_state,
            checkpoint_name="analysis_complete"
        )
        
        # Assert - Verify rollback
        assert rollback_result.success is True
        assert agent_state.current_state == AgentStateType.ANALYZING.value
        
        # Verify state data was rolled back
        rolled_back_data = agent_state.get_all_state_data()
        assert rolled_back_data["analysis_progress"] == 1.0
        assert "optimization_started" not in rolled_back_data  # Should be gone
        assert len(rolled_back_data["results"]) == 2
        
        # Verify can continue from rollback point
        retry_result = await state_tracker.transition_agent_state(
            agent_state=agent_state,
            from_state=AgentStateType.ANALYZING.value,
            to_state=AgentStateType.OPTIMIZING.value,
            retry_after_rollback=True
        )
        
        assert retry_result.success is True
        assert agent_state.current_state == AgentStateType.OPTIMIZING.value
        
        # Verify checkpoint history is maintained
        checkpoint_history = await state_tracker.get_checkpoint_history(agent_state.agent_id)
        assert len(checkpoint_history) >= 3  # Should have all our checkpoints
        
        checkpoint_names = [cp["name"] for cp in checkpoint_history]
        assert "data_complete" in checkpoint_names
        assert "analysis_halfway" in checkpoint_names
        assert "analysis_complete" in checkpoint_names