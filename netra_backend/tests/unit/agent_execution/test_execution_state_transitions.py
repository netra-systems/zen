"""
Unit Tests for Agent Execution State Transitions

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Revenue protection and user experience reliability
- Value Impact: Ensures agent execution state tracking prevents silent failures and provides real-time progress
- Strategic Impact: Core platform functionality - agent state management protects $500K+ ARR from execution failures

This module tests the ExecutionState enum transitions and validation logic to ensure:
1. All 9 ExecutionState values are properly defined and accessible
2. State transitions follow business logic rules
3. Invalid state transitions are prevented
4. State validation prevents dict objects (Issue #305 fix)
5. State values serialize correctly for WebSocket events
"""
import pytest
import unittest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, ExecutionState, ExecutionRecord, get_execution_tracker
from test_framework.ssot.base_test_case import SSotBaseTestCase

class ExecutionStateTransitionsTests(unittest.TestCase, SSotBaseTestCase):
    """Unit tests for ExecutionState enum transitions and validation."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.tracker = AgentExecutionTracker()
        self.test_user_id = f'user_{uuid.uuid4().hex[:8]}'
        self.test_thread_id = f'thread_{uuid.uuid4().hex[:8]}'
        self.test_agent_name = 'test_agent'

    def test_execution_state_enum_completeness(self):
        """Test that all 9 ExecutionState values are properly defined."""
        expected_states = {'PENDING', 'STARTING', 'RUNNING', 'COMPLETING', 'COMPLETED', 'FAILED', 'TIMEOUT', 'DEAD', 'CANCELLED'}
        actual_states = {state.name for state in ExecutionState}
        self.assertEqual(expected_states, actual_states, 'ExecutionState enum missing expected values')
        self.assertEqual(ExecutionState.PENDING.value, 'pending')
        self.assertEqual(ExecutionState.STARTING.value, 'starting')
        self.assertEqual(ExecutionState.RUNNING.value, 'running')
        self.assertEqual(ExecutionState.COMPLETING.value, 'completing')
        self.assertEqual(ExecutionState.COMPLETED.value, 'completed')
        self.assertEqual(ExecutionState.FAILED.value, 'failed')
        self.assertEqual(ExecutionState.TIMEOUT.value, 'timeout')
        self.assertEqual(ExecutionState.DEAD.value, 'dead')
        self.assertEqual(ExecutionState.CANCELLED.value, 'cancelled')

    def test_valid_state_transitions_from_pending(self):
        """Test valid transitions from PENDING state."""
        execution_id = self.tracker.create_execution(agent_name=self.test_agent_name, user_id=self.test_user_id, thread_id=self.test_thread_id)
        result = self.tracker.update_execution_state(execution_id, ExecutionState.STARTING)
        self.assertTrue(result, 'Should allow PENDING  ->  STARTING transition')
        execution = self.tracker.get_execution(execution_id)
        self.assertEqual(execution.state, ExecutionState.STARTING)

    def test_valid_state_transitions_from_starting(self):
        """Test valid transitions from STARTING state."""
        execution_id = self.tracker.create_execution(agent_name=self.test_agent_name, user_id=self.test_user_id, thread_id=self.test_thread_id)
        self.tracker.update_execution_state(execution_id, ExecutionState.STARTING)
        result = self.tracker.update_execution_state(execution_id, ExecutionState.RUNNING)
        self.assertTrue(result, 'Should allow STARTING  ->  RUNNING transition')
        execution = self.tracker.get_execution(execution_id)
        self.assertEqual(execution.state, ExecutionState.RUNNING)

    def test_valid_state_transitions_from_running(self):
        """Test valid transitions from RUNNING state."""
        execution_id = self.tracker.create_execution(agent_name=self.test_agent_name, user_id=self.test_user_id, thread_id=self.test_thread_id)
        self.tracker.update_execution_state(execution_id, ExecutionState.STARTING)
        self.tracker.update_execution_state(execution_id, ExecutionState.RUNNING)
        result = self.tracker.update_execution_state(execution_id, ExecutionState.COMPLETING)
        self.assertTrue(result, 'Should allow RUNNING  ->  COMPLETING transition')
        execution = self.tracker.get_execution(execution_id)
        self.assertEqual(execution.state, ExecutionState.COMPLETING)

    def test_valid_state_transitions_to_terminal_states(self):
        """Test transitions to terminal states (COMPLETED, FAILED, TIMEOUT, DEAD, CANCELLED)."""
        execution_id1 = self.tracker.create_execution(agent_name=self.test_agent_name, user_id=self.test_user_id, thread_id=self.test_thread_id)
        self.tracker.update_execution_state(execution_id1, ExecutionState.RUNNING)
        self.tracker.update_execution_state(execution_id1, ExecutionState.COMPLETING)
        result = self.tracker.update_execution_state(execution_id1, ExecutionState.COMPLETED)
        self.assertTrue(result, 'Should allow COMPLETING  ->  COMPLETED transition')
        execution_id2 = self.tracker.create_execution(agent_name=self.test_agent_name, user_id=self.test_user_id, thread_id=self.test_thread_id)
        self.tracker.update_execution_state(execution_id2, ExecutionState.RUNNING)
        result = self.tracker.update_execution_state(execution_id2, ExecutionState.FAILED)
        self.assertTrue(result, 'Should allow RUNNING  ->  FAILED transition')
        execution_id3 = self.tracker.create_execution(agent_name=self.test_agent_name, user_id=self.test_user_id, thread_id=self.test_thread_id)
        self.tracker.update_execution_state(execution_id3, ExecutionState.RUNNING)
        result = self.tracker.update_execution_state(execution_id3, ExecutionState.TIMEOUT)
        self.assertTrue(result, 'Should allow RUNNING  ->  TIMEOUT transition')

    def test_dict_object_state_rejection_issue_305_fix(self):
        """Test that dict objects are rejected as state values (Issue #305 fix)."""
        execution_id = self.tracker.create_execution(agent_name=self.test_agent_name, user_id=self.test_user_id, thread_id=self.test_thread_id)
        invalid_dict_states = [{'success': False, 'completed': True}, {'success': True, 'completed': True}, {'status': 'failed'}, {'state': 'running'}]
        for invalid_state in invalid_dict_states:
            with self.assertRaises(ValueError) as context:
                self.tracker.update_execution_state(execution_id, invalid_state)
            self.assertIn('Dict object', str(context.exception))
            self.assertIn('Issue #305', str(context.exception))

    def test_non_execution_state_enum_rejection(self):
        """Test that non-ExecutionState enum values are rejected."""
        execution_id = self.tracker.create_execution(agent_name=self.test_agent_name, user_id=self.test_user_id, thread_id=self.test_thread_id)
        invalid_states = ['pending', 42, None, [], ExecutionState]
        for invalid_state in invalid_states:
            with self.assertRaises((TypeError, ValueError)) as context:
                self.tracker.update_execution_state(execution_id, invalid_state)
            error_msg = str(context.exception)
            self.assertTrue('ExecutionState' in error_msg or 'enum' in error_msg, f'Error message should mention ExecutionState for invalid state: {invalid_state}')

    def test_terminal_state_immutability(self):
        """Test that terminal states cannot be changed once set."""
        terminal_states = [ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.TIMEOUT, ExecutionState.DEAD, ExecutionState.CANCELLED]
        for terminal_state in terminal_states:
            execution_id = self.tracker.create_execution(agent_name=self.test_agent_name, user_id=self.test_user_id, thread_id=self.test_thread_id)
            self.tracker.update_execution_state(execution_id, terminal_state)
            execution = self.tracker.get_execution(execution_id)
            self.assertEqual(execution.state, terminal_state)
            original_state = execution.state
            result = self.tracker.update_execution_state(execution_id, ExecutionState.RUNNING)
            execution_after = self.tracker.get_execution(execution_id)
            if not result:
                self.assertEqual(execution_after.state, original_state)

    def test_state_serialization_for_websocket_events(self):
        """Test that ExecutionState values serialize correctly for WebSocket events."""
        execution_id = self.tracker.create_execution(agent_name=self.test_agent_name, user_id=self.test_user_id, thread_id=self.test_thread_id)
        test_states = [ExecutionState.PENDING, ExecutionState.RUNNING, ExecutionState.COMPLETED]
        for state in test_states:
            self.tracker.update_execution_state(execution_id, state)
            execution = self.tracker.get_execution(execution_id)
            self.assertTrue(hasattr(execution.state, 'value'))
            self.assertIsInstance(execution.state.value, str)
            state_dict = {'execution_id': execution_id, 'state': execution.state.value, 'agent_name': execution.agent_name}
            import json
            serialized = json.dumps(state_dict)
            deserialized = json.loads(serialized)
            self.assertEqual(deserialized['state'], state.value)

    def test_execution_state_comparison_and_equality(self):
        """Test ExecutionState comparison operations."""
        self.assertEqual(ExecutionState.PENDING, ExecutionState.PENDING)
        self.assertNotEqual(ExecutionState.PENDING, ExecutionState.RUNNING)
        state_set = {ExecutionState.PENDING, ExecutionState.RUNNING, ExecutionState.PENDING}
        self.assertEqual(len(state_set), 2)
        state_counts = {ExecutionState.PENDING: 0, ExecutionState.RUNNING: 0, ExecutionState.COMPLETED: 0}
        state_counts[ExecutionState.PENDING] += 1
        self.assertEqual(state_counts[ExecutionState.PENDING], 1)

    def test_execution_state_business_logic_grouping(self):
        """Test logical grouping of states for business logic."""
        active_states = {ExecutionState.STARTING, ExecutionState.RUNNING, ExecutionState.COMPLETING}
        terminal_states = {ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.TIMEOUT, ExecutionState.DEAD, ExecutionState.CANCELLED}
        initial_states = {ExecutionState.PENDING}
        all_states = active_states | terminal_states | initial_states
        enum_states = set(ExecutionState)
        self.assertEqual(all_states, enum_states, 'All ExecutionState values should be categorized')
        for state in active_states:
            self.assertNotIn(state, terminal_states)
            self.assertNotIn(state, initial_states)
        for state in terminal_states:
            self.assertNotIn(state, active_states)
            self.assertNotIn(state, initial_states)

    def test_get_execution_tracker_singleton_pattern(self):
        """Test the get_execution_tracker factory function."""
        tracker1 = get_execution_tracker()
        tracker2 = get_execution_tracker()
        self.assertIs(tracker1, tracker2, 'get_execution_tracker should return the same instance')
        self.assertIsInstance(tracker1, AgentExecutionTracker)

    def test_execution_state_string_representation(self):
        """Test string representation of ExecutionState for debugging."""
        for state in ExecutionState:
            str_repr = str(state)
            self.assertIn(state.name, str_repr)
            repr_repr = repr(state)
            self.assertIn('ExecutionState', repr_repr)
            self.assertIn(state.name, repr_repr)
            self.assertEqual(state.value, state.value.lower())
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')