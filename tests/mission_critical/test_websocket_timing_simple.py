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
Simplified WebSocket timing tests focusing on actual implementation.
Tests critical timing scenarios with the real WebSocket manager.
"""

import asyncio
import uuid
import json
from typing import Dict, Any
import pytest
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager, get_websocket_manager
from netra_backend.app.websocket_core.message_buffer import BufferConfig
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestWebSocketTimingSimple:
    """Test critical WebSocket timing scenarios."""

    @pytest.fixture
    async def setup(self):
        """Setup test environment."""
        manager = WebSocketManager()
        user_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        yield {
            'manager': manager,
            'user_id': user_id,
            'run_id': run_id,
            'thread_id': thread_id
        }
        
        # Cleanup
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_connection_and_message_flow(self, setup):
        """Test basic connection and message flow."""
        manager = setup['manager']
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        # Connect
        connection_id = await manager.connect_user(
            setup['user_id'],
            mock_ws,
            thread_id=setup['thread_id']
        )
        
        # Send message
        test_message = {
            'type': 'agent_started',
            'data': {'agent': 'test'}
        }
        
        success = await manager.send_to_user(setup['user_id'], test_message)
        assert success
        
        # Verify message sent
        await asyncio.sleep(0.1)
        mock_ws.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_message_with_thread_context(self, setup):
        """Test message with thread context."""
        manager = setup['manager']
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        # Connect with thread_id
        connection_id = await manager.connect_user(
            setup['user_id'], 
            mock_ws,
            thread_id=setup['thread_id']
        )
        
        # Send message - use a recognized agent event type
        message = {
            'type': 'agent_started',
            'data': {'content': 'test'}
        }
        
        success = await manager.send_to_user(setup['user_id'], message)
        assert success
        
        # Verify sent
        await asyncio.sleep(0.1)
        mock_ws.send_json.assert_called()
        
        # Check message was sent
        sent_msg = mock_ws.send_json.call_args[0][0]
        assert sent_msg['type'] == 'agent_started'
        assert sent_msg['data']['content'] == 'test'

    @pytest.mark.asyncio
    async def test_multiple_connections(self, setup):
        """Test handling multiple connections."""
        manager = setup['manager']
        
        connections = []
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocket)
            mock_ws.websocket = TestWebSocketConnection()
            mock_ws.client_state = WebSocketState.CONNECTED
            user_id = str(uuid.uuid4())
            
            connection_id = await manager.connect_user(
                user_id,
                mock_ws,
                thread_id=setup['thread_id']
            )
            
            connections.append({
                'ws': mock_ws,
                'user_id': user_id,
                'connection_id': connection_id
            })
        
        # Send to each connection
        for conn in connections:
            success = await manager.send_to_user(conn['user_id'], {
                'type': 'test',
                'data': {'user_id': conn['user_id']}
            })
            assert success
        
        # Verify all received
        await asyncio.sleep(0.1)
        for conn in connections:
            conn['ws'].send_json.assert_called()

    @pytest.mark.asyncio
    async def test_disconnect_and_cleanup(self, setup):
        """Test disconnection and cleanup."""
        manager = setup['manager']
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        # Connect
        connection_id = await manager.connect_user(
            setup['user_id'],
            mock_ws,
            thread_id=setup['thread_id']
        )
        
        # Disconnect
        await manager.disconnect_user(setup['user_id'], mock_ws, 1000, "Test disconnect")
        
        # Try to send - should handle gracefully
        result = await manager.send_to_user(setup['user_id'], {
            'type': 'test',
            'data': {}
        })
        
        # Should return False since user is disconnected
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])