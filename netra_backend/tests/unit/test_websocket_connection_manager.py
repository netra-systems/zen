"""Unit tests for ConnectionManager information and stats.

Tests WebSocket connection information retrieval and statistics.
USER RETENTION CRITICAL - Real-time features keep users engaged.

Business Value: Ensures accurate connection tracking and monitoring
for operational insights and user experience optimization.
"""

import sys
from pathlib import Path

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import WebSocket

from netra_backend.app.websocket_core_info import ConnectionInfo

from netra_backend.app.websocket_core.manager import WebSocketManager

class TestWebSocketConnectionManager:
    """Test suite for WebSocket connection information and statistics."""
    
    @pytest.fixture
    def manager(self):
        """Create connection manager with mocked dependencies."""
        with patch('netra_backend.app.websocket.connection.ConnectionExecutionOrchestrator'):
            manager = ConnectionManager()
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
        with patch('netra_backend.app.websocket.connection_info.ConnectionValidator') as mock_validator:
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
    
    def test_connection_info_structure_completeness(self, manager, connection_info):
        """Test that connection info includes all required fields."""
        manager.active_connections["test-user"] = [connection_info]
        
        info_list = manager.get_connection_info("test-user")
        info = info_list[0]
        
        required_fields = [
            "connection_id", "message_count", "error_count", 
            "state", "connected_at", "last_ping"
        ]
        
        for field in required_fields:
            assert field in info
    
    def test_stats_accuracy_with_multiple_users(self, manager):
        """Test statistics accuracy with multiple users and connections."""
        # Setup complex connection scenario
        user_connections = {
            "user1": [Mock(), Mock(), Mock()],  # 3 connections
            "user2": [Mock()],                  # 1 connection
            "user3": [Mock(), Mock()]           # 2 connections
        }
        
        manager.active_connections = user_connections
        manager._stats = {"total_connections": 15, "connection_failures": 3}
        
        orchestrator_result = Mock(success=True)
        orchestrator_result.result = {"connection_stats": {}}
        manager.orchestrator.get_connection_stats = AsyncMock(return_value=orchestrator_result)
        
        # Test synchronous stats calculation
        legacy_stats = manager._get_legacy_stats()
        
        assert legacy_stats["active_connections"] == 6  # Total active
        assert legacy_stats["active_users"] == 3
        assert legacy_stats["total_connections"] == 15
        assert legacy_stats["connections_by_user"]["user1"] == 3
        assert legacy_stats["connections_by_user"]["user2"] == 1
        assert legacy_stats["connections_by_user"]["user3"] == 2
    
    def test_connection_registry_consistency(self, manager, connection_info):
        """Test consistency between active connections and registry."""
        # Register connection in both structures
        manager.active_connections["test-user"] = [connection_info]
        manager.connection_registry[connection_info.connection_id] = connection_info
        
        # Verify consistency
        assert connection_info.connection_id in manager.connection_registry
        assert manager.get_connection_by_id(connection_info.connection_id) == connection_info
        
        found_in_active = any(
            conn.connection_id == connection_info.connection_id
            for conn in manager.active_connections["test-user"]
        )
        assert found_in_active is True
    
    def test_empty_state_handling(self, manager):
        """Test handling of empty connection state."""
        # Test with no connections
        connections = manager.get_user_connections("empty-user")
        assert connections == []
        
        info_list = manager.get_connection_info("empty-user")
        assert info_list == []
        
        health = manager.get_health_status()
        assert health["active_connections_count"] == 0
        assert health["active_users_count"] == 0
    
    def test_connection_state_tracking(self, manager, connection_info):
        """Test accurate tracking of connection states."""
        manager.active_connections["test-user"] = [connection_info]
        
        info_list = manager.get_connection_info("test-user")
        info = info_list[0]
        
        # Verify state information is properly extracted
        assert info["state"] == connection_info.websocket.client_state.name
        assert info["message_count"] == connection_info.message_count
        assert info["error_count"] == connection_info.error_count
    
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
    
    def _verify_stats_structure(self, stats):
        """Helper to verify stats dictionary has required structure."""
        required_fields = ["active_connections", "active_users", "total_connections", "connections_by_user"]
        for field in required_fields:
            assert field in stats
            assert isinstance(stats[field], (int, dict))
    
    def _create_test_connection_scenario(self, manager):
        """Helper to create realistic connection test scenario."""
        scenarios = {
            "active_user": [Mock(), Mock()],
            "single_user": [Mock()],
            "heavy_user": [Mock(), Mock(), Mock(), Mock()]
        }
        manager.active_connections = scenarios
        return scenarios