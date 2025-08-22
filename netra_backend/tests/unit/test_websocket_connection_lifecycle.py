"""Unit tests for WebSocket connection lifecycle management.

Tests connection establishment, disconnection, and cleanup.
USER RETENTION CRITICAL - Real-time features keep users engaged.

Business Value: Ensures reliable WebSocket connection lifecycle preventing
user frustration and churn from connection failures.
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import WebSocket

from netra_backend.app.websocket.connection_info import ConnectionInfo

from netra_backend.app.websocket.connection import ConnectionManager

class TestWebSocketConnectionLifecycle:
    """Test suite for WebSocket connection lifecycle management."""
    
    @pytest.fixture
    def manager(self):
        """Create connection manager with mocked dependencies."""
        with patch('app.websocket.connection_manager.ConnectionExecutionOrchestrator'):
            manager = Modernget_connection_manager()
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
    
    async def test_concurrent_connection_operations(self, manager, mock_websocket):
        """Test handling of concurrent connection operations."""
        success_result = Mock()
        success_result.success = True
        success_result.result = {"connection_info": Mock(connection_id="concurrent-conn")}
        manager.orchestrator.establish_connection = AsyncMock(return_value=success_result)
        
        # Simulate concurrent connections
        tasks = [
            manager.connect(f"user-{i}", mock_websocket)
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed without exceptions
        assert all(not isinstance(r, Exception) for r in results)
        assert len(manager.active_connections) == 5
    
    async def test_connection_limit_edge_cases(self, manager, mock_websocket):
        """Test edge cases in connection limit enforcement."""
        manager.max_connections_per_user = 1
        
        # First connection should succeed
        success_result = Mock()
        success_result.success = True
        success_result.result = {"connection_info": Mock(connection_id="first-conn")}
        manager.orchestrator.establish_connection = AsyncMock(return_value=success_result)
        
        close_result = Mock(success=True)
        manager.orchestrator.close_connection = AsyncMock(return_value=close_result)
        
        await manager.connect("limit-user", mock_websocket)
        
        # Second connection should trigger limit enforcement
        success_result.result = {"connection_info": Mock(connection_id="second-conn")}
        await manager.connect("limit-user", mock_websocket)
        
        # Should have called close_connection to enforce limit
        manager.orchestrator.close_connection.assert_called()
    
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