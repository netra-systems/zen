"""
WebSocketManager Connection Management Tests
Tests connection establishment, disconnection, and connection lifecycle
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from starlette.websockets import WebSocketState
from datetime import datetime, timezone

from app.ws_manager import WebSocketManager, ConnectionInfo
from app.tests.test_ws_manager_comprehensive.conftest import MockWebSocket


class TestConnectionManagement:
    """Test connection establishment and management"""
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_user(self, fresh_manager, connected_websocket):
        """Test disconnecting non-existent user doesn't error"""
        # Should not raise exception
        await fresh_manager.disconnect("nonexistent_user", connected_websocket)
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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