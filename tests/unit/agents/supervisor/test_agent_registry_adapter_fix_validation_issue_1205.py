"""Validation Tests for AgentRegistryAdapter Issue #1205 Fix

POST-FIX VALIDATION TESTS: Ensure Issue #1205 fix works correctly
- Tests that get_async method accepts context parameter
- Validates that AgentExecutionCore integration works after fix
- Ensures no regression in existing functionality
- Tests both with and without context parameter for backward compatibility

Business Value Justification (BVJ):
- Segment: All (Free/Early/Mid/Enterprise/Platform)
- Business Goal: Fix Validation & Regression Prevention
- Value Impact: Ensures fix works correctly and doesn't break existing code
- Strategic Impact: Protects $500K+ ARR by ensuring stable agent execution after fix

Validation Strategy:
1. Method signature validation
2. Forward compatibility testing (with context)
3. Backward compatibility testing (without context)
4. Integration validation with AgentExecutionCore
5. Error handling and edge case validation
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
import inspect

from shared.types import UserID, ThreadID, RequestID
from test_framework.ssot.base_test_case import SSotAsyncTestCase

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.agents.supervisor.user_execution_engine import AgentRegistryAdapter
from netra_backend.app.services.user_execution_context import UserExecutionContext


class AgentRegistryAdapterFixValidationIssue1205Tests(SSotAsyncTestCase):
    """Validation tests for Issue #1205 fix."""

    async def setup_method(self, method):
        """Set up validation test fixtures."""
        await super().setup_method(method)

        # Create test user context
        self.user_context = UserExecutionContext(
            user_id=UserID("validation-test-user"),
            thread_id=ThreadID("validation-test-thread"),
            run_id=RequestID("validation-test-run"),
            agent_context={}
        )

        # Create mock dependencies
        self.mock_agent_class_registry = Mock()
        self.mock_agent_factory = AsyncMock()

        # Create adapter instance
        self.adapter = AgentRegistryAdapter(
            agent_class_registry=self.mock_agent_class_registry,
            agent_factory=self.mock_agent_factory,
            user_context=self.user_context
        )

        # Setup mock returns
        self.mock_agent_class = Mock()
        self.mock_agent_instance = Mock()
        self.mock_agent_class_registry.get.return_value = self.mock_agent_class
        self.mock_agent_factory.create_instance.return_value = self.mock_agent_instance

    def test_get_async_method_signature_validation(self):
        """VALIDATION: Test that get_async method has correct signature after fix."""
        # Get method signature
        method = getattr(self.adapter, 'get_async')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        print(f"Post-fix get_async signature: {sig}")

        # Required parameters
        self.assertIn('agent_name', params, "get_async must have agent_name parameter")

        # Check for context parameter support
        has_context_param = 'context' in params
        has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

        # After fix, should support context either via explicit parameter or **kwargs
        self.assertTrue(
            has_context_param or has_kwargs,
            f"get_async should accept context parameter. Current signature: {sig}"
        )

        if has_context_param:
            context_param = sig.parameters['context']
            # Context should be optional (have default value)
            self.assertIsNotNone(
                context_param.default,
                "context parameter should be optional with default value"
            )

    @pytest.mark.asyncio
    async def test_get_async_with_context_parameter_success(self):
        """VALIDATION: Test get_async works with context parameter (main fix)."""
        # This is the core test - should work after Issue #1205 fix
        result = await self.adapter.get_async("test_agent", context=self.user_context)

        # Should successfully return agent instance
        self.assertIsNotNone(result)
        self.assertEqual(result, self.mock_agent_instance)

        # Verify factory was called correctly
        self.mock_agent_factory.create_instance.assert_called_once_with(
            "test_agent",
            self.user_context,
            agent_class=self.mock_agent_class
        )

    @pytest.mark.asyncio
    async def test_get_async_backward_compatibility(self):
        """VALIDATION: Test get_async still works without context parameter."""
        # Ensure existing code that doesn't pass context still works
        result = await self.adapter.get_async("test_agent")

        # Should successfully return agent instance
        self.assertIsNotNone(result)
        self.assertEqual(result, self.mock_agent_instance)

        # Verify factory was called correctly
        self.mock_agent_factory.create_instance.assert_called_once_with(
            "test_agent",
            self.user_context,
            agent_class=self.mock_agent_class
        )

    @pytest.mark.asyncio
    async def test_get_async_with_none_context(self):
        """VALIDATION: Test get_async works with context=None."""
        # Test explicit None context
        result = await self.adapter.get_async("test_agent", context=None)

        # Should successfully return agent instance
        self.assertIsNotNone(result)
        self.assertEqual(result, self.mock_agent_instance)

    @pytest.mark.asyncio
    async def test_get_async_with_different_context(self):
        """VALIDATION: Test get_async works with different context object."""
        # Create different context
        different_context = UserExecutionContext(
            user_id=UserID("different-user"),
            thread_id=ThreadID("different-thread"),
            run_id=RequestID("different-run"),
            agent_context={}
        )

        # Test with different context
        result = await self.adapter.get_async("test_agent", context=different_context)

        # Should still work (adapter uses its own internal context)
        self.assertIsNotNone(result)
        self.assertEqual(result, self.mock_agent_instance)

        # Should still use adapter's internal context, not the passed one
        self.mock_agent_factory.create_instance.assert_called_once_with(
            "test_agent",
            self.user_context,  # Adapter's internal context
            agent_class=self.mock_agent_class
        )

    @pytest.mark.asyncio
    async def test_agent_execution_core_integration_success(self):
        """VALIDATION: Test AgentExecutionCore integration works after fix."""
        # Create AgentExecutionCore with adapter
        execution_core = AgentExecutionCore(
            registry=self.adapter,
            websocket_bridge=None,
            prerequisite_validation_level=None
        )

        # Mock successful agent execution
        mock_agent = AsyncMock()
        mock_agent.execute.return_value = {
            "success": True,
            "message": "Agent executed successfully"
        }

        # Mock the adapter to return our mock agent
        with patch.object(self.adapter, 'get_async', return_value=mock_agent) as mock_get_async:
            # Create execution context
            agent_context = AgentExecutionContext(
                agent_name="test_agent",
                run_id=RequestID("validation-test-run"),
                retry_count=0
            )

            # Execute agent - should work after fix
            result = await execution_core.execute_agent(
                context=agent_context,
                user_context=self.user_context,
                timeout=5.0
            )

            # Verify success
            self.assertIsNotNone(result)
            self.assertTrue(result.success)

            # Verify get_async was called with context parameter
            mock_get_async.assert_called_with("test_agent", context=self.user_context)

    @pytest.mark.asyncio
    async def test_get_async_error_handling(self):
        """VALIDATION: Test error handling in get_async method."""
        # Test agent not found
        self.mock_agent_class_registry.get.return_value = None

        result = await self.adapter.get_async("nonexistent_agent", context=self.user_context)

        # Should return None for nonexistent agent
        self.assertIsNone(result)

        # Test factory error
        self.mock_agent_class_registry.get.return_value = self.mock_agent_class
        self.mock_agent_factory.create_instance.side_effect = Exception("Factory error")

        result = await self.adapter.get_async("test_agent", context=self.user_context)

        # Should return None on factory error
        self.assertIsNone(result)

    @pytest.mark.asyncio
    async def test_multiple_context_calls(self):
        """VALIDATION: Test multiple calls with different contexts."""
        # Test multiple calls don't interfere with each other
        context1 = UserExecutionContext(
            user_id=UserID("user-1"),
            thread_id=ThreadID("thread-1"),
            run_id=RequestID("run-1"),
            agent_context={}
        )

        context2 = UserExecutionContext(
            user_id=UserID("user-2"),
            thread_id=ThreadID("thread-2"),
            run_id=RequestID("run-2"),
            agent_context={}
        )

        # Make multiple calls
        result1 = await self.adapter.get_async("test_agent", context=context1)
        result2 = await self.adapter.get_async("test_agent", context=context2)
        result3 = await self.adapter.get_async("test_agent")  # No context

        # All should succeed
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
        self.assertIsNotNone(result3)

        # Verify factory was called correctly each time
        self.assertEqual(self.mock_agent_factory.create_instance.call_count, 3)

    @pytest.mark.asyncio
    async def test_signature_compatibility_with_original_interface(self):
        """VALIDATION: Test signature is compatible with expected registry interface."""
        # Test that adapter can be used as a registry in AgentExecutionCore

        # Create a function that expects registry interface
        async def use_registry_interface(registry, agent_name, user_ctx):
            # This simulates how AgentExecutionCore uses the registry
            return await registry.get_async(agent_name, context=user_ctx)

        # Should work with our adapter after fix
        result = await use_registry_interface(self.adapter, "test_agent", self.user_context)

        self.assertIsNotNone(result)
        self.assertEqual(result, self.mock_agent_instance)

    def test_fix_implementation_documentation(self):
        """VALIDATION: Document the actual fix implementation."""
        # This test documents what the fix should look like

        method = getattr(self.adapter, 'get_async')
        sig = inspect.signature(method)

        fix_documentation = f"""
        Issue #1205 Fix Implementation:

        Original signature: async def get_async(self, agent_name: str)
        Fixed signature: {sig}

        The fix should:
        1. Accept context parameter (either positional or keyword-only)
        2. Make context parameter optional (default=None)
        3. Maintain backward compatibility
        4. Work with AgentExecutionCore call: get_async(agent_name, context=user_context)

        Implementation options:
        - async def get_async(self, agent_name: str, context=None)
        - async def get_async(self, agent_name: str, *, context=None)
        - async def get_async(self, agent_name: str, **kwargs)
        """

        print(fix_documentation)

        # Validate the fix exists
        params = list(sig.parameters.keys())
        has_context = 'context' in params
        has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

        self.assertTrue(
            has_context or has_kwargs,
            f"Fix not implemented: {sig} should accept context parameter"
        )

    @pytest.mark.asyncio
    async def test_performance_impact_validation(self):
        """VALIDATION: Ensure fix doesn't impact performance."""
        import time

        # Measure execution time
        start_time = time.time()

        # Execute multiple times
        for i in range(10):
            await self.adapter.get_async(f"test_agent_{i}", context=self.user_context)

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete reasonably fast (arbitrary threshold)
        self.assertLess(execution_time, 1.0, "Fix should not significantly impact performance")

        print(f"Performance test: 10 calls took {execution_time:.3f} seconds")

    @pytest.mark.asyncio
    async def test_concurrent_context_calls(self):
        """VALIDATION: Test concurrent calls with different contexts work correctly."""
        # Test concurrent execution doesn't cause issues

        contexts = [
            UserExecutionContext(
                user_id=UserID(f"user-{i}"),
                thread_id=ThreadID(f"thread-{i}"),
                run_id=RequestID(f"run-{i}"),
                agent_context={}
            )
            for i in range(5)
        ]

        # Execute concurrently
        tasks = [
            self.adapter.get_async(f"agent_{i}", context=ctx)
            for i, ctx in enumerate(contexts)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        for i, result in enumerate(results):
            self.assertIsNotNone(result, f"Concurrent call {i} should succeed")
            self.assertNotIsInstance(result, Exception, f"Call {i} should not raise exception: {result}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])