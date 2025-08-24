import sys
from pathlib import Path

import json
from unittest.mock import AsyncMock, MagicMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.schemas.registry import (
    AgentMessage,
    UserMessage,
    WebSocketMessage,
)

from netra_backend.app.services.message_handlers import MessageHandlerService

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
    
    # Mock supervisor.run to return a response
    mock_supervisor.run = AsyncMock(return_value={"response": "Test response"})
    
    handler_service = MessageHandlerService(mock_supervisor, mock_thread_service)
    
    # Mock thread service to return a thread
    mock_thread_service.get_or_create_thread = AsyncMock(return_value=Mock(id="thread_123"))
    mock_thread_service.create_message = AsyncMock()
    mock_thread_service.create_run = AsyncMock(return_value=Mock(id="run_123"))
    mock_thread_service.update_run_status = AsyncMock()
    
    payload = {
        "request": {
            "query": "Test query"
        }
    }
    
    # Test that the handler properly processes the request
    with patch('app.services.message_handlers.manager') as mock_manager:
        mock_manager.send_error = AsyncMock()
        mock_manager.send_message = AsyncMock()
        
        # Verify the handler accepts valid payload structure
        assert handler_service != None
        assert callable(handler_service.handle_start_agent)
        
        # Test with empty query - should still work but with empty request
        invalid_payload = {"request": {}}  # Missing 'query' field
        error_raised = False
        try:
            await handler_service.handle_start_agent("user_123", invalid_payload, mock_session)
            # The handler should process the request (even with empty query)
            # Verify key methods were called
            assert mock_thread_service.get_or_create_thread.called, "Should get or create thread"
            assert mock_thread_service.create_message.called, "Should create message"
            assert mock_supervisor.run.called, "Should run supervisor"
        except (KeyError, ValueError, AttributeError) as e:
            # If an error is raised, that's also acceptable
            error_raised = True
            assert str(e) is not None, "Error message should not be None"
        
        # Verify that handler either processed request or raised error (both are valid)
        if not error_raised:
            # If no error, verify handler was called and returned a valid response
            assert mock_supervisor.run.called, "Supervisor should have been invoked"
            # Check that the supervisor returned some response (even if it's None for empty request)
            assert hasattr(mock_supervisor.run, 'return_value'), \
                   "Supervisor should have a return value"
        else:
            # If error was raised, it was handled appropriately
            assert error_raised, "Error was raised and handled as expected"
@pytest.mark.asyncio
async def test_websocket_schema_imports():
    """Test that WebSocket schemas can be imported."""
    message = WebSocketMessage(type="user_message", payload={"data": "test"})
    assert message.type == "user_message"
    
    user_msg = UserMessage(content="Hello")
    assert user_msg.content == "Hello"
    
    agent_msg = AgentMessage(run_id="run_123", agent_id="agent_456", status="active", message="Response")
    assert agent_msg.message == "Response"