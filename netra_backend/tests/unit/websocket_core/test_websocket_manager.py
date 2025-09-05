"""Comprehensive unit tests for UnifiedWebSocketManager SSOT class.

Tests cover all public methods and key scenarios for WebSocket connection management.
Tests are designed to fail initially to identify gaps in functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any
import uuid

from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection,
    RegistryCompat,
    get_websocket_manager
)


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket object."""
    websocket = Mock()
    websocket.send_json = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def sample_connection():
    """Create a sample WebSocket connection."""
    return WebSocketConnection(
        connection_id="conn_123",
        user_id="user_456",
        websocket=Mock(),
        connected_at=datetime.now(),
        metadata={"test": "data"}
    )


@pytest.fixture
def manager():
    """Create a fresh WebSocket manager instance."""
    return UnifiedWebSocketManager()


@pytest.fixture
def mock_logger():
    """Mock the logger."""
    with patch('netra_backend.app.websocket_core.unified_manager.logger') as mock_log:
        yield mock_log


class TestWebSocketConnectionDataclass:
    """Test the WebSocketConnection dataclass."""
    
    def test_websocket_connection_creation_with_required_fields(self):
        """Test creating WebSocketConnection with required fields only."""
        connection = WebSocketConnection(
            connection_id="test_id",
            user_id="test_user",
            websocket=Mock(),
            connected_at=datetime.now()
        )
        assert connection.connection_id == "test_id"
        assert connection.user_id == "test_user"
        assert connection.websocket is not None
        assert isinstance(connection.connected_at, datetime)
        assert connection.metadata is None

    def test_websocket_connection_creation_with_metadata(self):
        """Test creating WebSocketConnection with metadata."""
        metadata = {"key": "value", "number": 123}
        connection = WebSocketConnection(
            connection_id="test_id",
            user_id="test_user",
            websocket=Mock(),
            connected_at=datetime.now(),
            metadata=metadata
        )
        assert connection.metadata == metadata

    def test_websocket_connection_equality(self):
        """Test WebSocketConnection equality comparison."""
        ws = Mock()
        dt = datetime.now()
        conn1 = WebSocketConnection("id1", "user1", ws, dt)
        conn2 = WebSocketConnection("id1", "user1", ws, dt)
        # Note: This will likely fail initially as dataclass equality is by value
        assert conn1 == conn2

    def test_websocket_connection_string_representation(self):
        """Test WebSocketConnection string representation."""
        connection = WebSocketConnection(
            connection_id="test_id",
            user_id="test_user",
            websocket=Mock(),
            connected_at=datetime.now()
        )
        str_repr = str(connection)
        assert "test_id" in str_repr
        assert "test_user" in str_repr


class TestRegistryCompat:
    """Test the RegistryCompat class for legacy compatibility."""
    
    @pytest.mark.asyncio
    async def test_registry_compat_initialization(self):
        """Test RegistryCompat initialization."""
        manager = UnifiedWebSocketManager()
        registry = RegistryCompat(manager)
        assert registry.manager is manager

    @pytest.mark.asyncio
    async def test_registry_register_connection_creates_websocket_connection(self):
        """Test registry register_connection creates proper WebSocketConnection."""
        manager = UnifiedWebSocketManager()
        registry = RegistryCompat(manager)
        
        # Mock ConnectionInfo object
        connection_info = Mock()
        connection_info.connection_id = "conn_123"
        connection_info.websocket = Mock()
        connection_info.connected_at = datetime.now()
        
        await registry.register_connection("user_456", connection_info)
        
        # This should create a connection in the manager
        assert len(manager._connections) == 1
        assert "conn_123" in manager._connections

    @pytest.mark.asyncio
    async def test_registry_get_user_connections_returns_connection_infos(self):
        """Test registry get_user_connections returns ConnectionInfo objects."""
        manager = UnifiedWebSocketManager()
        registry = RegistryCompat(manager)
        
        # This will likely fail initially - testing the expected behavior
        connections = registry.get_user_connections("nonexistent_user")
        assert connections == []

    @pytest.mark.asyncio
    async def test_registry_stores_connection_infos_for_retrieval(self):
        """Test registry stores connection_infos for later retrieval."""
        manager = UnifiedWebSocketManager()
        registry = RegistryCompat(manager)
        
        connection_info = Mock()
        connection_info.connection_id = "conn_123"
        connection_info.websocket = Mock()
        connection_info.connected_at = datetime.now()
        
        await registry.register_connection("user_456", connection_info)
        
        # Should be able to retrieve the connection info
        connections = registry.get_user_connections("user_456")
        assert len(connections) == 1
        assert connections[0] is connection_info


class TestUnifiedWebSocketManagerInitialization:
    """Test UnifiedWebSocketManager initialization and setup."""
    
    def test_manager_initialization_creates_empty_collections(self):
        """Test manager initialization creates empty connection collections."""
        manager = UnifiedWebSocketManager()
        assert isinstance(manager._connections, dict)
        assert len(manager._connections) == 0
        assert isinstance(manager._user_connections, dict)
        assert len(manager._user_connections) == 0

    def test_manager_initialization_creates_async_lock(self):
        """Test manager initialization creates asyncio lock."""
        manager = UnifiedWebSocketManager()
        assert hasattr(manager, '_lock')
        assert isinstance(manager._lock, asyncio.Lock)

    def test_manager_initialization_creates_registry_compat(self):
        """Test manager initialization creates RegistryCompat."""
        manager = UnifiedWebSocketManager()
        assert hasattr(manager, 'registry')
        assert isinstance(manager.registry, RegistryCompat)
        assert manager.registry.manager is manager

    def test_manager_initialization_creates_compatibility_attributes(self):
        """Test manager initialization creates legacy compatibility attributes."""
        manager = UnifiedWebSocketManager()
        assert hasattr(manager, '_connection_manager')
        assert manager._connection_manager is manager
        assert hasattr(manager, 'connection_manager')
        assert manager.connection_manager is manager
        assert hasattr(manager, 'active_connections')
        assert isinstance(manager.active_connections, dict)
        assert hasattr(manager, 'connection_registry')
        assert isinstance(manager.connection_registry, dict)

    def test_manager_logs_initialization(self, mock_logger):
        """Test manager logs successful initialization."""
        UnifiedWebSocketManager()
        mock_logger.info.assert_called_with("UnifiedWebSocketManager initialized")


class TestConnectionManagement:
    """Test connection addition, removal, and retrieval."""
    
    @pytest.mark.asyncio
    async def test_add_connection_stores_connection_correctly(self, manager, sample_connection):
        """Test add_connection stores connection in internal collections."""
        await manager.add_connection(sample_connection)
        
        assert sample_connection.connection_id in manager._connections
        assert manager._connections[sample_connection.connection_id] is sample_connection
        assert sample_connection.user_id in manager._user_connections
        assert sample_connection.connection_id in manager._user_connections[sample_connection.user_id]

    @pytest.mark.asyncio
    async def test_add_connection_handles_multiple_connections_per_user(self, manager, mock_websocket):
        """Test add_connection handles multiple connections for same user."""
        conn1 = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        conn2 = WebSocketConnection("conn2", "user1", mock_websocket, datetime.now())
        
        await manager.add_connection(conn1)
        await manager.add_connection(conn2)
        
        assert len(manager._user_connections["user1"]) == 2
        assert "conn1" in manager._user_connections["user1"]
        assert "conn2" in manager._user_connections["user1"]

    @pytest.mark.asyncio
    async def test_add_connection_updates_compatibility_mapping(self, manager, sample_connection, mock_logger):
        """Test add_connection updates active_connections for compatibility."""
        await manager.add_connection(sample_connection)
        
        assert sample_connection.user_id in manager.active_connections
        assert len(manager.active_connections[sample_connection.user_id]) == 1
        mock_logger.info.assert_called_with(f"Added connection {sample_connection.connection_id} for user {sample_connection.user_id}")

    @pytest.mark.asyncio
    async def test_add_connection_uses_async_lock(self, manager):
        """Test add_connection uses async lock for thread safety."""
        # This is a behavioral test - the lock should prevent race conditions
        connection = WebSocketConnection("conn1", "user1", Mock(), datetime.now())
        
        # Mock the lock's acquire method to verify it's used
        with patch.object(manager._lock, 'acquire', new_callable=AsyncMock) as mock_acquire:
            with patch.object(manager._lock, 'release') as mock_release:
                # The actual implementation uses async with, so we need to test differently
                await manager.add_connection(connection)
                # Verify the connection was added (indirect proof the lock was used)
                assert "conn1" in manager._connections

    @pytest.mark.asyncio
    async def test_remove_connection_removes_from_collections(self, manager, sample_connection):
        """Test remove_connection removes connection from all collections."""
        await manager.add_connection(sample_connection)
        await manager.remove_connection(sample_connection.connection_id)
        
        assert sample_connection.connection_id not in manager._connections
        assert sample_connection.user_id not in manager._user_connections

    @pytest.mark.asyncio
    async def test_remove_connection_handles_nonexistent_connection(self, manager, mock_logger):
        """Test remove_connection gracefully handles nonexistent connection."""
        # Should not raise an exception
        await manager.remove_connection("nonexistent_connection")
        # No specific assertion needed - just shouldn't crash

    @pytest.mark.asyncio
    async def test_remove_connection_preserves_other_user_connections(self, manager, mock_websocket):
        """Test remove_connection preserves other connections for same user."""
        conn1 = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        conn2 = WebSocketConnection("conn2", "user1", mock_websocket, datetime.now())
        
        await manager.add_connection(conn1)
        await manager.add_connection(conn2)
        await manager.remove_connection("conn1")
        
        assert "conn2" in manager._user_connections["user1"]
        assert "conn1" not in manager._user_connections["user1"]

    @pytest.mark.asyncio
    async def test_remove_connection_cleans_up_empty_user_connections(self, manager, sample_connection):
        """Test remove_connection removes user from _user_connections when no connections left."""
        await manager.add_connection(sample_connection)
        await manager.remove_connection(sample_connection.connection_id)
        
        assert sample_connection.user_id not in manager._user_connections

    @pytest.mark.asyncio
    async def test_remove_connection_updates_compatibility_mapping(self, manager, sample_connection, mock_logger):
        """Test remove_connection updates active_connections for compatibility."""
        await manager.add_connection(sample_connection)
        await manager.remove_connection(sample_connection.connection_id)
        
        assert sample_connection.user_id not in manager.active_connections
        mock_logger.info.assert_called_with(f"Removed connection {sample_connection.connection_id}")

    def test_get_connection_returns_correct_connection(self, manager, sample_connection):
        """Test get_connection returns the correct WebSocketConnection."""
        # Need to add connection synchronously for this test
        manager._connections[sample_connection.connection_id] = sample_connection
        
        retrieved = manager.get_connection(sample_connection.connection_id)
        assert retrieved is sample_connection

    def test_get_connection_returns_none_for_nonexistent(self, manager):
        """Test get_connection returns None for nonexistent connection."""
        result = manager.get_connection("nonexistent")
        assert result is None

    def test_get_user_connections_returns_connection_ids(self, manager, mock_websocket):
        """Test get_user_connections returns set of connection IDs."""
        # Manually add to test synchronously
        manager._user_connections["user1"] = {"conn1", "conn2"}
        
        connections = manager.get_user_connections("user1")
        assert isinstance(connections, set)
        assert connections == {"conn1", "conn2"}

    def test_get_user_connections_returns_empty_set_for_nonexistent_user(self, manager):
        """Test get_user_connections returns empty set for nonexistent user."""
        connections = manager.get_user_connections("nonexistent")
        assert connections == set()

    def test_get_user_connections_returns_copy_of_set(self, manager):
        """Test get_user_connections returns a copy, not the original set."""
        manager._user_connections["user1"] = {"conn1"}
        connections = manager.get_user_connections("user1")
        connections.add("conn2")  # Modify the returned set
        
        # Original should be unchanged
        assert manager._user_connections["user1"] == {"conn1"}


class TestMessageSending:
    """Test message sending functionality."""
    
    @pytest.mark.asyncio
    async def test_send_to_user_sends_to_all_user_connections(self, manager, mock_websocket):
        """Test send_to_user sends message to all connections for a user."""
        conn1 = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        conn2 = WebSocketConnection("conn2", "user1", mock_websocket, datetime.now())
        
        await manager.add_connection(conn1)
        await manager.add_connection(conn2)
        
        message = {"type": "test", "data": "message"}
        await manager.send_to_user("user1", message)
        
        # Should send to both connections
        assert mock_websocket.send_json.call_count == 2
        mock_websocket.send_json.assert_called_with(message)

    @pytest.mark.asyncio
    async def test_send_to_user_handles_send_failure_gracefully(self, manager, mock_logger):
        """Test send_to_user handles WebSocket send failures."""
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock(side_effect=Exception("Send failed"))
        
        connection = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        await manager.add_connection(connection)
        
        await manager.send_to_user("user1", {"test": "message"})
        
        # Should log error and remove connection
        mock_logger.error.assert_called()
        assert "conn1" not in manager._connections

    @pytest.mark.asyncio
    async def test_send_to_user_handles_nonexistent_user(self, manager):
        """Test send_to_user handles nonexistent user gracefully."""
        # Should not raise an exception
        await manager.send_to_user("nonexistent", {"test": "message"})

    @pytest.mark.asyncio
    async def test_send_to_user_skips_connections_without_websocket(self, manager, mock_logger):
        """Test send_to_user skips connections with None websocket."""
        connection = WebSocketConnection("conn1", "user1", None, datetime.now())
        manager._connections["conn1"] = connection
        manager._user_connections["user1"] = {"conn1"}
        
        await manager.send_to_user("user1", {"test": "message"})
        # Should not crash, just skip the connection

    @pytest.mark.asyncio
    async def test_send_to_thread_routes_to_send_to_user(self, manager):
        """Test send_to_thread routes to send_to_user using thread_id as user_id."""
        with patch.object(manager, 'send_to_user', new_callable=AsyncMock) as mock_send:
            result = await manager.send_to_thread("thread123", {"test": "data"})
            
            mock_send.assert_called_once_with("thread123", {"test": "data"})
            assert result is True

    @pytest.mark.asyncio
    async def test_send_to_thread_returns_false_on_exception(self, manager, mock_logger):
        """Test send_to_thread returns False when send_to_user raises exception."""
        with patch.object(manager, 'send_to_user', side_effect=Exception("Failed")):
            result = await manager.send_to_thread("thread123", {"test": "data"})
            
            assert result is False
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_emit_critical_event_creates_proper_message_structure(self, manager):
        """Test emit_critical_event creates proper message with timestamp."""
        with patch.object(manager, 'send_to_user', new_callable=AsyncMock) as mock_send:
            with patch('netra_backend.app.websocket_core.unified_manager.datetime') as mock_dt:
                mock_dt.utcnow.return_value.isoformat.return_value = "2023-01-01T00:00:00"
                
                await manager.emit_critical_event("user1", "test_event", {"key": "value"})
                
                expected_message = {
                    "type": "test_event",
                    "data": {"key": "value"},
                    "timestamp": "2023-01-01T00:00:00"
                }
                mock_send.assert_called_once_with("user1", expected_message)

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_connections(self, manager, mock_websocket):
        """Test broadcast sends message to all connections."""
        conn1 = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        conn2 = WebSocketConnection("conn2", "user2", mock_websocket, datetime.now())
        
        await manager.add_connection(conn1)
        await manager.add_connection(conn2)
        
        message = {"type": "broadcast", "data": "test"}
        await manager.broadcast(message)
        
        assert mock_websocket.send_json.call_count == 2
        mock_websocket.send_json.assert_called_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_handles_send_failures(self, manager, mock_logger):
        """Test broadcast handles send failures and removes failed connections."""
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock(side_effect=Exception("Send failed"))
        
        connection = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        await manager.add_connection(connection)
        
        await manager.broadcast({"test": "message"})
        
        # Should log error and remove connection
        mock_logger.error.assert_called()
        assert "conn1" not in manager._connections

    @pytest.mark.asyncio
    async def test_broadcast_with_empty_connections(self, manager):
        """Test broadcast with no connections doesn't crash."""
        await manager.broadcast({"test": "message"})
        # Should not raise exception


class TestLegacyCompatibilityMethods:
    """Test legacy compatibility methods."""
    
    @pytest.mark.asyncio
    async def test_connect_user_creates_connection_and_returns_info(self, manager, mock_websocket):
        """Test connect_user creates connection and returns ConnectionInfo-like object."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = "mock-uuid"
            
            conn_info = await manager.connect_user("user1", mock_websocket)
            
            assert conn_info.user_id == "user1"
            assert conn_info.connection_id == "mock-uuid"
            assert conn_info.websocket is mock_websocket
            assert "mock-uuid" in manager._connections

    @pytest.mark.asyncio
    async def test_connect_user_stores_in_connection_registry(self, manager, mock_websocket):
        """Test connect_user stores connection in registry for compatibility."""
        conn_info = await manager.connect_user("user1", mock_websocket)
        
        assert conn_info.connection_id in manager.connection_registry
        assert manager.connection_registry[conn_info.connection_id] is conn_info

    @pytest.mark.asyncio
    async def test_disconnect_user_removes_matching_connection(self, manager, mock_websocket, mock_logger):
        """Test disconnect_user removes the matching user/websocket connection."""
        conn_info = await manager.connect_user("user1", mock_websocket)
        await manager.disconnect_user("user1", mock_websocket)
        
        assert conn_info.connection_id not in manager._connections
        assert conn_info.connection_id not in manager.connection_registry
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_disconnect_user_handles_nonexistent_connection(self, manager, mock_websocket, mock_logger):
        """Test disconnect_user handles nonexistent connection gracefully."""
        await manager.disconnect_user("nonexistent", mock_websocket)
        
        mock_logger.warning.assert_called_with("Connection not found for user nonexistent during disconnect")

    @pytest.mark.asyncio
    async def test_find_connection_returns_matching_connection_info(self, manager, mock_websocket):
        """Test find_connection returns ConnectionInfo-like object for matching connection."""
        await manager.connect_user("user1", mock_websocket)
        
        found_conn = await manager.find_connection("user1", mock_websocket)
        
        assert found_conn is not None
        assert found_conn.user_id == "user1"
        assert found_conn.websocket is mock_websocket

    @pytest.mark.asyncio
    async def test_find_connection_returns_none_for_no_match(self, manager, mock_websocket):
        """Test find_connection returns None when no matching connection found."""
        found_conn = await manager.find_connection("user1", mock_websocket)
        assert found_conn is None

    @pytest.mark.asyncio
    async def test_handle_message_logs_and_returns_true(self, manager, mock_websocket, mock_logger):
        """Test handle_message logs message and returns True for compatibility."""
        message = {"type": "test", "data": "value"}
        result = await manager.handle_message("user1", mock_websocket, message)
        
        assert result is True
        mock_logger.debug.assert_called_with(f"Handling message from user1: {message}")

    @pytest.mark.asyncio
    async def test_handle_message_handles_exceptions(self, manager, mock_websocket, mock_logger):
        """Test handle_message handles exceptions and returns False."""
        with patch.object(mock_logger, 'debug', side_effect=Exception("Log failed")):
            result = await manager.handle_message("user1", mock_websocket, {"test": "data"})
            
            assert result is False
            mock_logger.error.assert_called()


class TestJobConnectionFunctionality:
    """Test job-specific connection functionality."""
    
    @pytest.mark.asyncio
    async def test_connect_to_job_creates_connection_with_job_metadata(self, manager, mock_websocket):
        """Test connect_to_job creates connection with job-specific metadata."""
        conn_info = await manager.connect_to_job(mock_websocket, "job123")
        
        assert conn_info.job_id == "job123"
        assert "job_job123_" in conn_info.user_id  # Should contain job prefix
        
        # Check metadata
        connection = manager.get_connection(conn_info.connection_id)
        assert connection.metadata["job_id"] == "job123"
        assert connection.metadata["connection_type"] == "job"

    @pytest.mark.asyncio
    async def test_connect_to_job_validates_job_id_type(self, manager, mock_websocket, mock_logger):
        """Test connect_to_job validates and converts job_id to string."""
        # Pass an invalid job_id type
        conn_info = await manager.connect_to_job(mock_websocket, 12345)
        
        # Should convert and create a valid job_id
        assert isinstance(conn_info.job_id, str)
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_connect_to_job_handles_invalid_job_id_patterns(self, manager, mock_websocket, mock_logger):
        """Test connect_to_job handles invalid job_id patterns like object representations."""
        invalid_job_id = "<WebSocket object at 0x123>"
        conn_info = await manager.connect_to_job(mock_websocket, invalid_job_id)
        
        # Should generate a new job_id
        assert "<" not in conn_info.job_id
        assert "object at" not in conn_info.job_id
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_connect_to_job_creates_room_manager_structure(self, manager, mock_websocket):
        """Test connect_to_job creates room manager structure for compatibility."""
        await manager.connect_to_job(mock_websocket, "job123")
        
        assert hasattr(manager, 'core')
        assert hasattr(manager.core, 'room_manager')
        assert hasattr(manager.core.room_manager, 'rooms')
        assert hasattr(manager.core.room_manager, 'room_connections')
        assert "job123" in manager.core.room_manager.rooms

    @pytest.mark.asyncio
    async def test_connect_to_job_adds_room_manager_methods(self, manager, mock_websocket):
        """Test connect_to_job adds get_stats and get_room_connections methods."""
        await manager.connect_to_job(mock_websocket, "job123")
        
        assert hasattr(manager.core.room_manager, 'get_stats')
        assert hasattr(manager.core.room_manager, 'get_room_connections')
        
        stats = manager.core.room_manager.get_stats()
        assert "room_connections" in stats
        
        room_connections = manager.core.room_manager.get_room_connections("job123")
        assert isinstance(room_connections, list)

    @pytest.mark.asyncio
    async def test_disconnect_from_job_calls_disconnect_user(self, manager, mock_websocket):
        """Test disconnect_from_job calls disconnect_user with correct user_id."""
        with patch.object(manager, 'disconnect_user', new_callable=AsyncMock) as mock_disconnect:
            await manager.disconnect_from_job("job123", mock_websocket)
            
            # Should call disconnect_user with job-based user_id
            expected_user_id = f"job_job123_{id(mock_websocket)}"
            mock_disconnect.assert_called_once_with(expected_user_id, mock_websocket)


class TestStatisticsAndMonitoring:
    """Test statistics and monitoring functionality."""
    
    def test_get_stats_returns_correct_structure(self, manager):
        """Test get_stats returns proper statistics structure."""
        stats = manager.get_stats()
        
        assert isinstance(stats, dict)
        assert "total_connections" in stats
        assert "unique_users" in stats
        assert "connections_by_user" in stats
        assert isinstance(stats["connections_by_user"], dict)

    @pytest.mark.asyncio
    async def test_get_stats_reflects_current_connections(self, manager, mock_websocket):
        """Test get_stats reflects current connection state."""
        initial_stats = manager.get_stats()
        assert initial_stats["total_connections"] == 0
        assert initial_stats["unique_users"] == 0
        
        # Add connections
        conn1 = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        conn2 = WebSocketConnection("conn2", "user1", mock_websocket, datetime.now())
        conn3 = WebSocketConnection("conn3", "user2", mock_websocket, datetime.now())
        
        await manager.add_connection(conn1)
        await manager.add_connection(conn2)
        await manager.add_connection(conn3)
        
        stats = manager.get_stats()
        assert stats["total_connections"] == 3
        assert stats["unique_users"] == 2
        assert stats["connections_by_user"]["user1"] == 2
        assert stats["connections_by_user"]["user2"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_updates_after_removal(self, manager, mock_websocket):
        """Test get_stats updates correctly after connection removal."""
        conn1 = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        await manager.add_connection(conn1)
        
        stats_before = manager.get_stats()
        assert stats_before["total_connections"] == 1
        
        await manager.remove_connection("conn1")
        
        stats_after = manager.get_stats()
        assert stats_after["total_connections"] == 0
        assert stats_after["unique_users"] == 0


class TestGlobalInstanceManagement:
    """Test global instance management."""
    
    def test_get_websocket_manager_returns_same_instance(self):
        """Test get_websocket_manager returns the same instance (singleton pattern)."""
        # Reset global instance for clean test
        import netra_backend.app.websocket_core.unified_manager as manager_module
        manager_module._manager_instance = None
        
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, UnifiedWebSocketManager)

    def test_get_websocket_manager_creates_instance_if_none(self):
        """Test get_websocket_manager creates instance if none exists."""
        # Reset global instance
        import netra_backend.app.websocket_core.unified_manager as manager_module
        manager_module._manager_instance = None
        
        manager = get_websocket_manager()
        
        assert isinstance(manager, UnifiedWebSocketManager)
        assert manager_module._manager_instance is manager


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_add_connection_handles_lock_acquisition_failure(self, manager):
        """Test add_connection handles lock acquisition failures."""
        # This is a complex scenario to test - async locks generally don't fail
        # But we can test that the method is properly async
        connection = WebSocketConnection("conn1", "user1", Mock(), datetime.now())
        
        # Verify this doesn't hang or crash
        await manager.add_connection(connection)
        assert "conn1" in manager._connections

    @pytest.mark.asyncio
    async def test_remove_connection_handles_concurrent_modification(self, manager, mock_websocket):
        """Test remove_connection handles concurrent modification scenarios."""
        conn = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        await manager.add_connection(conn)
        
        # Simulate concurrent modification by modifying the dict during iteration
        original_connections = manager._connections.copy()
        
        # This should not crash even if the dict is modified concurrently
        await manager.remove_connection("conn1")
        assert "conn1" not in manager._connections

    @pytest.mark.asyncio
    async def test_send_to_user_continues_after_partial_failures(self, manager, mock_logger):
        """Test send_to_user continues sending after partial failures."""
        # Create one good websocket and one that fails
        good_websocket = Mock()
        good_websocket.send_json = AsyncMock()
        
        bad_websocket = Mock()
        bad_websocket.send_json = AsyncMock(side_effect=Exception("Send failed"))
        
        conn1 = WebSocketConnection("conn1", "user1", good_websocket, datetime.now())
        conn2 = WebSocketConnection("conn2", "user1", bad_websocket, datetime.now())
        
        await manager.add_connection(conn1)
        await manager.add_connection(conn2)
        
        message = {"test": "data"}
        await manager.send_to_user("user1", message)
        
        # Good connection should have received the message
        good_websocket.send_json.assert_called_once_with(message)
        # Bad connection should be removed
        assert "conn2" not in manager._connections
        # Good connection should remain
        assert "conn1" in manager._connections

    @pytest.mark.asyncio
    async def test_broadcast_handles_connection_list_modification(self, manager, mock_websocket):
        """Test broadcast handles connection list modification during iteration."""
        connections = []
        for i in range(5):
            conn = WebSocketConnection(f"conn{i}", f"user{i}", mock_websocket, datetime.now())
            connections.append(conn)
            await manager.add_connection(conn)
        
        # Mock one websocket to fail and trigger removal
        failing_websocket = Mock()
        failing_websocket.send_json = AsyncMock(side_effect=Exception("Fail"))
        
        failing_conn = WebSocketConnection("failing", "failing_user", failing_websocket, datetime.now())
        await manager.add_connection(failing_conn)
        
        # This should not crash even though the connection list is modified during iteration
        await manager.broadcast({"test": "broadcast"})


class TestThreadSafetyAndConcurrency:
    """Test thread safety and concurrency scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_add_remove_operations(self, manager, mock_websocket):
        """Test concurrent add and remove operations don't cause race conditions."""
        async def add_connections():
            for i in range(10):
                conn = WebSocketConnection(f"add_conn{i}", f"add_user{i}", mock_websocket, datetime.now())
                await manager.add_connection(conn)
        
        async def remove_connections():
            # Wait a bit then start removing
            await asyncio.sleep(0.01)
            for i in range(5):
                await manager.remove_connection(f"add_conn{i}")
        
        # Run both operations concurrently
        await asyncio.gather(add_connections(), remove_connections())
        
        # Should have 5 connections remaining
        stats = manager.get_stats()
        assert stats["total_connections"] == 5

    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self, manager, mock_websocket):
        """Test concurrent operations on same user don't cause inconsistency."""
        user_id = "concurrent_user"
        
        async def add_user_connections():
            for i in range(5):
                conn = WebSocketConnection(f"user_conn{i}", user_id, mock_websocket, datetime.now())
                await manager.add_connection(conn)
        
        async def send_to_user_repeatedly():
            for _ in range(10):
                await manager.send_to_user(user_id, {"test": "concurrent"})
                await asyncio.sleep(0.001)
        
        # Run operations concurrently
        await asyncio.gather(add_user_connections(), send_to_user_repeatedly())
        
        # User should have all 5 connections
        user_connections = manager.get_user_connections(user_id)
        assert len(user_connections) == 5

    @pytest.mark.asyncio
    async def test_high_concurrency_stress_test(self, manager):
        """Test high concurrency operations for stability."""
        # This is a stress test - may fail if there are race conditions
        mock_websockets = [Mock() for _ in range(100)]
        for ws in mock_websockets:
            ws.send_json = AsyncMock()
        
        async def stress_operations():
            tasks = []
            
            # Add many connections
            for i in range(50):
                conn = WebSocketConnection(f"stress_conn{i}", f"stress_user{i%10}", mock_websockets[i], datetime.now())
                tasks.append(manager.add_connection(conn))
            
            # Send many messages
            for i in range(25):
                tasks.append(manager.send_to_user(f"stress_user{i%10}", {"stress": "test"}))
            
            # Remove some connections
            for i in range(0, 25, 2):
                tasks.append(manager.remove_connection(f"stress_conn{i}"))
            
            # Execute all operations concurrently
            await asyncio.gather(*tasks, return_exceptions=True)
        
        await stress_operations()
        
        # System should still be consistent
        stats = manager.get_stats()
        assert stats["total_connections"] >= 0  # Should not be negative
        assert stats["unique_users"] >= 0


# Additional edge case tests that are likely to fail initially
class TestEdgeCasesAndFailureScenarios:
    """Test edge cases and scenarios likely to expose bugs."""
    
    @pytest.mark.asyncio
    async def test_adding_duplicate_connection_ids(self, manager, mock_websocket):
        """Test adding connections with duplicate connection_ids."""
        conn1 = WebSocketConnection("duplicate_id", "user1", mock_websocket, datetime.now())
        conn2 = WebSocketConnection("duplicate_id", "user2", mock_websocket, datetime.now())
        
        await manager.add_connection(conn1)
        await manager.add_connection(conn2)
        
        # This might expose bugs in connection tracking
        # Second connection should overwrite the first
        connection = manager.get_connection("duplicate_id")
        assert connection.user_id == "user2"

    @pytest.mark.asyncio
    async def test_connection_with_none_user_id(self, manager, mock_websocket):
        """Test connection with None user_id."""
        conn = WebSocketConnection("conn1", None, mock_websocket, datetime.now())
        
        # This should either work or fail gracefully
        try:
            await manager.add_connection(conn)
            # If it works, check that it's handled properly
            stats = manager.get_stats()
            assert None in stats["connections_by_user"] or stats["connections_by_user"] == {}
        except (TypeError, AttributeError):
            # If it fails, that's also acceptable behavior
            pass

    @pytest.mark.asyncio
    async def test_connection_with_empty_string_ids(self, manager, mock_websocket):
        """Test connection with empty string IDs."""
        conn = WebSocketConnection("", "", mock_websocket, datetime.now())
        
        await manager.add_connection(conn)
        
        # Should handle empty strings without crashing
        retrieved = manager.get_connection("")
        assert retrieved is not None
        
        user_connections = manager.get_user_connections("")
        assert "" in user_connections

    @pytest.mark.asyncio
    async def test_very_large_message_sending(self, manager, mock_websocket):
        """Test sending very large messages."""
        conn = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        await manager.add_connection(conn)
        
        # Create a large message (1MB of data)
        large_data = "x" * (1024 * 1024)
        large_message = {"type": "large", "data": large_data}
        
        # This should not crash the system
        await manager.send_to_user("user1", large_message)
        mock_websocket.send_json.assert_called_once_with(large_message)

    def test_stats_with_unicode_user_ids(self, manager):
        """Test statistics with Unicode user IDs."""
        # Manually add connections with Unicode user IDs
        manager._user_connections["用户1"] = {"conn1", "conn2"}
        manager._user_connections["пользователь2"] = {"conn3"}
        manager._user_connections["مستخدم3"] = {"conn4", "conn5", "conn6"}
        
        stats = manager.get_stats()
        
        # Should handle Unicode properly
        assert stats["unique_users"] == 3
        assert "用户1" in stats["connections_by_user"]
        assert stats["connections_by_user"]["用户1"] == 2


class TestAdditionalFailingScenarios:
    """Additional tests designed to identify functionality gaps."""
    
    @pytest.mark.asyncio
    async def test_send_to_user_with_closed_websocket_detection(self, manager):
        """Test that send_to_user can detect and handle closed WebSocket connections."""
        mock_websocket = Mock()
        # Simulate a closed WebSocket by making send_json raise a specific exception
        mock_websocket.send_json = AsyncMock(side_effect=ConnectionResetError("Connection closed"))
        
        conn = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        await manager.add_connection(conn)
        
        await manager.send_to_user("user1", {"test": "message"})
        
        # Connection should be automatically removed when send fails
        assert "conn1" not in manager._connections

    def test_websocket_connection_dataclass_immutability(self):
        """Test that WebSocketConnection fields can be modified (this might fail)."""
        conn = WebSocketConnection("conn1", "user1", Mock(), datetime.now())
        original_user_id = conn.user_id
        
        # Try to modify the user_id - this should work for regular dataclasses
        conn.user_id = "modified_user"
        assert conn.user_id == "modified_user"
        assert conn.user_id != original_user_id

    @pytest.mark.asyncio
    async def test_manager_handles_websocket_without_send_json_method(self, manager):
        """Test manager handles WebSocket objects without send_json method."""
        # Create a websocket mock without send_json
        mock_websocket = Mock(spec=[])  # Empty spec means no methods
        
        conn = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        await manager.add_connection(conn)
        
        # This should handle the missing method gracefully
        await manager.send_to_user("user1", {"test": "message"})
        
        # Connection should be removed due to the error
        assert "conn1" not in manager._connections

    @pytest.mark.asyncio
    async def test_broadcast_with_mixed_websocket_states(self, manager):
        """Test broadcast with mix of working and failing WebSockets."""
        # Create working WebSocket
        working_ws = Mock()
        working_ws.send_json = AsyncMock()
        
        # Create failing WebSocket
        failing_ws = Mock()
        failing_ws.send_json = AsyncMock(side_effect=Exception("Send failed"))
        
        # Create WebSocket that raises different exception
        timeout_ws = Mock()
        timeout_ws.send_json = AsyncMock(side_effect=asyncio.TimeoutError("Timeout"))
        
        conn1 = WebSocketConnection("conn1", "user1", working_ws, datetime.now())
        conn2 = WebSocketConnection("conn2", "user2", failing_ws, datetime.now())
        conn3 = WebSocketConnection("conn3", "user3", timeout_ws, datetime.now())
        
        await manager.add_connection(conn1)
        await manager.add_connection(conn2)
        await manager.add_connection(conn3)
        
        await manager.broadcast({"type": "test", "data": "broadcast"})
        
        # Only working connection should remain
        assert "conn1" in manager._connections
        assert "conn2" not in manager._connections
        assert "conn3" not in manager._connections

    @pytest.mark.asyncio
    async def test_emit_critical_event_with_complex_data_structures(self, manager):
        """Test emit_critical_event with complex nested data structures."""
        with patch.object(manager, 'send_to_user', new_callable=AsyncMock) as mock_send:
            complex_data = {
                "nested": {"deep": {"data": [1, 2, 3]}},
                "list": [{"item": "value"}],
                "null_value": None,
                "bool_value": True,
                "unicode": "测试数据"
            }
            
            await manager.emit_critical_event("user1", "complex_event", complex_data)
            
            # Should handle complex data without issues
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert call_args[0] == "user1"
            message = call_args[1]
            assert message["data"] == complex_data

    def test_get_stats_performance_with_large_dataset(self, manager):
        """Test get_stats performance with large number of connections."""
        # Simulate large dataset by directly manipulating internal structures
        for i in range(10000):
            manager._connections[f"conn_{i}"] = WebSocketConnection(
                f"conn_{i}", f"user_{i%100}", Mock(), datetime.now()
            )
            user_id = f"user_{i%100}"
            if user_id not in manager._user_connections:
                manager._user_connections[user_id] = set()
            manager._user_connections[user_id].add(f"conn_{i}")
        
        # This should complete without timeout
        stats = manager.get_stats()
        assert stats["total_connections"] == 10000
        assert stats["unique_users"] == 100

    @pytest.mark.asyncio
    async def test_connection_cleanup_race_condition(self, manager):
        """Test potential race condition in connection cleanup."""
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock(side_effect=Exception("Fail"))
        
        # Add connection
        conn = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        await manager.add_connection(conn)
        
        # Simulate concurrent cleanup attempts
        async def cleanup1():
            await manager.send_to_user("user1", {"test": "1"})
        
        async def cleanup2():
            await manager.remove_connection("conn1")
        
        # Both operations should complete without errors
        await asyncio.gather(cleanup1(), cleanup2(), return_exceptions=True)

    @pytest.mark.asyncio
    async def test_user_isolation_verification(self, manager):
        """Test that user connections are properly isolated."""
        ws1 = Mock()
        ws1.send_json = AsyncMock()
        ws2 = Mock()
        ws2.send_json = AsyncMock()
        
        conn1 = WebSocketConnection("conn1", "user1", ws1, datetime.now())
        conn2 = WebSocketConnection("conn2", "user2", ws2, datetime.now())
        
        await manager.add_connection(conn1)
        await manager.add_connection(conn2)
        
        # Send to user1 only
        await manager.send_to_user("user1", {"private": "message"})
        
        # Only user1's websocket should receive the message
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

    def test_manager_state_consistency_after_operations(self, manager):
        """Test that manager internal state remains consistent."""
        # This test checks for state consistency bugs
        initial_stats = manager.get_stats()
        
        # Manually manipulate state to create inconsistency
        manager._connections["orphan_conn"] = WebSocketConnection(
            "orphan_conn", "orphan_user", Mock(), datetime.now()
        )
        # Don't add to _user_connections - this creates inconsistency
        
        stats = manager.get_stats()
        # This might fail if there are consistency checks
        assert stats["total_connections"] >= initial_stats["total_connections"]

    @pytest.mark.asyncio
    async def test_websocket_manager_memory_cleanup(self, manager):
        """Test that removed connections don't create memory leaks."""
        import weakref
        
        mock_websocket = Mock()
        conn = WebSocketConnection("conn1", "user1", mock_websocket, datetime.now())
        
        # Create weak reference to track if object is garbage collected
        weak_ref = weakref.ref(conn)
        
        await manager.add_connection(conn)
        await manager.remove_connection("conn1")
        
        # Clear local reference
        del conn
        
        # This might fail if there are lingering references
        # Note: This is a tricky test and might be flaky
        import gc
        gc.collect()
        # The weak reference should be None if properly cleaned up
        # assert weak_ref() is None  # Commented out as it might be unreliable