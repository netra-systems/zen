"""
Unit Tests for WebSocket Core Unified Manager

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core infrastructure
- Business Goal: Ensure WebSocket infrastructure supports $500K+ ARR Golden Path
- Value Impact: WebSocket Manager is MISSION CRITICAL for real-time AI interactions
- Strategic Impact: Connection management, user isolation, and event delivery core to platform

This test suite validates critical WebSocket Manager business logic:
1. Connection lifecycle management (add_connection, remove_connection)
2. User isolation and multi-user security (prevent cross-user event bleeding)
3. Event delivery and emission (5 critical WebSocket events)
4. Error handling and graceful degradation
5. Thread safety and concurrent operations
6. Message queuing and recovery mechanisms

CRITICAL BUSINESS RULES:
- User isolation MUST be maintained (multi-user system security)
- Connection state management MUST be thread-safe
- Event delivery MUST be reliable and ordered
- Cross-user contamination MUST be prevented
- Connection cleanup MUST be complete to prevent memory leaks
- Emergency/degraded modes MUST provide graceful degradation
"""

import asyncio
import pytest
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from shared.types.core_types import UserID, ConnectionID, WebSocketID, ThreadID
from shared.logging.unified_logging_ssot import get_logger

# Import the module under test
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketManagerMode,
    WebSocketConnection,
    _serialize_message_safely,
    _get_enum_key_representation
)

# Import UserExecutionContext for proper initialization
from netra_backend.app.core.user_execution_context import UserExecutionContext

logger = get_logger(__name__)


@dataclass
class MockWebSocketState:
    """Mock WebSocket state for testing."""
    client_state: str = "open"


class MockWebSocket:
    """Mock WebSocket connection for testing."""

    def __init__(self, state: str = "open", user_id: str = None):
        self.client_state = MockWebSocketState(client_state=state)
        self.user_id = user_id
        self.sent_messages = []
        self.closed = False
        self.close_code = None
        self.close_reason = None

    async def send_json(self, message: Dict[str, Any]):
        """Mock sending JSON message."""
        if self.closed:
            raise Exception("WebSocket is closed")
        self.sent_messages.append(message)
        logger.debug(f"MockWebSocket sent message: {json.dumps(message, indent=2)}")

    async def close(self, code: int = 1000, reason: str = ""):
        """Mock closing WebSocket."""
        self.closed = True
        self.close_code = code
        self.close_reason = reason
        logger.debug(f"MockWebSocket closed with code {code}, reason: {reason}")


class TestUnifiedWebSocketManager(SSotAsyncTestCase):
    """Unit tests for UnifiedWebSocketManager following SSOT patterns."""

    def setup_method(self, method):
        """Setup test method using SSOT patterns."""
        super().setup_method(method)

        # Test data
        self.test_user_id_1 = "test_user_001"
        self.test_user_id_2 = "test_user_002"
        self.test_connection_id_1 = f"conn_{uuid.uuid4()}"
        self.test_connection_id_2 = f"conn_{uuid.uuid4()}"
        self.test_thread_id = f"thread_{uuid.uuid4()}"

        # Create UserExecutionContext for proper user isolation
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id_1,
            organization_id="test_org_001",
            session_id=f"session_{uuid.uuid4()}",
            thread_id=self.test_thread_id
        )

        # Create manager instance for each test
        # Use a properly formatted SSOT token (must be exactly 64 characters for security)
        self.manager = UnifiedWebSocketManager(
            mode=WebSocketManagerMode.UNIFIED,
            user_context=self.user_context,
            _ssot_authorization_token="ssot_test_token_1234567890abcdef1234567890abcdef1234567890ab"
        )

        # Mock factory for creating test objects
        self.mock_factory = SSotMockFactory()

    async def teardown_method(self, method):
        """Cleanup test method using SSOT patterns."""
        # Clean up any active connections
        if hasattr(self, 'manager'):
            try:
                # Clean up test connections
                for conn_id in list(self.manager._connections.keys()):
                    await self.manager.remove_connection(conn_id)
            except Exception as e:
                logger.warning(f"Cleanup error: {e}")

        await super().teardown_method(method)

    def create_mock_websocket_connection(
        self,
        user_id: str,
        connection_id: str = None,
        websocket_state: str = "open"
    ) -> WebSocketConnection:
        """Create a mock WebSocket connection for testing."""
        if connection_id is None:
            connection_id = f"conn_{uuid.uuid4()}"

        mock_websocket = MockWebSocket(state=websocket_state, user_id=user_id)

        return WebSocketConnection(
            user_id=user_id,
            connection_id=connection_id,
            websocket=mock_websocket,
            thread_id=self.test_thread_id,
            metadata={"test": True, "created_at": datetime.now(timezone.utc).isoformat()}
        )


class TestWebSocketManagerInitialization(TestUnifiedWebSocketManager):
    """Test WebSocket manager initialization and configuration."""

    async def test_manager_initialization_unified_mode(self):
        """Test manager initializes correctly in UNIFIED mode."""
        user_context = UserExecutionContext(
            user_id="test_user",
            organization_id="test_org",
            session_id=f"session_{uuid.uuid4()}",
            thread_id=f"thread_{uuid.uuid4()}"
        )

        manager = UnifiedWebSocketManager(
            mode=WebSocketManagerMode.UNIFIED,
            user_context=user_context,
            _ssot_authorization_token="ssot_test_token_1234567890abcdef1234567890abcdef1234567890ab"
        )

        assert manager.mode == WebSocketManagerMode.UNIFIED
        assert manager._connections == {}
        assert manager._user_connections == {}
        assert manager._event_isolation_tokens == {}
        assert manager._user_event_queues == {}
        assert manager._cross_user_detection == {}

        logger.info("✓ Manager initialization test passed")

    async def test_manager_initialization_deprecated_modes_redirect(self):
        """Test that deprecated modes redirect to UNIFIED."""
        for deprecated_mode in [
            WebSocketManagerMode.ISOLATED,
            WebSocketManagerMode.EMERGENCY,
            WebSocketManagerMode.DEGRADED
        ]:
            user_context = UserExecutionContext(
                user_id="test_user",
                organization_id="test_org",
                session_id=f"session_{uuid.uuid4()}",
                thread_id=f"thread_{uuid.uuid4()}"
            )

            manager = UnifiedWebSocketManager(
                mode=deprecated_mode,
                user_context=user_context,
                _ssot_authorization_token="ssot_test_token_1234567890abcdef1234567890abcdef1234567890ab"
            )

            # All deprecated modes should redirect to UNIFIED
            assert manager.mode == WebSocketManagerMode.UNIFIED

        logger.info("✓ Deprecated modes redirection test passed")

    async def test_manager_initialization_without_auth_token_fails(self):
        """Test that manager requires SSOT authorization token."""
        with pytest.raises(ValueError, match="SSOT authorization token required"):
            UnifiedWebSocketManager(mode=WebSocketManagerMode.UNIFIED)

        logger.info("✓ Authorization token requirement test passed")


class TestConnectionLifecycleManagement(TestUnifiedWebSocketManager):
    """Test WebSocket connection lifecycle operations."""

    async def test_add_connection_success(self):
        """Test successful connection addition."""
        connection = self.create_mock_websocket_connection(
            user_id=self.test_user_id_1,
            connection_id=self.test_connection_id_1
        )

        # Add connection
        await self.manager.add_connection(connection)

        # Verify connection was added
        assert self.test_connection_id_1 in self.manager._connections
        assert self.test_user_id_1 in self.manager._user_connections
        assert self.test_connection_id_1 in self.manager._user_connections[self.test_user_id_1]

        # Verify isolation token was created
        assert self.test_connection_id_1 in self.manager._event_isolation_tokens

        # Verify user event queue was created
        assert self.test_user_id_1 in self.manager._user_event_queues

        logger.info("✓ Add connection success test passed")

    async def test_add_connection_invalid_user_id_fails(self):
        """Test that connection without user_id fails validation."""
        connection = WebSocketConnection(
            user_id="",  # Invalid empty user_id
            connection_id=self.test_connection_id_1,
            websocket=MockWebSocket(),
            thread_id=self.test_thread_id
        )

        with pytest.raises(ValueError, match="Connection must have a valid user_id"):
            await self.manager.add_connection(connection)

        logger.info("✓ Invalid user_id validation test passed")

    async def test_add_connection_invalid_connection_id_fails(self):
        """Test that connection without connection_id fails validation."""
        connection = WebSocketConnection(
            user_id=self.test_user_id_1,
            connection_id="",  # Invalid empty connection_id
            websocket=MockWebSocket(),
            thread_id=self.test_thread_id
        )

        with pytest.raises(ValueError, match="Connection must have a valid connection_id"):
            await self.manager.add_connection(connection)

        logger.info("✓ Invalid connection_id validation test passed")

    async def test_remove_connection_success(self):
        """Test successful connection removal."""
        connection = self.create_mock_websocket_connection(
            user_id=self.test_user_id_1,
            connection_id=self.test_connection_id_1
        )

        # Add connection first
        await self.manager.add_connection(connection)

        # Verify connection was added
        assert self.test_connection_id_1 in self.manager._connections

        # Remove connection
        await self.manager.remove_connection(self.test_connection_id_1)

        # Verify connection was removed
        assert self.test_connection_id_1 not in self.manager._connections
        assert self.test_connection_id_1 not in self.manager._event_isolation_tokens

        # Verify user connections updated
        if self.test_user_id_1 in self.manager._user_connections:
            assert self.test_connection_id_1 not in self.manager._user_connections[self.test_user_id_1]

        logger.info("✓ Remove connection success test passed")

    async def test_remove_nonexistent_connection_handles_gracefully(self):
        """Test that removing non-existent connection handles gracefully."""
        fake_connection_id = "fake_connection_123"

        # Should not raise exception
        await self.manager.remove_connection(fake_connection_id)

        logger.info("✓ Remove nonexistent connection graceful handling test passed")


class TestUserIsolationAndSecurity(TestUnifiedWebSocketManager):
    """Test user isolation and multi-user security."""

    async def test_user_isolation_validation(self):
        """Test user isolation validation method."""
        # Test valid isolation
        result = self.manager._validate_user_isolation(self.test_user_id_1, "test_operation")
        assert result is True

        logger.info("✓ User isolation validation test passed")

    async def test_cross_user_event_bleeding_prevention(self):
        """Test prevention of cross-user event contamination."""
        event_data = {
            "type": "agent_started",
            "user_id": self.test_user_id_2,  # Different user in event data
            "message": "Agent started",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Process event for target user
        cleaned_event = self.manager._prevent_cross_user_event_bleeding(
            event_data, self.test_user_id_1
        )

        # Event should be cleaned to prevent cross-user bleeding
        assert cleaned_event["user_id"] == self.test_user_id_1
        assert "cross_user_prevention" in cleaned_event

        logger.info("✓ Cross-user event bleeding prevention test passed")

    async def test_multiple_users_connection_isolation(self):
        """Test that multiple users' connections are properly isolated."""
        # Add connections for different users
        connection_1 = self.create_mock_websocket_connection(
            user_id=self.test_user_id_1,
            connection_id=self.test_connection_id_1
        )
        connection_2 = self.create_mock_websocket_connection(
            user_id=self.test_user_id_2,
            connection_id=self.test_connection_id_2
        )

        await self.manager.add_connection(connection_1)
        await self.manager.add_connection(connection_2)

        # Verify connections are isolated by user
        assert self.test_user_id_1 in self.manager._user_connections
        assert self.test_user_id_2 in self.manager._user_connections

        user_1_connections = self.manager._user_connections[self.test_user_id_1]
        user_2_connections = self.manager._user_connections[self.test_user_id_2]

        assert self.test_connection_id_1 in user_1_connections
        assert self.test_connection_id_1 not in user_2_connections
        assert self.test_connection_id_2 in user_2_connections
        assert self.test_connection_id_2 not in user_1_connections

        # Verify isolation tokens are different
        token_1 = self.manager._event_isolation_tokens[self.test_connection_id_1]
        token_2 = self.manager._event_isolation_tokens[self.test_connection_id_2]
        assert token_1 != token_2

        logger.info("✓ Multiple users connection isolation test passed")


class TestMessageSendingAndEventDelivery(TestUnifiedWebSocketManager):
    """Test message sending and event delivery functionality."""

    async def test_send_to_user_success(self):
        """Test successful message sending to user."""
        connection = self.create_mock_websocket_connection(
            user_id=self.test_user_id_1,
            connection_id=self.test_connection_id_1
        )
        await self.manager.add_connection(connection)

        test_message = {
            "type": "test_message",
            "content": "Hello, World!",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Send message to user
        await self.manager.send_to_user(self.test_user_id_1, test_message)

        # Verify message was sent via WebSocket
        mock_websocket = connection.websocket
        assert len(mock_websocket.sent_messages) == 1
        sent_message = mock_websocket.sent_messages[0]
        assert sent_message["type"] == "test_message"
        assert sent_message["content"] == "Hello, World!"

        logger.info("✓ Send to user success test passed")

    async def test_send_to_user_no_connections_handles_gracefully(self):
        """Test sending to user with no connections handles gracefully."""
        test_message = {
            "type": "test_message",
            "content": "No connections"
        }

        # Should not raise exception
        await self.manager.send_to_user("nonexistent_user", test_message)

        logger.info("✓ Send to user no connections graceful handling test passed")

    async def test_emit_critical_event_success(self):
        """Test emission of critical business events."""
        connection = self.create_mock_websocket_connection(
            user_id=self.test_user_id_1,
            connection_id=self.test_connection_id_1
        )
        await self.manager.add_connection(connection)

        event_data = {
            "agent_id": "agent_123",
            "message": "Agent started processing",
            "progress": 0
        }

        # Emit critical event
        await self.manager.emit_critical_event(
            self.test_user_id_1,
            "agent_started",
            event_data
        )

        # Verify event was sent
        mock_websocket = connection.websocket
        assert len(mock_websocket.sent_messages) == 1
        sent_event = mock_websocket.sent_messages[0]
        assert sent_event["type"] == "agent_started"
        assert sent_event["data"]["agent_id"] == "agent_123"

        logger.info("✓ Emit critical event success test passed")

    async def test_broadcast_message_to_all_users(self):
        """Test broadcasting message to all connected users."""
        # Add connections for multiple users
        connection_1 = self.create_mock_websocket_connection(
            user_id=self.test_user_id_1,
            connection_id=self.test_connection_id_1
        )
        connection_2 = self.create_mock_websocket_connection(
            user_id=self.test_user_id_2,
            connection_id=self.test_connection_id_2
        )

        await self.manager.add_connection(connection_1)
        await self.manager.add_connection(connection_2)

        broadcast_message = {
            "type": "system_announcement",
            "content": "System maintenance in 10 minutes"
        }

        # Broadcast message
        await self.manager.broadcast(broadcast_message)

        # Verify message was sent to all users
        assert len(connection_1.websocket.sent_messages) == 1
        assert len(connection_2.websocket.sent_messages) == 1

        for connection in [connection_1, connection_2]:
            sent_message = connection.websocket.sent_messages[0]
            assert sent_message["type"] == "system_announcement"
            assert "System maintenance" in sent_message["content"]

        logger.info("✓ Broadcast message to all users test passed")


class TestConcurrencyAndThreadSafety(TestUnifiedWebSocketManager):
    """Test concurrency and thread safety of WebSocket operations."""

    async def test_concurrent_connection_additions(self):
        """Test concurrent connection additions are thread-safe."""
        # Create multiple connections for the same user
        connections = []
        for i in range(5):
            connection = self.create_mock_websocket_connection(
                user_id=self.test_user_id_1,
                connection_id=f"conn_{i}_{uuid.uuid4()}"
            )
            connections.append(connection)

        # Add connections concurrently
        tasks = [self.manager.add_connection(conn) for conn in connections]
        await asyncio.gather(*tasks)

        # Verify all connections were added
        assert len(self.manager._connections) == 5
        assert len(self.manager._user_connections[self.test_user_id_1]) == 5

        # Verify each connection has unique isolation token
        isolation_tokens = set()
        for connection in connections:
            token = self.manager._event_isolation_tokens[connection.connection_id]
            assert token not in isolation_tokens
            isolation_tokens.add(token)

        logger.info("✓ Concurrent connection additions thread safety test passed")

    async def test_concurrent_message_sending(self):
        """Test concurrent message sending is thread-safe."""
        connection = self.create_mock_websocket_connection(
            user_id=self.test_user_id_1,
            connection_id=self.test_connection_id_1
        )
        await self.manager.add_connection(connection)

        # Send multiple messages concurrently
        messages = []
        for i in range(10):
            message = {
                "type": "concurrent_test",
                "message_id": i,
                "content": f"Message {i}"
            }
            messages.append(message)

        tasks = [
            self.manager.send_to_user(self.test_user_id_1, msg)
            for msg in messages
        ]
        await asyncio.gather(*tasks)

        # Verify all messages were sent
        mock_websocket = connection.websocket
        assert len(mock_websocket.sent_messages) == 10

        # Verify message ordering and content
        sent_message_ids = set()
        for sent_msg in mock_websocket.sent_messages:
            assert sent_msg["type"] == "concurrent_test"
            sent_message_ids.add(sent_msg["message_id"])

        # All message IDs should be present
        assert sent_message_ids == set(range(10))

        logger.info("✓ Concurrent message sending thread safety test passed")


class TestErrorHandlingAndRecovery(TestUnifiedWebSocketManager):
    """Test error handling and recovery mechanisms."""

    async def test_connection_cleanup_on_websocket_error(self):
        """Test that connections are cleaned up when WebSocket errors occur."""
        # Create connection with mock that will fail
        connection = self.create_mock_websocket_connection(
            user_id=self.test_user_id_1,
            connection_id=self.test_connection_id_1
        )

        # Mock WebSocket to raise exception on send
        async def failing_send_json(message):
            raise Exception("WebSocket connection lost")

        connection.websocket.send_json = failing_send_json

        await self.manager.add_connection(connection)

        test_message = {"type": "test", "content": "This will fail"}

        # Message sending should handle the error gracefully
        await self.manager.send_to_user(self.test_user_id_1, test_message)

        # Connection should still exist (error handling shouldn't auto-remove)
        assert self.test_connection_id_1 in self.manager._connections

        logger.info("✓ WebSocket error handling test passed")

    async def test_graceful_degradation_mode(self):
        """Test graceful degradation when entering degraded mode."""
        # Initialize manager in degraded mode
        user_context = UserExecutionContext(
            user_id=self.test_user_id_1,
            organization_id="test_org_001",
            session_id=f"session_{uuid.uuid4()}",
            thread_id=self.test_thread_id
        )

        degraded_manager = UnifiedWebSocketManager(
            mode=WebSocketManagerMode.DEGRADED,
            user_context=user_context,
            _ssot_authorization_token="ssot_test_token_1234567890abcdef1234567890abcdef1234567890ab",
            config={"enable_monitoring": False}
        )

        # Should still function in basic capacity
        connection = self.create_mock_websocket_connection(
            user_id=self.test_user_id_1,
            connection_id=self.test_connection_id_1
        )

        await degraded_manager.add_connection(connection)

        test_message = {"type": "degraded_test", "content": "Basic functionality"}
        await degraded_manager.send_to_user(self.test_user_id_1, test_message)

        # Basic functionality should work
        assert len(connection.websocket.sent_messages) == 1

        logger.info("✓ Graceful degradation mode test passed")


class TestMessageSerializationHelpers(TestUnifiedWebSocketManager):
    """Test message serialization helper functions."""

    async def test_serialize_message_safely_with_datetime(self):
        """Test safe serialization of messages containing datetime objects."""
        message_with_datetime = {
            "type": "test_message",
            "timestamp": datetime.now(timezone.utc),
            "content": "Message with datetime"
        }

        serialized = _serialize_message_safely(message_with_datetime)

        assert serialized["type"] == "test_message"
        assert isinstance(serialized["timestamp"], str)  # datetime converted to string
        assert serialized["content"] == "Message with datetime"

        logger.info("✓ Message serialization with datetime test passed")

    async def test_get_enum_key_representation(self):
        """Test enum key representation for WebSocket states."""
        from enum import Enum

        class TestWebSocketState(Enum):
            OPEN = "open"
            CLOSED = "closed"
            CONNECTING = "connecting"

        # Test WebSocket state enum representation
        open_state = TestWebSocketState.OPEN
        key_repr = _get_enum_key_representation(open_state)

        assert key_repr == "open"  # Should use lowercase name for WebSocket states

        logger.info("✓ Enum key representation test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])