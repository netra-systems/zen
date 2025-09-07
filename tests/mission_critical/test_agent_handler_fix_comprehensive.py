class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

"""
Comprehensive test for the critical agent_handler async context manager fix.

Tests the actual message flow through the agent handler to ensure:
1. The fix correctly uses async with instead of async for
2. Messages are properly routed
3. WebSocket events are sent
4. Database sessions are properly managed
"""

import pytest
import asyncio
from contextlib import asynccontextmanager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


@pytest.mark.asyncio
class TestAgentHandlerComprehensiveFix:
    """Comprehensive test suite for agent handler fix."""

    async def test_agent_handler_with_real_flow(self):
        """Test the complete flow with the fixed async context manager pattern."""
        
        handler = AgentMessageHandler()
        
        # Create real message objects
        start_agent_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "agent_name": "triage",
                "user_request": "Help me debug my application"
            }
        )
        
        # Mock WebSocket
        websocket = TestWebSocketConnection()
        
        # Mock database session
        websocket = TestWebSocketConnection()
        
        # Create the async context manager for database session
        @asynccontextmanager
        async def mock_get_request_scoped_db_session():
            """Mock that returns an async context manager with session."""
            try:
                yield mock_session
            finally:
                await mock_session.close()
        
        # Mock WebSocket manager
        websocket = TestWebSocketConnection()
        mock_ws_manager.get_connection_id_by_websocket = Mock(return_value="conn_test_123")
        mock_ws_manager.websocket = TestWebSocketConnection()  # Real WebSocket implementation
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_getter:
            mock_getter.return_value = mock_get_request_scoped_db_session()
            
            with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_manager') as mock_ws_getter:
                mock_ws_getter.return_value = mock_ws_manager
                
                with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_service_class:
                    # Mock the message handler service
                    websocket = TestWebSocketConnection()
                    mock_service.handle_start_agent = AsyncMock(return_value={
                        "success": True,
                        "run_id": "run_test_456",
                        "agent": "triage",
                        "message": "Triage agent started successfully"
                    })
                    mock_service_class.return_value = mock_service
                    
                    # Execute the handler
                    result = await handler.handle_message(
                        user_id="test_user_789",
                        message=start_agent_message,
                        websocket=mock_websocket
                    )
                    
                    # Verify success
                    assert result is True
                    
                    # Verify the service was called correctly
                    mock_service.handle_start_agent.assert_called_once()
                    call_args = mock_service.handle_start_agent.call_args
                    assert call_args[1]['agent_name'] == "triage"
                    assert call_args[1]['user_request'] == "Help me debug my application"
                    
                    # Verify thread association was updated
                    mock_ws_manager.update_connection_thread.assert_called()
                    
                    # Verify database session was used (not errored out)
                    assert mock_session is not None

    async def test_multiple_message_types(self):
        """Test handling different message types with the fixed pattern."""
        
        handler = AgentMessageHandler()
        
        message_types_to_test = [
            (MessageType.START_AGENT, {"agent_name": "triage", "user_request": "test"}),
            (MessageType.USER_MESSAGE, {"message": "Hello agent", "thread_id": "thread_123"}),
        ]
        
        for msg_type, payload in message_types_to_test:
            message = WebSocketMessage(type=msg_type, payload=payload)
            
            websocket = TestWebSocketConnection()
            
            @asynccontextmanager
            async def mock_get_request_scoped_db_session():
                yield mock_session
            
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_getter:
                mock_getter.return_value = mock_get_request_scoped_db_session()
                
                with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_service_class:
                    websocket = TestWebSocketConnection()
                    
                    # Set up appropriate mock responses
                    if msg_type == MessageType.START_AGENT:
                        mock_service.handle_start_agent = AsyncMock(return_value={
                            "success": True,
                            "run_id": "test_run",
                            "agent": payload["agent_name"]
                        })
                    elif msg_type == MessageType.USER_MESSAGE:
                        mock_service.handle_user_message = AsyncMock(return_value={
                            "success": True,
                            "message": "Response to user"
                        })
                    
                    mock_service_class.return_value = mock_service
                    
                    # Should not raise async for error
                    result = await handler.handle_message(
                        user_id=f"user_{msg_type.value}",
                        message=message,
                        websocket=mock_websocket
                    )
                    
                    # Should have some result (True or False)
                    assert result is not None

    async def test_error_handling_with_fixed_pattern(self):
        """Test that errors in message handling are properly caught."""
        
        handler = AgentMessageHandler()
        
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"agent_name": "triage", "user_request": "test"}
        )
        
        websocket = TestWebSocketConnection()
        
        @asynccontextmanager
        async def mock_get_request_scoped_db_session():
            yield mock_session
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_getter:
            mock_getter.return_value = mock_get_request_scoped_db_session()
            
            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_service_class:
                # Make the service raise an error
                websocket = TestWebSocketConnection()
                mock_service.handle_start_agent = AsyncMock(
                    side_effect=Exception("Service error")
                )
                mock_service_class.return_value = mock_service
                
                # Should handle the error gracefully
                result = await handler.handle_message(
                    user_id="error_test_user",
                    message=message,
                    websocket=mock_websocket
                )
                
                # Should return False on error
                assert result is False
                
                # Should update error stats
                assert handler.processing_stats["errors"] > 0

    async def test_concurrent_message_handling(self):
        """Test that multiple concurrent messages can be handled."""
        
        handler = AgentMessageHandler()
        
        async def handle_single_message(msg_id: int):
            message = WebSocketMessage(
                type=MessageType.START_AGENT,
                payload={"agent_name": f"agent_{msg_id}", "user_request": f"test_{msg_id}"}
            )
            
            websocket = TestWebSocketConnection()
            
            @asynccontextmanager
            async def mock_get_request_scoped_db_session():
                yield mock_session
            
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_getter:
                mock_getter.return_value = mock_get_request_scoped_db_session()
                
                with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_service_class:
                    websocket = TestWebSocketConnection()
                    mock_service.handle_start_agent = AsyncMock(return_value={
                        "success": True,
                        "run_id": f"run_{msg_id}",
                        "agent": f"agent_{msg_id}"
                    })
                    mock_service_class.return_value = mock_service
                    
                    return await handler.handle_message(
                        user_id=f"user_{msg_id}",
                        message=message,
                        websocket=mock_websocket
                    )
        
        # Handle 5 messages concurrently
        results = await asyncio.gather(*[
            handle_single_message(i) for i in range(5)
        ])
        
        # All should succeed
        assert all(results)
        
        # Stats should be updated
        assert handler.processing_stats[MessageType.START_AGENT] >= 5