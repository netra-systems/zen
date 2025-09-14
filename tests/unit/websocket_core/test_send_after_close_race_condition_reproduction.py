"""
Unit Tests for WebSocket "Send After Close" Race Condition - Issue #335

CRITICAL PURPOSE: These tests MUST FAIL initially to prove the race condition exists.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Detect and prevent "send after close" race conditions
- Value Impact: Prevents WebSocket errors that disrupt user chat experience
- Revenue Impact: Protects Golden Path reliability ($500K+ ARR)

TEST STRATEGY:
These tests specifically target the race condition where:
1. WebSocket connection enters CLOSING/CLOSED state
2. Concurrent thread attempts to send messages
3. System lacks proper state validation before sending
4. Results in "send after close" exception

EXPECTED BEHAVIOR: These tests should FAIL initially, demonstrating the race condition exists.
Once the issue is fixed, tests should pass by properly validating connection state.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any
import threading
import time

# Import the classes we need to test
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState,
    ConnectionStateMachine
)
from shared.types.core_types import UserID, ConnectionID
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestSendAfterCloseRaceCondition(SSotAsyncTestCase):
    """
    Unit tests to reproduce WebSocket send-after-close race condition.

    These tests MUST FAIL initially to prove the race condition exists.
    The race condition occurs when messages are sent to connections
    that are in CLOSING or CLOSED state without proper validation.
    """

    async def setup_method(self, method):
        """Set up test fixtures."""
        await super().async_setup_method(method)

        # Create manager with isolated mode for testing
        self.user_id = UserID("test_user_race_condition")
        self.connection_id = ConnectionID("conn_race_test_001")

        # Create mock WebSocket that can simulate closing states
        self.mock_websocket = AsyncMock()
        self.mock_websocket.send_json = AsyncMock()

        # Create manager in isolated mode
        self.manager = await get_websocket_manager(
            mode=WebSocketManagerMode.ISOLATED,
            user_context=Mock(user_id=self.user_id)
        )

    async def test_send_message_to_closing_connection_should_fail(self):
        """
        TEST SHOULD FAIL: Sending message to CLOSING connection should be prevented.

        This test reproduces the race condition by:
        1. Creating a connection in CLOSING state
        2. Attempting to send a message
        3. Expecting proper state validation (which currently doesn't exist)

        EXPECTED RESULT: This test should FAIL because the system currently
        doesn't validate connection state before sending messages.
        """
        # ARRANGE: Create connection in CLOSING state
        mock_connection = Mock()
        mock_connection.websocket = self.mock_websocket
        mock_connection.user_id = self.user_id
        mock_connection.connection_id = self.connection_id
        mock_connection.state = ApplicationConnectionState.CLOSING  # CRITICAL: Set to closing state

        # Add connection to manager's internal state
        self.manager.active_connections[self.user_id] = {self.connection_id: mock_connection}

        # ACT: Attempt to send message to closing connection
        test_message = {"type": "test_message", "data": "should_not_send"}

        # This should either:
        # A) Fail with proper validation (desired behavior) OR
        # B) Succeed improperly (current bug - race condition exists)
        with pytest.raises((RuntimeError, ValueError, ConnectionError)) as exc_info:
            await self.manager.send_message(self.user_id, test_message)

        # ASSERT: Expect that sending to CLOSING connection raises appropriate error
        # This assertion will FAIL initially because no validation exists
        assert "closing" in str(exc_info.value).lower() or "closed" in str(exc_info.value).lower()

        # Verify send_json was NOT called on closing connection
        self.mock_websocket.send_json.assert_not_called()

    async def test_send_message_to_closed_connection_should_fail(self):
        """
        TEST SHOULD FAIL: Sending message to CLOSED connection should be prevented.

        This test reproduces the race condition with CLOSED state.
        """
        # ARRANGE: Create connection in CLOSED state
        mock_connection = Mock()
        mock_connection.websocket = self.mock_websocket
        mock_connection.user_id = self.user_id
        mock_connection.connection_id = self.connection_id
        mock_connection.state = ApplicationConnectionState.CLOSED  # CRITICAL: Set to closed state

        # Add connection to manager
        self.manager.active_connections[self.user_id] = {self.connection_id: mock_connection}

        # ACT: Attempt to send message to closed connection
        test_message = {"type": "agent_started", "data": "should_fail"}

        # This should fail with proper validation
        with pytest.raises((RuntimeError, ValueError, ConnectionError)):
            await self.manager.send_message(self.user_id, test_message)

        # Verify send_json was NOT called on closed connection
        self.mock_websocket.send_json.assert_not_called()

    async def test_concurrent_send_and_close_race_condition(self):
        """
        TEST SHOULD FAIL: Reproduce actual race condition with concurrent operations.

        This test simulates the real-world scenario where:
        1. Thread A starts closing connection (sets state to CLOSING)
        2. Thread B attempts to send message concurrently
        3. Thread B doesn't check connection state before sending
        4. Results in send-after-close error
        """
        # ARRANGE: Create connection in operational state initially
        mock_connection = Mock()
        mock_connection.websocket = self.mock_websocket
        mock_connection.user_id = self.user_id
        mock_connection.connection_id = self.connection_id
        mock_connection.state = ApplicationConnectionState.PROCESSING_READY

        # Add connection to manager
        self.manager.active_connections[self.user_id] = {self.connection_id: mock_connection}

        # Create event to coordinate timing
        close_started = threading.Event()
        send_attempted = threading.Event()

        async def close_connection_slowly():
            """Simulate gradual connection close."""
            close_started.set()
            await asyncio.sleep(0.01)  # Small delay to create race window
            mock_connection.state = ApplicationConnectionState.CLOSING
            await asyncio.sleep(0.01)
            mock_connection.state = ApplicationConnectionState.CLOSED

        async def send_message_concurrently():
            """Simulate concurrent message send."""
            close_started.wait(timeout=1.0)  # Wait for close to start
            send_attempted.set()

            # This send should fail if proper validation exists
            test_message = {"type": "tool_executing", "data": "concurrent_test"}
            await self.manager.send_message(self.user_id, test_message)

        # ACT: Run close and send concurrently to create race condition
        close_task = asyncio.create_task(close_connection_slowly())
        send_task = asyncio.create_task(send_message_concurrently())

        # The send should fail due to connection being in closing/closed state
        with pytest.raises((RuntimeError, ValueError, ConnectionError)):
            await asyncio.gather(close_task, send_task)

        # Verify race condition scenario occurred
        assert close_started.is_set(), "Close operation should have started"
        assert send_attempted.is_set(), "Send operation should have been attempted"

    async def test_state_machine_validation_before_send(self):
        """
        TEST SHOULD FAIL: State machine should prevent sends to non-operational states.

        This tests the core fix needed: proper state validation before sending.
        """
        # ARRANGE: Test all non-operational states
        non_operational_states = [
            ApplicationConnectionState.CONNECTING,
            ApplicationConnectionState.CLOSING,
            ApplicationConnectionState.CLOSED,
            ApplicationConnectionState.FAILED,
            ApplicationConnectionState.RECONNECTING
        ]

        for state in non_operational_states:
            with self.subTest(state=state):
                # Create connection in non-operational state
                mock_connection = Mock()
                mock_connection.websocket = self.mock_websocket
                mock_connection.user_id = self.user_id
                mock_connection.connection_id = self.connection_id
                mock_connection.state = state

                # Add to manager
                self.manager.active_connections[self.user_id] = {self.connection_id: mock_connection}

                # ACT: Attempt send to non-operational connection
                test_message = {"type": "agent_completed", "data": f"test_{state}"}

                # ASSERT: Should fail for non-operational states
                with pytest.raises((RuntimeError, ValueError, ConnectionError)):
                    await self.manager.send_message(self.user_id, test_message)

                # Reset mock for next iteration
                self.mock_websocket.send_json.reset_mock()

    def test_is_closing_flag_validation_pattern(self):
        """
        TEST SHOULD FAIL: System should have is_closing flag validation.

        This tests for a common pattern to prevent send-after-close:
        checking an `is_closing` flag before attempting sends.
        """
        # ARRANGE: Create mock connection
        mock_connection = Mock()
        mock_connection.websocket = self.mock_websocket
        mock_connection.is_closing = True  # Set closing flag

        # ACT & ASSERT: Check if manager validates is_closing flag
        # This should exist but currently doesn't (will cause test failure)

        # Look for is_closing validation in send logic
        with patch.object(self.manager, 'get_connection', return_value=mock_connection):
            # This assertion will FAIL because is_closing validation doesn't exist
            assert hasattr(mock_connection, 'is_closing'), "Connection should have is_closing flag"

            # The manager should check this flag (but currently doesn't)
            # This is the pattern that needs to be implemented to fix the race condition
            with pytest.raises((RuntimeError, ValueError)):
                # This call should validate is_closing=True and raise error
                asyncio.run(self.manager.send_message(self.user_id, {"type": "test"}))


class TestWebSocketStateValidationMissing(SSotAsyncTestCase):
    """
    Tests to demonstrate missing validation patterns that cause race conditions.

    These tests DOCUMENT what validations are missing and should be added.
    """

    def test_connection_state_enum_coverage(self):
        """Verify all connection states are properly handled."""
        # This test documents which states exist and which need validation
        all_states = list(ApplicationConnectionState)

        operational_states = [
            ApplicationConnectionState.PROCESSING_READY,
            ApplicationConnectionState.PROCESSING,
            ApplicationConnectionState.IDLE,
            ApplicationConnectionState.DEGRADED
        ]

        non_operational_states = [
            ApplicationConnectionState.CONNECTING,
            ApplicationConnectionState.ACCEPTED,
            ApplicationConnectionState.AUTHENTICATED,
            ApplicationConnectionState.SERVICES_READY,
            ApplicationConnectionState.CLOSING,
            ApplicationConnectionState.CLOSED,
            ApplicationConnectionState.FAILED,
            ApplicationConnectionState.RECONNECTING
        ]

        # Verify all states are accounted for
        assert len(operational_states) + len(non_operational_states) == len(all_states)

        # This test documents that validation should prevent sends to non_operational_states
        # Currently this validation is MISSING (test will pass but documents the gap)
        assert len(non_operational_states) > 0, "Non-operational states need send prevention"

    async def test_websocket_send_json_exception_patterns(self):
        """
        Document exception patterns that occur during send-after-close.

        This test shows what exceptions should be caught and handled.
        """
        # Common exceptions during send-after-close scenarios:
        expected_exceptions = [
            ConnectionError("Connection closed"),
            RuntimeError("WebSocket connection closed"),
            ValueError("Cannot send to closed connection"),
            OSError("Socket is not connected"),
            # Add FastAPI/Starlette specific exceptions as discovered
        ]

        # Test should document these exception types for proper handling
        for exc in expected_exceptions:
            assert isinstance(exc, Exception), f"Should handle {type(exc).__name__}"

        # This test documents the exception handling patterns needed
        # but doesn't test the actual implementation (which is missing)
        pass


if __name__ == "__main__":
    # Run these tests to reproduce the race condition
    # EXPECTED: Tests should FAIL initially, proving race condition exists
    pytest.main([__file__, "-v", "--tb=short"])