"""Unit tests for ModernConnectionManager.

Tests WebSocket connection lifecycle for user retention.
USER RETENTION CRITICAL - Real-time features keep users engaged.

Business Value: Ensures reliable WebSocket connections preventing user
frustration and churn from connection failures.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import WebSocket

from app.websocket.connection_manager import ModernConnectionManager
from app.websocket.connection_info import ConnectionInfo


class TestModernConnectionManager:
    """Test suite for ModernConnectionManager connection lifecycle."""
    
    @pytest.fixture
    def manager(self):
        """Create connection manager with mocked dependencies."""
        with patch('app.websocket.connection_manager.ConnectionExecutionOrchestrator'):
            manager = ModernConnectionManager()
            manager.orchestrator = Mock()
            return manager
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection."""
        mock_ws = Mock(spec=WebSocket)
        mock_ws.client_state = Mock()
        mock_ws.client_state.name = "CONNECTED"
        return mock_ws
    
    @pytest.fixture
    def connection_info(self, mock_websocket):
        """Create test connection info."""
        return ConnectionInfo(
            websocket=mock_websocket,
            user_id="test-user",
            connection_id="test-conn-123"
        )
    
    @pytest.fixture
    def orchestrator_success_result(self, connection_info):
        """Create successful orchestrator result."""
        result = Mock()
        result.success = True
        result.result = {"connection_info": connection_info}
        return result
    
    @pytest.fixture
    def orchestrator_failure_result(self):
        """Create failed orchestrator result."""
        result = Mock()
        result.success = False
        result.error = "Connection establishment failed"
        return result
    
    async def test_connect_success(self, manager, mock_websocket, orchestrator_success_result):
        """Test successful WebSocket connection establishment."""
        manager.orchestrator.establish_connection = AsyncMock(return_value=orchestrator_success_result)
        
        conn_info = await manager.connect("test-user", mock_websocket)
        
        assert conn_info.user_id == "test-user"
        assert "test-user" in manager.active_connections
        assert len(manager.active_connections["test-user"]) == 1
        assert manager._stats["total_connections"] == 1
    
    async def test_connect_failure(self, manager, mock_websocket, orchestrator_failure_result):
        """Test failed WebSocket connection establishment."""
        manager.orchestrator.establish_connection = AsyncMock(return_value=orchestrator_failure_result)
        
        with pytest.raises(Exception) as exc_info:
            await manager.connect("test-user", mock_websocket)
        
        assert "Connection failed" in str(exc_info.value)
        assert manager._stats["connection_failures"] == 1
    
    async def test_connect_enforces_connection_limit(self, manager, mock_websocket):
        """Test connection limit enforcement by closing oldest."""
        manager.max_connections_per_user = 2
        
        # Add existing connections at limit
        existing_conn = Mock()
        existing_conn.connection_id = "old-conn"
        manager.active_connections["test-user"] = [existing_conn, Mock()]
        
        close_result = Mock(success=True)
        manager.orchestrator.close_connection = AsyncMock(return_value=close_result)
        
        success_result = Mock()
        success_result.success = True
        success_result.result = {"connection_info": Mock(connection_id="new-conn")}
        manager.orchestrator.establish_connection = AsyncMock(return_value=success_result)
        
        await manager.connect("test-user", mock_websocket)
        
        manager.orchestrator.close_connection.assert_called_once()
    
    async def test_disconnect_success(self, manager, mock_websocket, connection_info):
        """Test successful WebSocket disconnection."""
        manager.active_connections["test-user"] = [connection_info]
        manager.connection_registry[connection_info.connection_id] = connection_info
        
        disconnect_result = Mock(success=True)
        manager.orchestrator.close_connection = AsyncMock(return_value=disconnect_result)
        
        await manager.disconnect("test-user", mock_websocket)
        
        assert "test-user" not in manager.active_connections
        assert connection_info.connection_id not in manager.connection_registry
    
    async def test_disconnect_user_not_found(self, manager, mock_websocket):
        """Test disconnection when user not in active connections."""
        await manager.disconnect("nonexistent-user", mock_websocket)
        
        # Should not raise exception, just log and return
        manager.orchestrator.close_connection.assert_not_called()
    
    async def test_disconnect_connection_not_found(self, manager, mock_websocket):
        """Test disconnection when connection not found for user."""
        manager.active_connections["test-user"] = []
        
        await manager.disconnect("test-user", mock_websocket)
        
        # Should not call orchestrator if connection not found
        manager.orchestrator.close_connection.assert_not_called()
    
    async def test_cleanup_dead_connections(self, manager):
        """Test cleanup of dead WebSocket connections."""
        conn1 = Mock()
        conn2 = Mock()
        manager.active_connections = {"user1": [conn1], "user2": [conn2]}
        
        cleanup_result = Mock(success=True)
        cleanup_result.result = {"cleaned_connections": 1}
        manager.orchestrator.cleanup_dead_connections = AsyncMock(return_value=cleanup_result)
        
        await manager.cleanup_dead_connections()
        
        manager.orchestrator.cleanup_dead_connections.assert_called_once()
        passed_connections = manager.orchestrator.cleanup_dead_connections.call_args[0][0]
        assert len(passed_connections) == 2
    
    def test_get_user_connections(self, manager, connection_info):
        """Test getting connections for specific user."""
        manager.active_connections["test-user"] = [connection_info]
        
        connections = manager.get_user_connections("test-user")
        
        assert len(connections) == 1
        assert connections[0] == connection_info
    
    def test_get_user_connections_empty(self, manager):
        """Test getting connections for user with no connections."""
        connections = manager.get_user_connections("nonexistent-user")
        
        assert connections == []
    
    def test_get_connection_by_id_success(self, manager, connection_info):
        """Test getting connection by ID."""
        manager.connection_registry[connection_info.connection_id] = connection_info
        
        found_conn = manager.get_connection_by_id(connection_info.connection_id)
        
        assert found_conn == connection_info
    
    def test_get_connection_by_id_not_found(self, manager):
        """Test getting non-existent connection by ID."""
        found_conn = manager.get_connection_by_id("nonexistent-id")
        
        assert found_conn is None
    
    def test_get_connection_info_detailed(self, manager, connection_info):
        """Test getting detailed connection information."""
        manager.active_connections["test-user"] = [connection_info]
        
        info_list = manager.get_connection_info("test-user")
        
        assert len(info_list) == 1
        info = info_list[0]
        assert info["connection_id"] == connection_info.connection_id
        assert info["message_count"] == connection_info.message_count
        assert "connected_at" in info
    
    def test_is_connection_alive(self, manager, connection_info):
        """Test checking if connection is alive."""
        with patch('app.websocket.connection_manager.ConnectionValidator') as mock_validator:
            mock_validator.is_websocket_connected.return_value = True
            
            is_alive = manager.is_connection_alive(connection_info)
            
            assert is_alive is True
            mock_validator.is_websocket_connected.assert_called_once_with(connection_info.websocket)
    
    async def test_find_connection_success(self, manager, mock_websocket, connection_info):
        """Test finding connection for user and websocket."""
        manager.active_connections["test-user"] = [connection_info]
        
        found_conn = await manager.find_connection("test-user", mock_websocket)
        
        assert found_conn == connection_info
    
    async def test_find_connection_not_found(self, manager, mock_websocket):
        """Test finding non-existent connection."""
        found_conn = await manager.find_connection("test-user", mock_websocket)
        
        assert found_conn is None
    
    async def test_get_stats_with_orchestrator(self, manager):
        """Test getting comprehensive connection statistics."""
        manager.active_connections = {"user1": [Mock(), Mock()], "user2": [Mock()]}
        manager._stats = {"total_connections": 10, "connection_failures": 2}
        
        orchestrator_result = Mock(success=True)
        orchestrator_result.result = {"connection_stats": {"modern_metric": 42}}
        manager.orchestrator.get_connection_stats = AsyncMock(return_value=orchestrator_result)
        
        stats = await manager.get_stats()
        
        assert stats["active_connections"] == 3
        assert stats["active_users"] == 2
        assert stats["total_connections"] == 10
        assert stats["modern_stats"]["modern_metric"] == 42
    
    async def test_get_stats_orchestrator_failure(self, manager):
        """Test getting stats when orchestrator fails."""
        orchestrator_result = Mock(success=False)
        manager.orchestrator.get_connection_stats = AsyncMock(return_value=orchestrator_result)
        
        stats = await manager.get_stats()
        
        assert "modern_stats" in stats
        assert stats["modern_stats"] == {}
    
    async def test_shutdown_graceful(self, manager, connection_info):
        """Test graceful shutdown of connection manager."""
        manager.active_connections = {"test-user": [connection_info]}
        
        close_result = Mock(success=True)
        manager.orchestrator.close_connection = AsyncMock(return_value=close_result)
        
        # Mock get_stats to avoid circular dependency
        manager.get_stats = AsyncMock(return_value={"final": "stats"})
        
        await manager.shutdown()
        
        assert len(manager.active_connections) == 0
        assert len(manager.connection_registry) == 0
        manager.orchestrator.close_connection.assert_called_with(
            connection_info, code=1001, reason="Server shutdown"
        )
    
    async def test_shutdown_with_connection_errors(self, manager, connection_info):
        """Test shutdown handles connection close errors gracefully."""
        manager.active_connections = {"test-user": [connection_info]}
        
        close_result = Mock(success=False)
        manager.orchestrator.close_connection = AsyncMock(return_value=close_result)
        manager.get_stats = AsyncMock(return_value={})
        
        # Should not raise exception even if close fails
        await manager.shutdown()
        
        assert len(manager.active_connections) == 0
    
    def test_get_health_status(self, manager):
        """Test getting comprehensive health status."""
        manager.active_connections = {"user1": [Mock()], "user2": [Mock(), Mock()]}
        orchestrator_health = {"status": "healthy"}
        manager.orchestrator.get_health_status.return_value = orchestrator_health
        
        health = manager.get_health_status()
        
        assert health["manager_status"] == "healthy"
        assert health["active_connections_count"] == 3
        assert health["active_users_count"] == 2
        assert health["orchestrator_health"] == orchestrator_health
    
    def test_connection_lifecycle_state_management(self, manager, connection_info):
        """Test connection state is properly managed through lifecycle."""
        # Initial registration
        manager._register_new_connection("test-user", connection_info)
        assert connection_info.connection_id in manager.connection_registry
        
        # Mark as closing
        manager._mark_connection_as_closing(connection_info)
        assert connection_info.is_closing is True
        
        # Cleanup
        manager._cleanup_connection_registry("test-user", connection_info)
        assert connection_info.connection_id not in manager.connection_registry
    
    # Helper methods (each ≤8 lines)
    def _create_mock_connection_info(self, user_id="test-user", conn_id="test-conn"):
        """Helper to create mock connection info."""
        mock_ws = Mock(spec=WebSocket)
        mock_ws.client_state.name = "CONNECTED"
        return ConnectionInfo(
            websocket=mock_ws, user_id=user_id, connection_id=conn_id
        )
    
    def _setup_manager_with_connections(self, manager, user_conn_counts):
        """Helper to setup manager with specified connections per user."""
        for user_id, count in user_conn_counts.items():
            connections = [self._create_mock_connection_info(user_id, f"conn-{i}") for i in range(count)]
            manager.active_connections[user_id] = connections
            for conn in connections:
                manager.connection_registry[conn.connection_id] = conn
    
    def _assert_connection_cleanup(self, manager, user_id, connection_info):
        """Helper to assert connection was properly cleaned up."""
        assert user_id not in manager.active_connections or connection_info not in manager.active_connections[user_id]
        assert connection_info.connection_id not in manager.connection_registry