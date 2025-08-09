import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agent_service import AgentService
from app.schemas.Agent import AgentMessage, AgentResponse
from datetime import datetime

@pytest.mark.asyncio
class TestAgentMessageProcessing:
    
    async def test_process_user_message(self):
        """Test processing of user messages through agent service"""
        mock_supervisor = AsyncMock()
        mock_supervisor.process_message = AsyncMock(return_value={
            "response": "Test response",
            "sub_agents_used": ["triage", "data"],
            "tools_used": ["log_fetcher"],
            "execution_time": 1.5
        })
        
        agent_service = AgentService(mock_supervisor)
        
        message = AgentMessage(
            content="Analyze my workload performance",
            thread_id="test-thread-123",
            user_id="user-456"
        )
        
        response = await agent_service.process_message(message)
        
        assert response is not None
        mock_supervisor.process_message.assert_called_once()
    
    async def test_handle_tool_execution(self):
        """Test handling of tool execution during message processing"""
        mock_supervisor = AsyncMock()
        mock_supervisor.execute_tool = AsyncMock(return_value={
            "tool": "log_fetcher",
            "result": {"logs": ["log1", "log2"]},
            "execution_time": 0.5
        })
        
        agent_service = AgentService(mock_supervisor)
        
        tool_request = {
            "tool_name": "log_fetcher",
            "parameters": {"start_time": "2024-01-01", "end_time": "2024-01-02"}
        }
        
        result = await agent_service.execute_tool(tool_request)
        
        assert result["tool"] == "log_fetcher"
        assert "result" in result
    
    async def test_message_validation(self):
        """Test message validation and error handling"""
        mock_supervisor = AsyncMock()
        agent_service = AgentService(mock_supervisor)
        
        invalid_message = {
            "content": "",
            "thread_id": None
        }
        
        with pytest.raises(ValueError):
            await agent_service.validate_message(invalid_message)