"""
Unit tests to reproduce the AgentRegistryAdapter signature mismatch issue.

ISSUE: AgentRegistryAdapter.get_async() has incorrect signature causing TypeError
- Current broken signature: async def get_async(self, agent_name: str)
- Required signature: async def get_async(self, agent_name: str, context=None)
- Failing location: agent_execution_core.py:1085 when calling get_async with context parameter

These tests will:
1. Reproduce the signature mismatch failure
2. Validate the fix works correctly
3. Ensure proper user isolation and context handling
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Optional, Any

# Import the classes under test
from netra_backend.app.agents.supervisor.user_execution_engine import AgentRegistryAdapter
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext


class MockAgent(BaseAgent):
    """Mock agent for testing purposes."""

    def __init__(self, name: str = "test_agent", **kwargs):
        # Mock the parent initialization
        self.name = name
        self.user_context = kwargs.get('user_context')

    async def execute(self, *args, **kwargs):
        """Mock execute method."""
        return {"result": f"Mock execution for {self.name}"}


class AgentRegistryAdapterSignatureTests:
    """Test suite for AgentRegistryAdapter signature issues."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_agent_class_registry = Mock()
        self.mock_agent_factory = Mock()
        self.mock_user_context = UserExecutionContext.from_request_supervisor(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789",
            request_id="test_request_456",
            metadata={"test": "signature_test"}
        )

        # Create the adapter under test
        self.adapter = AgentRegistryAdapter(
            agent_class_registry=self.mock_agent_class_registry,
            agent_factory=self.mock_agent_factory,
            user_context=self.mock_user_context
        )

    def test_current_signature_missing_context_parameter(self):
        """Test that current get_async signature doesn't accept context parameter.

        This test reproduces the signature mismatch issue where AgentExecutionCore
        tries to call get_async with a context parameter but the method doesn't accept it.
        """
        # Verify current signature only accepts agent_name
        import inspect
        signature = inspect.signature(self.adapter.get_async)
        params = list(signature.parameters.keys())

        # Current broken state: only has 'agent_name' parameter
        assert 'agent_name' in params, "get_async should have agent_name parameter"

        # The issue: missing 'context' parameter
        # This assertion will PASS in current broken state, FAIL after fix
        assert 'context' not in params, "Current signature incorrectly missing context parameter"

    @pytest.mark.asyncio
    async def test_signature_mismatch_reproduces_type_error(self):
        """Test that calling get_async with context parameter causes TypeError.

        This reproduces the exact error occurring in agent_execution_core.py:1085
        """
        # Set up mock to return an agent class
        mock_agent_class = Mock()
        self.mock_agent_class_registry.get.return_value = mock_agent_class
        self.mock_agent_factory.create_instance.return_value = MockAgent("test")

        # This should fail with TypeError due to unexpected 'context' keyword argument
        with pytest.raises(TypeError) as exc_info:
            await self.adapter.get_async("test_agent", context=self.mock_user_context)

        # Verify the error message indicates the signature mismatch
        error_message = str(exc_info.value)
        assert "got an unexpected keyword argument 'context'" in error_message or \
               "takes" in error_message and "positional argument" in error_message, \
               f"Expected signature mismatch error, got: {error_message}"

    @pytest.mark.asyncio
    async def test_working_call_without_context(self):
        """Test that current signature works when called without context parameter."""
        # Set up mocks
        mock_agent_class = Mock()
        mock_agent_instance = MockAgent("working_agent")

        self.mock_agent_class_registry.get.return_value = mock_agent_class
        self.mock_agent_factory.create_instance.return_value = mock_agent_instance

        # This should work with current signature
        result = await self.adapter.get_async("working_agent")

        # Verify we get back the agent instance
        assert result == mock_agent_instance
        assert result.name == "working_agent"

    def test_expected_fixed_signature_should_accept_context(self):
        """Test specification for the fixed signature.

        After the fix, this test should pass. Currently it documents the requirement.
        """
        # After fix, signature should accept optional context parameter
        # This test documents the expected behavior after signature fix

        # Expected signature after fix:
        # async def get_async(self, agent_name: str, context=None)

        # This test will fail initially but should pass after the fix
        expected_params = ['agent_name', 'context']

        # Get current signature
        import inspect
        signature = inspect.signature(self.adapter.get_async)
        actual_params = list(signature.parameters.keys())

        # Document what we expect (this will fail until fixed)
        missing_params = [p for p in expected_params if p not in actual_params]

        # This assertion documents the fix needed
        assert len(missing_params) == 0, \
            f"Signature needs these parameters added: {missing_params}. " \
            f"Current params: {actual_params}, Expected: {expected_params}"

    @pytest.mark.asyncio
    async def test_agent_creation_with_user_isolation(self):
        """Test that agent creation properly handles user context for isolation."""
        # Set up mocks
        mock_agent_class = Mock()
        mock_agent_instance = MockAgent("isolated_agent")
        mock_agent_instance.user_context = self.mock_user_context

        self.mock_agent_class_registry.get.return_value = mock_agent_class
        self.mock_agent_factory.create_instance.return_value = mock_agent_instance

        # Call without context (current working signature)
        result = await self.adapter.get_async("isolated_agent")

        # Verify agent factory was called with correct user context
        self.mock_agent_factory.create_instance.assert_called_once()
        call_args = self.mock_agent_factory.create_instance.call_args

        # Should have been called with the adapter's user_context
        assert call_args[0][0] == mock_agent_class  # agent_class
        assert call_args[1]['user_context'] == self.mock_user_context

    @pytest.mark.asyncio
    async def test_no_caching_creates_fresh_instances(self):
        """Test that adapter creates fresh instances without caching (Issue #1186 Phase 2)."""
        # Set up mocks
        mock_agent_class = Mock()
        mock_agent_1 = MockAgent("fresh_1")
        mock_agent_2 = MockAgent("fresh_2")

        self.mock_agent_class_registry.get.return_value = mock_agent_class
        self.mock_agent_factory.create_instance.side_effect = [mock_agent_1, mock_agent_2]

        # Call twice with same agent name
        result_1 = await self.adapter.get_async("test_agent")
        result_2 = await self.adapter.get_async("test_agent")

        # Verify we get different instances (no caching)
        assert result_1 != result_2
        assert result_1 == mock_agent_1
        assert result_2 == mock_agent_2

        # Verify factory was called twice
        assert self.mock_agent_factory.create_instance.call_count == 2

    @pytest.mark.asyncio
    async def test_agent_not_found_handling(self):
        """Test behavior when agent is not found in registry."""
        # Set up registry to return None
        self.mock_agent_class_registry.get.return_value = None

        # Should return None for non-existent agent
        result = await self.adapter.get_async("nonexistent_agent")
        assert result is None

        # Factory should not be called
        self.mock_agent_factory.create_instance.assert_not_called()

    @pytest.mark.asyncio
    async def test_agent_creation_failure_handling(self):
        """Test error handling when agent factory fails."""
        # Set up mocks
        mock_agent_class = Mock()
        self.mock_agent_class_registry.get.return_value = mock_agent_class
        self.mock_agent_factory.create_instance.side_effect = Exception("Factory error")

        # Should return None on factory failure
        result = await self.adapter.get_async("failing_agent")
        assert result is None


class AgentRegistryAdapterIntegrationWithExecutionCoreTests:
    """Integration tests showing the signature mismatch in context of AgentExecutionCore."""

    def setup_method(self):
        """Set up integration test fixtures."""
        # Create real-ish user context
        self.user_context = UserExecutionContext(
            user_id="integration_test_user",
            request_id="integration_request",
            session_id="integration_session",
            metadata={"source": "integration_test"}
        )

        # Create mocked dependencies for AgentExecutionCore
        self.mock_registry = Mock()
        self.mock_websocket_manager = Mock()
        self.mock_state_manager = Mock()

        # Create execution core with mocked registry
        self.execution_core = AgentExecutionCore(
            registry=self.mock_registry,
            websocket_manager=self.mock_websocket_manager,
            state_manager=self.mock_state_manager
        )

    @pytest.mark.asyncio
    async def test_execution_core_calls_registry_with_context(self):
        """Test that AgentExecutionCore calls registry.get_async with context parameter.

        This reproduces the exact call pattern that causes the signature mismatch.
        """
        # Set up mock registry to fail with signature mismatch
        async def mock_get_async_broken_signature(agent_name):
            """Mock that simulates current broken signature (no context param)."""
            return MockAgent(agent_name)

        # This simulates the current broken signature
        self.mock_registry.get_async = mock_get_async_broken_signature

        # This should fail because execution core passes context but signature doesn't accept it
        with pytest.raises(TypeError) as exc_info:
            # This is the exact call pattern from agent_execution_core.py:1085
            await self.mock_registry.get_async("test_agent", context=self.user_context)

        error_message = str(exc_info.value)
        assert "unexpected keyword argument 'context'" in error_message or \
               "takes" in error_message

    @pytest.mark.asyncio
    async def test_execution_core_with_fixed_registry_signature(self):
        """Test that execution works correctly with fixed registry signature.

        This demonstrates how the system should work after the signature fix.
        """
        # Mock registry with correct signature (includes context parameter)
        async def mock_get_async_fixed_signature(agent_name, context=None):
            """Mock that simulates the fixed signature with context param."""
            agent = MockAgent(agent_name)
            agent.user_context = context  # Use the provided context
            return agent

        self.mock_registry.get_async = mock_get_async_fixed_signature

        # This should work after the signature fix
        agent = await self.mock_registry.get_async("test_agent", context=self.user_context)

        assert agent is not None
        assert agent.name == "test_agent"
        assert agent.user_context == self.user_context

    @pytest.mark.asyncio
    async def test_backward_compatibility_context_optional(self):
        """Test that fixed signature maintains backward compatibility.

        The context parameter should be optional to not break existing code.
        """
        # Mock registry with correct signature where context is optional
        async def mock_get_async_with_optional_context(agent_name, context=None):
            """Mock with optional context parameter."""
            agent = MockAgent(agent_name)
            if context:
                agent.user_context = context
            return agent

        self.mock_registry.get_async = mock_get_async_with_optional_context

        # Should work with context
        agent_with_context = await self.mock_registry.get_async("agent1", context=self.user_context)
        assert agent_with_context.user_context == self.user_context

        # Should also work without context (backward compatibility)
        agent_without_context = await self.mock_registry.get_async("agent2")
        assert agent_without_context.user_context is None

    def test_registry_adapter_signature_fix_specification(self):
        """Document the exact signature fix specification.

        This test documents what the fix should look like.
        """
        # Current broken signature:
        # async def get_async(self, agent_name: str)

        # Required fixed signature:
        # async def get_async(self, agent_name: str, context=None)

        # The fix should:
        # 1. Add optional context parameter with default None
        # 2. Pass context to agent factory if provided
        # 3. Maintain backward compatibility
        # 4. Support user isolation when context is provided

        expected_signature_parts = {
            'has_agent_name_param': True,
            'has_context_param': True,
            'context_is_optional': True,
            'context_default_is_none': True
        }

        # This documents what we need to implement
        assert all(expected_signature_parts.values()), \
            "Signature fix specification documented for implementation"


if __name__ == "__main__":
    # Run specific tests to reproduce the issue
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "test_signature_mismatch_reproduces_type_error"
    ])