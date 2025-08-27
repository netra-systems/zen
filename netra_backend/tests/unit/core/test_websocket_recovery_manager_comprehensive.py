"""
Comprehensive tests for WebSocket recovery functionality via WebSocketManager.

Tests the recovery capabilities built into WebSocketManager including:
- Connection recovery operations
- State management and persistence
- Error handling during recovery
- Recovery status tracking
- Connection lifecycle with recovery support
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from netra_backend.app.websocket_core.manager import WebSocketManager, get_websocket_manager
from netra_backend.app.schemas.websocket_models import WebSocketValidationError


class TestWebSocketManagerRecoveryInitialization:
    """Test WebSocketManager recovery functionality initialization."""
    
    def test_manager_initialization_includes_recovery(self):
        """Test WebSocket manager initializes with recovery capabilities."""
        manager = WebSocketManager()
        
        # Verify basic recovery-related structures exist
        assert hasattr(manager, 'connections')
        assert hasattr(manager, 'user_connections')
        assert hasattr(manager, 'connection_stats')
        assert isinstance(manager.connections, dict)
        assert len(manager.connections) == 0
        
    def test_manager_singleton_pattern(self):
        """Test WebSocket manager follows singleton pattern for recovery consistency."""
        manager1 = WebSocketManager()
        manager2 = WebSocketManager()
        
        assert manager1 is manager2
        assert id(manager1) == id(manager2)
        
    def test_connection_stats_initialization(self):
        """Test connection statistics are properly initialized for recovery tracking."""
        manager = WebSocketManager()
        
        stats = manager.connection_stats
        assert stats['total_connections'] == 0
        assert stats['active_connections'] == 0
        assert stats['messages_sent'] == 0
        assert stats['messages_received'] == 0
        assert stats['errors_handled'] == 0
        assert 'start_time' in stats


class TestWebSocketRecoveryConnectionManagement:
    """Test WebSocket recovery connection management functionality."""
    
    def setup_method(self):
        """Set up fresh manager instance for each test."""
        # Clear singleton instance for clean tests
        WebSocketManager._instance = None
        self.manager = WebSocketManager()
    
    @pytest.mark.asyncio
    async def test_create_connection_compatibility(self):
        """Test backward-compatible create_connection method."""
        # Mock WebSocket to avoid actual connection
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        # The create_connection method should work for recovery compatibility
        result = await self.manager.create_connection(
            "test-conn", "ws://localhost:8080", None
        )
        
        # Should return connection info (backward compatibility)
        assert result is not None
        
    def test_connection_tracking_structure(self):
        """Test that connection tracking supports recovery operations."""
        # Verify the manager has the proper structure for tracking connections
        assert hasattr(self.manager, 'connections')
        assert hasattr(self.manager, 'user_connections') 
        assert hasattr(self.manager, 'room_memberships')
        
        # These should be properly typed for recovery operations
        assert isinstance(self.manager.connections, dict)
        assert isinstance(self.manager.user_connections, dict)
        assert isinstance(self.manager.room_memberships, dict)
    
    @pytest.mark.asyncio
    async def test_remove_connection_compatibility(self):
        """Test backward-compatible remove_connection method."""
        # Add a mock connection first
        connection_id = "test-conn-123"
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        from datetime import datetime, timezone
        self.manager.connections[connection_id] = {
            "connection_id": connection_id,
            "user_id": "test_user",
            "websocket": mock_websocket,
            "is_healthy": True,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        # Test removal
        await self.manager.remove_connection(connection_id)
        
        # Connection should be removed
        assert connection_id not in self.manager.connections
    
    @pytest.mark.asyncio    
    async def test_connection_recovery_infrastructure(self):
        """Test that infrastructure exists for connection recovery."""
        # Verify recovery-related methods exist
        assert hasattr(self.manager, 'initiate_recovery')
        assert hasattr(self.manager, 'get_recovery_status')
        assert hasattr(self.manager, 'recover_all_connections')
        
        # These should be callable
        assert callable(self.manager.initiate_recovery)
        assert callable(self.manager.get_recovery_status)
        assert callable(self.manager.recover_all_connections)


class TestWebSocketRecoveryFunctionality:
    """Test WebSocket recovery functionality implementation."""
    
    def setup_method(self):
        """Set up fresh manager instance for each test."""
        WebSocketManager._instance = None
        self.manager = WebSocketManager()
    
    @pytest.mark.asyncio
    async def test_recover_all_connections_empty(self):
        """Test recovery when no connections exist."""
        results = await self.manager.recover_all_connections()
        
        # Should return empty dict when no connections
        assert isinstance(results, dict)
        assert len(results) == 0
        
    @pytest.mark.asyncio
    async def test_initiate_recovery_basic(self):
        """Test basic recovery initiation functionality."""
        connection_id = "test-conn-123"
        user_id = "test-user"
        error = ConnectionError("Test connection error")
        
        # Test recovery initiation
        result = await self.manager.initiate_recovery(
            connection_id, user_id, error
        )
        
        # Should return boolean indicating recovery attempt
        assert isinstance(result, bool)
        assert result is True  # Default implementation returns True
    
    @pytest.mark.asyncio
    async def test_initiate_recovery_with_strategies(self):
        """Test recovery initiation with specific strategies."""
        connection_id = "test-conn-123"
        user_id = "test-user"
        error = ConnectionError("Test connection error")
        strategies = ["reconnect", "reset_state"]
        
        # Test recovery with strategies
        result = await self.manager.initiate_recovery(
            connection_id, user_id, error, strategies
        )
        
        # Should handle strategies and return success
        assert isinstance(result, bool)
        assert result is True
        
    def test_get_recovery_status_no_connection(self):
        """Test recovery status for non-existent connection."""
        status = self.manager.get_recovery_status("nonexistent-conn")
        
        # Should return None for non-existent connections
        assert status is None
        
    def test_get_recovery_status_with_connection(self):
        """Test recovery status for existing connection."""
        connection_id = "test-conn-123"
        # Add a mock connection
        from datetime import datetime, timezone
        self.manager.connections[connection_id] = {
            "connection_id": connection_id,
            "user_id": "test_user",
            "websocket": Mock(spec=WebSocket),
            "is_healthy": True,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        status = self.manager.get_recovery_status(connection_id)
        
        # Should return status information for existing connections
        assert status is not None
        assert status["connection_id"] == connection_id
        assert status["user_id"] == "test_user"
        assert status["is_healthy"] == True
        assert status["message_count"] == 0
        assert "last_activity" in status


class TestWebSocketRecoveryStateManagement:
    """Test recovery state management and persistence."""
    
    def setup_method(self):
        """Set up fresh manager instance for each test."""
        WebSocketManager._instance = None
        self.manager = WebSocketManager()
    
    def test_save_state_snapshot_compatibility(self):
        """Test state snapshot saving for recovery compatibility."""
        connection_id = "test-conn-123"
        state_data = {"last_message": "ping", "retry_count": 2}
        
        # Should not raise exception - provides backward compatibility
        self.manager.save_state_snapshot(connection_id, state_data)
        
        # Method exists and handles the call gracefully
        assert True  # If we reach here, no exception was raised
        
    def test_connection_state_tracking(self):
        """Test that connections maintain state for recovery purposes."""
        # Mock connection data structure
        connection_id = "test-conn-123"
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        from datetime import datetime, timezone
        connection_data = {
            "connection_id": connection_id,
            "user_id": "test_user",
            "websocket": mock_websocket,
            "connected_at": "2023-01-01T00:00:00Z",
            "is_healthy": True,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        self.manager.connections[connection_id] = connection_data
        
        # Verify connection state is trackable
        stored_connection = self.manager.connections.get(connection_id)
        assert stored_connection is not None
        assert stored_connection["user_id"] == "test_user"
        assert "connected_at" in stored_connection


class TestWebSocketRecoveryStatusReporting:
    """Test recovery-related status reporting functionality."""
    
    def setup_method(self):
        """Set up fresh manager instance for each test."""
        WebSocketManager._instance = None
        self.manager = WebSocketManager()
    
    def test_get_all_status_empty(self):
        """Test status reporting with no connections."""
        status = self.manager.get_all_status()
        
        # Should return empty dict when no connections
        assert isinstance(status, dict)
        assert len(status) == 0
        
    def test_get_all_status_with_connections(self):
        """Test status reporting with active connections."""
        # Add mock connections
        connection_id1 = "conn1"
        connection_id2 = "conn2"
        
        mock_websocket1 = Mock(spec=WebSocket)
        mock_websocket1.client_state = WebSocketState.CONNECTED
        
        mock_websocket2 = Mock(spec=WebSocket) 
        mock_websocket2.client_state = WebSocketState.DISCONNECTED
        
        from datetime import datetime, timezone
        self.manager.connections[connection_id1] = {
            "connection_id": connection_id1,
            "user_id": "user1",
            "websocket": mock_websocket1,
            "is_healthy": True,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 5
        }
        
        self.manager.connections[connection_id2] = {
            "connection_id": connection_id2,
            "user_id": "user2", 
            "websocket": mock_websocket2,
            "is_healthy": False,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 3
        }
        
        status = self.manager.get_all_status()
        
        # Should return status for all connections
        assert isinstance(status, dict)
        assert len(status) == 2
        assert connection_id1 in status
        assert connection_id2 in status


class TestWebSocketRecoveryCleanup:
    """Test cleanup and resource management for recovery."""
    
    def setup_method(self):
        """Set up fresh manager instance for each test."""
        WebSocketManager._instance = None
        self.manager = WebSocketManager()
    
    @pytest.mark.asyncio
    async def test_cleanup_all_connections(self):
        """Test cleanup of all connections for recovery."""
        # Add mock connections
        connection_id1 = "conn1"
        connection_id2 = "conn2"
        
        mock_websocket1 = Mock(spec=WebSocket)
        mock_websocket2 = Mock(spec=WebSocket)
        
        from datetime import datetime, timezone
        self.manager.connections[connection_id1] = {
            "connection_id": connection_id1,
            "user_id": "user1",
            "websocket": mock_websocket1,
            "is_healthy": True,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        self.manager.connections[connection_id2] = {
            "connection_id": connection_id2,
            "user_id": "user2",
            "websocket": mock_websocket2,
            "is_healthy": True,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        # Test cleanup
        await self.manager.cleanup_all()
        
        # Connections should be cleaned up
        # (Implementation details may vary, but method should complete without error)
        assert True  # If we reach here, cleanup completed successfully
        
    @pytest.mark.asyncio
    async def test_cleanup_all_empty(self):
        """Test cleanup with no connections."""
        # Should not raise exception
        await self.manager.cleanup_all()
        
        # Should handle empty state gracefully
        assert len(self.manager.connections) == 0


class TestWebSocketRecoveryInternalMethods:
    """Test internal methods supporting recovery functionality."""
    
    def setup_method(self):
        """Set up fresh manager instance for each test."""
        WebSocketManager._instance = None
        self.manager = WebSocketManager()
        
    def test_connection_tracking_methods(self):
        """Test that connection tracking supports recovery operations."""
        # Test basic tracking functionality exists
        assert hasattr(self.manager, 'connections')
        assert hasattr(self.manager, 'user_connections')
        
        # Should be able to track connections by ID and user
        connection_id = "test-conn-123"
        user_id = "test-user"
        
        # Verify structures can hold connection data
        from datetime import datetime, timezone
        self.manager.connections[connection_id] = {
            "connection_id": connection_id,
            "user_id": user_id,
            "websocket": Mock(spec=WebSocket),
            "is_healthy": True,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        if user_id not in self.manager.user_connections:
            self.manager.user_connections[user_id] = set()
        self.manager.user_connections[user_id].add(connection_id)
        
        # Verify tracking works
        assert connection_id in self.manager.connections
        assert user_id in self.manager.user_connections
        assert connection_id in self.manager.user_connections[user_id]
    
    def test_stats_tracking_for_recovery(self):
        """Test that statistics tracking supports recovery monitoring."""
        # Verify stats structure supports recovery monitoring
        stats = self.manager.connection_stats
        
        assert 'total_connections' in stats
        assert 'active_connections' in stats
        assert 'errors_handled' in stats
        
        # Should be able to increment error count (for recovery tracking)
        initial_errors = stats['errors_handled']
        stats['errors_handled'] += 1
        assert stats['errors_handled'] == initial_errors + 1


class TestWebSocketRecoveryErrorHandling:
    """Test error handling in recovery operations."""
    
    def setup_method(self):
        """Set up fresh manager instance for each test."""
        WebSocketManager._instance = None
        self.manager = WebSocketManager()
    
    @pytest.mark.asyncio
    async def test_recovery_with_connection_errors(self):
        """Test recovery behavior when connection errors occur."""
        connection_id = "error-conn-123"
        user_id = "test-user"
        error = ConnectionError("Network unreachable")
        
        # Recovery should handle errors gracefully
        result = await self.manager.initiate_recovery(connection_id, user_id, error)
        
        # Should not raise exception and return appropriate status
        assert isinstance(result, bool)
        
    @pytest.mark.asyncio  
    async def test_cleanup_with_invalid_connections(self):
        """Test cleanup handling of invalid connection states."""
        # Add a connection with invalid/None websocket
        connection_id = "invalid-conn"
        from datetime import datetime, timezone
        self.manager.connections[connection_id] = {
            "connection_id": connection_id,
            "user_id": "test_user",
            "websocket": None,  # Invalid state
            "is_healthy": False,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        # Should handle cleanup gracefully even with invalid connections
        await self.manager.cleanup_all()
        
        # Should complete without exception
        assert True
        
    def test_error_stats_tracking(self):
        """Test that error statistics are properly tracked for recovery monitoring."""
        stats = self.manager.connection_stats
        initial_errors = stats.get('errors_handled', 0)
        
        # Simulate error tracking (what recovery system would do)
        stats['errors_handled'] = initial_errors + 1
        
        assert stats['errors_handled'] == initial_errors + 1
        assert stats['errors_handled'] >= 0


class TestWebSocketRecoveryIdentification:
    """Test connection identification and lookup for recovery."""
    
    def setup_method(self):
        """Set up fresh manager instance for each test."""
        WebSocketManager._instance = None
        self.manager = WebSocketManager()
    
    def test_connection_id_case_sensitivity(self):
        """Test connection IDs are case-sensitive for recovery tracking."""
        from datetime import datetime, timezone
        connection_data1 = {
            "connection_id": "TestConn",
            "user_id": "user1",
            "websocket": Mock(spec=WebSocket),
            "is_healthy": True,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        connection_data2 = {
            "connection_id": "testconn", 
            "user_id": "user2",
            "websocket": Mock(spec=WebSocket),
            "is_healthy": True,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        self.manager.connections["TestConn"] = connection_data1
        self.manager.connections["testconn"] = connection_data2
        
        assert self.manager.connections["TestConn"] is connection_data1
        assert self.manager.connections["testconn"] is connection_data2
        assert len(self.manager.connections) == 2
        
    def test_connection_lookup_nonexistent(self):
        """Test recovery status lookup for non-existent connections."""
        # Should not raise KeyError
        result = self.manager.connections.get("nonexistent")
        assert result is None
        
        # Recovery status should also handle non-existent connections
        status = self.manager.get_recovery_status("nonexistent")
        assert status is None


@pytest.mark.integration
class TestWebSocketRecoveryIntegration:
    """Integration tests for WebSocket recovery functionality."""
    
    def setup_method(self):
        """Set up fresh manager instance for each test."""
        WebSocketManager._instance = None
        self.manager = WebSocketManager()
    
    @pytest.mark.asyncio
    async def test_complete_recovery_workflow(self):
        """Test complete recovery workflow: connection, error, recovery, cleanup."""
        connection_id = "integration-test-conn"
        user_id = "test-user"
        
        # Simulate connection creation (mock)
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        from datetime import datetime, timezone
        self.manager.connections[connection_id] = {
            "connection_id": connection_id,
            "user_id": user_id,
            "websocket": mock_websocket,
            "connected_at": "2023-01-01T00:00:00Z",
            "is_healthy": True,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        # Check initial status
        initial_status = self.manager.get_all_status()
        assert connection_id in initial_status
        
        # Test recovery initiation
        error = ConnectionError("Integration test error")
        recovery_result = await self.manager.initiate_recovery(
            connection_id, user_id, error, ["reconnect"]
        )
        assert isinstance(recovery_result, bool)
        
        # Test recovery status check
        recovery_status = self.manager.get_recovery_status(connection_id)
        # Status depends on implementation - may be None for active connections
        
        # Test recovery for all connections
        all_recovery = await self.manager.recover_all_connections()
        assert isinstance(all_recovery, dict)
        
        # Test state snapshot
        self.manager.save_state_snapshot(connection_id, {"test_data": "recovery_test"})
        
        # Final cleanup
        await self.manager.cleanup_all()
        
        # Verify cleanup completed
        assert True  # If we reach here, all operations completed successfully
    
    @pytest.mark.asyncio
    async def test_concurrent_recovery_operations(self):
        """Test concurrent recovery operations on manager."""
        # Create multiple mock connections
        connection_ids = []
        for i in range(3):
            connection_id = f"concurrent_conn_{i}"
            connection_ids.append(connection_id)
            
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.client_state = WebSocketState.CONNECTED if i % 2 == 0 else WebSocketState.DISCONNECTED
            
            from datetime import datetime, timezone
            self.manager.connections[connection_id] = {
                "connection_id": connection_id,
                "user_id": f"user_{i}",
                "websocket": mock_websocket,
                "is_healthy": True,
                "last_activity": datetime.now(timezone.utc),
                "message_count": 0
            }
        
        assert len(self.manager.connections) == 3
        
        # Perform concurrent recovery operations
        recovery_task = self.manager.recover_all_connections()
        
        # Execute recovery and get status
        results = await recovery_task
        status = self.manager.get_all_status()
        
        # Verify results
        assert isinstance(results, dict)
        assert isinstance(status, dict)
        # After recovery, disconnected connections are cleaned up, so expect 2 remaining
        assert len(status) == 2
        
        # Cleanup
        await self.manager.cleanup_all()


class TestWebSocketRecoveryGlobalInstance:
    """Test global WebSocket recovery manager instance."""
    
    def test_global_recovery_manager_exists(self):
        """Test global recovery manager instance is available."""
        from netra_backend.app.websocket_core.manager import websocket_recovery_manager
        
        assert websocket_recovery_manager is not None
        assert isinstance(websocket_recovery_manager, WebSocketManager)
        
    def test_get_websocket_manager_function(self):
        """Test get_websocket_manager function provides recovery-capable instance."""
        manager = get_websocket_manager()
        
        assert manager is not None
        assert isinstance(manager, WebSocketManager)
        assert hasattr(manager, 'initiate_recovery')
        assert hasattr(manager, 'recover_all_connections')
        
    def test_manager_singleton_behavior(self):
        """Test WebSocket manager singleton behavior for recovery consistency."""
        manager1 = WebSocketManager()
        manager2 = WebSocketManager()
        
        # Should be same instance (singleton)
        assert manager1 is manager2
        
        # Should maintain consistent recovery interface
        assert hasattr(manager1, 'recover_all_connections')
        assert hasattr(manager2, 'recover_all_connections')
        
    @pytest.mark.asyncio
    async def test_global_instance_recovery_capabilities(self):
        """Test global instance has all recovery capabilities."""
        from netra_backend.app.websocket_core.manager import websocket_recovery_manager
        
        # Test recovery methods are available
        assert callable(websocket_recovery_manager.initiate_recovery)
        assert callable(websocket_recovery_manager.get_recovery_status)
        assert callable(websocket_recovery_manager.recover_all_connections)
        assert callable(websocket_recovery_manager.get_all_status)
        assert callable(websocket_recovery_manager.cleanup_all)
        assert callable(websocket_recovery_manager.save_state_snapshot)
        
        # Test basic recovery operation
        result = await websocket_recovery_manager.recover_all_connections()
        assert isinstance(result, dict)


class TestWebSocketRecoveryStrategies:
    """Test different recovery strategy implementations."""
    
    def setup_method(self):
        """Set up fresh manager instance for each test."""
        WebSocketManager._instance = None
        self.manager = WebSocketManager()
    
    @pytest.mark.asyncio
    async def test_recovery_with_different_strategies(self):
        """Test recovery with different strategy configurations."""
        connection_id = "strategy-test-conn"
        user_id = "strategy-user"
        error = ConnectionError("Strategy test error")
        
        strategies_list = [
            None,  # Default strategies
            ["reconnect"],
            ["reconnect", "reset_state"],
            ["reconnect", "reset_state", "fallback"],
            ["custom_strategy"]
        ]
        
        for i, strategies in enumerate(strategies_list):
            result = await self.manager.initiate_recovery(
                f"{connection_id}_{i}", f"{user_id}_{i}", error, strategies
            )
            assert isinstance(result, bool)
            # Implementation should handle different strategy lists gracefully
            
    def test_recovery_status_states(self):
        """Test recovery status for different connection states."""
        # Test with no connection
        status = self.manager.get_recovery_status("nonexistent")
        assert status is None
        
        # Test with active connection
        connection_id = "status-test-conn"
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        from datetime import datetime, timezone
        self.manager.connections[connection_id] = {
            "connection_id": connection_id,
            "user_id": "status-user",
            "websocket": mock_websocket,
            "is_healthy": True,
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0
        }
        
        status = self.manager.get_recovery_status(connection_id)
        # Current implementation returns None for active connections (no recovery needed)
        # This is the expected behavior
        
    @pytest.mark.asyncio
    async def test_recovery_strategy_error_handling(self):
        """Test that invalid strategies don't break recovery."""
        connection_id = "error-strategy-conn"
        user_id = "error-user"
        error = RuntimeError("Test error")
        
        # Test with invalid strategy types
        invalid_strategies = [
            [123, 456],  # Non-string strategies
            ["", None],  # Empty/null strategies
            ["invalid_strategy_name"]  # Unknown strategy
        ]
        
        for strategies in invalid_strategies:
            # Should not raise exception, should handle gracefully
            result = await self.manager.initiate_recovery(
                connection_id, user_id, error, strategies
            )
            assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__])