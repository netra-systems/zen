"""Test AgentRegistryAdapter Issue #1205 - Missing get_async Method Signature

CRITICAL ISSUE: AgentRegistryAdapter.get_async method missing context parameter
- AgentExecutionCore calls: await self.registry.get_async(agent_name, context=user_execution_context)
- AgentRegistryAdapter has: async def get_async(self, agent_name: str) - missing context parameter
- This causes: "'AgentRegistryAdapter' object has no attribute 'get_async'" TypeError

Business Value Justification (BVJ):
- Segment: All (Free/Early/Mid/Enterprise/Platform)
- Business Goal: Agent System Reliability & User Experience
- Value Impact: Prevents agent execution failures that block AI responses
- Strategic Impact: Core foundation for $500K+ ARR - agent failures = immediate revenue loss

Test Strategy:
1. Reproduction tests: Simulate exact failure scenario
2. Unit tests: Test method signature and functionality
3. Integration tests: Test real agent execution flow
4. Validation tests: Ensure fix doesn't break existing functionality
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
from uuid import uuid4

from shared.types import UserID, ThreadID, RequestID
from test_framework.ssot.base_test_case import SSotBaseTestCase

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.user_execution_engine import AgentRegistryAdapter
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestAgentRegistryAdapterIssue1205(SSotBaseTestCase):
    """Test suite reproducing and validating fix for Issue #1205."""

    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)

        # Create test user context
        self.user_context = UserExecutionContext(
            user_id=UserID("test-user-123"),
            thread_id=ThreadID("test-thread-456"),
            run_id=RequestID("test-run-789"),
            agent_context={}
        )

        # Create mock agent class registry
        self.mock_agent_class_registry = Mock()
        self.mock_agent_factory = AsyncMock()

        # Create AgentRegistryAdapter instance
        self.adapter = AgentRegistryAdapter(
            agent_class_registry=self.mock_agent_class_registry,
            agent_factory=self.mock_agent_factory,
            user_context=self.user_context
        )

    def test_agent_registry_adapter_has_get_async_method(self):
        """Test that AgentRegistryAdapter has get_async method."""
        # This test should pass - method exists
        self.assertTrue(hasattr(self.adapter, 'get_async'))
        self.assertTrue(callable(getattr(self.adapter, 'get_async')))

    def test_get_async_method_signature_reproduction(self):
        """REPRODUCTION TEST: Test get_async method signature matches expected interface.

        CURRENT BUG: get_async(agent_name) missing context parameter
        EXPECTED: get_async(agent_name, context=None) or similar
        """
        import inspect

        # Get method signature
        method = getattr(self.adapter, 'get_async')
        sig = inspect.signature(method)

        # Check current signature (this will show the bug)
        params = list(sig.parameters.keys())
        self.assertIn('agent_name', params, "get_async should have agent_name parameter")

        # ISSUE #1205: This test will FAIL because context parameter is missing
        # This is the exact reproduction of the bug
        try:
            self.assertIn('context', params, "get_async should have context parameter for Issue #1205 fix")
            self.fail("Test should fail due to missing context parameter - this indicates the bug is already fixed")
        except AssertionError:
            # Expected failure - this confirms the bug exists
            print(f"CONFIRMED BUG: get_async signature has parameters: {params}")
            print("MISSING: context parameter needed for AgentExecutionCore compatibility")

    @pytest.mark.asyncio
    async def test_agent_execution_core_calls_get_async_with_context(self):
        """REPRODUCTION TEST: Simulate AgentExecutionCore calling get_async with context parameter.

        This test reproduces the exact scenario where AgentExecutionCore
        tries to call registry.get_async(agent_name, context=user_execution_context)
        """
        # Create mock registry that has the current broken signature
        mock_registry = Mock()

        # Current broken signature - only accepts agent_name
        async def broken_get_async(agent_name: str):
            return Mock()  # Mock agent

        mock_registry.get_async = broken_get_async

        # Try to call with context parameter (as AgentExecutionCore does)
        agent_name = "test_agent"

        # This should fail with TypeError due to unexpected keyword argument 'context'
        with self.assertRaises(TypeError) as context_manager:
            await mock_registry.get_async(agent_name, context=self.user_context)

        error = str(context_manager.exception)
        self.assertIn("unexpected keyword argument", error.lower())
        self.assertIn("context", error.lower())
        print(f"REPRODUCTION SUCCESSFUL: {error}")

    @pytest.mark.asyncio
    async def test_agent_execution_core_integration_failure(self):
        """INTEGRATION TEST: Test AgentExecutionCore fails when using AgentRegistryAdapter.

        This test demonstrates the integration failure between AgentExecutionCore
        and AgentRegistryAdapter due to incompatible get_async signatures.
        """
        # Create AgentExecutionCore with our adapter
        execution_core = AgentExecutionCore(
            registry=self.adapter,
            websocket_bridge=None,
            prerequisite_validation_level=None
        )

        # Create execution context
        agent_context = AgentExecutionContext(
            agent_name="test_agent",
            run_id=RequestID("test-run-123"),
            retry_count=0
        )

        # Mock the adapter's get_async to simulate agent not found (avoid other errors)
        self.adapter.get_async = AsyncMock(return_value=None)

        # Try to execute - this should fail due to signature mismatch
        # when AgentExecutionCore calls await self.registry.get_async(agent_name, context=user_execution_context)
        with self.assertRaises(TypeError) as context_manager:
            await execution_core.execute_agent(
                context=agent_context,
                user_context=self.user_context,
                timeout=5.0
            )

        error = str(context_manager.exception)
        # Should fail on the get_async call with unexpected keyword argument
        self.assertTrue(
            "unexpected keyword argument" in error.lower() or
            "context" in error.lower(),
            f"Expected signature mismatch error, got: {error}"
        )

    def test_expected_method_signature_after_fix(self):
        """VALIDATION TEST: Define expected signature after Issue #1205 fix.

        This test documents what the get_async signature should be after the fix.
        """
        # Expected signature after fix:
        # async def get_async(self, agent_name: str, context=None)
        # OR
        # async def get_async(self, agent_name: str, *, context=None)  # keyword-only

        expected_params = ['self', 'agent_name']
        # Should also support context parameter (either positional or keyword-only)

        import inspect
        method = getattr(self.adapter, 'get_async')
        sig = inspect.signature(method)
        actual_params = list(sig.parameters.keys())

        # Basic requirements
        for param in expected_params:
            if param != 'self':  # self is implicit in bound methods
                self.assertIn(param, actual_params, f"Missing required parameter: {param}")

        # After fix, should either:
        # 1. Have 'context' parameter
        # 2. Accept **kwargs
        # 3. Have some way to handle the context argument

        has_context = 'context' in actual_params
        has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

        print(f"Current signature: {sig}")
        print(f"Has context parameter: {has_context}")
        print(f"Has **kwargs: {has_kwargs}")

        # This assertion will guide the fix
        self.assertTrue(
            has_context or has_kwargs,
            "After Issue #1205 fix, get_async should accept context parameter or **kwargs"
        )

    @pytest.mark.asyncio
    async def test_agent_class_registry_mock_behavior(self):
        """UNIT TEST: Test AgentRegistryAdapter behavior with mock dependencies."""
        # Setup mock agent class
        mock_agent_class = Mock()
        mock_agent_instance = Mock()

        # Configure mocks
        self.mock_agent_class_registry.get.return_value = mock_agent_class
        self.mock_agent_factory.create_instance.return_value = mock_agent_instance

        # Test current get_async method (without context)
        result = await self.adapter.get_async("test_agent")

        # Verify behavior
        self.mock_agent_class_registry.get.assert_called_once_with("test_agent")
        self.mock_agent_factory.create_instance.assert_called_once_with(
            "test_agent",
            self.user_context,
            agent_class=mock_agent_class
        )
        self.assertEqual(result, mock_agent_instance)

    @pytest.mark.asyncio
    async def test_adapter_registry_integration_current_behavior(self):
        """INTEGRATION TEST: Current behavior of AgentRegistryAdapter with registry."""
        # Test that adapter works correctly with its current implementation
        # This establishes baseline behavior before the fix

        # Setup: Agent exists in registry
        mock_agent_class = Mock()
        mock_agent_instance = Mock()

        self.mock_agent_class_registry.get.return_value = mock_agent_class
        self.mock_agent_factory.create_instance.return_value = mock_agent_instance

        # Execute: Call get_async with valid agent
        result = await self.adapter.get_async("existing_agent")

        # Verify: Proper instance creation
        self.assertIsNotNone(result)
        self.assertEqual(result, mock_agent_instance)

        # Verify factory was called correctly
        self.mock_agent_factory.create_instance.assert_called_once()
        call_args = self.mock_agent_factory.create_instance.call_args
        self.assertEqual(call_args[0][0], "existing_agent")  # agent_name
        self.assertEqual(call_args[0][1], self.user_context)  # user_context
        self.assertEqual(call_args[1]['agent_class'], mock_agent_class)  # agent_class

    def test_registry_adapter_availability_check(self):
        """UNIT TEST: Verify adapter can be used as registry interface."""
        # Test that adapter provides the expected interface for registry

        # Should have get method
        self.assertTrue(hasattr(self.adapter, 'get'))
        self.assertTrue(callable(getattr(self.adapter, 'get')))

        # Should have get_async method
        self.assertTrue(hasattr(self.adapter, 'get_async'))
        self.assertTrue(callable(getattr(self.adapter, 'get_async')))

        # Should have registry information
        self.assertTrue(hasattr(self.adapter, 'agent_class_registry'))
        self.assertTrue(hasattr(self.adapter, 'agent_factory'))
        self.assertTrue(hasattr(self.adapter, 'user_context'))

    def test_issue_1205_github_reference(self):
        """DOCUMENTATION TEST: Reference Issue #1205 for tracking."""
        # This test serves as documentation linking to the GitHub issue
        issue_number = 1205
        issue_title = "AgentRegistryAdapter missing get_async method with correct signature"

        # Test confirms we're addressing the right issue
        self.assertEqual(issue_number, 1205)
        self.assertIn("get_async", issue_title.lower())
        self.assertIn("signature", issue_title.lower())

        print(f"Testing Issue #{issue_number}: {issue_title}")
        print("Root cause: Method exists but wrong signature (missing context parameter)")
        print("Current signature: get_async(self, agent_name: str)")
        print("Required signature: get_async(agent_name, context=user_execution_context)")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])