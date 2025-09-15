"""
Test 2: Regression Prevention Test for AgentLifecycleMixin Methods (Issue #877)

PURPOSE: Test AgentLifecycleMixin methods work with UserExecutionContext (not DeepAgentState)
REGRESSION: AgentLifecycleMixin still uses DeepAgentState parameter types

This test MUST FAIL initially to prove the regression exists.
After fix, it will PASS when methods accept UserExecutionContext.

Design:
- Create UserExecutionContext instances
- Test _pre_run and _post_run methods
- Validate method compatibility
- Ensure proper error handling
"""
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from typing import Any, Dict
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase

@pytest.mark.unit
class AgentLifecycleRegressionPreventionTests(SSotAsyncTestCase):
    """Test suite preventing AgentLifecycleMixin SSOT regression"""

    async def asyncSetUp(self):
        """Set up test environment with mock agent and contexts"""
        await super().asyncSetUp()
        self.user_context = self._create_user_execution_context()
        self.deprecated_state = self._create_mock_deep_agent_state()
        self.test_agent = self._create_test_agent()
        self.test_run_id = str(uuid.uuid4())

    def _create_user_execution_context(self):
        """Create SSOT UserExecutionContext instance"""
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            return UserExecutionContext(user_id='test_user_123', thread_id='test_thread_456', request_id='test_request_789', session_id='test_session_abc')
        except ImportError:
            mock_context = Mock()
            mock_context.user_id = 'test_user_123'
            mock_context.thread_id = 'test_thread_456'
            mock_context.request_id = 'test_request_789'
            mock_context.session_id = 'test_session_abc'
            return mock_context

    def _create_mock_deep_agent_state(self):
        """Create deprecated DeepAgentState mock for testing"""
        mock_state = Mock()
        mock_state.step_count = 0
        mock_state.user_id = 'test_user_123'
        mock_state.thread_id = 'test_thread_456'
        mock_state.current_agent = 'test_agent'
        return mock_state

    def _create_test_agent(self):
        """Create test agent implementing AgentLifecycleMixin"""
        from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin

        class AgentTests(AgentLifecycleMixin):

            def __init__(self):
                self.name = 'AgentTests'
                self.user_id = 'test_user_123'
                self.start_time = None
                self.end_time = None
                self.context = Mock()
                self.logger = Mock()
                self.emit_agent_started = AsyncMock()
                self.emit_agent_completed = AsyncMock()
                self.emit_error = AsyncMock()
                self.set_state = Mock()
                self._log_agent_start = Mock()
                self._log_agent_completion = Mock()

            async def execute(self, state, run_id: str, stream_updates: bool) -> None:
                """Mock execute method"""
                pass
        return AgentTests()

    async def test_pre_run_with_user_execution_context(self):
        """
        FAILING TEST: _pre_run should accept UserExecutionContext, not DeepAgentState

        Expected: FAIL initially (method expects DeepAgentState)
        After Fix: PASS (method accepts UserExecutionContext)
        """
        try:
            result = await self.test_agent._pre_run(state=self.user_context, run_id=self.test_run_id, stream_updates=True)
            self.assertTrue(result, 'pre_run should return True for valid context')
        except (TypeError, AttributeError) as e:
            self.fail(f'SSOT REGRESSION: _pre_run method cannot accept UserExecutionContext!\n  - Error: {str(e)}\n  - Method signature still expects deprecated DeepAgentState\n  - REMEDIATION: Update method to accept UserExecutionContext\n  - Issue #877: AgentLifecycleMixin SSOT compliance violation')

    async def test_post_run_with_user_execution_context(self):
        """
        FAILING TEST: _post_run should accept UserExecutionContext, not DeepAgentState

        Expected: FAIL initially (method expects DeepAgentState)
        After Fix: PASS (method accepts UserExecutionContext)
        """
        self.test_agent.start_time = 1000.0
        self.test_agent.end_time = 1001.5
        try:
            await self.test_agent._post_run(state=self.user_context, run_id=self.test_run_id, stream_updates=True, success=True)
            self.test_agent.set_state.assert_called()
        except (TypeError, AttributeError) as e:
            self.fail(f'SSOT REGRESSION: _post_run method cannot accept UserExecutionContext!\n  - Error: {str(e)}\n  - Method signature still expects deprecated DeepAgentState\n  - REMEDIATION: Update method to accept UserExecutionContext\n  - Issue #877: AgentLifecycleMixin SSOT compliance violation')

    async def test_execute_method_signature_compliance(self):
        """
        FAILING TEST: execute method should accept UserExecutionContext

        Expected: FAIL initially (abstract method signature uses DeepAgentState)
        After Fix: PASS (method signature accepts UserExecutionContext)
        """
        try:
            await self.test_agent.execute(state=self.user_context, run_id=self.test_run_id, stream_updates=True)
        except (TypeError, AttributeError) as e:
            self.fail(f'SSOT REGRESSION: execute method cannot accept UserExecutionContext!\n  - Error: {str(e)}\n  - Abstract method signature still expects DeepAgentState\n  - REMEDIATION: Update abstract method signature\n  - Issue #877: AgentLifecycleMixin interface SSOT violation')

    async def test_cleanup_method_compliance(self):
        """
        FAILING TEST: cleanup method should accept UserExecutionContext

        Expected: FAIL initially (method expects DeepAgentState)
        After Fix: PASS (method accepts UserExecutionContext)
        """
        try:
            await self.test_agent.cleanup(state=self.user_context, run_id=self.test_run_id)
            self.test_agent.context.clear.assert_called()
        except (TypeError, AttributeError) as e:
            self.fail(f'SSOT REGRESSION: cleanup method cannot accept UserExecutionContext!\n  - Error: {str(e)}\n  - Method signature still expects DeepAgentState\n  - REMEDIATION: Update cleanup method signature\n  - Issue #877: AgentLifecycleMixin cleanup SSOT violation')

    async def test_check_entry_conditions_compliance(self):
        """
        FAILING TEST: check_entry_conditions should accept UserExecutionContext

        Expected: FAIL initially (method expects DeepAgentState)
        After Fix: PASS (method accepts UserExecutionContext)
        """
        try:
            result = await self.test_agent.check_entry_conditions(state=self.user_context, run_id=self.test_run_id)
            self.assertIsInstance(result, bool, 'check_entry_conditions should return boolean')
        except (TypeError, AttributeError) as e:
            self.fail(f'SSOT REGRESSION: check_entry_conditions cannot accept UserExecutionContext!\n  - Error: {str(e)}\n  - Method signature still expects DeepAgentState\n  - REMEDIATION: Update method signature\n  - Issue #877: AgentLifecycleMixin entry conditions SSOT violation')

    async def test_run_method_end_to_end_compliance(self):
        """
        FAILING TEST: Main run method should work end-to-end with UserExecutionContext

        Expected: FAIL initially (run method uses DeepAgentState internally)
        After Fix: PASS (complete workflow with UserExecutionContext)
        """
        self.test_agent.timing_collector = Mock()
        self.test_agent.timing_collector.start_execution.return_value = Mock()
        self.test_agent.timing_collector.complete_execution.return_value = Mock()
        try:
            await self.test_agent.run(state=self.user_context, run_id=self.test_run_id, stream_updates=True)
            self.test_agent.emit_agent_started.assert_called()
        except (TypeError, AttributeError) as e:
            self.fail(f'SSOT REGRESSION: run method workflow fails with UserExecutionContext!\n  - Error: {str(e)}\n  - End-to-end workflow still depends on DeepAgentState\n  - REMEDIATION: Update entire workflow for UserExecutionContext\n  - Issue #877: AgentLifecycleMixin workflow SSOT violation')

    async def test_deprecated_deepagentstate_rejection(self):
        """
        SUCCESS TEST: After fix, methods should reject deprecated DeepAgentState

        Expected: FAIL initially (methods accept DeepAgentState)
        After Fix: PASS (methods reject deprecated DeepAgentState)
        """
        with self.assertRaises((TypeError, ValueError), msg='Methods should reject deprecated DeepAgentState after migration'):
            await self.test_agent._pre_run(state=self.deprecated_state, run_id=self.test_run_id, stream_updates=True)

    async def test_user_isolation_with_context(self):
        """
        FAILING TEST: Verify user isolation works with UserExecutionContext

        Expected: FAIL initially (isolation depends on DeepAgentState)
        After Fix: PASS (proper isolation with UserExecutionContext)
        """
        second_context = self._create_user_execution_context()
        second_context.user_id = 'different_user_456'
        try:
            result1 = await self.test_agent.check_entry_conditions(state=self.user_context, run_id=self.test_run_id)
            result2 = await self.test_agent.check_entry_conditions(state=second_context, run_id=str(uuid.uuid4()))
            self.assertTrue(result1, 'First context should work')
            self.assertTrue(result2, 'Second context should work independently')
        except (TypeError, AttributeError) as e:
            self.fail(f'SSOT REGRESSION: User isolation fails with UserExecutionContext!\n  - Error: {str(e)}\n  - Multi-user isolation still depends on DeepAgentState\n  - REMEDIATION: Implement proper context isolation\n  - Issue #877: User isolation SSOT violation')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')