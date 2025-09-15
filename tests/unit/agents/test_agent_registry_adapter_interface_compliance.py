"""
Unit tests for Issue #1205 - AgentRegistryAdapter method signature mismatch.

These tests reproduce the bug where AgentRegistryAdapter.get_async() method
signature doesn't match the expected interface used by AgentExecutionCore.

EXPECTED BEHAVIOR: Tests should FAIL initially, demonstrating the interface violation.
After fix: Tests should PASS, confirming interface compliance.

Test Strategy:
1. Direct method signature validation
2. TypeError reproduction from production
3. Interface contract verification
"""

import pytest
import asyncio
import inspect
import unittest
from unittest.mock import Mock, AsyncMock
from typing import Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.user_execution_engine import AgentRegistryAdapter
from netra_backend.app.services.user_execution_context import UserExecutionContext


class AgentRegistryAdapterInterfaceComplianceTests(SSotAsyncTestCase, unittest.TestCase):
    """Test suite for AgentRegistryAdapter interface compliance validation."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Mock agent class registry
        self.mock_agent_class_registry = Mock()
        self.mock_agent_class_registry.get.return_value = Mock()  # Mock agent class

        # Mock agent factory
        self.mock_agent_factory = AsyncMock()
        self.mock_agent_factory.create_agent_async.return_value = Mock()  # Mock agent instance

        # Mock user context
        self.mock_user_context = Mock(spec=UserExecutionContext)
        self.mock_user_context.user_id = "test_user_123"

        # Create adapter instance
        self.adapter = AgentRegistryAdapter(
            agent_class_registry=self.mock_agent_class_registry,
            agent_factory=self.mock_agent_factory,
            user_context=self.mock_user_context
        )

    def test_get_async_method_signature_inspection(self):
        """Test that get_async method signature matches expected interface.

        ISSUE #1205: This test should FAIL initially because get_async() doesn't accept context parameter.
        AgentExecutionCore expects: get_async(agent_name, context=user_execution_context)
        Current signature: get_async(agent_name: str)
        """
        import inspect

        # Get method signature
        sig = inspect.signature(self.adapter.get_async)
        params = list(sig.parameters.keys())

        # Expected signature should include 'context' parameter
        expected_params = ['agent_name', 'context']

        # This assertion should FAIL initially - demonstrating the bug
        self.assertEqual(params, expected_params,
                        f"Method signature mismatch. Expected {expected_params}, got {params}")

        # Verify context parameter is optional (has default value)
        if 'context' in params:
            context_param = sig.parameters['context']
            self.assertTrue(context_param.default is not inspect.Parameter.empty,
                           "Context parameter should be optional with default value")

    async def test_direct_method_call_with_context_parameter(self):
        """Test direct method call with context parameter - should reproduce TypeError.

        ISSUE #1205: This test should FAIL initially with TypeError:
        "get_async() got an unexpected keyword argument 'context'"
        """
        agent_name = "test_agent"
        context = self.mock_user_context

        # This call should fail with TypeError initially
        try:
            result = await self.adapter.get_async(agent_name, context=context)
            # If we reach here after the fix, verify the result
            self.assertIsNotNone(result, "Should return agent instance when fixed")
        except TypeError as e:
            # This is expected initially - the bug we're reproducing
            self.assertIn("unexpected keyword argument 'context'", str(e),
                         f"Unexpected TypeError message: {e}")
            # Re-raise to make test fail as expected
            raise

    async def test_agent_execution_core_call_pattern_simulation(self):
        """Test the exact call pattern used by AgentExecutionCore.

        ISSUE #1205: Simulates the exact call that fails in production:
        agent = await self.registry.get_async(agent_name, context=user_execution_context)
        """
        agent_name = "supervisor_agent"
        user_execution_context = self.mock_user_context

        # Simulate AgentExecutionCore call pattern
        try:
            # This is the exact pattern from agent_execution_core.py line that fails
            agent = await self.adapter.get_async(agent_name, context=user_execution_context)

            # If fixed, verify proper behavior
            self.assertIsNotNone(agent, "Should return agent instance")

            # Verify factory was called with correct parameters
            self.mock_agent_factory.create_agent_async.assert_called()

        except TypeError as e:
            # Expected failure initially
            self.fail(f"Interface mismatch prevents AgentExecutionCore integration: {e}")

    def test_interface_contract_verification(self):
        """Verify that AgentRegistryAdapter implements expected registry interface.

        ISSUE #1205: Documents the expected interface contract for registry objects.
        """
        # Expected interface methods and signatures
        expected_interface = {
            'get_async': ['agent_name', 'context'],  # context should be optional
            'get': ['agent_name']  # synchronous version
        }

        for method_name, expected_params in expected_interface.items():
            # Verify method exists
            self.assertTrue(hasattr(self.adapter, method_name),
                           f"Missing required method: {method_name}")

            # Get method signature
            method = getattr(self.adapter, method_name)
            sig = inspect.signature(method)
            actual_params = list(sig.parameters.keys())

            # Skip 'self' parameter for instance methods
            if actual_params and actual_params[0] == 'self':
                actual_params = actual_params[1:]

            # This should pass after fix
            self.assertEqual(actual_params, expected_params,
                            f"Method {method_name} signature mismatch. "
                            f"Expected {expected_params}, got {actual_params}")

    async def test_backwards_compatibility_with_existing_calls(self):
        """Test that fixing get_async doesn't break existing usage patterns.

        Ensures that existing calls without context parameter still work.
        """
        agent_name = "test_agent"

        # Test call without context (existing pattern)
        try:
            result = await self.adapter.get_async(agent_name)
            self.assertIsNotNone(result, "Should work without context parameter")
        except Exception as e:
            self.fail(f"Backwards compatibility broken: {e}")

    def test_context_parameter_handling_edge_cases(self):
        """Test edge cases for context parameter handling."""
        import inspect

        # Skip this test if method doesn't have context parameter yet (before fix)
        sig = inspect.signature(self.adapter.get_async)
        if 'context' not in sig.parameters:
            self.skipTest("Context parameter not implemented yet - this is expected before fix")

        # Test with None context
        async def test_none_context():
            result = await self.adapter.get_async("test_agent", context=None)
            self.assertIsNotNone(result)

        # Test with valid context
        async def test_valid_context():
            result = await self.adapter.get_async("test_agent", context=self.mock_user_context)
            self.assertIsNotNone(result)

        # Run async tests
        asyncio.run(test_none_context())
        asyncio.run(test_valid_context())


if __name__ == '__main__':
    pytest.main([__file__, '-v'])