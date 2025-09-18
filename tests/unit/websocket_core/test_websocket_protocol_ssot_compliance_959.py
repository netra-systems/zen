"""
Test WebSocket Protocol SSOT compliance for Issue #959

This test validates that the SSOT consolidation for WebSocketProtocol
naming conflicts has been successfully resolved.

Business Value:
- Prevents naming conflicts that could cause import errors
- Ensures clear separation between Protocol interface and concrete implementation
- Validates backward compatibility is maintained
"""

import unittest
from typing import Protocol

from netra_backend.app.websocket_core.protocols import (
    WebSocketProtocol,
    WebSocketConnectionWrapper,
    WebSocketProtocolValidator
)


class TestWebSocketProtocolSSOTCompliance(unittest.TestCase):
    """Test suite for Issue #959 SSOT consolidation validation."""

    def test_protocol_interface_still_exists(self):
        """Test that WebSocketProtocol as Protocol interface still works."""
        # Should be able to use as type hint
        def function_expecting_protocol(manager: WebSocketProtocol) -> str:
            return f"Manager type: {type(manager).__name__}"

        # Create instance and test
        wrapper = WebSocketConnectionWrapper()
        result = function_expecting_protocol(wrapper)
        self.assertIn("WebSocketConnectionWrapper", result)

    def test_concrete_class_renamed_correctly(self):
        """Test that concrete class is now WebSocketConnectionWrapper."""
        wrapper = WebSocketConnectionWrapper(
            connection_id="test-123",
            user_id="user-456"
        )

        self.assertEqual(wrapper.connection_id, "test-123")
        self.assertEqual(wrapper.user_id, "user-456")
        self.assertTrue(wrapper.is_active)
        self.assertEqual(type(wrapper).__name__, "WebSocketConnectionWrapper")

    def test_backward_compatibility_alias(self):
        """Test that backward compatibility alias works."""
        # This should work due to the alias WebSocketProtocol = WebSocketConnectionWrapper
        legacy_instance = WebSocketProtocol(
            connection_id="legacy-123",
            user_id="legacy-456"
        )

        self.assertEqual(legacy_instance.connection_id, "legacy-123")
        self.assertEqual(legacy_instance.user_id, "legacy-456")
        self.assertTrue(legacy_instance.is_active)

    def test_types_are_equivalent_due_to_alias(self):
        """Test that the alias makes types equivalent."""
        wrapper = WebSocketConnectionWrapper()
        legacy = WebSocketProtocol()

        # Should be same type due to alias
        self.assertEqual(type(wrapper), type(legacy))
        self.assertEqual(type(wrapper).__name__, "WebSocketConnectionWrapper")

    def test_validator_works_with_new_class(self):
        """Test that validator processes the new class correctly."""
        wrapper = WebSocketConnectionWrapper()

        # Validator should handle it properly
        result = WebSocketProtocolValidator.validate_manager_protocol(wrapper)

        self.assertIsInstance(result, dict)
        self.assertIn('compliant', result)
        self.assertIn('manager_type', result)
        self.assertEqual(result['manager_type'], 'WebSocketConnectionWrapper')

    def test_no_naming_conflict(self):
        """Test that there's no naming conflict in the module."""
        # Import should work without conflicts
        from netra_backend.app.websocket_core.protocols import WebSocketProtocol

        # Should be able to create instances
        instance = WebSocketProtocol()
        self.assertIsNotNone(instance)

    async def test_async_methods_work(self):
        """Test that async methods on wrapper work correctly."""
        wrapper = WebSocketConnectionWrapper()

        # Test send_message (should return False since no real websocket)
        result = await wrapper.send_message({"test": "message"})
        self.assertFalse(result)

        # Test close
        await wrapper.close()
        self.assertFalse(wrapper.is_active)


if __name__ == '__main__':
    unittest.main()