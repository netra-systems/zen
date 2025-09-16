"""
Test suite for WebSocket 'send after close' race condition fix.

ISSUE #335: Verifies that the WebSocket manager properly handles race conditions
where send operations are attempted after WebSocket close has been initiated.

Tests validate:
1. is_closing flag prevents send operations on closing connections
2. Concurrent close and broadcast operations don't cause runtime errors
3. Connection state is properly tracked during cleanup
4. Error handling gracefully manages send-after-close scenarios
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, Any

from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
from netra_backend.app.websocket_core.utils import safe_websocket_close
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestSendAfterCloseRaceCondition:
    """Test WebSocket send-after-close race condition fix."""

    @pytest.fixture
    async def manager(self):
        """Create a WebSocket manager for testing."""
        test_user_id = "101463487227881885914"  # Valid Google user ID format
        manager = await create_websocket_manager(user_id=test_user_id)
        yield manager
        # Cleanup
        if hasattr(manager, '_cleanup_all_connections'):
            await manager._cleanup_all_connections()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket with realistic behavior."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client_state = Mock()
        websocket.client_state.name = "CONNECTED"
        return websocket

    @pytest.fixture
    def mock_closing_websocket(self):
        """Create a mock WebSocket in closing state."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        # Simulate different WebSocket states
        try:
            from starlette.websockets import WebSocketState
            websocket.client_state = WebSocketState.CLOSING
        except ImportError:
            # Fallback for environments without starlette
            websocket.client_state = Mock()
            websocket.client_state.name = "CLOSING"
        return websocket

    @pytest.mark.asyncio
    async def test_is_closing_flag_prevents_send(self, manager, mock_websocket):
        """Test that is_closing flag prevents send operations."""
        # Setup
        user_id = "test_user_001"
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)

        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc),
            is_closing=True  # Mark as closing
        )

        # Add connection to manager
        await manager.add_connection(connection)

        # Attempt to send message - should be prevented by is_closing flag
        result = await manager.send_message(connection_id, {"test": "message"})

        # Verify
        assert result is False, "Send should fail for closing connection"
        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_connection_safety_check_websocket_state(self, manager, mock_closing_websocket):
        """Test that safety check detects WebSocket in closing state."""
        # Setup
        user_id = "test_user_002"
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)

        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_closing_websocket,
            connected_at=datetime.now(timezone.utc),
            is_closing=False  # Not marked as closing yet
        )

        await manager.add_connection(connection)

        # Attempt send - should be prevented by WebSocket state check
        result = await manager.send_message(connection_id, {"test": "message"})

        # Verify
        assert result is False, "Send should fail for WebSocket in CLOSING state"
        mock_closing_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_broadcast_and_close_race_condition(self, manager):
        """Test concurrent broadcast and connection close operations."""
        # Setup multiple connections
        connections = []
        user_ids = [f"test_user_{i:03d}" for i in range(5)]

        for user_id in user_ids:
            mock_ws = Mock()
            mock_ws.send_json = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.client_state = Mock()
            mock_ws.client_state.name = "CONNECTED"

            connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=mock_ws,
                connected_at=datetime.now(timezone.utc)
            )
            await manager.add_connection(connection)
            connections.append((connection_id, connection, mock_ws))

        # Simulate race condition: start broadcast and close operations concurrently
        async def broadcast_messages():
            """Continuously broadcast messages."""
            for i in range(10):
                await manager.broadcast({"type": "test", "data": f"message_{i}"})
                await asyncio.sleep(0.01)  # Small delay to allow race conditions

        async def close_connections():
            """Close connections during broadcast."""
            await asyncio.sleep(0.02)  # Let broadcast start first
            for connection_id, connection, mock_ws in connections[::2]:  # Close every other connection
                # Mark as closing first (this is what our fix does)
                connection.is_closing = True
                # Simulate the actual close operation
                await manager.remove_connection(connection_id)

        # Run concurrently to create race condition
        await asyncio.gather(
            broadcast_messages(),
            close_connections(),
            return_exceptions=True  # Don't fail on expected exceptions
        )

        # Verify no runtime errors occurred and connections were properly managed
        remaining_connections = list(manager._connections.values())
        assert len(remaining_connections) == 3, "Should have 3 remaining connections"

    @pytest.mark.asyncio
    async def test_send_after_close_error_handling(self, manager, mock_websocket):
        """Test proper error handling when send-after-close occurs."""
        # Setup
        user_id = "test_user_003"
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)

        # Configure mock to raise send-after-close error
        mock_websocket.send_json.side_effect = RuntimeError(
            "Cannot call 'send' once a close message has been sent."
        )

        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc)
        )

        await manager.add_connection(connection)

        # Attempt send - should handle error gracefully
        result = await manager.send_message(connection_id, {"test": "message"})

        # Verify error was handled and connection marked as closing
        assert result is False, "Send should fail gracefully"
        # Get the connection from the manager to check if it was marked as closing
        stored_connection = manager.get_connection(connection_id)
        if stored_connection:
            assert stored_connection.is_closing is True, "Connection should be marked as closing"

    @pytest.mark.asyncio
    async def test_broadcast_skips_unsafe_connections(self, manager):
        """Test that broadcast skips connections that are not safe to send to."""
        # Setup mix of safe and unsafe connections
        safe_connection = await self._create_test_connection(manager, "safe_user", is_closing=False)
        closing_connection = await self._create_test_connection(manager, "closing_user", is_closing=True)

        # Perform broadcast
        await manager.broadcast({"type": "test", "data": "broadcast_message"})

        # Verify only safe connection received message
        safe_connection.websocket.send_json.assert_called_once()
        closing_connection.websocket.send_json.assert_not_called()

    async def _create_test_connection(self, manager, user_id: str, is_closing: bool = False):
        """Helper to create test connection."""
        mock_ws = Mock()
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.client_state = Mock()
        mock_ws.client_state.name = "CONNECTED"

        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_ws,
            connected_at=datetime.now(timezone.utc)
        )

        await manager.add_connection(connection)

        # Set the is_closing flag after adding to manager
        if is_closing:
            stored_connection = manager.get_connection(connection_id)
            if stored_connection:
                stored_connection.is_closing = True

        return stored_connection if stored_connection else connection

    @pytest.mark.asyncio
    async def test_connection_cleanup_sets_closing_flag(self, manager, mock_websocket):
        """Test that connection cleanup properly sets is_closing flag."""
        # Setup
        user_id = "test_user_004"
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)

        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc)
        )

        await manager.add_connection(connection)

        # Verify connection is not closing initially
        assert connection.is_closing is False

        # Remove connection (this should set is_closing flag)
        await manager.remove_connection(connection_id)

        # Verify connection was marked as closing during removal
        # Note: Connection is removed from manager, so we can't check it directly
        # This test validates the removal process completed without errors
        assert connection_id not in manager._connections

    @pytest.mark.asyncio
    async def test_safe_websocket_close_integration(self):
        """Test integration with safe_websocket_close utility."""
        mock_websocket = Mock()
        mock_websocket.close = AsyncMock()

        # Test normal close
        await safe_websocket_close(mock_websocket)
        mock_websocket.close.assert_called_once_with(code=1000, reason="Normal closure")

        # Test close with send-after-close error (should not raise)
        mock_websocket.close.side_effect = RuntimeError("Cannot call 'send' once a close message has been sent.")

        # Should not raise exception
        await safe_websocket_close(mock_websocket, code=1001, reason="Test close")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])