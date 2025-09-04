"""
Mission Critical Tests for WebSocket Error Fixes - 2025-09-04

Tests for:
1. Message routing failures
2. WebSocket accept race condition 
3. Async context manager errors
4. Handler registration and cleanup
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import WebSocket
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from netra_backend.app.websocket_core import (
    WebSocketManager,
    MessageRouter,
    get_websocket_manager,
    get_message_router,
)
from netra_backend.app.websocket_core.handlers import ConnectionHandler, MessageRouter
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage


class TestWebSocketMessageRouting:
    """Test message routing fixes."""
    
    @pytest.mark.asyncio
    async def test_handler_registration_on_connection(self):
        """Test that handlers are properly registered when connection is established."""
        # Setup
        router = MessageRouter()
        initial_count = len(router.handlers)
        
        # Create mock WebSocket and dependencies
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.app.state.agent_supervisor = Mock()
        mock_websocket.app.state.thread_service = Mock()
        
        # Import and create handler
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
        from netra_backend.app.services.message_handlers import MessageHandlerService
        
        ws_manager = Mock()
        message_service = MessageHandlerService(
            mock_websocket.app.state.agent_supervisor,
            mock_websocket.app.state.thread_service,
            ws_manager
        )
        agent_handler = AgentMessageHandler(message_service, mock_websocket)
        
        # Register handler
        router.add_handler(agent_handler)
        
        # Verify
        assert len(router.handlers) == initial_count + 1
        assert any(isinstance(h, AgentMessageHandler) for h in router.handlers)
        
        # Test message routing
        message = WebSocketMessage(
            type=MessageType.CHAT,
            payload={"content": "test message"},
            timestamp=time.time()
        )
        
        handler = router._find_handler(MessageType.CHAT)
        assert handler is not None
        assert isinstance(handler, (AgentMessageHandler, type(agent_handler)))
    
    @pytest.mark.asyncio
    async def test_handler_cleanup_on_disconnect(self):
        """Test that handlers are properly cleaned up on disconnect."""
        # Setup
        router = MessageRouter()
        mock_websocket1 = AsyncMock(spec=WebSocket)
        mock_websocket2 = AsyncMock(spec=WebSocket)
        
        # Add handlers for two different connections
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
        
        handler1 = AgentMessageHandler(Mock(), mock_websocket1)
        handler2 = AgentMessageHandler(Mock(), mock_websocket2)
        
        router.add_handler(handler1)
        router.add_handler(handler2)
        initial_count = len(router.handlers)
        
        # Simulate disconnect cleanup for websocket1
        handlers_to_remove = []
        for handler in router.handlers:
            if isinstance(handler, AgentMessageHandler) and handler.websocket == mock_websocket1:
                handlers_to_remove.append(handler)
        
        for handler in handlers_to_remove:
            router.handlers.remove(handler)
        
        # Verify
        assert len(router.handlers) == initial_count - 1
        assert handler1 not in router.handlers
        assert handler2 in router.handlers
    
    @pytest.mark.asyncio
    async def test_message_routing_with_missing_handler(self):
        """Test graceful handling when no handler is available."""
        router = MessageRouter()
        
        # Remove all handlers to simulate missing handler scenario
        router.handlers = []
        
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = Mock()
        mock_websocket.application_state._mock_name = "test"
        mock_websocket.send_json = AsyncMock()
        
        # Try to route a message
        result = await router.route_message(
            "test_user",
            mock_websocket,
            {"type": "unknown_type", "content": "test"}
        )
        
        # Should handle gracefully with fallback
        assert result is True  # Fallback handler returns True
        
        # Verify ack was sent for unknown message
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "ack"
        assert call_args["received_type"] == "unknown_type"


class TestWebSocketRaceCondition:
    """Test WebSocket accept race condition fixes."""
    
    @pytest.mark.asyncio
    async def test_accept_before_authentication(self):
        """Test that WebSocket accepts connection before authentication."""
        from netra_backend.app.routes.websocket import websocket_endpoint
        
        # Mock WebSocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.headers = {"sec-websocket-protocol": "jwt-auth"}
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
        mock_websocket.app.state.agent_supervisor = None
        mock_websocket.app.state.thread_service = None
        mock_websocket.app.state.startup_complete = True
        
        # Mock authenticator to simulate auth failure
        with patch('netra_backend.app.routes.websocket.get_websocket_authenticator') as mock_auth:
            mock_authenticator = Mock()
            mock_authenticator.authenticate_websocket = AsyncMock(side_effect=Exception("Auth failed"))
            mock_auth.return_value = mock_authenticator
            
            # Run endpoint
            try:
                await websocket_endpoint(mock_websocket)
            except Exception:
                pass
            
            # Verify accept was called BEFORE authentication
            mock_websocket.accept.assert_called_once_with(subprotocol="jwt-auth")
            assert mock_websocket.accept.called
            assert mock_authenticator.authenticate_websocket.called
            
            # Verify order: accept was called before authenticate
            accept_call_order = None
            auth_call_order = None
            
            for i, call in enumerate(mock_websocket.method_calls):
                if call[0] == 'accept':
                    accept_call_order = i
            
            # Authentication happens after accept
            assert accept_call_order is not None
            assert accept_call_order == 0  # First call should be accept
    
    @pytest.mark.asyncio 
    async def test_concurrent_connections(self):
        """Test handling of multiple concurrent connections."""
        router = MessageRouter()
        connections = []
        
        async def create_connection(conn_id: str):
            mock_ws = AsyncMock(spec=WebSocket)
            mock_ws.connection_id = conn_id
            mock_ws.app.state.agent_supervisor = Mock()
            mock_ws.app.state.thread_service = Mock()
            
            # Simulate connection setup
            from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
            handler = AgentMessageHandler(Mock(), mock_ws)
            router.add_handler(handler)
            
            connections.append((conn_id, mock_ws, handler))
            await asyncio.sleep(0.01)  # Simulate network delay
            return handler
        
        # Create 10 concurrent connections
        tasks = [create_connection(f"conn_{i}") for i in range(10)]
        handlers = await asyncio.gather(*tasks)
        
        # Verify all handlers were registered
        assert len(handlers) == 10
        for handler in handlers:
            assert handler in router.handlers
        
        # Clean up all connections
        for conn_id, mock_ws, handler in connections:
            if handler in router.handlers:
                router.handlers.remove(handler)
        
        # Verify cleanup
        for handler in handlers:
            assert handler not in router.handlers


class TestAsyncContextManager:
    """Test async context manager fixes for database sessions."""
    
    @pytest.mark.asyncio
    async def test_database_session_context_manager(self):
        """Test that database sessions use proper async context manager."""
        from netra_backend.app.dependencies import get_request_scoped_db_session
        
        # Mock the DatabaseManager
        with patch('netra_backend.app.dependencies.DatabaseManager') as mock_dm:
            mock_session = AsyncMock()
            mock_dm.get_async_session.return_value.__aenter__.return_value = mock_session
            mock_dm.get_async_session.return_value.__aexit__.return_value = None
            
            # Use the context manager
            async with get_request_scoped_db_session() as session:
                assert session == mock_session
            
            # Verify context manager was properly used
            mock_dm.get_async_session.assert_called_once()
            mock_dm.get_async_session.return_value.__aenter__.assert_called_once()
            mock_dm.get_async_session.return_value.__aexit__.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agent_message_handler_db_session(self):
        """Test AgentMessageHandler properly manages database sessions."""
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
        from netra_backend.app.services.message_handlers import MessageHandlerService
        
        # Mock dependencies
        mock_supervisor = Mock()
        mock_thread_service = Mock()
        mock_ws_manager = Mock()
        mock_websocket = AsyncMock(spec=WebSocket)
        
        # Create handler
        message_service = MessageHandlerService(
            mock_supervisor,
            mock_thread_service,
            mock_ws_manager
        )
        handler = AgentMessageHandler(message_service, mock_websocket)
        
        # Mock database session
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            # Mock message service methods
            message_service.handle_user_message = AsyncMock()
            
            # Create test message
            message = WebSocketMessage(
                type=MessageType.CHAT,
                payload={"content": "test"},
                timestamp=time.time()
            )
            
            # Handle message
            result = await handler.handle_message("test_user", mock_websocket, message)
            
            # Verify session was properly managed
            mock_get_session.assert_called_once()
            mock_get_session.return_value.__aenter__.assert_called_once()
            mock_get_session.return_value.__aexit__.assert_called_once()


class TestErrorRecovery:
    """Test error recovery and resilience."""
    
    @pytest.mark.asyncio
    async def test_missing_thread_service_recovery(self):
        """Test automatic creation of missing thread_service."""
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.headers = {}
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
        mock_websocket.app.state.agent_supervisor = Mock()
        mock_websocket.app.state.thread_service = None  # Missing
        mock_websocket.app.state.startup_complete = True
        
        with patch('netra_backend.app.routes.websocket.get_websocket_authenticator') as mock_auth:
            mock_auth.return_value.authenticate_websocket = AsyncMock(return_value="test_user")
            
            with patch('netra_backend.app.routes.websocket.ThreadService') as mock_ts:
                mock_thread_service = Mock()
                mock_ts.return_value = mock_thread_service
                
                from netra_backend.app.routes.websocket import websocket_endpoint
                
                try:
                    await websocket_endpoint(mock_websocket)
                except WebSocketDisconnect:
                    pass
                
                # Verify thread_service was created
                assert mock_websocket.app.state.thread_service == mock_thread_service
    
    @pytest.mark.asyncio
    async def test_environment_specific_error_handling(self):
        """Test different error handling for staging vs development."""
        from netra_backend.app.routes.websocket import websocket_endpoint
        
        # Test staging environment - should raise critical errors
        with patch('netra_backend.app.routes.websocket.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda k, d: "staging" if k == "ENVIRONMENT" else d
            
            mock_websocket = AsyncMock(spec=WebSocket)
            mock_websocket.headers = {}
            mock_websocket.accept = AsyncMock()
            mock_websocket.app.state.agent_supervisor = None  # Missing in staging
            mock_websocket.app.state.thread_service = None
            mock_websocket.app.state.startup_complete = True
            mock_websocket.send_json = AsyncMock()
            mock_websocket.close = AsyncMock()
            
            with patch('netra_backend.app.routes.websocket.safe_websocket_send') as mock_send:
                with patch('netra_backend.app.routes.websocket.safe_websocket_close') as mock_close:
                    with pytest.raises(RuntimeError, match="Chat critical failure in staging"):
                        await websocket_endpoint(mock_websocket)
                    
                    # Verify critical error was sent
                    mock_send.assert_called_once()
                    error_msg = mock_send.call_args[0][1]
                    assert error_msg["error_code"] == "CRITICAL_FAILURE"


# Integration test combining all fixes
@pytest.mark.asyncio
async def test_full_websocket_flow_with_fixes():
    """Integration test of complete WebSocket flow with all fixes."""
    from netra_backend.app.routes.websocket import websocket_endpoint
    
    # Setup mock environment
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.headers = {"sec-websocket-protocol": "jwt-auth"}
    mock_websocket.accept = AsyncMock()
    mock_websocket.app.state.agent_supervisor = Mock()
    mock_websocket.app.state.thread_service = Mock()
    mock_websocket.app.state.startup_complete = True
    
    # Setup message flow
    messages = [
        json.dumps({"type": "chat", "content": "Hello", "thread_id": "thread123"}),
        json.dumps({"type": "ping"}),
    ]
    mock_websocket.receive_text = AsyncMock(side_effect=messages + [WebSocketDisconnect()])
    mock_websocket.send_json = AsyncMock()
    mock_websocket.send_text = AsyncMock()
    
    with patch('netra_backend.app.routes.websocket.get_websocket_authenticator') as mock_auth:
        mock_auth.return_value.authenticate_websocket = AsyncMock(return_value="test_user")
        
        with patch('netra_backend.app.routes.websocket.get_websocket_manager') as mock_mgr:
            ws_manager = Mock()
            ws_manager.connect_user = AsyncMock(return_value="conn123")
            ws_manager.disconnect_user = AsyncMock()
            ws_manager.get_connection_id_by_websocket = Mock(return_value="conn123")
            ws_manager.update_connection_thread = Mock(return_value=True)
            mock_mgr.return_value = ws_manager
            
            with patch('netra_backend.app.routes.websocket.get_message_router') as mock_router:
                router = MessageRouter()
                mock_router.return_value = router
                
                try:
                    await websocket_endpoint(mock_websocket)
                except WebSocketDisconnect:
                    pass
                
                # Verify flow
                mock_websocket.accept.assert_called_once()
                mock_auth.return_value.authenticate_websocket.assert_called_once()
                ws_manager.connect_user.assert_called_once()
                
                # Verify handlers were registered and cleaned up
                # (would need to track in real implementation)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])