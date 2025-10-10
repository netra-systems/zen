"""
Test for the timing fix that ensures CLI waits for server handshake
before sending messages.

This test verifies that:
1. CLI waits for handshake_response before marking connection as ready
2. CLI retries handshake with delay if server isn't ready
3. CLI properly fails connection if server doesn't complete handshake
4. No messages are sent before server reaches PROCESSING phase
"""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.agent_cli import WebSocketClient
from shared import Environment, EnvironmentConfig


class TestTimingFix(unittest.TestCase):
    """Test suite for CLI timing fix"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = MagicMock()
        self.config.ws_url = "ws://localhost:8000/ws"
        self.config.environment = Environment.LOCAL
        self.config.json_mode = False
        self.config.ci_mode = False
        self.token = "test_token"
        self.debug = MagicMock()

    @patch('scripts.agent_cli.websockets.connect')
    async def test_successful_handshake_on_first_try(self, mock_connect):
        """Test successful handshake on first attempt"""
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # Mock handshake response
        handshake_response = {
            "type": "handshake_response",
            "thread_id": "test-thread-123",
            "user_id": "user-456",
            "session_id": "session-789"
        }
        mock_ws.recv.return_value = json.dumps(handshake_response)

        # Create client and connect
        client = WebSocketClient(
            self.config, self.token, self.debug,
            send_logs=False, logs_count=10,
            logs_project=None, logs_path=None,
            logs_user=None, handshake_timeout=5
        )

        result = await client.connect()

        # Assertions
        self.assertTrue(result)
        self.assertTrue(client.connected)
        self.assertEqual(client.current_thread_id, "test-thread-123")
        mock_ws.close.assert_not_called()

    @patch('scripts.agent_cli.websockets.connect')
    @patch('scripts.agent_cli.asyncio.sleep')
    async def test_handshake_retry_after_delay(self, mock_sleep, mock_connect):
        """Test handshake retry after delay when server not ready"""
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # First attempt: timeout (server not ready)
        # Second attempt: successful handshake
        handshake_response = {
            "type": "handshake_response",
            "thread_id": "test-thread-123",
            "user_id": "user-456",
            "session_id": "session-789"
        }

        # Configure recv to timeout first, then succeed
        mock_ws.recv.side_effect = [
            asyncio.TimeoutError(),  # First handshake attempt times out
            json.dumps(handshake_response)  # Second attempt succeeds
        ]

        # Create client and connect
        client = WebSocketClient(
            self.config, self.token, self.debug,
            send_logs=False, logs_count=10,
            logs_project=None, logs_path=None,
            logs_user=None, handshake_timeout=1
        )

        result = await client.connect()

        # Assertions
        self.assertTrue(result)
        self.assertTrue(client.connected)
        self.assertEqual(client.current_thread_id, "test-thread-123")
        mock_sleep.assert_called_once_with(3.0)  # Verify delay was applied
        mock_ws.close.assert_not_called()

    @patch('scripts.agent_cli.websockets.connect')
    @patch('scripts.agent_cli.asyncio.sleep')
    async def test_connection_fails_if_no_handshake(self, mock_sleep, mock_connect):
        """Test connection fails properly when server never completes handshake"""
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # Both handshake attempts timeout
        mock_ws.recv.side_effect = [
            asyncio.TimeoutError(),  # First attempt
            asyncio.TimeoutError()   # Second attempt after retry
        ]

        # Create client and connect
        client = WebSocketClient(
            self.config, self.token, self.debug,
            send_logs=False, logs_count=10,
            logs_project=None, logs_path=None,
            logs_user=None, handshake_timeout=1
        )

        result = await client.connect()

        # Assertions
        self.assertFalse(result)  # Connection should fail
        self.assertFalse(client.connected)  # Should not be marked as connected
        self.assertIsNone(client.current_thread_id)  # No thread ID assigned
        mock_sleep.assert_called_once_with(3.0)  # Verify retry delay
        mock_ws.close.assert_called_once()  # WebSocket should be closed

    @patch('scripts.agent_cli.websockets.connect')
    async def test_no_message_sent_without_handshake(self, mock_connect):
        """Test that send_message fails if handshake not completed"""
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # Handshake times out - no response
        mock_ws.recv.side_effect = asyncio.TimeoutError()

        # Create client and try to connect
        client = WebSocketClient(
            self.config, self.token, self.debug,
            send_logs=False, logs_count=10,
            logs_project=None, logs_path=None,
            logs_user=None, handshake_timeout=1
        )

        # Connection should fail due to no handshake
        result = await client.connect()
        self.assertFalse(result)

        # Attempting to send message should fail
        with self.assertRaises(Exception) as context:
            await client.send_message("test message")

        # Verify no message was sent via WebSocket
        mock_ws.send.assert_not_called()

    @patch('scripts.agent_cli.websockets.connect')
    async def test_connection_established_is_not_handshake(self, mock_connect):
        """Test that connection_established event is not treated as handshake"""
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # Send connection_established instead of handshake_response
        connection_event = {
            "type": "connection_established",
            "message": "Connected to server"
        }

        # Then timeout (no actual handshake)
        mock_ws.recv.side_effect = [
            json.dumps(connection_event),
            asyncio.TimeoutError()
        ]

        # Create client and connect
        client = WebSocketClient(
            self.config, self.token, self.debug,
            send_logs=False, logs_count=10,
            logs_project=None, logs_path=None,
            logs_user=None, handshake_timeout=1
        )

        result = await client.connect()

        # Connection should fail - connection_established is not a handshake
        self.assertFalse(result)
        self.assertFalse(client.connected)
        self.assertIsNone(client.current_thread_id)


def run_async_test(coro):
    """Helper to run async tests"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


class AsyncTestRunner(unittest.TestCase):
    """Wrapper to run async tests"""

    def test_successful_handshake(self):
        test = TestTimingFix()
        test.setUp()
        run_async_test(test.test_successful_handshake_on_first_try())

    def test_retry_after_delay(self):
        test = TestTimingFix()
        test.setUp()
        run_async_test(test.test_handshake_retry_after_delay())

    def test_connection_fails(self):
        test = TestTimingFix()
        test.setUp()
        run_async_test(test.test_connection_fails_if_no_handshake())

    def test_no_early_messages(self):
        test = TestTimingFix()
        test.setUp()
        run_async_test(test.test_no_message_sent_without_handshake())

    def test_connection_established_ignored(self):
        test = TestTimingFix()
        test.setUp()
        run_async_test(test.test_connection_established_is_not_handshake())


if __name__ == '__main__':
    unittest.main()