"""
Unit tests for UnifiedWebSocketManager - Testing core connection management and message serialization.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Multi-user WebSocket connection reliability
- Value Impact: Ensures proper connection isolation and message handling for concurrent users
- Strategic Impact: Foundation for real-time chat - validates connection management without external dependencies

These tests focus on the UnifiedWebSocketManager's core functionality including
connection lifecycle, user isolation, and the critical message serialization system.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, MagicMock
from enum import Enum
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager, 
    WebSocketConnection,
    _serialize_message_safely
)


class TestUnifiedWebSocketManagerCore:
    """Unit tests for core UnifiedWebSocketManager functionality."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create UnifiedWebSocketManager instance."""
        return UnifiedWebSocketManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection."""
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        return mock_ws
    
    @pytest.fixture
    def sample_connection(self, mock_websocket):
        """Create sample WebSocket connection."""
        return WebSocketConnection(
            connection_id="test_conn_123",
            user_id="user_456",
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc),
            metadata={"test": True, "connection_type": "unit_test"}
        )
    
    def test_initializes_with_correct_default_state(self, websocket_manager):
        """Test WebSocketManager initializes with proper default state."""
        assert len(websocket_manager._connections) == 0
        assert len(websocket_manager._user_connections) == 0
        assert websocket_manager._lock is not None
        assert len(websocket_manager._user_connection_locks) == 0
        assert websocket_manager._connection_lock_creation_lock is not None
        
        # Verify compatibility attributes
        assert websocket_manager._connection_manager is websocket_manager
        assert websocket_manager.connection_manager is websocket_manager
        assert hasattr(websocket_manager, 'active_connections')
        assert hasattr(websocket_manager, 'connection_registry')
        assert hasattr(websocket_manager, 'registry')
    
    @pytest.mark.asyncio
    async def test_adds_connection_successfully(self, websocket_manager, sample_connection):
        """Test successful connection addition with proper state tracking."""
        # Act
        await websocket_manager.add_connection(sample_connection)
        
        # Assert
        assert sample_connection.connection_id in websocket_manager._connections
        assert websocket_manager._connections[sample_connection.connection_id] == sample_connection
        
        # Verify user connection tracking
        assert sample_connection.user_id in websocket_manager._user_connections
        user_connections = websocket_manager._user_connections[sample_connection.user_id]
        assert sample_connection.connection_id in user_connections
        
        # Verify compatibility mappings
        assert sample_connection.user_id in websocket_manager.active_connections
        assert len(websocket_manager.active_connections[sample_connection.user_id]) == 1
    
    @pytest.mark.asyncio
    async def test_removes_connection_successfully(self, websocket_manager, sample_connection):
        """Test successful connection removal with proper cleanup."""
        # Arrange - Add connection first
        await websocket_manager.add_connection(sample_connection)
        assert sample_connection.connection_id in websocket_manager._connections
        
        # Act
        await websocket_manager.remove_connection(sample_connection.connection_id)
        
        # Assert
        assert sample_connection.connection_id not in websocket_manager._connections
        assert sample_connection.user_id not in websocket_manager._user_connections
        
        # Verify compatibility mappings cleanup
        assert sample_connection.user_id not in websocket_manager.active_connections
    
    @pytest.mark.asyncio
    async def test_handles_multiple_connections_per_user(self, websocket_manager):
        """Test manager properly handles multiple connections for same user."""
        user_id = "multi_conn_user_789"
        
        # Create multiple mock WebSockets
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws3 = AsyncMock()
        
        connections = [
            WebSocketConnection("conn_1", user_id, mock_ws1, datetime.now(timezone.utc)),
            WebSocketConnection("conn_2", user_id, mock_ws2, datetime.now(timezone.utc)), 
            WebSocketConnection("conn_3", user_id, mock_ws3, datetime.now(timezone.utc))
        ]
        
        # Act - Add all connections
        for conn in connections:
            await websocket_manager.add_connection(conn)
        
        # Assert - Verify all connections tracked for user
        assert len(websocket_manager._user_connections[user_id]) == 3
        assert len(websocket_manager.active_connections[user_id]) == 3
        
        # Remove one connection
        await websocket_manager.remove_connection("conn_2")
        
        # Verify partial removal
        assert len(websocket_manager._user_connections[user_id]) == 2
        assert "conn_2" not in websocket_manager._connections
        assert "conn_1" in websocket_manager._connections
        assert "conn_3" in websocket_manager._connections
    
    def test_gets_connection_by_id(self, websocket_manager, sample_connection):
        """Test retrieving connection by ID."""
        # Arrange
        websocket_manager._connections[sample_connection.connection_id] = sample_connection
        
        # Act & Assert
        retrieved = websocket_manager.get_connection(sample_connection.connection_id)
        assert retrieved == sample_connection
        
        # Test non-existent connection
        assert websocket_manager.get_connection("non_existent") is None
    
    def test_gets_user_connections(self, websocket_manager):
        """Test retrieving all connections for a user."""
        user_id = "test_user_multi"
        connection_ids = {"conn_1", "conn_2", "conn_3"}
        
        # Arrange
        websocket_manager._user_connections[user_id] = connection_ids
        
        # Act
        retrieved = websocket_manager.get_user_connections(user_id)
        
        # Assert
        assert retrieved == connection_ids
        assert retrieved is not websocket_manager._user_connections[user_id]  # Should be copy
        
        # Test non-existent user
        assert websocket_manager.get_user_connections("non_existent") == set()
    
    def test_connection_health_status_checking(self, websocket_manager, sample_connection):
        """Test connection health status methods."""
        user_id = sample_connection.user_id
        
        # Test with no connections
        assert websocket_manager.is_connection_active(user_id) is False
        health = websocket_manager.get_connection_health(user_id)
        assert health['has_active_connections'] is False
        assert health['total_connections'] == 0
        
        # Add connection
        websocket_manager._connections[sample_connection.connection_id] = sample_connection
        websocket_manager._user_connections[user_id] = {sample_connection.connection_id}
        
        # Test with active connection
        assert websocket_manager.is_connection_active(user_id) is True
        health = websocket_manager.get_connection_health(user_id)
        assert health['has_active_connections'] is True
        assert health['total_connections'] == 1
        assert health['active_connections'] == 1
        assert len(health['connections']) == 1
        
        connection_detail = health['connections'][0]
        assert connection_detail['connection_id'] == sample_connection.connection_id
        assert connection_detail['active'] is True
        assert 'connected_at' in connection_detail
        assert connection_detail['metadata'] == sample_connection.metadata


class TestMessageSerialization:
    """Unit tests for the critical message serialization system."""
    
    def test_serializes_basic_dict_messages(self):
        """Test serialization of basic dictionary messages."""
        message = {
            "type": "agent_started",
            "payload": {
                "agent_name": "test_agent",
                "timestamp": 1234567890
            }
        }
        
        result = _serialize_message_safely(message)
        assert result == message
        
        # Verify it's JSON serializable
        json.dumps(result)  # Should not raise
    
    def test_serializes_enum_objects_safely(self):
        """Test serialization of enum objects (critical for WebSocketState)."""
        class TestEnum(Enum):
            CONNECTED = "connected"
            DISCONNECTED = "disconnected"
        
        # Test enum in message
        message = {
            "type": "connection_status",
            "status": TestEnum.CONNECTED,
            "data": {"state": TestEnum.DISCONNECTED}
        }
        
        result = _serialize_message_safely(message)
        assert result["status"] == "connected"
        assert result["data"]["state"] == "disconnected"
    
    def test_serializes_websocket_state_enums(self):
        """Test serialization of WebSocket state enums (critical Cloud Run fix)."""
        # Mock WebSocketState enum
        class MockWebSocketState(Enum):
            CONNECTED = 1
            DISCONNECTED = 0
            
            @property
            def name(self):
                return "CONNECTED" if self.value == 1 else "DISCONNECTED"
        
        state = MockWebSocketState.CONNECTED
        result = _serialize_message_safely(state)
        assert result == "connected"  # Should be lowercase
        
        # Test in message structure
        message = {"websocket_state": state, "other_data": "test"}
        result = _serialize_message_safely(message)
        assert result["websocket_state"] == "connected"
        assert result["other_data"] == "test"
    
    def test_serializes_pydantic_models_with_datetime(self):
        """Test serialization of Pydantic models with proper datetime handling."""
        # Mock Pydantic model
        class MockPydanticModel:
            def __init__(self):
                self.timestamp = datetime.now(timezone.utc)
                self.data = "test_value"
            
            def model_dump(self, mode=None):
                if mode == 'json':
                    return {
                        "timestamp": self.timestamp.isoformat(),
                        "data": self.data
                    }
                return {
                    "timestamp": self.timestamp,
                    "data": self.data
                }
        
        model = MockPydanticModel()
        result = _serialize_message_safely(model)
        
        assert "timestamp" in result
        assert result["data"] == "test_value"
        # Should use JSON mode for proper datetime serialization
        assert isinstance(result["timestamp"], str)
    
    def test_serializes_dataclasses_recursively(self):
        """Test serialization of dataclasses with nested serialization."""
        from dataclasses import dataclass
        
        @dataclass
        class NestedData:
            value: str
            count: int
        
        @dataclass
        class TestDataclass:
            name: str
            nested: NestedData
            timestamp: datetime
        
        nested = NestedData("test_value", 42)
        test_obj = TestDataclass("test_name", nested, datetime.now(timezone.utc))
        
        result = _serialize_message_safely(test_obj)
        
        assert result["name"] == "test_name"
        assert result["nested"]["value"] == "test_value"
        assert result["nested"]["count"] == 42
        assert isinstance(result["timestamp"], str)  # Datetime should be serialized
    
    def test_handles_complex_nested_structures(self):
        """Test serialization of complex nested structures with multiple types."""
        class CustomEnum(Enum):
            TYPE_A = "type_a"
            TYPE_B = "type_b"
        
        complex_message = {
            "type": "complex_event",
            "status": CustomEnum.TYPE_A,
            "data": {
                "items": [
                    {"name": "item1", "type": CustomEnum.TYPE_B},
                    {"name": "item2", "count": 5}
                ],
                "metadata": {
                    "created_at": datetime.now(timezone.utc),
                    "tags": {"important", "test", "serialization"}  # Set should become list
                }
            }
        }
        
        result = _serialize_message_safely(complex_message)
        
        assert result["type"] == "complex_event"
        assert result["status"] == "type_a"
        assert len(result["data"]["items"]) == 2
        assert result["data"]["items"][0]["type"] == "type_b"
        assert result["data"]["items"][1]["count"] == 5
        assert isinstance(result["data"]["metadata"]["created_at"], str)
        assert isinstance(result["data"]["metadata"]["tags"], list)
        assert len(result["data"]["metadata"]["tags"]) == 3
    
    def test_fallback_string_conversion_for_unhandled_types(self):
        """Test fallback string conversion for types that can't be serialized."""
        class UnserializableClass:
            def __init__(self):
                self.data = "internal_data"
        
        unserializable = UnserializableClass()
        result = _serialize_message_safely(unserializable)
        
        # Should fallback to string representation
        assert isinstance(result, str)
        assert "UnserializableClass" in result
    
    def test_handles_none_and_empty_values(self):
        """Test serialization handles None and empty values properly."""
        message = {
            "valid_data": "test",
            "none_value": None,
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {}
        }
        
        result = _serialize_message_safely(message)
        
        assert result == message  # Should pass through unchanged
        json.dumps(result)  # Should be JSON serializable


class TestUnifiedWebSocketManagerCompatibility:
    """Unit tests for legacy compatibility features."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create UnifiedWebSocketManager instance."""
        return UnifiedWebSocketManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_legacy_connect_user_method(self, websocket_manager, mock_websocket):
        """Test legacy connect_user method creates proper connection."""
        user_id = "legacy_user_123"
        
        # Act
        conn_info = await websocket_manager.connect_user(user_id, mock_websocket)
        
        # Assert - Should return connection info object
        assert hasattr(conn_info, 'user_id')
        assert hasattr(conn_info, 'connection_id')
        assert hasattr(conn_info, 'websocket')
        assert conn_info.user_id == user_id
        assert conn_info.websocket == mock_websocket
        
        # Verify connection was added to manager
        assert conn_info.connection_id in websocket_manager._connections
        assert user_id in websocket_manager._user_connections
        assert conn_info.connection_id in websocket_manager.connection_registry
    
    @pytest.mark.asyncio 
    async def test_legacy_disconnect_user_method(self, websocket_manager, mock_websocket):
        """Test legacy disconnect_user method removes connection."""
        user_id = "legacy_disconnect_user"
        
        # Connect first
        conn_info = await websocket_manager.connect_user(user_id, mock_websocket)
        assert conn_info.connection_id in websocket_manager._connections
        
        # Act - Disconnect
        await websocket_manager.disconnect_user(user_id, mock_websocket)
        
        # Assert - Connection should be removed
        assert conn_info.connection_id not in websocket_manager._connections
        assert user_id not in websocket_manager._user_connections or \
               len(websocket_manager._user_connections[user_id]) == 0
        assert conn_info.connection_id not in websocket_manager.connection_registry
    
    @pytest.mark.asyncio
    async def test_connect_to_job_creates_job_connection(self, websocket_manager, mock_websocket):
        """Test connect_to_job creates proper job-based connection."""
        job_id = "test_job_456"
        
        # Act
        conn_info = await websocket_manager.connect_to_job(mock_websocket, job_id)
        
        # Assert
        assert hasattr(conn_info, 'job_id')
        assert conn_info.job_id == job_id
        assert conn_info.websocket == mock_websocket
        
        # Verify job room management setup
        assert hasattr(websocket_manager, 'core')
        assert hasattr(websocket_manager.core, 'room_manager')
        assert job_id in websocket_manager.core.room_manager.rooms
        assert conn_info.connection_id in websocket_manager.core.room_manager.rooms[job_id]
        
        # Test room manager functionality
        stats = websocket_manager.core.room_manager.get_stats()
        assert job_id in stats["room_connections"]
        
        room_connections = websocket_manager.core.room_manager.get_room_connections(job_id)
        assert len(room_connections) == 1
    
    def test_registry_compat_wrapper(self, websocket_manager):
        """Test RegistryCompat wrapper provides legacy test compatibility."""
        registry = websocket_manager.registry
        
        # Should have the compatibility methods
        assert hasattr(registry, 'register_connection')
        assert hasattr(registry, 'get_user_connections')
        assert callable(registry.register_connection)
        assert callable(registry.get_user_connections)
    
    @pytest.mark.asyncio
    async def test_find_connection_method(self, websocket_manager, mock_websocket):
        """Test find_connection method locates connections properly."""
        user_id = "find_test_user"
        
        # Connect user
        conn_info = await websocket_manager.connect_user(user_id, mock_websocket)
        
        # Act
        found_connection = await websocket_manager.find_connection(user_id, mock_websocket)
        
        # Assert
        assert found_connection is not None
        assert found_connection.user_id == user_id
        assert found_connection.websocket == mock_websocket
        assert found_connection.connection_id == conn_info.connection_id
        
        # Test with non-existent connection
        other_websocket = AsyncMock()
        not_found = await websocket_manager.find_connection(user_id, other_websocket)
        assert not_found is None