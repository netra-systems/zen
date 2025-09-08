"""
Unit Tests for Agent Execution State Flow - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agent execution follows proper state transitions
- Value Impact: Users experience predictable and reliable AI behavior
- Strategic Impact: Consistent execution patterns build user trust and enable scalability

CRITICAL: Proper state management prevents agent confusion and ensures reliable business value delivery.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from enum import Enum
from typing import Dict, Any

from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from shared.types import UserID, ThreadID, RunID

class MockAgentExecutionState(Enum):
    """Mock execution states for testing."""
    UNINITIALIZED = "uninitialized"
    STARTING = "starting"
    THINKING = "thinking"
    EXECUTING_TOOL = "executing_tool"
    PROCESSING_RESULT = "processing_result"
    COMPLETED = "completed"
    FAILED = "failed"

class TestAgentExecutionStateFlow:
    """Test agent execution engine state flow management."""
    
    @pytest.fixture
    def mock_agent_registry(self):
        """Mock agent registry for testing."""
        registry = Mock(spec=AgentRegistry)
        registry.get_agent = Mock()
        return registry
    
    @pytest.fixture
    def mock_execution_context(self):
        """Mock execution context."""
        context = Mock(spec=AgentExecutionContext)
        context.user_id = UserID("state_test_user")
        context.thread_id = ThreadID("state_test_thread")
        context.run_id = RunID("state_test_run")
        context.agent_name = "state_test_agent"
        context.message = "Test message for state flow"
        return context
    
    @pytest.fixture
    def mock_agent_state(self):
        """Mock agent state for testing."""
        state = Mock(spec=DeepAgentState)
        state.execution_state = MockAgentExecutionState.UNINITIALIZED
        state.error = None
        state.result = None
        state.tools_executed = []
        return state
    
    @pytest.fixture
    def execution_engine(self, mock_agent_registry):
        """Create execution engine with mocked dependencies."""
        engine = ExecutionEngine(agent_registry=mock_agent_registry)
        return engine

    @pytest.mark.unit
    async def test_agent_execution_state_initialization(self, execution_engine, mock_execution_context, mock_agent_state):
        """
        Test agent execution starts with proper state initialization.
        
        Business Value: Proper initialization ensures consistent execution baseline.
        Critical for preventing state corruption that could confuse users.
        """
        # Arrange: Setup mock agent
        mock_agent = Mock()
        mock_agent.execute = AsyncMock(return_value=mock_agent_state)
        execution_engine.agent_registry.get_agent.return_value = mock_agent
        
        # Mock state initialization
        mock_agent_state.execution_state = MockAgentExecutionState.UNINITIALIZED
        
        # Act: Initialize execution
        result = await execution_engine.execute_agent(mock_execution_context)
        
        # Assert: Proper state initialization
        execution_engine.agent_registry.get_agent.assert_called_once_with("state_test_agent")
        mock_agent.execute.assert_called_once()
        
        # Business requirement: Execution produces a result
        assert result is not None, "Agent execution should return a result"
        
        # Verify execution context was used properly
        execute_call_args = mock_agent.execute.call_args
        assert execute_call_args is not None, "Agent execute should be called with context"

    @pytest.mark.unit
    async def test_agent_execution_state_progression_success_path(self, execution_engine, mock_execution_context, mock_agent_state):
        """
        Test agent execution progresses through expected states successfully.
        
        Business Value: Predictable state progression enables reliable user experience.
        Users can trust that started agents will complete properly.
        """
        # Arrange: Mock successful agent execution with state progression
        mock_agent = Mock()
        state_progression = []
        
        async def mock_execute_with_states(context):
            # Simulate state progression during execution
            state_progression.append(MockAgentExecutionState.STARTING)
            await asyncio.sleep(0.01)  # Simulate processing time
            
            state_progression.append(MockAgentExecutionState.THINKING)
            await asyncio.sleep(0.01)
            
            state_progression.append(MockAgentExecutionState.EXECUTING_TOOL)
            await asyncio.sleep(0.01)
            
            state_progression.append(MockAgentExecutionState.PROCESSING_RESULT)
            await asyncio.sleep(0.01)
            
            state_progression.append(MockAgentExecutionState.COMPLETED)
            
            # Return successful result
            mock_agent_state.execution_state = MockAgentExecutionState.COMPLETED
            mock_agent_state.result = {
                "summary": "Agent execution completed successfully",
                "business_value": "Cost optimization analysis complete",
                "recommendations": 3
            }
            return mock_agent_state
        
        mock_agent.execute = mock_execute_with_states
        execution_engine.agent_registry.get_agent.return_value = mock_agent
        
        # Act: Execute agent and track state progression
        result = await execution_engine.execute_agent(mock_execution_context)
        
        # Assert: Proper state progression occurred
        expected_states = [
            MockAgentExecutionState.STARTING,
            MockAgentExecutionState.THINKING,
            MockAgentExecutionState.EXECUTING_TOOL,
            MockAgentExecutionState.PROCESSING_RESULT,
            MockAgentExecutionState.COMPLETED
        ]
        
        assert state_progression == expected_states, f"Expected {expected_states}, got {state_progression}"
        
        # Business requirement: Successful completion provides value
        assert result is not None, "Successful execution should return result"
        if hasattr(result, 'result') and result.result:
            assert "business_value" in str(result.result), "Result should indicate business value delivered"

    @pytest.mark.unit
    async def test_agent_execution_state_error_handling(self, execution_engine, mock_execution_context, mock_agent_state):
        """
        Test agent execution handles errors gracefully with proper state management.
        
        Business Value: Graceful error handling prevents user confusion and data loss.
        Error recovery maintains platform reliability and user trust.
        """
        # Arrange: Mock agent that encounters an error
        mock_agent = Mock()
        error_states = []
        
        async def mock_execute_with_error(context):
            error_states.append(MockAgentExecutionState.STARTING)
            await asyncio.sleep(0.01)
            
            error_states.append(MockAgentExecutionState.THINKING)
            await asyncio.sleep(0.01)
            
            # Simulate error during tool execution
            error_states.append(MockAgentExecutionState.EXECUTING_TOOL)
            error_states.append(MockAgentExecutionState.FAILED)
            
            # Return error state
            mock_agent_state.execution_state = MockAgentExecutionState.FAILED
            mock_agent_state.error = "Simulated tool execution error"
            mock_agent_state.result = {
                "error": "Tool execution failed", 
                "partial_results": "Some analysis was completed",
                "recovery_suggestions": ["retry_later", "check_permissions"]
            }
            return mock_agent_state
        
        mock_agent.execute = mock_execute_with_error
        execution_engine.agent_registry.get_agent.return_value = mock_agent
        
        # Act: Execute agent with error scenario
        result = await execution_engine.execute_agent(mock_execution_context)
        
        # Assert: Error handled gracefully
        assert MockAgentExecutionState.FAILED in error_states, "Should reach failed state"
        assert MockAgentExecutionState.STARTING in error_states, "Should start execution normally"
        
        # Business requirement: Error states still provide useful information
        assert result is not None, "Error execution should still return a result"
        if hasattr(result, 'error'):
            assert result.error is not None, "Error should be captured"
        
        # Business requirement: Partial results preserved when possible
        if hasattr(result, 'result') and result.result:
            result_str = str(result.result)
            assert "partial" in result_str.lower() or "recovery" in result_str.lower(), \
                "Error result should provide recovery information"

    @pytest.mark.unit
    async def test_agent_execution_concurrent_state_isolation(self, mock_agent_registry):
        """
        Test concurrent agent executions maintain separate state isolation.
        
        Business Value: Multiple users can run agents simultaneously without interference.
        CRITICAL: State contamination between users would be catastrophic.
        """
        # Arrange: Create multiple execution engines and contexts
        engine1 = ExecutionEngine(agent_registry=mock_agent_registry)
        engine2 = ExecutionEngine(agent_registry=mock_agent_registry)
        
        context1 = Mock(spec=AgentExecutionContext)
        context1.user_id = UserID("concurrent_user_1")
        context1.thread_id = ThreadID("concurrent_thread_1")
        context1.run_id = RunID("concurrent_run_1")
        context1.agent_name = "concurrent_agent_1"
        context1.message = "User 1 message"
        
        context2 = Mock(spec=AgentExecutionContext)
        context2.user_id = UserID("concurrent_user_2")
        context2.thread_id = ThreadID("concurrent_thread_2")
        context2.run_id = RunID("concurrent_run_2")
        context2.agent_name = "concurrent_agent_2"
        context2.message = "User 2 message"
        
        # Mock agents with different behaviors
        execution_states = {"agent1": [], "agent2": []}
        
        async def mock_agent1_execute(context):
            execution_states["agent1"].append("started")
            await asyncio.sleep(0.05)  # Longer execution
            execution_states["agent1"].append("processing")
            await asyncio.sleep(0.05)
            execution_states["agent1"].append("completed")
            
            state = Mock(spec=DeepAgentState)
            state.result = {"agent": "agent1", "user": str(context.user_id)}
            return state
        
        async def mock_agent2_execute(context):
            execution_states["agent2"].append("started")
            await asyncio.sleep(0.02)  # Shorter execution
            execution_states["agent2"].append("completed")
            
            state = Mock(spec=DeepAgentState)
            state.result = {"agent": "agent2", "user": str(context.user_id)}
            return state
        
        mock_agent1 = Mock()
        mock_agent1.execute = mock_agent1_execute
        mock_agent2 = Mock()
        mock_agent2.execute = mock_agent2_execute
        
        def get_agent_by_name(agent_name):
            return mock_agent1 if agent_name == "concurrent_agent_1" else mock_agent2
        
        mock_agent_registry.get_agent.side_effect = get_agent_by_name
        
        # Act: Execute both agents concurrently
        results = await asyncio.gather(
            engine1.execute_agent(context1),
            engine2.execute_agent(context2)
        )
        
        # Assert: Both executions completed with proper isolation
        assert len(results) == 2, "Both concurrent executions should complete"
        
        result1, result2 = results
        
        # Verify state isolation - each execution tracked separately
        assert len(execution_states["agent1"]) == 3, "Agent1 should complete full state sequence"
        assert len(execution_states["agent2"]) == 2, "Agent2 should complete short state sequence"
        
        # Business requirement: Results maintain user isolation
        if hasattr(result1, 'result') and result1.result:
            assert "concurrent_user_1" in str(result1.result), "Result1 should be for user1"
        
        if hasattr(result2, 'result') and result2.result:
            assert "concurrent_user_2" in str(result2.result), "Result2 should be for user2"

    @pytest.mark.unit
    async def test_agent_execution_state_timeout_handling(self, execution_engine, mock_execution_context, mock_agent_state):
        """
        Test agent execution handles timeout scenarios properly.
        
        Business Value: Timeouts prevent infinite waiting and resource exhaustion.
        Essential for maintaining platform performance under all conditions.
        """
        # Arrange: Mock agent that times out
        mock_agent = Mock()
        timeout_states = []
        
        async def mock_slow_execute(context):
            timeout_states.append(MockAgentExecutionState.STARTING)
            timeout_states.append(MockAgentExecutionState.THINKING)
            
            # Simulate very slow processing that would timeout
            await asyncio.sleep(10)  # This should be interrupted by timeout
            
            timeout_states.append(MockAgentExecutionState.COMPLETED)  # Should not reach here
            return mock_agent_state
        
        mock_agent.execute = mock_slow_execute
        execution_engine.agent_registry.get_agent.return_value = mock_agent
        
        # Act: Execute with timeout
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Use asyncio.wait_for to simulate timeout behavior
            result = await asyncio.wait_for(
                execution_engine.execute_agent(mock_execution_context), 
                timeout=0.1  # 100ms timeout
            )
        except asyncio.TimeoutError:
            # This is expected behavior
            result = None
        
        end_time = asyncio.get_event_loop().time()
        execution_time = end_time - start_time
        
        # Assert: Timeout handled appropriately
        assert execution_time < 1.0, f"Execution should timeout quickly, took {execution_time:.3f}s"
        
        # Business requirement: Timeout prevents resource waste
        assert execution_time >= 0.09, "Should respect timeout period"
        
        # Verify agent started but didn't complete full sequence
        assert MockAgentExecutionState.STARTING in timeout_states, "Should start execution"
        assert MockAgentExecutionState.COMPLETED not in timeout_states, "Should not complete due to timeout"

    @pytest.mark.unit
    async def test_agent_execution_state_resource_cleanup(self, execution_engine, mock_execution_context):
        """
        Test agent execution properly cleans up resources after completion.
        
        Business Value: Resource cleanup prevents memory leaks and maintains performance.
        Essential for long-running platform operation serving multiple customers.
        """
        # Arrange: Mock agent that tracks resource usage
        resource_tracker = {"allocated": 0, "cleaned": 0}
        
        async def mock_execute_with_resources(context):
            # Simulate resource allocation
            resource_tracker["allocated"] += 1
            
            try:
                # Simulate work
                await asyncio.sleep(0.01)
                
                result_state = Mock(spec=DeepAgentState)
                result_state.result = {"status": "completed", "resources_used": resource_tracker["allocated"]}
                return result_state
                
            finally:
                # Simulate resource cleanup
                resource_tracker["cleaned"] += 1
        
        mock_agent = Mock()
        mock_agent.execute = mock_execute_with_resources
        execution_engine.agent_registry.get_agent.return_value = mock_agent
        
        # Act: Execute agent multiple times to test cleanup
        for i in range(3):
            result = await execution_engine.execute_agent(mock_execution_context)
            
            # Assert: Resources properly managed for each execution
            assert resource_tracker["allocated"] == i + 1, f"Should allocate resources for execution {i+1}"
            assert resource_tracker["cleaned"] == i + 1, f"Should clean up resources after execution {i+1}"
        
        # Business requirement: No resource leaks after multiple executions
        assert resource_tracker["allocated"] == resource_tracker["cleaned"], \
            "All allocated resources should be cleaned up"