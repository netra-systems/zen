#!/usr/bin/env python3
"""
Issue #1113 UserExecutionEngine Constructor Test Remediation

Business Value Justification (BVJ):
- Segment: Platform/Internal (enables all customer segments)
- Business Goal: Ensure UserExecutionEngine constructor validation works correctly
- Value Impact: Protects $500K+ ARR chat functionality by validating core execution engine
- Revenue Impact: Prevents production failures in agent execution that could break customer chat

Purpose: This test reproduces and fixes the UserExecutionEngine constructor validation
logic mismatch discovered in Issue #1113. The issue was misidentified as an import
problem but is actually a test logic mismatch where tests expect old constructor
signature (2 args + RuntimeError) but current implementation requires 3 args and
raises ValueError.

Expected Behavior:
- BEFORE FIX: Tests fail because they expect RuntimeError but get ValueError
- AFTER FIX: Tests pass with correct ValueError and constructor signature validation

Root Cause: SSOT migration (Issues #565, #802, #1116) updated UserExecutionEngine
constructor but related tests were not updated to match new signature.

Author: Claude Code Agent - Issue #1113 Test Remediation
Created: 2025-09-14
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from typing import Any

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Test framework imports following SSOT patterns
import unittest
try:
    from test_framework.ssot.base_test_case import SSotBaseTestCase
    SSOT_FRAMEWORK_AVAILABLE = True
except ImportError:
    SSotBaseTestCase = unittest.TestCase
    SSOT_FRAMEWORK_AVAILABLE = False

# Import the system under test
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.mark.unit
class Issue1113UserExecutionEngineConstructorFixTests(SSotBaseTestCase):
    """
    Test remediation for Issue #1113 UserExecutionEngine constructor validation.

    This test suite addresses the constructor logic mismatch where tests expected
    old signature (2 args + RuntimeError) but current implementation requires
    3 args and raises ValueError for invalid arguments.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Mock required dependencies for valid constructor tests
        self.mock_user_context = MagicMock(spec=UserExecutionContext)
        self.mock_user_context.user_id = "test-user-123"
        self.mock_user_context.request_id = "req-456"

        self.mock_agent_factory = MagicMock()
        self.mock_websocket_emitter = MagicMock()

    def test_issue_1113_reproduce_original_failure_pattern(self):
        """
        REPRODUCE: Original test pattern that was failing in Issue #1113.

        This demonstrates the old test logic that expected RuntimeError but
        gets ValueError, causing the constructor validation mismatch.
        """
        # This is the pattern that was failing - expecting RuntimeError but getting ValueError
        with pytest.raises(ValueError, match="Invalid arguments"):
            # OLD FAILING PATTERN: 2 args expecting RuntimeError
            # NEW REALITY: 2 args raises ValueError
            engine = UserExecutionEngine(None, None)  # 2 args - invalid signature

    def test_user_execution_engine_constructor_invalid_signature_two_args(self):
        """
        Test UserExecutionEngine constructor fails gracefully with 2 arguments.

        FIXED BEHAVIOR: Now correctly expects ValueError instead of RuntimeError.
        """
        # Test with 2 None arguments (invalid)
        with pytest.raises(ValueError, match="Invalid arguments. Use UserExecutionEngine"):
            engine = UserExecutionEngine(None, None)

        # Test with 2 random arguments (invalid)
        with pytest.raises(ValueError, match="Invalid arguments. Use UserExecutionEngine"):
            engine = UserExecutionEngine("arg1", "arg2")

    def test_user_execution_engine_constructor_invalid_signature_one_arg(self):
        """
        Test UserExecutionEngine constructor fails gracefully with 1 argument.
        """
        with pytest.raises(ValueError, match="Invalid arguments. Use UserExecutionEngine"):
            engine = UserExecutionEngine(self.mock_user_context)  # 1 arg - invalid

    def test_user_execution_engine_constructor_invalid_signature_no_args(self):
        """
        Test UserExecutionEngine constructor fails gracefully with no arguments.
        """
        with pytest.raises(ValueError, match="Invalid arguments. Use UserExecutionEngine"):
            engine = UserExecutionEngine()  # 0 args - invalid

    def test_user_execution_engine_constructor_valid_positional_signature(self):
        """
        Test UserExecutionEngine constructor succeeds with valid 3-argument signature.

        BUSINESS VALUE: Validates the correct factory pattern that enables proper
        user isolation and multi-tenant execution critical for $500K+ ARR protection.
        """
        # Valid 3-argument positional constructor
        engine = UserExecutionEngine(
            self.mock_user_context,
            self.mock_agent_factory,
            self.mock_websocket_emitter
        )

        # Verify engine was created successfully
        self.assertIsNotNone(engine)
        self.assertEqual(engine.context, self.mock_user_context)
        self.assertIsNotNone(engine.engine_id)

    def test_user_execution_engine_constructor_valid_keyword_signature(self):
        """
        Test UserExecutionEngine constructor succeeds with valid keyword arguments.
        """
        # Valid keyword constructor
        engine = UserExecutionEngine(
            context=self.mock_user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )

        # Verify engine was created successfully
        self.assertIsNotNone(engine)
        self.assertEqual(engine.context, self.mock_user_context)
        self.assertIsNotNone(engine.engine_id)

    def test_user_execution_engine_constructor_mixed_positional_keyword(self):
        """
        Test UserExecutionEngine constructor with mixed positional/keyword args.
        """
        # Mixed positional + keyword (should work)
        engine = UserExecutionEngine(
            self.mock_user_context,  # positional
            agent_factory=self.mock_agent_factory,  # keyword
            websocket_emitter=self.mock_websocket_emitter  # keyword
        )

        self.assertIsNotNone(engine)
        self.assertEqual(engine.context, self.mock_user_context)

    def test_user_execution_engine_constructor_validates_user_context_requirement(self):
        """
        Test UserExecutionEngine constructor enforces user_context requirement.

        SECURITY: This validates that user isolation is enforced at construction time,
        critical for preventing cross-user data contamination.
        """
        # Test with None user context (should fail)
        with pytest.raises(ValueError, match="user_context is required"):
            engine = UserExecutionEngine(
                context=None,  # Invalid - None context
                agent_factory=self.mock_agent_factory,
                websocket_emitter=self.mock_websocket_emitter
            )

    def test_ssot_factory_pattern_compliance(self):
        """
        Test that UserExecutionEngine follows SSOT factory pattern requirements.

        SSOT COMPLIANCE: Validates the constructor creates proper isolated instances
        that prevent singleton-related security vulnerabilities.
        """
        # Create multiple engines - should be isolated instances
        engine1 = UserExecutionEngine(
            self.mock_user_context,
            self.mock_agent_factory,
            self.mock_websocket_emitter
        )

        # Create second context for isolation test
        mock_context2 = MagicMock(spec=UserExecutionContext)
        mock_context2.user_id = "different-user-789"

        engine2 = UserExecutionEngine(
            mock_context2,
            self.mock_agent_factory,
            self.mock_websocket_emitter
        )

        # Verify instances are separate (no shared state)
        self.assertNotEqual(engine1.engine_id, engine2.engine_id)
        self.assertNotEqual(engine1.context.user_id, engine2.context.user_id)
        self.assertEqual(engine1.context.user_id, "test-user-123")
        self.assertEqual(engine2.context.user_id, "different-user-789")

    def test_backwards_compatibility_legacy_method_support(self):
        """
        Test that UserExecutionEngine maintains backwards compatibility methods.

        MIGRATION SUPPORT: Ensures existing code doesn't break during SSOT migration.
        """
        engine = UserExecutionEngine(
            self.mock_user_context,
            self.mock_agent_factory,
            self.mock_websocket_emitter
        )

        # Verify key methods exist for backwards compatibility
        self.assertTrue(hasattr(engine, 'execute_agent'))
        self.assertTrue(hasattr(engine, 'get_agent_state'))
        self.assertTrue(hasattr(engine, 'set_agent_state'))

        # Verify WebSocket integration
        self.assertTrue(hasattr(engine, 'websocket_emitter'))


@pytest.mark.unit
class Issue1113ConstructorErrorMessagesTests(SSotBaseTestCase):
    """
    Test suite for validating specific error messages in UserExecutionEngine constructor.

    This ensures developers get clear guidance when using the constructor incorrectly.
    """

    def test_constructor_error_message_content(self):
        """
        Test that constructor error messages provide clear guidance.
        """
        try:
            # Trigger error with invalid constructor
            engine = UserExecutionEngine("invalid", "args")
            self.fail("Expected ValueError was not raised")
        except ValueError as e:
            error_message = str(e)

            # Verify error message contains helpful guidance
            self.assertIn("Invalid arguments", error_message)
            self.assertIn("UserExecutionEngine", error_message)
            self.assertIn("context", error_message)
            self.assertIn("agent_factory", error_message)
            self.assertIn("websocket_emitter", error_message)

    def test_constructor_error_suggests_keyword_form(self):
        """
        Test that constructor error suggests both positional and keyword forms.
        """
        with pytest.raises(ValueError) as exc_info:
            engine = UserExecutionEngine()

        error_message = str(exc_info.value)
        self.assertIn("keyword form", error_message)


if __name__ == "__main__":
    import unittest
    unittest.main()