"""
Simple Resource Exhaustion Test - Designed to FAIL and prove the bug exists

CRITICAL: This test demonstrates the WebSocket Manager emergency cleanup failure.
"""

import unittest
import asyncio
from unittest.mock import MagicMock
from typing import List

# Use the SSOT base test case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import WebSocket components - these must be real components, not mocked
from netra_backend.app.websocket_core.unified_manager import MAX_CONNECTIONS_PER_USER
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.types import create_isolated_mode
from shared.types.core_types import UserID, ThreadID, ConnectionID
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestResourceExhaustionSimple(SSotAsyncTestCase):
    """
    Simple test to prove WebSocket Manager resource exhaustion emergency cleanup bug.

    EXPECTED: This test should FAIL, proving the bug exists.
    """

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.test_user_id = UserID("test_user_exhaustion")
        self.created_managers: List[WebSocketManager] = []
        self.mock_websockets: List[MagicMock] = []
        logger.info("Starting resource exhaustion simple test")

    def teardown_method(self, method):
        """Clean up test resources."""
        # Force cleanup
        for manager in self.created_managers:
            try:
                if hasattr(manager, 'cleanup'):
                    asyncio.create_task(manager.cleanup())
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")

        self.created_managers.clear()
        self.mock_websockets.clear()
        super().teardown_method(method)

    def _create_mock_websocket(self, connection_id: str) -> MagicMock:
        """Create a mock WebSocket for testing."""
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

    async def test_exceeds_max_connections_limit(self):
        """
        TEST: Try to create more than MAX_CONNECTIONS_PER_USER connections.

        EXPECTED TO FAIL: This should fail because emergency cleanup doesn't work properly.
        The system should enforce the limit but due to the bug, it may allow too many.
        """
        logger.info(f"Testing connection limit: MAX_CONNECTIONS_PER_USER = {MAX_CONNECTIONS_PER_USER}")

        successful_connections = 0

        # Try to create double the allowed connections
        for i in range(MAX_CONNECTIONS_PER_USER * 2):
            try:
                mock_ws = self._create_mock_websocket(f"ws_conn_{i}")

                mode = create_isolated_mode(
                    user_id=self.test_user_id,
                    thread_id=ThreadID(f"thread_{i}"),
                    connection_id=ConnectionID(f"conn_{i}")
                )

                manager = WebSocketManager(mock_ws, mode)
                await manager.initialize()

                self.created_managers.append(manager)
                successful_connections += 1

                logger.debug(f"Created connection {i+1}: success")

            except Exception as e:
                logger.info(f"Connection {i+1} failed (expected after limit): {e}")
                break

        # BUG ASSERTION: This should FAIL because the system allows too many connections
        # The emergency cleanup should limit connections to MAX_CONNECTIONS_PER_USER
        self.assertLessEqual(
            successful_connections,
            MAX_CONNECTIONS_PER_USER,
            f"BUG DETECTED: System allowed {successful_connections} connections for user {self.test_user_id}, "
            f"but MAX_CONNECTIONS_PER_USER is {MAX_CONNECTIONS_PER_USER}. "
            f"Emergency cleanup failed to enforce connection limits properly."
        )

        logger.info(f"Test completed: {successful_connections} successful connections")

    async def test_zombie_connection_cleanup_failure(self):
        """
        TEST: Create connections, mark some as closed, then try new connections.

        EXPECTED TO FAIL: Emergency cleanup should detect and remove closed connections,
        but the bug prevents proper cleanup.
        """
        logger.info("Testing zombie connection cleanup")

        # Create connections up to limit
        for i in range(MAX_CONNECTIONS_PER_USER):
            mock_ws = self._create_mock_websocket(f"zombie_ws_{i}")

            mode = create_isolated_mode(
                user_id=self.test_user_id,
                thread_id=ThreadID(f"zombie_thread_{i}"),
                connection_id=ConnectionID(f"zombie_conn_{i}")
            )

            manager = WebSocketManager(mock_ws, mode)
            await manager.initialize()
            self.created_managers.append(manager)

        # Mark first 3 connections as "closed" (zombie state)
        zombie_count = 3
        for i in range(zombie_count):
            self.mock_websockets[i].closed = True
            logger.debug(f"Marked connection {i} as closed (zombie)")

        # Wait for potential cleanup
        await asyncio.sleep(0.1)

        # Now try to create new connections - should work if cleanup detected zombies
        new_connections_created = 0

        for i in range(zombie_count):
            try:
                mock_ws = self._create_mock_websocket(f"new_ws_{i}")

                mode = create_isolated_mode(
                    user_id=self.test_user_id,
                    thread_id=ThreadID(f"new_thread_{i}"),
                    connection_id=ConnectionID(f"new_conn_{i}")
                )

                manager = WebSocketManager(mock_ws, mode)
                await manager.initialize()

                self.created_managers.append(manager)
                new_connections_created += 1

            except Exception as e:
                logger.info(f"New connection {i} failed: {e}")
                break

        # BUG ASSERTION: This should FAIL because zombie cleanup doesn't work
        # We should be able to create new connections equal to the number of zombies
        self.assertGreaterEqual(
            new_connections_created,
            zombie_count,
            f"BUG DETECTED: Emergency cleanup failed to detect and remove {zombie_count} zombie connections. "
            f"Only {new_connections_created} new connections could be created. "
            f"Emergency cleanup is not properly detecting closed WebSocket connections."
        )

        logger.info(f"Zombie cleanup test: {new_connections_created} new connections created")


if __name__ == "__main__":
    unittest.main()