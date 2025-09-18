"""
Issue #1167 Interface Contract Tests - Phase 1 Implementation

CRITICAL MISSION: Create tests that prove the exact interface failures identified in the Five Whys analysis.

These tests are designed to FAIL initially, proving that the interface issues exist as identified.
Each test focuses on a specific contract violation that prevents proper WebSocket message routing.

EXPECTED BEHAVIOR: All tests should FAIL until Issue #1167 is resolved.

Test Coverage:
1. test_agent_websocket_bridge_has_handle_message() - Prove missing method
2. test_user_execution_context_metadata_parameter() - Prove invalid constructor parameter
3. test_websocket_message_routing_integration() - Prove interface mismatch

Business Impact: $500K+ ARR Golden Path WebSocket functionality blocked by these interface issues.
"""

import pytest
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.ssot.base_test_case import SSotBaseTestCase
from fastapi import WebSocket

# SSOT imports following registry patterns
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, create_agent_websocket_bridge
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from shared.types.core_types import UserID, ThreadID, RunID


@pytest.mark.unit
class Issue1167InterfaceContractsTests(SSotBaseTestCase, unittest.TestCase):
    """
    Interface contract tests to prove the identified failures exist.

    These tests validate the Five Whys analysis findings by testing actual interface contracts.
    Each test should FAIL until the corresponding interface issue is resolved.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_websocket = MagicMock(spec=WebSocket)
        self.test_user_id = "test-user-1167"
        self.test_thread_id = "test-thread-1167"
        self.test_run_id = "test-run-1167"

    def test_agent_websocket_bridge_has_handle_message(self):
        """
        INTERFACE CONTRACT TEST: AgentWebSocketBridge must have handle_message() method.

        This test proves that AgentWebSocketBridge is missing the handle_message() method
        that is expected by the WebSocket message routing infrastructure.

        Five Whys Analysis Finding: AgentWebSocketBridge lacks handle_message() method
        Expected Result: FAIL with AttributeError - 'AgentWebSocketBridge' object has no attribute 'handle_message'
        Business Impact: WebSocket message routing cannot delegate to agent processing
        """
        # Create AgentWebSocketBridge instance
        bridge = create_agent_websocket_bridge()
        self.assertIsInstance(bridge, AgentWebSocketBridge)

        # Create test message
        test_message = WebSocketMessage(
            type=MessageType.AGENT_START,
            data={'agent_type': 'DataHelper', 'user_request': 'test request'},
            user_id=self.test_user_id,
            run_id=self.test_run_id
        )

        # CRITICAL TEST: This should FAIL - AgentWebSocketBridge should not have handle_message method
        with self.assertRaises(AttributeError) as context:
            # This should fail because handle_message method doesn't exist
            bridge.handle_message(self.test_user_id, self.mock_websocket, test_message)

        # Verify the exact error indicates missing handle_message method
        error_message = str(context.exception)
        self.assertIn("handle_message", error_message)
        self.assertIn("AgentWebSocketBridge", error_message)

        # Document the interface contract violation
        self.fail(
            f"INTERFACE CONTRACT VIOLATION: AgentWebSocketBridge missing handle_message() method. "
            f"Error: {error_message}. "
            f"This prevents WebSocket message routing from delegating to agent processing, "
            f"blocking $500K+ ARR Golden Path functionality."
        )

    def test_user_execution_context_metadata_parameter(self):
        """
        INTERFACE CONTRACT TEST: UserExecutionContext constructor must not accept 'metadata' parameter.

        This test proves that UserExecutionContext constructor is being called with an invalid
        'metadata' parameter that doesn't exist in the actual constructor signature.

        Five Whys Analysis Finding: UserExecutionContext called with non-existent 'metadata' parameter
        Expected Result: FAIL with TypeError - unexpected keyword argument 'metadata'
        Business Impact: Agent initialization fails preventing WebSocket message processing
        """
        # CRITICAL TEST: This should FAIL - UserExecutionContext doesn't accept metadata parameter
        with self.assertRaises(TypeError) as context:
            # This reproduces the exact error from the Five Whys analysis
            user_context = UserExecutionContext(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id,
                metadata={'user_request': 'test request', 'agent_type': 'DataHelper'}  # Invalid parameter
            )

        # Verify the exact error message pattern
        error_message = str(context.exception)
        self.assertIn("unexpected keyword argument 'metadata'", error_message)
        self.assertIn("UserExecutionContext", error_message)

        # Document the interface contract violation
        self.fail(
            f"INTERFACE CONTRACT VIOLATION: UserExecutionContext constructor called with invalid 'metadata' parameter. "
            f"Error: {error_message}. "
            f"This prevents proper user context creation, blocking agent initialization and WebSocket processing."
        )

    def test_user_execution_context_correct_constructor_works(self):
        """
        VALIDATION TEST: UserExecutionContext with correct parameters should work.

        This test verifies that UserExecutionContext works correctly when called with valid parameters,
        demonstrating that the issue is specifically with the invalid 'metadata' parameter usage.

        Expected Result: PASS - Shows correct constructor usage works
        """
        # This should work - using correct constructor parameters
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
            # No metadata parameter - this is correct
        )

        # Verify the context was created successfully
        self.assertEqual(user_context.user_id, self.test_user_id)
        self.assertEqual(user_context.thread_id, self.test_thread_id)
        self.assertEqual(user_context.run_id, self.test_run_id)

    @patch('netra_backend.app.services.agent_websocket_bridge.WebSocketManager')
    @patch('netra_backend.app.services.agent_websocket_bridge.get_thread_run_registry')
    def test_websocket_message_routing_integration(self, mock_registry, mock_websocket_manager):
        """
        INTERFACE CONTRACT TEST: WebSocket message routing integration must work end-to-end.

        This test proves that there is an interface mismatch between WebSocket message routing
        and agent processing that prevents proper message flow.

        Five Whys Analysis Finding: Interface mismatch in WebSocket message routing chain
        Expected Result: FAIL with integration error showing interface mismatch
        Business Impact: Messages cannot flow from WebSocket to agents, breaking chat functionality
        """
        # Set up mocks for the integration test
        mock_registry.return_value = MagicMock()
        mock_websocket_manager.return_value = MagicMock()

        # Create AgentWebSocketBridge instance
        bridge = create_agent_websocket_bridge()

        # Create valid UserExecutionContext (without metadata)
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )

        # Create test message for agent start
        test_message = WebSocketMessage(
            type=MessageType.AGENT_START,
            data={'agent_type': 'DataHelper', 'user_request': 'test integration request'},
            user_id=self.test_user_id,
            run_id=self.test_run_id
        )

        # CRITICAL TEST: Try to simulate the expected message routing flow
        # This should reveal the interface mismatch identified in Five Whys analysis
        try:
            # Step 1: Try to use bridge as a message handler (should fail - no handle_message)
            if hasattr(bridge, 'handle_message'):
                result = bridge.handle_message(self.test_user_id, self.mock_websocket, test_message)
                self.fail("AgentWebSocketBridge should not have handle_message method")

            # Step 2: Try alternative routing through bridge methods
            # This should also fail due to interface mismatches
            bridge.notify_agent_started(
                user_id=self.test_user_id,
                run_id=self.test_run_id,
                agent_name="DataHelper",
                agent_type="DataHelper"
            )

            # If we get here, the interface contract violation wasn't detected
            self.fail(
                "INTERFACE CONTRACT VIOLATION: Expected integration failure due to interface mismatch "
                "between WebSocket message routing and agent processing. "
                "The routing should fail but didn't, indicating the test needs refinement."
            )

        except AttributeError as e:
            # This is expected - proves the interface contract violation
            if "handle_message" in str(e):
                self.fail(
                    f"INTERFACE CONTRACT VIOLATION: WebSocket message routing expects handle_message() "
                    f"but AgentWebSocketBridge doesn't provide it. Error: {e}. "
                    f"This breaks the message routing chain from WebSocket to agents."
                )
            else:
                # Some other AttributeError - re-raise for investigation
                raise

        except Exception as e:
            # Document any other integration failures
            self.fail(
                f"INTERFACE CONTRACT VIOLATION: Integration failure in WebSocket message routing. "
                f"Error: {e}. Type: {type(e).__name__}. "
                f"This prevents messages from flowing properly from WebSocket to agents."
            )

    def test_websocket_message_routing_expected_interface(self):
        """
        INTERFACE SPECIFICATION TEST: Document the expected interface contracts.

        This test documents what the interface contracts should look like when fixed,
        providing a specification for the resolution of Issue #1167.

        Expected Result: FAIL (documents current contract violations)
        Purpose: Specification for future interface implementation
        """
        # Document expected AgentWebSocketBridge interface
        expected_bridge_methods = [
            'handle_message',  # Missing method causing routing failure
            'notify_agent_started',  # Exists
            'notify_agent_thinking',  # Exists
            'notify_tool_executing',  # Exists
            'notify_tool_completed',  # Exists
            'notify_agent_completed'  # Exists
        ]

        # Check AgentWebSocketBridge interface
        bridge = create_agent_websocket_bridge()
        missing_methods = []

        for method in expected_bridge_methods:
            if not hasattr(bridge, method):
                missing_methods.append(method)

        # Document expected UserExecutionContext constructor signature
        try:
            # This should work - correct constructor
            UserExecutionContext(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
            correct_constructor = True
        except Exception:
            correct_constructor = False

        try:
            # This should fail - incorrect constructor with metadata
            UserExecutionContext(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id,
                metadata={'test': 'data'}
            )
            metadata_constructor_works = True
        except TypeError:
            metadata_constructor_works = False

        # Generate interface contract violation report
        violations = []

        if missing_methods:
            violations.append(f"AgentWebSocketBridge missing methods: {missing_methods}")

        if not correct_constructor:
            violations.append("UserExecutionContext correct constructor doesn't work")

        if metadata_constructor_works:
            violations.append("UserExecutionContext incorrectly accepts 'metadata' parameter")

        if violations:
            self.fail(
                f"INTERFACE CONTRACT VIOLATIONS DETECTED:\n" +
                "\n".join(f"- {v}" for v in violations) +
                f"\n\nThese violations prevent proper WebSocket message routing and agent integration, "
                f"blocking $500K+ ARR Golden Path functionality."
            )


if __name__ == '__main__':
    print("ISSUE #1167 INTERFACE CONTRACT TESTS - PHASE 1")
    print("=" * 60)
    print("MISSION: Prove the interface failures identified in Five Whys analysis")
    print("EXPECTED: All tests should FAIL until Issue #1167 is resolved")
    print("BUSINESS IMPACT: $500K+ ARR Golden Path WebSocket functionality")
    print("=" * 60)
    print("")
    print("TEST COVERAGE:")
    print("1. AgentWebSocketBridge missing handle_message() method")
    print("2. UserExecutionContext invalid 'metadata' parameter usage")
    print("3. WebSocket message routing integration interface mismatch")
    print("")
    print("RUN COMMAND: python tests/unified_test_runner.py --category unit --pattern test_issue_1167")
    print("")
    unittest.main()