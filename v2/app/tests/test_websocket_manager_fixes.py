"""Test suite for WebSocket manager critical fixes."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from starlette.websockets import WebSocketState

from app.ws_manager import WebSocketManager, ConnectionInfo


@pytest.fixture
def ws_manager():
    """Create a fresh WebSocket manager instance."""
    # Reset singleton for testing
    WebSocketManager._instance = None
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    ws = Mock()
    ws.client_state = WebSocketState.CONNECTED
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_broadcast_uses_correct_websocket_attribute(ws_manager, mock_websocket):
    """Test that broadcast method correctly accesses websocket.send_json()."""
    # Connect a user
    user_id = "test_user"
    conn_info = ConnectionInfo(websocket=mock_websocket, user_id=user_id)
    ws_manager.active_connections[user_id] = [conn_info]
    ws_manager.connection_registry[conn_info.connection_id] = conn_info
    
    # Broadcast a message
    message = {"type": "test", "data": "test_data"}
    result = await ws_manager.broadcast(message)
    
    # Verify the message was sent correctly
    mock_websocket.send_json.assert_called_once()
    sent_message = mock_websocket.send_json.call_args[0][0]
    assert sent_message["type"] == "test"
    assert sent_message["data"] == "test_data"
    assert "timestamp" in sent_message
    
    # Verify statistics
    assert result["successful"] == 1
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_broadcast_handles_disconnected_websockets(ws_manager):
    """Test that broadcast properly handles disconnected WebSockets."""
    # Create mix of connected and disconnected sockets
    connected_ws = Mock()
    connected_ws.client_state = WebSocketState.CONNECTED
    connected_ws.send_json = AsyncMock()
    connected_ws.close = AsyncMock()
    
    disconnected_ws = Mock()
    disconnected_ws.client_state = WebSocketState.DISCONNECTED
    disconnected_ws.close = AsyncMock()
    
    # Add connections
    ws_manager.active_connections["user1"] = [
        ConnectionInfo(websocket=connected_ws, user_id="user1"),
        ConnectionInfo(websocket=disconnected_ws, user_id="user1")
    ]
    
    # Broadcast
    result = await ws_manager.broadcast({"type": "test"})
    
    # Verify only connected socket received message
    connected_ws.send_json.assert_called_once()
    assert result["successful"] == 1
    assert result["failed"] == 1


@pytest.mark.asyncio
async def test_broadcast_handles_send_errors(ws_manager):
    """Test that broadcast handles errors during send gracefully."""
    # Create WebSocket that throws error on send
    error_ws = Mock()
    error_ws.client_state = WebSocketState.CONNECTED
    error_ws.send_json = AsyncMock(side_effect=RuntimeError("Connection lost"))
    error_ws.close = AsyncMock()
    
    # Add connection
    conn_info = ConnectionInfo(websocket=error_ws, user_id="user1")
    ws_manager.active_connections["user1"] = [conn_info]
    ws_manager.connection_registry[conn_info.connection_id] = conn_info
    
    # Broadcast should handle error gracefully
    result = await ws_manager.broadcast({"type": "test"})
    
    assert result["successful"] == 0
    assert result["failed"] == 1
    
    # Connection should be removed
    assert "user1" not in ws_manager.active_connections


@pytest.mark.asyncio
async def test_connection_limit_per_user(ws_manager):
    """Test that connection limit per user is enforced."""
    user_id = "test_user"
    
    # Create multiple mock websockets
    websockets = []
    for i in range(ws_manager.MAX_CONNECTIONS_PER_USER + 2):
        ws = Mock()
        ws.client_state = WebSocketState.CONNECTED
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        websockets.append(ws)
    
    # Connect up to the limit
    for i in range(ws_manager.MAX_CONNECTIONS_PER_USER):
        await ws_manager.connect(user_id, websockets[i])
    
    assert len(ws_manager.active_connections[user_id]) == ws_manager.MAX_CONNECTIONS_PER_USER
    
    # Connect one more - should close oldest
    await ws_manager.connect(user_id, websockets[ws_manager.MAX_CONNECTIONS_PER_USER])
    
    # Verify limit is maintained
    assert len(ws_manager.active_connections[user_id]) == ws_manager.MAX_CONNECTIONS_PER_USER
    
    # Verify oldest connection was closed
    websockets[0].close.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_with_multiple_users(ws_manager):
    """Test broadcast to multiple users with multiple connections each."""
    # Create connections for multiple users
    users_connections = {}
    for user_id in ["user1", "user2", "user3"]:
        users_connections[user_id] = []
        for i in range(2):
            ws = Mock()
            ws.client_state = WebSocketState.CONNECTED
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            
            conn_info = ConnectionInfo(websocket=ws, user_id=user_id)
            users_connections[user_id].append(conn_info)
            
            if user_id not in ws_manager.active_connections:
                ws_manager.active_connections[user_id] = []
            ws_manager.active_connections[user_id].append(conn_info)
            ws_manager.connection_registry[conn_info.connection_id] = conn_info
    
    # Broadcast message
    message = {"type": "broadcast_test", "content": "test"}
    result = await ws_manager.broadcast(message)
    
    # Verify all connections received the message
    assert result["successful"] == 6  # 3 users * 2 connections each
    assert result["failed"] == 0
    
    # Verify each WebSocket received the message
    for user_conns in users_connections.values():
        for conn_info in user_conns:
            conn_info.websocket.send_json.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown_handles_cancelled_tasks(ws_manager):
    """Test that shutdown properly handles already cancelled tasks."""
    # Create mock tasks
    active_task = Mock()
    active_task.done.return_value = False
    active_task.cancel = Mock()
    
    cancelled_task = Mock()
    cancelled_task.done.return_value = True
    cancelled_task.cancel = Mock()
    
    ws_manager.heartbeat_tasks = {
        "task1": active_task,
        "task2": cancelled_task
    }
    
    # Create mock connection
    ws = Mock()
    ws.client_state = WebSocketState.CONNECTED
    ws.close = AsyncMock()
    
    conn_info = ConnectionInfo(websocket=ws, user_id="user1")
    ws_manager.active_connections["user1"] = [conn_info]
    
    # Run shutdown
    await ws_manager.shutdown()
    
    # Verify only active task was cancelled
    active_task.cancel.assert_called_once()
    cancelled_task.cancel.assert_not_called()
    
    # Verify connection was closed
    ws.close.assert_called_once()
    
    # Verify all structures are cleared
    assert len(ws_manager.active_connections) == 0
    assert len(ws_manager.connection_registry) == 0
    assert len(ws_manager.heartbeat_tasks) == 0


@pytest.mark.asyncio
async def test_broadcast_adds_timestamp(ws_manager, mock_websocket):
    """Test that broadcast adds timestamp if not present."""
    user_id = "test_user"
    conn_info = ConnectionInfo(websocket=mock_websocket, user_id=user_id)
    ws_manager.active_connections[user_id] = [conn_info]
    
    # Send message without timestamp
    await ws_manager.broadcast({"type": "test"})
    
    # Verify timestamp was added
    sent_message = mock_websocket.send_json.call_args[0][0]
    assert "timestamp" in sent_message
    assert isinstance(sent_message["timestamp"], float)


@pytest.mark.asyncio
async def test_broadcast_preserves_existing_timestamp(ws_manager, mock_websocket):
    """Test that broadcast preserves existing timestamp."""
    user_id = "test_user"
    conn_info = ConnectionInfo(websocket=mock_websocket, user_id=user_id)
    ws_manager.active_connections[user_id] = [conn_info]
    
    # Send message with timestamp
    original_timestamp = 1234567890.0
    await ws_manager.broadcast({"type": "test", "timestamp": original_timestamp})
    
    # Verify original timestamp was preserved
    sent_message = mock_websocket.send_json.call_args[0][0]
    assert sent_message["timestamp"] == original_timestamp


@pytest.mark.asyncio
async def test_broadcast_updates_statistics(ws_manager):
    """Test that broadcast properly updates statistics."""
    # Setup connections
    success_ws = Mock()
    success_ws.client_state = WebSocketState.CONNECTED
    success_ws.send_json = AsyncMock()
    
    error_ws = Mock()
    error_ws.client_state = WebSocketState.CONNECTED
    error_ws.send_json = AsyncMock(side_effect=RuntimeError("Error"))
    error_ws.close = AsyncMock()
    
    # Add connections
    conn1 = ConnectionInfo(websocket=success_ws, user_id="user1")
    conn2 = ConnectionInfo(websocket=error_ws, user_id="user2")
    
    ws_manager.active_connections["user1"] = [conn1]
    ws_manager.active_connections["user2"] = [conn2]
    ws_manager.connection_registry[conn1.connection_id] = conn1
    ws_manager.connection_registry[conn2.connection_id] = conn2
    
    # Reset stats
    ws_manager._stats["total_messages_sent"] = 0
    ws_manager._stats["total_errors"] = 0
    
    # Broadcast
    await ws_manager.broadcast({"type": "test"})
    
    # Verify statistics were updated
    assert ws_manager._stats["total_messages_sent"] == 1
    assert ws_manager._stats["total_errors"] == 1
    assert conn1.message_count == 1
    assert conn2.error_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])