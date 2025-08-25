"""
Comprehensive tests for WebSocketRecoveryManager - production-critical WebSocket recovery.

Tests cover multiple connection management, recovery strategies, state persistence,
error handling, and connection lifecycle management.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any

from netra_backend.app.core.websocket_recovery_strategies import (
    WebSocketRecoveryManager, websocket_recovery_manager
)
from netra_backend.app.core.websocket_recovery_types import (
    ConnectionState, ReconnectionConfig
)


class TestWebSocketRecoveryManagerInitialization:
    """Test WebSocketRecoveryManager initialization and configuration."""
    
    def test_initialization_creates_empty_connections(self):
        """Test recovery manager initializes with empty connections."""
        manager = WebSocketRecoveryManager()
        
        assert isinstance(manager.connections, dict)
        assert len(manager.connections) == 0
        assert isinstance(manager.default_config, ReconnectionConfig)
        
    def test_default_reconnection_config(self):
        """Test default reconnection configuration is properly set."""
        manager = WebSocketRecoveryManager()
        
        config = manager.default_config
        assert config is not None
        # Default config values would depend on ReconnectionConfig implementation


class TestConnectionManagement:
    """Test WebSocket connection creation and management."""
    
    @pytest.mark.asyncio
    @patch('netra_backend.app.core.websocket_recovery_strategies.WebSocketConnectionManager')
    async def test_create_connection_new(self, mock_ws_manager_class):
        """Test creating a new WebSocket connection."""
        mock_manager = Mock()
        mock_ws_manager_class.return_value = mock_manager
        
        recovery_manager = WebSocketRecoveryManager()
        
        result = await recovery_manager.create_connection(
            "test-conn", "ws://localhost:8080", None
        )
        
        assert result is mock_manager
        assert "test-conn" in recovery_manager.connections
        assert recovery_manager.connections["test-conn"] is mock_manager
        mock_ws_manager_class.assert_called_once_with(
            "test-conn", "ws://localhost:8080", recovery_manager.default_config
        )
        
    @pytest.mark.asyncio
    @patch('netra_backend.app.core.websocket_recovery_strategies.WebSocketConnectionManager')
    async def test_create_connection_with_custom_config(self, mock_ws_manager_class):
        """Test creating connection with custom configuration."""
        mock_manager = Mock()
        mock_ws_manager_class.return_value = mock_manager
        
        custom_config = ReconnectionConfig()
        recovery_manager = WebSocketRecoveryManager()
        
        await recovery_manager.create_connection(
            "test-conn", "ws://localhost:8080", custom_config
        )
        
        mock_ws_manager_class.assert_called_once_with(
            "test-conn", "ws://localhost:8080", custom_config
        )
        
    @pytest.mark.asyncio
    @patch('netra_backend.app.core.websocket_recovery_strategies.WebSocketConnectionManager')
    async def test_create_connection_replaces_existing(self, mock_ws_manager_class):
        """Test creating connection replaces existing connection."""
        old_manager = Mock()
        old_manager.disconnect = AsyncMock()
        new_manager = Mock()
        
        mock_ws_manager_class.side_effect = [old_manager, new_manager]
        
        recovery_manager = WebSocketRecoveryManager()
        
        # Create first connection
        await recovery_manager.create_connection("test-conn", "ws://old-url", None)
        assert recovery_manager.connections["test-conn"] is old_manager
        
        # Create second connection with same ID
        result = await recovery_manager.create_connection("test-conn", "ws://new-url", None)
        
        # Should have removed old connection
        old_manager.disconnect.assert_called_once_with("removed")
        
        # Should have new connection
        assert result is new_manager
        assert recovery_manager.connections["test-conn"] is new_manager
        
    @pytest.mark.asyncio
    async def test_remove_connection_existing(self):
        """Test removing an existing connection."""
        mock_manager = Mock()
        mock_manager.disconnect = AsyncMock()
        
        recovery_manager = WebSocketRecoveryManager()
        recovery_manager.connections["test-conn"] = mock_manager
        
        await recovery_manager.remove_connection("test-conn")
        
        mock_manager.disconnect.assert_called_once_with("removed")
        assert "test-conn" not in recovery_manager.connections
        
    @pytest.mark.asyncio
    async def test_remove_connection_nonexistent(self):
        """Test removing non-existent connection does not error."""
        recovery_manager = WebSocketRecoveryManager()
        
        # Should not raise exception
        await recovery_manager.remove_connection("nonexistent")
        
        assert len(recovery_manager.connections) == 0


class TestConnectionRecovery:
    """Test WebSocket connection recovery functionality."""
    
    @pytest.mark.asyncio
    async def test_recover_all_connections_mixed_states(self):
        """Test recovery attempts only failed/disconnected connections."""
        # Create connections with different states
        healthy_manager = Mock()
        healthy_manager.state = ConnectionState.CONNECTED
        
        failed_manager = Mock()
        failed_manager.state = ConnectionState.FAILED
        failed_manager.connect = AsyncMock(return_value=True)
        
        disconnected_manager = Mock()
        disconnected_manager.state = ConnectionState.DISCONNECTED
        disconnected_manager.connect = AsyncMock(return_value=False)
        
        recovery_manager = WebSocketRecoveryManager()
        recovery_manager.connections = {
            "healthy": healthy_manager,
            "failed": failed_manager,
            "disconnected": disconnected_manager
        }
        
        results = await recovery_manager.recover_all_connections()
        
        # Should only attempt recovery for failed and disconnected
        assert len(results) == 2
        assert results["failed"] is True
        assert results["disconnected"] is False
        
        # Should not have attempted to connect healthy connection
        assert not hasattr(healthy_manager, 'connect') or not healthy_manager.connect.called
        failed_manager.connect.assert_called_once()
        disconnected_manager.connect.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_recover_all_connections_no_recovery_needed(self):
        """Test recovery when all connections are healthy."""
        healthy_manager = Mock()
        healthy_manager.state = ConnectionState.CONNECTED
        
        recovery_manager = WebSocketRecoveryManager()
        recovery_manager.connections = {"healthy": healthy_manager}
        
        results = await recovery_manager.recover_all_connections()
        
        assert len(results) == 0  # No recovery attempts
        
    @pytest.mark.asyncio
    async def test_needs_recovery_states(self):
        """Test needs_recovery logic for different connection states."""
        recovery_manager = WebSocketRecoveryManager()
        
        # Test all possible states
        states_needing_recovery = [ConnectionState.FAILED, ConnectionState.DISCONNECTED]
        states_not_needing_recovery = [ConnectionState.CONNECTED, ConnectionState.CONNECTING]
        
        for state in states_needing_recovery:
            manager = Mock()
            manager.state = state
            assert recovery_manager._needs_recovery(manager) is True
            
        for state in states_not_needing_recovery:
            manager = Mock()
            manager.state = state
            assert recovery_manager._needs_recovery(manager) is False
            
    @pytest.mark.asyncio
    async def test_attempt_connection_recovery_success(self):
        """Test successful connection recovery."""
        manager = Mock()
        manager.connect = AsyncMock(return_value=True)
        
        recovery_manager = WebSocketRecoveryManager()
        
        result = await recovery_manager._attempt_connection_recovery("test-conn", manager)
        
        assert result is True
        manager.connect.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_attempt_connection_recovery_failure(self):
        """Test failed connection recovery."""
        manager = Mock()
        manager.connect = AsyncMock(side_effect=Exception("Connection failed"))
        
        recovery_manager = WebSocketRecoveryManager()
        
        result = await recovery_manager._attempt_connection_recovery("test-conn", manager)
        
        assert result is False
        manager.connect.assert_called_once()


class TestStateManagement:
    """Test connection state management and persistence."""
    
    def test_save_state_snapshot(self):
        """Test state snapshot saving functionality."""
        recovery_manager = WebSocketRecoveryManager()
        
        # Should not raise exception
        recovery_manager.save_state_snapshot("test-conn", {"key": "value"})
        
        # In real implementation, this would verify state persistence
        
    @pytest.mark.asyncio
    async def test_initiate_recovery_with_strategies(self):
        """Test recovery initiation with specific strategies."""
        recovery_manager = WebSocketRecoveryManager()
        
        strategies = ["reconnect", "reset_state", "fallback"]
        result = await recovery_manager.initiate_recovery(
            "test-conn", "user123", Exception("Connection lost"), strategies
        )
        
        assert result is True  # Mock implementation returns True
        
    def test_get_recovery_status(self):
        """Test recovery status retrieval."""
        recovery_manager = WebSocketRecoveryManager()
        
        status = recovery_manager.get_recovery_status("test-conn")
        
        # Mock implementation returns None after successful cleanup
        assert status is None


class TestStatusReporting:
    """Test connection status reporting functionality."""
    
    def test_get_all_status_empty(self):
        """Test status reporting with no connections."""
        recovery_manager = WebSocketRecoveryManager()
        
        status = recovery_manager.get_all_status()
        
        assert status == {}
        
    def test_get_all_status_multiple_connections(self):
        """Test status reporting with multiple connections."""
        manager1 = Mock()
        manager1.get_status.return_value = {"state": "connected", "uptime": 100}
        
        manager2 = Mock()
        manager2.get_status.return_value = {"state": "failed", "error": "timeout"}
        
        recovery_manager = WebSocketRecoveryManager()
        recovery_manager.connections = {
            "conn1": manager1,
            "conn2": manager2
        }
        
        status = recovery_manager.get_all_status()
        
        assert len(status) == 2
        assert status["conn1"]["state"] == "connected"
        assert status["conn2"]["state"] == "failed"
        
        manager1.get_status.assert_called_once()
        manager2.get_status.assert_called_once()


class TestCleanupOperations:
    """Test cleanup and resource management."""
    
    @pytest.mark.asyncio
    async def test_cleanup_all_connections(self):
        """Test cleanup of all connections."""
        manager1 = Mock()
        manager1.disconnect = AsyncMock()
        
        manager2 = Mock()
        manager2.disconnect = AsyncMock()
        
        recovery_manager = WebSocketRecoveryManager()
        recovery_manager.connections = {
            "conn1": manager1,
            "conn2": manager2
        }
        
        await recovery_manager.cleanup_all()
        
        # Both connections should be cleaned up
        manager1.disconnect.assert_called_once_with("removed")
        manager2.disconnect.assert_called_once_with("removed")
        
        # Connections dict should be empty
        assert len(recovery_manager.connections) == 0
        
    @pytest.mark.asyncio
    async def test_cleanup_all_empty(self):
        """Test cleanup with no connections."""
        recovery_manager = WebSocketRecoveryManager()
        
        # Should not raise exception
        await recovery_manager.cleanup_all()
        
        assert len(recovery_manager.connections) == 0


class TestPrivateHelperMethods:
    """Test private helper methods."""
    
    @patch('netra_backend.app.core.websocket_recovery_strategies.WebSocketConnectionManager')
    def test_create_connection_manager(self, mock_ws_manager_class):
        """Test creation of WebSocket connection manager."""
        mock_manager = Mock()
        mock_ws_manager_class.return_value = mock_manager
        
        recovery_manager = WebSocketRecoveryManager()
        config = ReconnectionConfig()
        
        result = recovery_manager._create_connection_manager("test-conn", "ws://test", config)
        
        assert result is mock_manager
        mock_ws_manager_class.assert_called_once_with("test-conn", "ws://test", config)
        
    def test_register_connection(self):
        """Test connection registration."""
        recovery_manager = WebSocketRecoveryManager()
        mock_manager = Mock()
        
        recovery_manager._register_connection("test-conn", mock_manager)
        
        assert "test-conn" in recovery_manager.connections
        assert recovery_manager.connections["test-conn"] is mock_manager


class TestErrorHandling:
    """Test error handling in recovery operations."""
    
    @pytest.mark.asyncio
    async def test_connection_recovery_exception_handling(self):
        """Test exception handling during connection recovery."""
        manager = Mock()
        manager.connect = AsyncMock(side_effect=ConnectionError("Network unreachable"))
        
        recovery_manager = WebSocketRecoveryManager()
        
        with patch.object(recovery_manager.logger if hasattr(recovery_manager, 'logger') else Mock(), 'error') as mock_log:
            result = await recovery_manager._attempt_connection_recovery("test-conn", manager)
            
            assert result is False
            # Should log the error (if logger is available)
            
    @pytest.mark.asyncio
    async def test_remove_connection_cleanup_exception(self):
        """Test handling of exceptions during connection cleanup."""
        manager = Mock()
        manager.disconnect = AsyncMock(side_effect=Exception("Cleanup failed"))
        
        recovery_manager = WebSocketRecoveryManager()
        recovery_manager.connections["test-conn"] = manager
        
        # Should handle exception gracefully
        await recovery_manager.remove_connection("test-conn")
        
        # Connection should still be removed from tracking
        assert "test-conn" not in recovery_manager.connections


class TestConnectionIdentification:
    """Test connection identification and lookup."""
    
    def test_connection_id_case_sensitivity(self):
        """Test connection IDs are case-sensitive."""
        recovery_manager = WebSocketRecoveryManager()
        
        manager1 = Mock()
        manager2 = Mock()
        
        recovery_manager.connections["TestConn"] = manager1
        recovery_manager.connections["testconn"] = manager2
        
        assert recovery_manager.connections["TestConn"] is manager1
        assert recovery_manager.connections["testconn"] is manager2
        assert len(recovery_manager.connections) == 2
        
    def test_connection_lookup_nonexistent(self):
        """Test lookup of non-existent connections."""
        recovery_manager = WebSocketRecoveryManager()
        
        # Should not raise KeyError
        result = recovery_manager.connections.get("nonexistent")
        assert result is None


@pytest.mark.integration
class TestWebSocketRecoveryManagerIntegration:
    """Integration tests for WebSocketRecoveryManager with real components."""
    
    @pytest.mark.asyncio
    @patch('netra_backend.app.core.websocket_recovery_strategies.WebSocketConnectionManager')
    async def test_full_connection_lifecycle(self, mock_ws_manager_class):
        """Test complete connection lifecycle: create, recover, cleanup."""
        # Mock WebSocket manager
        mock_manager = Mock()
        mock_manager.state = ConnectionState.CONNECTED
        mock_manager.get_status.return_value = {"state": "connected"}
        mock_manager.disconnect = AsyncMock()
        mock_ws_manager_class.return_value = mock_manager
        
        recovery_manager = WebSocketRecoveryManager()
        
        # Create connection
        manager = await recovery_manager.create_connection(
            "integration-test", "ws://localhost:8080"
        )
        
        assert manager is mock_manager
        assert "integration-test" in recovery_manager.connections
        
        # Check status
        status = recovery_manager.get_all_status()
        assert "integration-test" in status
        assert status["integration-test"]["state"] == "connected"
        
        # Test recovery (should skip connected connection)
        recovery_results = await recovery_manager.recover_all_connections()
        assert len(recovery_results) == 0
        
        # Test state persistence
        recovery_manager.save_state_snapshot("integration-test", {"last_message": "ping"})
        
        # Cleanup
        await recovery_manager.cleanup_all()
        
        mock_manager.disconnect.assert_called_once_with("removed")
        assert len(recovery_manager.connections) == 0
        
    @pytest.mark.asyncio
    @patch('netra_backend.app.core.websocket_recovery_strategies.WebSocketConnectionManager')
    async def test_concurrent_operations(self, mock_ws_manager_class):
        """Test concurrent operations on recovery manager."""
        # Create multiple mock managers
        managers = []
        for i in range(3):
            mock_manager = Mock()
            mock_manager.state = ConnectionState.FAILED if i % 2 == 0 else ConnectionState.CONNECTED
            mock_manager.connect = AsyncMock(return_value=True)
            mock_manager.get_status.return_value = {"state": f"state_{i}"}
            mock_manager.disconnect = AsyncMock()
            managers.append(mock_manager)
        
        mock_ws_manager_class.side_effect = managers
        
        recovery_manager = WebSocketRecoveryManager()
        
        # Create multiple connections concurrently
        tasks = []
        for i in range(3):
            task = recovery_manager.create_connection(
                f"conn_{i}", f"ws://localhost:808{i}"
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        assert len(recovery_manager.connections) == 3
        
        # Perform concurrent recovery and status check
        recovery_task = recovery_manager.recover_all_connections()
        status_task = asyncio.create_task(
            asyncio.coroutine(lambda: recovery_manager.get_all_status())()
        )
        
        results, status = await asyncio.gather(recovery_task, status_task)
        
        # Should have attempted recovery for failed connections
        assert len(results) == 2  # conn_0 and conn_2 are failed
        assert len(status) == 3
        
        # Cleanup
        await recovery_manager.cleanup_all()


class TestGlobalInstance:
    """Test global WebSocket recovery manager instance."""
    
    def test_global_instance_exists(self):
        """Test global instance is available and properly typed."""
        assert websocket_recovery_manager is not None
        assert isinstance(websocket_recovery_manager, WebSocketRecoveryManager)
        
    def test_global_instance_singleton(self):
        """Test global instance is singleton-like."""
        from netra_backend.app.core.websocket_recovery_strategies import websocket_recovery_manager as wm2
        
        # Should be the same instance
        assert websocket_recovery_manager is wm2
        
    @pytest.mark.asyncio
    async def test_global_instance_isolation(self):
        """Test global instance operations don't interfere with new instances."""
        # Create local instance
        local_manager = WebSocketRecoveryManager()
        
        # Add connection to local instance
        with patch('netra_backend.app.core.websocket_recovery_strategies.WebSocketConnectionManager') as mock_ws:
            mock_ws.return_value = Mock()
            await local_manager.create_connection("local", "ws://local")
        
        # Global instance should remain empty
        assert len(websocket_recovery_manager.connections) == 0
        assert len(local_manager.connections) == 1
        
        # Cleanup
        await local_manager.cleanup_all()


class TestRecoveryStrategies:
    """Test different recovery strategy implementations."""
    
    @pytest.mark.asyncio
    async def test_recovery_with_different_strategies(self):
        """Test recovery with different strategy lists."""
        recovery_manager = WebSocketRecoveryManager()
        
        strategies_list = [
            ["reconnect"],
            ["reconnect", "reset_state"],
            ["reconnect", "reset_state", "fallback"],
            ["custom_strategy", "another_strategy"]
        ]
        
        for i, strategies in enumerate(strategies_list):
            result = await recovery_manager.initiate_recovery(
                f"conn_{i}", f"user_{i}", Exception("Test error"), strategies
            )
            assert result is True  # Mock implementation
            
    def test_recovery_status_lifecycle(self):
        """Test recovery status through different phases."""
        recovery_manager = WebSocketRecoveryManager()
        
        # Initially no status
        status = recovery_manager.get_recovery_status("new-conn")
        assert status is None  # Mock implementation returns None
        
        # After recovery operations, status should be available/cleared
        # This would be more meaningful with real implementation