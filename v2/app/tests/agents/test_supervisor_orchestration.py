import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.supervisor import Supervisor
from app.agents.base import BaseAgent

@pytest.mark.asyncio
class TestSupervisorOrchestration:
    
    async def test_supervisor_agent_selection(self):
        """Test supervisor's ability to select appropriate sub-agents"""
        mock_db = AsyncMock()
        mock_llm = AsyncMock()
        mock_websocket = AsyncMock()
        mock_tool_dispatcher = AsyncMock()
        
        supervisor = Supervisor(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
        
        mock_llm.generate = AsyncMock(return_value={
            "selected_agents": ["triage", "data_analysis"],
            "reasoning": "User query requires data analysis"
        })
        
        message = "Show me performance metrics for the last week"
        selected_agents = await supervisor.select_agents(message)
        
        assert "triage" in selected_agents
        assert "data_analysis" in selected_agents
    
    async def test_multi_agent_coordination(self):
        """Test coordination between multiple sub-agents"""
        mock_db = AsyncMock()
        mock_llm = AsyncMock()
        mock_websocket = AsyncMock()
        mock_tool_dispatcher = AsyncMock()
        
        supervisor = Supervisor(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
        
        mock_triage_agent = AsyncMock()
        mock_data_agent = AsyncMock()
        
        mock_triage_agent.process = AsyncMock(return_value={
            "category": "performance_analysis",
            "priority": "high"
        })
        
        mock_data_agent.process = AsyncMock(return_value={
            "metrics": {"latency": 100, "throughput": 1000},
            "recommendations": ["Optimize caching"]
        })
        
        with patch.object(supervisor, 'agents', {'triage': mock_triage_agent, 'data': mock_data_agent}):
            result = await supervisor.coordinate_agents("Analyze performance", ["triage", "data"])
            
            mock_triage_agent.process.assert_called_once()
            mock_data_agent.process.assert_called_once()
    
    async def test_error_handling_in_orchestration(self):
        """Test error handling when sub-agent fails"""
        mock_db = AsyncMock()
        mock_llm = AsyncMock()
        mock_websocket = AsyncMock()
        mock_tool_dispatcher = AsyncMock()
        
        supervisor = Supervisor(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
        
        mock_failing_agent = AsyncMock()
        mock_failing_agent.process = AsyncMock(side_effect=Exception("Agent failed"))
        
        with patch.object(supervisor, 'agents', {'failing': mock_failing_agent}):
            result = await supervisor.handle_agent_failure("failing", "Test message")
            
            assert result["status"] == "error"
            assert "Agent failed" in result["error_message"]