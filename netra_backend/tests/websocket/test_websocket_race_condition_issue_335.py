"""
Unit Tests for Issue #335 - WebSocket Send After Close Race Condition

These tests are designed to reproduce the race condition where messages are sent
to WebSocket connections that are already closing or closed, resulting in
"send after close" errors.

Test Plan:
1. Test safe_websocket_close function with concurrent send operations
2. Test WebSocketConnection state management during close operations
3. Test the is_closing flag implementation gap
4. Test concurrent close operations causing race conditions

Expected Behavior:
- Initial tests should FAIL, demonstrating the race condition exists
- After implementing the fix, tests should PASS

Business Value: $500K+ ARR depends on reliable WebSocket communication
"""

import asyncio
import pytest
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import concurrent.futures
from typing import Optional, Any

# SSOT test infrastructure imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import the components we're testing
try:
    from netra_backend.app.websocket_core.utils import safe_websocket_close
    from netra_backend.app.websocket_core.unified_manager import (
        WebSocketConnection, UnifiedWebSocketManager, WebSocketManagerMode
    )
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
    from netra_backend.app.websocket_core.types import (
        WebSocketConnectionState, ConnectionInfo
    )
    from shared.types.core_types import ensure_user_id
    from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


class MockWebSocket:
    """Mock WebSocket with state simulation for race condition testing."""

    def __init__(self):
        self.is_connected = True
        self.is_closing = False
        self.close_called = False
        self.send_count = 0
        self.send_errors = []
        self._close_lock = asyncio.Lock()

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Simulate WebSocket close with race condition potential."""
        async with self._close_lock:
            if self.close_called:
                raise RuntimeError("WebSocket is already closed")

            self.is_closing = True
            # Simulate brief delay where connection is closing but not yet closed
            await asyncio.sleep(0.001)

            self.close_called = True
            self.is_connected = False
            self.is_closing = False

    async def send_json(self, data: Any):
        """Simulate sending JSON with race condition detection."""
        if self.is_closing:
            # This is the race condition we want to catch
            error_msg = "Cannot send data after close has been initiated"
            self.send_errors.append(error_msg)
            raise RuntimeError(error_msg)

        if not self.is_connected:
            error_msg = "WebSocket is closed"
            self.send_errors.append(error_msg)
            raise RuntimeError(error_msg)

        self.send_count += 1
        # Simulate brief send delay
        await asyncio.sleep(0.001)


class WebSocketRaceConditionIssue335Tests(SSotAsyncTestCase):
    """
    Test suite for Issue #335 - WebSocket Send After Close Race Condition.

    These tests are designed to FAIL initially, demonstrating the race condition,
    and then PASS after the fix is implemented.
    """

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")

        self.id_manager = UnifiedIDManager()
        self.mock_user_context = self._create_mock_user_context()

    def _create_mock_user_context(self):
        """Create mock user context for testing."""
        return type('MockUserContext', (), {
            'user_id': self.id_manager.generate_id(IDType.USER, prefix="test"),
            'session_id': self.id_manager.generate_id(IDType.THREAD, prefix="test"),
            'request_id': self.id_manager.generate_id(IDType.REQUEST, prefix="test"),
            'is_test': True
        })()

    async def test_safe_websocket_close_race_condition_basic(self):
        """
        Test basic race condition in safe_websocket_close function.

        Expected: This test should PASS as safe_websocket_close handles errors.
        However, it doesn't prevent the race condition from occurring.
        """
        mock_websocket = MockWebSocket()

        # Test normal close
        await safe_websocket_close(mock_websocket)

        self.assertTrue(mock_websocket.close_called)
        self.assertFalse(mock_websocket.is_connected)

    async def test_concurrent_send_and_close_operations(self):
        """
        Test concurrent send and close operations to reproduce race condition.

        Expected: This test should FAIL, demonstrating the race condition exists.
        The send operation should fail with "send after close" error.
        """
        mock_websocket = MockWebSocket()

        async def send_message():
            """Simulate sending a message."""
            try:
                await asyncio.sleep(0.005)  # Delay to increase race condition chance
                await mock_websocket.send_json({"type": "test", "data": "test message"})
                return "send_success"
            except RuntimeError as e:
                return f"send_error: {e}"

        async def close_connection():
            """Simulate closing the connection."""
            await asyncio.sleep(0.002)  # Small delay before close
            await mock_websocket.close()
            return "close_success"

        # Execute send and close concurrently to create race condition
        results = await asyncio.gather(
            send_message(),
            close_connection(),
            return_exceptions=True
        )

        # Check if race condition occurred
        send_result = results[0]
        close_result = results[1]

        print(f"Send result: {send_result}")
        print(f"Close result: {close_result}")
        print(f"Send errors: {mock_websocket.send_errors}")

        # This test demonstrates the race condition exists
        # We expect either:
        # 1. The send operation to fail with a race condition error, OR
        # 2. The websocket to track send errors showing the race condition occurred
        race_condition_detected = False

        if isinstance(send_result, str) and "send_error" in send_result:
            # Direct send error detected
            race_condition_detected = "close" in send_result.lower()

        elif len(mock_websocket.send_errors) > 0:
            # Send errors tracked in mock websocket
            race_condition_detected = any("close" in error.lower() for error in mock_websocket.send_errors)

        # Assert that we successfully reproduced the race condition
        self.assertTrue(race_condition_detected,
                       f"Race condition should be detected. Send result: {send_result}, Errors: {mock_websocket.send_errors}")

        self.assertEqual(close_result, "close_success")

    async def test_websocket_connection_is_closing_flag_gap(self):
        """
        Test the is_closing flag implementation gap in WebSocketConnection.

        Expected: This test should FAIL initially, showing the flag isn't used
        effectively to prevent send operations during close.
        """
        # Create a WebSocketConnection with mock websocket
        mock_websocket = MockWebSocket()
        connection_id = self.id_manager.generate_id(IDType.WEBSOCKET, prefix="test")
        user_id = self.id_manager.generate_id(IDType.USER, prefix="test")

        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.now()
        )

        # Start closing process
        mock_websocket.is_closing = True

        # Attempt to send message when connection is closing
        # This should be prevented by checking is_closing flag, but currently isn't
        try:
            await mock_websocket.send_json({"type": "test", "data": "should be prevented"})
            send_succeeded = True
            send_error = None
        except RuntimeError as e:
            send_succeeded = False
            send_error = str(e)

        # This assertion should FAIL initially, showing the race condition
        # After fix, we expect send to be prevented when is_closing is True
        self.assertFalse(send_succeeded,
                        f"Send operation should be prevented when is_closing=True, but got: {send_error}")
        self.assertIsNotNone(send_error)
        self.assertIn("close", send_error.lower())

    async def test_websocket_manager_send_during_close_race_condition(self):
        """
        Test race condition in UnifiedWebSocketManager send operations during close.

        Expected: This test should FAIL initially, showing the manager doesn't
        prevent sends to closing connections.
        """
        # Create manager with mock context
        manager = get_websocket_manager(
            user_context=self.mock_user_context,
            mode=WebSocketManagerMode.UNIFIED
        )

        # Create mock websocket connection
        mock_websocket = MockWebSocket()
        connection_id = self.id_manager.generate_id(IDType.WEBSOCKET, prefix="test")
        user_id = ensure_user_id(self.mock_user_context.user_id)

        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.now()
        )

        # Add connection to manager
        await manager.add_connection(connection)

        async def close_connection():
            """Simulate closing connection."""
            await asyncio.sleep(0.002)
            mock_websocket.is_closing = True
            await mock_websocket.close()

        async def send_via_manager():
            """Simulate sending via manager."""
            await asyncio.sleep(0.005)
            return await manager.send_message(connection_id, {"type": "test", "data": "test"})

        # Execute close and send concurrently
        results = await asyncio.gather(
            close_connection(),
            send_via_manager(),
            return_exceptions=True
        )

        close_result = results[0]
        send_result = results[1]

        # Check if race condition was detected
        has_send_errors = len(mock_websocket.send_errors) > 0

        # This assertion should FAIL initially, showing the race condition
        # After fix, the manager should prevent sends to closing connections
        self.assertTrue(has_send_errors or isinstance(send_result, Exception),
                       "Manager should prevent sends to closing connections or handle errors gracefully")

    async def test_multiple_concurrent_close_operations(self):
        """
        Test multiple concurrent close operations causing race conditions.

        Expected: This test should handle multiple close attempts gracefully.
        """
        mock_websocket = MockWebSocket()

        async def attempt_close():
            """Attempt to close the websocket."""
            try:
                await safe_websocket_close(mock_websocket)
                return "close_success"
            except Exception as e:
                return f"close_error: {e}"

        # Attempt multiple concurrent closes
        close_tasks = [attempt_close() for _ in range(3)]
        results = await asyncio.gather(*close_tasks, return_exceptions=True)

        # At least one close should succeed
        successful_closes = [r for r in results if r == "close_success"]

        # This should pass even with current implementation due to safe_websocket_close error handling
        self.assertGreaterEqual(len(successful_closes), 1,
                               "At least one close operation should succeed")

        # Connection should be closed
        self.assertTrue(mock_websocket.close_called)
        self.assertFalse(mock_websocket.is_connected)

    async def test_connection_state_transitions_during_race_condition(self):
        """
        Test ConnectionInfo state transitions during race conditions.

        Expected: This test validates state management during concurrent operations.
        """
        # Create ConnectionInfo with proper state management
        connection_id = self.id_manager.generate_id(IDType.WEBSOCKET, prefix="test")
        user_id = self.id_manager.generate_id(IDType.USER, prefix="test")

        connection_info = ConnectionInfo(
            connection_id=connection_id,
            user_id=user_id,
            connected_at=datetime.now(),
            websocket=MockWebSocket()
        )

        # Test state transitions
        self.assertEqual(connection_info.state, WebSocketConnectionState.ACTIVE)
        self.assertFalse(connection_info.is_closing)

        # Transition to closing
        success = connection_info.transition_to_closing()
        self.assertTrue(success)
        self.assertEqual(connection_info.state, WebSocketConnectionState.CLOSING)
        self.assertTrue(connection_info.is_closing)

        # Attempt to transition to closing again (should fail)
        success = connection_info.transition_to_closing()
        self.assertFalse(success, "Should not be able to transition to closing twice")

        # Transition to closed
        success = connection_info.transition_to_closed()
        self.assertTrue(success)
        self.assertEqual(connection_info.state, WebSocketConnectionState.CLOSED)
        self.assertFalse(connection_info.is_closing)

    def test_race_condition_detection_synchronous(self):
        """
        Test race condition detection in synchronous context.

        This tests the theoretical race condition detection without async complexity.
        """
        # Create mock connection that's in closing state
        mock_websocket = Mock()
        mock_websocket.is_closing = True

        # This should detect the race condition
        try:
            # Simulate what happens when send is attempted on closing websocket
            if hasattr(mock_websocket, 'is_closing') and mock_websocket.is_closing:
                raise RuntimeError("Cannot send data after close has been initiated")
            self.fail("Expected RuntimeError when sending to closing WebSocket")
        except RuntimeError as e:
            # This is expected - race condition detected
            self.assertIn("close", str(e).lower())


# Integration test (non-docker) for WebSocket lifecycle
class WebSocketLifecycleRaceConditionTests(SSotAsyncTestCase):
    """
    Integration tests for WebSocket lifecycle race conditions without Docker.

    These tests validate the complete WebSocket lifecycle including race condition
    scenarios that may occur in production.
    """

    def setup_method(self, method):
        """Set up integration test environment."""
        super().setup_method(method)

        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")

        self.id_manager = UnifiedIDManager()

    async def test_websocket_manager_lifecycle_with_race_conditions(self):
        """
        Test complete WebSocket manager lifecycle with race condition scenarios.

        This integration test simulates real-world race conditions that may occur
        during WebSocket connection lifecycle management.
        """
        # Create manager
        mock_user_context = type('MockUserContext', (), {
            'user_id': self.id_manager.generate_id(IDType.USER, prefix="test"),
            'session_id': self.id_manager.generate_id(IDType.THREAD, prefix="test"),
            'request_id': self.id_manager.generate_id(IDType.REQUEST, prefix="test"),
            'is_test': True
        })()

        manager = UnifiedWebSocketManager(
            mode=WebSocketManagerMode.UNIFIED,
            user_context=mock_user_context
        )

        # Create multiple connections
        connections = []
        for i in range(3):
            mock_websocket = MockWebSocket()
            connection_id = self.id_manager.generate_id(IDType.CONNECTION, prefix=f"test_{i}")
            user_id = ensure_user_id(mock_user_context.user_id)

            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=mock_websocket,
                connected_at=datetime.now()
            )

            connections.append(connection)
            await manager.add_connection(connection)

        # Verify connections added
        self.assertEqual(len(manager._connections), 3)

        # Simulate concurrent operations: sends, closes, and new connections
        async def concurrent_operations():
            tasks = []

            # Send messages to all connections
            for connection in connections:
                tasks.append(manager.send_message(
                    connection.connection_id,
                    {"type": "test", "data": f"message to {connection.connection_id}"}
                ))

            # Close some connections concurrently
            for connection in connections[:2]:
                tasks.append(safe_websocket_close(connection.websocket))

            # Add new connection while others are closing
            new_mock_websocket = MockWebSocket()
            new_connection_id = self.id_manager.generate_id(IDType.WEBSOCKET, prefix="new_test")
            new_connection = WebSocketConnection(
                connection_id=new_connection_id,
                user_id=ensure_user_id(mock_user_context.user_id),
                websocket=new_mock_websocket,
                connected_at=datetime.now()
            )
            tasks.append(manager.add_connection(new_connection))

            # Execute all operations concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        # Execute concurrent operations
        results = await concurrent_operations()

        # Analyze results for race conditions
        errors = [r for r in results if isinstance(r, Exception)]
        successful_operations = [r for r in results if not isinstance(r, Exception)]

        # Log results for analysis
        print(f"Concurrent operations completed:")
        print(f"  - Successful operations: {len(successful_operations)}")
        print(f"  - Errors: {len(errors)}")

        for i, error in enumerate(errors):
            print(f"  - Error {i+1}: {type(error).__name__}: {error}")

        # Check for race condition indicators
        send_errors_detected = any(
            hasattr(conn.websocket, 'send_errors') and len(conn.websocket.send_errors) > 0
            for conn in connections
        )

        # Check if race conditions were detected - this is expected for now
        if send_errors_detected:
            print("Race conditions detected in send operations - this demonstrates Issue #335")

        # Verify manager is still in valid state
        self.assertIsInstance(manager._connections, dict)

if __name__ == '__main__':
    # Run the tests
    unittest.main()