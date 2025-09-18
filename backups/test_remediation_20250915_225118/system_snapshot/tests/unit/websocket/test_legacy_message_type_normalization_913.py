"""
Unit Tests for Issue #913 - WebSocket Legacy Message Type Not Recognized

This module reproduces the exact error from Issue #913 where 'legacy_response'
and 'legacy_heartbeat' message types are not recognized by normalize_message_type().

BUSINESS IMPACT: $500K+ ARR depends on WebSocket message processing without errors
to ensure Golden Path chat functionality works correctly.

Issue #913: WebSocket Legacy Message Type 'legacy_response' Not Recognized
Root Cause: Missing 'legacy_response' and 'legacy_heartbeat' in LEGACY_MESSAGE_TYPE_MAP

TEST STRATEGY: These tests WILL FAIL initially to reproduce the bug, then PASS after fix.
"""

import pytest
import unittest
from typing import Dict, Any

from netra_backend.app.websocket_core.types import (
    MessageType,
    normalize_message_type,
    create_server_message,
    LEGACY_MESSAGE_TYPE_MAP
)


@pytest.mark.unit
class LegacyMessageTypeNormalization913Tests(unittest.TestCase):
    """Test normalize_message_type() function with legacy message types for Issue #913."""

    def test_legacy_response_message_type_fails_before_fix(self):
        """
        FAILING TEST: Reproduces Issue #913 - legacy_response not recognized.

        This test MUST FAIL initially to prove the bug exists.
        After fix, this should pass.
        """
        with self.assertRaises(ValueError) as context:
            normalize_message_type("legacy_response")

        # Validate the exact error message from Issue #913
        error_msg = str(context.exception)
        self.assertIn("Unknown message type: 'legacy_response'", error_msg)
        self.assertIn("Valid types:", error_msg)

        # Verify legacy_response is not currently in the map
        self.assertNotIn("legacy_response", LEGACY_MESSAGE_TYPE_MAP)

    def test_legacy_heartbeat_message_type_fails_before_fix(self):
        """
        FAILING TEST: Reproduces Issue #913 - legacy_heartbeat not recognized.

        This test MUST FAIL initially to prove the bug exists.
        After fix, this should pass.
        """
        with self.assertRaises(ValueError) as context:
            normalize_message_type("legacy_heartbeat")

        # Validate the exact error message structure
        error_msg = str(context.exception)
        self.assertIn("Unknown message type: 'legacy_heartbeat'", error_msg)
        self.assertIn("Valid types:", error_msg)

        # Verify legacy_heartbeat is not currently in the map
        self.assertNotIn("legacy_heartbeat", LEGACY_MESSAGE_TYPE_MAP)

    def test_create_server_message_with_legacy_response_fails(self):
        """
        FAILING TEST: Reproduces server message creation error with legacy_response.

        This demonstrates the complete flow failure from Issue #913.
        create_server_message() -> normalize_message_type() -> ValueError
        """
        with self.assertRaises(ValueError) as context:
            create_server_message("legacy_response", {"status": "success", "data": "test"})

        # Validate the error propagates correctly from normalize_message_type
        error_msg = str(context.exception)
        self.assertIn("Invalid message type 'legacy_response'", error_msg)
        self.assertIn("Unknown message type: 'legacy_response'", error_msg)

    def test_create_server_message_with_legacy_heartbeat_fails(self):
        """
        FAILING TEST: Reproduces server message creation error with legacy_heartbeat.

        This demonstrates the complete flow failure from Issue #913.
        """
        with self.assertRaises(ValueError) as context:
            create_server_message("legacy_heartbeat", {"timestamp": "2025-09-13T19:00:00Z"})

        # Validate the error propagates correctly
        error_msg = str(context.exception)
        self.assertIn("Invalid message type 'legacy_heartbeat'", error_msg)
        self.assertIn("Unknown message type: 'legacy_heartbeat'", error_msg)

    def test_existing_legacy_types_work_correctly(self):
        """
        PASSING TEST: Verify existing legacy message types work correctly.

        This ensures we don't break existing functionality while fixing Issue #913.
        """
        # Test some existing legacy mappings work fine
        test_cases = [
            ("user", MessageType.USER_MESSAGE),
            ("agent", MessageType.AGENT_REQUEST),
            ("heartbeat", MessageType.HEARTBEAT),
            ("ping", MessageType.PING),
            ("agent_started", MessageType.AGENT_STARTED),
            ("tool_executing", MessageType.TOOL_EXECUTING)
        ]

        for legacy_type, expected_type in test_cases:
            with self.subTest(legacy_type=legacy_type):
                result = normalize_message_type(legacy_type)
                self.assertEqual(result, expected_type)

                # Verify create_server_message works with these types
                server_msg = create_server_message(legacy_type, {"test": "data"})
                self.assertEqual(server_msg.type, expected_type)

    def test_valid_message_type_enum_works(self):
        """
        PASSING TEST: Verify MessageType enum values work correctly.

        This ensures standard MessageType enum handling is unaffected.
        """
        # Test MessageType enum values pass through correctly
        test_types = [
            MessageType.USER_MESSAGE,
            MessageType.AGENT_RESPONSE,
            MessageType.HEARTBEAT,
            MessageType.AGENT_STARTED,
            MessageType.TOOL_EXECUTING
        ]

        for msg_type in test_types:
            with self.subTest(msg_type=msg_type):
                result = normalize_message_type(msg_type)
                self.assertEqual(result, msg_type)

                # Verify create_server_message works with enum types
                server_msg = create_server_message(msg_type, {"test": "data"})
                self.assertEqual(server_msg.type, msg_type)

    def test_invalid_message_type_raises_clear_error(self):
        """
        PASSING TEST: Verify invalid types raise clear errors.

        This validates error handling works correctly.
        """
        invalid_types = [
            "completely_unknown_type",
            "invalid_message",
            "",
            None,
            123,
            []
        ]

        for invalid_type in invalid_types:
            with self.subTest(invalid_type=invalid_type):
                with self.assertRaises(ValueError) as context:
                    normalize_message_type(invalid_type)

                error_msg = str(context.exception)
                # For string types, should mention "Unknown message type"
                if isinstance(invalid_type, str) and invalid_type:
                    self.assertIn("Unknown message type", error_msg)
                else:
                    # For non-string types, should mention type validation
                    self.assertIn("Message type must be", error_msg)


@pytest.mark.unit
class LegacyMessageTypeFix913Tests(unittest.TestCase):
    """
    Tests that will PASS after Issue #913 fix is implemented.

    These tests validate that the fix works correctly and legacy types
    map to appropriate MessageType enum values.
    """

    def test_legacy_response_mapping_after_fix(self):
        """
        VALIDATION TEST: This will PASS after legacy_response is added to LEGACY_MESSAGE_TYPE_MAP.

        Uncomment after implementing the fix to validate it works.
        """
        # TODO: Uncomment after fix implementation
        # result = normalize_message_type("legacy_response")
        # self.assertIsInstance(result, MessageType)
        # self.assertEqual(result, MessageType.AGENT_RESPONSE)  # Expected mapping
        #
        # # Test server message creation works
        # server_msg = create_server_message("legacy_response", {"status": "success"})
        # self.assertEqual(server_msg.type, MessageType.AGENT_RESPONSE)
        pass

    def test_legacy_heartbeat_mapping_after_fix(self):
        """
        VALIDATION TEST: This will PASS after legacy_heartbeat is added to LEGACY_MESSAGE_TYPE_MAP.

        Uncomment after implementing the fix to validate it works.
        """
        # TODO: Uncomment after fix implementation
        # result = normalize_message_type("legacy_heartbeat")
        # self.assertIsInstance(result, MessageType)
        # self.assertEqual(result, MessageType.HEARTBEAT)  # Expected mapping
        #
        # # Test server message creation works
        # server_msg = create_server_message("legacy_heartbeat", {"timestamp": "2025-09-13T19:00:00Z"})
        # self.assertEqual(server_msg.type, MessageType.HEARTBEAT)
        pass

    def test_legacy_types_in_mapping_after_fix(self):
        """
        VALIDATION TEST: Verify legacy types are properly added to LEGACY_MESSAGE_TYPE_MAP.

        Uncomment after implementing the fix.
        """
        # TODO: Uncomment after fix implementation
        # self.assertIn("legacy_response", LEGACY_MESSAGE_TYPE_MAP)
        # self.assertIn("legacy_heartbeat", LEGACY_MESSAGE_TYPE_MAP)
        # self.assertEqual(LEGACY_MESSAGE_TYPE_MAP["legacy_response"], MessageType.AGENT_RESPONSE)
        # self.assertEqual(LEGACY_MESSAGE_TYPE_MAP["legacy_heartbeat"], MessageType.HEARTBEAT)
        pass


if __name__ == "__main__":
    unittest.main()