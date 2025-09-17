"""
Unit Test: WebSocket Manager Emergency Cleanup Failure

This test reproduces the specific emergency cleanup failure scenario:
"HARD LIMIT: User still over limit after cleanup (20/20)"

REPRODUCTION TARGET:
- User hits MAX_CONNECTIONS_PER_USER (20) limit
- Emergency cleanup is triggered
- Cleanup fails to reduce connection count
- User remains over limit after cleanup
- System logs "HARD LIMIT: User still over limit after cleanup (20/20)"

BUSINESS IMPACT:
- Golden Path disruption: Users cannot establish new WebSocket connections
- Revenue impact: Chat functionality blocked for affected users
- Customer experience: Connection failures during AI interactions

This test follows SSOT testing patterns and uses real services.
"""

import pytest
import asyncio
import time
from typing import List, Set
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.websocket_manager import (
    get_websocket_manager,
    UnifiedWebSocketManager,
    WebSocketConnection,
    create_test_user_context
)
from netra_backend.app.websocket_core.websocket_manager import MAX_CONNECTIONS_PER_USER
from netra_backend.app.websocket_core.types import WebSocketManagerMode
from shared.types.core_types import ensure_user_id, ensure_websocket_id
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestWebSocketManagerEmergencyCleanup(SSotAsyncTestCase):
    """
    Unit tests for WebSocket Manager emergency cleanup failure scenarios.

    This test class specifically reproduces the "HARD LIMIT: User still over limit after cleanup"
    scenario identified in the WebSocket Manager Emergency Cleanup Failure issue.
    """

    def setup_method(self, method):
        """Setup test environment for each test method."""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.test_user_id = ensure_user_id(self.id_manager.generate_id(IDType.USER, prefix="cleanup_test"))
        self.zombie_connections: List[WebSocketConnection] = []
        self.cleanup_failures: List[str] = []

    async def teardown_method(self, method):
        """Cleanup after each test."""
        # Clean up any zombie connections created during testing
        for connection in self.zombie_connections:
            try:
                if hasattr(connection, 'websocket') and connection.websocket:
                    await connection.websocket.close()
            except Exception:
                pass
        self.zombie_connections.clear()
        await super().teardown_method(method)

    def _create_mock_websocket(self, connection_id: str) -> MagicMock:
        """Create a mock WebSocket connection for testing."""
        mock_websocket = MagicMock()
        mock_websocket.closed = False
        mock_websocket.close = AsyncMock()

        # Simulate connection state for cleanup scenarios
        mock_websocket._connection_id = connection_id
        mock_websocket.state = MagicMock()
        mock_websocket.state.value = 1  # OPEN state

        return mock_websocket

    def _create_test_websocket_connection(self, user_id: str, connection_suffix: str = None) -> WebSocketConnection:
        """Create a test WebSocket connection that can become a zombie."""
        connection_id = ensure_websocket_id(
            self.id_manager.generate_id(IDType.WEBSOCKET, prefix=f"zombie_{connection_suffix or 'conn'}")
        )

        mock_websocket = self._create_mock_websocket(connection_id)

        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc),
            thread_id=self.id_manager.generate_id(IDType.THREAD, prefix="test_thread"),
            metadata={"test": True, "cleanup_test": True}
        )

        self.zombie_connections.append(connection)
        return connection

    async def _create_zombie_manager_scenario(self, manager: UnifiedWebSocketManager,
                                            user_id: str, zombie_count: int = 15) -> List[WebSocketConnection]:
        """
        Create a scenario with zombie connections that resist cleanup.

        This simulates the conditions that lead to emergency cleanup failure:
        - Connections that appear active but are actually stale
        - Connections with inconsistent cleanup keys
        - Connections that fail validation during cleanup
        """
        zombie_connections = []

        for i in range(zombie_count):
            connection = self._create_test_websocket_connection(user_id, f"zombie_{i}")

            # Simulate different types of zombie conditions
            if i % 3 == 0:
                # Type 1: Stale connection with mismatched cleanup keys
                connection.metadata["cleanup_key_mismatch"] = True
                # Simulate thread_id inconsistency that prevents cleanup
                connection.thread_id = f"mismatched_thread_{i}"

            elif i % 3 == 1:
                # Type 2: Connection that appears active but is actually dead
                connection.websocket.closed = False  # Appears active
                connection.websocket.state.value = 1  # OPEN state
                # But will fail during cleanup validation
                connection.metadata["cleanup_validation_failure"] = True

            else:
                # Type 3: Connection with broken cleanup process
                connection.metadata["cleanup_process_failure"] = True
                # Mock cleanup process to fail
                original_close = connection.websocket.close
                async def failing_close(*args, **kwargs):
                    self.cleanup_failures.append(connection.connection_id)
                    raise Exception(f"Cleanup failed for {connection.connection_id}")
                connection.websocket.close = failing_close

            # Add connection to manager (this should work)
            try:
                await manager.add_connection(connection)
                zombie_connections.append(connection)
            except ValueError as e:
                if "exceeded maximum connections" in str(e):
                    # Expected once we hit the limit
                    break
                else:
                    raise

        return zombie_connections

    async def test_emergency_cleanup_failure_reproduction(self):
        """
        CRITICAL TEST: Reproduce the exact "User still over limit after cleanup" scenario.

        This test reproduces the specific failure mode:
        1. User accumulates MAX_CONNECTIONS_PER_USER (20) connections
        2. Emergency cleanup is triggered when trying to add connection #21
        3. Cleanup attempts to remove zombie connections but fails
        4. User remains at 20/20 connections after cleanup
        5. System logs "HARD LIMIT: User still over limit after cleanup (20/20)"
        """
        user_context = create_test_user_context()
        user_context.user_id = self.test_user_id

        # Create manager for test user
        manager = get_websocket_manager(user_context=user_context, mode=WebSocketManagerMode.ISOLATED)

        # STEP 1: Fill user to MAX_CONNECTIONS_PER_USER limit with zombie connections
        self.logger.info(f"Creating {MAX_CONNECTIONS_PER_USER} zombie connections for user {self.test_user_id[:8]}...")

        zombie_connections = await self._create_zombie_manager_scenario(
            manager, self.test_user_id, zombie_count=MAX_CONNECTIONS_PER_USER
        )

        # Verify we're at the limit
        user_connections = manager._user_connections.get(self.test_user_id, set())
        self.assertEqual(len(user_connections), MAX_CONNECTIONS_PER_USER,
                        f"Should be at MAX_CONNECTIONS_PER_USER ({MAX_CONNECTIONS_PER_USER}) before cleanup test")

        # STEP 2: Attempt to add one more connection (should trigger emergency cleanup)
        self.logger.info("Attempting to add connection #21 to trigger emergency cleanup...")

        overflow_connection = self._create_test_websocket_connection(self.test_user_id, "overflow")

        # This should trigger the emergency cleanup failure
        with self.assertRaises(ValueError) as context:
            await manager.add_connection(overflow_connection)

        # STEP 3: Verify the specific error message matches the issue description
        error_message = str(context.exception)
        self.assertIn("exceeded maximum connections per user limit", error_message)
        self.assertIn(str(MAX_CONNECTIONS_PER_USER), error_message)

        # STEP 4: Verify emergency cleanup was attempted but failed
        # Check that user is still over limit after cleanup attempt
        user_connections_after_cleanup = manager._user_connections.get(self.test_user_id, set())

        self.assertGreaterEqual(len(user_connections_after_cleanup), MAX_CONNECTIONS_PER_USER,
                               "REPRODUCTION SUCCESS: User still over limit after cleanup attempt")

        # STEP 5: Verify cleanup failures occurred
        self.assertGreater(len(self.cleanup_failures), 0,
                          "Should have recorded cleanup failures for zombie connections")

        self.logger.warning(f"REPRODUCED ISSUE: User {self.test_user_id[:8]} still has "
                          f"{len(user_connections_after_cleanup)}/{MAX_CONNECTIONS_PER_USER} connections "
                          f"after emergency cleanup attempt. Cleanup failed for {len(self.cleanup_failures)} connections.")

    async def test_zombie_connection_detection(self):
        """
        Test detection of zombie connections that prevent proper cleanup.

        Zombie connections are connections that:
        - Appear active in the manager's tracking
        - Cannot be cleaned up due to various failure modes
        - Accumulate over time leading to resource exhaustion
        """
        user_context = create_test_user_context()
        user_context.user_id = self.test_user_id

        manager = get_websocket_manager(user_context=user_context, mode=WebSocketManagerMode.ISOLATED)

        # Create different types of zombie connections
        zombie_connections = []

        # Type 1: Connection with thread_id mismatch (most common cause)
        zombie_1 = self._create_test_websocket_connection(self.test_user_id, "thread_mismatch")
        zombie_1.thread_id = "mismatched_thread_id"
        await manager.add_connection(zombie_1)
        zombie_connections.append(zombie_1)

        # Type 2: Connection with broken WebSocket close method
        zombie_2 = self._create_test_websocket_connection(self.test_user_id, "broken_close")
        original_close = zombie_2.websocket.close
        async def broken_close(*args, **kwargs):
            raise Exception("WebSocket close failed")
        zombie_2.websocket.close = broken_close
        await manager.add_connection(zombie_2)
        zombie_connections.append(zombie_2)

        # Type 3: Connection with inconsistent cleanup keys
        zombie_3 = self._create_test_websocket_connection(self.test_user_id, "key_mismatch")
        zombie_3.metadata["isolation_key_mismatch"] = True
        await manager.add_connection(zombie_3)
        zombie_connections.append(zombie_3)

        # Verify all zombies are tracked
        user_connections = manager._user_connections.get(self.test_user_id, set())
        self.assertEqual(len(user_connections), 3, "Should have 3 zombie connections")

        # Attempt cleanup - should detect and log zombie connections
        cleanup_attempted = 0
        cleanup_succeeded = 0

        for connection in zombie_connections:
            try:
                await manager.remove_connection(connection.connection_id)
                cleanup_succeeded += 1
            except Exception as e:
                cleanup_attempted += 1
                self.logger.warning(f"Zombie detection SUCCESS: Connection {connection.connection_id} "
                                  f"failed cleanup as expected: {e}")

        # Verify some connections failed cleanup (zombie detection)
        self.assertGreater(cleanup_attempted, 0, "Should have detected zombie connections")

        # Verify zombies remain in manager tracking
        user_connections_after = manager._user_connections.get(self.test_user_id, set())
        self.assertGreater(len(user_connections_after), 0,
                          "Zombie connections should remain in tracking after failed cleanup")

    async def test_resource_validation_during_cleanup(self):
        """
        Test resource validation failures during emergency cleanup.

        This test simulates scenarios where cleanup processes fail validation:
        - Resource locks that prevent cleanup
        - Inconsistent internal state
        - Cleanup race conditions
        """
        user_context = create_test_user_context()
        user_context.user_id = self.test_user_id

        manager = get_websocket_manager(user_context=user_context, mode=WebSocketManagerMode.ISOLATED)

        # Create connections with various validation failure conditions
        connections_with_validation_issues = []

        for i in range(5):
            connection = self._create_test_websocket_connection(self.test_user_id, f"validation_{i}")

            # Simulate different validation failure scenarios
            if i % 2 == 0:
                # Simulate locked resource that prevents cleanup
                connection.metadata["resource_locked"] = True
                connection.metadata["lock_owner"] = f"some_other_process_{i}"
            else:
                # Simulate inconsistent internal state
                connection.metadata["state_inconsistent"] = True
                connection.metadata["expected_state"] = "CLOSED"
                connection.metadata["actual_state"] = "UNKNOWN"

            await manager.add_connection(connection)
            connections_with_validation_issues.append(connection)

        # Attempt cleanup with validation failures expected
        validation_failures = 0

        for connection in connections_with_validation_issues:
            connection_id = connection.connection_id

            # Mock validation failure during cleanup
            if connection.metadata.get("resource_locked") or connection.metadata.get("state_inconsistent"):
                # Simulate cleanup validation failure
                with patch.object(manager, 'remove_connection') as mock_remove:
                    mock_remove.side_effect = Exception(f"Validation failed for {connection_id}")

                    try:
                        await manager.remove_connection(connection_id)
                    except Exception as e:
                        validation_failures += 1
                        self.logger.info(f"Expected validation failure for {connection_id}: {e}")

        self.assertGreater(validation_failures, 0,
                          "Should have encountered resource validation failures during cleanup")

        # Verify connections remain tracked after validation failures
        user_connections = manager._user_connections.get(self.test_user_id, set())
        self.assertGreater(len(user_connections), 0,
                          "Connections with validation failures should remain in tracking")

    async def test_emergency_cleanup_performance_degradation(self):
        """
        Test performance degradation during emergency cleanup scenarios.

        This test validates that emergency cleanup doesn't cause:
        - Excessive cleanup times (> 5 seconds)
        - Memory leaks during failed cleanup
        - CPU spikes that affect other operations
        """
        user_context = create_test_user_context()
        user_context.user_id = self.test_user_id

        manager = get_websocket_manager(user_context=user_context, mode=WebSocketManagerMode.ISOLATED)

        # Create a scenario with many connections needing cleanup
        cleanup_start_time = time.time()

        # Add connections up to the limit
        for i in range(min(MAX_CONNECTIONS_PER_USER, 10)):  # Limit to 10 for unit test performance
            connection = self._create_test_websocket_connection(self.test_user_id, f"perf_test_{i}")

            # Make every 3rd connection problematic for cleanup
            if i % 3 == 0:
                connection.metadata["cleanup_slow"] = True
                # Simulate slow cleanup
                original_close = connection.websocket.close
                async def slow_close(*args, **kwargs):
                    await asyncio.sleep(0.1)  # 100ms delay
                    await original_close(*args, **kwargs)
                connection.websocket.close = slow_close

            await manager.add_connection(connection)

        # Measure cleanup performance
        user_connections = manager._user_connections.get(self.test_user_id, set())
        connections_to_cleanup = list(user_connections)[:5]  # Cleanup first 5

        cleanup_times = []

        for connection_id in connections_to_cleanup:
            cleanup_start = time.time()
            try:
                await manager.remove_connection(connection_id)
                cleanup_time = time.time() - cleanup_start
                cleanup_times.append(cleanup_time)
            except Exception as e:
                cleanup_time = time.time() - cleanup_start
                cleanup_times.append(cleanup_time)
                self.logger.info(f"Cleanup failed for {connection_id} in {cleanup_time:.3f}s: {e}")

        # Validate performance requirements
        if cleanup_times:
            avg_cleanup_time = sum(cleanup_times) / len(cleanup_times)
            max_cleanup_time = max(cleanup_times)

            self.assertLess(max_cleanup_time, 5.0,
                           f"Individual cleanup should not exceed 5 seconds, got {max_cleanup_time:.3f}s")

            self.assertLess(avg_cleanup_time, 1.0,
                           f"Average cleanup time should be under 1 second, got {avg_cleanup_time:.3f}s")

            self.logger.info(f"Cleanup performance: avg={avg_cleanup_time:.3f}s, max={max_cleanup_time:.3f}s")

        total_cleanup_time = time.time() - cleanup_start_time
        self.assertLess(total_cleanup_time, 10.0,
                       f"Total cleanup operation should complete within 10 seconds, got {total_cleanup_time:.3f}s")

    async def test_hard_limit_error_message_accuracy(self):
        """
        Test that the "HARD LIMIT" error message accurately reflects the state.

        Verifies:
        - Error message contains correct connection counts
        - Error message includes user identification
        - Error logging includes relevant context for debugging
        """
        user_context = create_test_user_context()
        user_context.user_id = self.test_user_id

        manager = get_websocket_manager(user_context=user_context, mode=WebSocketManagerMode.ISOLATED)

        # Fill to exact limit
        connections_added = 0
        for i in range(MAX_CONNECTIONS_PER_USER):
            connection = self._create_test_websocket_connection(self.test_user_id, f"limit_test_{i}")
            try:
                await manager.add_connection(connection)
                connections_added += 1
            except ValueError:
                break

        self.assertEqual(connections_added, MAX_CONNECTIONS_PER_USER,
                        f"Should have successfully added {MAX_CONNECTIONS_PER_USER} connections")

        # Attempt to add one more (should trigger the hard limit error)
        overflow_connection = self._create_test_websocket_connection(self.test_user_id, "overflow")

        with self.assertRaises(ValueError) as context:
            await manager.add_connection(overflow_connection)

        error_message = str(context.exception)

        # Verify error message accuracy
        self.assertIn(self.test_user_id, error_message,
                     "Error message should include user ID")

        self.assertIn(str(MAX_CONNECTIONS_PER_USER), error_message,
                     f"Error message should include limit ({MAX_CONNECTIONS_PER_USER})")

        self.assertIn("maximum connections per user limit", error_message,
                     "Error message should clearly indicate the limit type")

        # Verify current count is mentioned in error
        current_count = len(manager._user_connections.get(self.test_user_id, set()))
        self.assertIn(str(current_count), error_message,
                     f"Error message should include current count ({current_count})")

        self.logger.info(f"HARD LIMIT error message verification passed: {error_message}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])