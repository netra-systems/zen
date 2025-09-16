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
            self.fail(f'Cannot import AgentLifecycleMixin: {e}')
        pre_run_method = getattr(AgentLifecycleMixin, '_pre_run', None)
        if pre_run_method is None:
            self.fail('_pre_run method not found in AgentLifecycleMixin')
        signature = inspect.signature(pre_run_method)
        state_param = signature.parameters.get('state')
        if state_param is None:
            self.fail("'state' parameter not found in _pre_run method")
        annotation = state_param.annotation
        annotation_str = str(annotation) if annotation != inspect.Parameter.empty else 'None'
        if 'DeepAgentState' in annotation_str:
            self.fail(f'REGRESSION CONFIRMED: _pre_run method signature uses DeepAgentState\nMethod: AgentLifecycleMixin._pre_run\nState parameter annotation: {annotation_str}\nFull signature: {signature}\nExpected: Should use UserExecutionContext or compatible type\nImpact: Agent pre-execution using deprecated state pattern')
        self.assertTrue(True, '_pre_run method signature properly migrated')

    def test_post_run_method_signature_uses_deepagentstate(self):
        """Test that _post_run method signature still uses DeepAgentState.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: _post_run method expects DeepAgentState parameter
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        except ImportError as e:
            self.fail(f'Cannot import AgentLifecycleMixin: {e}')
        post_run_method = getattr(AgentLifecycleMixin, '_post_run', None)
        if post_run_method is None:
            self.fail('_post_run method not found in AgentLifecycleMixin')
        signature = inspect.signature(post_run_method)
        state_param = signature.parameters.get('state')
        if state_param is None:
            self.fail("'state' parameter not found in _post_run method")
        annotation = state_param.annotation
        annotation_str = str(annotation) if annotation != inspect.Parameter.empty else 'None'
        if 'DeepAgentState' in annotation_str:
            self.fail(f'REGRESSION CONFIRMED: _post_run method signature uses DeepAgentState\nMethod: AgentLifecycleMixin._post_run\nState parameter annotation: {annotation_str}\nFull signature: {signature}\nExpected: Should use UserExecutionContext or compatible type\nImpact: Agent post-execution using deprecated state pattern')
        self.assertTrue(True, '_post_run method signature properly migrated')

    def test_execute_method_signature_uses_deepagentstate(self):
        """Test that execute method signature still uses DeepAgentState.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: execute method expects DeepAgentState parameter
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        except ImportError as e:
            self.fail(f'Cannot import AgentLifecycleMixin: {e}')
        execute_method = getattr(AgentLifecycleMixin, 'execute', None)
        if execute_method is None:
            self.fail('execute method not found in AgentLifecycleMixin')
        signature = inspect.signature(execute_method)
        state_param = signature.parameters.get('state')
        if state_param is None:
            self.fail("'state' parameter not found in execute method")
        annotation = state_param.annotation
        annotation_str = str(annotation) if annotation != inspect.Parameter.empty else 'None'
        if 'DeepAgentState' in annotation_str:
            self.fail(f'REGRESSION CONFIRMED: execute method signature uses DeepAgentState\nMethod: AgentLifecycleMixin.execute\nState parameter annotation: {annotation_str}\nFull signature: {signature}\nExpected: Should use UserExecutionContext or compatible type\nImpact: Agent execution using deprecated state pattern')
        self.assertTrue(True, 'execute method signature properly migrated')

    def test_check_entry_conditions_method_signature_uses_deepagentstate(self):
        """Test that check_entry_conditions method signature still uses DeepAgentState.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: check_entry_conditions method expects DeepAgentState parameter
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        except ImportError as e:
            self.fail(f'Cannot import AgentLifecycleMixin: {e}')
        method = getattr(AgentLifecycleMixin, 'check_entry_conditions', None)
        if method is None:
            self.fail('check_entry_conditions method not found in AgentLifecycleMixin')
        signature = inspect.signature(method)
        state_param = signature.parameters.get('state')
        if state_param is None:
            self.fail("'state' parameter not found in check_entry_conditions method")
        annotation = state_param.annotation
        annotation_str = str(annotation) if annotation != inspect.Parameter.empty else 'None'
        if 'DeepAgentState' in annotation_str:
            self.fail(f'REGRESSION CONFIRMED: check_entry_conditions method signature uses DeepAgentState\nMethod: AgentLifecycleMixin.check_entry_conditions\nState parameter annotation: {annotation_str}\nFull signature: {signature}\nExpected: Should use UserExecutionContext or compatible type\nImpact: Agent entry condition checking using deprecated state pattern')
        self.assertTrue(True, 'check_entry_conditions method signature properly migrated')

    def test_cleanup_method_signature_uses_deepagentstate(self):
        """Test that cleanup method signature still uses DeepAgentState.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: cleanup method expects DeepAgentState parameter
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        except ImportError as e:
            self.fail(f'Cannot import AgentLifecycleMixin: {e}')
        cleanup_method = getattr(AgentLifecycleMixin, 'cleanup', None)
        if cleanup_method is None:
            self.fail('cleanup method not found in AgentLifecycleMixin')
        signature = inspect.signature(cleanup_method)
        state_param = signature.parameters.get('state')
        if state_param is None:
            self.fail("'state' parameter not found in cleanup method")
        annotation = state_param.annotation
        annotation_str = str(annotation) if annotation != inspect.Parameter.empty else 'None'
        if 'DeepAgentState' in annotation_str:
            self.fail(f'REGRESSION CONFIRMED: cleanup method signature uses DeepAgentState\nMethod: AgentLifecycleMixin.cleanup\nState parameter annotation: {annotation_str}\nFull signature: {signature}\nExpected: Should use UserExecutionContext or compatible type\nImpact: Agent cleanup using deprecated state pattern')
        self.assertTrue(True, 'cleanup method signature properly migrated')

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
            self.skip(f'Cannot import required classes: {e}')

        class TestAgent(AgentLifecycleMixin):

            def __init__(self):
                self.name = 'TestAgent'
                self.logger = Mock()
                self.start_time = 0.0
                self.end_time = 0.0
                self.context = Mock()
                self.emit_agent_started = AsyncMock()
                self.emit_agent_completed = AsyncMock()
                self.emit_error = AsyncMock()
                self.set_state = Mock()
                self._log_agent_start = Mock()
                self._log_agent_completion = Mock()

            async def execute(self, state, run_id, stream_updates):
                """Mock execute method."""
                pass
        agent = TestAgent()
        deprecated_state = DeepAgentState(user_request='test request', user_id='test_user_123', run_id='test_run_456')
        run_id = 'test_run_789'
        try:
            result = await agent._pre_run(deprecated_state, run_id, True)
            self.fail(f'REGRESSION CONFIRMED: _pre_run method accepts DeepAgentState at runtime\nMethod returned: {result}\nState type: {type(deprecated_state)}\nExpected: Method should reject DeepAgentState and require UserExecutionContext\nImpact: Runtime acceptance of deprecated state creates vulnerability')
        except TypeError as e:
            if 'UserExecutionContext' in str(e) or 'DeepAgentState' in str(e):
                self.assertTrue(True, 'Method properly rejects DeepAgentState')
            else:
                self.fail(f'Unexpected error when testing with DeepAgentState: {e}')
        except Exception as e:
            if 'Mock' in str(e) or 'attribute' in str(e).lower():
                self.fail(f'REGRESSION CONFIRMED: _pre_run method executed with DeepAgentState\nError: {e}\nExpected: Method should reject DeepAgentState with clear type error\nImpact: Runtime execution with deprecated state pattern')
            else:
                raise

    def test_agent_lifecycle_imports_reveal_dependency_on_deprecated_state(self):
        """Test that agent_lifecycle.py imports reveal dependency on deprecated state.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: Import structure shows dependency on DeepAgentState
        """
        try:
            import netra_backend.app.agents.agent_lifecycle as lifecycle_module
        except ImportError as e:
            self.fail(f'Cannot import agent_lifecycle module: {e}')
        module_globals = dir(lifecycle_module)
        if 'DeepAgentState' in module_globals:
            self.fail(f"REGRESSION CONFIRMED: agent_lifecycle module exposes DeepAgentState\nModule globals containing DeepAgentState: {[g for g in module_globals if 'DeepAgentState' in g]}\nExpected: DeepAgentState should not be accessible from agent_lifecycle\nImpact: Module level dependency on deprecated state pattern")
        for attr_name in module_globals:
            attr = getattr(lifecycle_module, attr_name)
            if inspect.isfunction(attr) or inspect.isclass(attr):
                try:
                    hints = get_type_hints(attr)
                    for param_name, param_type in hints.items():
                        if hasattr(param_type, '__name__') and 'DeepAgentState' in param_type.__name__:
                            self.fail(f'REGRESSION CONFIRMED: {attr_name} uses DeepAgentState in type hints\nParameter: {param_name}\nType: {param_type}\nExpected: Should use UserExecutionContext or compatible type\nImpact: Type system dependency on deprecated state')
                except (NameError, AttributeError, TypeError):
                    pass
        self.assertTrue(True, 'agent_lifecycle module properly migrated from DeepAgentState')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')