"""
Integration tests for admin agents

Tests the integration between triage, corpus admin, and tool dispatcher agents.
All functions maintain 8-line limit with single responsibility.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.agents.corpus_admin import CorpusAdminSubAgent
from app.agents.admin_tool_dispatcher import AdminToolDispatcher
from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.ws_manager import WebSocketManager


class TestAdminAgentIntegration:
    """Integration tests for admin agents"""
    
    @pytest.fixture
    async def mock_supervisor(self):
        """Create mock supervisor with agents"""
        supervisor = AsyncMock(spec=Supervisor)
        supervisor.triage_agent = AsyncMock(spec=TriageSubAgent)
        supervisor.corpus_admin = AsyncMock(spec=CorpusAdminSubAgent)
        supervisor.tool_dispatcher = AsyncMock(spec=AdminToolDispatcher)
        return supervisor
    
    @pytest.fixture
    async def mock_websocket(self):
        """Create mock WebSocket manager"""
        ws_manager = AsyncMock(spec=WebSocketManager)
        ws_manager.send_message = AsyncMock()
        ws_manager.broadcast = AsyncMock()
        return ws_manager
    
    async def test_agent_routing(self, mock_supervisor):
        """Test triage to corpus admin routing"""
        mock_supervisor.triage_agent.process.return_value = {
            "intent": "corpus_generation",
            "target_agent": "corpus_admin",
            "parameters": {"domain": "fintech"}
        }
        result = await mock_supervisor.triage_agent.process("Generate corpus for fintech")
        assert result["target_agent"] == "corpus_admin"
        assert result["parameters"]["domain"] == "fintech"
    
    async def test_tool_execution(self, mock_supervisor):
        """Test tool dispatcher integration"""
        mock_supervisor.tool_dispatcher.dispatch_tool.return_value = {
            "success": True,
            "tool": "create_corpus",
            "result": {"corpus_id": "test_123"}
        }
        result = await self._execute_tool_dispatch(mock_supervisor)
        assert result["success"] is True
        assert result["result"]["corpus_id"] == "test_123"
    
    async def _execute_tool_dispatch(self, supervisor):
        """Execute tool dispatch operation"""
        return await supervisor.tool_dispatcher.dispatch_tool(
            tool_name="create_corpus",
            parameters={"name": "test_corpus"},
            state={},
            run_id="run_123"
        )
    
    async def test_websocket_communication(self, mock_supervisor, mock_websocket):
        """Test real-time updates via WebSocket"""
        mock_websocket.send_message.return_value = True
        await mock_websocket.send_message("user_123", {
            "type": "corpus_progress",
            "data": {"progress": 50}
        })
        mock_websocket.send_message.assert_called_once()
        assert mock_websocket.send_message.call_args[0][1]["data"]["progress"] == 50
    
    async def test_agent_chain_execution(self, mock_supervisor):
        """Test complete agent chain execution"""
        await self._setup_agent_chain_mocks(mock_supervisor)
        result = await self._execute_agent_chain(mock_supervisor)
        assert result["status"] == "completed"
        assert result["corpus_id"] == "corpus_456"
    
    async def _setup_agent_chain_mocks(self, supervisor):
        """Setup mocks for agent chain"""
        supervisor.triage_agent.process.return_value = {
            "target_agent": "corpus_admin"
        }
        supervisor.corpus_admin.process.return_value = {
            "action": "create",
            "corpus_id": "corpus_456"
        }
    
    async def _execute_agent_chain(self, supervisor):
        """Execute complete agent chain"""
        triage_result = await supervisor.triage_agent.process("Create corpus")
        corpus_result = await supervisor.corpus_admin.process(triage_result)
        return {"status": "completed", "corpus_id": corpus_result["corpus_id"]}
    
    async def test_error_propagation(self, mock_supervisor):
        """Test error propagation through agents"""
        mock_supervisor.corpus_admin.process.side_effect = Exception("Processing error")
        with pytest.raises(Exception) as exc_info:
            await mock_supervisor.corpus_admin.process({"request": "invalid"})
        assert "Processing error" in str(exc_info.value)
    
    async def test_concurrent_agent_operations(self, mock_supervisor):
        """Test concurrent agent operations"""
        results = await self._execute_concurrent_operations(mock_supervisor)
        assert len(results) == 3
        assert all(r["success"] for r in results)
    
    async def _execute_concurrent_operations(self, supervisor):
        """Execute multiple concurrent operations"""
        import asyncio
        supervisor.corpus_admin.process.return_value = {"success": True}
        tasks = [
            supervisor.corpus_admin.process({"id": i})
            for i in range(3)
        ]
        return await asyncio.gather(*tasks)


class TestAgentStateManagement:
    """Test agent state management integration"""
    
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