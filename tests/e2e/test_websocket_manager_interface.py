"""
End-to-end tests for WebSocket manager interface issues.

This test module validates WebSocket manager behavior and interface
consistency across different scenarios.
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.websocket_manager.websocket_manager import WebSocketManager
from netra_backend.app.websocket_manager.session_manager import SessionManager


@pytest.mark.e2e
@pytest.mark.env_test
class TestWebSocketManagerInterface:
    """Test WebSocket manager interface consistency and edge cases."""

    @pytest.fixture
    async def websocket_manager(self):
        """Create WebSocket manager for testing."""
        manager = WebSocketManager()
        yield manager
        # Cleanup
        await manager.cleanup()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_json = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    async def test_connection_lifecycle_consistency(self, websocket_manager, mock_websocket):
        """Test WebSocket connection lifecycle consistency."""
        session_id = "test_session_123"
        user_id = "user_456"

        # Test connection establishment
        await websocket_manager.connect_client(session_id, user_id, mock_websocket)
        
        # Verify connection is tracked
        assert websocket_manager.is_client_connected(session_id)
        assert websocket_manager.get_client_count() == 1

        # Test message sending
        test_message = {"type": "test", "data": "hello"}
        await websocket_manager.send_to_client(session_id, test_message)
        
        mock_websocket.send_json.assert_called_once_with(test_message)

        # Test disconnection
        await websocket_manager.disconnect_client(session_id)
        
        assert not websocket_manager.is_client_connected(session_id)
        assert websocket_manager.get_client_count() == 0

    @pytest.mark.asyncio
    async def test_broadcast_message_consistency(self, websocket_manager):
        """Test broadcast message consistency across multiple clients."""
        # Setup multiple mock clients
        clients = {}
        for i in range(5):
            session_id = f"session_{i}"
            user_id = f"user_{i}"
            websocket = AsyncMock()
            clients[session_id] = websocket
            await websocket_manager.connect_client(session_id, user_id, websocket)

        # Broadcast a message
        broadcast_message = {"type": "broadcast", "data": "global_update"}
        await websocket_manager.broadcast_to_all(broadcast_message)

        # Verify all clients received the message
        for websocket in clients.values():
            websocket.send_json.assert_called_once_with(broadcast_message)

    @pytest.mark.asyncio
    async def test_error_handling_during_message_sending(self, websocket_manager, mock_websocket):
        """Test error handling when sending messages to disconnected clients."""
        session_id = "test_session"
        user_id = "test_user"

        # Connect client
        await websocket_manager.connect_client(session_id, user_id, mock_websocket)

        # Simulate WebSocket send failure
        mock_websocket.send_json.side_effect = Exception("Connection broken")

        # Attempt to send message - should handle error gracefully
        test_message = {"type": "test", "data": "test"}
        
        # Should not raise exception
        try:
            await websocket_manager.send_to_client(session_id, test_message)
        except Exception as e:
            pytest.fail(f"WebSocket manager should handle send errors gracefully: {e}")

        # Client should be automatically disconnected on error
        assert not websocket_manager.is_client_connected(session_id)

    @pytest.mark.asyncio
    async def test_session_manager_integration(self, websocket_manager):
        """Test WebSocket manager integration with session management."""
        with patch('netra_backend.app.websocket_manager.websocket_manager.SessionManager') as mock_session_manager_class:
            mock_session_manager = AsyncMock()
            mock_session_manager_class.return_value = mock_session_manager
            
            # Setup session validation
            mock_session_manager.validate_session.return_value = {
                "valid": True,
                "user_id": "validated_user",
                "session_id": "validated_session"
            }

            session_id = "test_session"
            user_id = "test_user"
            mock_websocket = AsyncMock()

            # Connect with session validation
            await websocket_manager.connect_client_with_auth(session_id, user_id, mock_websocket)

            # Verify session validation was called
            mock_session_manager.validate_session.assert_called_once_with(session_id, user_id)

    @pytest.mark.asyncio
    async def test_concurrent_connection_handling(self, websocket_manager):
        """Test handling of concurrent WebSocket connections."""
        async def connect_client(client_id):
            session_id = f"session_{client_id}"
            user_id = f"user_{client_id}"
            websocket = AsyncMock()
            
            await websocket_manager.connect_client(session_id, user_id, websocket)
            await asyncio.sleep(0.1)  # Simulate some work
            await websocket_manager.disconnect_client(session_id)
            return session_id

        # Create concurrent connections
        tasks = [connect_client(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert websocket_manager.get_client_count() == 0  # All should be disconnected

    @pytest.mark.asyncio
    async def test_message_queuing_for_disconnected_clients(self, websocket_manager):
        """Test message queuing behavior for temporarily disconnected clients."""
        session_id = "temp_disconnect_session"
        user_id = "temp_user"
        mock_websocket = AsyncMock()

        # Connect client
        await websocket_manager.connect_client(session_id, user_id, mock_websocket)

        # Simulate temporary disconnection (but keep session)
        await websocket_manager.disconnect_client(session_id, keep_session=True)

        # Try to send message to disconnected client
        queued_message = {"type": "queued", "data": "offline_message"}
        result = await websocket_manager.send_to_client(session_id, queued_message, queue_if_offline=True)

        # Should indicate message was queued
        assert result.get("queued") is True

        # Reconnect client
        new_mock_websocket = AsyncMock()
        await websocket_manager.reconnect_client(session_id, new_mock_websocket)

        # Should receive queued message
        new_mock_websocket.send_json.assert_called_with(queued_message)

    @pytest.mark.asyncio
    async def test_websocket_connection_state_consistency(self, websocket_manager, mock_websocket):
        """Test WebSocket connection state consistency across operations."""
        session_id = "state_test_session"
        user_id = "state_test_user"

        # Initial state
        assert not websocket_manager.is_client_connected(session_id)
        assert websocket_manager.get_client_info(session_id) is None

        # Connect
        await websocket_manager.connect_client(session_id, user_id, mock_websocket)
        
        # State after connection
        assert websocket_manager.is_client_connected(session_id)
        client_info = websocket_manager.get_client_info(session_id)
        assert client_info is not None
        assert client_info["user_id"] == user_id
        assert client_info["session_id"] == session_id

        # State should be consistent across multiple checks
        for _ in range(5):
            assert websocket_manager.is_client_connected(session_id)
            assert websocket_manager.get_client_info(session_id)["user_id"] == user_id

        # Disconnect
        await websocket_manager.disconnect_client(session_id)
        
        # State after disconnection
        assert not websocket_manager.is_client_connected(session_id)
        assert websocket_manager.get_client_info(session_id) is None

    @pytest.mark.asyncio
    async def test_websocket_resource_cleanup(self, websocket_manager):
        """Test proper resource cleanup in WebSocket manager."""
        session_ids = []
        
        # Create multiple connections
        for i in range(5):
            session_id = f"cleanup_session_{i}"
            user_id = f"cleanup_user_{i}"
            mock_websocket = AsyncMock()
            
            await websocket_manager.connect_client(session_id, user_id, mock_websocket)
            session_ids.append(session_id)

        assert websocket_manager.get_client_count() == 5

        # Cleanup all resources
        await websocket_manager.cleanup()

        # Verify cleanup
        assert websocket_manager.get_client_count() == 0
        for session_id in session_ids:
            assert not websocket_manager.is_client_connected(session_id)