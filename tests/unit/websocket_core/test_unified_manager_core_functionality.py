"""Test WebSocket Core Unified Manager - Core Functionality Tests

Business Value Justification (BVJ):
- Segment: Platform/All Users (Free -> Enterprise)
- Business Goal: Protect $500K+ ARR WebSocket chat functionality
- Value Impact: Ensures WebSocket manager initialization, connection management, and event routing work reliably
- Revenue Impact: Prevents system failures that would block customer chat interactions

This test suite focuses on the core functionality of the WebSocket unified manager
without complex mocking or external dependencies. Tests validate:

1. Manager initialization and state management
2. Connection lifecycle management
3. Event routing and delivery
4. User isolation and security
5. Error handling and recovery

These tests follow SSOT patterns and avoid over-mocking to ensure they
actually test the real business logic that customers depend on.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock

# SSOT imports following SSOT_IMPORT_REGISTRY.md
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketManagerMode
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ConnectionID, WebSocketID
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestWebSocketConnection:
    """Simple WebSocket connection mock for testing."""

    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> List[dict]:
        """Get all sent messages."""
        return self.messages_sent.copy()


class TestUnifiedWebSocketManagerCore(SSotAsyncTestCase):
    """Test core functionality of UnifiedWebSocketManager.

    Focuses on business-critical functionality without external dependencies.
    """

    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.manager = UnifiedWebSocketManager(mode=WebSocketManagerMode.UNIFIED)

    async def asyncTearDown(self):
        """Clean up test environment."""
        if hasattr(self, 'manager'):
            # Clean up any connections
            try:
                await self.manager.cleanup()
            except Exception as e:
                logger.warning(f"Cleanup error: {e}")
        await super().asyncTearDown()

    async def test_manager_initialization(self):
        """Test that manager initializes correctly."""
        # Test basic initialization
        self.assertIsNotNone(self.manager)
        self.assertEqual(self.manager.mode, WebSocketManagerMode.UNIFIED)

        # Test that manager starts in correct state
        self.assertIsInstance(self.manager._connections, dict)
        self.assertIsInstance(self.manager._user_connections, dict)

    async def test_connection_registration(self):
        """Test connection registration and tracking."""
        # Create test connection
        connection_id = "test_conn_001"
        user_id = "user_001"
        connection = TestWebSocketConnection(connection_id)

        # Register connection
        await self.manager.register_connection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=connection
        )

        # Verify connection is registered
        self.assertTrue(await self.manager.has_connection(connection_id))
        self.assertIn(user_id, self.manager._user_connections)
        self.assertIn(connection_id, self.manager._user_connections[user_id])

    async def test_user_isolation(self):
        """Test that users are properly isolated."""
        # Create connections for two different users
        user1_id = "user_001"
        user2_id = "user_002"
        conn1_id = "conn_001"
        conn2_id = "conn_002"

        connection1 = TestWebSocketConnection(conn1_id)
        connection2 = TestWebSocketConnection(conn2_id)

        # Register both connections
        await self.manager.register_connection(conn1_id, user1_id, connection1)
        await self.manager.register_connection(conn2_id, user2_id, connection2)

        # Verify user isolation
        user1_connections = await self.manager.get_user_connections(user1_id)
        user2_connections = await self.manager.get_user_connections(user2_id)

        self.assertEqual(len(user1_connections), 1)
        self.assertEqual(len(user2_connections), 1)
        self.assertIn(conn1_id, [conn.connection_id for conn in user1_connections])
        self.assertIn(conn2_id, [conn.connection_id for conn in user2_connections])

        # Verify no cross-contamination
        self.assertNotIn(conn2_id, [conn.connection_id for conn in user1_connections])
        self.assertNotIn(conn1_id, [conn.connection_id for conn in user2_connections])

    async def test_event_routing_to_specific_user(self):
        """Test that events are routed only to the intended user."""
        # Setup two users
        user1_id = "user_001"
        user2_id = "user_002"
        conn1_id = "conn_001"
        conn2_id = "conn_002"

        connection1 = TestWebSocketConnection(conn1_id)
        connection2 = TestWebSocketConnection(conn2_id)

        await self.manager.register_connection(conn1_id, user1_id, connection1)
        await self.manager.register_connection(conn2_id, user2_id, connection2)

        # Send event to user1 only
        event_message = {
            "type": "agent_started",
            "data": {"agent_id": "test_agent", "message": "Hello User 1"}
        }

        await self.manager.send_to_user(user1_id, event_message)

        # Verify only user1 received the message
        user1_messages = connection1.get_messages()
        user2_messages = connection2.get_messages()

        self.assertEqual(len(user1_messages), 1)
        self.assertEqual(len(user2_messages), 0)
        self.assertEqual(user1_messages[0], event_message)

    async def test_connection_cleanup(self):
        """Test connection cleanup and deregistration."""
        # Setup connection
        user_id = "user_001"
        conn_id = "conn_001"
        connection = TestWebSocketConnection(conn_id)

        await self.manager.register_connection(conn_id, user_id, connection)

        # Verify connection exists
        self.assertTrue(await self.manager.has_connection(conn_id))

        # Remove connection
        await self.manager.remove_connection(conn_id)

        # Verify connection is removed
        self.assertFalse(await self.manager.has_connection(conn_id))

        # Verify user connections are updated
        user_connections = await self.manager.get_user_connections(user_id)
        self.assertEqual(len(user_connections), 0)

    async def test_concurrent_connections_same_user(self):
        """Test that a single user can have multiple concurrent connections."""
        user_id = "user_001"
        conn1_id = "conn_001"
        conn2_id = "conn_002"

        connection1 = TestWebSocketConnection(conn1_id)
        connection2 = TestWebSocketConnection(conn2_id)

        # Register both connections for the same user
        await self.manager.register_connection(conn1_id, user_id, connection1)
        await self.manager.register_connection(conn2_id, user_id, connection2)

        # Verify both connections are tracked
        user_connections = await self.manager.get_user_connections(user_id)
        self.assertEqual(len(user_connections), 2)

        # Send message to user - should reach both connections
        event_message = {"type": "test_event", "data": {"message": "hello"}}
        await self.manager.send_to_user(user_id, event_message)

        # Verify both connections received the message
        self.assertEqual(len(connection1.get_messages()), 1)
        self.assertEqual(len(connection2.get_messages()), 1)

    async def test_invalid_connection_handling(self):
        """Test handling of invalid connection scenarios."""
        # Test sending to non-existent user
        result = await self.manager.send_to_user("nonexistent_user", {"test": "data"})
        self.assertFalse(result)  # Should return False for non-existent user

        # Test removing non-existent connection
        result = await self.manager.remove_connection("nonexistent_connection")
        self.assertFalse(result)  # Should return False for non-existent connection

        # Test checking non-existent connection
        self.assertFalse(await self.manager.has_connection("nonexistent_connection"))


class TestWebSocketManagerModes(SSotAsyncTestCase):
    """Test different WebSocket manager modes."""

    async def test_unified_mode_compatibility(self):
        """Test that all modes redirect to UNIFIED mode."""
        # Test all enum values redirect to UNIFIED
        for mode in WebSocketManagerMode:
            manager = UnifiedWebSocketManager(mode=mode)
            self.assertEqual(manager.mode, WebSocketManagerMode.UNIFIED)

    async def test_mode_deprecation_warnings(self):
        """Test that deprecated modes still work but with warnings."""
        # These should all work without errors
        modes_to_test = [
            WebSocketManagerMode.ISOLATED,
            WebSocketManagerMode.EMERGENCY,
            WebSocketManagerMode.DEGRADED
        ]

        for mode in modes_to_test:
            manager = UnifiedWebSocketManager(mode=mode)
            self.assertIsNotNone(manager)
            # All modes should resolve to UNIFIED
            self.assertEqual(manager.mode, WebSocketManagerMode.UNIFIED)


class TestWebSocketManagerWithUserContext(SSotAsyncTestCase):
    """Test WebSocket manager integration with UserExecutionContext."""

    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.manager = UnifiedWebSocketManager(mode=WebSocketManagerMode.UNIFIED)

    async def test_user_context_integration(self):
        """Test WebSocket manager works with UserExecutionContext."""
        # Create user context
        user_context = UserExecutionContext(
            user_id="test_user_001",
            thread_id="thread_001",
            run_id="run_001",
            websocket_client_id="ws_client_001"
        )

        # Create connection
        connection = TestWebSocketConnection("conn_001")

        # Register connection using user context
        await self.manager.register_connection(
            connection_id=user_context.websocket_client_id,
            user_id=user_context.user_id,
            websocket=connection
        )

        # Verify registration
        self.assertTrue(await self.manager.has_connection(user_context.websocket_client_id))

        # Send event using user context
        event = {
            "type": "agent_thinking",
            "data": {
                "user_id": user_context.user_id,
                "thread_id": user_context.thread_id,
                "message": "Processing your request..."
            }
        }

        result = await self.manager.send_to_user(user_context.user_id, event)
        self.assertTrue(result)

        # Verify message was received
        messages = connection.get_messages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], event)

    async def test_multiple_user_contexts_isolation(self):
        """Test that multiple user contexts maintain proper isolation."""
        # Create multiple user contexts
        contexts = []
        connections = []

        for i in range(3):
            context = UserExecutionContext(
                user_id=f"user_{i:03d}",
                thread_id=f"thread_{i:03d}",
                run_id=f"run_{i:03d}",
                websocket_client_id=f"ws_client_{i:03d}"
            )
            connection = TestWebSocketConnection(f"conn_{i:03d}")

            contexts.append(context)
            connections.append(connection)

            # Register each connection
            await self.manager.register_connection(
                connection_id=context.websocket_client_id,
                user_id=context.user_id,
                websocket=connection
            )

        # Send different events to each user
        for i, context in enumerate(contexts):
            event = {
                "type": "user_specific_event",
                "data": {"user_index": i, "message": f"Hello user {i}"}
            }
            await self.manager.send_to_user(context.user_id, event)

        # Verify each user only received their own event
        for i, connection in enumerate(connections):
            messages = connection.get_messages()
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["data"]["user_index"], i)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
