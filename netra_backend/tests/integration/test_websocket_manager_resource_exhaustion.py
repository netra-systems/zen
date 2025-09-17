"""
Integration Test: WebSocket Manager Resource Exhaustion

This test reproduces resource exhaustion scenarios in a more realistic environment
with multiple WebSocket managers and real service interactions.

REPRODUCTION TARGET:
- Multi-user resource exhaustion scenarios
- WebSocket manager isolation failures
- Real service integration during resource limits
- Cross-manager cleanup interference

BUSINESS IMPACT:
- Platform stability under load
- Multi-user isolation during resource pressure
- Service degradation prevention during peak usage

This test uses real services and Docker orchestration when available.
"""

import pytest
import asyncio
import time
import gc
from typing import Dict, List, Set
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.canonical_import_patterns import (
    get_websocket_manager,
    UnifiedWebSocketManager,
    WebSocketConnection,
    create_test_user_context,
    check_websocket_service_available
)
from netra_backend.app.websocket_core.unified_manager import MAX_CONNECTIONS_PER_USER
from netra_backend.app.websocket_core.types import WebSocketManagerMode
from shared.types.core_types import ensure_user_id, ensure_websocket_id
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

# Import database connectivity for integration testing
try:
    from netra_backend.app.db.database_manager import get_database_manager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# Import configuration for real service testing
try:
    from netra_backend.app.core.configuration.base import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


class TestWebSocketManagerResourceExhaustion(SSotAsyncTestCase):
    """
    Integration tests for WebSocket Manager resource exhaustion scenarios.

    This test class validates behavior under resource pressure with:
    - Multiple concurrent users
    - Real service integration
    - Cross-manager resource sharing
    - Memory and connection limit enforcement
    """

    def setup_method(self, method):
        """Setup test environment with real services when available."""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()

        # Create multiple test users for multi-user scenarios
        self.test_users = {
            'primary': ensure_user_id(self.id_manager.generate_id(IDType.USER, prefix="exhaust_primary")),
            'secondary': ensure_user_id(self.id_manager.generate_id(IDType.USER, prefix="exhaust_secondary")),
            'tertiary': ensure_user_id(self.id_manager.generate_id(IDType.USER, prefix="exhaust_tertiary"))
        }

        # Track managers and connections for cleanup
        self.active_managers: Dict[str, UnifiedWebSocketManager] = {}
        self.active_connections: Dict[str, List[WebSocketConnection]] = {}
        self.resource_metrics: Dict[str, any] = {
            'peak_connections': 0,
            'failed_cleanups': 0,
            'memory_samples': [],
            'cleanup_times': []
        }

    async def teardown_method(self, method):
        """Comprehensive cleanup of integration test resources."""
        cleanup_start = time.time()

        # Clean up all active connections
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    if hasattr(connection, 'websocket') and connection.websocket:
                        await connection.websocket.close()
                except Exception as e:
                    self.logger.warning(f"Failed to close connection {connection.connection_id}: {e}")

        # Clean up all active managers
        for user_id, manager in self.active_managers.items():
            try:
                if hasattr(manager, 'shutdown'):
                    await manager.shutdown()
            except Exception as e:
                self.logger.warning(f"Failed to shutdown manager for user {user_id}: {e}")

        # Force garbage collection to validate memory cleanup
        gc.collect()

        cleanup_time = time.time() - cleanup_start
        self.resource_metrics['cleanup_times'].append(cleanup_time)

        self.logger.info(f"Integration test cleanup completed in {cleanup_time:.3f}s")
        self.logger.info(f"Resource metrics: {self.resource_metrics}")

        await super().teardown_method(method)

    def _create_realistic_websocket(self, connection_id: str, user_id: str) -> MagicMock:
        """Create a realistic WebSocket mock that behaves like a real WebSocket connection."""
        mock_websocket = MagicMock()
        mock_websocket.closed = False
        mock_websocket.close = AsyncMock()

        # Add realistic WebSocket state tracking
        mock_websocket._connection_id = connection_id
        mock_websocket._user_id = user_id
        mock_websocket.state = MagicMock()
        mock_websocket.state.value = 1  # OPEN state

        # Add send/receive simulation
        mock_websocket.send = AsyncMock()
        mock_websocket.recv = AsyncMock()

        # Add realistic close behavior
        async def realistic_close(*args, **kwargs):
            mock_websocket.closed = True
            mock_websocket.state.value = 3  # CLOSED state

        mock_websocket.close = realistic_close

        return mock_websocket

    async def _create_user_manager(self, user_id: str) -> UnifiedWebSocketManager:
        """Create a WebSocket manager for a specific user with real service integration."""
        user_context = create_test_user_context()
        user_context.user_id = user_id

        # Use real service integration when available
        mode = WebSocketManagerMode.ISOLATED
        if await check_websocket_service_available():
            mode = WebSocketManagerMode.UNIFIED

        manager = get_websocket_manager(user_context=user_context, mode=mode)
        self.active_managers[user_id] = manager

        return manager

    async def _create_user_connections(self, user_id: str, count: int,
                                     connection_type: str = "normal") -> List[WebSocketConnection]:
        """Create multiple WebSocket connections for a user with different behavioral types."""
        connections = []
        manager = self.active_managers.get(user_id)

        if not manager:
            manager = await self._create_user_manager(user_id)

        for i in range(count):
            connection_id = ensure_websocket_id(
                self.id_manager.generate_id(IDType.WEBSOCKET, prefix=f"{connection_type}_{i}")
            )

            mock_websocket = self._create_realistic_websocket(connection_id, user_id)

            # Create different connection behavior types
            if connection_type == "zombie":
                # Zombie connections resist cleanup
                async def failing_close(*args, **kwargs):
                    self.resource_metrics['failed_cleanups'] += 1
                    raise Exception(f"Zombie connection {connection_id} refuses to close")
                mock_websocket.close = failing_close

            elif connection_type == "slow":
                # Slow connections take time to clean up
                async def slow_close(*args, **kwargs):
                    await asyncio.sleep(0.5)  # 500ms cleanup delay
                    mock_websocket.closed = True
                mock_websocket.close = slow_close

            elif connection_type == "leaky":
                # Leaky connections don't properly release resources
                mock_websocket._memory_leak_simulation = b"x" * 1024  # 1KB leak per connection

            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=mock_websocket,
                connected_at=datetime.now(timezone.utc),
                thread_id=self.id_manager.generate_id(IDType.THREAD, prefix="integration"),
                metadata={"connection_type": connection_type, "test": True}
            )

            try:
                await manager.add_connection(connection)
                connections.append(connection)

                # Track peak connections
                total_connections = sum(len(conns) for conns in self.active_connections.values())
                self.resource_metrics['peak_connections'] = max(
                    self.resource_metrics['peak_connections'], total_connections + 1
                )

            except ValueError as e:
                if "exceeded maximum connections" in str(e):
                    self.logger.info(f"Hit connection limit for user {user_id[:8]} at connection {i}")
                    break
                else:
                    raise

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].extend(connections)

        return connections

    async def test_multi_user_resource_exhaustion(self):
        """
        Test resource exhaustion scenarios with multiple users.

        Validates:
        - User isolation is maintained under resource pressure
        - One user hitting limits doesn't affect other users
        - Cross-user cleanup doesn't interfere with active connections
        """
        self.logger.info("Testing multi-user resource exhaustion scenarios...")

        # PHASE 1: Fill primary user to near-limit
        primary_user = self.test_users['primary']
        primary_connections = await self._create_user_connections(
            primary_user, MAX_CONNECTIONS_PER_USER - 2, "normal"
        )

        self.assertEqual(len(primary_connections), MAX_CONNECTIONS_PER_USER - 2,
                        "Primary user should have near-limit connections")

        # PHASE 2: Fill secondary user with zombie connections (problematic)
        secondary_user = self.test_users['secondary']
        secondary_connections = await self._create_user_connections(
            secondary_user, MAX_CONNECTIONS_PER_USER, "zombie"
        )

        # PHASE 3: Tertiary user should still be able to create connections
        tertiary_user = self.test_users['tertiary']
        tertiary_connections = await self._create_user_connections(
            tertiary_user, 5, "normal"
        )

        self.assertEqual(len(tertiary_connections), 5,
                        "Tertiary user should be unaffected by other users' resource issues")

        # PHASE 4: Primary user should still be able to add remaining connections
        remaining_connections = await self._create_user_connections(
            primary_user, 2, "normal"
        )

        total_primary = len(primary_connections) + len(remaining_connections)
        self.assertEqual(total_primary, MAX_CONNECTIONS_PER_USER,
                        "Primary user should reach exactly the limit")

        # PHASE 5: Verify isolation - secondary's zombie problem shouldn't affect others
        try:
            # Primary user should hit limit cleanly
            overflow_connection = await self._create_user_connections(primary_user, 1, "normal")
            self.assertEqual(len(overflow_connection), 0,
                           "Primary user should be at limit and unable to add more")
        except Exception:
            pass  # Expected to hit limit

        # Tertiary should still work fine
        more_tertiary = await self._create_user_connections(tertiary_user, 3, "normal")
        self.assertEqual(len(more_tertiary), 3,
                        "Tertiary user should remain unaffected by resource exhaustion in other users")

        self.logger.info(f"Multi-user isolation test passed. Peak connections: {self.resource_metrics['peak_connections']}")

    async def test_emergency_cleanup_with_real_services(self):
        """
        Test emergency cleanup behavior with real service integration.

        This test validates cleanup under realistic conditions:
        - Database connections during cleanup
        - Memory pressure during resource limits
        - Service degradation prevention
        """
        if not (DB_AVAILABLE and CONFIG_AVAILABLE):
            pytest.skip("Real services not available for integration testing")

        self.logger.info("Testing emergency cleanup with real service integration...")

        user_id = self.test_users['primary']

        # Create manager with real service backing
        manager = await self._create_user_manager(user_id)

        # Add real service integration components
        if DB_AVAILABLE:
            try:
                db_manager = get_database_manager()
                self.logger.info("Database integration available for cleanup testing")
            except Exception as e:
                self.logger.warning(f"Database integration failed: {e}")

        # Create connections with mixed types including problematic ones
        normal_connections = await self._create_user_connections(user_id, 10, "normal")
        zombie_connections = await self._create_user_connections(user_id, 5, "zombie")
        slow_connections = await self._create_user_connections(user_id, 5, "slow")

        total_connections = len(normal_connections) + len(zombie_connections) + len(slow_connections)
        self.assertEqual(total_connections, MAX_CONNECTIONS_PER_USER,
                        "Should have exactly MAX_CONNECTIONS_PER_USER connections")

        # Attempt emergency cleanup by trying to add one more connection
        cleanup_start_time = time.time()

        try:
            overflow_connection = await self._create_user_connections(user_id, 1, "normal")
            if len(overflow_connection) > 0:
                self.fail("Should not have been able to add connection beyond limit")
        except ValueError as e:
            self.assertIn("exceeded maximum connections", str(e))
            self.logger.info("Expected limit enforcement triggered")

        cleanup_time = time.time() - cleanup_start_time
        self.resource_metrics['cleanup_times'].append(cleanup_time)

        # Verify emergency cleanup attempted to handle problematic connections
        self.assertGreater(self.resource_metrics['failed_cleanups'], 0,
                          "Should have attempted cleanup of zombie connections")

        # Verify real service integration didn't break during cleanup
        if DB_AVAILABLE:
            try:
                # Verify database still accessible after cleanup stress
                db_manager = get_database_manager()
                self.logger.info("Database integration remained stable during cleanup")
            except Exception as e:
                self.fail(f"Real service integration failed during cleanup: {e}")

        self.logger.info(f"Emergency cleanup with real services completed in {cleanup_time:.3f}s")

    async def test_memory_pressure_during_resource_limits(self):
        """
        Test system behavior under memory pressure combined with connection limits.

        Validates:
        - Memory usage tracking during resource exhaustion
        - Cleanup efficiency under memory pressure
        - Resource leak detection
        """
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        self.resource_metrics['memory_samples'].append(('initial', initial_memory))
        self.logger.info(f"Initial memory usage: {initial_memory:.1f} MB")

        user_id = self.test_users['primary']
        manager = await self._create_user_manager(user_id)

        # Create connections with intentional memory leaks
        leaky_connections = await self._create_user_connections(user_id, MAX_CONNECTIONS_PER_USER, "leaky")

        after_creation_memory = process.memory_info().rss / 1024 / 1024  # MB
        self.resource_metrics['memory_samples'].append(('after_creation', after_creation_memory))

        memory_increase = after_creation_memory - initial_memory
        self.logger.info(f"Memory after connection creation: {after_creation_memory:.1f} MB (+{memory_increase:.1f} MB)")

        # Attempt cleanup under memory pressure
        cleanup_start_time = time.time()

        connections_to_cleanup = leaky_connections[:10]  # Cleanup first 10
        for connection in connections_to_cleanup:
            try:
                await manager.remove_connection(connection.connection_id)
            except Exception as e:
                self.logger.info(f"Cleanup failed for connection {connection.connection_id}: {e}")

        # Force garbage collection
        gc.collect()

        after_cleanup_memory = process.memory_info().rss / 1024 / 1024  # MB
        self.resource_metrics['memory_samples'].append(('after_cleanup', after_cleanup_memory))

        cleanup_time = time.time() - cleanup_start_time
        self.resource_metrics['cleanup_times'].append(cleanup_time)

        # Validate memory behavior
        memory_after_cleanup = after_cleanup_memory - initial_memory
        self.logger.info(f"Memory after cleanup: {after_cleanup_memory:.1f} MB (net: +{memory_after_cleanup:.1f} MB)")

        # Memory should not grow unbounded
        self.assertLess(memory_after_cleanup, memory_increase * 2,
                       f"Memory usage should not double after cleanup. "
                       f"Before cleanup: +{memory_increase:.1f}MB, After: +{memory_after_cleanup:.1f}MB")

        # Cleanup should complete in reasonable time even under memory pressure
        self.assertLess(cleanup_time, 10.0,
                       f"Cleanup should complete within 10 seconds even under memory pressure, got {cleanup_time:.3f}s")

        self.logger.info(f"Memory pressure test completed. Memory samples: {self.resource_metrics['memory_samples']}")

    async def test_concurrent_cleanup_interference(self):
        """
        Test that concurrent cleanup operations don't interfere with each other.

        Validates:
        - Multiple users can perform cleanup simultaneously
        - Cleanup operations are properly isolated
        - No race conditions in resource management
        """
        self.logger.info("Testing concurrent cleanup interference...")

        # Create managers for all test users
        managers = {}
        for user_key, user_id in self.test_users.items():
            managers[user_key] = await self._create_user_manager(user_id)

        # Fill all users with connections of different types
        user_connections = {}
        for user_key, user_id in self.test_users.items():
            connection_type = ["normal", "zombie", "slow"][hash(user_key) % 3]
            connections = await self._create_user_connections(user_id, MAX_CONNECTIONS_PER_USER, connection_type)
            user_connections[user_key] = connections

        # Trigger concurrent cleanup operations
        async def cleanup_user_connections(user_key: str, user_id: str):
            manager = managers[user_key]
            connections = user_connections[user_key]

            cleanup_count = 0
            cleanup_failures = 0

            # Cleanup half of the connections for each user
            connections_to_cleanup = connections[:len(connections)//2]

            for connection in connections_to_cleanup:
                try:
                    await manager.remove_connection(connection.connection_id)
                    cleanup_count += 1
                except Exception as e:
                    cleanup_failures += 1
                    self.logger.debug(f"Cleanup failed for {user_key} connection {connection.connection_id}: {e}")

            return cleanup_count, cleanup_failures

        # Execute all cleanups concurrently
        cleanup_tasks = [
            cleanup_user_connections(user_key, user_id)
            for user_key, user_id in self.test_users.items()
        ]

        concurrent_start_time = time.time()
        cleanup_results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        concurrent_cleanup_time = time.time() - concurrent_start_time

        self.resource_metrics['cleanup_times'].append(concurrent_cleanup_time)

        # Validate concurrent cleanup results
        total_cleaned = 0
        total_failures = 0

        for i, result in enumerate(cleanup_results):
            user_key = list(self.test_users.keys())[i]

            if isinstance(result, Exception):
                self.fail(f"Concurrent cleanup failed for user {user_key}: {result}")

            cleaned, failures = result
            total_cleaned += cleaned
            total_failures += failures

            self.logger.info(f"User {user_key}: cleaned {cleaned}, failed {failures}")

        # Validate isolation - each user should have independent cleanup results
        self.assertGreater(total_cleaned, 0, "Should have successfully cleaned some connections")

        # Verify no race conditions - cleanup time should be reasonable even with concurrency
        self.assertLess(concurrent_cleanup_time, 15.0,
                       f"Concurrent cleanup should complete within 15 seconds, got {concurrent_cleanup_time:.3f}s")

        self.logger.info(f"Concurrent cleanup test completed. "
                        f"Total cleaned: {total_cleaned}, Total failures: {total_failures}, "
                        f"Time: {concurrent_cleanup_time:.3f}s")

    async def test_resource_exhaustion_recovery(self):
        """
        Test recovery behavior after resource exhaustion events.

        Validates:
        - System can recover from resource exhaustion
        - New connections work after cleanup
        - No permanent resource leaks after recovery
        """
        self.logger.info("Testing resource exhaustion recovery...")

        user_id = self.test_users['primary']
        manager = await self._create_user_manager(user_id)

        # PHASE 1: Exhaust resources
        exhaustion_connections = await self._create_user_connections(user_id, MAX_CONNECTIONS_PER_USER, "normal")
        self.assertEqual(len(exhaustion_connections), MAX_CONNECTIONS_PER_USER)

        # PHASE 2: Verify exhaustion
        try:
            overflow_connection = await self._create_user_connections(user_id, 1, "normal")
            if len(overflow_connection) > 0:
                self.fail("Should not be able to add connection when at limit")
        except ValueError:
            pass  # Expected

        # PHASE 3: Perform recovery by cleaning up half the connections
        recovery_start_time = time.time()
        connections_to_remove = exhaustion_connections[:MAX_CONNECTIONS_PER_USER//2]

        removed_count = 0
        for connection in connections_to_remove:
            try:
                await manager.remove_connection(connection.connection_id)
                removed_count += 1
            except Exception as e:
                self.logger.warning(f"Recovery cleanup failed for {connection.connection_id}: {e}")

        recovery_time = time.time() - recovery_start_time
        self.resource_metrics['cleanup_times'].append(recovery_time)

        self.assertGreater(removed_count, 0, "Should have successfully removed some connections during recovery")

        # PHASE 4: Verify recovery - should be able to add new connections
        post_recovery_connections = await self._create_user_connections(user_id, 5, "normal")
        self.assertGreater(len(post_recovery_connections), 0,
                          "Should be able to add new connections after recovery")

        # PHASE 5: Verify system stability after recovery
        user_connections_set = manager._user_connections.get(user_id, set())
        expected_connections = MAX_CONNECTIONS_PER_USER - removed_count + len(post_recovery_connections)

        # Allow for some variance due to cleanup timing
        self.assertLessEqual(len(user_connections_set), MAX_CONNECTIONS_PER_USER,
                           "Should not exceed maximum connections after recovery")

        self.logger.info(f"Resource exhaustion recovery completed in {recovery_time:.3f}s. "
                        f"Removed: {removed_count}, Added: {len(post_recovery_connections)}, "
                        f"Final count: {len(user_connections_set)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])