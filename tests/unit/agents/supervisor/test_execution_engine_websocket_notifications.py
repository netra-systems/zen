"""Test Case 1: Unit Test for Agent Execution Core WebSocket Notifications

Test Plan for Issue #1028: Missing WebSocket completion notifications in agent execution success path

This test validates that notify_agent_completed() is properly called during successful agent execution.
Expected: This test should FAIL initially to prove the bug exists.

AGENT_SESSION_ID = agent-session-2025-01-14-1524
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestExecutionEngineWebSocketNotifications(SSotAsyncTestCase):
    """Test WebSocket notification behavior in agent execution success path."""

    async def asyncSetUp(self):
        """Set up test fixtures with mocked dependencies."""
        await super().asyncSetUp()

        # Create test context
        self.user_context = UserExecutionContext(
            user_id="test_user_12345",
            operation_name="test_agent_execution",
            correlation_id=str(uuid4())
        )

        self.agent_context = AgentExecutionContext(
            agent_name="test_agent",
            thread_id="thread_123",
            user_id="test_user_12345",
            run_id="run_456",
            metadata={"message": "Test message"}
        )

        # Mock WebSocket bridge with notify_agent_completed
        self.mock_websocket_bridge = AsyncMock()
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock(return_value=True)

        # Mock agent registry
        self.mock_agent_registry = AsyncMock()

        # Mock agent execution result (success case)
        self.success_result = AgentExecutionResult(
            success=True,
            data={"response": "Test response"},
            duration=1.5,
            error=None
        )

        # Mock agent instance that returns successful result
        self.mock_agent_instance = AsyncMock()
        self.mock_agent_instance.execute = AsyncMock(return_value=self.success_result)

        # Mock agent registry to return our mock agent
        self.mock_agent_registry.get_async = AsyncMock(return_value=self.mock_agent_instance)

    async def test_notify_agent_completed_called_on_success(self):
        """Test that notify_agent_completed is called when agent execution succeeds.

        Issue #1028: This test should FAIL initially to prove the bug exists.
        Expected: notify_agent_completed should be called once with success=True
        Actual: May not be called at all in success path
        """
        # Create AgentExecutionCore with mocked dependencies
        execution_core = AgentExecutionCore(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge
        )

        # Execute the agent
        result = await execution_core.execute_agent(
            context=self.agent_context,
            user_context=self.user_context
        )

        # Verify the execution was successful
        self.assertTrue(result.success, "Agent execution should have succeeded")
        self.assertEqual(result.data, {"response": "Test response"})

        # CRITICAL TEST: Verify notify_agent_completed was called for success case
        # This is the bug - this call should happen but may be missing
        self.mock_websocket_bridge.notify_agent_completed.assert_called_once()

        # Verify the call was made with correct parameters
        call_args = self.mock_websocket_bridge.notify_agent_completed.call_args
        self.assertIsNotNone(call_args, "notify_agent_completed should have been called")

        # Check that the call includes success indicators
        if call_args and call_args[1]:  # If keyword arguments exist
            kwargs = call_args[1]
            # Should include run_id, agent_name, and success result
            self.assertIn('run_id', kwargs)
            self.assertIn('agent_name', kwargs)
            self.assertEqual(kwargs['agent_name'], 'test_agent')
            self.assertIn('result', kwargs)

            result_data = kwargs['result']
            if isinstance(result_data, dict):
                self.assertTrue(result_data.get('success', False),
                               "Result should indicate success")

    async def test_notify_agent_completed_called_on_failure(self):
        """Test that notify_agent_completed is called when agent execution fails.

        This serves as a control test - failure path should work correctly.
        """
        # Create failure result
        failure_result = AgentExecutionResult(
            success=False,
            data=None,
            duration=0.5,
            error="Test error"
        )

        # Mock agent to return failure
        self.mock_agent_instance.execute = AsyncMock(return_value=failure_result)

        # Create AgentExecutionCore with mocked dependencies
        execution_core = AgentExecutionCore(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge
        )

        # Execute the agent
        result = await execution_core.execute_agent(
            context=self.agent_context,
            user_context=self.user_context
        )

        # Verify the execution failed as expected
        self.assertFalse(result.success, "Agent execution should have failed")
        self.assertEqual(result.error, "Test error")

        # Verify notify_agent_completed was called for failure case
        self.mock_websocket_bridge.notify_agent_completed.assert_called_once()

        # Verify the call indicates failure
        call_args = self.mock_websocket_bridge.notify_agent_completed.call_args
        if call_args and call_args[1]:
            kwargs = call_args[1]
            result_data = kwargs.get('result', {})
            if isinstance(result_data, dict):
                self.assertFalse(result_data.get('success', True),
                                "Result should indicate failure")

    async def test_websocket_bridge_none_handling(self):
        """Test behavior when websocket_bridge is None."""
        # Create AgentExecutionCore with None websocket_bridge
        execution_core = AgentExecutionCore(
            agent_registry=self.mock_agent_registry,
            websocket_bridge=None
        )

        # Execute the agent - should not crash
        result = await execution_core.execute_agent_isolated(
            context=self.agent_context,
            user_execution_context=self.user_context
        )

        # Verify execution still works
        self.assertTrue(result.success, "Agent execution should succeed even without WebSocket bridge")

    async def test_notify_agent_completed_exception_handling(self):
        """Test that notify_agent_completed exceptions don't break execution."""
        # Mock notify_agent_completed to raise exception
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock(
            side_effect=Exception("WebSocket notification failed")
        )

        # Create AgentExecutionCore
        execution_core = AgentExecutionCore(
            agent_registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge
        )

        # Execute the agent - should handle the exception gracefully
        result = await execution_core.execute_agent_isolated(
            context=self.agent_context,
            user_execution_context=self.user_context
        )

        # Verify execution still succeeds despite notification failure
        self.assertTrue(result.success, "Agent execution should succeed despite WebSocket notification failure")

        # Verify the call was attempted
        self.mock_websocket_bridge.notify_agent_completed.assert_called_once()

    def test_bug_reproduction_summary(self):
        """Document the expected bug behavior for Issue #1028."""
        bug_description = """
        Issue #1028: Missing WebSocket completion notifications in agent execution success path

        Expected Behavior:
        - Agent executes successfully
        - notify_agent_completed() is called with success=True
        - WebSocket event 'agent_completed' is sent to frontend
        - User sees completion notification

        Actual Bug Behavior:
        - Agent executes successfully
        - notify_agent_completed() may NOT be called in success path
        - WebSocket event 'agent_completed' is missing
        - User does not see completion notification

        Root Cause:
        - AgentExecutionCore.execute_agent_isolated() has comment saying
          "agent_completed event is automatically sent by agent tracker"
        - But this automatic sending may not be working
        - Manual call to notify_agent_completed() is missing in success path
        - Failure path has manual call (lines 745-749) but success path does not

        Business Impact:
        - Users don't know when agent execution completes successfully
        - Frontend may show perpetual "loading" state
        - Poor user experience for 90% of platform value (chat functionality)
        """

        # This test documents the issue - it will pass regardless
        self.assertTrue(True, "Bug documentation complete")


if __name__ == "__main__":
    # Run the specific test that should fail
    import unittest

    # Create test suite with just the critical test
    suite = unittest.TestSuite()
    suite.addTest(TestExecutionEngineWebSocketNotifications('test_notify_agent_completed_called_on_success'))

    # Run the test
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Report results
    if result.failures:
        print("\n=== TEST FAILED AS EXPECTED (PROVING BUG EXISTS) ===")
        for test, failure in result.failures:
            print(f"Failed Test: {test}")
            print(f"Failure: {failure}")
    elif result.errors:
        print("\n=== TEST ERROR (UNEXPECTED) ===")
        for test, error in result.errors:
            print(f"Error Test: {test}")
            print(f"Error: {error}")
    else:
        print("\n=== TEST PASSED (BUG MAY BE FIXED OR TEST NEEDS ADJUSTMENT) ===")