"""Unit tests for WebSocket Ghost Connection Prevention.

Tests WebSocket connection state management and ghost connection cleanup.
RELIABILITY CRITICAL - Prevents resource leaks and connection exhaustion.

Business Value: Ensures connection limits work properly, preventing
resource exhaustion that could impact all users ($50K+ MRR protection).
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import WebSocket

from netra_backend.app.websocket_core_info import ConnectionInfo, ConnectionState

from netra_backend.app.websocket_core import WebSocketManager as ConnectionManager

class TestGhostConnectionPrevention:
    """Test suite for ghost connection prevention and cleanup."""
    
    @pytest.fixture
    def manager(self):
        """Create connection manager with mocked dependencies."""
        with patch('netra_backend.app.websocket.connection_manager.ConnectionExecutionOrchestrator'):
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
    def active_connection(self, mock_websocket):
        """Create active connection."""
        return ConnectionInfo(
            websocket=mock_websocket,
            user_id="test-user",
            connection_id="active-conn-123"
        )
    
    @pytest.fixture
    def failed_connection(self, mock_websocket):
        """Create failed connection."""
        conn = ConnectionInfo(
            websocket=mock_websocket,
            user_id="test-user",
            connection_id="failed-conn-456"
        )
        conn.transition_to_failed()
        return conn
    
    @pytest.fixture
    def stale_closing_connection(self, mock_websocket):
        """Create stale closing connection."""
        conn = ConnectionInfo(
            websocket=mock_websocket,
            user_id="test-user",
            connection_id="stale-conn-789"
        )
        conn.transition_to_closing()
        # Make it stale (older than 60 seconds)
        conn.last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=90)
        return conn

    async def test_close_oldest_connection_success(self, manager, active_connection):
        """Test successful closure of oldest connection."""
        await manager.registry.register_connection("test-user", active_connection)
        
        # Mock successful closure
        orchestrator_result = Mock(success=True)
        manager.orchestrator.close_connection = AsyncMock(return_value=orchestrator_result)
        
        await manager._close_oldest_connection("test-user")
        
        # Verify connection transitioned to closed and was removed
        assert active_connection.state == ConnectionState.CLOSED
        assert len(manager.registry.get_user_connections("test-user")) == 0

    async def test_close_oldest_connection_failure_creates_ghost(self, manager, active_connection):
        """Test failed closure creates ghost connection that gets cleaned up."""
        await manager.registry.register_connection("test-user", active_connection)
        
        # Mock failed closure
        orchestrator_result = Mock(success=False)
        manager.orchestrator.close_connection = AsyncMock(return_value=orchestrator_result)
        
        await manager._close_oldest_connection("test-user")
        
        # Verify connection transitioned to failed state (ghost)
        assert active_connection.state == ConnectionState.FAILED
        assert len(manager.registry.get_user_connections("test-user")) == 1  # Still tracked
        assert active_connection.is_ghost_connection()

    async def test_close_oldest_connection_exception_creates_ghost(self, manager, active_connection):
        """Test exception during closure creates ghost connection."""
        await manager.registry.register_connection("test-user", active_connection)
        
        # Mock exception during closure
        manager.orchestrator.close_connection = AsyncMock(side_effect=Exception("Network error"))
        
        await manager._close_oldest_connection("test-user")
        
        # Verify connection transitioned to failed state
        assert active_connection.state == ConnectionState.FAILED
        assert active_connection.is_ghost_connection()

    async def test_disconnect_atomic_state_management(self, manager, mock_websocket, active_connection):
        """Test atomic state management during disconnection."""
        await manager.registry.register_connection("test-user", active_connection)
        
        # Mock successful disconnect
        orchestrator_result = Mock(success=True)
        manager.orchestrator.close_connection = AsyncMock(return_value=orchestrator_result)
        
        await manager.disconnect("test-user", mock_websocket)
        
        # Verify atomic state transition to closed
        assert active_connection.state == ConnectionState.CLOSED
        assert len(manager.registry.get_user_connections("test-user")) == 0

    async def test_disconnect_failure_marks_as_failed(self, manager, mock_websocket, active_connection):
        """Test disconnect failure properly marks connection as failed."""
        await manager.registry.register_connection("test-user", active_connection)
        
        # Mock failed disconnect
        orchestrator_result = Mock(success=False)
        manager.orchestrator.close_connection = AsyncMock(return_value=orchestrator_result)
        
        await manager.disconnect("test-user", mock_websocket)
        
        # Verify connection marked as failed (not removed)
        assert active_connection.state == ConnectionState.FAILED
        assert len(manager.registry.get_user_connections("test-user")) == 1

    def test_connection_state_transitions(self, active_connection):
        """Test atomic connection state transitions."""
        # Test transition to closing
        success = active_connection.transition_to_closing()
        assert success is True
        assert active_connection.state == ConnectionState.CLOSING
        assert active_connection.is_closing is True
        
        # Test cannot transition to closing again
        success = active_connection.transition_to_closing()
        assert success is False
        
        # Test transition to failed
        active_connection.transition_to_failed()
        assert active_connection.state == ConnectionState.FAILED
        assert active_connection.failure_count == 1
        
        # Test transition to closed
        active_connection.transition_to_closed()
        assert active_connection.state == ConnectionState.CLOSED
        assert active_connection.is_closing is False

    def test_ghost_connection_detection(self, failed_connection, stale_closing_connection, active_connection):
        """Test ghost connection detection logic."""
        # Failed connection should be detected as ghost
        assert failed_connection.is_ghost_connection()
        
        # Stale closing connection should be detected as ghost
        assert stale_closing_connection.is_ghost_connection()
        
        # Active connection should not be ghost
        assert not active_connection.is_ghost_connection()

    def test_retry_closure_logic(self, failed_connection):
        """Test retry closure decision logic."""
        # Fresh failure should be retried
        assert failed_connection.should_retry_closure()
        
        # Exceed retry limit
        failed_connection.failure_count = 5
        assert not failed_connection.should_retry_closure()

    async def test_cleanup_ghost_connections(self, manager, failed_connection, stale_closing_connection, active_connection):
        """Test cleanup of ghost connections."""
        connections = [failed_connection, stale_closing_connection, active_connection]
        for conn in connections:
            await manager.registry.register_connection("test-user", conn)
        
        # Mock successful retry for failed connection
        orchestrator_result = Mock(success=True)
        manager.orchestrator.close_connection = AsyncMock(return_value=orchestrator_result)
        
        await manager.ghost_manager.cleanup_ghost_connections(connections)
        
        # Verify ghost connections were handled
        assert failed_connection.state == ConnectionState.CLOSED  # Retry succeeded
        assert stale_closing_connection.state == ConnectionState.CLOSED  # Force cleanup
        assert active_connection.state == ConnectionState.ACTIVE  # Unchanged

    async def test_force_cleanup_exhausted_retries(self, manager, failed_connection):
        """Test force cleanup of connection with exhausted retries."""
        failed_connection.failure_count = 5  # Exceed retry limit
        await manager.registry.register_connection("test-user", failed_connection)
        
        await manager.ghost_manager._handle_ghost_connection(failed_connection)
        
        # Should be force cleaned up
        assert failed_connection.state == ConnectionState.CLOSED

    async def test_ghost_connection_monitoring(self, manager, failed_connection, stale_closing_connection, active_connection):
        """Test ghost connection monitoring capabilities."""
        connections = [failed_connection, stale_closing_connection, active_connection]
        for conn in connections:
            await manager.registry.register_connection("test-user", conn)
        
        # Test ghost connection count
        ghost_count = await manager.get_ghost_connections_count()
        assert ghost_count == 2  # failed + stale closing
        
        # Test connections by state
        state_counts = manager.get_connections_by_state()
        assert state_counts[ConnectionState.ACTIVE.value] == 1
        assert state_counts[ConnectionState.FAILED.value] == 1
        assert state_counts[ConnectionState.CLOSING.value] == 1

    async def test_cleanup_dead_connections_with_ghosts(self, manager, failed_connection):
        """Test that cleanup_dead_connections handles ghost connections."""
        await manager.registry.register_connection("test-user", failed_connection)
        
        # Mock orchestrator cleanup
        orchestrator_result = Mock(success=True)
        orchestrator_result.result = {"cleaned_connections": 1}
        manager.orchestrator.cleanup_dead_connections = AsyncMock(return_value=orchestrator_result)
        
        await manager.cleanup_dead_connections()
        
        # Verify ghost cleanup was called
        assert failed_connection.state == ConnectionState.CLOSED  # Force cleaned

    async def test_stats_include_ghost_information(self, manager, failed_connection, active_connection):
        """Test that stats include ghost connection information."""
        await manager.registry.register_connection("test-user", failed_connection)
        await manager.registry.register_connection("test-user", active_connection)
        
        stats = manager._get_basic_stats()
        
        # Verify state counts are included
        assert "connections_by_state" in stats
        state_counts = stats["connections_by_state"]
        assert state_counts[ConnectionState.ACTIVE.value] == 1
        assert state_counts[ConnectionState.FAILED.value] == 1

    async def test_no_ghost_connections_after_failures_compliance(self, manager, active_connection):
        """Test compliance with 'no ghost connections after failures' requirement."""
        # Simulate 10 random disconnections with failures (reduced for test speed)
        for i in range(10):
            conn = ConnectionInfo(
                websocket=Mock(),
                user_id="test-user", 
                connection_id=f"conn-{i}"
            )
            await manager.registry.register_connection("test-user", conn)
            
            # Simulate failure every other time
            if i % 2 == 0:
                orchestrator_result = Mock(success=False)
            else:
                orchestrator_result = Mock(success=True)
            
            manager.orchestrator.close_connection = AsyncMock(return_value=orchestrator_result)
            
            await manager._close_oldest_connection("test-user")
            
            # Run cleanup after each failure
            cleanup_result = Mock(success=True, result={"cleaned_connections": 0})
            manager._execute_connection_cleanup = AsyncMock(return_value=cleanup_result)
            await manager.cleanup_dead_connections()
        
        # Verify no ghost connections remain
        ghost_count = await manager.get_ghost_connections_count()
        assert ghost_count == 0

    def test_connection_can_be_cleaned_up_logic(self, failed_connection, stale_closing_connection, active_connection):
        """Test connection cleanup eligibility logic."""
        # Failed connections can be cleaned up
        assert failed_connection.can_be_cleaned_up()
        
        # Ghost connections can be cleaned up
        assert stale_closing_connection.can_be_cleaned_up()
        
        # Active connections cannot be cleaned up
        assert not active_connection.can_be_cleaned_up()
        
        # Test closed connection can be cleaned up
        active_connection.transition_to_closed()
        assert active_connection.can_be_cleaned_up()

    # Helper methods (each ≤8 lines)
    def _create_failed_connection(self, user_id="test-user", conn_id="failed-conn"):
        """Helper to create failed connection."""
        mock_ws = Mock(spec=WebSocket)
        conn = ConnectionInfo(websocket=mock_ws, user_id=user_id, connection_id=conn_id)
        conn.transition_to_failed()
        return conn
    
    def _create_stale_connection(self, user_id="test-user", conn_id="stale-conn"):
        """Helper to create stale closing connection."""
        mock_ws = Mock(spec=WebSocket) 
        conn = ConnectionInfo(websocket=mock_ws, user_id=user_id, connection_id=conn_id)
        conn.transition_to_closing()
        conn.last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=90)
        return conn
    
    async def _verify_ghost_cleanup_effectiveness(self, manager, ghost_connections):
        """Helper to verify ghost cleanup removes all ghosts."""
        await manager._cleanup_ghost_connections(ghost_connections)
        for conn in ghost_connections:
            if conn.is_ghost_connection():
                assert conn.state == ConnectionState.CLOSED
    
    def _setup_mixed_connection_scenario(self, manager):
        """Helper to setup mixed connection state scenario."""
        connections = {
            "active": self._create_active_connection(),
            "failed": self._create_failed_connection(), 
            "stale": self._create_stale_connection()
        }
        manager.active_connections["test-user"] = list(connections.values())
        return connections
    
    def _create_active_connection(self, user_id="test-user", conn_id="active-conn"):
        """Helper to create active connection."""
        mock_ws = Mock(spec=WebSocket)
        return ConnectionInfo(websocket=mock_ws, user_id=user_id, connection_id=conn_id)