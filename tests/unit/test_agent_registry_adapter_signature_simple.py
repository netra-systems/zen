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


class TestAgentRegistryAdapterSignatureMismatchSimple:
    """Simple focused test for the signature mismatch issue."""

    def setup_method(self):
        """Set up minimal test fixtures."""
        self.mock_registry = Mock()
        self.mock_factory = Mock()
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

    def test_current_broken_signature_lacks_context_parameter(self):
        """Test that current signature is missing the required context parameter."""
        signature = inspect.signature(self.adapter.get_async)
        params = list(signature.parameters.keys())

        # Current broken state - missing context parameter
        assert 'agent_name' in params
        assert 'context' not in params, "Current signature incorrectly missing context parameter"

        # This documents what we expect after the fix
        expected_params = ['agent_name', 'context']
        missing_params = [p for p in expected_params if p not in params]
        assert missing_params == ['context'], f"Missing required parameters for fix: {missing_params}"

    @pytest.mark.asyncio
    async def test_call_with_context_parameter_fails_with_type_error(self):
        """Test that calling get_async with context parameter fails due to signature mismatch."""
        # Set up mock to return something when called correctly
        mock_agent_class = Mock()
        mock_agent_instance = Mock()
        mock_agent_instance.name = "test_agent"

        self.mock_registry.get.return_value = mock_agent_class
        self.mock_factory.create_instance.return_value = mock_agent_instance

        # This call should fail with TypeError because context parameter is not accepted
        with pytest.raises(TypeError) as exc_info:
            await self.adapter.get_async("test_agent", context=self.user_context)

        # Verify it's specifically a signature mismatch error
        error_msg = str(exc_info.value)
        assert "unexpected keyword argument 'context'" in error_msg, \
            f"Expected signature error with 'context', got: {error_msg}"

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

        # Verify factory was called with user context from adapter constructor
        self.mock_factory.create_instance.assert_called_once()
        call_args = self.mock_factory.create_instance.call_args
        assert call_args[1]['user_context'] == self.user_context

    def test_signature_fix_specification(self):
        """Document the exact signature fix required."""
        # Current broken signature from the adapter
        current_signature = inspect.signature(self.adapter.get_async)

        # Expected signature after fix:
        # async def get_async(self, agent_name: str, context=None)

        fix_specification = {
            "current_signature": str(current_signature),
            "current_params": list(current_signature.parameters.keys()),
            "required_change": "Add 'context=None' parameter to get_async method",
            "new_signature": "async def get_async(self, agent_name: str, context=None)",
            "backward_compatibility": "context parameter must have default value None",
            "behavior": "When context provided, use it for agent creation; when None, use adapter's user_context"
        }

        # Document the specification
        assert fix_specification["current_params"] == ["agent_name"]
        assert "context" not in fix_specification["current_params"]
        assert fix_specification["required_change"] == "Add 'context=None' parameter to get_async method"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])