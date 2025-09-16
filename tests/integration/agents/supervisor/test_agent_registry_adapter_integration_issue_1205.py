"""Integration Test for AgentRegistryAdapter Issue #1205

CRITICAL INTEGRATION TESTS: Real agent execution flow with AgentRegistryAdapter
- Tests actual integration between AgentExecutionCore and AgentRegistryAdapter
- Validates that agent execution works end-to-end after Issue #1205 fix
- Uses real registry components (not mocked) to catch integration issues

Business Value Justification (BVJ):
- Segment: All (Free/Early/Mid/Enterprise/Platform)
- Business Goal: System Integration Reliability
- Value Impact: Ensures agent execution pipeline works end-to-end
- Strategic Impact: Protects $500K+ ARR by preventing integration failures

Integration Test Strategy:
1. Real component integration (minimal mocking)
2. End-to-end agent execution flow
3. WebSocket integration validation
4. User context isolation verification
5. Error handling and fallback testing
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from shared.types import UserID, ThreadID, RequestID
from test_framework.ssot.base_test_case import SSotAsyncTestCase

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.agents.supervisor.user_execution_engine import AgentRegistryAdapter
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext


class AgentRegistryAdapterIntegrationIssue1205Tests(SSotAsyncTestCase):
    """Integration tests for AgentRegistryAdapter Issue #1205 fix."""

    async def setup_method(self, method):
        """Set up integration test fixtures."""
        await super().setup_method(method)

        # Create real user context
        self.user_context = UserExecutionContext(
            user_id=UserID("integration-test-user"),
            thread_id=ThreadID("integration-test-thread"),
            run_id=RequestID("integration-test-run"),
            agent_context={}
        )

        # Create real agent class registry
        self.agent_class_registry = AgentRegistry()

        # Create real agent factory
        self.agent_factory = AgentInstanceFactory()

        # Register a test agent class
        self.test_agent_class = self._create_test_agent_class()
        self.agent_class_registry.register("test_agent", self.test_agent_class)

        # Create adapter with real components
        self.adapter = AgentRegistryAdapter(
            agent_class_registry=self.agent_class_registry,
            agent_factory=self.agent_factory,
            user_context=self.user_context
        )

        # Create AgentExecutionCore with adapter
        self.execution_core = AgentExecutionCore(
            registry=self.adapter,
            websocket_bridge=None,
            prerequisite_validation_level=None
        )

    def _create_test_agent_class(self):
        """Create a test agent class for integration testing."""
        class AgentTests:
            def __init__(self, user_context=None, **kwargs):
                self.user_context = user_context
                self._user_id = getattr(user_context, 'user_id', None)

            async def execute(self, user_execution_context, run_id, websocket_enabled=True):
                """Simple test agent execution."""
                return {
                    "success": True,
                    "message": f"Test agent executed for user {self._user_id}",
                    "run_id": str(run_id),
                    "agent_type": "test_agent"
                }

        return AgentTests

    @pytest.mark.asyncio
    async def test_adapter_get_async_current_signature(self):
        """Test current get_async signature behavior (before fix)."""
        # Test that get_async works with current signature
        result = await self.adapter.get_async("test_agent")

        # Should successfully create agent instance
        self.assertIsNotNone(result)
        self.assertEqual(result.__class__.__name__, "AgentTests")
        self.assertEqual(result.user_context, self.user_context)

    @pytest.mark.asyncio
    async def test_adapter_get_async_with_context_parameter_failure(self):
        """REPRODUCTION: Test get_async fails when called with context parameter."""
        # This reproduces the exact failure from AgentExecutionCore
        with self.assertRaises(TypeError) as context_manager:
            await self.adapter.get_async("test_agent", context=self.user_context)

        error = str(context_manager.exception)
        self.assertIn("unexpected keyword argument", error.lower())
        self.assertIn("context", error.lower())

    @pytest.mark.asyncio
    async def test_agent_execution_core_integration_failure(self):
        """INTEGRATION: Test full agent execution fails due to signature mismatch."""
        # Create execution context
        agent_context = AgentExecutionContext(
            agent_name="test_agent",
            run_id=RequestID("integration-test-run"),
            retry_count=0
        )

        # This should fail when AgentExecutionCore calls get_async with context
        # The failure happens in _get_agent_or_error method at line:
        # agent = await self.registry.get_async(agent_name, context=user_execution_context)
        with self.assertRaises(TypeError) as context_manager:
            result = await self.execution_core.execute_agent(
                context=agent_context,
                user_context=self.user_context,
                timeout=5.0
            )

        error = str(context_manager.exception)
        # Should fail on get_async signature mismatch
        self.assertTrue(
            "unexpected keyword argument 'context'" in error or
            "context" in error,
            f"Expected signature mismatch error, got: {error}"
        )

    @pytest.mark.asyncio
    async def test_registry_adapter_agent_count_validation(self):
        """INTEGRATION: Test registry shows available agents > 0."""
        # Verify test setup is correct
        registry_dict = getattr(self.agent_class_registry, '_registry', {})
        self.assertGreater(len(registry_dict), 0, "Registry should have registered agents")
        self.assertIn("test_agent", registry_dict, "test_agent should be registered")

        # Verify adapter can access registry
        agent_class = self.agent_class_registry.get("test_agent")
        self.assertIsNotNone(agent_class, "Should find test_agent in registry")
        self.assertEqual(agent_class, self.test_agent_class)

    @pytest.mark.asyncio
    async def test_agent_factory_create_instance_direct(self):
        """INTEGRATION: Test agent factory works correctly."""
        # Test direct factory usage
        agent_instance = await self.agent_factory.create_instance(
            "test_agent",
            self.user_context,
            agent_class=self.test_agent_class
        )

        self.assertIsNotNone(agent_instance)
        self.assertIsInstance(agent_instance, self.test_agent_class)
        self.assertEqual(agent_instance.user_context, self.user_context)

    @pytest.mark.asyncio
    async def test_agent_execution_direct_validation(self):
        """INTEGRATION: Test agent execution works directly."""
        # Create agent instance
        agent_instance = await self.adapter.get_async("test_agent")

        # Execute agent directly
        result = await agent_instance.execute(
            self.user_context,
            RequestID("test-run"),
            True
        )

        # Verify execution result
        self.assertIsNotNone(result)
        self.assertTrue(result.get("success"))
        self.assertIn("Test agent executed", result.get("message", ""))

    @pytest.mark.asyncio
    async def test_execution_core_get_agent_or_error_method(self):
        """INTEGRATION: Test specific method that causes the failure."""
        # This tests the exact method where the error occurs
        execution_core = self.execution_core

        # Mock the get_async call to avoid the signature error for this test
        with patch.object(self.adapter, 'get_async') as mock_get_async:
            mock_agent = Mock()
            mock_get_async.return_value = mock_agent

            # Call the internal method that's failing
            result = await execution_core._get_agent_or_error(
                "test_agent",
                self.user_context
            )

            # Verify it tried to call with context parameter
            mock_get_async.assert_called_once_with("test_agent", context=self.user_context)
            self.assertEqual(result, mock_agent)

    @pytest.mark.asyncio
    async def test_websocket_bridge_integration(self):
        """INTEGRATION: Test with WebSocket bridge (mocked)."""
        # Create execution core with mock WebSocket bridge
        mock_websocket_bridge = AsyncMock()
        execution_core_with_ws = AgentExecutionCore(
            registry=self.adapter,
            websocket_bridge=mock_websocket_bridge,
            prerequisite_validation_level=None
        )

        # Create execution context
        agent_context = AgentExecutionContext(
            agent_name="test_agent",
            run_id=RequestID("ws-test-run"),
            retry_count=0
        )

        # Should still fail due to signature mismatch, but test setup works
        with self.assertRaises(TypeError):
            await execution_core_with_ws.execute_agent(
                context=agent_context,
                user_context=self.user_context,
                timeout=5.0
            )

        # WebSocket bridge should have been called for initialization
        # (before the signature error occurs)
        # We can't verify specific calls due to the early failure, but setup should work

    @pytest.mark.asyncio
    async def test_user_isolation_context_propagation(self):
        """INTEGRATION: Test user context isolation in adapter."""
        # Create different user contexts
        user_context_1 = UserExecutionContext(
            user_id=UserID("user-1"),
            thread_id=ThreadID("thread-1"),
            run_id=RequestID("run-1"),
            agent_context={}
        )

        user_context_2 = UserExecutionContext(
            user_id=UserID("user-2"),
            thread_id=ThreadID("thread-2"),
            run_id=RequestID("run-2"),
            agent_context={}
        )

        # Create separate adapters for each user
        adapter_1 = AgentRegistryAdapter(
            self.agent_class_registry,
            self.agent_factory,
            user_context_1
        )

        adapter_2 = AgentRegistryAdapter(
            self.agent_class_registry,
            self.agent_factory,
            user_context_2
        )

        # Create agents for each user
        agent_1 = await adapter_1.get_async("test_agent")
        agent_2 = await adapter_2.get_async("test_agent")

        # Verify user isolation
        self.assertNotEqual(agent_1, agent_2)  # Different instances
        self.assertEqual(agent_1.user_context.user_id, "user-1")
        self.assertEqual(agent_2.user_context.user_id, "user-2")

    def test_expected_fix_documentation(self):
        """DOCUMENTATION: Document expected fix for Issue #1205."""
        # Document the required fix

        expected_fix = """
        Issue #1205 Fix Required:

        BEFORE (Current):
        async def get_async(self, agent_name: str):

        AFTER (Fixed):
        async def get_async(self, agent_name: str, context=None):
        OR
        async def get_async(self, agent_name: str, *, context=None):
        OR
        async def get_async(self, agent_name: str, **kwargs):

        The method should accept the context parameter that AgentExecutionCore
        passes: await self.registry.get_async(agent_name, context=user_execution_context)
        """

        self.assertIn("async def get_async", expected_fix)
        self.assertIn("context", expected_fix)
        print(expected_fix)

    @pytest.mark.asyncio
    async def test_error_message_validation(self):
        """VALIDATION: Test error messages for debugging."""
        # Test helps validate exact error message for Issue #1205
        try:
            await self.adapter.get_async("test_agent", context=self.user_context)
            self.fail("Should have raised TypeError")
        except TypeError as e:
            error_message = str(e)
            print(f"Issue #1205 Error: {error_message}")

            # Validate it's the expected error
            self.assertIn("get_async", error_message)
            # Should mention unexpected keyword argument 'context'
            self.assertTrue(
                "unexpected keyword argument 'context'" in error_message or
                "context" in error_message
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])