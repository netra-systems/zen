"""
Integration Tests for Issue #913 - WebSocket Legacy Message Processing Flow

This module tests the complete WebSocket message processing flow with legacy
message types through the WebSocket stack to validate Issue #913 impact.

BUSINESS IMPACT: $500K+ ARR depends on WebSocket message processing without errors
to ensure Golden Path chat functionality works correctly.

Issue #913: WebSocket Legacy Message Type 'legacy_response' Not Recognized
Integration Impact: Legacy message types fail in message routing and processing

TEST STRATEGY: These tests WILL FAIL initially to prove integration issues,
then PASS after fix is implemented.
"""

import pytest
import unittest
import asyncio
import json
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Import SSOT test base class
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import WebSocket core components
from netra_backend.app.websocket_core.types import (
    MessageType,
    normalize_message_type,
    create_server_message,
    WebSocketMessage
)
from netra_backend.app.websocket_core.manager import WebSocketManager


@pytest.mark.integration
class TestWebSocketLegacyMessageIntegration913(SSotAsyncTestCase):
    """Test WebSocket message processing with legacy message types for Issue #913."""

    def setUp(self):
        """Set up test fixtures with WebSocket components."""
        super().setUp()

        # Mock WebSocket manager components
        self.websocket_manager = MagicMock(spec=WebSocketManager)
        self.mock_connection = AsyncMock()
        self.mock_connection.connection_id = "test-connection-123"

        # Mock message processing components
        self.mock_message_handler = AsyncMock()
        self.mock_event_emitter = AsyncMock()

        # Set up manager components
        self.websocket_manager.process_message = AsyncMock()
        self.websocket_manager.send_message = AsyncMock()
        self.websocket_manager.handle_message = AsyncMock()

    async def test_websocket_legacy_response_message_integration_fails(self):
        """
        FAILING INTEGRATION: Tests legacy_response through WebSocket stack.

        This test demonstrates that legacy_response message type fails
        during WebSocket message processing due to missing LEGACY_MESSAGE_TYPE_MAP entry.
        """
        # Create a WebSocket message with legacy_response type
        legacy_message = {
            "type": "legacy_response",
            "payload": {
                "status": "success",
                "response_data": "Agent task completed",
                "agent_id": "test-agent-123"
            },
            "connection_id": "test-connection-123",
            "timestamp": 1726251600.0  # 2025-09-13
        }

        # This should fail because legacy_response is not in LEGACY_MESSAGE_TYPE_MAP
        with self.assertRaises(ValueError) as context:
            # Simulate WebSocket message processing that calls normalize_message_type
            message_type = normalize_message_type(legacy_message["type"])

        # Validate the error matches Issue #913
        error_msg = str(context.exception)
        self.assertIn("Unknown message type: 'legacy_response'", error_msg)

        # Also test server message creation fails
        with self.assertRaises(ValueError) as context:
            create_server_message("legacy_response", legacy_message["payload"])

        error_msg = str(context.exception)
        self.assertIn("Invalid message type 'legacy_response'", error_msg)

    async def test_websocket_legacy_heartbeat_integration_fails(self):
        """
        FAILING INTEGRATION: Tests legacy_heartbeat through WebSocket stack.

        This test demonstrates that legacy_heartbeat message type fails
        during WebSocket message processing.
        """
        # Create a WebSocket message with legacy_heartbeat type
        legacy_heartbeat = {
            "type": "legacy_heartbeat",
            "payload": {
                "timestamp": 1726251600.0,
                "connection_status": "active",
                "client_id": "web-client-456"
            },
            "connection_id": "test-connection-123"
        }

        # This should fail because legacy_heartbeat is not in LEGACY_MESSAGE_TYPE_MAP
        with self.assertRaises(ValueError) as context:
            message_type = normalize_message_type(legacy_heartbeat["type"])

        error_msg = str(context.exception)
        self.assertIn("Unknown message type: 'legacy_heartbeat'", error_msg)

        # Also test server message creation fails
        with self.assertRaises(ValueError):
            create_server_message("legacy_heartbeat", legacy_heartbeat["payload"])

    async def test_websocket_message_handler_with_legacy_types_fails(self):
        """
        FAILING INTEGRATION: Tests complete message handler flow with legacy types.

        This simulates the complete WebSocket message handling flow that would
        fail when legacy message types are encountered.
        """
        test_messages = [
            {
                "type": "legacy_response",
                "payload": {"status": "completed", "data": "test"},
                "connection_id": "test-conn-1"
            },
            {
                "type": "legacy_heartbeat",
                "payload": {"timestamp": 1726251600.0},
                "connection_id": "test-conn-2"
            }
        ]

        for message in test_messages:
            with self.subTest(message_type=message["type"]):
                # This simulates the WebSocket handler processing flow
                with self.assertRaises(ValueError) as context:
                    # Step 1: Normalize message type (this fails for legacy types)
                    normalized_type = normalize_message_type(message["type"])

                    # Step 2: Create server message (would also fail)
                    server_message = create_server_message(
                        message["type"],
                        message["payload"]
                    )

                # Validate error propagation
                error_msg = str(context.exception)
                self.assertIn(f"Unknown message type: '{message['type']}'", error_msg)

    async def test_existing_message_types_work_in_integration(self):
        """
        PASSING INTEGRATION: Verify existing message types work correctly in integration.

        This ensures we don't break existing WebSocket functionality while fixing Issue #913.
        """
        # Test existing message types that should work fine
        working_messages = [
            {
                "type": "user_message",
                "payload": {"text": "Hello", "user_id": "user-123"}
            },
            {
                "type": "agent_started",
                "payload": {"agent_id": "supervisor", "status": "started"}
            },
            {
                "type": "heartbeat",
                "payload": {"timestamp": 1726251600.0}
            },
            {
                "type": "tool_executing",
                "payload": {"tool": "search", "status": "running"}
            }
        ]

        for message in working_messages:
            with self.subTest(message_type=message["type"]):
                # These should work without errors
                normalized_type = normalize_message_type(message["type"])
                self.assertIsInstance(normalized_type, MessageType)

                # Server message creation should also work
                server_message = create_server_message(
                    message["type"],
                    message["payload"]
                )
                self.assertEqual(server_message.type, normalized_type)

    async def test_websocket_manager_mock_with_legacy_types(self):
        """
        FAILING INTEGRATION: Test WebSocket manager behavior with legacy types.

        This tests how the WebSocket manager would handle legacy message types
        through its message processing pipeline.
        """
        # Configure mock to simulate real WebSocket manager behavior
        async def mock_process_message(message_data):
            """Mock that simulates real WebSocket message processing."""
            # Real WebSocket manager would call normalize_message_type internally
            msg_type = message_data.get("type")
            normalized = normalize_message_type(msg_type)  # This will fail for legacy types
            return {"type": normalized, "processed": True}

        self.websocket_manager.process_message.side_effect = mock_process_message

        # Test messages that should fail
        failing_messages = [
            {"type": "legacy_response", "payload": {"status": "success"}},
            {"type": "legacy_heartbeat", "payload": {"timestamp": 1726251600.0}}
        ]

        for message in failing_messages:
            with self.subTest(message_type=message["type"]):
                with self.assertRaises(ValueError):
                    await self.websocket_manager.process_message(message)


@pytest.mark.integration
class TestWebSocketLegacyMessageFixValidation913(SSotAsyncTestCase):
    """
    Integration tests that will PASS after Issue #913 fix is implemented.

    These tests validate that the WebSocket integration works correctly
    after adding legacy message types to LEGACY_MESSAGE_TYPE_MAP.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Mock WebSocket manager
        self.websocket_manager = MagicMock(spec=WebSocketManager)
        self.websocket_manager.process_message = AsyncMock()
        self.websocket_manager.send_message = AsyncMock()

    async def test_legacy_response_integration_after_fix(self):
        """
        VALIDATION INTEGRATION: This will PASS after legacy_response fix.

        Uncomment after implementing the fix to validate integration works.
        """
        # TODO: Uncomment after fix implementation
        # legacy_message = {
        #     "type": "legacy_response",
        #     "payload": {"status": "success", "data": "test"},
        #     "connection_id": "test-connection"
        # }
        #
        # # This should work after fix
        # normalized_type = normalize_message_type(legacy_message["type"])
        # self.assertEqual(normalized_type, MessageType.AGENT_RESPONSE)
        #
        # # Server message creation should work
        # server_message = create_server_message(
        #     legacy_message["type"],
        #     legacy_message["payload"]
        # )
        # self.assertEqual(server_message.type, MessageType.AGENT_RESPONSE)
        pass

    async def test_legacy_heartbeat_integration_after_fix(self):
        """
        VALIDATION INTEGRATION: This will PASS after legacy_heartbeat fix.

        Uncomment after implementing the fix to validate integration works.
        """
        # TODO: Uncomment after fix implementation
        # legacy_heartbeat = {
        #     "type": "legacy_heartbeat",
        #     "payload": {"timestamp": 1726251600.0},
        #     "connection_id": "test-connection"
        # }
        #
        # # This should work after fix
        # normalized_type = normalize_message_type(legacy_heartbeat["type"])
        # self.assertEqual(normalized_type, MessageType.HEARTBEAT)
        #
        # # Server message creation should work
        # server_message = create_server_message(
        #     legacy_heartbeat["type"],
        #     legacy_heartbeat["payload"]
        # )
        # self.assertEqual(server_message.type, MessageType.HEARTBEAT)
        pass

    async def test_websocket_manager_with_legacy_types_after_fix(self):
        """
        VALIDATION INTEGRATION: Test WebSocket manager with legacy types after fix.

        Uncomment after implementing the fix.
        """
        # TODO: Uncomment after fix implementation
        # async def mock_process_message_after_fix(message_data):
        #     """Mock that simulates fixed WebSocket message processing."""
        #     msg_type = message_data.get("type")
        #     normalized = normalize_message_type(msg_type)  # Should work after fix
        #     return {"type": normalized, "processed": True}
        #
        # self.websocket_manager.process_message.side_effect = mock_process_message_after_fix
        #
        # # Test messages that should now work
        # working_messages = [
        #     {"type": "legacy_response", "payload": {"status": "success"}},
        #     {"type": "legacy_heartbeat", "payload": {"timestamp": 1726251600.0}}
        # ]
        #
        # for message in working_messages:
        #     with self.subTest(message_type=message["type"]):
        #         result = await self.websocket_manager.process_message(message)
        #         self.assertTrue(result["processed"])
        #         self.assertIsInstance(result["type"], MessageType)
        pass


if __name__ == "__main__":
    unittest.main()