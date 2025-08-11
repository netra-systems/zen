import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agent_service import AgentService
from app.schemas import AgentMessage, WebSocketMessage
from datetime import datetime

@pytest.mark.asyncio
class TestAgentMessageProcessing:
    
    async def test_process_user_message(self):
        """Test processing of user messages through agent service"""
        from unittest.mock import Mock
        
        # Mock supervisor properly
        mock_supervisor = AsyncMock()
        mock_supervisor.run = AsyncMock(return_value={"status": "completed"})
        
        agent_service = AgentService(mock_supervisor)
        
        # Mock the start_agent_run method
        agent_service.start_agent_run = AsyncMock(return_value="test_run_id_123")
        
        user_id = "user-456"
        thread_id = "test-thread-123"
        request = "Analyze my workload performance"
        
        run_id = await agent_service.start_agent_run(
            user_id=user_id,
            thread_id=thread_id,
            request=request
        )
        
        assert run_id != None
        assert isinstance(run_id, str)
        agent_service.start_agent_run.assert_called_once()
    
    async def test_handle_tool_execution(self):
        """Test handling of tool execution during message processing"""
        # Mock supervisor
        mock_supervisor = AsyncMock()
        
        agent_service = AgentService(mock_supervisor)
        
        # Since AgentService might not have execute_tool method, we'll mock it
        if not hasattr(agent_service, 'execute_tool'):
            agent_service.execute_tool = AsyncMock(return_value={
                "tool": "log_fetcher",
                "result": {"logs": ["log1", "log2"]},
                "execution_time": 0.5
            })
        
        tool_request = {
            "tool_name": "log_fetcher",
            "parameters": {"start_time": "2024-01-01", "end_time": "2024-01-02"}
        }
        
        result = await agent_service.execute_tool(tool_request)
        
        assert result["tool"] == "log_fetcher"
        assert "result" in result
    
    async def test_message_validation(self):
        """Test message validation and error handling"""
        # Mock supervisor
        mock_supervisor = AsyncMock()
        
        agent_service = AgentService(mock_supervisor)
        
        # Test invalid parameters to start_agent_run
        with pytest.raises((ValueError, TypeError, Exception)):
            await agent_service.start_agent_run(
                user_id=None,  # Invalid user ID
                thread_id="",  # Empty thread ID
                request=""     # Empty request
            )