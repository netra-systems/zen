"""Comprehensive tests for WebSocket Manager with 100% coverage."""
import pytest
import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
from starlette.websockets import WebSocketState
from app.ws_manager import WebSocketManager, ConnectionInfo, manager, ws_manager
import json


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket with necessary attributes."""
    ws = AsyncMock()
    ws.client_state = WebSocketState.CONNECTED
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def ws_manager_instance():
    """Create a fresh WebSocketManager instance for testing."""
    # Reset singleton for testing
    WebSocketManager._instance = None
    mgr = WebSocketManager()
    yield mgr
    # Cleanup
    WebSocketManager._instance = None


@pytest.mark.asyncio
class TestWebSocketManager:
    """Test suite for WebSocketManager."""
    
    async def test_singleton_pattern(self):
        """Test that WebSocketManager follows singleton pattern."""
        mgr1 = WebSocketManager()
        mgr2 = WebSocketManager()
        assert mgr1 is mgr2
        assert manager is ws_manager
    
    async def test_initialization(self, ws_manager_instance):
        """Test proper initialization of WebSocketManager."""
        assert ws_manager_instance.active_connections == {}
        assert ws_manager_instance.connection_registry == {}
        assert ws_manager_instance.heartbeat_tasks == {}
        assert ws_manager_instance._stats["total_connections"] == 0
        assert ws_manager_instance._stats["total_messages_sent"] == 0
        assert ws_manager_instance._stats["total_messages_received"] == 0
        assert ws_manager_instance._stats["total_errors"] == 0
        assert ws_manager_instance._stats["connection_failures"] == 0
    
    async def test_connect_new_user(self, ws_manager_instance, mock_websocket):
        """Test connecting a new user."""
        user_id = "test_user_1"
        
        # Connect user
        conn_info = await ws_manager_instance.connect(user_id, mock_websocket)
        
        # Verify connection was established
        assert user_id in ws_manager_instance.active_connections
        assert len(ws_manager_instance.active_connections[user_id]) == 1
        assert conn_info.connection_id in ws_manager_instance.connection_registry
        assert ws_manager_instance._stats["total_connections"] == 1
        
        # Verify heartbeat task was started
        assert conn_info.connection_id in ws_manager_instance.heartbeat_tasks
        
        # Verify initial message was sent
        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "connection_established"
        assert call_args["connection_id"] == conn_info.connection_id
    
    async def test_connect_multiple_connections_same_user(self, ws_manager_instance):
        """Test multiple connections for the same user."""
        user_id = "test_user_2"
        websockets = []
        
        # Connect multiple times (up to limit)
        for i in range(WebSocketManager.MAX_CONNECTIONS_PER_USER):
            ws = AsyncMock()
            ws.client_state = WebSocketState.CONNECTED
            ws.send_json = AsyncMock()
            websockets.append(ws)
            await ws_manager_instance.connect(user_id, ws)
        
        assert len(ws_manager_instance.active_connections[user_id]) == WebSocketManager.MAX_CONNECTIONS_PER_USER
    
    async def test_connect_exceeds_connection_limit(self, ws_manager_instance):
        """Test that exceeding connection limit closes oldest connection."""
        user_id = "test_user_3"
        websockets = []
        
        # Fill up to connection limit
        for i in range(WebSocketManager.MAX_CONNECTIONS_PER_USER):
            ws = AsyncMock()
            ws.client_state = WebSocketState.CONNECTED
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            websockets.append(ws)
            await ws_manager_instance.connect(user_id, ws)
        
        # Add one more connection (should close the oldest)
        new_ws = AsyncMock()
        new_ws.client_state = WebSocketState.CONNECTED
        new_ws.send_json = AsyncMock()
        
        with patch('app.ws_manager.logger') as mock_logger:
            await ws_manager_instance.connect(user_id, new_ws)
            mock_logger.warning.assert_called()
        
        # Verify oldest was removed and new one added
        assert len(ws_manager_instance.active_connections[user_id]) == WebSocketManager.MAX_CONNECTIONS_PER_USER
        assert ws_manager_instance.active_connections[user_id][-1].websocket == new_ws
    
    async def test_disconnect_existing_connection(self, ws_manager_instance, mock_websocket):
        """Test disconnecting an existing connection."""
        user_id = "test_user_4"
        
        # Connect first
        conn_info = await ws_manager_instance.connect(user_id, mock_websocket)
        
        # Disconnect
        await ws_manager_instance.disconnect(user_id, mock_websocket)
        
        # Verify cleanup
        assert user_id not in ws_manager_instance.active_connections
        assert conn_info.connection_id not in ws_manager_instance.connection_registry
        assert conn_info.connection_id not in ws_manager_instance.heartbeat_tasks
        mock_websocket.close.assert_called_once()
    
    async def test_disconnect_nonexistent_user(self, ws_manager_instance, mock_websocket):
        """Test disconnecting a non-existent user."""
        # Should not raise any errors
        await ws_manager_instance.disconnect("nonexistent_user", mock_websocket)
    
    async def test_disconnect_with_close_error(self, ws_manager_instance, mock_websocket):
        """Test disconnect when closing WebSocket raises error."""
        user_id = "test_user_5"
        
        # Connect first
        await ws_manager_instance.connect(user_id, mock_websocket)
        
        # Make close raise an error
        mock_websocket.close.side_effect = Exception("Close failed")
        
        # Should handle error gracefully
        with patch('app.ws_manager.logger') as mock_logger:
            await ws_manager_instance.disconnect(user_id, mock_websocket)
            mock_logger.debug.assert_called()
    
    async def test_send_message_to_user(self, ws_manager_instance, mock_websocket):
        """Test sending a message to a user."""
        user_id = "test_user_6"
        
        # Connect user
        await ws_manager_instance.connect(user_id, mock_websocket)
        
        # Send message
        message = {"type": "test", "data": "hello"}
        result = await ws_manager_instance.send_message(user_id, message)
        
        assert result == True
        assert mock_websocket.send_json.call_count >= 2  # Initial + our message
        
        # Verify stats updated
        assert ws_manager_instance._stats["total_messages_sent"] > 0
    
    async def test_send_message_no_connections(self, ws_manager_instance):
        """Test sending message when user has no connections."""
        result = await ws_manager_instance.send_message("no_connections", {"test": "data"})
        assert result == False
    
    async def test_send_message_invalid_type(self, ws_manager_instance, mock_websocket):
        """Test sending invalid message type."""
        user_id = "test_user_7"
        await ws_manager_instance.connect(user_id, mock_websocket)
        
        with patch('app.ws_manager.logger') as mock_logger:
            result = await ws_manager_instance.send_message(user_id, "not a dict")
            assert result == False
            mock_logger.error.assert_called()
    
    async def test_send_message_adds_timestamp(self, ws_manager_instance, mock_websocket):
        """Test that send_message adds timestamp if missing."""
        user_id = "test_user_8"
        await ws_manager_instance.connect(user_id, mock_websocket)
        
        message = {"type": "test"}
        await ws_manager_instance.send_message(user_id, message)
        
        # Get the sent message
        sent_calls = mock_websocket.send_json.call_args_list
        sent_message = None
        for call in sent_calls:
            if call[0][0].get("type") == "test":
                sent_message = call[0][0]
                break
        
        assert sent_message != None
        assert "timestamp" in sent_message
    
    async def test_send_to_connection_retry_logic(self, ws_manager_instance):
        """Test retry logic when sending to connection."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.CONNECTED
        
        # First two attempts fail, third succeeds
        conn_info.websocket.send_json = AsyncMock(
            side_effect=[ConnectionError("Failed"), ConnectionError("Failed"), None]
        )
        
        with patch('app.ws_manager.logger'):
            result = await ws_manager_instance._send_to_connection(
                conn_info, {"test": "data"}, retry=True
            )
        
        assert result == True
        assert conn_info.websocket.send_json.call_count == 3
        assert conn_info.error_count == 2
    
    async def test_send_to_connection_all_retries_fail(self, ws_manager_instance):
        """Test when all retry attempts fail."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.CONNECTED
        conn_info.websocket.send_json = AsyncMock(side_effect=ConnectionError("Failed"))
        
        with patch('app.ws_manager.logger') as mock_logger:
            result = await ws_manager_instance._send_to_connection(
                conn_info, {"test": "data"}, retry=True
            )
        
        assert result == False
        assert conn_info.websocket.send_json.call_count == WebSocketManager.MAX_RETRY_ATTEMPTS
        mock_logger.error.assert_called()
    
    async def test_send_to_connection_closed_state(self, ws_manager_instance):
        """Test sending to connection in closed state."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.DISCONNECTED
        
        result = await ws_manager_instance._send_to_connection(
            conn_info, {"test": "data"}, retry=False
        )
        
        assert result == False
        conn_info.websocket.send_json.assert_not_called()
    
    async def test_send_to_connection_runtime_error_with_close(self, ws_manager_instance):
        """Test handling RuntimeError with 'close' in message."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.CONNECTED
        conn_info.websocket.send_json = AsyncMock(
            side_effect=RuntimeError("Connection closed")
        )
        
        with patch('app.ws_manager.logger'):
            result = await ws_manager_instance._send_to_connection(
                conn_info, {"test": "data"}, retry=False
            )
        
        assert result == False
    
    async def test_send_to_connection_unexpected_error(self, ws_manager_instance):
        """Test handling unexpected errors."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.CONNECTED
        conn_info.websocket.send_json = AsyncMock(
            side_effect=ValueError("Unexpected error")
        )
        
        with patch('app.ws_manager.logger') as mock_logger:
            result = await ws_manager_instance._send_to_connection(
                conn_info, {"test": "data"}, retry=False
            )
        
        assert result == False
        mock_logger.error.assert_called()
    
    async def test_send_system_message(self, ws_manager_instance):
        """Test sending system message."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.CONNECTED
        
        message = {"type": "system_test"}
        await ws_manager_instance._send_system_message(conn_info, message)
        
        conn_info.websocket.send_json.assert_called_once()
        sent_message = conn_info.websocket.send_json.call_args[0][0]
        assert sent_message["system"] == True
        assert sent_message["type"] == "system_test"
    
    async def test_is_connection_alive_connected(self, ws_manager_instance):
        """Test checking if connection is alive when connected."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.CONNECTED
        conn_info.last_ping = datetime.now(timezone.utc)
        
        assert ws_manager_instance._is_connection_alive(conn_info) == True
    
    async def test_is_connection_alive_disconnected(self, ws_manager_instance):
        """Test checking if connection is alive when disconnected."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.DISCONNECTED
        
        assert ws_manager_instance._is_connection_alive(conn_info) == False
    
    async def test_is_connection_alive_timeout(self, ws_manager_instance):
        """Test checking if connection is alive with heartbeat timeout."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.CONNECTED
        # Set last ping to exceed timeout
        conn_info.last_ping = datetime.now(timezone.utc) - timedelta(
            seconds=WebSocketManager.HEARTBEAT_TIMEOUT + 1
        )
        
        with patch('app.ws_manager.logger'):
            assert ws_manager_instance._is_connection_alive(conn_info) == False
    
    async def test_heartbeat_loop_normal(self, ws_manager_instance):
        """Test heartbeat loop normal operation."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.CONNECTED
        
        # Mock to run loop twice then disconnect
        call_count = 0
        def get_state():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return WebSocketState.CONNECTED
            return WebSocketState.DISCONNECTED
        
        conn_info.websocket.client_state = property(lambda self: get_state())
        
        with patch.object(ws_manager_instance, '_send_system_message', new_callable=AsyncMock):
            with patch.object(ws_manager_instance, '_is_connection_alive', return_value=True):
                with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                    await ws_manager_instance._heartbeat_loop(conn_info)
    
    async def test_heartbeat_loop_cancelled(self, ws_manager_instance):
        """Test heartbeat loop when cancelled."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.CONNECTED
        ws_manager_instance.connection_registry[conn_info.connection_id] = conn_info
        
        with patch.object(ws_manager_instance, '_send_system_message', side_effect=asyncio.CancelledError):
            with patch.object(ws_manager_instance, 'disconnect', new_callable=AsyncMock):
                with patch('app.ws_manager.logger'):
                    await ws_manager_instance._heartbeat_loop(conn_info)
    
    async def test_heartbeat_loop_error(self, ws_manager_instance):
        """Test heartbeat loop with error."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.CONNECTED
        ws_manager_instance.connection_registry[conn_info.connection_id] = conn_info
        
        with patch.object(ws_manager_instance, '_send_system_message', side_effect=Exception("Test error")):
            with patch.object(ws_manager_instance, 'disconnect', new_callable=AsyncMock):
                with patch('app.ws_manager.logger') as mock_logger:
                    await ws_manager_instance._heartbeat_loop(conn_info)
                    mock_logger.error.assert_called()
    
    async def test_heartbeat_loop_connection_fails_check(self, ws_manager_instance):
        """Test heartbeat loop when connection fails alive check."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.CONNECTED
        
        with patch.object(ws_manager_instance, '_send_system_message', new_callable=AsyncMock):
            with patch.object(ws_manager_instance, '_is_connection_alive', return_value=False):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    with patch('app.ws_manager.logger'):
                        await ws_manager_instance._heartbeat_loop(conn_info)
    
    async def test_handle_pong(self, ws_manager_instance, mock_websocket):
        """Test handling pong response."""
        user_id = "test_user_9"
        
        # Connect user
        conn_info = await ws_manager_instance.connect(user_id, mock_websocket)
        
        # Handle pong
        await ws_manager_instance.handle_pong(user_id, mock_websocket)
        
        # Verify pong was recorded
        assert conn_info.last_pong != None
    
    async def test_handle_pong_no_connection(self, ws_manager_instance, mock_websocket):
        """Test handling pong for non-existent connection."""
        # Should not raise error
        await ws_manager_instance.handle_pong("no_user", mock_websocket)
    
    async def test_send_error(self, ws_manager_instance, mock_websocket):
        """Test sending error message."""
        user_id = "test_user_10"
        await ws_manager_instance.connect(user_id, mock_websocket)
        
        await ws_manager_instance.send_error(user_id, "Test error", "TestAgent")
        
        # Check that error message was sent
        calls = mock_websocket.send_json.call_args_list
        error_sent = False
        for call in calls:
            msg = call[0][0]
            if msg.get("type") == "error":
                assert msg["payload"]["error"] == "Test error"
                assert msg["payload"]["sub_agent_name"] == "TestAgent"
                assert msg["displayed_to_user"] == True
                error_sent = True
                break
        assert error_sent
    
    async def test_send_agent_log(self, ws_manager_instance, mock_websocket):
        """Test sending agent log message."""
        user_id = "test_user_11"
        await ws_manager_instance.connect(user_id, mock_websocket)
        
        await ws_manager_instance.send_agent_log(user_id, "INFO", "Test log", "TestAgent")
        
        # Check that log message was sent
        calls = mock_websocket.send_json.call_args_list
        log_sent = False
        for call in calls:
            msg = call[0][0]
            if msg.get("type") == "agent_log":
                assert msg["payload"]["level"] == "INFO"
                assert msg["payload"]["message"] == "Test log"
                assert msg["payload"]["sub_agent_name"] == "TestAgent"
                assert "timestamp" in msg["payload"]
                assert msg["displayed_to_user"] == True
                log_sent = True
                break
        assert log_sent
    
    async def test_send_tool_call(self, ws_manager_instance, mock_websocket):
        """Test sending tool call message."""
        user_id = "test_user_12"
        await ws_manager_instance.connect(user_id, mock_websocket)
        
        tool_args = {"arg1": "value1", "arg2": "value2"}
        await ws_manager_instance.send_tool_call(user_id, "TestTool", tool_args, "TestAgent")
        
        # Check that tool call message was sent
        calls = mock_websocket.send_json.call_args_list
        tool_sent = False
        for call in calls:
            msg = call[0][0]
            if msg.get("type") == "tool_call":
                assert msg["payload"]["tool_name"] == "TestTool"
                assert msg["payload"]["tool_args"] == tool_args
                assert msg["payload"]["sub_agent_name"] == "TestAgent"
                assert "timestamp" in msg["payload"]
                assert msg["displayed_to_user"] == True
                tool_sent = True
                break
        assert tool_sent
    
    async def test_send_tool_result(self, ws_manager_instance, mock_websocket):
        """Test sending tool result message."""
        user_id = "test_user_13"
        await ws_manager_instance.connect(user_id, mock_websocket)
        
        result = {"output": "Success", "data": [1, 2, 3]}
        await ws_manager_instance.send_tool_result(user_id, "TestTool", result, "TestAgent")
        
        # Check that tool result message was sent
        calls = mock_websocket.send_json.call_args_list
        result_sent = False
        for call in calls:
            msg = call[0][0]
            if msg.get("type") == "tool_result":
                assert msg["payload"]["tool_name"] == "TestTool"
                assert msg["payload"]["result"] == result
                assert msg["payload"]["sub_agent_name"] == "TestAgent"
                assert "timestamp" in msg["payload"]
                assert msg["displayed_to_user"] == True
                result_sent = True
                break
        assert result_sent
    
    async def test_broadcast_success(self, ws_manager_instance):
        """Test broadcasting message to all users."""
        # Connect multiple users
        users = ["user1", "user2", "user3"]
        for user_id in users:
            ws = AsyncMock()
            ws.client_state = WebSocketState.CONNECTED
            ws.send_json = AsyncMock()
            await ws_manager_instance.connect(user_id, ws)
        
        # Broadcast message
        message = {"type": "broadcast", "data": "Hello all"}
        result = await ws_manager_instance.broadcast(message)
        
        assert result["successful"] == 3
        assert result["failed"] == 0
        assert ws_manager_instance._stats["total_messages_sent"] >= 3
    
    async def test_broadcast_with_failures(self, ws_manager_instance):
        """Test broadcasting with some failed connections."""
        # Connect users with mixed states
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws1.send_json = AsyncMock()
        await ws_manager_instance.connect("user1", ws1)
        
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.DISCONNECTED
        ws2.send_json = AsyncMock()
        await ws_manager_instance.connect("user2", ws2)
        
        ws3 = AsyncMock()
        ws3.client_state = WebSocketState.CONNECTED
        ws3.send_json = AsyncMock(side_effect=ConnectionError("Failed"))
        await ws_manager_instance.connect("user3", ws3)
        
        with patch('app.ws_manager.logger'):
            result = await ws_manager_instance.broadcast({"type": "test"})
        
        assert result["successful"] == 1
        assert result["failed"] == 2
    
    async def test_broadcast_unexpected_error(self, ws_manager_instance):
        """Test broadcast handling unexpected errors."""
        ws = AsyncMock()
        ws.client_state = WebSocketState.CONNECTED
        ws.send_json = AsyncMock(side_effect=ValueError("Unexpected"))
        await ws_manager_instance.connect("user1", ws)
        
        with patch('app.ws_manager.logger') as mock_logger:
            result = await ws_manager_instance.broadcast({"type": "test"})
            mock_logger.error.assert_called()
        
        assert result["failed"] == 1
    
    async def test_broadcast_adds_timestamp(self, ws_manager_instance):
        """Test that broadcast adds timestamp if missing."""
        ws = AsyncMock()
        ws.client_state = WebSocketState.CONNECTED
        ws.send_json = AsyncMock()
        await ws_manager_instance.connect("user1", ws)
        
        message = {"type": "test"}
        await ws_manager_instance.broadcast(message)
        
        sent_message = ws.send_json.call_args_list[-1][0][0]
        assert "timestamp" in sent_message
    
    async def test_shutdown(self, ws_manager_instance):
        """Test graceful shutdown."""
        # Connect multiple users
        users = ["user1", "user2"]
        for user_id in users:
            ws = AsyncMock()
            ws.client_state = WebSocketState.CONNECTED
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            await ws_manager_instance.connect(user_id, ws)
        
        # Perform shutdown
        with patch('app.ws_manager.logger'):
            await ws_manager_instance.shutdown()
        
        # Verify cleanup
        assert len(ws_manager_instance.active_connections) == 0
        assert len(ws_manager_instance.connection_registry) == 0
        assert len(ws_manager_instance.heartbeat_tasks) == 0
    
    async def test_shutdown_with_close_errors(self, ws_manager_instance):
        """Test shutdown when closing connections raises errors."""
        ws = AsyncMock()
        ws.client_state = WebSocketState.CONNECTED
        ws.send_json = AsyncMock()
        ws.close = AsyncMock(side_effect=Exception("Close failed"))
        await ws_manager_instance.connect("user1", ws)
        
        with patch('app.ws_manager.logger'):
            await ws_manager_instance.shutdown()
        
        # Should still complete cleanup
        assert len(ws_manager_instance.active_connections) == 0
    
    async def test_get_stats(self, ws_manager_instance):
        """Test getting statistics."""
        # Connect some users
        await ws_manager_instance.connect("user1", AsyncMock())
        await ws_manager_instance.connect("user2", AsyncMock())
        await ws_manager_instance.connect("user2", AsyncMock())  # Second connection for user2
        
        stats = ws_manager_instance.get_stats()
        
        assert stats["total_connections"] == 3
        assert stats["active_connections"] == 3
        assert stats["active_users"] == 2
        assert stats["connections_by_user"]["user1"] == 1
        assert stats["connections_by_user"]["user2"] == 2
    
    async def test_get_connection_info(self, ws_manager_instance, mock_websocket):
        """Test getting connection info for a user."""
        user_id = "test_user_14"
        
        # Connect user
        await ws_manager_instance.connect(user_id, mock_websocket)
        
        # Get connection info
        info = ws_manager_instance.get_connection_info(user_id)
        
        assert len(info) == 1
        assert "connection_id" in info[0]
        assert "connected_at" in info[0]
        assert "last_ping" in info[0]
        assert "last_pong" in info[0]
        assert info[0]["message_count"] == 0
        assert info[0]["error_count"] == 0
        assert info[0]["is_alive"] == True
    
    async def test_get_connection_info_no_user(self, ws_manager_instance):
        """Test getting connection info for non-existent user."""
        info = ws_manager_instance.get_connection_info("no_user")
        assert info == []
    
    async def test_connection_info_dataclass(self):
        """Test ConnectionInfo dataclass initialization."""
        ws = Mock()
        conn_info = ConnectionInfo(websocket=ws, user_id="test_user")
        
        assert conn_info.websocket == ws
        assert conn_info.user_id == "test_user"
        assert conn_info.message_count == 0
        assert conn_info.error_count == 0
        assert conn_info.last_pong == None
        assert isinstance(conn_info.connected_at, datetime)
        assert isinstance(conn_info.last_ping, datetime)
        assert conn_info.connection_id.startswith("conn_")
    
    async def test_remove_dead_connections_during_send(self, ws_manager_instance):
        """Test that dead connections are removed during send_message."""
        user_id = "test_user_15"
        
        # Create two connections, one alive and one dead
        ws_alive = AsyncMock()
        ws_alive.client_state = WebSocketState.CONNECTED
        ws_alive.send_json = AsyncMock()
        
        ws_dead = AsyncMock()
        ws_dead.client_state = WebSocketState.CONNECTED  # Start as connected
        ws_dead.send_json = AsyncMock(side_effect=RuntimeError("Connection closed"))
        ws_dead.close = AsyncMock()
        
        await ws_manager_instance.connect(user_id, ws_alive)
        conn_dead = await ws_manager_instance.connect(user_id, ws_dead)
        
        # Now make the dead connection appear disconnected
        ws_dead.client_state = WebSocketState.DISCONNECTED
        
        # Send message - should detect and remove dead connection
        result = await ws_manager_instance.send_message(user_id, {"type": "test"})
        
        # Verify message was sent successfully to alive connection
        assert result == True
        
        # Verify dead connection was removed
        assert len(ws_manager_instance.active_connections[user_id]) == 1
        assert ws_manager_instance.active_connections[user_id][0].websocket == ws_alive
    
    async def test_send_message_removes_dead_connections(self, ws_manager_instance):
        """Test that send_message removes connections that fail alive check."""
        user_id = "test_user_16"
        
        # Create two connections
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws1.send_json = AsyncMock()
        ws1.close = AsyncMock()
        
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED
        ws2.send_json = AsyncMock()
        ws2.close = AsyncMock()
        
        conn1 = await ws_manager_instance.connect(user_id, ws1)
        conn2 = await ws_manager_instance.connect(user_id, ws2)
        
        # Store original connections for comparison
        original_conns = ws_manager_instance.active_connections[user_id].copy()
        
        # Mock _send_to_connection to return success for first, failure for second
        # Mock _is_connection_alive to return False for the second connection
        async def mock_send_to_connection(conn_info, message, retry):
            if conn_info == original_conns[0]:
                return True
            else:
                return False
        
        def mock_is_alive(conn_info):
            if conn_info == original_conns[0]:
                return True
            else:
                return False
        
        with patch.object(ws_manager_instance, '_send_to_connection', side_effect=mock_send_to_connection):
            with patch.object(ws_manager_instance, '_is_connection_alive', side_effect=mock_is_alive):
                result = await ws_manager_instance.send_message(user_id, {"type": "test"})
        
        # Should have succeeded overall (first connection worked)
        assert result == True
        
        # Second connection should have been removed
        assert len(ws_manager_instance.active_connections[user_id]) == 1
        assert ws_manager_instance.active_connections[user_id][0] == conn1
    
    async def test_send_to_connection_exhausts_retries(self, ws_manager_instance):
        """Test that _send_to_connection returns False after exhausting all retries."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        conn_info.websocket.client_state = WebSocketState.CONNECTED
        
        # Make all attempts fail with ConnectionError
        conn_info.websocket.send_json = AsyncMock(
            side_effect=ConnectionError("Connection failed")
        )
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('app.ws_manager.logger'):
                result = await ws_manager_instance._send_to_connection(
                    conn_info, {"test": "data"}, retry=True
                )
        
        # Should return False after all retries fail
        assert result == False
        assert conn_info.websocket.send_json.call_count == WebSocketManager.MAX_RETRY_ATTEMPTS
    
    async def test_send_to_connection_no_retry_false(self, ws_manager_instance):
        """Test that _send_to_connection returns False immediately with retry=False."""
        conn_info = ConnectionInfo(
            websocket=AsyncMock(),
            user_id="test_user",
            connection_id="test_conn"
        )
        # Set websocket to disconnected state
        conn_info.websocket.client_state = WebSocketState.DISCONNECTED
        
        # Since state is DISCONNECTED, it should return False before trying to send
        result = await ws_manager_instance._send_to_connection(
            conn_info, {"test": "data"}, retry=False
        )
        
        assert result == False
        conn_info.websocket.send_json.assert_not_called()
    
    async def test_threading_lock(self):
        """Test that singleton uses threading lock correctly."""
        import threading
        
        results = []
        
        def create_manager():
            mgr = WebSocketManager()
            results.append(mgr)
        
        # Create multiple threads trying to create manager
        threads = []
        for _ in range(10):
            t = threading.Thread(target=create_manager)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All should be the same instance
        assert all(mgr is results[0] for mgr in results)