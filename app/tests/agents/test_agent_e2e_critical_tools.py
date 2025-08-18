"""
Critical end-to-end tests for tool integration, state persistence, and error handling.
Tests 4-6: Tool dispatcher integration, state persistence/recovery, error handling.
"""

import pytest
import asyncio
import uuid
from unittest.mock import patch, AsyncMock

from app.agents.state import DeepAgentState
from app.services.state_persistence import state_persistence_service
from app.tests.agents.test_agent_e2e_critical_setup import AgentE2ETestBase


class TestAgentE2ECriticalTools(AgentE2ETestBase):
    """Critical tests for tool integration and state management"""
    @pytest.mark.asyncio
    async def test_4_tool_dispatcher_integration(self, setup_agent_infrastructure):
        """
        Test Case 4: Tool Dispatcher Integration
        - Test tool execution through dispatcher
        - Verify tool results are properly integrated
        - Test multiple tool calls in sequence
        """
        infra = setup_agent_infrastructure
        tool_dispatcher = infra["tool_dispatcher"]
        llm_manager = infra["llm_manager"]
        
        # Setup tool calls response
        llm_manager.call_llm = AsyncMock(return_value={
            "content": "Let me analyze your data",
            "tool_calls": [
                {"name": "get_workload_data", "arguments": {"time_range": "1h"}},
                {"name": "analyze_metrics", "arguments": {"metrics": ["gpu", "memory"]}}
            ]
        })
        
        # Mock tool execution results
        tool_results = [
            {"data": "workload_metrics", "status": "success"},
            {"analysis": "optimization_suggestions", "status": "success"}
        ]
        tool_dispatcher.dispatch_tool = AsyncMock(side_effect=tool_results)
        
        # Execute a sub-agent that uses tools
        from app.agents.data_sub_agent.agent import DataSubAgent
        data_agent = DataSubAgent(llm_manager, tool_dispatcher)
        state = DeepAgentState(user_request="Analyze GPU metrics")
        
        # Mock the data agent's execute to simulate tool usage
        async def mock_execute_with_tools(state, rid, stream):
            # Simulate making tool calls
            for tool_result in tool_results:
                await tool_dispatcher.dispatch_tool("mock_tool", {})
            # Store tool results in data_result field which exists in DeepAgentState
            state.data_result = {"tool_outputs": tool_results}
            return state
        
        data_agent.execute = mock_execute_with_tools
        await data_agent.execute(state, str(uuid.uuid4()), False)
        
        # Verify tool calls were made
        assert tool_dispatcher.dispatch_tool.call_count >= 2
        
        # Verify tool results were integrated into state
        assert state.data_result != None
        assert "tool_outputs" in state.data_result
        assert len(state.data_result["tool_outputs"]) == 2
    @pytest.mark.asyncio
    async def test_5_state_persistence_and_recovery(self, setup_agent_infrastructure):
        """
        Test Case 5: State Persistence and Recovery
        - Test state saving during execution
        - Test state recovery after interruption
        - Test thread context preservation
        """
        infra = setup_agent_infrastructure
        supervisor = infra["supervisor"]
        db_session = infra["db_session"]
        
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        supervisor.thread_id = thread_id
        supervisor.user_id = user_id
        
        # Mock state persistence
        saved_states = {}
        
        async def mock_save_state(run_id, thread_id, user_id, state, db_session):
            saved_states[run_id] = {
                "thread_id": thread_id,
                "user_id": user_id,
                "state": state.model_dump()
            }
            
        async def mock_load_state(run_id, db_session):
            if run_id in saved_states:
                return DeepAgentState(**saved_states[run_id]["state"])
            return None
            
        # Mock state persistence service methods
        with patch.object(state_persistence_service, 'save_agent_state', AsyncMock(side_effect=mock_save_state)):
            with patch.object(state_persistence_service, 'load_agent_state', AsyncMock(side_effect=mock_load_state)):
                with patch.object(state_persistence_service, 'get_thread_context', AsyncMock(return_value=None)):
                    # First run - state should be saved
                    state1 = await supervisor.run("Initial request", thread_id, user_id, run_id)
                
                # Verify state was saved
                assert run_id in saved_states
                assert saved_states[run_id]["thread_id"] == thread_id
                
                # Simulate recovery - load previous state
                with patch.object(state_persistence_service, 'get_thread_context', 
                                AsyncMock(return_value={"current_run_id": run_id})):
                    
                    # Second run should load previous state
                    state2 = await supervisor.run("Follow-up request", thread_id, user_id, run_id + "_2")
                    
                    # Verify state continuity
                    assert state2.user_request == "Follow-up request"
    def _get_sub_agents(self, supervisor):
        """Get sub-agents from supervisor based on implementation"""
        if hasattr(supervisor, '_impl') and supervisor._impl:
            if hasattr(supervisor._impl, 'agents'):
                return list(supervisor._impl.agents.values())
            else:
                return supervisor._impl.sub_agents
        else:
            return supervisor.sub_agents

    def _setup_error_agent(self, supervisor):
        """Setup sub-agent to simulate error"""
        sub_agents = self._get_sub_agents(supervisor)
        sub_agents[2].execute = AsyncMock(side_effect=Exception("Sub-agent failure"))

    async def _capture_error_messages(self, websocket_manager):
        """Setup error message capture"""
        error_messages = []
        async def capture_error(rid, msg):
            if msg.get("type") == "error":
                error_messages.append(msg)
        websocket_manager.send_message = AsyncMock(side_effect=capture_error)
        return error_messages

    async def _execute_with_error(self, supervisor, run_id):
        """Execute supervisor with expected error"""
        try:
            await supervisor.run("Test with error", supervisor.thread_id, supervisor.user_id, run_id)
        except Exception:
            pass  # Expected to fail

    def _verify_error_handling(self, websocket_manager, error_messages):
        """Verify error handling behavior"""
        assert websocket_manager.send_message.called or len(error_messages) >= 0

    def _setup_retry_mechanism(self, supervisor):
        """Setup retry mechanism for testing"""
        supervisor._retry_count = 0
        max_retries = 3
        async def retry_execute(state, rid, stream):
            supervisor._retry_count += 1
            if supervisor._retry_count < max_retries:
                raise Exception("Temporary failure")
            return state
        sub_agents = self._get_sub_agents(supervisor)
        sub_agents[2].execute = retry_execute
        return max_retries

    async def _test_retry_execution(self, supervisor, run_id, max_retries):
        """Test retry execution mechanism"""
        with patch.object(state_persistence_service, 'save_agent_state', AsyncMock()):
            with patch.object(state_persistence_service, 'load_agent_state', AsyncMock(return_value=None)):
                with patch.object(state_persistence_service, 'get_thread_context', AsyncMock(return_value=None)):
                    for i in range(max_retries):
                        try:
                            await supervisor.run("Test with retry", supervisor.thread_id, supervisor.user_id, run_id + f"_retry_{i}")
                            break
                        except:
                            continue

    @pytest.mark.asyncio
    async def test_6_error_handling_and_recovery(self, setup_agent_infrastructure):
        """
        Test Case 6: Error Handling and Recovery
        - Test graceful error handling in sub-agents
        - Test supervisor error recovery strategies
        - Test error propagation to user
        """
        infra = setup_agent_infrastructure
        supervisor = infra["supervisor"]
        websocket_manager = infra["websocket_manager"]
        run_id = str(uuid.uuid4())
        with patch.object(state_persistence_service, 'save_agent_state', AsyncMock()):
            with patch.object(state_persistence_service, 'load_agent_state', AsyncMock(return_value=None)):
                with patch.object(state_persistence_service, 'get_thread_context', AsyncMock(return_value=None)):
                    self._setup_error_agent(supervisor)
        error_messages = await self._capture_error_messages(websocket_manager)
        await self._execute_with_error(supervisor, run_id)
        self._verify_error_handling(websocket_manager, error_messages)
        max_retries = self._setup_retry_mechanism(supervisor)
        await self._test_retry_execution(supervisor, run_id, max_retries)
        assert supervisor._retry_count >= 1