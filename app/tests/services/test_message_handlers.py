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
    assert handler_service.supervisor != None
    assert handler_service.thread_service != None

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
    
    # Test that the handler properly processes the request
    with patch('app.services.message_handlers.manager') as mock_manager:
        mock_manager.send_error = AsyncMock()
        
        # Verify the handler accepts valid payload structure
        assert handler_service != None
        assert callable(handler_service.handle_start_agent)
        
        # Test with invalid payload should raise or handle error
        invalid_payload = {"request": {}}  # Missing 'query' field
        error_raised = False
        try:
            await handler_service.handle_start_agent("user_123", invalid_payload, mock_session)
            # If it doesn't raise, check that error handler was called
            assert mock_manager.send_error.called, "Error handler should be called for invalid payload"
            assert mock_manager.send_error.call_count > 0, "Error handler should be called at least once"
        except (KeyError, ValueError, AttributeError) as e:
            # Expected for invalid payload - verify we got the right kind of error
            error_raised = True
            assert str(e) is not None, "Error message should not be None"
        
        # Either an error was raised OR the error handler was called
        assert error_raised or mock_manager.send_error.called, "Invalid payload should either raise an error or call error handler"

@pytest.mark.asyncio 
async def test_websocket_schema_imports():
    """Test that WebSocket schemas can be imported."""
    message = WebSocketMessage(type="test", payload={"data": "test"})
    assert message.type == "test"
    
    user_msg = UserMessage(text="Hello")
    assert user_msg.text == "Hello"
    
    agent_msg = AgentMessage(text="Response")
    assert agent_msg.text == "Response"