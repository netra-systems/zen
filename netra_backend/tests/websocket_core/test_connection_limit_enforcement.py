"""
Connection Limit Enforcement Test - Designed to FAIL and prove the emergency cleanup bug

CRITICAL: This test directly tests the connection limit enforcement in unified_manager.py
to reproduce the emergency cleanup failure when MAX_CONNECTIONS_PER_USER is exceeded.

The bug: Emergency cleanup doesn't properly free connection slots when limits are hit.
"""

import unittest
import asyncio
from unittest.mock import MagicMock
from typing import List, Dict

# SSOT imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Real WebSocket components (no mocking for critical paths)
from netra_backend.app.websocket_core.websocket_manager import (
    _UnifiedWebSocketManagerImplementation,
    MAX_CONNECTIONS_PER_USER
)
from netra_backend.app.websocket_core.types import WebSocketConnection, WebSocketManagerMode
from shared.types.core_types import UserID, ThreadID, ConnectionID, WebSocketID
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestConnectionLimitEnforcement(SSotAsyncTestCase):
    """
    Test WebSocket connection limit enforcement and emergency cleanup failure.

    EXPECTED: These tests should FAIL, proving the emergency cleanup bug exists.
    """

    def setup_method(self, method):
        """Set up test with real WebSocket manager."""
        super().setup_method(method)

        # Create actual WebSocket manager instance (real component)
        self.manager = _UnifiedWebSocketManagerImplementation()

        self.test_user_id = UserID("limit_test_user")
        self.created_connections: List[WebSocketConnection] = []
        self.mock_websockets: List[MagicMock] = []

        logger.info("Setting up connection limit enforcement test")

    def teardown_method(self, method):
        """Clean up connections."""
        async def cleanup_async():
            # Clean up all connections
            for connection in self.created_connections:
                try:
                    await self.manager.remove_connection(connection.connection_id)
                except Exception as e:
                    logger.warning(f"Error removing connection {connection.connection_id}: {e}")

        try:
            asyncio.get_event_loop().run_until_complete(cleanup_async())
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

        self.created_connections.clear()
        self.mock_websockets.clear()
        super().teardown_method(method)

    def _create_mock_websocket(self, connection_id: str) -> MagicMock:
        """Create mock WebSocket for testing."""
        mock_ws = MagicMock()
        mock_ws.id = connection_id
        mock_ws.closed = False
        mock_ws.close = MagicMock()
        mock_ws.send = MagicMock()
        mock_ws.remote_address = ("127.0.0.1", 12345)
        mock_ws.path = "/ws"
        mock_ws.request_headers = {}

        self.mock_websockets.append(mock_ws)
        return mock_ws

    async def test_connection_limit_enforcement_direct(self):
        """
        Test direct connection limit enforcement via add_connection method.

        EXPECTED TO FAIL: This should demonstrate that emergency cleanup doesn't work
        when the connection limit is exceeded.
        """
        logger.info(f"Testing direct connection limit enforcement: MAX_CONNECTIONS_PER_USER = {MAX_CONNECTIONS_PER_USER}")

        successful_connections = 0
        failed_connections = 0

        # Create connections up to and beyond the limit
        for i in range(MAX_CONNECTIONS_PER_USER + 5):  # Try to exceed by 5
            try:
                mock_ws = self._create_mock_websocket(f"direct_conn_{i}")

                # Create WebSocketConnection object
                connection = WebSocketConnection(
                    connection_id=ConnectionID(f"direct_conn_{i}"),
                    user_id=self.test_user_id,
                    thread_id=ThreadID(f"direct_thread_{i}"),
                    websocket_id=WebSocketID(f"direct_ws_{i}"),
                    websocket=mock_ws,
                    mode=WebSocketManagerMode.ISOLATED,
                    connected_at=None  # Will be set by manager
                )

                # This is the critical call that should enforce limits
                await self.manager.add_connection(connection)

                self.created_connections.append(connection)
                successful_connections += 1

                logger.info(f"Successfully added connection {i+1}/{MAX_CONNECTIONS_PER_USER + 5}")

            except ValueError as e:
                # This is expected when limit is exceeded
                failed_connections += 1
                logger.info(f"Connection {i+1} failed (expected): {e}")

            except Exception as e:
                # Unexpected error
                failed_connections += 1
                logger.warning(f"Connection {i+1} failed unexpectedly: {e}")

        logger.info(f"Results: {successful_connections} successful, {failed_connections} failed")

        # BUG ASSERTION 1: Should not exceed the limit
        self.assertLessEqual(
            successful_connections,
            MAX_CONNECTIONS_PER_USER,
            f"BUG DETECTED: System allowed {successful_connections} connections for user {self.test_user_id}, "
            f"but MAX_CONNECTIONS_PER_USER is {MAX_CONNECTIONS_PER_USER}. "
            f"Connection limit enforcement failed."
        )

        # BUG ASSERTION 2: Should have some failures
        self.assertGreater(
            failed_connections,
            0,
            f"BUG DETECTED: Expected some connection failures after limit, but all {successful_connections} succeeded. "
            f"No limit enforcement is happening."
        )

    async def test_emergency_cleanup_after_zombie_connections(self):
        """
        Test emergency cleanup when zombie connections should free up slots.

        EXPECTED TO FAIL: Emergency cleanup should detect closed WebSockets and free slots,
        but the bug prevents this from working properly.
        """
        logger.info("Testing emergency cleanup with zombie connections")

        # Fill up to the connection limit
        for i in range(MAX_CONNECTIONS_PER_USER):
            mock_ws = self._create_mock_websocket(f"zombie_test_conn_{i}")

            connection = WebSocketConnection(
                connection_id=ConnectionID(f"zombie_test_conn_{i}"),
                user_id=self.test_user_id,
                thread_id=ThreadID(f"zombie_test_thread_{i}"),
                websocket_id=WebSocketID(f"zombie_test_ws_{i}"),
                websocket=mock_ws,
                mode=WebSocketManagerMode.ISOLATED,
                connected_at=None
            )

            await self.manager.add_connection(connection)
            self.created_connections.append(connection)

        logger.info(f"Created {len(self.created_connections)} connections (at limit)")

        # Now mark some WebSockets as closed (zombie state)
        zombie_count = 3
        for i in range(zombie_count):
            self.mock_websockets[i].closed = True
            logger.info(f"Marked WebSocket {i} as closed (zombie)")

        # Wait for any background cleanup processes
        await asyncio.sleep(0.5)

        # Now try to add new connections - should work if emergency cleanup detects zombies
        new_successful_connections = 0

        for i in range(zombie_count + 1):  # Try to add more than zombie count
            try:
                mock_ws = self._create_mock_websocket(f"post_zombie_conn_{i}")

                connection = WebSocketConnection(
                    connection_id=ConnectionID(f"post_zombie_conn_{i}"),
                    user_id=self.test_user_id,
                    thread_id=ThreadID(f"post_zombie_thread_{i}"),
                    websocket_id=WebSocketID(f"post_zombie_ws_{i}"),
                    websocket=mock_ws,
                    mode=WebSocketManagerMode.ISOLATED,
                    connected_at=None
                )

                await self.manager.add_connection(connection)
                self.created_connections.append(connection)
                new_successful_connections += 1

                logger.info(f"Successfully added post-zombie connection {i+1}")

            except Exception as e:
                logger.info(f"Post-zombie connection {i+1} failed: {e}")
                break

        # BUG ASSERTION: Emergency cleanup should have freed at least zombie_count slots
        self.assertGreaterEqual(
            new_successful_connections,
            zombie_count,
            f"BUG DETECTED: Emergency cleanup failed to detect and clean up {zombie_count} zombie connections. "
            f"Only {new_successful_connections} new connections could be added. "
            f"Emergency cleanup is not properly detecting closed WebSocket connections."
        )

    async def test_connection_cleanup_completeness(self):
        """
        Test that cleanup actually removes connections from internal tracking.

        EXPECTED TO FAIL: When connections are removed, the internal tracking should update
        to allow new connections, but the bug causes stale tracking.
        """
        logger.info("Testing connection cleanup completeness")

        # Create connections up to limit
        initial_connections = []
        for i in range(MAX_CONNECTIONS_PER_USER):
            mock_ws = self._create_mock_websocket(f"cleanup_test_conn_{i}")

            connection = WebSocketConnection(
                connection_id=ConnectionID(f"cleanup_test_conn_{i}"),
                user_id=self.test_user_id,
                thread_id=ThreadID(f"cleanup_test_thread_{i}"),
                websocket_id=WebSocketID(f"cleanup_test_ws_{i}"),
                websocket=mock_ws,
                mode=WebSocketManagerMode.ISOLATED,
                connected_at=None
            )

            await self.manager.add_connection(connection)
            initial_connections.append(connection)
            self.created_connections.append(connection)

        logger.info(f"Created {len(initial_connections)} connections at limit")

        # Manually remove some connections
        connections_to_remove = 4
        for i in range(connections_to_remove):
            connection = initial_connections[i]
            await self.manager.remove_connection(connection.connection_id)
            logger.info(f"Manually removed connection {connection.connection_id}")

        # Wait for cleanup to propagate
        await asyncio.sleep(0.2)

        # Try to add new connections - should work since we removed some
        new_connections_added = 0

        for i in range(connections_to_remove + 1):  # Try to add more than we removed
            try:
                mock_ws = self._create_mock_websocket(f"post_cleanup_conn_{i}")

                connection = WebSocketConnection(
                    connection_id=ConnectionID(f"post_cleanup_conn_{i}"),
                    user_id=self.test_user_id,
                    thread_id=ThreadID(f"post_cleanup_thread_{i}"),
                    websocket_id=WebSocketID(f"post_cleanup_ws_{i}"),
                    websocket=mock_ws,
                    mode=WebSocketManagerMode.ISOLATED,
                    connected_at=None
                )

                await self.manager.add_connection(connection)
                self.created_connections.append(connection)
                new_connections_added += 1

                logger.info(f"Successfully added post-cleanup connection {i+1}")

            except Exception as e:
                logger.info(f"Post-cleanup connection {i+1} failed: {e}")
                break

        # BUG ASSERTION: Should be able to add at least as many as we removed
        self.assertGreaterEqual(
            new_connections_added,
            connections_to_remove,
            f"BUG DETECTED: After removing {connections_to_remove} connections, "
            f"only {new_connections_added} new connections could be added. "
            f"Connection cleanup is not properly updating internal tracking, "
            f"leaving stale entries that block new connections."
        )

        logger.info(f"Cleanup completeness test: {new_connections_added} new connections added after cleanup")


if __name__ == "__main__":
    unittest.main()