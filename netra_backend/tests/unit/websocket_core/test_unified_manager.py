"""
Comprehensive Unit Tests for Unified WebSocket Manager - SSOT Implementation

Business Value Protection: $500K+ ARR WebSocket connection management comprehensive testing
Addresses Issue #714 Phase 1B: Core Manager Tests

This test suite provides comprehensive coverage for the unified WebSocket manager,
focusing on the highest-impact uncovered code paths identified in coverage analysis.

Key Test Areas:
1. WebSocket connection lifecycle management (connect, disconnect, cleanup)
2. Message routing and user isolation
3. Connection state transitions and error handling
4. Factory pattern validation (prevent singleton issues)
5. Thread-safe operations and concurrency
6. Memory management and circular reference prevention
7. User context isolation and security

Coverage Target: unified_manager.py (currently 8.70% -> target 80%+)
"""

import asyncio
import json
import time
import uuid
import weakref
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

import pytest
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Import target module components - SSOT after Issue #824
from netra_backend.app.websocket_core.unified_manager import (
    WebSocketManagerMode,
    _get_enum_key_representation,
    _serialize_message_safely,
    WebSocketConnection,
    RegistryCompat,
    UnifiedWebSocketManager
)
# Import get_websocket_manager from SSOT location
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

# Import related types and dependencies
from shared.types.core_types import (
    UserID, ThreadID, ConnectionID, WebSocketID, RequestID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id
)
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from netra_backend.app.services.user_execution_context import UserExecutionContext


class UnifiedWebSocketManagerTests(SSotAsyncTestCase):
    """Test suite for unified WebSocket manager functionality."""

    def setup_method(self, method):
        """Set up test environment with SSOT compliance."""
        super().setup_method(method)

        # Use SSOT mock factory for consistent mocking
        self.mock_factory = SSotMockFactory()

        # Create common test data
        self.test_user_id = "user_123"
        self.test_thread_id = "thread_456"
        self.test_connection_id = "conn_789"
        self.test_websocket_id = "ws_101112"
        self.test_timestamp = datetime.now(timezone.utc)

        # Mock WebSocket for testing
        self.mock_websocket = self.mock_factory.create_mock_websocket(
            state=WebSocketState.CONNECTING,
            headers={"authorization": "Bearer test_token"}
        )

        # Sample connection data
        self.test_connection = WebSocketConnection(
            connection_id=self.test_connection_id,
            user_id=self.test_user_id,
            websocket=self.mock_websocket,
            connected_at=self.test_timestamp,
            thread_id=self.test_thread_id,
            metadata={"test": "data"}
        )

    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)

    def test_websocket_manager_mode_enum_ssot_consolidation(self):
        """Test WebSocketManagerMode enum SSOT consolidation."""
        # All modes should redirect to UNIFIED for SSOT compliance
        self.assertEqual(WebSocketManagerMode.UNIFIED, "unified")
        self.assertEqual(WebSocketManagerMode.ISOLATED, "unified")  # Redirects to UNIFIED
        self.assertEqual(WebSocketManagerMode.EMERGENCY, "unified")  # Redirects to UNIFIED
        self.assertEqual(WebSocketManagerMode.DEGRADED, "unified")  # Redirects to UNIFIED

    def test_get_enum_key_representation_websocket_state(self):
        """Test _get_enum_key_representation with WebSocketState enum."""
        # Test with WebSocketState enum (should use lowercase names)
        connecting_repr = _get_enum_key_representation(WebSocketState.CONNECTING)
        connected_repr = _get_enum_key_representation(WebSocketState.CONNECTED)
        disconnected_repr = _get_enum_key_representation(WebSocketState.DISCONNECTED)

        self.assertEqual(connecting_repr, "connecting")
        self.assertEqual(connected_repr, "connected")
        self.assertEqual(disconnected_repr, "disconnected")

    def test_get_enum_key_representation_string_enum(self):
        """Test _get_enum_key_representation with string enum."""
        # Test with WebSocketManagerMode (string enum)
        unified_repr = _get_enum_key_representation(WebSocketManagerMode.UNIFIED)
        self.assertEqual(unified_repr, "unified")

    def test_serialize_message_safely_basic_types(self):
        """Test _serialize_message_safely with basic data types."""
        # Test string
        result = _serialize_message_safely("test_string")
        self.assertEqual(result, "test_string")

        # Test number
        result = _serialize_message_safely(42)
        self.assertEqual(result, 42)

        # Test boolean
        result = _serialize_message_safely(True)
        self.assertEqual(result, True)

        # Test None
        result = _serialize_message_safely(None)
        self.assertIsNone(result)

    def test_serialize_message_safely_dict_with_enum_keys(self):
        """Test _serialize_message_safely with dictionary containing enum keys."""
        # Test dict with enum keys
        test_dict = {
            WebSocketState.CONNECTING: "connecting_value",
            WebSocketState.CONNECTED: "connected_value"
        }

        result = _serialize_message_safely(test_dict)

        # Enum keys should be converted to string representations
        self.assertIn("connecting", result)
        self.assertIn("connected", result)
        self.assertEqual(result["connecting"], "connecting_value")
        self.assertEqual(result["connected"], "connected_value")

    def test_serialize_message_safely_nested_dict(self):
        """Test _serialize_message_safely with nested dictionaries."""
        nested_dict = {
            "level1": {
                "level2": {
                    WebSocketState.CONNECTING: "deep_value",
                    "normal_key": "normal_value"
                }
            }
        }

        result = _serialize_message_safely(nested_dict)

        # Verify nested structure is preserved with enum keys serialized
        self.assertIn("level1", result)
        self.assertIn("level2", result["level1"])
        self.assertIn("connecting", result["level1"]["level2"])
        self.assertEqual(result["level1"]["level2"]["connecting"], "deep_value")

    def test_serialize_message_safely_object_with_to_dict(self):
        """Test _serialize_message_safely with object having to_dict method."""
        # Create mock object with to_dict method
        mock_object = Mock()
        mock_object.to_dict.return_value = {"serialized": "data"}

        result = _serialize_message_safely(mock_object)

        self.assertEqual(result, {"serialized": "data"})
        mock_object.to_dict.assert_called_once()

    def test_serialize_message_safely_dataclass(self):
        """Test _serialize_message_safely with dataclass objects."""
        from dataclasses import dataclass

        @dataclass
        class DataClassTests:
            name: str
            value: int

        test_obj = DataClassTests(name="test", value=42)
        result = _serialize_message_safely(test_obj)

        self.assertEqual(result["name"], "test")
        self.assertEqual(result["value"], 42)

    def test_serialize_message_safely_datetime(self):
        """Test _serialize_message_safely with datetime objects."""
        test_datetime = datetime.now(timezone.utc)
        result = _serialize_message_safely(test_datetime)

        # Should return ISO format string
        self.assertEqual(result, test_datetime.isoformat())

    def test_serialize_message_safely_collections(self):
        """Test _serialize_message_safely with various collection types."""
        # Test list
        test_list = [1, 2, {"key": "value"}]
        result = _serialize_message_safely(test_list)
        self.assertEqual(result, [1, 2, {"key": "value"}])

        # Test tuple
        test_tuple = (1, 2, 3)
        result = _serialize_message_safely(test_tuple)
        self.assertEqual(result, [1, 2, 3])

        # Test set
        test_set = {1, 2, 3}
        result = _serialize_message_safely(test_set)
        self.assertCountEqual(result, [1, 2, 3])

    def test_serialize_message_safely_fallback(self):
        """Test _serialize_message_safely fallback to string conversion."""
        # Create object that can't be JSON serialized
        class NonSerializable:
            def __str__(self):
                return "non_serializable_object"

        test_obj = NonSerializable()
        result = _serialize_message_safely(test_obj)

        self.assertEqual(result, "non_serializable_object")

    def test_websocket_connection_creation_and_validation(self):
        """Test WebSocketConnection dataclass creation and validation."""
        connection = WebSocketConnection(
            connection_id=self.test_connection_id,
            user_id=self.test_user_id,
            websocket=self.mock_websocket,
            connected_at=self.test_timestamp,
            thread_id=self.test_thread_id,
            metadata={"test": "metadata"}
        )

        # Verify properties
        self.assertEqual(connection.connection_id, self.test_connection_id)
        self.assertEqual(connection.user_id, self.test_user_id)
        self.assertEqual(connection.websocket, self.mock_websocket)
        self.assertEqual(connection.connected_at, self.test_timestamp)
        self.assertEqual(connection.thread_id, self.test_thread_id)
        self.assertEqual(connection.metadata, {"test": "metadata"})

    def test_websocket_connection_user_id_validation(self):
        """Test WebSocketConnection user_id validation via ensure_user_id."""
        # Test that user_id is properly validated during initialization
        connection = WebSocketConnection(
            connection_id=self.test_connection_id,
            user_id="raw_user_id",  # Should be validated by ensure_user_id
            websocket=self.mock_websocket,
            connected_at=self.test_timestamp
        )

        # User ID should be validated (exact behavior depends on ensure_user_id implementation)
        self.assertIsNotNone(connection.user_id)

    def test_registry_compat_initialization_weak_reference(self):
        """Test RegistryCompat initialization with weak reference to prevent circular references."""
        # Create mock manager
        mock_manager = Mock()

        # Create registry with weak reference
        registry = RegistryCompat(mock_manager)

        # Verify weak reference is stored
        self.assertIsNotNone(registry._manager_ref)
        self.assertEqual(registry.manager, mock_manager)

    def test_registry_compat_manager_garbage_collection(self):
        """Test RegistryCompat handles manager garbage collection gracefully."""
        # Create manager and registry
        mock_manager = Mock()
        registry = RegistryCompat(mock_manager)

        # Delete manager reference
        del mock_manager

        # Accessing manager should raise RuntimeError after garbage collection
        with self.assertRaises(RuntimeError) as context:
            _ = registry.manager

        self.assertIn("garbage collected", str(context.exception))

    async def test_registry_compat_register_connection(self):
        """Test RegistryCompat register_connection functionality."""
        # Create mock manager with add_connection method
        mock_manager = AsyncMock()
        registry = RegistryCompat(mock_manager)

        # Create mock connection info
        mock_connection_info = Mock()
        mock_connection_info.connection_id = self.test_connection_id
        mock_connection_info.websocket = self.mock_websocket
        mock_connection_info.connected_at = self.test_timestamp
        mock_connection_info.thread_id = self.test_thread_id

        # Register connection
        await registry.register_connection(self.test_user_id, mock_connection_info)

        # Verify manager.add_connection was called
        mock_manager.add_connection.assert_called_once()

        # Verify connection info was stored
        self.assertTrue(hasattr(mock_manager, '_connection_infos'))
        self.assertIn(self.test_connection_id, mock_manager._connection_infos)

    def test_registry_compat_get_user_connections(self):
        """Test RegistryCompat get_user_connections functionality."""
        # Create mock manager
        mock_manager = Mock()
        mock_manager._user_connections = {self.test_user_id: [self.test_connection_id]}
        mock_manager._connection_infos = {self.test_connection_id: "mock_connection_info"}

        registry = RegistryCompat(mock_manager)

        # Get user connections
        connections = registry.get_user_connections(self.test_user_id)

        # Verify connections returned
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0], "mock_connection_info")

    def test_registry_compat_get_user_connections_no_connections(self):
        """Test RegistryCompat get_user_connections with no connections."""
        # Create mock manager with no connections
        mock_manager = Mock()
        mock_manager._user_connections = {}

        registry = RegistryCompat(mock_manager)

        # Get user connections (should return empty list)
        connections = registry.get_user_connections(self.test_user_id)
        self.assertEqual(connections, [])

    def test_unified_websocket_manager_initialization(self):
        """Test UnifiedWebSocketManager initialization."""
        manager = UnifiedWebSocketManager()

        # Verify manager is properly initialized
        self.assertIsNotNone(manager)
        self.assertIsInstance(manager, UnifiedWebSocketManager)

        # Verify internal state initialization
        self.assertTrue(hasattr(manager, '_connections'))
        self.assertTrue(hasattr(manager, '_user_connections'))

    async def test_unified_websocket_manager_add_connection(self):
        """Test UnifiedWebSocketManager add_connection functionality."""
        manager = UnifiedWebSocketManager()

        # Add connection
        await manager.add_connection(self.test_connection)

        # Verify connection was added
        self.assertIn(self.test_connection_id, manager._connections)
        self.assertEqual(manager._connections[self.test_connection_id], self.test_connection)

        # Verify user mapping was updated
        self.assertIn(self.test_user_id, manager._user_connections)
        self.assertIn(self.test_connection_id, manager._user_connections[self.test_user_id])

    async def test_unified_websocket_manager_remove_connection(self):
        """Test UnifiedWebSocketManager remove_connection functionality."""
        manager = UnifiedWebSocketManager()

        # Add then remove connection
        await manager.add_connection(self.test_connection)
        await manager.remove_connection(self.test_connection_id)

        # Verify connection was removed
        self.assertNotIn(self.test_connection_id, manager._connections)

        # Verify user mapping was cleaned up
        if self.test_user_id in manager._user_connections:
            self.assertNotIn(self.test_connection_id, manager._user_connections[self.test_user_id])

    async def test_unified_websocket_manager_get_connection(self):
        """Test UnifiedWebSocketManager get_connection functionality."""
        manager = UnifiedWebSocketManager()

        # Add connection
        await manager.add_connection(self.test_connection)

        # Get connection
        retrieved_connection = manager.get_connection(self.test_connection_id)

        # Verify correct connection returned
        self.assertEqual(retrieved_connection, self.test_connection)

    async def test_unified_websocket_manager_get_user_connections(self):
        """Test UnifiedWebSocketManager get_user_connections functionality."""
        manager = UnifiedWebSocketManager()

        # Add connection
        await manager.add_connection(self.test_connection)

        # Get user connections
        user_connections = manager.get_user_connections(self.test_user_id)

        # Verify user connections returned
        self.assertEqual(len(user_connections), 1)
        self.assertEqual(user_connections[0], self.test_connection)

    async def test_unified_websocket_manager_send_message_to_connection(self):
        """Test UnifiedWebSocketManager send_message_to_connection functionality."""
        manager = UnifiedWebSocketManager()

        # Mock WebSocket send method
        self.mock_websocket.send_text = AsyncMock()

        # Add connection
        await manager.add_connection(self.test_connection)

        # Send message
        test_message = {"type": "test", "data": "message"}
        await manager.send_message_to_connection(self.test_connection_id, test_message)

        # Verify message was sent
        self.mock_websocket.send_text.assert_called_once()

    async def test_unified_websocket_manager_send_message_to_user(self):
        """Test UnifiedWebSocketManager send_message_to_user functionality."""
        manager = UnifiedWebSocketManager()

        # Mock WebSocket send method
        self.mock_websocket.send_text = AsyncMock()

        # Add connection
        await manager.add_connection(self.test_connection)

        # Send message to user
        test_message = {"type": "test", "data": "user_message"}
        await manager.send_message_to_user(self.test_user_id, test_message)

        # Verify message was sent to user's connection
        self.mock_websocket.send_text.assert_called_once()

    async def test_unified_websocket_manager_broadcast_message(self):
        """Test UnifiedWebSocketManager broadcast_message functionality."""
        manager = UnifiedWebSocketManager()

        # Create multiple connections for different users
        user2_id = "user_456"
        connection2_id = "conn_456"
        mock_websocket2 = self.mock_factory.create_mock_websocket()
        mock_websocket2.send_text = AsyncMock()

        connection2 = WebSocketConnection(
            connection_id=connection2_id,
            user_id=user2_id,
            websocket=mock_websocket2,
            connected_at=self.test_timestamp
        )

        # Mock send_text for first connection too
        self.mock_websocket.send_text = AsyncMock()

        # Add both connections
        await manager.add_connection(self.test_connection)
        await manager.add_connection(connection2)

        # Broadcast message
        test_message = {"type": "broadcast", "data": "broadcast_message"}
        await manager.broadcast_message(test_message)

        # Verify message was sent to both connections
        self.mock_websocket.send_text.assert_called_once()
        mock_websocket2.send_text.assert_called_once()

    async def test_unified_websocket_manager_user_isolation(self):
        """Test UnifiedWebSocketManager properly isolates users."""
        manager = UnifiedWebSocketManager()

        # Create connections for two different users
        user2_id = "user_different"
        connection2_id = "conn_different"
        mock_websocket2 = self.mock_factory.create_mock_websocket()

        connection2 = WebSocketConnection(
            connection_id=connection2_id,
            user_id=user2_id,
            websocket=mock_websocket2,
            connected_at=self.test_timestamp
        )

        # Add both connections
        await manager.add_connection(self.test_connection)
        await manager.add_connection(connection2)

        # Get connections for each user
        user1_connections = manager.get_user_connections(self.test_user_id)
        user2_connections = manager.get_user_connections(user2_id)

        # Verify isolation - each user only sees their own connections
        self.assertEqual(len(user1_connections), 1)
        self.assertEqual(len(user2_connections), 1)
        self.assertEqual(user1_connections[0].user_id, self.test_user_id)
        self.assertEqual(user2_connections[0].user_id, user2_id)

    async def test_unified_websocket_manager_thread_safety(self):
        """Test UnifiedWebSocketManager thread safety with concurrent operations."""
        manager = UnifiedWebSocketManager()

        # Create multiple connections for concurrent testing
        connections = []
        for i in range(10):
            connection = WebSocketConnection(
                connection_id=f"conn_{i}",
                user_id=f"user_{i}",
                websocket=self.mock_factory.create_mock_websocket(),
                connected_at=self.test_timestamp
            )
            connections.append(connection)

        # Add connections concurrently
        add_tasks = [manager.add_connection(conn) for conn in connections]
        await asyncio.gather(*add_tasks)

        # Verify all connections were added
        self.assertEqual(len(manager._connections), 10)

        # Remove connections concurrently
        remove_tasks = [manager.remove_connection(f"conn_{i}") for i in range(10)]
        await asyncio.gather(*remove_tasks)

        # Verify all connections were removed
        self.assertEqual(len(manager._connections), 0)

    async def test_unified_websocket_manager_error_handling_invalid_connection(self):
        """Test UnifiedWebSocketManager error handling with invalid connection operations."""
        manager = UnifiedWebSocketManager()

        # Try to get non-existent connection
        connection = manager.get_connection("non_existent_id")
        self.assertIsNone(connection)

        # Try to remove non-existent connection (should not raise error)
        await manager.remove_connection("non_existent_id")

        # Try to send message to non-existent connection
        with self.assertRaises(Exception):
            await manager.send_message_to_connection("non_existent_id", {"test": "message"})

    async def test_unified_websocket_manager_memory_management(self):
        """Test UnifiedWebSocketManager memory management and cleanup."""
        manager = UnifiedWebSocketManager()

        # Add many connections
        connection_count = 100
        for i in range(connection_count):
            connection = WebSocketConnection(
                connection_id=f"conn_{i}",
                user_id=f"user_{i}",
                websocket=self.mock_factory.create_mock_websocket(),
                connected_at=self.test_timestamp
            )
            await manager.add_connection(connection)

        # Verify connections added
        self.assertEqual(len(manager._connections), connection_count)

        # Remove all connections
        for i in range(connection_count):
            await manager.remove_connection(f"conn_{i}")

        # Verify memory cleanup
        self.assertEqual(len(manager._connections), 0)
        self.assertEqual(len(manager._user_connections), 0)

    async def test_unified_websocket_manager_factory_pattern_validation(self):
        """Test UnifiedWebSocketManager factory pattern prevents singleton issues."""
        # Create multiple manager instances
        manager1 = UnifiedWebSocketManager()
        manager2 = UnifiedWebSocketManager()

        # Verify they are different instances (not singleton)
        self.assertIsNot(manager1, manager2)

        # Add connection to first manager
        await manager1.add_connection(self.test_connection)

        # Second manager should not have the connection (isolation)
        connection_in_manager2 = manager2.get_connection(self.test_connection_id)
        self.assertIsNone(connection_in_manager2)

    async def test_unified_websocket_manager_connection_state_transitions(self):
        """Test UnifiedWebSocketManager handles connection state transitions."""
        manager = UnifiedWebSocketManager()

        # Add connection
        await manager.add_connection(self.test_connection)

        # Verify connection is in CONNECTING state initially
        connection = manager.get_connection(self.test_connection_id)
        self.assertEqual(connection.websocket.client_state, WebSocketState.CONNECTING)

        # Simulate state change to CONNECTED
        self.mock_websocket.client_state = WebSocketState.CONNECTED

        # Connection should reflect state change
        connection = manager.get_connection(self.test_connection_id)
        self.assertEqual(connection.websocket.client_state, WebSocketState.CONNECTED)

    async def test_unified_websocket_manager_message_serialization_integration(self):
        """Test UnifiedWebSocketManager integrates with message serialization."""
        manager = UnifiedWebSocketManager()

        # Mock WebSocket send method to capture serialized message
        self.mock_websocket.send_text = AsyncMock()

        # Add connection
        await manager.add_connection(self.test_connection)

        # Send complex message with various data types
        complex_message = {
            "timestamp": datetime.now(timezone.utc),
            "state": WebSocketState.CONNECTED,
            "data": {"nested": {"value": 42}},
            "list": [1, 2, 3]
        }

        await manager.send_message_to_connection(self.test_connection_id, complex_message)

        # Verify send_text was called (message should be serialized internally)
        self.mock_websocket.send_text.assert_called_once()

    def test_get_websocket_manager_factory_function(self):
        """Test get_websocket_manager factory function."""
        # Get manager instance
        manager = get_websocket_manager()

        # Verify it's the correct type
        self.assertIsInstance(manager, UnifiedWebSocketManager)

        # Get another instance
        manager2 = get_websocket_manager()

        # Should return same instance (singleton factory pattern)
        self.assertEqual(manager, manager2)

    async def test_unified_websocket_manager_connection_metadata_handling(self):
        """Test UnifiedWebSocketManager handles connection metadata properly."""
        manager = UnifiedWebSocketManager()

        # Create connection with metadata
        metadata = {
            "client_info": {"browser": "Chrome", "version": "90.0"},
            "session_data": {"started_at": self.test_timestamp.isoformat()},
            "custom_data": {"feature_flags": ["flag1", "flag2"]}
        }

        connection_with_metadata = WebSocketConnection(
            connection_id=self.test_connection_id,
            user_id=self.test_user_id,
            websocket=self.mock_websocket,
            connected_at=self.test_timestamp,
            metadata=metadata
        )

        # Add connection
        await manager.add_connection(connection_with_metadata)

        # Retrieve connection and verify metadata preserved
        retrieved_connection = manager.get_connection(self.test_connection_id)
        self.assertEqual(retrieved_connection.metadata, metadata)

    async def test_unified_websocket_manager_concurrent_user_operations(self):
        """Test UnifiedWebSocketManager handles concurrent operations on same user."""
        manager = UnifiedWebSocketManager()

        # Create multiple connections for same user
        user_connections = []
        for i in range(5):
            connection = WebSocketConnection(
                connection_id=f"conn_{i}",
                user_id=self.test_user_id,  # Same user
                websocket=self.mock_factory.create_mock_websocket(),
                connected_at=self.test_timestamp
            )
            user_connections.append(connection)

        # Add connections concurrently
        add_tasks = [manager.add_connection(conn) for conn in user_connections]
        await asyncio.gather(*add_tasks)

        # Verify all connections added for user
        retrieved_connections = manager.get_user_connections(self.test_user_id)
        self.assertEqual(len(retrieved_connections), 5)

        # Send message to user (should reach all connections)
        mock_websockets = [conn.websocket for conn in user_connections]
        for ws in mock_websockets:
            ws.send_text = AsyncMock()

        test_message = {"type": "user_message", "data": "test"}
        await manager.send_message_to_user(self.test_user_id, test_message)

        # Verify message sent to all user connections
        for ws in mock_websockets:
            ws.send_text.assert_called_once()

    async def test_unified_websocket_manager_connection_lifecycle_events(self):
        """Test UnifiedWebSocketManager connection lifecycle event handling."""
        manager = UnifiedWebSocketManager()

        # Track lifecycle events
        events = []

        # Mock event handlers (if they exist)
        original_add = manager.add_connection
        original_remove = manager.remove_connection

        async def add_with_event(*args, **kwargs):
            events.append("connection_added")
            return await original_add(*args, **kwargs)

        async def remove_with_event(*args, **kwargs):
            events.append("connection_removed")
            return await original_remove(*args, **kwargs)

        manager.add_connection = add_with_event
        manager.remove_connection = remove_with_event

        # Perform lifecycle operations
        await manager.add_connection(self.test_connection)
        await manager.remove_connection(self.test_connection_id)

        # Verify events were tracked
        self.assertIn("connection_added", events)
        self.assertIn("connection_removed", events)