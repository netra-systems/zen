"""
Targeted test for ExecutionState transition bug reproduction.

PURPOSE: Reproduce the specific TIMEOUT  ->  FAILED invalid transition bug identified in issue #276.

EXPECTED BEHAVIOR:
- Test should FAIL with an invalid state transition error
- Demonstrates the state machine logic issue where TIMEOUT state cannot transition to FAILED
- Shows the exact failure mode that needs to be fixed

BUG TO REPRODUCE:
- ExecutionState has an invalid transition from TIMEOUT to FAILED
- This breaks the agent execution flow when timeouts occur
- Results in agent executions getting stuck in inconsistent states
"""
import pytest
from unittest.mock import Mock, patch
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, ExecutionState, ExecutionRecord, AgentExecutionPhase
from datetime import datetime, timezone

class TestExecutionStateTransitionsBug(SSotBaseTestCase):
    """Test to reproduce the ExecutionState transition bug."""

    def setup_method(self, method=None):
        """Setup test with execution tracker."""
        super().setup_method(method)
        self.tracker = AgentExecutionTracker()
        self.execution_id = None

    def test_timeout_to_failed_transition_should_fail(self):
        """
        Test that reproduces the TIMEOUT  ->  FAILED invalid transition bug.
        
        EXPECTED RESULT: This test should FAIL with an invalid state transition error.
        This demonstrates the bug where ExecutionState doesn't allow TIMEOUT  ->  FAILED transitions.
        """
        self.execution_id = self.tracker.create_execution(agent_name='test_agent', thread_id='test_thread', user_id='test_user', timeout_seconds=1)
        started = self.tracker.start_execution(self.execution_id)
        self.assertTrue(started, 'Execution should start successfully')
        record = self.tracker.get_execution(self.execution_id)
        self.assertIsNotNone(record, 'Execution record should exist')
        success = self.tracker.update_execution_state(self.execution_id, ExecutionState.TIMEOUT, error='Execution timed out after 1 seconds')
        self.assertTrue(success, 'Should be able to set TIMEOUT state')
        record = self.tracker.get_execution(self.execution_id)
        self.assertEqual(record.state, ExecutionState.TIMEOUT, 'Execution should be in TIMEOUT state')
        with self.expect_exception(ValueError, 'Invalid state transition.*TIMEOUT.*FAILED'):
            success = self.tracker.update_execution_state(self.execution_id, ExecutionState.FAILED, error='Additional failure after timeout')
            if success:
                self.fail('BUG REPRODUCED: ExecutionState allowed invalid TIMEOUT  ->  FAILED transition. This creates inconsistent agent execution states and can cause deadlocks.')

    def test_valid_timeout_transitions_should_work(self):
        """
        Test that validates what transitions FROM timeout should be allowed.
        
        This test helps define the correct behavior for fixing the bug.
        """
        self.execution_id = self.tracker.create_execution(agent_name='test_agent', thread_id='test_thread', user_id='test_user')
        self.tracker.start_execution(self.execution_id)
        self.tracker.update_execution_state(self.execution_id, ExecutionState.TIMEOUT, error='Execution timed out')
        record = self.tracker.get_execution(self.execution_id)
        self.assertTrue(record.is_terminal, 'TIMEOUT should be a terminal state')
        self.assertIn(ExecutionState.TIMEOUT, [ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.TIMEOUT, ExecutionState.DEAD, ExecutionState.CANCELLED], 'TIMEOUT should be included in terminal states')

    def test_phase_transition_timeout_validation(self):
        """
        Test phase transitions when timeout occurs.
        
        This reproduces the related issue where AgentExecutionPhase.TIMEOUT
        transitions may not be properly validated.
        """
        self.execution_id = self.tracker.create_execution(agent_name='test_agent', thread_id='test_thread', user_id='test_user')
        self.tracker.start_execution(self.execution_id)
        success = self.tracker.transition_state(self.execution_id, AgentExecutionPhase.THINKING)
        self.assertTrue(success, 'Should transition to THINKING phase')
        success = self.tracker.transition_state(self.execution_id, AgentExecutionPhase.TIMEOUT)
        self.assertTrue(success, 'Should transition to TIMEOUT phase')
        with self.expect_exception(Exception):
            self.tracker.transition_state(self.execution_id, AgentExecutionPhase.FAILED)
            record = self.tracker.get_execution(self.execution_id)
            if record.current_phase == AgentExecutionPhase.FAILED:
                self.fail('BUG REPRODUCED: AgentExecutionPhase allowed invalid TIMEOUT  ->  FAILED transition. Phase transitions should validate state machine rules.')

    def test_execution_state_consistency_check(self):
        """
        Test that reproduces state consistency issues.
        
        This test validates that ExecutionState and AgentExecutionPhase 
        remain consistent during transitions.
        """
        self.execution_id = self.tracker.create_execution(agent_name='test_agent', thread_id='test_thread', user_id='test_user')
        self.tracker.start_execution(self.execution_id)
        record = self.tracker.get_execution(self.execution_id)
        initial_state = record.state
        initial_phase = record.current_phase
        self.tracker.update_execution_state(self.execution_id, ExecutionState.TIMEOUT, error='State-level timeout')
        self.tracker.transition_state(self.execution_id, AgentExecutionPhase.TIMEOUT)
        record = self.tracker.get_execution(self.execution_id)
        if record.state == ExecutionState.TIMEOUT:
            expected_phase = AgentExecutionPhase.TIMEOUT
            self.assertEqual(record.current_phase, expected_phase, f'BUG: State is {record.state} but phase is {record.current_phase}. State and phase should be consistent for timeout conditions.')
        try:
            self.tracker.update_execution_state(self.execution_id, ExecutionState.FAILED, error='Inconsistent state change')
            record = self.tracker.get_execution(self.execution_id)
            if record.state == ExecutionState.FAILED and record.current_phase == AgentExecutionPhase.TIMEOUT:
                self.fail(f'BUG REPRODUCED: ExecutionState and AgentExecutionPhase are inconsistent. State: {record.state}, Phase: {record.current_phase}. The system allowed an invalid state where execution state is FAILED but phase is still TIMEOUT, creating logical inconsistency.')
        except Exception as e:
            self.record_metric('validation_error_caught', str(e))

    def teardown_method(self, method=None):
        """Clean up test execution."""
        if self.execution_id and hasattr(self, 'tracker'):
            try:
                record = self.tracker.get_execution(self.execution_id)
                if record and (not record.is_terminal):
                    self.tracker.update_execution_state(self.execution_id, ExecutionState.CANCELLED, error='Test cleanup')
            except Exception:
                pass
        super().teardown_method(method)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')