"""
Simple focused test to demonstrate the AgentRegistryAdapter signature mismatch issue.

This is a minimal, focused test that demonstrates the core issue without
complex setup or dependencies that might fail for other reasons.
"""

import pytest
import inspect
from unittest.mock import Mock, AsyncMock

from netra_backend.app.agents.supervisor.user_execution_engine import AgentRegistryAdapter
from netra_backend.app.services.user_execution_context import UserExecutionContext


class AgentRegistryAdapterSignatureMismatchSimpleTests:
    """Simple focused test for the signature mismatch issue."""

    def setup_method(self):
        """Set up minimal test fixtures."""
        self.mock_registry = Mock()
        self.mock_factory = Mock()
        # Make the factory method async to match the real implementation
        self.mock_factory.create_instance = AsyncMock()
        self.user_context = UserExecutionContext.from_request_supervisor(
            user_id="simple_test_user",
            thread_id="simple_thread",
            run_id="simple_run",
            metadata={"test": "simple_signature_test"}
        )

        self.adapter = AgentRegistryAdapter(
            agent_class_registry=self.mock_registry,
            agent_factory=self.mock_factory,
            user_context=self.user_context
        )

    def test_current_signature_has_required_parameters(self):
        """Test that current signature has all required parameters."""
        signature = inspect.signature(self.adapter.get_async)
        params = list(signature.parameters.keys())

        # Current working state - signature is correct
        assert 'agent_name' in params, "get_async should have agent_name parameter"
        assert 'context' in params, "get_async should have context parameter"

        # Verify complete signature is as expected
        expected_params = ['agent_name', 'context']
        assert all(param in params for param in expected_params), \
            f"Missing required parameters. Current: {params}, Expected: {expected_params}"

    @pytest.mark.asyncio
    async def test_call_with_context_parameter_works_correctly(self):
        """Test that calling get_async with context parameter works correctly."""
        # Set up mock to return something when called correctly
        mock_agent_class = Mock()
        mock_agent_instance = Mock()
        mock_agent_instance.name = "test_agent"

        self.mock_registry.get.return_value = mock_agent_class
        self.mock_factory.create_instance.return_value = mock_agent_instance

        # This call should work correctly with the fixed signature
        result = await self.adapter.get_async("test_agent", context=self.user_context)

        # Verify we get the expected result
        assert result == mock_agent_instance, "Should return the agent instance from factory"

        # Verify the factory was called with correct parameters
        self.mock_factory.create_instance.assert_called_once_with(
            "test_agent",
            self.user_context,  # The context parameter should be passed to factory
            agent_class=mock_agent_class
        )

    @pytest.mark.asyncio
    async def test_call_without_context_parameter_works(self):
        """Test that current signature works when called without context (backward compatibility)."""
        # Set up mocks
        mock_agent_class = Mock()
        mock_agent_instance = Mock()
        mock_agent_instance.name = "working_agent"

        self.mock_registry.get.return_value = mock_agent_class
        self.mock_factory.create_instance.return_value = mock_agent_instance

        # This should work with current signature
        result = await self.adapter.get_async("working_agent")

        # Verify we get the expected result
        assert result == mock_agent_instance
        assert result.name == "working_agent"

        # Verify factory was called with correct parameters
        self.mock_factory.create_instance.assert_called_once_with(
            "working_agent",
            self.user_context,  # Should use adapter's context as default
            agent_class=mock_agent_class
        )

    def test_signature_fix_verification(self):
        """Verify that the signature fix has been applied correctly."""
        # Current signature from the adapter (should be fixed now)
        current_signature = inspect.signature(self.adapter.get_async)

        # Expected signature is:
        # async def get_async(self, agent_name: str, context=None)

        fix_verification = {
            "current_signature": str(current_signature),
            "current_params": list(current_signature.parameters.keys()),
            "signature_status": "FIXED",
            "expected_signature": "async def get_async(self, agent_name: str, context=None)",
            "backward_compatibility": "context parameter has default value None",
            "behavior": "When context provided, use it for agent creation; when None, use adapter's user_context"
        }

        # Verify the fix is complete
        assert fix_verification["current_params"] == ["agent_name", "context"], \
            f"Expected both parameters, got: {fix_verification['current_params']}"
        assert "context" in fix_verification["current_params"], "context parameter should be present"

        # Verify context parameter has default value
        context_param = current_signature.parameters.get('context')
        assert context_param is not None, "context parameter should exist"
        assert context_param.default is None, "context parameter should have default value None"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])