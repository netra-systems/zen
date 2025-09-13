"""
Unit tests for WebSocket Unified Manager Connection Lifecycle Management.

This test suite covers connection establishment, teardown, and lifecycle management
for the unified WebSocket manager, focusing on business logic and user isolation.

Issue #825 Phase 1 Batch 1: Connection Lifecycle Methods
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.types import ConnectionInfo


class TestUnifiedManagerConnectionLifecycle(SSotAsyncTestCase):
    """Test connection lifecycle management in UnifiedWebSocketManager."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        await super().asyncSetUp()
        self.manager = UnifiedWebSocketManager()

        # Mock WebSocket for testing
        self.mock_websocket = AsyncMock()
        self.mock_websocket.client_state = 1  # CONNECTING
        self.mock_websocket.close = AsyncMock()
        self.mock_websocket.send_json = AsyncMock()

        # Test data
        self.test_user_id = "test_user_123"
        self.test_connection_id = "conn_123"
        self.test_thread_id = "thread_123"

    async def asyncTearDown(self):
        """Clean up test fixtures."""
        # Ensure clean teardown
        if hasattr(self.manager, '_connections'):
            for connection in list(self.manager._connections.values()):
                try:
                    await self.manager.disconnect_user(
                        connection.user_id,
                        connection.websocket
                    )
                except Exception:
                    pass  # Ignore cleanup errors
        await super().asyncTearDown()

    async def test_connect_user_success(self):
        """Test successful user connection establishment."""
        # Act
        result = await self.manager.connect_user(
            user_id=self.test_user_id,
            websocket=self.mock_websocket,
            connection_id=self.test_connection_id,
            thread_id=self.test_thread_id
        )

        # Assert
        self.assertIsNotNone(result)
        self.assertIn(self.test_user_id, self.manager._user_connections)

        # Verify connection info is stored correctly
        connections = self.manager._user_connections[self.test_user_id]
        self.assertEqual(len(connections), 1)
        connection_info = connections[0]
        self.assertEqual(connection_info.user_id, self.test_user_id)
        self.assertEqual(connection_info.websocket, self.mock_websocket)

    async def test_connect_user_multiple_connections(self):
        """Test connecting same user with multiple WebSocket connections."""
        # Setup
        mock_websocket_2 = AsyncMock()
        mock_websocket_2.client_state = 1

        # Act - Connect first WebSocket
        result1 = await self.manager.connect_user(
            user_id=self.test_user_id,
            websocket=self.mock_websocket,
            connection_id="conn_1"
        )

        # Act - Connect second WebSocket for same user
        result2 = await self.manager.connect_user(
            user_id=self.test_user_id,
            websocket=mock_websocket_2,
            connection_id="conn_2"
        )

        # Assert
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)

        # Verify both connections are tracked
        connections = self.manager._user_connections[self.test_user_id]
        self.assertEqual(len(connections), 2)

        # Verify connection isolation
        websockets = [conn.websocket for conn in connections]
        self.assertIn(self.mock_websocket, websockets)
        self.assertIn(mock_websocket_2, websockets)

    async def test_connect_user_invalid_websocket(self):
        """Test connection attempt with invalid WebSocket."""
        # Setup
        invalid_websocket = None

        # Act & Assert
        with self.assertRaises(ValueError):
            await self.manager.connect_user(
                user_id=self.test_user_id,
                websocket=invalid_websocket,
                connection_id=self.test_connection_id
            )

    async def test_connect_user_invalid_user_id(self):
        """Test connection attempt with invalid user ID."""
        # Act & Assert
        with self.assertRaises((ValueError, TypeError)):
            await self.manager.connect_user(
                user_id=None,
                websocket=self.mock_websocket,
                connection_id=self.test_connection_id
            )

    async def test_disconnect_user_success(self):
        """Test successful user disconnection."""
        # Setup - Connect user first
        await self.manager.connect_user(
            user_id=self.test_user_id,
            websocket=self.mock_websocket,
            connection_id=self.test_connection_id
        )

        # Verify user is connected
        self.assertIn(self.test_user_id, self.manager._user_connections)

        # Act - Disconnect user
        await self.manager.disconnect_user(
            user_id=self.test_user_id,
            websocket=self.mock_websocket
        )

        # Assert - Connection is removed
        self.mock_websocket.close.assert_called_once()

        # Verify user connections are cleaned up
        if self.test_user_id in self.manager._user_connections:
            connections = self.manager._user_connections[self.test_user_id]
            # Connection should be removed or list should be empty
            self.assertEqual(len(connections), 0)

    async def test_disconnect_user_partial_cleanup(self):
        """Test disconnection when user has multiple connections."""
        # Setup - Connect user with multiple WebSockets
        mock_websocket_2 = AsyncMock()
        mock_websocket_2.client_state = 1

        await self.manager.connect_user(
            user_id=self.test_user_id,
            websocket=self.mock_websocket,
            connection_id="conn_1"
        )

        await self.manager.connect_user(
            user_id=self.test_user_id,
            websocket=mock_websocket_2,
            connection_id="conn_2"
        )

        # Verify both connections exist
        connections = self.manager._user_connections[self.test_user_id]
        self.assertEqual(len(connections), 2)

        # Act - Disconnect one WebSocket
        await self.manager.disconnect_user(
            user_id=self.test_user_id,
            websocket=self.mock_websocket
        )

        # Assert - Only one connection closed
        self.mock_websocket.close.assert_called_once()
        mock_websocket_2.close.assert_not_called()

        # Verify one connection remains
        remaining_connections = self.manager._user_connections[self.test_user_id]
        self.assertEqual(len(remaining_connections), 1)
        self.assertEqual(remaining_connections[0].websocket, mock_websocket_2)

    async def test_disconnect_nonexistent_user(self):
        """Test disconnecting a user that doesn't exist."""
        # Act - Disconnect user that was never connected
        try:
            await self.manager.disconnect_user(
                user_id="nonexistent_user",
                websocket=self.mock_websocket
            )
            # Should not raise exception - graceful handling
        except Exception as e:
            self.fail(f"Disconnect should handle nonexistent users gracefully: {e}")

    async def test_connection_state_tracking(self):
        """Test that connection state is properly tracked."""
        # Act - Connect user
        await self.manager.connect_user(
            user_id=self.test_user_id,
            websocket=self.mock_websocket,
            connection_id=self.test_connection_id
        )

        # Assert - Verify connection state
        connections = self.manager._user_connections[self.test_user_id]
        self.assertEqual(len(connections), 1)

        connection = connections[0]
        self.assertEqual(connection.user_id, self.test_user_id)
        self.assertEqual(connection.websocket, self.mock_websocket)
        self.assertEqual(connection.connection_id, self.test_connection_id)

        # Verify connection is active
        self.assertTrue(hasattr(connection, 'connected_at'))
        self.assertIsNotNone(connection.connected_at)

    async def test_user_isolation_boundaries(self):
        """Test that user connections are properly isolated."""
        # Setup - Connect two different users
        user_1_id = "user_1"
        user_2_id = "user_2"
        mock_websocket_1 = AsyncMock()
        mock_websocket_2 = AsyncMock()
        mock_websocket_1.client_state = 1
        mock_websocket_2.client_state = 1

        # Act - Connect both users
        await self.manager.connect_user(
            user_id=user_1_id,
            websocket=mock_websocket_1,
            connection_id="conn_1"
        )

        await self.manager.connect_user(
            user_id=user_2_id,
            websocket=mock_websocket_2,
            connection_id="conn_2"
        )

        # Assert - Verify isolation
        user_1_connections = self.manager._user_connections[user_1_id]
        user_2_connections = self.manager._user_connections[user_2_id]

        self.assertEqual(len(user_1_connections), 1)
        self.assertEqual(len(user_2_connections), 1)
        self.assertEqual(user_1_connections[0].websocket, mock_websocket_1)
        self.assertEqual(user_2_connections[0].websocket, mock_websocket_2)

        # Verify cross-user isolation
        self.assertNotEqual(
            user_1_connections[0].connection_id,
            user_2_connections[0].connection_id
        )

    async def test_connection_error_handling(self):
        """Test error handling during connection process."""
        # Setup - Mock WebSocket that raises exception
        failing_websocket = AsyncMock()
        failing_websocket.client_state = 1

        # Mock internal method to raise exception
        original_method = self.manager._add_connection

        def failing_add_connection(*args, **kwargs):
            raise RuntimeError("Connection failed")

        self.manager._add_connection = failing_add_connection

        # Act & Assert
        with self.assertRaises(RuntimeError):
            await self.manager.connect_user(
                user_id=self.test_user_id,
                websocket=failing_websocket,
                connection_id=self.test_connection_id
            )

        # Restore original method
        self.manager._add_connection = original_method

    async def test_concurrent_connection_handling(self):
        """Test handling multiple concurrent connections."""
        # Setup - Multiple users and WebSockets
        users = ["user_1", "user_2", "user_3"]
        websockets = []

        for i in range(3):
            mock_ws = AsyncMock()
            mock_ws.client_state = 1
            websockets.append(mock_ws)

        # Act - Connect all users concurrently
        tasks = []
        for i, user_id in enumerate(users):
            task = self.manager.connect_user(
                user_id=user_id,
                websocket=websockets[i],
                connection_id=f"conn_{i}"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Assert - All connections successful
        for result in results:
            self.assertIsNotNone(result)

        # Verify all users are connected
        for user_id in users:
            self.assertIn(user_id, self.manager._user_connections)
            connections = self.manager._user_connections[user_id]
            self.assertEqual(len(connections), 1)

    async def test_memory_cleanup_on_disconnect(self):
        """Test that memory is properly cleaned up on disconnect."""
        # Setup - Connect user
        await self.manager.connect_user(
            user_id=self.test_user_id,
            websocket=self.mock_websocket,
            connection_id=self.test_connection_id
        )

        # Verify connection exists in memory
        initial_connection_count = len(self.manager._connections)
        user_connection_count = len(self.manager._user_connections.get(self.test_user_id, []))
        self.assertGreater(user_connection_count, 0)

        # Act - Disconnect user
        await self.manager.disconnect_user(
            user_id=self.test_user_id,
            websocket=self.mock_websocket
        )

        # Assert - Memory is cleaned up
        final_user_connections = self.manager._user_connections.get(self.test_user_id, [])
        self.assertEqual(len(final_user_connections), 0)

        # Verify connection references are cleaned up
        final_connection_count = len(self.manager._connections)
        self.assertLessEqual(final_connection_count, initial_connection_count)


if __name__ == '__main__':
    pytest.main([__file__])