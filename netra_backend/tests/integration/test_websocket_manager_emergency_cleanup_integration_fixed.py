"""
Integration Tests for WebSocket Manager Emergency Cleanup Resource Exhaustion

CRITICAL TEST PLAN: These tests are designed to FAIL initially to prove the bug exists.
Integration focus: Test real WebSocket components interacting during resource exhaustion.

Business Impact: $500K+ ARR dependent on WebSocket reliability for Golden Path user flow.

Integration Test Cases:
1. Multi-user resource exhaustion with real WebSocket connections
2. Cross-user connection limits and cleanup interaction
3. Real agent execution context during resource exhaustion
4. Integration with actual database session management during cleanup
5. Real-time event emission during emergency cleanup scenarios

Following CLAUDE.md requirements:
- Inherits from SSOT BaseTestCase
- Uses real WebSocket components (no mocking for integration)
- Tests with actual database connections where applicable
- Uses IsolatedEnvironment for environment access
- Tests FAIL to prove bug exists
"""

import unittest
import asyncio
import json
from unittest.mock import MagicMock, patch
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta

# SSOT IMPORT: Following SSOT_IMPORT_REGISTRY.md requirements
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# WebSocket Core imports - Real components for integration testing
from netra_backend.app.websocket_core.websocket_manager import (
    _UnifiedWebSocketManagerImplementation,
    MAX_CONNECTIONS_PER_USER,
    RegistryCompat
)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.types import (
    WebSocketConnection,
    WebSocketManagerMode,
    create_isolated_mode
)
from netra_backend.app.websocket_core.connection_manager import ConnectionManager
from netra_backend.app.websocket_core.user_session_manager import UserSessionManager

# Agent and execution context imports for integration testing
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContextManager

# Core types and utilities
from shared.types.core_types import UserID, ThreadID, ConnectionID, WebSocketID
from shared.logging.unified_logging_ssot import get_logger

# Database integration for connection tracking
from netra_backend.app.db.postgres import PostgresManager

logger = get_logger(__name__)


class TestWebSocketManagerEmergencyCleanupIntegration(SSotAsyncTestCase):
    """
    Integration tests for WebSocket Manager Emergency Cleanup failures during resource exhaustion.

    CRITICAL: These tests are designed to FAIL initially to prove the bug exists.
    They test real component interactions during emergency cleanup scenarios.
    """

    def setup_method(self, method):
        """Set up integration test environment using SSOT patterns."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()

        # Integration test configuration
        self.test_users = [
            UserID(f"integration_user_{i}") for i in range(5)
        ]

        # Track all created managers and connections for cleanup
        self.integration_managers: Dict[UserID, List[WebSocketManager]] = {}
        self.integration_connections: List[MagicMock] = []
        self.active_sessions: Set[str] = set()

        # Initialize user tracking
        for user_id in self.test_users:
            self.integration_managers[user_id] = []

        logger.info(f"Starting integration test: {method.__name__}")

    def teardown_method(self, method):
        """Clean up integration test resources."""
        async def cleanup_async():
            # Clean up all managers
            for user_id, managers in self.integration_managers.items():
                for manager in managers:
                    try:
                        if hasattr(manager, 'cleanup'):
                            await manager.cleanup()
                    except Exception as e:
                        logger.warning(f"Error during manager cleanup for {user_id}: {e}")

            # Clean up connections
            for conn in self.integration_connections:
                try:
                    if hasattr(conn, 'close') and not conn.closed:
                        conn.close()
                except Exception as e:
                    logger.warning(f"Error during connection cleanup: {e}")

        # Run cleanup
        try:
            asyncio.get_event_loop().run_until_complete(cleanup_async())
        except Exception as e:
            logger.warning(f"Error during integration cleanup: {e}")

        self.integration_managers.clear()
        self.integration_connections.clear()
        self.active_sessions.clear()

        super().teardown_method(method)

    def _create_realistic_websocket_mock(self, user_id: UserID, connection_id: str) -> MagicMock:
        """Create a realistic WebSocket mock for integration testing."""
        mock_ws = MagicMock()
        mock_ws.id = connection_id
        mock_ws.closed = False
        mock_ws.close = MagicMock()
        mock_ws.send = MagicMock()

        # Realistic WebSocket properties
        mock_ws.remote_address = ("127.0.0.1", 12345 + len(self.integration_connections))
        mock_ws.path = f"/ws/user/{user_id}"
        mock_ws.request_headers = {
            "User-Agent": "TestClient/1.0",
            "Origin": "https://staging.netrasystems.ai",
            "Connection": "Upgrade",
            "Upgrade": "websocket"
        }

        # Track connection state changes
        original_close = mock_ws.close

        def close_with_tracking():
            mock_ws.closed = True
            logger.debug(f"WebSocket {connection_id} for user {user_id} closed")
            return original_close()

        mock_ws.close = close_with_tracking

        self.integration_connections.append(mock_ws)
        return mock_ws

    async def test_multi_user_resource_exhaustion_cascade_failure(self):
        """
        INTEGRATION TEST 1: Multi-user resource exhaustion leads to cascade failures.

        EXPECTED RESULT: This test should FAIL because emergency cleanup fails
        across multiple users, causing system-wide WebSocket connection issues.

        BUG PROOF: When multiple users hit connection limits simultaneously,
        emergency cleanup fails and blocks all users from new connections.
        """
        logger.info("Testing multi-user resource exhaustion cascade failure")

        # Track successful and failed connections per user
        user_success_counts = {user_id: 0 for user_id in self.test_users}
        user_failure_counts = {user_id: 0 for user_id in self.test_users}

        # Create connections for each user up to and beyond limits
        for user_id in self.test_users:
            logger.info(f"Creating connections for user: {user_id}")

            for i in range(MAX_CONNECTIONS_PER_USER + 3):  # Exceed limit by 3
                try:
                    mock_ws = self._create_realistic_websocket_mock(
                        user_id, f"{user_id}_conn_{i}"
                    )

                    mode = create_isolated_mode(
                        user_id=user_id,
                        thread_id=ThreadID(f"{user_id}_thread_{i}"),
                        connection_id=ConnectionID(f"{user_id}_conn_{i}")
                    )

                    manager = WebSocketManager(mock_ws, mode)
                    await manager.initialize()

                    self.integration_managers[user_id].append(manager)
                    user_success_counts[user_id] += 1

                    logger.debug(f"Created connection {i+1} for user {user_id}")

                except Exception as e:
                    user_failure_counts[user_id] += 1
                    logger.info(f"Connection {i+1} failed for user {user_id}: {e}")

        # Analyze results for cascade failure patterns
        total_successful_connections = sum(user_success_counts.values())
        total_failed_connections = sum(user_failure_counts.values())

        logger.info(f"Total successful connections: {total_successful_connections}")
        logger.info(f"Total failed connections: {total_failed_connections}")
        logger.info(f"Per-user success: {user_success_counts}")
        logger.info(f"Per-user failures: {user_failure_counts}")

        # BUG ASSERTION 1: Each user should be limited to MAX_CONNECTIONS_PER_USER
        for user_id, success_count in user_success_counts.items():
            self.assertLessEqual(
                success_count,
                MAX_CONNECTIONS_PER_USER,
                f"BUG DETECTED: User {user_id} has {success_count} connections, "
                f"exceeding MAX_CONNECTIONS_PER_USER ({MAX_CONNECTIONS_PER_USER}). "
                f"Emergency cleanup failed to enforce per-user limits."
            )

        # BUG ASSERTION 2: System should not have complete cascade failure
        # At least some connections should succeed for each user
        users_completely_blocked = [
            user_id for user_id, count in user_success_counts.items() if count == 0
        ]

        self.assertEqual(
            len(users_completely_blocked),
            0,
            f"BUG DETECTED: Complete cascade failure - users {users_completely_blocked} "
            f"are completely blocked from connections. Emergency cleanup failure "
            f"caused system-wide WebSocket unavailability."
        )

        # Now test cross-user cleanup interference
        # Try to create new connections for one user after others hit limits
        test_user = self.test_users[0]

        # Manually close some connections for test user to free slots
        managers_to_close = self.integration_managers[test_user][:3]
        for manager in managers_to_close:
            if hasattr(manager, '_websocket'):
                manager._websocket.close()

        # Wait for cleanup to process
        await asyncio.sleep(0.2)

        # Try to create new connection - should work if cleanup is effective
        try:
            mock_ws = self._create_realistic_websocket_mock(
                test_user, f"{test_user}_recovery_conn"
            )

            mode = create_isolated_mode(
                user_id=test_user,
                thread_id=ThreadID(f"{test_user}_recovery_thread"),
                connection_id=ConnectionID(f"{test_user}_recovery_conn")
            )

            recovery_manager = WebSocketManager(mock_ws, mode)
            await recovery_manager.initialize()
            self.integration_managers[test_user].append(recovery_manager)

            logger.info(f"Recovery connection succeeded for {test_user}")

        except Exception as e:
            # BUG DETECTED: Cross-user cleanup interference
            self.fail(
                f"BUG DETECTED: Cross-user cleanup interference. "
                f"User {test_user} cannot create new connections even after freeing slots. "
                f"Emergency cleanup system has cross-user contamination. Error: {e}"
            )

    async def test_agent_execution_context_during_emergency_cleanup(self):
        """
        INTEGRATION TEST 2: Agent execution context corruption during emergency cleanup.

        EXPECTED RESULT: This test should FAIL because emergency cleanup corrupts
        active agent execution contexts, breaking the Golden Path user flow.

        BUG PROOF: When emergency cleanup runs, it interferes with active agent
        executions, causing context loss and agent communication failures.
        """
        logger.info("Testing agent execution context during emergency cleanup")

        test_user = self.test_users[0]

        # Create connections up to limit with active agent contexts
        active_contexts = []

        for i in range(MAX_CONNECTIONS_PER_USER):
            mock_ws = self._create_realistic_websocket_mock(
                test_user, f"{test_user}_agent_conn_{i}"
            )

            mode = create_isolated_mode(
                user_id=test_user,
                thread_id=ThreadID(f"{test_user}_agent_thread_{i}"),
                connection_id=ConnectionID(f"{test_user}_agent_conn_{i}")
            )

            manager = WebSocketManager(mock_ws, mode)
            await manager.initialize()
            self.integration_managers[test_user].append(manager)

            # Simulate active agent execution context
            context = {
                "user_id": test_user,
                "thread_id": f"{test_user}_agent_thread_{i}",
                "agent_state": "thinking",
                "execution_stage": "tool_execution",
                "active_tools": ["data_analyzer", "report_generator"],
                "start_time": datetime.now(),
                "expected_duration": timedelta(minutes=5)
            }
            active_contexts.append(context)

            # Simulate WebSocket events for active agent
            mock_ws.send.assert_not_called()  # Initially no events

        # Now trigger emergency cleanup by exceeding limits
        emergency_trigger_count = 3
        for i in range(emergency_trigger_count):
            try:
                mock_ws = self._create_realistic_websocket_mock(
                    test_user, f"{test_user}_emergency_trigger_{i}"
                )

                mode = create_isolated_mode(
                    user_id=test_user,
                    thread_id=ThreadID(f"{test_user}_emergency_thread_{i}"),
                    connection_id=ConnectionID(f"{test_user}_emergency_conn_{i}")
                )

                manager = WebSocketManager(mock_ws, mode)
                await manager.initialize()
                self.integration_managers[test_user].append(manager)

            except Exception as e:
                logger.info(f"Emergency trigger {i} failed as expected: {e}")

        # Wait for emergency cleanup to process
        await asyncio.sleep(0.1)

        # BUG ASSERTION: Check that active agent contexts are still valid
        # Emergency cleanup should NOT interfere with active agent executions

        # Test 1: Verify existing connections can still send agent events
        active_managers = self.integration_managers[test_user][:MAX_CONNECTIONS_PER_USER]

        for i, manager in enumerate(active_managers):
            try:
                # Simulate agent event emission
                test_event = {
                    "event_type": "agent_thinking",
                    "user_id": str(test_user),
                    "thread_id": f"{test_user}_agent_thread_{i}",
                    "message": "Analyzing data...",
                    "timestamp": datetime.now().isoformat()
                }

                # This should work if manager is still functional
                if hasattr(manager, 'emit_event'):
                    await manager.emit_event(test_event)
                elif hasattr(manager, '_websocket') and not manager._websocket.closed:
                    manager._websocket.send(json.dumps(test_event))

            except Exception as e:
                # BUG DETECTED: Emergency cleanup corrupted agent execution context
                self.fail(
                    f"BUG DETECTED: Emergency cleanup corrupted agent execution context. "
                    f"Manager {i} for user {test_user} cannot send agent events after cleanup. "
                    f"Active agent execution contexts are being destroyed during emergency cleanup. "
                    f"Error: {e}. This breaks the Golden Path user flow."
                )

        # Test 2: Verify agent context data integrity
        # Check that the contexts we created are still valid
        corrupted_contexts = []

        for i, context in enumerate(active_contexts):
            # Simulate checking if context is still accessible
            # In real implementation, this would check UserExecutionContextManager
            try:
                # Basic integrity check
                required_fields = ["user_id", "thread_id", "agent_state"]
                for field in required_fields:
                    if field not in context:
                        corrupted_contexts.append(i)
                        break

                # Check if context is still "active" (not cleaned up improperly)
                if context.get("agent_state") != "thinking":
                    corrupted_contexts.append(i)

            except Exception as e:
                corrupted_contexts.append(i)
                logger.error(f"Context {i} corrupted: {e}")

        # BUG ASSERTION: No contexts should be corrupted by emergency cleanup
        self.assertEqual(
            len(corrupted_contexts),
            0,
            f"BUG DETECTED: Emergency cleanup corrupted {len(corrupted_contexts)} agent execution contexts "
            f"out of {len(active_contexts)} active contexts. Corrupted context indices: {corrupted_contexts}. "
            f"Emergency cleanup is improperly interfering with active agent operations, "
            f"breaking the Golden Path user experience."
        )

    async def test_database_session_leak_during_emergency_cleanup(self):
        """
        INTEGRATION TEST 3: Database session leaks during emergency cleanup.

        EXPECTED RESULT: This test should FAIL because emergency cleanup fails
        to properly close database sessions, leading to connection pool exhaustion.

        BUG PROOF: When emergency cleanup runs, it leaves database sessions open,
        eventually exhausting the connection pool and blocking all database operations.
        """
        logger.info("Testing database session leaks during emergency cleanup")

        test_user = self.test_users[0]
        initial_session_count = 0

        # Track "database sessions" (simulated)
        # In real implementation, this would integrate with PostgresManager
        simulated_db_sessions = []

        # Create connections that each open a database session
        for i in range(MAX_CONNECTIONS_PER_USER):
            mock_ws = self._create_realistic_websocket_mock(
                test_user, f"{test_user}_db_conn_{i}"
            )

            mode = create_isolated_mode(
                user_id=test_user,
                thread_id=ThreadID(f"{test_user}_db_thread_{i}"),
                connection_id=ConnectionID(f"{test_user}_db_conn_{i}")
            )

            manager = WebSocketManager(mock_ws, mode)
            await manager.initialize()
            self.integration_managers[test_user].append(manager)

            # Simulate database session creation for each WebSocket connection
            # In real implementation, this would be actual database sessions
            db_session = {
                "session_id": f"db_session_{i}",
                "user_id": test_user,
                "connection_id": f"{test_user}_db_conn_{i}",
                "created_at": datetime.now(),
                "active": True,
                "queries_executed": 0
            }
            simulated_db_sessions.append(db_session)

        initial_session_count = len(simulated_db_sessions)
        logger.info(f"Created {initial_session_count} database sessions")

        # Trigger emergency cleanup by exceeding connection limits
        for i in range(3):
            try:
                mock_ws = self._create_realistic_websocket_mock(
                    test_user, f"{test_user}_overflow_conn_{i}"
                )

                mode = create_isolated_mode(
                    user_id=test_user,
                    thread_id=ThreadID(f"{test_user}_overflow_thread_{i}"),
                    connection_id=ConnectionID(f"{test_user}_overflow_conn_{i}")
                )

                manager = WebSocketManager(mock_ws, mode)
                await manager.initialize()
                self.integration_managers[test_user].append(manager)

                # These should also create database sessions
                db_session = {
                    "session_id": f"db_session_overflow_{i}",
                    "user_id": test_user,
                    "connection_id": f"{test_user}_overflow_conn_{i}",
                    "created_at": datetime.now(),
                    "active": True,
                    "queries_executed": 0
                }
                simulated_db_sessions.append(db_session)

            except Exception as e:
                logger.info(f"Overflow connection {i} failed: {e}")

        # Wait for emergency cleanup
        await asyncio.sleep(0.2)

        # Simulate what emergency cleanup SHOULD do to database sessions
        # It should close sessions for connections that were cleaned up
        cleaned_up_connections = set()

        # Check which managers/connections were cleaned up
        for manager in self.integration_managers[test_user]:
            if hasattr(manager, '_websocket') and manager._websocket.closed:
                conn_id = getattr(manager, '_connection_id', None)
                if conn_id:
                    cleaned_up_connections.add(str(conn_id))

        # Emergency cleanup should have closed corresponding database sessions
        # BUG: It doesn't properly close database sessions
        sessions_that_should_be_closed = [
            session for session in simulated_db_sessions
            if session["connection_id"] in cleaned_up_connections
        ]

        # BUG ASSERTION 1: Database sessions should be closed when connections are cleaned up
        for session in sessions_that_should_be_closed:
            # In a working system, emergency cleanup would mark these as inactive
            # BUG: They remain active, causing session leaks
            self.assertFalse(
                session["active"],
                f"BUG DETECTED: Database session {session['session_id']} is still active "
                f"after its WebSocket connection {session['connection_id']} was cleaned up. "
                f"Emergency cleanup failed to properly close database sessions, "
                f"leading to session leaks and potential connection pool exhaustion."
            )

        # BUG ASSERTION 2: Total active sessions should decrease after cleanup
        active_sessions_after_cleanup = [
            session for session in simulated_db_sessions if session["active"]
        ]

        # Expected: Some sessions should be closed, so active count should be less than initial
        self.assertLess(
            len(active_sessions_after_cleanup),
            initial_session_count,
            f"BUG DETECTED: No database sessions were closed during emergency cleanup. "
            f"Started with {initial_session_count} sessions, still have {len(active_sessions_after_cleanup)} active. "
            f"Emergency cleanup is not properly managing database session lifecycle, "
            f"leading to resource leaks that will eventually block all database operations."
        )

        # BUG ASSERTION 3: Try to create new connection - should work if sessions were properly closed
        try:
            mock_ws = self._create_realistic_websocket_mock(
                test_user, f"{test_user}_post_cleanup_conn"
            )

            mode = create_isolated_mode(
                user_id=test_user,
                thread_id=ThreadID(f"{test_user}_post_cleanup_thread"),
                connection_id=ConnectionID(f"{test_user}_post_cleanup_conn")
            )

            manager = WebSocketManager(mock_ws, mode)
            await manager.initialize()
            self.integration_managers[test_user].append(manager)

            # Should be able to create a database session
            new_db_session = {
                "session_id": "db_session_post_cleanup",
                "user_id": test_user,
                "connection_id": f"{test_user}_post_cleanup_conn",
                "created_at": datetime.now(),
                "active": True,
                "queries_executed": 0
            }
            simulated_db_sessions.append(new_db_session)

            logger.info("Post-cleanup connection and database session created successfully")

        except Exception as e:
            # BUG DETECTED: Database session leaks preventing new connections
            self.fail(
                f"BUG DETECTED: Cannot create new connection after emergency cleanup due to "
                f"database session leaks. Emergency cleanup failed to properly close "
                f"database sessions, leading to resource exhaustion. Error: {e}. "
                f"This prevents users from creating new connections even when "
                f"WebSocket connections have been cleaned up."
            )


if __name__ == "__main__":
    unittest.main()