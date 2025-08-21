"""
Tests for WebSocketManager singleton pattern and connection management
"""

import pytest
import asyncio
import threading
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from starlette.websockets import WebSocketState

from netra_backend.app.services.websocket.ws_manager import WebSocketManager, ConnectionInfo, manager, ws_manager
from netra_backend.tests.ws_manager.test_base import WebSocketTestBase, MockWebSocket

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



class TestSingletonPattern(WebSocketTestBase):
    """Test the singleton pattern implementation"""
    
    def test_singleton_instance(self):
        """Test that WebSocketManager is a singleton"""
        self.reset_manager_singleton()
        
        manager1 = WebSocketManager()
        manager2 = WebSocketManager()
        
        assert manager1 is manager2
        assert id(manager1) == id(manager2)
    
    def test_module_level_instances(self):
        """Test that module-level instances are the same"""
        assert manager is ws_manager
        assert isinstance(manager, WebSocketManager)
        assert isinstance(ws_manager, WebSocketManager)
    
    def test_singleton_thread_safety(self):
        """Test singleton creation is thread-safe"""
        self.reset_manager_singleton()
        
        instances = []
        errors = []
        
        def create_instance():
            try:
                instances.append(WebSocketManager())
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(instances) == 10
        # All instances should be the same object
        assert all(inst is instances[0] for inst in instances)
    
    def test_singleton_with_different_imports(self):
        """Test singleton works across different import styles"""
        self.reset_manager_singleton()
        
        from netra_backend.app.services.websocket.ws_manager import WebSocketManager as WSM1
        from netra_backend.app import ws_manager as ws_module
        WSM2 = ws_module.WebSocketManager
        
        instance1 = WSM1()
        instance2 = WSM2()
        
        assert instance1 is instance2


class TestConnectionManagement(WebSocketTestBase):
    """Test connection lifecycle and management"""
    async def test_connect_new_connection(self, fresh_manager, mock_websocket):
        """Test connecting a new WebSocket"""
        connection_id = "test-connection-123"
        user_id = "user-456"
        role = "admin"
        metadata = {"source": "test"}
        
        await fresh_manager.connect(
            websocket=mock_websocket,
            connection_id=connection_id,
            user_id=user_id,
            role=role,
            metadata=metadata
        )
        
        assert connection_id in fresh_manager.connections
        assert connection_id in fresh_manager.connection_info
        
        info = fresh_manager.connection_info[connection_id]
        assert info.connection_id == connection_id
        assert info.user_id == user_id
        assert info.role == role
        assert info.metadata == metadata
        assert isinstance(info.connected_at, datetime)
    async def test_connect_duplicate_connection(self, fresh_manager, mock_websocket):
        """Test connecting with duplicate connection ID"""
        connection_id = "duplicate-123"
        
        # First connection
        await fresh_manager.connect(mock_websocket, connection_id)
        
        # Duplicate connection with new websocket
        new_websocket = MockWebSocket()
        await fresh_manager.connect(new_websocket, connection_id)
        
        # Should replace the old connection
        assert fresh_manager.connections[connection_id] is new_websocket
    async def test_disconnect_existing_connection(self, fresh_manager, mock_websocket):
        """Test disconnecting an existing connection"""
        connection_id = "test-disconnect-123"
        
        await fresh_manager.connect(mock_websocket, connection_id)
        assert connection_id in fresh_manager.connections
        
        await fresh_manager.disconnect(connection_id)
        
        assert connection_id not in fresh_manager.connections
        assert connection_id not in fresh_manager.connection_info
    async def test_disconnect_nonexistent_connection(self, fresh_manager):
        """Test disconnecting a non-existent connection"""
        # Should not raise an error
        await fresh_manager.disconnect("nonexistent-123")
    async def test_disconnect_with_reason(self, fresh_manager, mock_websocket):
        """Test disconnecting with close code and reason"""
        connection_id = "test-close-123"
        
        await fresh_manager.connect(mock_websocket, connection_id)
        await fresh_manager.disconnect(connection_id, code=1001, reason="Going away")
        
        mock_websocket.close.assert_called_once_with(code=1001, reason="Going away")
        assert connection_id not in fresh_manager.connections
    async def test_disconnect_already_disconnected(self, fresh_manager):
        """Test disconnecting an already disconnected WebSocket"""
        connection_id = "test-already-disconnected"
        ws = MockWebSocket(WebSocketState.DISCONNECTED)
        
        await fresh_manager.connect(ws, connection_id)
        
        # Should handle gracefully without errors
        await fresh_manager.disconnect(connection_id)
        
        # close should not be called on already disconnected websocket
        ws.close.assert_not_called()
    async def test_disconnect_with_error(self, fresh_manager, mock_websocket):
        """Test disconnect handles close errors gracefully"""
        connection_id = "test-error-123"
        mock_websocket.close.side_effect = Exception("Close failed")
        
        await fresh_manager.connect(mock_websocket, connection_id)
        
        # Should not raise even if close fails
        await fresh_manager.disconnect(connection_id)
        
        # Connection should still be removed
        assert connection_id not in fresh_manager.connections
    async def test_get_connection_exists(self, fresh_manager, mock_websocket):
        """Test getting an existing connection"""
        connection_id = "test-get-123"
        
        await fresh_manager.connect(mock_websocket, connection_id)
        
        retrieved_ws = fresh_manager.get_connection(connection_id)
        assert retrieved_ws is mock_websocket
    
    def test_get_connection_not_exists(self, fresh_manager):
        """Test getting a non-existent connection"""
        retrieved_ws = fresh_manager.get_connection("nonexistent-123")
        assert retrieved_ws is None
    async def test_is_connected_true(self, fresh_manager, connected_websocket):
        """Test is_connected returns True for connected WebSocket"""
        connection_id = "test-connected-123"
        
        await fresh_manager.connect(connected_websocket, connection_id)
        
        assert fresh_manager.is_connected(connection_id) is True
    async def test_is_connected_false_disconnected(self, fresh_manager, disconnected_websocket):
        """Test is_connected returns False for disconnected WebSocket"""
        connection_id = "test-disconnected-123"
        
        await fresh_manager.connect(disconnected_websocket, connection_id)
        
        assert fresh_manager.is_connected(connection_id) is False
    
    def test_is_connected_false_nonexistent(self, fresh_manager):
        """Test is_connected returns False for non-existent connection"""
        assert fresh_manager.is_connected("nonexistent-123") is False
    
    def test_get_all_connections_empty(self, fresh_manager):
        """Test getting all connections when empty"""
        connections = fresh_manager.get_all_connections()
        assert connections == {}
    async def test_get_all_connections_multiple(self, fresh_manager):
        """Test getting all connections with multiple connections"""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()
        
        await fresh_manager.connect(ws1, "conn-1")
        await fresh_manager.connect(ws2, "conn-2")
        await fresh_manager.connect(ws3, "conn-3")
        
        connections = fresh_manager.get_all_connections()
        
        assert len(connections) == 3
        assert connections["conn-1"] is ws1
        assert connections["conn-2"] is ws2
        assert connections["conn-3"] is ws3