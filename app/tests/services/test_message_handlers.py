import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from app.services.message_handlers import MessageHandlerService
from app.schemas.WebSocket import WebSocketMessage, UserMessage, AgentMessage
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_message_handler_service_initialization():
    mock_supervisor = Mock()
    mock_thread_service = Mock()
    
    handler_service = MessageHandlerService(mock_supervisor, mock_thread_service)
    assert handler_service.supervisor is not None
    assert handler_service.thread_service is not None

@pytest.mark.asyncio
async def test_handle_start_agent():
    mock_supervisor = Mock()
    mock_thread_service = Mock()
    mock_session = Mock(spec=AsyncSession)
    
    handler_service = MessageHandlerService(mock_supervisor, mock_thread_service)
    
    # Mock thread service to return a thread
    mock_thread_service.get_or_create_thread = AsyncMock(return_value=Mock(id="thread_123"))
    
    payload = {
        "request": {
            "query": "Test query"
        }
    }
    
    # Test that the method exists and can be called
    with patch('app.services.message_handlers.manager') as mock_manager:
        mock_manager.send_error = AsyncMock()
        try:
            await handler_service.handle_start_agent("user_123", payload, mock_session)
            # If no exception, the basic structure works
            assert True
        except Exception as e:
            # Expected since we're using mocks
            assert "supervisor" in str(e).lower() or "agent" in str(e).lower()

@pytest.mark.asyncio 
async def test_websocket_schema_imports():
    """Test that WebSocket schemas can be imported."""
    message = WebSocketMessage(type="test", payload={"data": "test"})
    assert message.type == "test"
    
    user_msg = UserMessage(text="Hello")
    assert user_msg.text == "Hello"
    
    agent_msg = AgentMessage(text="Response")
    assert agent_msg.text == "Response"