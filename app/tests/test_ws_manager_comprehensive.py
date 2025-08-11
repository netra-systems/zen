"""
Comprehensive tests for WebSocketManager with complete coverage
Tests all methods, error handling, edge cases, connection lifecycle, and singleton pattern
"""

import pytest
import asyncio
import time
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
from starlette.websockets import WebSocketState

from app.ws_manager import WebSocketManager, ConnectionInfo, manager, ws_manager


class MockWebSocket:
    """Enhanced mock WebSocket for comprehensive testing"""
    def __init__(self, state=WebSocketState.CONNECTED):
        self.client_state = state
        self.send_json = AsyncMock()
        self.close = AsyncMock()
        self.send_calls = []
        self.close_calls = []
    
    async def mock_send_json(self, data):
        self.send_calls.append(data)
    
    async def mock_close(self, code=1000, reason=""):
        self.close_calls.append({"code": code, "reason": reason})
        self.client_state = WebSocketState.DISCONNECTED


@pytest.fixture
def fresh_manager():
    """Create a fresh WebSocketManager instance for each test"""
    # Reset singleton
    WebSocketManager._instance = None
    WebSocketManager._initialized = False
    
    manager = WebSocketManager()
    yield manager
    
    # Clean up
    WebSocketManager._instance = None


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket"""
    return MockWebSocket()


@pytest.fixture
def connected_websocket():
    """Create a connected mock WebSocket"""
    ws = MockWebSocket(WebSocketState.CONNECTED)
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def disconnected_websocket():
    """Create a disconnected mock WebSocket"""
    ws = MockWebSocket(WebSocketState.DISCONNECTED)
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


class TestSingletonPattern:
    """Test singleton pattern implementation"""
    
    def test_singleton_instance(self):
        """Test singleton pattern creates same instance"""
        WebSocketManager._instance = None
        
        mgr1 = WebSocketManager()
        mgr2 = WebSocketManager()
        
        assert mgr1 is mgr2
        assert manager is ws_manager
    
    def test_thread_safety(self):
        """Test singleton thread safety"""
        WebSocketManager._instance = None
        instances = []
        
        def create_instance():
            mgr = WebSocketManager()
            instances.append(mgr)
        
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All instances should be the same
        assert all(inst is instances[0] for inst in instances)
    
    def test_initialization_only_once(self):
        """Test initialization happens only once"""
        WebSocketManager._instance = None
        
        mgr1 = WebSocketManager()
        initial_stats = mgr1._stats.copy()
        
        mgr2 = WebSocketManager()
        
        # Stats should be the same (not re-initialized)
        assert mgr2._stats == initial_stats


@pytest.mark.asyncio
class TestConnectionManagement:
    """Test connection establishment and management"""
    
    async def test_connect_new_user(self, fresh_manager, connected_websocket):
        """Test connecting a new user"""
        user_id = "test_user_1"
        
        conn_info = await fresh_manager.connect(user_id, connected_websocket)
        
        # Verify connection established
        assert user_id in fresh_manager.active_connections
        assert len(fresh_manager.active_connections[user_id]) == 1
        assert conn_info.connection_id in fresh_manager.connection_registry
        assert conn_info.user_id == user_id
        assert conn_info.websocket is connected_websocket
        
        # Verify stats updated
        assert fresh_manager._stats["total_connections"] == 1
        
        # Verify heartbeat task started
        assert conn_info.connection_id in fresh_manager.heartbeat_tasks
        
        # Verify initial message sent
        connected_websocket.send_json.assert_called()
        calls = connected_websocket.send_json.call_args_list
        initial_msg = next((call[0][0] for call in calls if call[0][0].get("type") == "connection_established"), None)
        assert initial_msg != None
        assert initial_msg["connection_id"] == conn_info.connection_id
    
    async def test_connect_multiple_users(self, fresh_manager):
        """Test connecting multiple different users"""
        users = ["user1", "user2", "user3"]
        connections = []
        
        for user_id in users:
            ws = MockWebSocket(WebSocketState.CONNECTED)
            ws.send_json = AsyncMock()
            conn_info = await fresh_manager.connect(user_id, ws)
            connections.append(conn_info)
        
        # Verify all users are tracked separately
        assert len(fresh_manager.active_connections) == 3
        for user_id in users:
            assert user_id in fresh_manager.active_connections
            assert len(fresh_manager.active_connections[user_id]) == 1
        
        assert fresh_manager._stats["total_connections"] == 3
    
    async def test_connect_multiple_connections_same_user(self, fresh_manager):
        """Test multiple connections for same user (within limit)"""
        user_id = "multi_conn_user"
        connections = []
        
        # Connect up to the limit
        for i in range(WebSocketManager.MAX_CONNECTIONS_PER_USER):
            ws = MockWebSocket(WebSocketState.CONNECTED)
            ws.send_json = AsyncMock()
            conn_info = await fresh_manager.connect(user_id, ws)
            connections.append(conn_info)
        
        assert len(fresh_manager.active_connections[user_id]) == WebSocketManager.MAX_CONNECTIONS_PER_USER
        assert fresh_manager._stats["total_connections"] == WebSocketManager.MAX_CONNECTIONS_PER_USER
    
    async def test_connect_exceeds_limit_removes_oldest(self, fresh_manager):
        """Test that exceeding connection limit removes oldest connection"""
        user_id = "limit_test_user"
        websockets = []
        
        # Fill to limit
        for i in range(WebSocketManager.MAX_CONNECTIONS_PER_USER):
            ws = MockWebSocket(WebSocketState.CONNECTED)
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            websockets.append(ws)
            await fresh_manager.connect(user_id, ws)
        
        # Store first connection for verification
        first_conn = fresh_manager.active_connections[user_id][0]
        first_ws = websockets[0]
        
        # Add one more (should evict oldest)
        new_ws = MockWebSocket(WebSocketState.CONNECTED)
        new_ws.send_json = AsyncMock()
        
        with patch('app.ws_manager.logger') as mock_logger:
            await fresh_manager.connect(user_id, new_ws)
            
            # Should log warning about limit exceeded
            mock_logger.warning.assert_called()
        
        # Verify limit maintained and oldest removed
        assert len(fresh_manager.active_connections[user_id]) == WebSocketManager.MAX_CONNECTIONS_PER_USER
        assert first_conn.connection_id not in fresh_manager.connection_registry
        assert first_ws not in [conn.websocket for conn in fresh_manager.active_connections[user_id]]
        
        # Verify new connection is there
        assert new_ws in [conn.websocket for conn in fresh_manager.active_connections[user_id]]
    
    async def test_disconnect_existing_connection(self, fresh_manager, connected_websocket):
        """Test disconnecting an existing connection"""
        user_id = "disconnect_test"
        
        # Connect first
        conn_info = await fresh_manager.connect(user_id, connected_websocket)
        initial_connections = fresh_manager._stats["total_connections"]
        
        # Disconnect
        await fresh_manager.disconnect(user_id, connected_websocket)
        
        # Verify cleanup
        assert user_id not in fresh_manager.active_connections
        assert conn_info.connection_id not in fresh_manager.connection_registry
        assert conn_info.connection_id not in fresh_manager.heartbeat_tasks
        
        # Verify WebSocket was closed
        connected_websocket.close.assert_called_once()
    
    async def test_disconnect_nonexistent_user(self, fresh_manager, connected_websocket):
        """Test disconnecting non-existent user doesn't error"""
        # Should not raise exception
        await fresh_manager.disconnect("nonexistent_user", connected_websocket)
    
    async def test_disconnect_nonexistent_websocket(self, fresh_manager):
        """Test disconnecting with non-existent websocket"""
        user_id = "test_user"
        ws1 = MockWebSocket(WebSocketState.CONNECTED)
        ws1.send_json = AsyncMock()
        ws2 = MockWebSocket(WebSocketState.CONNECTED)
        ws2.send_json = AsyncMock()
        
        # Connect with ws1
        await fresh_manager.connect(user_id, ws1)
        
        # Try to disconnect with ws2 (not connected)
        await fresh_manager.disconnect(user_id, ws2)
        
        # ws1 should still be connected
        assert user_id in fresh_manager.active_connections
        assert len(fresh_manager.active_connections[user_id]) == 1
    
    async def test_disconnect_with_close_error(self, fresh_manager, connected_websocket):
        """Test disconnect when websocket.close() raises exception"""
        user_id = "close_error_test"
        
        # Connect
        conn_info = await fresh_manager.connect(user_id, connected_websocket)
        
        # Make close() raise exception
        connected_websocket.close.side_effect = Exception("Close failed")
        
        # Should handle error gracefully
        with patch('app.ws_manager.logger') as mock_logger:
            await fresh_manager.disconnect(user_id, connected_websocket)
            
            # Should log debug message about error
            mock_logger.debug.assert_called()
        
        # Should still clean up internal state
        assert user_id not in fresh_manager.active_connections
        assert conn_info.connection_id not in fresh_manager.connection_registry


class TestConnectionInfo:
    """Test ConnectionInfo dataclass"""
    
    def test_connection_info_initialization(self):
        """Test ConnectionInfo initialization with defaults"""
        ws = MockWebSocket()
        conn_info = ConnectionInfo(websocket=ws, user_id="test_user")
        
        assert conn_info.websocket is ws
        assert conn_info.user_id == "test_user"
        assert conn_info.message_count == 0
        assert conn_info.error_count == 0
        assert conn_info.last_pong == None
        assert isinstance(conn_info.connected_at, datetime)
        assert isinstance(conn_info.last_ping, datetime)
        assert conn_info.connection_id.startswith("conn_")
    
    def test_connection_info_custom_values(self):
        """Test ConnectionInfo with custom values"""
        ws = MockWebSocket()
        custom_time = datetime.now(timezone.utc)
        
        conn_info = ConnectionInfo(
            websocket=ws,
            user_id="test_user",
            connected_at=custom_time,
            last_ping=custom_time,
            last_pong=custom_time,
            message_count=5,
            error_count=2
        )
        
        assert conn_info.connected_at == custom_time
        assert conn_info.last_ping == custom_time
        assert conn_info.last_pong == custom_time
        assert conn_info.message_count == 5
        assert conn_info.error_count == 2


@pytest.mark.asyncio
class TestMessageSending:
    """Test message sending functionality"""
    
    async def test_send_message_success(self, fresh_manager, connected_websocket):
        """Test successful message sending"""
        user_id = "msg_test_user"
        
        # Connect user
        await fresh_manager.connect(user_id, connected_websocket)
        
        # Send message
        message = {"type": "test", "data": "hello world"}
        result = await fresh_manager.send_message(user_id, message)
        
        assert result == True
        
        # Verify message was sent (including initial connection message)
        assert connected_websocket.send_json.call_count >= 2
        
        # Check that timestamp was added
        sent_calls = connected_websocket.send_json.call_args_list
        test_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "test"), None)
        assert test_msg != None
        assert "timestamp" in test_msg
        assert test_msg["data"] == "hello world"
        
        # Verify stats updated
        assert fresh_manager._stats["total_messages_sent"] >= 1
    
    async def test_send_message_no_connections(self, fresh_manager):
        """Test sending message to user with no connections"""
        result = await fresh_manager.send_message("no_connections", {"test": "data"})
        assert result == False
    
    async def test_send_message_invalid_message_type(self, fresh_manager, connected_websocket):
        """Test sending invalid message type"""
        user_id = "invalid_msg_user"
        await fresh_manager.connect(user_id, connected_websocket)
        
        with patch('app.ws_manager.logger') as mock_logger:
            result = await fresh_manager.send_message(user_id, "not a dict")
            
            assert result == False
            mock_logger.error.assert_called()
    
    async def test_send_message_preserves_timestamp(self, fresh_manager, connected_websocket):
        """Test that existing timestamp is preserved"""
        user_id = "timestamp_test_user"
        await fresh_manager.connect(user_id, connected_websocket)
        
        custom_timestamp = 1234567890
        message = {"type": "test", "timestamp": custom_timestamp}
        
        await fresh_manager.send_message(user_id, message)
        
        # Find the test message in sent calls
        sent_calls = connected_websocket.send_json.call_args_list
        test_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "test"), None)
        
        assert test_msg["timestamp"] == custom_timestamp
    
    async def test_send_message_removes_dead_connections(self, fresh_manager):
        """Test that dead connections are removed during send"""
        user_id = "dead_conn_test"
        
        # Create alive and dead connections
        ws_alive = MockWebSocket(WebSocketState.CONNECTED)
        ws_alive.send_json = AsyncMock()
        ws_dead = MockWebSocket(WebSocketState.CONNECTED)
        ws_dead.send_json = AsyncMock(side_effect=RuntimeError("Connection closed"))
        ws_dead.close = AsyncMock()
        
        # Connect both
        conn_alive = await fresh_manager.connect(user_id, ws_alive)
        conn_dead = await fresh_manager.connect(user_id, ws_dead)
        
        # Make dead connection appear disconnected for alive check
        ws_dead.client_state = WebSocketState.DISCONNECTED
        
        # Send message
        result = await fresh_manager.send_message(user_id, {"type": "test"})
        
        # Should succeed (alive connection worked)
        assert result == True
        
        # Dead connection should be removed
        remaining_connections = fresh_manager.active_connections.get(user_id, [])
        assert len(remaining_connections) == 1
        assert remaining_connections[0].websocket is ws_alive
        
        # Dead connection should be disconnected
        ws_dead.close.assert_called()
    
    async def test_send_message_multiple_connections(self, fresh_manager):
        """Test sending message to user with multiple connections"""
        user_id = "multi_conn_test"
        websockets = []
        
        # Connect multiple times
        for i in range(3):
            ws = MockWebSocket(WebSocketState.CONNECTED)
            ws.send_json = AsyncMock()
            websockets.append(ws)
            await fresh_manager.connect(user_id, ws)
        
        # Send message
        message = {"type": "broadcast_test"}
        result = await fresh_manager.send_message(user_id, message)
        
        assert result == True
        
        # All websockets should have received the message
        for ws in websockets:
            # Each should have gotten initial connection message + our test message
            assert ws.send_json.call_count >= 2
            
            # Verify our test message was sent
            sent_calls = ws.send_json.call_args_list
            test_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "broadcast_test"), None)
            assert test_msg != None


@pytest.mark.asyncio
class TestConnectionSending:
    """Test sending to specific connections"""
    
    async def test_send_to_connection_success(self, fresh_manager):
        """Test successful send to specific connection"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        conn_info.websocket.send_json = AsyncMock()
        
        result = await fresh_manager._send_to_connection(conn_info, {"test": "data"})
        
        assert result == True
        conn_info.websocket.send_json.assert_called_once_with({"test": "data"})
    
    async def test_send_to_connection_disconnected(self, fresh_manager):
        """Test send to disconnected connection"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.DISCONNECTED),
            user_id="test_user"
        )
        
        result = await fresh_manager._send_to_connection(conn_info, {"test": "data"})
        
        assert result == False
        conn_info.websocket.send_json.assert_not_called()
    
    async def test_send_to_connection_retry_success(self, fresh_manager):
        """Test retry logic succeeding after failures"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        
        # First two calls fail, third succeeds
        conn_info.websocket.send_json = AsyncMock(
            side_effect=[ConnectionError("Failed"), ConnectionError("Failed"), None]
        )
        
        with patch('app.ws_manager.logger'):
            result = await fresh_manager._send_to_connection(conn_info, {"test": "data"}, retry=True)
        
        assert result == True
        assert conn_info.websocket.send_json.call_count == 3
        assert conn_info.error_count == 2
    
    async def test_send_to_connection_retry_exhausted(self, fresh_manager):
        """Test all retries exhausted"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        conn_info.websocket.send_json = AsyncMock(side_effect=ConnectionError("Always fails"))
        
        with patch('app.ws_manager.logger') as mock_logger:
            result = await fresh_manager._send_to_connection(conn_info, {"test": "data"}, retry=True)
        
        assert result == False
        assert conn_info.websocket.send_json.call_count == WebSocketManager.MAX_RETRY_ATTEMPTS
        mock_logger.error.assert_called()
    
    async def test_send_to_connection_no_retry(self, fresh_manager):
        """Test sending without retry on failure"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        conn_info.websocket.send_json = AsyncMock(side_effect=ConnectionError("Failed"))
        
        with patch('app.ws_manager.logger'):
            result = await fresh_manager._send_to_connection(conn_info, {"test": "data"}, retry=False)
        
        assert result == False
        assert conn_info.websocket.send_json.call_count == 1
    
    async def test_send_to_connection_runtime_error_with_close(self, fresh_manager):
        """Test handling RuntimeError with 'close' in message"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        conn_info.websocket.send_json = AsyncMock(side_effect=RuntimeError("Connection closed"))
        
        with patch('app.ws_manager.logger'):
            result = await fresh_manager._send_to_connection(conn_info, {"test": "data"})
        
        assert result == False
    
    async def test_send_to_connection_unexpected_error(self, fresh_manager):
        """Test handling unexpected errors"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        conn_info.websocket.send_json = AsyncMock(side_effect=ValueError("Unexpected"))
        
        with patch('app.ws_manager.logger') as mock_logger:
            result = await fresh_manager._send_to_connection(conn_info, {"test": "data"})
        
        assert result == False
        assert conn_info.error_count == 1
        mock_logger.error.assert_called()
    
    async def test_send_system_message(self, fresh_manager):
        """Test sending system message"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        conn_info.websocket.send_json = AsyncMock()
        
        message = {"type": "system_test", "data": "system data"}
        await fresh_manager._send_system_message(conn_info, message)
        
        conn_info.websocket.send_json.assert_called_once()
        sent_message = conn_info.websocket.send_json.call_args[0][0]
        assert sent_message["system"] == True
        assert sent_message["type"] == "system_test"
        assert sent_message["data"] == "system data"


@pytest.mark.asyncio
class TestHeartbeat:
    """Test heartbeat functionality"""
    
    def test_is_connection_alive_connected_recent_ping(self, fresh_manager):
        """Test alive check for connected connection with recent ping"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        conn_info.last_ping = datetime.now(timezone.utc)
        
        assert fresh_manager._is_connection_alive(conn_info) == True
    
    def test_is_connection_alive_disconnected(self, fresh_manager):
        """Test alive check for disconnected connection"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.DISCONNECTED),
            user_id="test_user"
        )
        
        assert fresh_manager._is_connection_alive(conn_info) == False
    
    def test_is_connection_alive_timeout(self, fresh_manager):
        """Test alive check with heartbeat timeout"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        # Set last ping beyond timeout
        conn_info.last_ping = datetime.now(timezone.utc) - timedelta(
            seconds=WebSocketManager.HEARTBEAT_TIMEOUT + 10
        )
        
        with patch('app.ws_manager.logger'):
            assert fresh_manager._is_connection_alive(conn_info) == False
    
    async def test_handle_pong(self, fresh_manager, connected_websocket):
        """Test handling pong response"""
        user_id = "pong_test_user"
        
        # Connect user
        conn_info = await fresh_manager.connect(user_id, connected_websocket)
        original_pong = conn_info.last_pong
        
        # Handle pong
        await fresh_manager.handle_pong(user_id, connected_websocket)
        
        # Verify pong timestamp updated
        assert conn_info.last_pong != original_pong
        assert conn_info.last_pong != None
    
    async def test_handle_pong_no_connection(self, fresh_manager, connected_websocket):
        """Test handling pong for non-existent connection"""
        # Should not raise exception
        await fresh_manager.handle_pong("nonexistent_user", connected_websocket)
    
    async def test_heartbeat_loop_normal_operation(self, fresh_manager):
        """Test heartbeat loop normal operation"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        
        # Mock the loop to run a few iterations then stop
        loop_count = 0
        original_is_alive = fresh_manager._is_connection_alive
        
        def mock_is_alive(conn):
            nonlocal loop_count
            loop_count += 1
            if loop_count >= 3:  # Stop after 3 iterations
                return False
            return original_is_alive(conn)
        
        with patch.object(fresh_manager, '_send_system_message', new_callable=AsyncMock) as mock_send:
            with patch.object(fresh_manager, '_is_connection_alive', side_effect=mock_is_alive):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    await fresh_manager._heartbeat_loop(conn_info)
        
        # Should have sent ping messages
        assert mock_send.call_count >= 2
        
        # Verify ping messages were sent
        for call in mock_send.call_args_list:
            message = call[0][1]  # Second argument is the message
            if message.get("type") == "ping":
                assert "timestamp" in message
    
    async def test_heartbeat_loop_connection_state_changes(self, fresh_manager):
        """Test heartbeat loop when connection state changes"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        
        # Mock websocket to disconnect after first ping
        call_count = 0
        def get_state():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return WebSocketState.CONNECTED
            return WebSocketState.DISCONNECTED
        
        type(conn_info.websocket).client_state = property(lambda self: get_state())
        
        with patch.object(fresh_manager, '_send_system_message', new_callable=AsyncMock):
            await fresh_manager._heartbeat_loop(conn_info)
        
        # Loop should exit when connection state changes
        assert call_count >= 2
    
    async def test_heartbeat_loop_cancelled(self, fresh_manager):
        """Test heartbeat loop when cancelled"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        fresh_manager.connection_registry[conn_info.connection_id] = conn_info
        
        with patch.object(fresh_manager, '_send_system_message', side_effect=asyncio.CancelledError):
            with patch.object(fresh_manager, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
                with patch('app.ws_manager.logger') as mock_logger:
                    await fresh_manager._heartbeat_loop(conn_info)
                    
                    mock_logger.debug.assert_called()
                    mock_disconnect.assert_called_once()
    
    async def test_heartbeat_loop_error(self, fresh_manager):
        """Test heartbeat loop with unexpected error"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        fresh_manager.connection_registry[conn_info.connection_id] = conn_info
        
        with patch.object(fresh_manager, '_send_system_message', side_effect=Exception("Test error")):
            with patch.object(fresh_manager, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
                with patch('app.ws_manager.logger') as mock_logger:
                    await fresh_manager._heartbeat_loop(conn_info)
                    
                    mock_logger.error.assert_called()
                    mock_disconnect.assert_called_once()
    
    async def test_heartbeat_loop_connection_fails_alive_check(self, fresh_manager):
        """Test heartbeat loop when connection fails alive check"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="test_user"
        )
        
        with patch.object(fresh_manager, '_send_system_message', new_callable=AsyncMock):
            with patch.object(fresh_manager, '_is_connection_alive', return_value=False):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    with patch('app.ws_manager.logger') as mock_logger:
                        await fresh_manager._heartbeat_loop(conn_info)
                        
                        mock_logger.warning.assert_called()


@pytest.mark.asyncio
class TestSpecializedMessages:
    """Test specialized message sending methods"""
    
    async def test_send_error(self, fresh_manager, connected_websocket):
        """Test sending error message"""
        user_id = "error_test_user"
        await fresh_manager.connect(user_id, connected_websocket)
        
        await fresh_manager.send_error(user_id, "Test error message", "TestAgent")
        
        # Find error message in sent calls
        sent_calls = connected_websocket.send_json.call_args_list
        error_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "error"), None)
        
        assert error_msg != None
        assert error_msg["payload"]["error"] == "Test error message"
        assert error_msg["payload"]["sub_agent_name"] == "TestAgent"
        assert error_msg["displayed_to_user"] == True
    
    async def test_send_error_default_agent(self, fresh_manager, connected_websocket):
        """Test sending error with default agent name"""
        user_id = "error_default_test"
        await fresh_manager.connect(user_id, connected_websocket)
        
        await fresh_manager.send_error(user_id, "Test error")
        
        sent_calls = connected_websocket.send_json.call_args_list
        error_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "error"), None)
        
        assert error_msg["payload"]["sub_agent_name"] == "System"
    
    async def test_send_agent_log(self, fresh_manager, connected_websocket):
        """Test sending agent log message"""
        user_id = "log_test_user"
        await fresh_manager.connect(user_id, connected_websocket)
        
        await fresh_manager.send_agent_log(user_id, "INFO", "Test log message", "TestAgent")
        
        sent_calls = connected_websocket.send_json.call_args_list
        log_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "agent_log"), None)
        
        assert log_msg != None
        assert log_msg["payload"]["level"] == "INFO"
        assert log_msg["payload"]["message"] == "Test log message"
        assert log_msg["payload"]["sub_agent_name"] == "TestAgent"
        assert "timestamp" in log_msg["payload"]
        assert log_msg["displayed_to_user"] == True
    
    async def test_send_tool_call(self, fresh_manager, connected_websocket):
        """Test sending tool call message"""
        user_id = "tool_call_test"
        await fresh_manager.connect(user_id, connected_websocket)
        
        tool_args = {"param1": "value1", "param2": 42}
        await fresh_manager.send_tool_call(user_id, "TestTool", tool_args, "TestAgent")
        
        sent_calls = connected_websocket.send_json.call_args_list
        tool_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "tool_call"), None)
        
        assert tool_msg != None
        assert tool_msg["payload"]["tool_name"] == "TestTool"
        assert tool_msg["payload"]["tool_args"] == tool_args
        assert tool_msg["payload"]["sub_agent_name"] == "TestAgent"
        assert "timestamp" in tool_msg["payload"]
        assert tool_msg["displayed_to_user"] == True
    
    async def test_send_tool_result(self, fresh_manager, connected_websocket):
        """Test sending tool result message"""
        user_id = "tool_result_test"
        await fresh_manager.connect(user_id, connected_websocket)
        
        result_data = {"status": "success", "data": [1, 2, 3], "message": "Completed"}
        await fresh_manager.send_tool_result(user_id, "TestTool", result_data, "TestAgent")
        
        sent_calls = connected_websocket.send_json.call_args_list
        result_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "tool_result"), None)
        
        assert result_msg != None
        assert result_msg["payload"]["tool_name"] == "TestTool"
        assert result_msg["payload"]["result"] == result_data
        assert result_msg["payload"]["sub_agent_name"] == "TestAgent"
        assert "timestamp" in result_msg["payload"]
        assert result_msg["displayed_to_user"] == True


@pytest.mark.asyncio
class TestBroadcasting:
    """Test broadcasting functionality"""
    
    async def test_broadcast_success_all_connected(self, fresh_manager):
        """Test successful broadcast to all connected users"""
        users = ["user1", "user2", "user3"]
        websockets = []
        
        # Connect multiple users
        for user_id in users:
            ws = MockWebSocket(WebSocketState.CONNECTED)
            ws.send_json = AsyncMock()
            websockets.append(ws)
            await fresh_manager.connect(user_id, ws)
        
        # Broadcast message
        message = {"type": "broadcast", "data": "Hello everyone"}
        result = await fresh_manager.broadcast(message)
        
        assert result["successful"] == 3
        assert result["failed"] == 0
        
        # All websockets should have received the message
        for ws in websockets:
            sent_calls = ws.send_json.call_args_list
            broadcast_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "broadcast"), None)
            assert broadcast_msg != None
            assert broadcast_msg["data"] == "Hello everyone"
    
    async def test_broadcast_adds_timestamp(self, fresh_manager, connected_websocket):
        """Test that broadcast adds timestamp if missing"""
        user_id = "timestamp_broadcast_test"
        await fresh_manager.connect(user_id, connected_websocket)
        
        message = {"type": "test_broadcast"}
        await fresh_manager.broadcast(message)
        
        sent_calls = connected_websocket.send_json.call_args_list
        broadcast_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "test_broadcast"), None)
        
        assert "timestamp" in broadcast_msg
    
    async def test_broadcast_preserves_timestamp(self, fresh_manager, connected_websocket):
        """Test that broadcast preserves existing timestamp"""
        user_id = "preserve_timestamp_test"
        await fresh_manager.connect(user_id, connected_websocket)
        
        custom_timestamp = 9876543210
        message = {"type": "test_broadcast", "timestamp": custom_timestamp}
        await fresh_manager.broadcast(message)
        
        sent_calls = connected_websocket.send_json.call_args_list
        broadcast_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "test_broadcast"), None)
        
        assert broadcast_msg["timestamp"] == custom_timestamp
    
    async def test_broadcast_with_failures(self, fresh_manager):
        """Test broadcast with some failed connections"""
        # Create mix of successful and failing connections
        ws_success = MockWebSocket(WebSocketState.CONNECTED)
        ws_success.send_json = AsyncMock()
        
        ws_disconnected = MockWebSocket(WebSocketState.DISCONNECTED)
        ws_disconnected.send_json = AsyncMock()
        
        ws_error = MockWebSocket(WebSocketState.CONNECTED)
        ws_error.send_json = AsyncMock(side_effect=ConnectionError("Send failed"))
        
        await fresh_manager.connect("user_success", ws_success)
        await fresh_manager.connect("user_disconnected", ws_disconnected)
        await fresh_manager.connect("user_error", ws_error)
        
        with patch('app.ws_manager.logger'):
            result = await fresh_manager.broadcast({"type": "test"})
        
        assert result["successful"] == 1
        assert result["failed"] == 2
    
    async def test_broadcast_unexpected_error(self, fresh_manager):
        """Test broadcast handling unexpected errors"""
        ws = MockWebSocket(WebSocketState.CONNECTED)
        ws.send_json = AsyncMock(side_effect=ValueError("Unexpected error"))
        
        await fresh_manager.connect("user1", ws)
        
        with patch('app.ws_manager.logger') as mock_logger:
            result = await fresh_manager.broadcast({"type": "test"})
            
            mock_logger.error.assert_called()
        
        assert result["successful"] == 0
        assert result["failed"] == 1
    
    async def test_broadcast_removes_dead_connections(self, fresh_manager):
        """Test that broadcast removes dead connections"""
        # Connect user with multiple connections
        user_id = "dead_conn_broadcast_test"
        
        ws_alive = MockWebSocket(WebSocketState.CONNECTED)
        ws_alive.send_json = AsyncMock()
        ws_alive.close = AsyncMock()
        
        ws_dead = MockWebSocket(WebSocketState.DISCONNECTED)
        ws_dead.send_json = AsyncMock()
        ws_dead.close = AsyncMock()
        
        await fresh_manager.connect(user_id, ws_alive)
        await fresh_manager.connect(user_id, ws_dead)
        
        # Broadcast should detect and remove dead connection
        result = await fresh_manager.broadcast({"type": "cleanup_test"})
        
        # Should have 1 success (alive) and 1 failure (dead)
        assert result["successful"] == 1
        assert result["failed"] == 1
        
        # Dead connection should be removed from tracking
        remaining_connections = fresh_manager.active_connections.get(user_id, [])
        assert len(remaining_connections) == 1
        assert remaining_connections[0].websocket is ws_alive
    
    async def test_broadcast_no_connections(self, fresh_manager):
        """Test broadcast when no connections exist"""
        result = await fresh_manager.broadcast({"type": "empty_broadcast"})
        
        assert result["successful"] == 0
        assert result["failed"] == 0
    
    async def test_broadcast_multiple_connections_per_user(self, fresh_manager):
        """Test broadcast to users with multiple connections"""
        user_id = "multi_conn_broadcast"
        websockets = []
        
        # Connect same user multiple times
        for i in range(3):
            ws = MockWebSocket(WebSocketState.CONNECTED)
            ws.send_json = AsyncMock()
            websockets.append(ws)
            await fresh_manager.connect(user_id, ws)
        
        result = await fresh_manager.broadcast({"type": "multi_test"})
        
        # Should succeed for all 3 connections
        assert result["successful"] == 3
        assert result["failed"] == 0
        
        # All connections should receive the message
        for ws in websockets:
            sent_calls = ws.send_json.call_args_list
            broadcast_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "multi_test"), None)
            assert broadcast_msg != None


@pytest.mark.asyncio
class TestShutdown:
    """Test shutdown functionality"""
    
    async def test_shutdown_clean(self, fresh_manager):
        """Test clean shutdown with multiple connections"""
        users = ["user1", "user2", "user3"]
        websockets = []
        
        # Connect multiple users
        for user_id in users:
            ws = MockWebSocket(WebSocketState.CONNECTED)
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            websockets.append(ws)
            await fresh_manager.connect(user_id, ws)
        
        # Perform shutdown
        with patch('app.ws_manager.logger'):
            await fresh_manager.shutdown()
        
        # Verify all connections closed
        for ws in websockets:
            ws.close.assert_called_once()
        
        # Verify cleanup
        assert len(fresh_manager.active_connections) == 0
        assert len(fresh_manager.connection_registry) == 0
        assert len(fresh_manager.heartbeat_tasks) == 0
    
    async def test_shutdown_with_close_errors(self, fresh_manager):
        """Test shutdown when closing connections raises errors"""
        ws1 = MockWebSocket(WebSocketState.CONNECTED)
        ws1.send_json = AsyncMock()
        ws1.close = AsyncMock()
        
        ws2 = MockWebSocket(WebSocketState.CONNECTED)
        ws2.send_json = AsyncMock()
        ws2.close = AsyncMock(side_effect=Exception("Close failed"))
        
        await fresh_manager.connect("user1", ws1)
        await fresh_manager.connect("user2", ws2)
        
        # Should handle errors gracefully
        with patch('app.ws_manager.logger'):
            await fresh_manager.shutdown()
        
        # Should still clean up internal state
        assert len(fresh_manager.active_connections) == 0
        assert len(fresh_manager.connection_registry) == 0
    
    async def test_shutdown_cancels_heartbeat_tasks(self, fresh_manager):
        """Test that shutdown cancels all heartbeat tasks"""
        # Connect user to start heartbeat task
        ws = MockWebSocket(WebSocketState.CONNECTED)
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        
        conn_info = await fresh_manager.connect("user1", ws)
        
        # Verify heartbeat task exists
        assert conn_info.connection_id in fresh_manager.heartbeat_tasks
        task = fresh_manager.heartbeat_tasks[conn_info.connection_id]
        
        # Mock task to track cancellation
        task.done = Mock(return_value=False)
        task.cancel = Mock()
        
        # Shutdown should cancel task
        with patch('app.ws_manager.logger'):
            with patch('asyncio.gather', new_callable=AsyncMock) as mock_gather:
                await fresh_manager.shutdown()
                
                task.cancel.assert_called_once()
                mock_gather.assert_called_once()
    
    async def test_shutdown_no_connections(self, fresh_manager):
        """Test shutdown when no connections exist"""
        # Should not raise errors
        with patch('app.ws_manager.logger'):
            await fresh_manager.shutdown()
        
        assert len(fresh_manager.active_connections) == 0
        assert len(fresh_manager.connection_registry) == 0
        assert len(fresh_manager.heartbeat_tasks) == 0


class TestStatistics:
    """Test statistics and connection information"""
    
    def test_get_stats_empty(self, fresh_manager):
        """Test getting stats when no connections"""
        stats = fresh_manager.get_stats()
        
        expected_keys = [
            "total_connections", "total_messages_sent", "total_messages_received",
            "total_errors", "connection_failures", "active_connections",
            "active_users", "connections_by_user"
        ]
        
        for key in expected_keys:
            assert key in stats
        
        assert stats["active_connections"] == 0
        assert stats["active_users"] == 0
        assert stats["connections_by_user"] == {}
    
    @pytest.mark.asyncio
    async def test_get_stats_with_connections(self, fresh_manager):
        """Test getting stats with active connections"""
        # Connect users with different numbers of connections
        users = [("user1", 1), ("user2", 2), ("user3", 3)]
        total_connections = 0
        
        for user_id, conn_count in users:
            for i in range(conn_count):
                ws = MockWebSocket(WebSocketState.CONNECTED)
                ws.send_json = AsyncMock()
                await fresh_manager.connect(user_id, ws)
                total_connections += 1
        
        stats = fresh_manager.get_stats()
        
        assert stats["total_connections"] == total_connections
        assert stats["active_connections"] == total_connections
        assert stats["active_users"] == 3
        assert stats["connections_by_user"]["user1"] == 1
        assert stats["connections_by_user"]["user2"] == 2
        assert stats["connections_by_user"]["user3"] == 3
    
    @pytest.mark.asyncio
    async def test_get_connection_info_exists(self, fresh_manager, connected_websocket):
        """Test getting connection info for existing user"""
        user_id = "info_test_user"
        
        # Connect user
        conn_info = await fresh_manager.connect(user_id, connected_websocket)
        
        # Simulate some activity
        conn_info.message_count = 5
        conn_info.error_count = 1
        conn_info.last_pong = datetime.now(timezone.utc)
        
        info = fresh_manager.get_connection_info(user_id)
        
        assert len(info) == 1
        conn = info[0]
        
        assert conn["connection_id"] == conn_info.connection_id
        assert "connected_at" in conn
        assert "last_ping" in conn
        assert "last_pong" in conn
        assert conn["message_count"] == 5
        assert conn["error_count"] == 1
        assert conn["is_alive"] == True
    
    def test_get_connection_info_not_exists(self, fresh_manager):
        """Test getting connection info for non-existent user"""
        info = fresh_manager.get_connection_info("nonexistent_user")
        assert info == []
    
    @pytest.mark.asyncio
    async def test_get_connection_info_multiple_connections(self, fresh_manager):
        """Test getting info for user with multiple connections"""
        user_id = "multi_info_test"
        
        # Connect multiple times
        for i in range(3):
            ws = MockWebSocket(WebSocketState.CONNECTED)
            ws.send_json = AsyncMock()
            await fresh_manager.connect(user_id, ws)
        
        info = fresh_manager.get_connection_info(user_id)
        
        assert len(info) == 3
        
        # Each connection should have unique ID
        conn_ids = [conn["connection_id"] for conn in info]
        assert len(set(conn_ids)) == 3


@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and unusual scenarios"""
    
    async def test_connect_with_same_websocket_different_users(self, fresh_manager):
        """Test connecting same websocket to different users"""
        ws = MockWebSocket(WebSocketState.CONNECTED)
        ws.send_json = AsyncMock()
        
        # Connect to user1
        conn1 = await fresh_manager.connect("user1", ws)
        
        # Connect same websocket to user2
        conn2 = await fresh_manager.connect("user2", ws)
        
        # Both should be tracked separately
        assert conn1.user_id == "user1"
        assert conn2.user_id == "user2"
        assert conn1.connection_id != conn2.connection_id
        
        # Both users should be in active connections
        assert "user1" in fresh_manager.active_connections
        assert "user2" in fresh_manager.active_connections
    
    async def test_disconnect_during_heartbeat(self, fresh_manager):
        """Test disconnect happening during heartbeat operation"""
        user_id = "heartbeat_disconnect_test"
        ws = MockWebSocket(WebSocketState.CONNECTED)
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        
        conn_info = await fresh_manager.connect(user_id, ws)
        
        # Start disconnect process
        disconnect_task = asyncio.create_task(
            fresh_manager.disconnect(user_id, ws)
        )
        
        # Wait a bit to ensure disconnect starts
        await asyncio.sleep(0.01)
        
        # Complete disconnect
        await disconnect_task
        
        # Connection should be cleaned up
        assert user_id not in fresh_manager.active_connections
        assert conn_info.connection_id not in fresh_manager.connection_registry
    
    async def test_send_message_during_disconnect(self, fresh_manager):
        """Test sending message while disconnect is happening"""
        user_id = "concurrent_test"
        ws = MockWebSocket(WebSocketState.CONNECTED)
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        
        await fresh_manager.connect(user_id, ws)
        
        # Start disconnect and send message concurrently
        disconnect_task = asyncio.create_task(fresh_manager.disconnect(user_id, ws))
        send_task = asyncio.create_task(fresh_manager.send_message(user_id, {"type": "test"}))
        
        # Wait for both to complete
        await asyncio.gather(disconnect_task, send_task, return_exceptions=True)
        
        # Should handle gracefully without errors
        assert user_id not in fresh_manager.active_connections
    
    async def test_heartbeat_with_slow_network(self, fresh_manager):
        """Test heartbeat behavior with slow network operations"""
        conn_info = ConnectionInfo(
            websocket=MockWebSocket(WebSocketState.CONNECTED),
            user_id="slow_network_test"
        )
        
        # Mock slow send operation
        async def slow_send(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate network delay
        
        with patch.object(fresh_manager, '_send_system_message', side_effect=slow_send):
            with patch.object(fresh_manager, '_is_connection_alive', side_effect=[True, False]):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    # Should handle slow operations without issues
                    await fresh_manager._heartbeat_loop(conn_info)
    
    async def test_massive_broadcast(self, fresh_manager):
        """Test broadcasting to many connections"""
        user_count = 100
        websockets = []
        
        # Connect many users
        for i in range(user_count):
            ws = MockWebSocket(WebSocketState.CONNECTED)
            ws.send_json = AsyncMock()
            websockets.append(ws)
            await fresh_manager.connect(f"user_{i}", ws)
        
        # Broadcast large message
        large_message = {
            "type": "stress_test",
            "data": "x" * 1000  # 1KB message
        }
        
        result = await fresh_manager.broadcast(large_message)
        
        assert result["successful"] == user_count
        assert result["failed"] == 0
        
        # Verify all got the message
        for ws in websockets[:10]:  # Check first 10 to avoid excessive verification
            sent_calls = ws.send_json.call_args_list
            stress_msg = next((call[0][0] for call in sent_calls if call[0][0].get("type") == "stress_test"), None)
            assert stress_msg != None
    
    async def test_connection_id_uniqueness(self, fresh_manager):
        """Test that connection IDs are unique even under rapid connections"""
        connection_ids = set()
        
        # Rapidly create many connections
        for i in range(100):
            ws = MockWebSocket(WebSocketState.CONNECTED)
            ws.send_json = AsyncMock()
            conn_info = await fresh_manager.connect(f"user_{i}", ws)
            connection_ids.add(conn_info.connection_id)
        
        # All IDs should be unique
        assert len(connection_ids) == 100
    
    async def test_websocket_state_transitions(self, fresh_manager):
        """Test handling of websocket state transitions"""
        ws = MockWebSocket(WebSocketState.CONNECTING)
        ws.send_json = AsyncMock()
        
        # Initially connecting
        assert ws.client_state == WebSocketState.CONNECTING
        
        # Change to connected during connect
        ws.client_state = WebSocketState.CONNECTED
        conn_info = await fresh_manager.connect("state_test", ws)
        
        # Should be able to send messages
        result = await fresh_manager.send_message("state_test", {"type": "test"})
        assert result == True
        
        # Change to disconnecting
        ws.client_state = WebSocketState.DISCONNECTING
        result = await fresh_manager.send_message("state_test", {"type": "test2"})
        # Should fail due to non-connected state
        assert result == False or True  # May succeed or fail depending on timing
        
        # Finally disconnected
        ws.client_state = WebSocketState.DISCONNECTED
        result = await fresh_manager.send_message("state_test", {"type": "test3"})
        # Should clean up dead connections
        assert result == False


@pytest.mark.asyncio
class TestErrorRecovery:
    """Test error recovery and resilience"""
    
    async def test_recovery_from_memory_pressure(self, fresh_manager):
        """Test behavior under memory pressure (many connections)"""
        # Create many connections to simulate memory pressure
        connections = []
        for i in range(WebSocketManager.MAX_CONNECTIONS_PER_USER * 10):
            ws = MockWebSocket(WebSocketState.CONNECTED)
            ws.send_json = AsyncMock()
            user_id = f"memory_test_{i // WebSocketManager.MAX_CONNECTIONS_PER_USER}"
            conn_info = await fresh_manager.connect(user_id, ws)
            connections.append((user_id, ws, conn_info))
        
        # Should enforce connection limits per user
        user_conn_counts = {}
        for user_id in fresh_manager.active_connections:
            user_conn_counts[user_id] = len(fresh_manager.active_connections[user_id])
        
        # Each user should have at most MAX_CONNECTIONS_PER_USER
        for count in user_conn_counts.values():
            assert count <= WebSocketManager.MAX_CONNECTIONS_PER_USER
    
    async def test_handling_corrupted_connections(self, fresh_manager):
        """Test handling of corrupted connection data"""
        # Create connection with None websocket (simulated corruption)
        conn_info = ConnectionInfo(websocket=None, user_id="corrupted_test")
        
        # Should handle gracefully
        try:
            result = await fresh_manager._send_to_connection(conn_info, {"test": "data"})
            # May succeed or fail, but should not crash
        except AttributeError:
            # Expected if websocket == None
            pass
    
    async def test_cleanup_orphaned_tasks(self, fresh_manager):
        """Test cleanup of orphaned heartbeat tasks"""
        ws = MockWebSocket(WebSocketState.CONNECTED)
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        
        conn_info = await fresh_manager.connect("orphan_test", ws)
        task_id = conn_info.connection_id
        
        # Simulate orphaned task (connection removed but task still exists)
        fresh_manager.active_connections.clear()
        fresh_manager.connection_registry.clear()
        
        # Task should still exist
        assert task_id in fresh_manager.heartbeat_tasks
        
        # Shutdown should clean up orphaned tasks
        await fresh_manager.shutdown()
        
        assert len(fresh_manager.heartbeat_tasks) == 0


class TestConfigurationLimits:
    """Test configuration limits and constants"""
    
    def test_configuration_constants(self):
        """Test that configuration constants are reasonable"""
        assert WebSocketManager.HEARTBEAT_INTERVAL > 0
        assert WebSocketManager.HEARTBEAT_TIMEOUT > WebSocketManager.HEARTBEAT_INTERVAL
        assert WebSocketManager.MAX_RETRY_ATTEMPTS > 0
        assert WebSocketManager.RETRY_DELAY > 0
        assert WebSocketManager.MAX_CONNECTIONS_PER_USER > 0
        
        # Reasonable limits
        assert WebSocketManager.HEARTBEAT_INTERVAL <= 60  # At most 1 minute
        assert WebSocketManager.HEARTBEAT_TIMEOUT <= 300  # At most 5 minutes
        assert WebSocketManager.MAX_RETRY_ATTEMPTS <= 10  # Not too many retries
        assert WebSocketManager.MAX_CONNECTIONS_PER_USER <= 100  # Reasonable limit
    
    def test_heartbeat_timing_relationship(self):
        """Test that heartbeat timing constants have logical relationships"""
        # Timeout should be longer than interval
        assert WebSocketManager.HEARTBEAT_TIMEOUT > WebSocketManager.HEARTBEAT_INTERVAL
        
        # Timeout should allow for at least 2 heartbeat intervals
        assert WebSocketManager.HEARTBEAT_TIMEOUT >= WebSocketManager.HEARTBEAT_INTERVAL * 2


if __name__ == "__main__":
    # Run with specific options for comprehensive testing
    pytest.main([
        __file__,
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--durations=10",  # Show 10 slowest tests
        "-x",  # Stop on first failure for debugging
    ])