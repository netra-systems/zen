"""Test cases for WebSocket closing state handling.

Tests to prevent regression of the "Cannot call send once a close message has been sent" error.
"""

# Add project root to path
import sys
from pathlib import Path

from ..test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from starlette.websockets import WebSocketState

from app.schemas.websocket_message_types import ServerMessage
from app.websocket.broadcast_core import BroadcastManager

# Add project root to path
from app.websocket.connection import ConnectionInfo, ConnectionManager

# Add project root to path


class TestWebSocketClosingState:
    """Test WebSocket closing state handling."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.client_state = WebSocketState.CONNECTED
        ws.application_state = WebSocketState.CONNECTED
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws
    
    @pytest.fixture
    def connection_info(self, mock_websocket):
        """Create a ConnectionInfo instance."""
        return ConnectionInfo(
            websocket=mock_websocket,
            user_id="test_user",
            connection_id="test_conn_123"
        )
    
    @pytest.fixture
    def connection_manager(self):
        """Create a ConnectionManager instance."""
        return ConnectionManager()
    
    @pytest.fixture
    def broadcast_manager(self, connection_manager):
        """Create a BroadcastManager instance."""
        return BroadcastManager(connection_manager)
    
    @pytest.mark.asyncio
    async def test_is_closing_flag_prevents_send(self, broadcast_manager, connection_info):
        """Test that is_closing flag prevents message sending."""
        # Mark connection as closing
        connection_info.is_closing = True
        
        # Attempt to send message
        result = broadcast_manager._is_connection_ready(connection_info)
        
        # Should return False
        assert result is False
    
    @pytest.mark.asyncio
    async def test_disconnected_client_state_prevents_send(self, broadcast_manager, connection_info):
        """Test that disconnected client state prevents sending."""
        # Set client state to disconnected
        connection_info.websocket.client_state = WebSocketState.DISCONNECTED
        
        # Attempt to check if ready
        result = broadcast_manager._is_connection_ready(connection_info)
        
        # Should return False
        assert result is False
    
    @pytest.mark.asyncio
    async def test_disconnected_app_state_prevents_send(self, broadcast_manager, connection_info):
        """Test that disconnected application state prevents sending."""
        # Set application state to disconnected
        connection_info.websocket.application_state = WebSocketState.DISCONNECTED
        
        # Attempt to check if ready
        result = broadcast_manager._is_connection_ready(connection_info)
        
        # Should return False
        assert result is False
    
    @pytest.mark.asyncio
    async def test_connection_ready_when_fully_connected(self, broadcast_manager, connection_info):
        """Test that connection is ready when fully connected."""
        # Everything is connected and not closing
        connection_info.is_closing = False
        connection_info.websocket.client_state = WebSocketState.CONNECTED
        connection_info.websocket.application_state = WebSocketState.CONNECTED
        
        # Check if ready
        result = broadcast_manager._is_connection_ready(connection_info)
        
        # Should return True
        assert result is True
    
    @pytest.mark.asyncio
    async def test_disconnect_sets_is_closing_flag(self, connection_manager, mock_websocket):
        """Test that disconnect sets the is_closing flag."""
        # Setup connection
        user_id = "test_user"
        connection_manager.active_connections[user_id] = []
        conn_info = ConnectionInfo(websocket=mock_websocket, user_id=user_id)
        connection_manager.active_connections[user_id].append(conn_info)
        connection_manager.connection_registry[conn_info.connection_id] = conn_info
        
        # Disconnect
        await connection_manager.disconnect(user_id, mock_websocket)
        
        # Check that is_closing was set
        assert conn_info.is_closing is True
    
    @pytest.mark.asyncio
    async def test_error_handling_for_send_after_close(self, broadcast_manager, connection_info):
        """Test error handling when send is called after close."""
        # Setup error scenario
        error_msg = 'Cannot call "send" once a close message has been sent'
        connection_info.websocket.send_json = AsyncMock(
            side_effect=RuntimeError(error_msg)
        )
        
        # Attempt to send
        result = await broadcast_manager._send_to_connection(
            connection_info, 
            {"type": "test", "payload": {}}
        )
        
        # Should return False and not raise
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cleanup_marks_connections_as_closing(self, broadcast_manager, connection_manager):
        """Test that cleanup marks connections as closing."""
        # Setup connections
        user_id = "test_user"
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.DISCONNECTED
        ws1.application_state = WebSocketState.DISCONNECTED
        
        conn_info = ConnectionInfo(websocket=ws1, user_id=user_id)
        connections_to_remove = [(user_id, conn_info)]
        
        # Mock _disconnect_internal
        connection_manager._disconnect_internal = AsyncMock()
        
        # Cleanup
        await broadcast_manager._cleanup_broadcast_dead_connections(connections_to_remove)
        
        # Check is_closing was set
        assert conn_info.is_closing is True
        
        # Check disconnect was called
        connection_manager._disconnect_internal.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_send_and_close_race_condition(self, broadcast_manager, connection_info):
        """Test handling of concurrent send and close operations."""
        send_count = 0
        close_called = False
        
        async def mock_send_json(data):
            nonlocal send_count, close_called
            send_count += 1
            if close_called:
                raise RuntimeError('Cannot call "send" once a close message has been sent')
            await asyncio.sleep(0.01)  # Simulate network delay
        
        async def mock_close(code=1000, reason=""):
            nonlocal close_called
            close_called = True
            await asyncio.sleep(0.01)  # Simulate network delay
        
        connection_info.websocket.send_json = mock_send_json
        connection_info.websocket.close = mock_close
        
        # Start send and close concurrently
        send_task = asyncio.create_task(
            broadcast_manager._send_to_connection(connection_info, {"type": "test"})
        )
        close_task = asyncio.create_task(
            broadcast_manager.connection_manager._close_websocket_safely(
                connection_info.websocket, 1000, "test"
            )
        )
        
        # Wait for both
        send_result = await send_task
        await close_task
        
        # Send might succeed or fail depending on timing, but shouldn't raise
        assert isinstance(send_result, bool)
    
    @pytest.mark.asyncio
    async def test_broadcast_to_closing_connection_skipped(self, broadcast_manager, connection_manager):
        """Test that broadcasts skip connections marked as closing."""
        # Setup
        user_id = "test_user"
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws1.application_state = WebSocketState.CONNECTED
        ws1.send_json = AsyncMock()
        
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED
        ws2.application_state = WebSocketState.CONNECTED
        ws2.send_json = AsyncMock()
        
        conn1 = ConnectionInfo(websocket=ws1, user_id=user_id, connection_id="conn1")
        conn2 = ConnectionInfo(websocket=ws2, user_id=user_id, connection_id="conn2")
        
        # Mark conn1 as closing
        conn1.is_closing = True
        
        connection_manager.active_connections[user_id] = [conn1, conn2]
        
        # Broadcast to user with valid message type
        message = {"type": "agent_update", "payload": {"status": "test"}}
        result = await broadcast_manager.broadcast_to_user(user_id, message)
        
        # Only conn2 should receive the message
        ws1.send_json.assert_not_called()
        ws2.send_json.assert_called_once()
        assert result is True


class TestWebSocketStateTransitions:
    """Test WebSocket state transitions."""
    
    @pytest.mark.asyncio
    async def test_state_transition_connected_to_closing(self):
        """Test state transition from connected to closing."""
        ws = AsyncMock()
        ws.client_state = WebSocketState.CONNECTED
        ws.application_state = WebSocketState.CONNECTED
        
        conn_info = ConnectionInfo(websocket=ws, user_id="test")
        
        # Initially not closing
        assert conn_info.is_closing is False
        
        # Mark as closing
        conn_info.is_closing = True
        
        # Should be marked as closing
        assert conn_info.is_closing is True
    
    @pytest.fixture
    def connection_manager(self):
        """Create a ConnectionManager instance."""
        return ConnectionManager()
    
    @pytest.mark.asyncio 
    async def test_close_websocket_safely_checks_states(self, connection_manager):
        """Test that _close_websocket_safely checks both states."""
        ws = AsyncMock()
        ws.close = AsyncMock()
        
        # Test various state combinations
        test_cases = [
            (WebSocketState.CONNECTED, WebSocketState.CONNECTED, True),
            (WebSocketState.CONNECTED, WebSocketState.DISCONNECTED, False),
            (WebSocketState.DISCONNECTED, WebSocketState.CONNECTED, False),
            (WebSocketState.DISCONNECTED, WebSocketState.DISCONNECTED, False),
        ]
        
        for client_state, app_state, should_close in test_cases:
            ws.client_state = client_state
            ws.application_state = app_state
            ws.close.reset_mock()
            
            await connection_manager._close_websocket_safely(ws, 1000, "test")
            
            if should_close:
                ws.close.assert_called_once()
            else:
                ws.close.assert_not_called()