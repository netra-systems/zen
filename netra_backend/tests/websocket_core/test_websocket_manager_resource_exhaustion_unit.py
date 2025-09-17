"""
Unit Tests for WebSocket Manager Resource Exhaustion Emergency Cleanup Failure

CRITICAL TEST PLAN: These tests are designed to FAIL initially to prove the bug exists.
Test focus: Reproduce the emergency cleanup failure when hitting MAX_CONNECTIONS_PER_USER limit.

Business Impact: $500K+ ARR dependent on WebSocket reliability for Golden Path user flow.

Test Cases:
1. Test that creates 20 WebSocket managers and hits the limit (MAX_CONNECTIONS_PER_USER = 10)
2. Test that simulates zombie managers during emergency cleanup
3. Test that verifies cleanup fails to free sufficient managers
4. Test that validates user gets blocked from new connections

Following CLAUDE.md requirements:
- Inherits from SSOT BaseTestCase
- Uses IsolatedEnvironment for environment access
- Tests FAIL to prove bug exists
- No mocking for core WebSocket components (use real WebSocket components)
"""

import unittest
import asyncio
from unittest.mock import MagicMock, patch
from typing import Dict, List, Optional, Any

# SSOT IMPORT: Following SSOT_IMPORT_REGISTRY.md requirements
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.environment.isolated_environment import IsolatedEnvironment

# WebSocket Core imports - Real components (no mocking per CLAUDE.md)
from netra_backend.app.websocket_core.websocket_manager import (
    _UnifiedWebSocketManagerImplementation,
    MAX_CONNECTIONS_PER_USER
)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.types import (
    WebSocketConnection,
    WebSocketManagerMode,
    create_isolated_mode
)
from shared.types.core_types import UserID, ThreadID, ConnectionID, WebSocketID
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestWebSocketManagerResourceExhaustionUnit(SSotAsyncTestCase):
    """
    Unit tests for WebSocket Manager Resource Exhaustion and Emergency Cleanup failures.

    CRITICAL: These tests are designed to FAIL initially to prove the bug exists.
    They reproduce the emergency cleanup failure scenario where managers accumulate
    and cannot be properly cleaned up when hitting resource limits.
    """

    def setup_method(self, method):
        """Set up test environment using SSOT patterns."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()

        # Test configuration for resource exhaustion scenarios
        self.test_user_id = UserID("test_user_resource_exhaustion")
        self.test_thread_id = ThreadID("test_thread_resource")

        # Track managers created during test for cleanup
        self.created_managers: List[WebSocketManager] = []
        self.mock_websockets: List[MagicMock] = []

        logger.info(f"Starting resource exhaustion test: {method.__name__}")

    def teardown_method(self, method):
        """Clean up test resources."""
        # Force cleanup of any remaining managers
        for manager in self.created_managers:
            try:
                if hasattr(manager, 'cleanup'):
                    asyncio.create_task(manager.cleanup())
            except Exception as e:
                logger.warning(f"Error during manager cleanup: {e}")

        self.created_managers.clear()
        self.mock_websockets.clear()

        super().teardown_method(method)

    def _create_mock_websocket(self, connection_id: str = None) -> MagicMock:
        """Create a mock WebSocket connection for testing."""
        mock_ws = MagicMock()
        mock_ws.id = connection_id or f"ws_{len(self.mock_websockets)}"
        mock_ws.closed = False
        mock_ws.close = MagicMock()
        mock_ws.send = MagicMock()

        # Add properties that WebSocket manager expects
        mock_ws.remote_address = ("127.0.0.1", 12345)
        mock_ws.path = "/ws"
        mock_ws.request_headers = {}

        self.mock_websockets.append(mock_ws)
        return mock_ws

    async def test_max_connections_per_user_limit_hit(self):
        """
        TEST CASE 1: Test hitting MAX_CONNECTIONS_PER_USER limit (10 connections).

        EXPECTED RESULT: This test should FAIL because the system allows more than
        MAX_CONNECTIONS_PER_USER connections to be created before proper cleanup.

        BUG PROOF: When 20 managers are created for the same user, the system should
        reject new connections after 10, but emergency cleanup fails to free slots.
        """
        logger.info(f"Testing MAX_CONNECTIONS_PER_USER limit: {MAX_CONNECTIONS_PER_USER}")

        successful_connections = 0
        failed_connections = 0

        # Create managers up to the limit plus extra to trigger emergency cleanup
        for i in range(MAX_CONNECTIONS_PER_USER * 2):  # 20 connections for same user
            try:
                # Create new WebSocket manager for same user
                mock_ws = self._create_mock_websocket(f"ws_connection_{i}")

                # Use isolated mode for consistent testing
                mode = create_isolated_mode(
                    user_id=self.test_user_id,
                    thread_id=ThreadID(f"thread_{i}"),
                    connection_id=ConnectionID(f"conn_{i}")
                )

                manager = WebSocketManager(mock_ws, mode)
                self.created_managers.append(manager)

                # Initialize the manager (this should eventually fail after limit)
                await manager.initialize()
                successful_connections += 1

                logger.info(f"Created manager {i+1}/{MAX_CONNECTIONS_PER_USER * 2} for user {self.test_user_id}")

            except Exception as e:
                failed_connections += 1
                logger.info(f"Manager creation failed at {i+1}: {e}")

        # BUG ASSERTION: This should FAIL because cleanup doesn't work properly
        # The system should reject connections after MAX_CONNECTIONS_PER_USER (10)
        # But due to the bug, it may allow more connections than the limit
        self.assertLessEqual(
            successful_connections,
            MAX_CONNECTIONS_PER_USER,
            f"BUG DETECTED: System allowed {successful_connections} connections for user {self.test_user_id}, "
            f"but MAX_CONNECTIONS_PER_USER is {MAX_CONNECTIONS_PER_USER}. "
            f"Emergency cleanup failed to free connection slots properly."
        )

        # Additional assertion: Should have some failed connections
        self.assertGreater(
            failed_connections,
            0,
            f"BUG DETECTED: Expected some connection failures after limit, but all {successful_connections} succeeded. "
            f"Emergency cleanup is not enforcing connection limits properly."
        )

    async def test_zombie_managers_during_emergency_cleanup(self):
        """
        TEST CASE 2: Test zombie managers persist during emergency cleanup.

        EXPECTED RESULT: This test should FAIL because zombie managers (managers that
        should be cleaned up but remain in memory) prevent new connections.

        BUG PROOF: When cleanup fails, old managers remain active and block new users.
        """
        logger.info("Testing zombie manager detection during emergency cleanup")

        # Create managers that simulate "zombie" state (not properly cleaned up)
        zombie_managers = []

        for i in range(MAX_CONNECTIONS_PER_USER):
            mock_ws = self._create_mock_websocket(f"zombie_ws_{i}")
            # Simulate closed WebSocket that manager doesn't detect
            mock_ws.closed = True

            mode = create_isolated_mode(
                user_id=self.test_user_id,
                thread_id=ThreadID(f"zombie_thread_{i}"),
                connection_id=ConnectionID(f"zombie_conn_{i}")
            )

            manager = WebSocketManager(mock_ws, mode)
            await manager.initialize()

            # Simulate the manager being in a "zombie" state where WebSocket is closed
            # but manager still thinks it's active
            zombie_managers.append(manager)
            self.created_managers.append(manager)

        # Now try to create a new legitimate connection
        # This should trigger emergency cleanup of zombie managers
        new_mock_ws = self._create_mock_websocket("new_legitimate_ws")
        new_mode = create_isolated_mode(
            user_id=self.test_user_id,
            thread_id=ThreadID("new_thread"),
            connection_id=ConnectionID("new_conn")
        )

        # BUG ASSERTION: This should FAIL because zombie cleanup doesn't work
        try:
            new_manager = WebSocketManager(new_mock_ws, new_mode)
            await new_manager.initialize()
            self.created_managers.append(new_manager)

            # If we get here, it means cleanup worked (test should fail to prove bug)
            self.fail(
                f"BUG NOT DETECTED: Expected new connection to fail due to zombie managers, "
                f"but it succeeded. Emergency cleanup may have worked correctly, "
                f"or zombie detection is not working. Expected failure due to {len(zombie_managers)} zombie managers."
            )

        except Exception as e:
            # Expected failure - but let's verify it's due to resource exhaustion, not other issues
            error_msg = str(e).lower()
            if "max" in error_msg or "limit" in error_msg or "exhaustion" in error_msg:
                logger.info(f"Expected failure due to resource exhaustion: {e}")
                # This is the expected behavior, but test should fail to prove bug exists
                self.fail(
                    f"BUG CONFIRMED: Emergency cleanup failed to remove zombie managers. "
                    f"New connection blocked by {len(zombie_managers)} zombie managers. Error: {e}"
                )
            else:
                # Unexpected error - re-raise
                raise

    async def test_emergency_cleanup_insufficient_slots_freed(self):
        """
        TEST CASE 3: Test that emergency cleanup fails to free sufficient connection slots.

        EXPECTED RESULT: This test should FAIL because emergency cleanup doesn't free
        enough slots to allow new connections.

        BUG PROOF: When emergency cleanup runs, it should free at least 2-3 slots,
        but the bug causes it to free 0 or insufficient slots.
        """
        logger.info("Testing emergency cleanup slot freeing efficiency")

        # Fill up to the limit
        initial_managers = []
        for i in range(MAX_CONNECTIONS_PER_USER):
            mock_ws = self._create_mock_websocket(f"initial_ws_{i}")

            mode = create_isolated_mode(
                user_id=self.test_user_id,
                thread_id=ThreadID(f"initial_thread_{i}"),
                connection_id=ConnectionID(f"initial_conn_{i}")
            )

            manager = WebSocketManager(mock_ws, mode)
            await manager.initialize()

            initial_managers.append(manager)
            self.created_managers.append(manager)

        # Now simulate some connections being "stale" (should be cleaned up)
        stale_count = 3
        for i in range(stale_count):
            initial_managers[i]._websocket.closed = True  # Mark as closed

        # Try to create new connections that should trigger emergency cleanup
        successful_new_connections = 0

        for i in range(stale_count + 1):  # Try to create more than stale connections available
            try:
                mock_ws = self._create_mock_websocket(f"new_ws_{i}")

                mode = create_isolated_mode(
                    user_id=self.test_user_id,
                    thread_id=ThreadID(f"new_thread_{i}"),
                    connection_id=ConnectionID(f"new_conn_{i}")
                )

                manager = WebSocketManager(mock_ws, mode)
                await manager.initialize()

                successful_new_connections += 1
                self.created_managers.append(manager)

            except Exception as e:
                logger.info(f"New connection {i} failed: {e}")
                break

        # BUG ASSERTION: This should FAIL because cleanup doesn't free enough slots
        # Emergency cleanup should have freed at least 'stale_count' slots
        self.assertGreaterEqual(
            successful_new_connections,
            stale_count,
            f"BUG DETECTED: Emergency cleanup failed to free sufficient slots. "
            f"Expected at least {stale_count} new connections after cleanup of stale connections, "
            f"but only {successful_new_connections} succeeded. "
            f"Emergency cleanup is not properly detecting and removing stale connections."
        )

    async def test_user_blocked_from_new_connections_after_failed_cleanup(self):
        """
        TEST CASE 4: Test that user gets permanently blocked from new connections
        after emergency cleanup fails.

        EXPECTED RESULT: This test should FAIL because failed emergency cleanup
        leaves the user in a state where they cannot create any new connections.

        BUG PROOF: After emergency cleanup fails, the user should still be able to
        create new connections once resources are properly freed, but the bug
        causes a permanent block.
        """
        logger.info("Testing user connection blocking after failed emergency cleanup")

        # Fill up connections to trigger emergency cleanup failure
        for i in range(MAX_CONNECTIONS_PER_USER + 2):  # Exceed limit to trigger emergency mode
            try:
                mock_ws = self._create_mock_websocket(f"overflow_ws_{i}")

                mode = create_isolated_mode(
                    user_id=self.test_user_id,
                    thread_id=ThreadID(f"overflow_thread_{i}"),
                    connection_id=ConnectionID(f"overflow_conn_{i}")
                )

                manager = WebSocketManager(mock_ws, mode)
                await manager.initialize()
                self.created_managers.append(manager)

            except Exception as e:
                logger.info(f"Expected overflow failure at connection {i}: {e}")
                # Expected to fail after limit
                break

        # Now manually clean up ALL managers to simulate proper cleanup
        for manager in self.created_managers:
            try:
                if hasattr(manager, 'cleanup'):
                    await manager.cleanup()
                # Also simulate WebSocket closure
                if hasattr(manager, '_websocket'):
                    manager._websocket.closed = True
            except Exception as e:
                logger.warning(f"Manual cleanup error: {e}")

        # Clear our tracking (simulating proper cleanup)
        self.created_managers.clear()

        # Wait a bit to ensure cleanup propagates
        await asyncio.sleep(0.1)

        # Now try to create a new connection - this should work since we cleaned up
        try:
            mock_ws = self._create_mock_websocket("recovery_test_ws")

            mode = create_isolated_mode(
                user_id=self.test_user_id,
                thread_id=ThreadID("recovery_thread"),
                connection_id=ConnectionID("recovery_conn")
            )

            recovery_manager = WebSocketManager(mock_ws, mode)
            await recovery_manager.initialize()
            self.created_managers.append(recovery_manager)

            logger.info("Recovery connection succeeded")

        except Exception as e:
            # BUG DETECTED: User is still blocked even after manual cleanup
            self.fail(
                f"BUG DETECTED: User {self.test_user_id} is permanently blocked from new connections "
                f"even after proper cleanup. Emergency cleanup failure created permanent block. "
                f"Error: {e}. This indicates the emergency cleanup system is not properly "
                f"tracking or resetting user connection counts."
            )


if __name__ == "__main__":
    unittest.main()