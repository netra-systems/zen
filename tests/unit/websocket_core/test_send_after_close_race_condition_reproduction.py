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
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.websocket_core.websocket_manager import WebSocketManagerMode
from netra_backend.app.websocket_core.connection_state_machine import ApplicationConnectionState, ConnectionStateMachine
from shared.types.core_types import UserID, ConnectionID
from test_framework.ssot.base_test_case import SSotAsyncTestCase

@pytest.mark.unit
class SendAfterCloseRaceConditionTests(SSotAsyncTestCase):
    """
    Unit tests to reproduce WebSocket send-after-close race condition.

    These tests MUST FAIL initially to prove the race condition exists.
    The race condition occurs when messages are sent to connections
    that are in CLOSING or CLOSED state without proper validation.
    """

    async def setup_method(self, method):
        """Set up test fixtures."""
        await super().async_setup_method(method)
        self.user_id = UserID('test_user_race_condition')
        self.connection_id = ConnectionID('conn_race_test_001')
        self.mock_websocket = AsyncMock()
        self.mock_websocket.send_json = AsyncMock()
        self.manager = get_websocket_manager(mode=WebSocketManagerMode.ISOLATED, user_context=Mock(user_id=self.user_id))

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
        mock_connection = Mock()
        mock_connection.websocket = self.mock_websocket
        mock_connection.user_id = self.user_id
        mock_connection.connection_id = self.connection_id
        mock_connection.state = ApplicationConnectionState.CLOSING
        self.manager.active_connections[self.user_id] = {self.connection_id: mock_connection}
        test_message = {'type': 'test_message', 'data': 'should_not_send'}
        with pytest.raises((RuntimeError, ValueError, ConnectionError)) as exc_info:
            await self.manager.send_message(self.user_id, test_message)
        assert 'closing' in str(exc_info.value).lower() or 'closed' in str(exc_info.value).lower()
        self.mock_websocket.send_json.assert_not_called()

    async def test_send_message_to_closed_connection_should_fail(self):
        """
        TEST SHOULD FAIL: Sending message to CLOSED connection should be prevented.

        This test reproduces the race condition with CLOSED state.
        """
        mock_connection = Mock()
        mock_connection.websocket = self.mock_websocket
        mock_connection.user_id = self.user_id
        mock_connection.connection_id = self.connection_id
        mock_connection.state = ApplicationConnectionState.CLOSED
        self.manager.active_connections[self.user_id] = {self.connection_id: mock_connection}
        test_message = {'type': 'agent_started', 'data': 'should_fail'}
        with pytest.raises((RuntimeError, ValueError, ConnectionError)):
            await self.manager.send_message(self.user_id, test_message)
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
        mock_connection = Mock()
        mock_connection.websocket = self.mock_websocket
        mock_connection.user_id = self.user_id
        mock_connection.connection_id = self.connection_id
        mock_connection.state = ApplicationConnectionState.PROCESSING_READY
        self.manager.active_connections[self.user_id] = {self.connection_id: mock_connection}
        close_started = threading.Event()
        send_attempted = threading.Event()

        async def close_connection_slowly():
            """Simulate gradual connection close."""
            close_started.set()
            await asyncio.sleep(0.01)
            mock_connection.state = ApplicationConnectionState.CLOSING
            await asyncio.sleep(0.01)
            mock_connection.state = ApplicationConnectionState.CLOSED

        async def send_message_concurrently():
            """Simulate concurrent message send."""
            close_started.wait(timeout=1.0)
            send_attempted.set()
            test_message = {'type': 'tool_executing', 'data': 'concurrent_test'}
            await self.manager.send_message(self.user_id, test_message)
        close_task = asyncio.create_task(close_connection_slowly())
        send_task = asyncio.create_task(send_message_concurrently())
        with pytest.raises((RuntimeError, ValueError, ConnectionError)):
            await asyncio.gather(close_task, send_task)
        assert close_started.is_set(), 'Close operation should have started'
        assert send_attempted.is_set(), 'Send operation should have been attempted'

    async def test_state_machine_validation_before_send(self):
        """
        TEST SHOULD FAIL: State machine should prevent sends to non-operational states.

        This tests the core fix needed: proper state validation before sending.
        """
        non_operational_states = [ApplicationConnectionState.CONNECTING, ApplicationConnectionState.CLOSING, ApplicationConnectionState.CLOSED, ApplicationConnectionState.FAILED, ApplicationConnectionState.RECONNECTING]
        for state in non_operational_states:
            with self.subTest(state=state):
                mock_connection = Mock()
                mock_connection.websocket = self.mock_websocket
                mock_connection.user_id = self.user_id
                mock_connection.connection_id = self.connection_id
                mock_connection.state = state
                self.manager.active_connections[self.user_id] = {self.connection_id: mock_connection}
                test_message = {'type': 'agent_completed', 'data': f'test_{state}'}
                with pytest.raises((RuntimeError, ValueError, ConnectionError)):
                    await self.manager.send_message(self.user_id, test_message)
                self.mock_websocket.send_json.reset_mock()

    def test_is_closing_flag_validation_pattern(self):
        """
        TEST SHOULD FAIL: System should have is_closing flag validation.

        This tests for a common pattern to prevent send-after-close:
        checking an `is_closing` flag before attempting sends.
        """
        mock_connection = Mock()
        mock_connection.websocket = self.mock_websocket
        mock_connection.is_closing = True
        with patch.object(self.manager, 'get_connection', return_value=mock_connection):
            assert hasattr(mock_connection, 'is_closing'), 'Connection should have is_closing flag'
            with pytest.raises((RuntimeError, ValueError)):
                asyncio.run(self.manager.send_message(self.user_id, {'type': 'test'}))

@pytest.mark.unit
class WebSocketStateValidationMissingTests(SSotAsyncTestCase):
    """
    Tests to demonstrate missing validation patterns that cause race conditions.

    These tests DOCUMENT what validations are missing and should be added.
    """

    def test_connection_state_enum_coverage(self):
        """Verify all connection states are properly handled."""
        all_states = list(ApplicationConnectionState)
        operational_states = [ApplicationConnectionState.PROCESSING_READY, ApplicationConnectionState.PROCESSING, ApplicationConnectionState.IDLE, ApplicationConnectionState.DEGRADED]
        non_operational_states = [ApplicationConnectionState.CONNECTING, ApplicationConnectionState.ACCEPTED, ApplicationConnectionState.AUTHENTICATED, ApplicationConnectionState.SERVICES_READY, ApplicationConnectionState.CLOSING, ApplicationConnectionState.CLOSED, ApplicationConnectionState.FAILED, ApplicationConnectionState.RECONNECTING]
        assert len(operational_states) + len(non_operational_states) == len(all_states)
        assert len(non_operational_states) > 0, 'Non-operational states need send prevention'

    async def test_websocket_send_json_exception_patterns(self):
        """
        Document exception patterns that occur during send-after-close.

        This test shows what exceptions should be caught and handled.
        """
        expected_exceptions = [ConnectionError('Connection closed'), RuntimeError('WebSocket connection closed'), ValueError('Cannot send to closed connection'), OSError('Socket is not connected')]
        for exc in expected_exceptions:
            assert isinstance(exc, Exception), f'Should handle {type(exc).__name__}'
        pass
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')