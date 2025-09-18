"""
Test Issue #1093: SSOT WebSocket Agent Handler Compatibility Layer

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Zero-Downtime Migration
- Value Impact: Ensures existing imports continue working during SSOT transition
- Strategic Impact: Maintains system stability while eliminating fragmentation

This test validates that the compatibility layer properly redirects existing
imports to the SSOT implementation without breaking existing code.
"""

import pytest
from unittest.mock import MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.types import MessageType


class TestCompatibilityLayer(SSotAsyncTestCase):
    """Tests validating backwards compatibility for existing imports."""

    async def test_agent_handler_import_compatibility(self):
        """Test that existing AgentMessageHandler imports work with SSOT."""
        # Test original import path continues to work
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler

        # Create handler using original import
        mock_service = MagicMock()
        mock_websocket = MagicMock()
        handler = AgentMessageHandler(mock_service, mock_websocket)

        # Verify it's actually the SSOT implementation
        stats = handler.get_stats()
        self.assertEqual(stats["handler_type"], "SSOT_CANONICAL")
        self.assertEqual(stats["consolidation_issue"], "#1093")

        # Verify all original functionality works
        self.assertTrue(handler.can_handle(MessageType.START_AGENT))
        self.assertTrue(handler.can_handle(MessageType.USER_MESSAGE))
        self.assertTrue(handler.can_handle(MessageType.CHAT))

    async def test_agent_handler_alias_compatibility(self):
        """Test that AgentHandler alias works with SSOT."""
        # Test alias import
        from netra_backend.app.websocket_core.agent_handler import AgentHandler

        # Create handler using alias
        mock_service = MagicMock()
        mock_websocket = MagicMock()
        handler = AgentHandler(mock_service, mock_websocket)

        # Verify it's the same SSOT implementation
        stats = handler.get_stats()
        self.assertEqual(stats["handler_type"], "SSOT_CANONICAL")

        # Verify AgentHandler and AgentMessageHandler are the same
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
        self.assertEqual(AgentHandler, AgentMessageHandler)

    async def test_ssot_implementation_direct_import(self):
        """Test that direct SSOT import works for new development."""
        # Test direct SSOT import
        from netra_backend.app.websocket_core.ssot_agent_message_handler import SSotAgentMessageHandler

        mock_service = MagicMock()
        mock_websocket = MagicMock()
        handler = SSotAgentMessageHandler(mock_service, mock_websocket)

        # Verify SSOT functionality
        stats = handler.get_stats()
        self.assertEqual(stats["handler_type"], "SSOT_CANONICAL")
        self.assertEqual(stats["consolidation_issue"], "#1093")

        # Verify enhanced SSOT features
        self.assertIn("golden_path_events_sent", stats)
        self.assertIn("v3_pattern_usage", stats)
        self.assertIn("user_isolation_instances", stats)

    async def test_compatibility_interface_consistency(self):
        """Test that compatibility imports have same interface as SSOT."""
        # Import through compatibility layer
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler as CompatHandler

        # Import SSOT directly
        from netra_backend.app.websocket_core.ssot_agent_message_handler import SSotAgentMessageHandler

        # Verify they are the same class
        self.assertEqual(CompatHandler, SSotAgentMessageHandler)

        # Create instances
        mock_service = MagicMock()
        mock_websocket = MagicMock()

        compat_handler = CompatHandler(mock_service, mock_websocket)
        ssot_handler = SSotAgentMessageHandler(mock_service, mock_websocket)

        # Verify identical interfaces
        compat_methods = set(dir(compat_handler))
        ssot_methods = set(dir(ssot_handler))
        self.assertEqual(compat_methods, ssot_methods)

        # Verify identical functionality
        for message_type in [MessageType.START_AGENT, MessageType.USER_MESSAGE, MessageType.CHAT]:
            self.assertEqual(
                compat_handler.can_handle(message_type),
                ssot_handler.can_handle(message_type)
            )

    async def test_existing_code_patterns_work(self):
        """Test that existing code patterns continue to work unchanged."""
        # Simulate existing code pattern
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler

        mock_service = MagicMock()
        mock_websocket = MagicMock()

        # Create handler as existing code would
        handler = AgentMessageHandler(mock_service, mock_websocket)

        # Test existing patterns work
        self.assertTrue(hasattr(handler, 'handle_message'))
        self.assertTrue(hasattr(handler, 'can_handle'))
        self.assertTrue(hasattr(handler, 'get_stats'))
        self.assertTrue(hasattr(handler, 'supported_types'))

        # Test that stats work as expected
        stats = handler.get_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("messages_processed", stats)
        self.assertIn("errors", stats)

        # Test that message type checking works
        self.assertEqual(len(handler.supported_types), 3)
        self.assertIn(MessageType.START_AGENT, handler.supported_types)

    async def test_backwards_compatibility_aliases_in_ssot(self):
        """Test that SSOT module provides backwards compatibility aliases."""
        # Test aliases defined in SSOT module
        from netra_backend.app.websocket_core.ssot_agent_message_handler import (
            AgentMessageHandler,
            AgentHandler,
            SSotAgentMessageHandler
        )

        # Verify aliases point to SSOT implementation
        self.assertEqual(AgentMessageHandler, SSotAgentMessageHandler)
        self.assertEqual(AgentHandler, SSotAgentMessageHandler)

        # Test that all aliases work identically
        mock_service = MagicMock()
        mock_websocket = MagicMock()

        handlers = [
            AgentMessageHandler(mock_service, mock_websocket),
            AgentHandler(mock_service, mock_websocket),
            SSotAgentMessageHandler(mock_service, mock_websocket)
        ]

        # Verify all handlers are identical
        for i, handler in enumerate(handlers):
            stats = handler.get_stats()
            self.assertEqual(stats["handler_type"], "SSOT_CANONICAL")

            # Verify same supported types
            for other_handler in handlers[i+1:]:
                self.assertEqual(handler.supported_types, other_handler.supported_types)


class TestMigrationValidation(SSotAsyncTestCase):
    """Tests validating successful migration from fragmented to SSOT handlers."""

    async def test_fragmentation_resolved(self):
        """Test that fragmentation issue is resolved with SSOT."""
        # Before SSOT: Multiple different handler classes existed
        # After SSOT: All imports should resolve to same implementation

        # Import all possible handler variations
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler as AH1
        from netra_backend.app.websocket_core.agent_handler import AgentHandler as AH2
        from netra_backend.app.websocket_core.ssot_agent_message_handler import SSotAgentMessageHandler as AH3
        from netra_backend.app.websocket_core.ssot_agent_message_handler import AgentMessageHandler as AH4
        from netra_backend.app.websocket_core.ssot_agent_message_handler import AgentHandler as AH5

        # Verify all imports resolve to the same SSOT implementation
        handlers = [AH1, AH2, AH3, AH4, AH5]
        for i, handler_class in enumerate(handlers):
            for other_handler_class in handlers[i+1:]:
                self.assertEqual(handler_class, other_handler_class,
                    f"All handler imports should resolve to the same SSOT class")

        # Verify it's the SSOT implementation
        mock_service = MagicMock()
        mock_websocket = MagicMock()
        instance = AH1(mock_service, mock_websocket)
        stats = instance.get_stats()
        self.assertEqual(stats["handler_type"], "SSOT_CANONICAL")

    async def test_golden_path_consistency(self):
        """Test that all handler imports ensure Golden Path events."""
        # Import through different paths
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler as CompatHandler
        from netra_backend.app.websocket_core.ssot_agent_message_handler import SSotAgentMessageHandler

        mock_service = MagicMock()
        mock_websocket = MagicMock()

        # Create handlers through different import paths
        compat_handler = CompatHandler(mock_service, mock_websocket)
        ssot_handler = SSotAgentMessageHandler(mock_service, mock_websocket)

        # Verify both track Golden Path events
        compat_stats = compat_handler.get_stats()
        ssot_stats = ssot_handler.get_stats()

        self.assertIn("golden_path_events_sent", compat_stats)
        self.assertIn("golden_path_events_sent", ssot_stats)

        # Verify both use V3 pattern
        self.assertIn("v3_pattern_usage", compat_stats)
        self.assertIn("v3_pattern_usage", ssot_stats)

        # Verify both provide user isolation
        self.assertIn("user_isolation_instances", compat_stats)
        self.assertIn("user_isolation_instances", ssot_stats)

    async def test_no_functionality_lost(self):
        """Test that SSOT consolidation doesn't lose any functionality."""
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler

        mock_service = MagicMock()
        mock_websocket = MagicMock()
        handler = AgentMessageHandler(mock_service, mock_websocket)

        # Verify all expected methods exist
        required_methods = [
            'handle_message',
            'can_handle',
            'get_stats',
            '_handle_message_v3_clean_ssot',
            '_route_ssot_agent_message_v3',
            '_handle_ssot_message_v3',
            '_update_ssot_processing_stats'
        ]

        for method in required_methods:
            self.assertTrue(hasattr(handler, method),
                f"SSOT handler missing required method: {method}")

        # Verify all expected properties exist
        required_properties = [
            'supported_types',
            'processing_stats',
            'message_handler_service',
            'websocket'
        ]

        for prop in required_properties:
            self.assertTrue(hasattr(handler, prop),
                f"SSOT handler missing required property: {prop}")

        # Verify message type support preserved
        self.assertEqual(len(handler.supported_types), 3)
        self.assertTrue(handler.can_handle(MessageType.START_AGENT))
        self.assertTrue(handler.can_handle(MessageType.USER_MESSAGE))
        self.assertTrue(handler.can_handle(MessageType.CHAT))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])