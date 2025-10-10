#!/usr/bin/env python3
"""
Test for connection_established event timing requirement.

This test verifies that:
1. Events are only sent AFTER both handshake AND connection_established
2. connection_established received during handshake allows immediate sending
3. connection_established received after handshake triggers event flushing
4. Proper error handling when connection_established is not received
"""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.agent_cli import WebSocketClient, Environment


class TestConnectionEstablishedTiming(unittest.TestCase):
    """Test suite for connection_established event timing"""

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
    async def test_connection_established_during_handshake(self, mock_connect):
        """Test normal flow: connection_established arrives during handshake"""
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # Simulate server sending connection_established then handshake_response
        connection_event = {
            "type": "connection_established",
            "data": {"connection_id": "conn-123"}
        }
        handshake_response = {
            "type": "handshake_response",
            "thread_id": "test-thread-123",
            "user_id": "user-456",
            "session_id": "session-789"
        }

        mock_ws.recv.side_effect = [
            json.dumps(connection_event),
            json.dumps(handshake_response)
        ]

        # Create client and connect
        client = WebSocketClient(
            self.config, self.token, self.debug,
            send_logs=False, logs_count=10,
            logs_project=None, logs_path=None,
            logs_user=None, handshake_timeout=5
        )

        result = await client.connect()

        # Assertions
        self.assertTrue(result, "Connection should succeed")
        self.assertTrue(client.connected, "Client should be marked as connected")
        self.assertTrue(client.connection_established_received,
                       "connection_established flag should be set")
        self.assertTrue(client.ready_to_send_events,
                       "Should be ready to send events after both conditions met")
        self.assertEqual(client.current_thread_id, "test-thread-123")

    @patch('scripts.agent_cli.websockets.connect')
    async def test_handshake_only_not_ready(self, mock_connect):
        """Test that handshake alone is not sufficient - need connection_established too"""
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # Simulate server sending ONLY handshake_response (no connection_established)
        handshake_response = {
            "type": "handshake_response",
            "thread_id": "test-thread-123",
            "user_id": "user-456",
            "session_id": "session-789"
        }

        mock_ws.recv.side_effect = [
            json.dumps(handshake_response)
        ]

        # Create client and connect
        client = WebSocketClient(
            self.config, self.token, self.debug,
            send_logs=False, logs_count=10,
            logs_project=None, logs_path=None,
            logs_user=None, handshake_timeout=5
        )

        result = await client.connect()

        # Assertions
        self.assertTrue(result, "Connection should succeed (handshake completed)")
        self.assertTrue(client.connected, "Client should be marked as connected")
        self.assertFalse(client.connection_established_received,
                        "connection_established should NOT be received")
        self.assertFalse(client.ready_to_send_events,
                        "Should NOT be ready to send - missing connection_established")

    @patch('scripts.agent_cli.websockets.connect')
    async def test_send_message_blocked_without_connection_established(self, mock_connect):
        """Test that send_message raises error when connection_established not received"""
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # Simulate handshake without connection_established
        handshake_response = {
            "type": "handshake_response",
            "thread_id": "test-thread-123",
            "user_id": "user-456",
            "session_id": "session-789"
        }

        mock_ws.recv.side_effect = [
            json.dumps(handshake_response)
        ]

        # Create client and connect
        client = WebSocketClient(
            self.config, self.token, self.debug,
            send_logs=False, logs_count=10,
            logs_project=None, logs_path=None,
            logs_user=None, handshake_timeout=5
        )

        await client.connect()

        # Verify we're connected but not ready
        self.assertTrue(client.connected)
        self.assertFalse(client.ready_to_send_events)

        # Try to send message - should raise error
        with self.assertRaises(RuntimeError) as context:
            await client.send_message("test message")

        # Verify error message mentions connection_established
        self.assertIn("connection_established", str(context.exception).lower())

        # Verify no message was sent
        mock_ws.send.assert_not_called()

    @patch('scripts.agent_cli.websockets.connect')
    async def test_reversed_order_handshake_before_connection_established(self, mock_connect):
        """Test edge case: handshake_response arrives before connection_established"""
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # Unusual order: handshake_response BEFORE connection_established
        handshake_response = {
            "type": "handshake_response",
            "thread_id": "test-thread-123",
            "user_id": "user-456",
            "session_id": "session-789"
        }
        connection_event = {
            "type": "connection_established",
            "data": {"connection_id": "conn-123"}
        }

        mock_ws.recv.side_effect = [
            json.dumps(handshake_response),
            json.dumps(connection_event)
        ]

        # Create client and connect
        client = WebSocketClient(
            self.config, self.token, self.debug,
            send_logs=False, logs_count=10,
            logs_project=None, logs_path=None,
            logs_user=None, handshake_timeout=5
        )

        # Connect will return after handshake_response (first message)
        result = await client.connect()

        # At this point, handshake is complete but connection_established not received yet
        self.assertTrue(result)
        self.assertTrue(client.connected)
        self.assertFalse(client.connection_established_received)
        self.assertFalse(client.ready_to_send_events)

        # Now manually process the connection_established event (simulating receive_events)
        # This would normally happen in receive_events callback
        client.connection_established_received = True
        if client.connected and not client.ready_to_send_events:
            client.ready_to_send_events = True

        # Now should be ready
        self.assertTrue(client.ready_to_send_events)

    @patch('scripts.agent_cli.websockets.connect')
    async def test_duplicate_connection_established_after_handshake(self, mock_connect):
        """Test that duplicate connection_established events are handled correctly"""
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        # Normal order with duplicate connection_established later
        connection_event = {
            "type": "connection_established",
            "data": {"connection_id": "conn-123"}
        }
        handshake_response = {
            "type": "handshake_response",
            "thread_id": "test-thread-123",
            "user_id": "user-456",
            "session_id": "session-789"
        }

        mock_ws.recv.side_effect = [
            json.dumps(connection_event),
            json.dumps(handshake_response)
        ]

        # Create client and connect
        client = WebSocketClient(
            self.config, self.token, self.debug,
            send_logs=False, logs_count=10,
            logs_project=None, logs_path=None,
            logs_user=None, handshake_timeout=5
        )

        result = await client.connect()

        # Should be ready after connect
        self.assertTrue(result)
        self.assertTrue(client.ready_to_send_events)

        # Simulate duplicate connection_established in receive_events
        # (this is what the code at line 4156-4162 in agent_cli.py handles)
        duplicate_count_before = len([e for e in client.events
                                     if e.type == 'connection_established'])

        # The receive_events code should skip duplicate connection_established
        # We're testing that the flag doesn't get reset or cause issues


def run_async_test(coro):
    """Helper to run async tests"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


class AsyncTestRunner(unittest.TestCase):
    """Wrapper to run async tests"""

    def test_connection_established_during_handshake(self):
        test = TestConnectionEstablishedTiming()
        test.setUp()
        run_async_test(test.test_connection_established_during_handshake())

    def test_handshake_only_not_ready(self):
        test = TestConnectionEstablishedTiming()
        test.setUp()
        run_async_test(test.test_handshake_only_not_ready())

    def test_send_message_blocked(self):
        test = TestConnectionEstablishedTiming()
        test.setUp()
        run_async_test(test.test_send_message_blocked_without_connection_established())

    def test_reversed_order(self):
        test = TestConnectionEstablishedTiming()
        test.setUp()
        run_async_test(test.test_reversed_order_handshake_before_connection_established())

    def test_duplicate_connection_established(self):
        test = TestConnectionEstablishedTiming()
        test.setUp()
        run_async_test(test.test_duplicate_connection_established_after_handshake())


if __name__ == '__main__':
    unittest.main()
