"""Comprehensive unit tests for IsolatedWebSocketManager.

This test suite provides 100% method coverage of the IsolatedWebSocketManager class
with focus on security, user isolation, and strongly typed ID integration.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Ensure WebSocket communication security and prevent user data leakage
- Value Impact: Validates complete user isolation in multi-user AI chat sessions
- Strategic Impact: Prevents security breaches that could destroy business trust

Test Coverage Areas:
1. Initialization & Context Validation - Proper setup with UserExecutionContext
2. Connection Management - Add/remove connections with user validation
3. Message Routing - Isolated message delivery per user
4. Security Validation - Connection ownership and access control
5. Strongly Typed IDs - Integration with shared.types.core_types
6. Resource Management - Cleanup and memory leak prevention
7. Error Handling - Invalid connections, malformed messages, timeouts
8. Metrics & Health - Manager statistics and health monitoring
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

# Core imports
from netra_backend.app.websocket_core.websocket_manager_factory import IsolatedWebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from shared.types.core_types import (
    UserID, ThreadID, ConnectionID, WebSocketID, RequestID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id
)
from fastapi.websockets import WebSocketState


class TestIsolatedWebSocketManagerComprehensive:
    """Comprehensive test suite for IsolatedWebSocketManager."""
    
    @pytest.fixture
    def user_context(self):
        """Create a valid UserExecutionContext for testing."""
        return UserExecutionContext(
            user_id="test-user-12345",
            thread_id="thread-test-12345",
            run_id="run-test-12345",
            request_id="req-test-12345",
            agent_context={
                "agent_type": "test_agent",
                "execution_mode": "isolated"
            }
        )
    
    @pytest.fixture
    def different_user_context(self):
        """Create a UserExecutionContext for a different user to test isolation."""
        return UserExecutionContext(
            user_id="different-user-67890",
            thread_id="thread-different-67890",
            run_id="run-different-67890",
            request_id="req-different-67890",
            agent_context={
                "agent_type": "test_agent",
                "execution_mode": "isolated"
            }
        )
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        websocket = AsyncMock()
        websocket.client_state = WebSocketState.CONNECTED
        websocket.send_json = AsyncMock()
        return websocket
    
    @pytest.fixture
    def websocket_connection(self, user_context, mock_websocket):
        """Create a valid WebSocketConnection for testing."""
        return WebSocketConnection(
            connection_id="conn-test-12345",
            user_id=user_context.user_id,
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc),
            metadata={"test": "metadata"},
            thread_id="thread-test-12345"
        )
    
    @pytest.fixture
    def different_user_connection(self, different_user_context, mock_websocket):
        """Create a WebSocketConnection for a different user."""
        return WebSocketConnection(
            connection_id="conn-different-67890",
            user_id=different_user_context.user_id,
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc),
            metadata={"test": "metadata"}
        )

    # ==========================================================================
    # INITIALIZATION TESTS
    # ==========================================================================
    
    def test_init_valid_context(self, user_context):
        """Test successful initialization with valid UserExecutionContext."""
        manager = IsolatedWebSocketManager(user_context)
        
        assert manager.user_context == user_context
        assert manager._is_active is True
        assert len(manager._connections) == 0
        assert len(manager._connection_ids) == 0
        assert manager._message_queue.maxsize == 1000
        assert manager._connection_error_count == 0
        assert manager._last_error_time is None
        assert len(manager._message_recovery_queue) == 0
        
        # Validate metrics initialization
        assert manager._metrics is not None
        assert manager._metrics.connections_managed == 0
        
        # Validate lifecycle manager initialization
        assert manager._lifecycle_manager is not None

    def test_init_invalid_context_type(self):
        """Test initialization fails with invalid context type."""
        with pytest.raises(ValueError, match="user_context must be a UserExecutionContext instance"):
            IsolatedWebSocketManager("invalid_context")
    
    def test_init_none_context(self):
        """Test initialization fails with None context."""
        with pytest.raises(ValueError, match="user_context must be a UserExecutionContext instance"):
            IsolatedWebSocketManager(None)

    # ==========================================================================
    # CONNECTION MANAGEMENT TESTS
    # ==========================================================================
    
    @pytest.mark.asyncio
    async def test_add_connection_success(self, user_context, websocket_connection):
        """Test successful connection addition."""
        manager = IsolatedWebSocketManager(user_context)
        
        await manager.add_connection(websocket_connection)
        
        assert len(manager._connections) == 1
        assert websocket_connection.connection_id in manager._connections
        assert websocket_connection.connection_id in manager._connection_ids
        assert manager._metrics.connections_managed == 1
    
    @pytest.mark.asyncio
    async def test_add_connection_wrong_user_security_violation(self, user_context, different_user_connection):
        """Test security violation when adding connection for wrong user."""
        manager = IsolatedWebSocketManager(user_context)
        
        with pytest.raises(ValueError, match="Connection user_id .* does not match manager user_id"):
            await manager.add_connection(different_user_connection)
        
        # Ensure no connection was added
        assert len(manager._connections) == 0
        assert len(manager._connection_ids) == 0
    
    @pytest.mark.asyncio
    async def test_add_connection_inactive_manager(self, user_context, websocket_connection):
        """Test adding connection to inactive manager fails."""
        manager = IsolatedWebSocketManager(user_context)
        manager._is_active = False
        
        with pytest.raises(RuntimeError, match="WebSocket manager .* is no longer active"):
            await manager.add_connection(websocket_connection)
    
    @pytest.mark.asyncio
    async def test_remove_connection_success(self, user_context, websocket_connection):
        """Test successful connection removal."""
        manager = IsolatedWebSocketManager(user_context)
        
        # Add connection first
        await manager.add_connection(websocket_connection)
        assert len(manager._connections) == 1
        
        # Remove connection
        await manager.remove_connection(websocket_connection.connection_id)
        
        assert len(manager._connections) == 0
        assert websocket_connection.connection_id not in manager._connection_ids
        assert manager._metrics.connections_managed == 0
    
    @pytest.mark.asyncio
    async def test_remove_connection_nonexistent(self, user_context):
        """Test removing non-existent connection."""
        manager = IsolatedWebSocketManager(user_context)
        
        # Should not raise error, just log debug message
        await manager.remove_connection("nonexistent-connection")
        
        assert len(manager._connections) == 0
    
    @pytest.mark.asyncio
    async def test_remove_connection_wrong_user_security(self, user_context, different_user_connection):
        """Test security check when removing connection with wrong user."""
        manager = IsolatedWebSocketManager(user_context)
        
        # Manually add connection to bypass add_connection security (simulating corruption)
        manager._connections[different_user_connection.connection_id] = different_user_connection
        manager._connection_ids.add(different_user_connection.connection_id)
        
        # Should not remove connection due to security violation
        await manager.remove_connection(different_user_connection.connection_id)
        
        # Connection should still be there (security prevented removal)
        assert different_user_connection.connection_id in manager._connections

    def test_get_connection_success(self, user_context, websocket_connection):
        """Test successful connection retrieval."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        
        retrieved = manager.get_connection(websocket_connection.connection_id)
        
        assert retrieved == websocket_connection
    
    def test_get_connection_nonexistent(self, user_context):
        """Test retrieving non-existent connection returns None."""
        manager = IsolatedWebSocketManager(user_context)
        
        result = manager.get_connection("nonexistent")
        
        assert result is None
    
    def test_get_connection_inactive_manager(self, user_context, websocket_connection):
        """Test getting connection from inactive manager fails."""
        manager = IsolatedWebSocketManager(user_context)
        manager._is_active = False
        
        with pytest.raises(RuntimeError, match="WebSocket manager .* is no longer active"):
            manager.get_connection(websocket_connection.connection_id)

    def test_get_user_connections(self, user_context, websocket_connection):
        """Test getting all connection IDs for user."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        manager._connection_ids.add(websocket_connection.connection_id)
        
        connections = manager.get_user_connections()
        
        assert isinstance(connections, set)
        assert websocket_connection.connection_id in connections
        assert len(connections) == 1
    
    def test_get_user_connections_empty(self, user_context):
        """Test getting connections when none exist."""
        manager = IsolatedWebSocketManager(user_context)
        
        connections = manager.get_user_connections()
        
        assert isinstance(connections, set)
        assert len(connections) == 0

    # ==========================================================================
    # CONNECTION HEALTH AND VALIDATION TESTS  
    # ==========================================================================
    
    def test_is_connection_active_valid_user(self, user_context, websocket_connection):
        """Test connection activity check for valid user."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        manager._connection_ids.add(websocket_connection.connection_id)
        
        is_active = manager.is_connection_active(user_context.user_id)
        
        assert is_active is True
    
    def test_is_connection_active_different_user_security(self, user_context, different_user_context):
        """Test security violation when checking different user's connections."""
        manager = IsolatedWebSocketManager(user_context)
        
        is_active = manager.is_connection_active(different_user_context.user_id)
        
        assert is_active is False  # Security violation returns False
    
    def test_is_connection_active_no_connections(self, user_context):
        """Test connection activity when no connections exist."""
        manager = IsolatedWebSocketManager(user_context)
        
        is_active = manager.is_connection_active(user_context.user_id)
        
        assert is_active is False
    
    def test_is_connection_active_invalid_websocket(self, user_context):
        """Test connection activity when WebSocket is None."""
        manager = IsolatedWebSocketManager(user_context)
        
        # Create connection with None websocket
        bad_connection = WebSocketConnection(
            connection_id="bad-conn",
            user_id=user_context.user_id,
            websocket=None,
            connected_at=datetime.utcnow()
        )
        manager._connections["bad-conn"] = bad_connection
        manager._connection_ids.add("bad-conn")
        
        is_active = manager.is_connection_active(user_context.user_id)
        
        assert is_active is False

    # ==========================================================================
    # MESSAGE ROUTING AND ISOLATION TESTS
    # ==========================================================================
    
    @pytest.mark.asyncio
    async def test_send_to_user_success(self, user_context, websocket_connection):
        """Test successful message delivery to user."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        manager._connection_ids.add(websocket_connection.connection_id)
        
        message = {"type": "test_message", "data": "test_data"}
        
        await manager.send_to_user(message)
        
        # Verify message was sent
        websocket_connection.websocket.send_json.assert_called_once()
        assert manager._metrics.messages_sent_total == 1
        assert manager._metrics.messages_failed_total == 0
    
    @pytest.mark.asyncio
    async def test_send_to_user_no_connections(self, user_context):
        """Test message delivery when no connections exist."""
        manager = IsolatedWebSocketManager(user_context)
        
        message = {"type": "test_message", "data": "test_data"}
        
        await manager.send_to_user(message)
        
        # Should add to recovery queue
        assert len(manager._message_recovery_queue) == 1
        assert manager._message_recovery_queue[0]["type"] == "test_message"
        assert manager._message_recovery_queue[0]["failure_reason"] == "no_connections"
        assert manager._metrics.messages_failed_total == 1
    
    @pytest.mark.asyncio
    async def test_send_to_user_websocket_send_error(self, user_context, websocket_connection):
        """Test message delivery with WebSocket send error."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        manager._connection_ids.add(websocket_connection.connection_id)
        
        # Mock send_json to raise a generic exception
        websocket_connection.websocket.send_json.side_effect = Exception("Send failed")
        
        message = {"type": "test_message", "data": "test_data"}
        
        await manager.send_to_user(message)
        
        # Connection should be removed after error
        assert len(manager._connections) == 0
        assert manager._connection_error_count == 1
        assert manager._last_error_time is not None
        assert manager._metrics.messages_failed_total == 1
    
    @pytest.mark.asyncio
    async def test_send_to_user_websocket_disconnected(self, user_context, websocket_connection):
        """Test message delivery to disconnected WebSocket."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        manager._connection_ids.add(websocket_connection.connection_id)
        
        # Set WebSocket to disconnected state
        websocket_connection.websocket.client_state = WebSocketState.DISCONNECTED
        
        message = {"type": "test_message", "data": "test_data"}
        
        await manager.send_to_user(message)
        
        # Connection should be removed
        assert len(manager._connections) == 0
        assert manager._metrics.messages_failed_total == 1
    
    @pytest.mark.asyncio
    async def test_send_to_user_inactive_manager(self, user_context):
        """Test sending message from inactive manager fails."""
        manager = IsolatedWebSocketManager(user_context)
        manager._is_active = False
        
        message = {"type": "test_message", "data": "test_data"}
        
        with pytest.raises(RuntimeError, match="WebSocket manager .* is no longer active"):
            await manager.send_to_user(message)

    @pytest.mark.asyncio
    async def test_emit_critical_event_success(self, user_context, websocket_connection):
        """Test successful critical event emission."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        manager._connection_ids.add(websocket_connection.connection_id)
        
        event_data = {"agent_id": "test-agent", "status": "started"}
        
        await manager.emit_critical_event("agent_started", event_data)
        
        # Verify critical event was sent with proper structure
        websocket_connection.websocket.send_json.assert_called_once()
        call_args = websocket_connection.websocket.send_json.call_args[0][0]
        
        assert call_args["type"] == "agent_started"
        assert call_args["data"] == event_data
        assert call_args["critical"] is True
        assert call_args["user_context"]["user_id"] == user_context.user_id
        assert call_args["user_context"]["request_id"] == user_context.request_id
    
    @pytest.mark.asyncio
    async def test_emit_critical_event_empty_type(self, user_context):
        """Test critical event emission with empty event type."""
        manager = IsolatedWebSocketManager(user_context)
        
        with pytest.raises(ValueError, match="event_type cannot be empty"):
            await manager.emit_critical_event("", {"data": "test"})
    
    @pytest.mark.asyncio
    async def test_emit_critical_event_send_failure(self, user_context, websocket_connection):
        """Test critical event emission failure handling."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        manager._connection_ids.add(websocket_connection.connection_id)
        
        # Mock send failure
        websocket_connection.websocket.send_json.side_effect = Exception("Send failed")
        
        event_data = {"agent_id": "test-agent", "status": "started"}
        
        with pytest.raises(Exception, match="Send failed"):
            await manager.emit_critical_event("agent_started", event_data)
        
        # Should add to recovery queue
        assert len(manager._message_recovery_queue) == 1
        recovery_msg = manager._message_recovery_queue[0]
        assert recovery_msg["type"] == "agent_started"
        assert "emission_error" in recovery_msg["failure_reason"]

    # ==========================================================================
    # THREAD MANAGEMENT AND COMPATIBILITY TESTS
    # ==========================================================================
    
    def test_update_connection_thread_success(self, user_context, websocket_connection):
        """Test successful thread ID update."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        
        new_thread_id = "new-thread-12345"
        result = manager.update_connection_thread(websocket_connection.connection_id, new_thread_id)
        
        assert result is True
        assert websocket_connection.thread_id == new_thread_id
    
    def test_update_connection_thread_nonexistent_connection(self, user_context):
        """Test thread update for non-existent connection."""
        manager = IsolatedWebSocketManager(user_context)
        
        result = manager.update_connection_thread("nonexistent", "thread-123")
        
        assert result is False
    
    def test_update_connection_thread_no_thread_attribute(self, user_context):
        """Test thread update when connection lacks thread_id attribute."""
        manager = IsolatedWebSocketManager(user_context)
        
        # Create connection without thread_id attribute
        mock_connection = Mock()
        del mock_connection.thread_id  # Remove the attribute
        manager._connections["test-conn"] = mock_connection
        
        result = manager.update_connection_thread("test-conn", "thread-123")
        
        assert result is False

    def test_get_connection_id_by_websocket_found(self, user_context, websocket_connection):
        """Test finding connection ID by WebSocket instance."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        
        found_id = manager.get_connection_id_by_websocket(websocket_connection.websocket)
        
        assert found_id == ConnectionID(websocket_connection.connection_id)
    
    def test_get_connection_id_by_websocket_not_found(self, user_context):
        """Test WebSocket lookup when not found."""
        manager = IsolatedWebSocketManager(user_context)
        mock_websocket = Mock()
        
        found_id = manager.get_connection_id_by_websocket(mock_websocket)
        
        assert found_id is None

    @pytest.mark.asyncio
    async def test_send_to_thread_compatibility(self, user_context, websocket_connection):
        """Test thread-based message sending compatibility method."""
        manager = IsolatedWebSocketManager(user_context)
        websocket_connection.thread_id = "target-thread-123"
        manager._connections[websocket_connection.connection_id] = websocket_connection
        manager._connection_ids.add(websocket_connection.connection_id)
        
        message = {"type": "thread_message", "content": "Hello thread"}
        result = await manager.send_to_thread("target-thread-123", message)
        
        # Should find and send to connection with matching thread
        assert result is True
        websocket_connection.websocket.send_json.assert_called_once()

    # ==========================================================================
    # HEALTH AND METRICS TESTS
    # ==========================================================================
    
    def test_get_connection_health_valid_user(self, user_context, websocket_connection):
        """Test connection health check for valid user."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        manager._connection_ids.add(websocket_connection.connection_id)
        
        health = manager.get_connection_health(user_context.user_id)
        
        assert health["user_id"] == user_context.user_id
        assert health["total_connections"] == 1
        assert health["active_connections"] == 1
        assert health["has_active_connections"] is True
        assert health["manager_active"] is True
        assert len(health["connections"]) == 1
        
        conn_detail = health["connections"][0]
        assert conn_detail["connection_id"] == websocket_connection.connection_id
        assert conn_detail["active"] is True
        assert conn_detail["thread_id"] == websocket_connection.thread_id
    
    def test_get_connection_health_different_user_isolation(self, user_context, different_user_context):
        """Test health check isolation for different user."""
        manager = IsolatedWebSocketManager(user_context)
        
        health = manager.get_connection_health(different_user_context.user_id)
        
        assert health["error"] == "user_isolation_violation"
        assert "Cannot get health for different user" in health["message"]
    
    def test_get_manager_stats(self, user_context, websocket_connection):
        """Test comprehensive manager statistics."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        manager._connection_ids.add(websocket_connection.connection_id)
        manager._connection_error_count = 3
        manager._message_recovery_queue.append({"test": "message"})
        
        stats = manager.get_manager_stats()
        
        assert stats["manager_id"] == id(manager)
        assert stats["is_active"] is True
        assert stats["user_context"] == user_context.to_dict()
        assert stats["connections"]["total"] == 1
        assert websocket_connection.connection_id in stats["connections"]["connection_ids"]
        assert stats["recovery_queue_size"] == 1
        assert stats["error_count"] == 3

    # ==========================================================================
    # CLEANUP AND RESOURCE MANAGEMENT TESTS
    # ==========================================================================
    
    @pytest.mark.asyncio
    async def test_cleanup_all_connections(self, user_context, websocket_connection):
        """Test complete manager cleanup."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        manager._connection_ids.add(websocket_connection.connection_id)
        manager._message_recovery_queue.append({"test": "message"})
        
        await manager.cleanup_all_connections()
        
        # Manager should be deactivated and cleaned
        assert manager._is_active is False
        assert len(manager._connections) == 0
        assert len(manager._connection_ids) == 0
        assert len(manager._message_recovery_queue) == 0
        assert manager._metrics.cleanup_scheduled is True

    # ==========================================================================
    # STRONGLY TYPED ID INTEGRATION TESTS
    # ==========================================================================
    
    def test_strongly_typed_id_integration(self, user_context):
        """Test integration with strongly typed IDs from shared.types.core_types."""
        manager = IsolatedWebSocketManager(user_context)
        
        # Test ensure_* utility functions work correctly
        user_id = ensure_user_id("test-user-123")
        thread_id = ensure_thread_id("test-thread-123")
        websocket_id = ensure_websocket_id("test-websocket-123")
        
        assert isinstance(user_id, str)  # NewType still resolves to base type
        assert isinstance(thread_id, str)
        assert isinstance(websocket_id, str)
        
        # Test UserExecutionContext uses typed IDs
        assert isinstance(UserID(user_context.user_id), str)
        assert isinstance(ThreadID(user_context.thread_id), str)
        assert isinstance(RequestID(user_context.request_id), str)
    
    def test_connection_id_type_safety(self, user_context, mock_websocket):
        """Test ConnectionID type safety in WebSocket operations."""
        manager = IsolatedWebSocketManager(user_context)
        
        # Create connection with typed ID
        connection_id = ConnectionID("typed-conn-123")
        websocket_conn = WebSocketConnection(
            connection_id=str(connection_id),  # Convert to string for compatibility
            user_id=user_context.user_id,
            websocket=mock_websocket,
            connected_at=datetime.utcnow()
        )
        
        # Test get_connection_id_by_websocket returns typed ID
        manager._connections[str(connection_id)] = websocket_conn
        found_id = manager.get_connection_id_by_websocket(mock_websocket)
        
        assert isinstance(found_id, type(connection_id))
        assert found_id == connection_id

    # ==========================================================================
    # ERROR HANDLING AND EDGE CASES
    # ==========================================================================
    
    def test_validate_active_inactive_manager(self, user_context):
        """Test _validate_active method with inactive manager."""
        manager = IsolatedWebSocketManager(user_context)
        manager._is_active = False
        
        with pytest.raises(RuntimeError, match="WebSocket manager .* is no longer active"):
            manager._validate_active()
    
    def test_update_activity_metrics(self, user_context):
        """Test _update_activity updates metrics correctly."""
        manager = IsolatedWebSocketManager(user_context)
        initial_time = manager._metrics.last_activity
        
        # Small delay to ensure time difference
        import time
        time.sleep(0.001)
        
        manager._update_activity()
        
        assert manager._metrics.last_activity > initial_time
        assert manager._metrics.manager_age_seconds > 0
    
    @pytest.mark.asyncio
    async def test_message_serialization_safety(self, user_context, websocket_connection):
        """Test safe message serialization with complex objects."""
        manager = IsolatedWebSocketManager(user_context)
        manager._connections[websocket_connection.connection_id] = websocket_connection
        manager._connection_ids.add(websocket_connection.connection_id)
        
        # Message with complex objects that need serialization
        complex_message = {
            "type": "complex_message",
            "websocket_state": WebSocketState.CONNECTED,  # Enum that needs serialization
            "timestamp": datetime.now(timezone.utc),  # Datetime object
            "user_context": user_context  # Complex object
        }
        
        # Should not raise serialization errors
        await manager.send_to_user(complex_message)
        
        # Verify message was processed (exact serialization handled by _serialize_message_safely)
        websocket_connection.websocket.send_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_operations(self, user_context, mock_websocket):
        """Test thread safety of concurrent connection operations."""
        manager = IsolatedWebSocketManager(user_context)
        
        # Create multiple connections
        connections = []
        for i in range(5):
            conn = WebSocketConnection(
                connection_id=f"conn-{i}",
                user_id=user_context.user_id,
                websocket=AsyncMock(),
                connected_at=datetime.utcnow()
            )
            connections.append(conn)
        
        # Add connections concurrently
        tasks = [manager.add_connection(conn) for conn in connections]
        await asyncio.gather(*tasks)
        
        assert len(manager._connections) == 5
        assert len(manager._connection_ids) == 5
        
        # Remove connections concurrently
        remove_tasks = [manager.remove_connection(f"conn-{i}") for i in range(5)]
        await asyncio.gather(*remove_tasks)
        
        assert len(manager._connections) == 0
        assert len(manager._connection_ids) == 0

    @pytest.mark.asyncio 
    async def test_memory_leak_prevention(self, user_context, websocket_connection):
        """Test that cleanup prevents memory leaks."""
        manager = IsolatedWebSocketManager(user_context)
        
        # Add connection and fill recovery queue
        await manager.add_connection(websocket_connection)
        for i in range(10):
            manager._message_recovery_queue.append({"message": f"test-{i}"})
        
        # Verify resources exist
        assert len(manager._connections) == 1
        assert len(manager._message_recovery_queue) == 10
        
        # Cleanup should clear all references
        await manager.cleanup_all_connections()
        
        assert len(manager._connections) == 0
        assert len(manager._connection_ids) == 0
        assert len(manager._message_recovery_queue) == 0
        assert manager._is_active is False
        
        # Further operations should fail safely
        with pytest.raises(RuntimeError):
            await manager.add_connection(websocket_connection)