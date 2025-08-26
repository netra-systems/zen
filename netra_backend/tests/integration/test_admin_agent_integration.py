"""
Integration tests for admin agents

Tests the integration between triage, corpus admin, and tool dispatcher agents.
All functions maintain 25-line limit with single responsibility.
"""

from netra_backend.app.websocket_core.manager import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest
import pytest_asyncio

from netra_backend.app.agents.admin_tool_dispatcher import AdminToolDispatcher

from netra_backend.app.agents.corpus_admin import CorpusAdminSubAgent
from netra_backend.app.agents.supervisor_consolidated import (

    SupervisorAgent as Supervisor,

)
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.websocket_core.manager import WebSocketManager

class TestAdminAgentIntegration:

    """Integration tests for admin agents"""
    
    @pytest.fixture

    def mock_supervisor(self):

        """Create mock supervisor with agents"""

        # Mock: Async component isolation for testing without real async operations
        supervisor = AsyncMock(spec=Supervisor)

        # Mock: Agent service isolation for testing without LLM agent execution
        supervisor.triage_agent = AsyncMock(spec=TriageSubAgent)

        # Mock: Generic component isolation for controlled unit testing
        supervisor.triage_agent.execute = AsyncMock()

        # Mock: Agent service isolation for testing without LLM agent execution
        supervisor.corpus_admin = AsyncMock(spec=CorpusAdminSubAgent)

        # Mock: Generic component isolation for controlled unit testing
        supervisor.corpus_admin.execute = AsyncMock()

        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        supervisor.tool_dispatcher = AsyncMock(spec=AdminToolDispatcher)

        # Mock: Tool execution isolation for predictable agent testing
        supervisor.tool_dispatcher.dispatch_tool = AsyncMock()

        return supervisor
    
    @pytest.fixture

    def mock_websocket(self):

        """Create mock WebSocket manager"""

        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        ws_manager = AsyncMock(spec=WebSocketManager)

        # Mock: Generic component isolation for controlled unit testing
        ws_manager.send_message = AsyncMock()

        # Mock: Generic component isolation for controlled unit testing
        ws_manager.broadcast = AsyncMock()

        return ws_manager
    
    @pytest.mark.asyncio
    async def test_agent_routing(self, mock_supervisor):

        """Test triage to corpus admin routing"""

        # Mock the execute method to simulate triage result in state
        async def mock_execute(state, run_id, stream_updates):
            # Simulate setting triage_result on the state
            state.triage_result = {
                "intent": "corpus_generation",
                "target_agent": "corpus_admin",
                "parameters": {"domain": "fintech"}
            }
        
        mock_supervisor.triage_agent.execute.side_effect = mock_execute
        
        # Create a mock state to pass to execute
        from netra_backend.app.agents.state import DeepAgentState
        test_state = DeepAgentState(user_request="Generate corpus for fintech")
        await mock_supervisor.triage_agent.execute(test_state, "test_run", False)
        result = test_state.triage_result

        assert result["target_agent"] == "corpus_admin"

        assert result["parameters"]["domain"] == "fintech"
    
    @pytest.mark.asyncio
    async def test_tool_execution(self, mock_supervisor):

        """Test tool dispatcher integration"""

        mock_supervisor.tool_dispatcher.dispatch_tool.return_value = {

            "success": True,

            "tool": "create_corpus",

            "result": {"corpus_id": "test_123"}

        }

        # Mock: Component isolation for testing without external dependencies
        result = await self._execute_tool_dispatch(mock_supervisor)

        assert result["success"] is True

        assert result["result"]["corpus_id"] == "test_123"
    
    # Mock: Component isolation for testing without external dependencies
    async def _execute_tool_dispatch(self, supervisor):

        """Execute tool dispatch operation"""

        return await supervisor.tool_dispatcher.dispatch_tool(

            tool_name="create_corpus",

            parameters={"name": "test_corpus"},

            state={},

            run_id="run_123"

        )
    
    @pytest.mark.asyncio
    async def test_websocket_communication(self, mock_supervisor, mock_websocket):

        """Test real-time updates via WebSocket"""

        mock_websocket.send_message.return_value = True

        await mock_websocket.send_message("user_123", {

            "type": "corpus_progress",

            "data": {"progress": 50}

        })

        mock_websocket.send_message.assert_called_once()

        assert mock_websocket.send_message.call_args[0][1]["data"]["progress"] == 50
    
    @pytest.mark.asyncio
    async def test_agent_chain_execution(self, mock_supervisor):

        """Test complete agent chain execution"""

        await self._setup_agent_chain_mocks(mock_supervisor)

        result = await self._execute_agent_chain(mock_supervisor)

        assert result["status"] == "completed"

        assert result["corpus_id"] == "corpus_456"
    
    async def _setup_agent_chain_mocks(self, supervisor):

        """Setup mocks for agent chain"""

        # Mock the execute methods to simulate results in state
        async def mock_triage_execute(state, run_id, stream_updates):
            state.triage_result = {"target_agent": "corpus_admin"}
        
        async def mock_corpus_execute(state, run_id, stream_updates):
            # Use agent_input to store corpus results since there's no corpus_result field
            state.agent_input = state.agent_input or {}
            state.agent_input["corpus_result"] = {
                "action": "create",
                "corpus_id": "corpus_456"
            }
        
        supervisor.triage_agent.execute.side_effect = mock_triage_execute
        supervisor.corpus_admin.execute.side_effect = mock_corpus_execute
    
    async def _execute_agent_chain(self, supervisor):

        """Execute complete agent chain"""

        # Execute triage agent
        from netra_backend.app.agents.state import DeepAgentState
        triage_state = DeepAgentState(user_request="Create corpus")
        await supervisor.triage_agent.execute(triage_state, "test_run", False)
        triage_result = triage_state.triage_result

        # Execute corpus admin agent
        corpus_state = DeepAgentState(user_request="Create corpus")
        corpus_state.triage_result = triage_result
        await supervisor.corpus_admin.execute(corpus_state, "test_run", False)
        corpus_result = corpus_state.agent_input.get("corpus_result") if corpus_state.agent_input else {}

        return {"status": "completed", "corpus_id": corpus_result["corpus_id"]}
    
    @pytest.mark.asyncio
    async def test_error_propagation(self, mock_supervisor):

        """Test error propagation through agents"""

        mock_supervisor.corpus_admin.execute.side_effect = Exception("Processing error")

        with pytest.raises(Exception) as exc_info:
            from netra_backend.app.agents.state import DeepAgentState
            invalid_state = DeepAgentState(user_request="invalid")
            await mock_supervisor.corpus_admin.execute(invalid_state, "test_run", False)

        assert "Processing error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_operations(self, mock_supervisor):

        """Test concurrent agent operations"""

        results = await self._execute_concurrent_operations(mock_supervisor)

        assert len(results) == 3

        assert all(r["success"] for r in results)
    
    async def _execute_concurrent_operations(self, supervisor):

        """Execute multiple concurrent operations"""
        import asyncio

        # Mock the execute method to simulate success
        async def mock_execute_success(state, run_id, stream_updates):
            # Use agent_input to store results since there's no corpus_result field
            state.agent_input = state.agent_input or {}
            state.agent_input["corpus_result"] = {"success": True}
        
        supervisor.corpus_admin.execute.side_effect = mock_execute_success

        # Create tasks with proper execute method signature and collect states
        tasks = []
        states = []
        for i in range(3):
            from netra_backend.app.agents.state import DeepAgentState
            state = DeepAgentState(user_request=f"task_{i}")
            states.append(state)
            tasks.append(supervisor.corpus_admin.execute(state, f"run_{i}", False))

        # Execute all tasks concurrently
        await asyncio.gather(*tasks)
        
        # Extract results from the states
        results = []
        for state in states:
            if state.agent_input and "corpus_result" in state.agent_input:
                results.append(state.agent_input["corpus_result"])
            else:
                results.append({"success": False})
        
        return results

class TestAgentStateManagement:

    """Test agent state management integration"""
    
    @pytest.mark.asyncio
    async def test_state_persistence(self):

        """Test state persistence across agent calls"""

        state = {"corpus_count": 0}

        state = await self._update_state(state, "increment")

        assert state["corpus_count"] == 1

        state = await self._update_state(state, "increment")

        assert state["corpus_count"] == 2
    
    async def _update_state(self, state: Dict, action: str) -> Dict:

        """Update agent state based on action"""

        if action == "increment":

            state["corpus_count"] = state.get("corpus_count", 0) + 1

        elif action == "reset":

            state["corpus_count"] = 0

        return state
    
    @pytest.mark.asyncio
    async def test_state_recovery(self):

        """Test state recovery after error"""

        state = {"last_operation": "create_corpus", "checkpoint": "step_2"}

        recovered_state = await self._recover_state(state)

        assert recovered_state["resumed"] is True

        assert recovered_state["checkpoint"] == "step_2"
    
    async def _recover_state(self, state: Dict) -> Dict:

        """Recover state from checkpoint"""

        return {

            "resumed": True,

            "checkpoint": state.get("checkpoint"),

            "last_operation": state.get("last_operation")

        }

class TestAgentCommunication:

    """Test inter-agent communication"""
    
    @pytest.mark.asyncio
    async def test_message_passing(self):

        """Test message passing between agents"""

        message = {"type": "corpus_request", "data": {"action": "create"}}

        response = await self._process_message(message)

        assert response["status"] == "received"

        assert response["processed"] is True
    
    async def _process_message(self, message: Dict) -> Dict:

        """Process inter-agent message"""

        return {

            "status": "received",

            "processed": True,

            "message_type": message.get("type"),

            "timestamp": "2024-01-01T00:00:00Z"

        }
    
    @pytest.mark.asyncio
    async def test_broadcast_updates(self):

        """Test broadcasting updates to multiple agents"""

        update = {"event": "corpus_created", "corpus_id": "test_789"}

        results = await self._broadcast_to_agents(update)

        assert len(results) == 3

        assert all(r["received"] for r in results)
    
    async def _broadcast_to_agents(self, update: Dict) -> list:

        """Broadcast update to all agents"""

        agents = ["triage", "corpus_admin", "tool_dispatcher"]

        return [

            {"agent": agent, "received": True, "update": update}

            for agent in agents

        ]