import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agent_service import AgentService
from app.schemas import AgentMessage, WebSocketMessage
from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_agent_service_initialization():
    # Mock supervisor
    mock_supervisor = AsyncMock(spec=Supervisor)
    
    service = AgentService(mock_supervisor)
    assert service.supervisor != None
    assert service.thread_service != None
    assert service.message_handler != None

@pytest.mark.asyncio
async def test_agent_service_process_request():
    # Mock supervisor
    mock_supervisor = AsyncMock(spec=Supervisor)
    mock_supervisor.run = AsyncMock(return_value={"status": "completed", "result": "test_result"})
    
    service = AgentService(mock_supervisor)
    
    # Create a request model
    from app.schemas import RequestModel
    request_model = RequestModel(
        id="test_id",
        user_id="user_456",
        query="Test message",
        workloads=[]
    )
    
    run_id = "run_id_123"
    result = await service.run(request_model, run_id, stream_updates=True)
    
    assert result["status"] == "completed"
    mock_supervisor.run.assert_called_once()

@pytest.mark.asyncio
async def test_agent_service_websocket_message_handling():
    # Mock supervisor and dependencies
    mock_supervisor = AsyncMock(spec=Supervisor)
    mock_db = AsyncMock(spec=AsyncSession)
    
    service = AgentService(mock_supervisor)
    
    # Mock the message handler
    service.message_handler.handle_user_message = AsyncMock()
    
    # Test handling a user message
    user_id = "user_123"
    message = {
        "type": "user_message",
        "payload": {
            "content": "Test message",
            "thread_id": "thread_123"
        }
    }
    
    await service.handle_websocket_message(user_id, message, mock_db)
    
    # Verify the message handler was called
    service.message_handler.handle_user_message.assert_called_once_with(
        user_id, message["payload"], mock_db
    )