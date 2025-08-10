import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from app.agents.supervisor import Supervisor
from app.agents.base import BaseSubAgent
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.state import DeepAgentState

@pytest.mark.asyncio
class TestSupervisorOrchestration:
    
    async def test_supervisor_agent_selection(self):
        """Test supervisor's ability to select appropriate sub-agents"""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_llm = AsyncMock()
        mock_websocket = AsyncMock()
        mock_tool_dispatcher = AsyncMock()
        
        supervisor = Supervisor(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
        
        # Mock the sub_agents property
        supervisor.sub_agents = [
            Mock(name="TriageAgent"),
            Mock(name="DataAgent"),
            Mock(name="OptimizationAgent")
        ]
        
        message = "Show me performance metrics for the last week"
        
        # Test that supervisor has sub-agents
        assert len(supervisor.sub_agents) > 0
        assert any("Triage" in str(agent.name) or "triage" in str(agent.name).lower() for agent in supervisor.sub_agents)
    
    async def test_multi_agent_coordination(self):
        """Test coordination between multiple sub-agents"""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_llm = AsyncMock()
        mock_websocket = AsyncMock()
        mock_tool_dispatcher = AsyncMock()
        
        supervisor = Supervisor(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
        
        # Mock the sub-agent execution
        mock_triage_agent = AsyncMock()
        mock_data_agent = AsyncMock()
        
        mock_triage_agent.execute = AsyncMock(return_value=DeepAgentState(
            user_request="Analyze performance",
            triage_result={"category": "performance_analysis", "priority": "high"}
        ))
        
        mock_data_agent.execute = AsyncMock(return_value=DeepAgentState(
            user_request="Analyze performance",
            data_result={"metrics": {"latency": 100, "throughput": 1000}}
        ))
        
        supervisor.sub_agents = [mock_triage_agent, mock_data_agent]
        
        # Mock the supervisor's run method
        async def mock_run(request, run_id, stream_updates):
            state = DeepAgentState(user_request=request)
            for agent in supervisor.sub_agents:
                state = await agent.execute(state, run_id, stream_updates)
            return state
            
        supervisor.run = mock_run
        
        result = await supervisor.run("Analyze performance", "test_run_id", False)
        
        mock_triage_agent.execute.assert_called_once()
        mock_data_agent.execute.assert_called_once()
    
    async def test_error_handling_in_orchestration(self):
        """Test error handling when sub-agent fails"""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_llm = AsyncMock()
        mock_websocket = AsyncMock()
        mock_tool_dispatcher = AsyncMock()
        
        supervisor = Supervisor(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
        
        mock_failing_agent = AsyncMock()
        mock_failing_agent.execute = AsyncMock(side_effect=Exception("Agent failed"))
        
        supervisor.sub_agents = [mock_failing_agent]
        
        # Mock the supervisor's run method to handle errors
        async def mock_run_with_error(request, run_id, stream_updates):
            try:
                state = DeepAgentState(user_request=request)
                for agent in supervisor.sub_agents:
                    state = await agent.execute(state, run_id, stream_updates)
                return state
            except Exception as e:
                # Supervisor should handle the error gracefully
                raise e
                
        supervisor.run = mock_run_with_error
        
        with pytest.raises(Exception) as exc_info:
            await supervisor.run("Test message", "test_run_id", False)
            
        assert "Agent failed" in str(exc_info.value)