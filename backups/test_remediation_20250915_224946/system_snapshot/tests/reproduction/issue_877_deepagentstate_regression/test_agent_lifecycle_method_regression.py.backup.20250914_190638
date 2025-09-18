"""Test Issue #877: Agent Lifecycle Method Signature Regression

This test reproduces the regression where agent lifecycle methods still expect
DeepAgentState parameters instead of proper UserExecutionContext integration.

FOCUS AREAS:
- Method signature validation for proper state management
- Runtime behavior testing with actual method calls
- Integration between agent lifecycle and execution context

These tests will FAIL initially, proving the regression exists.
They should PASS after proper SSOT remediation.
"""

import inspect
from unittest.mock import Mock, AsyncMock
from typing import get_type_hints

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestAgentLifecycleMethodRegression(SSotBaseTestCase):
    """Test suite to validate agent lifecycle method signature regressions."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

    def test_pre_run_method_signature_uses_deepagentstate(self):
        """Test that _pre_run method signature still uses DeepAgentState.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: _pre_run method expects DeepAgentState parameter
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        except ImportError as e:
            self.fail(f"Cannot import AgentLifecycleMixin: {e}")

        # Get the _pre_run method
        pre_run_method = getattr(AgentLifecycleMixin, '_pre_run', None)
        if pre_run_method is None:
            self.fail("_pre_run method not found in AgentLifecycleMixin")

        # Inspect the method signature
        signature = inspect.signature(pre_run_method)

        # Check state parameter type annotation
        state_param = signature.parameters.get('state')
        if state_param is None:
            self.fail("'state' parameter not found in _pre_run method")

        # Check if annotation references DeepAgentState
        annotation = state_param.annotation
        annotation_str = str(annotation) if annotation != inspect.Parameter.empty else "None"

        if 'DeepAgentState' in annotation_str:
            self.fail(
                f"REGRESSION CONFIRMED: _pre_run method signature uses DeepAgentState\n"
                f"Method: AgentLifecycleMixin._pre_run\n"
                f"State parameter annotation: {annotation_str}\n"
                f"Full signature: {signature}\n"
                f"Expected: Should use UserExecutionContext or compatible type\n"
                f"Impact: Agent pre-execution using deprecated state pattern"
            )

        # If we reach here, the method signature was properly migrated
        self.assertTrue(True, "_pre_run method signature properly migrated")

    def test_post_run_method_signature_uses_deepagentstate(self):
        """Test that _post_run method signature still uses DeepAgentState.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: _post_run method expects DeepAgentState parameter
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        except ImportError as e:
            self.fail(f"Cannot import AgentLifecycleMixin: {e}")

        # Get the _post_run method
        post_run_method = getattr(AgentLifecycleMixin, '_post_run', None)
        if post_run_method is None:
            self.fail("_post_run method not found in AgentLifecycleMixin")

        # Inspect the method signature
        signature = inspect.signature(post_run_method)

        # Check state parameter type annotation
        state_param = signature.parameters.get('state')
        if state_param is None:
            self.fail("'state' parameter not found in _post_run method")

        # Check if annotation references DeepAgentState
        annotation = state_param.annotation
        annotation_str = str(annotation) if annotation != inspect.Parameter.empty else "None"

        if 'DeepAgentState' in annotation_str:
            self.fail(
                f"REGRESSION CONFIRMED: _post_run method signature uses DeepAgentState\n"
                f"Method: AgentLifecycleMixin._post_run\n"
                f"State parameter annotation: {annotation_str}\n"
                f"Full signature: {signature}\n"
                f"Expected: Should use UserExecutionContext or compatible type\n"
                f"Impact: Agent post-execution using deprecated state pattern"
            )

        # If we reach here, the method signature was properly migrated
        self.assertTrue(True, "_post_run method signature properly migrated")

    def test_execute_method_signature_uses_deepagentstate(self):
        """Test that execute method signature still uses DeepAgentState.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: execute method expects DeepAgentState parameter
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        except ImportError as e:
            self.fail(f"Cannot import AgentLifecycleMixin: {e}")

        # Get the execute method
        execute_method = getattr(AgentLifecycleMixin, 'execute', None)
        if execute_method is None:
            self.fail("execute method not found in AgentLifecycleMixin")

        # Inspect the method signature
        signature = inspect.signature(execute_method)

        # Check state parameter type annotation
        state_param = signature.parameters.get('state')
        if state_param is None:
            self.fail("'state' parameter not found in execute method")

        # Check if annotation references DeepAgentState
        annotation = state_param.annotation
        annotation_str = str(annotation) if annotation != inspect.Parameter.empty else "None"

        if 'DeepAgentState' in annotation_str:
            self.fail(
                f"REGRESSION CONFIRMED: execute method signature uses DeepAgentState\n"
                f"Method: AgentLifecycleMixin.execute\n"
                f"State parameter annotation: {annotation_str}\n"
                f"Full signature: {signature}\n"
                f"Expected: Should use UserExecutionContext or compatible type\n"
                f"Impact: Agent execution using deprecated state pattern"
            )

        # If we reach here, the method signature was properly migrated
        self.assertTrue(True, "execute method signature properly migrated")

    def test_check_entry_conditions_method_signature_uses_deepagentstate(self):
        """Test that check_entry_conditions method signature still uses DeepAgentState.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: check_entry_conditions method expects DeepAgentState parameter
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        except ImportError as e:
            self.fail(f"Cannot import AgentLifecycleMixin: {e}")

        # Get the check_entry_conditions method
        method = getattr(AgentLifecycleMixin, 'check_entry_conditions', None)
        if method is None:
            self.fail("check_entry_conditions method not found in AgentLifecycleMixin")

        # Inspect the method signature
        signature = inspect.signature(method)

        # Check state parameter type annotation
        state_param = signature.parameters.get('state')
        if state_param is None:
            self.fail("'state' parameter not found in check_entry_conditions method")

        # Check if annotation references DeepAgentState
        annotation = state_param.annotation
        annotation_str = str(annotation) if annotation != inspect.Parameter.empty else "None"

        if 'DeepAgentState' in annotation_str:
            self.fail(
                f"REGRESSION CONFIRMED: check_entry_conditions method signature uses DeepAgentState\n"
                f"Method: AgentLifecycleMixin.check_entry_conditions\n"
                f"State parameter annotation: {annotation_str}\n"
                f"Full signature: {signature}\n"
                f"Expected: Should use UserExecutionContext or compatible type\n"
                f"Impact: Agent entry condition checking using deprecated state pattern"
            )

        # If we reach here, the method signature was properly migrated
        self.assertTrue(True, "check_entry_conditions method signature properly migrated")

    def test_cleanup_method_signature_uses_deepagentstate(self):
        """Test that cleanup method signature still uses DeepAgentState.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: cleanup method expects DeepAgentState parameter
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        except ImportError as e:
            self.fail(f"Cannot import AgentLifecycleMixin: {e}")

        # Get the cleanup method
        cleanup_method = getattr(AgentLifecycleMixin, 'cleanup', None)
        if cleanup_method is None:
            self.fail("cleanup method not found in AgentLifecycleMixin")

        # Inspect the method signature
        signature = inspect.signature(cleanup_method)

        # Check state parameter type annotation
        state_param = signature.parameters.get('state')
        if state_param is None:
            self.fail("'state' parameter not found in cleanup method")

        # Check if annotation references DeepAgentState
        annotation = state_param.annotation
        annotation_str = str(annotation) if annotation != inspect.Parameter.empty else "None"

        if 'DeepAgentState' in annotation_str:
            self.fail(
                f"REGRESSION CONFIRMED: cleanup method signature uses DeepAgentState\n"
                f"Method: AgentLifecycleMixin.cleanup\n"
                f"State parameter annotation: {annotation_str}\n"
                f"Full signature: {signature}\n"
                f"Expected: Should use UserExecutionContext or compatible type\n"
                f"Impact: Agent cleanup using deprecated state pattern"
            )

        # If we reach here, the method signature was properly migrated
        self.assertTrue(True, "cleanup method signature properly migrated")


class TestAgentLifecycleRuntimeBehavior(SSotBaseTestCase):
    """Test suite to validate agent lifecycle runtime behavior with deprecated state."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

    async def test_agent_lifecycle_methods_accept_deepagentstate_at_runtime(self):
        """Test that agent lifecycle methods accept DeepAgentState objects at runtime.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: Methods should reject DeepAgentState and require UserExecutionContext
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
            from netra_backend.app.schemas.agent_models import DeepAgentState
        except ImportError as e:
            self.skip(f"Cannot import required classes: {e}")

        # Create a test agent class that uses the mixin
        class TestAgent(AgentLifecycleMixin):
            def __init__(self):
                self.name = "TestAgent"
                self.logger = Mock()
                self.start_time = 0.0
                self.end_time = 0.0
                self.context = Mock()

                # Mock WebSocket methods
                self.emit_agent_started = AsyncMock()
                self.emit_agent_completed = AsyncMock()
                self.emit_error = AsyncMock()

                # Mock lifecycle methods
                self.set_state = Mock()
                self._log_agent_start = Mock()
                self._log_agent_completion = Mock()

            async def execute(self, state, run_id, stream_updates):
                """Mock execute method."""
                pass

        # Create test agent instance
        agent = TestAgent()

        # Create DeepAgentState instance (deprecated pattern)
        deprecated_state = DeepAgentState(
            user_request="test request",
            user_id="test_user_123",
            run_id="test_run_456"
        )

        # Try to call methods with DeepAgentState
        run_id = "test_run_789"

        try:
            # Test _pre_run with DeepAgentState - this should fail in proper implementation
            result = await agent._pre_run(deprecated_state, run_id, True)

            # If this succeeds, it means the method still accepts DeepAgentState
            self.fail(
                f"REGRESSION CONFIRMED: _pre_run method accepts DeepAgentState at runtime\n"
                f"Method returned: {result}\n"
                f"State type: {type(deprecated_state)}\n"
                f"Expected: Method should reject DeepAgentState and require UserExecutionContext\n"
                f"Impact: Runtime acceptance of deprecated state creates vulnerability"
            )

        except TypeError as e:
            # Expected behavior - method should reject DeepAgentState
            if 'UserExecutionContext' in str(e) or 'DeepAgentState' in str(e):
                self.assertTrue(True, "Method properly rejects DeepAgentState")
            else:
                # Different error - might indicate other issues
                self.fail(f"Unexpected error when testing with DeepAgentState: {e}")

        except Exception as e:
            # Other exceptions might indicate the method still works with DeepAgentState
            if "Mock" in str(e) or "attribute" in str(e).lower():
                # Mock-related error, likely means method executed with DeepAgentState
                self.fail(
                    f"REGRESSION CONFIRMED: _pre_run method executed with DeepAgentState\n"
                    f"Error: {e}\n"
                    f"Expected: Method should reject DeepAgentState with clear type error\n"
                    f"Impact: Runtime execution with deprecated state pattern"
                )
            else:
                # Re-raise other exceptions
                raise

    def test_agent_lifecycle_imports_reveal_dependency_on_deprecated_state(self):
        """Test that agent_lifecycle.py imports reveal dependency on deprecated state.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: Import structure shows dependency on DeepAgentState
        """
        try:
            import netra_backend.app.agents.agent_lifecycle as lifecycle_module
        except ImportError as e:
            self.fail(f"Cannot import agent_lifecycle module: {e}")

        # Check module's global namespace for DeepAgentState
        module_globals = dir(lifecycle_module)

        if 'DeepAgentState' in module_globals:
            self.fail(
                f"REGRESSION CONFIRMED: agent_lifecycle module exposes DeepAgentState\n"
                f"Module globals containing DeepAgentState: {[g for g in module_globals if 'DeepAgentState' in g]}\n"
                f"Expected: DeepAgentState should not be accessible from agent_lifecycle\n"
                f"Impact: Module level dependency on deprecated state pattern"
            )

        # Check if any functions in the module reference DeepAgentState
        for attr_name in module_globals:
            attr = getattr(lifecycle_module, attr_name)
            if inspect.isfunction(attr) or inspect.isclass(attr):
                try:
                    # Check annotations
                    hints = get_type_hints(attr)
                    for param_name, param_type in hints.items():
                        if hasattr(param_type, '__name__') and 'DeepAgentState' in param_type.__name__:
                            self.fail(
                                f"REGRESSION CONFIRMED: {attr_name} uses DeepAgentState in type hints\n"
                                f"Parameter: {param_name}\n"
                                f"Type: {param_type}\n"
                                f"Expected: Should use UserExecutionContext or compatible type\n"
                                f"Impact: Type system dependency on deprecated state"
                            )
                except (NameError, AttributeError, TypeError):
                    # Skip type hint checking if it fails
                    pass

        # If we reach here, no deprecated dependencies found (regression fixed)
        self.assertTrue(True, "agent_lifecycle module properly migrated from DeepAgentState")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])