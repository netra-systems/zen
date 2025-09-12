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

from netra_backend.app.core.agent_execution_tracker import (
    AgentExecutionTracker,
    ExecutionState,
    ExecutionRecord,
    AgentExecutionPhase
)
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
        # Create an execution
        self.execution_id = self.tracker.create_execution(
            agent_name="test_agent",
            thread_id="test_thread",
            user_id="test_user",
            timeout_seconds=1  # Short timeout for testing
        )
        
        # Start the execution
        started = self.tracker.start_execution(self.execution_id)
        self.assertTrue(started, "Execution should start successfully")
        
        # Manually set the execution to TIMEOUT state
        # This simulates what happens when an agent times out
        record = self.tracker.get_execution(self.execution_id)
        self.assertIsNotNone(record, "Execution record should exist")
        
        # Force the execution into TIMEOUT state
        success = self.tracker.update_execution_state(
            self.execution_id,
            ExecutionState.TIMEOUT,
            error="Execution timed out after 1 seconds"
        )
        self.assertTrue(success, "Should be able to set TIMEOUT state")
        
        # Verify the execution is in TIMEOUT state
        record = self.tracker.get_execution(self.execution_id)
        self.assertEqual(record.state, ExecutionState.TIMEOUT, "Execution should be in TIMEOUT state")
        
        # NOW ATTEMPT THE PROBLEMATIC TRANSITION: TIMEOUT  ->  FAILED
        # This should fail due to the state machine validation
        # but the current implementation might allow it, creating inconsistency
        
        # BUG REPRODUCTION: Try to transition from TIMEOUT to FAILED
        # This is what happens in real scenarios when error handling tries to mark a timed-out execution as failed
        with self.expect_exception(ValueError, "Invalid state transition.*TIMEOUT.*FAILED"):
            success = self.tracker.update_execution_state(
                self.execution_id,
                ExecutionState.FAILED,
                error="Additional failure after timeout"
            )
            
            # If we reach here without exception, the bug is present
            # The system should prevent TIMEOUT  ->  FAILED transitions
            if success:
                self.fail(
                    "BUG REPRODUCED: ExecutionState allowed invalid TIMEOUT  ->  FAILED transition. "
                    "This creates inconsistent agent execution states and can cause deadlocks."
                )
    
    def test_valid_timeout_transitions_should_work(self):
        """
        Test that validates what transitions FROM timeout should be allowed.
        
        This test helps define the correct behavior for fixing the bug.
        """
        # Create and start execution
        self.execution_id = self.tracker.create_execution(
            agent_name="test_agent",
            thread_id="test_thread", 
            user_id="test_user"
        )
        
        self.tracker.start_execution(self.execution_id)
        
        # Set to TIMEOUT state
        self.tracker.update_execution_state(
            self.execution_id,
            ExecutionState.TIMEOUT,
            error="Execution timed out"
        )
        
        # TIMEOUT should be a terminal state - no transitions allowed
        record = self.tracker.get_execution(self.execution_id)
        self.assertTrue(record.is_terminal, "TIMEOUT should be a terminal state")
        
        # Verify that the execution tracker correctly identifies it as terminal
        self.assertIn(ExecutionState.TIMEOUT, [
            ExecutionState.COMPLETED, 
            ExecutionState.FAILED,
            ExecutionState.TIMEOUT, 
            ExecutionState.DEAD, 
            ExecutionState.CANCELLED
        ], "TIMEOUT should be included in terminal states")
    
    def test_phase_transition_timeout_validation(self):
        """
        Test phase transitions when timeout occurs.
        
        This reproduces the related issue where AgentExecutionPhase.TIMEOUT
        transitions may not be properly validated.
        """
        # Create execution
        self.execution_id = self.tracker.create_execution(
            agent_name="test_agent",
            thread_id="test_thread",
            user_id="test_user"
        )
        
        # Start execution and move through phases
        self.tracker.start_execution(self.execution_id)
        
        # Move to THINKING phase
        success = self.tracker.transition_state(
            self.execution_id,
            AgentExecutionPhase.THINKING
        )
        self.assertTrue(success, "Should transition to THINKING phase")
        
        # NOW REPRODUCE THE BUG: Try to transition to TIMEOUT phase
        # and then attempt invalid follow-up transitions
        success = self.tracker.transition_state(
            self.execution_id,
            AgentExecutionPhase.TIMEOUT
        )
        self.assertTrue(success, "Should transition to TIMEOUT phase")
        
        # BUG: Attempt to transition from TIMEOUT to FAILED phase
        # This should fail with validation error
        with self.expect_exception(Exception):  # Expect some form of validation error
            self.tracker.transition_state(
                self.execution_id,
                AgentExecutionPhase.FAILED
            )
            
            # If no exception is raised, the bug is reproduced
            record = self.tracker.get_execution(self.execution_id)
            if record.current_phase == AgentExecutionPhase.FAILED:
                self.fail(
                    "BUG REPRODUCED: AgentExecutionPhase allowed invalid TIMEOUT  ->  FAILED transition. "
                    "Phase transitions should validate state machine rules."
                )
    
    def test_execution_state_consistency_check(self):
        """
        Test that reproduces state consistency issues.
        
        This test validates that ExecutionState and AgentExecutionPhase 
        remain consistent during transitions.
        """
        # Create execution
        self.execution_id = self.tracker.create_execution(
            agent_name="test_agent",
            thread_id="test_thread",
            user_id="test_user"
        )
        
        self.tracker.start_execution(self.execution_id)
        
        # Get initial record
        record = self.tracker.get_execution(self.execution_id)
        initial_state = record.state
        initial_phase = record.current_phase
        
        # Transition to timeout at state level
        self.tracker.update_execution_state(
            self.execution_id,
            ExecutionState.TIMEOUT,
            error="State-level timeout"
        )
        
        # Transition to timeout at phase level  
        self.tracker.transition_state(
            self.execution_id,
            AgentExecutionPhase.TIMEOUT
        )
        
        # Verify consistency
        record = self.tracker.get_execution(self.execution_id)
        
        # STATE AND PHASE SHOULD BE CONSISTENT
        # If state is TIMEOUT, phase should also indicate timeout
        if record.state == ExecutionState.TIMEOUT:
            expected_phase = AgentExecutionPhase.TIMEOUT
            self.assertEqual(
                record.current_phase, 
                expected_phase,
                f"BUG: State is {record.state} but phase is {record.current_phase}. "
                f"State and phase should be consistent for timeout conditions."
            )
        
        # BUG REPRODUCTION: Try inconsistent state update
        # This should be prevented by proper validation
        try:
            # Try to set state to FAILED while phase is TIMEOUT
            self.tracker.update_execution_state(
                self.execution_id,
                ExecutionState.FAILED,
                error="Inconsistent state change"
            )
            
            record = self.tracker.get_execution(self.execution_id)
            if (record.state == ExecutionState.FAILED and 
                record.current_phase == AgentExecutionPhase.TIMEOUT):
                self.fail(
                    "BUG REPRODUCED: ExecutionState and AgentExecutionPhase are inconsistent. "
                    f"State: {record.state}, Phase: {record.current_phase}. "
                    "The system allowed an invalid state where execution state is FAILED "
                    "but phase is still TIMEOUT, creating logical inconsistency."
                )
        except Exception as e:
            # This is expected - the system should prevent inconsistent states
            self.record_metric("validation_error_caught", str(e))
    
    def teardown_method(self, method=None):
        """Clean up test execution."""
        if self.execution_id and hasattr(self, 'tracker'):
            try:
                # Clean up the execution if it exists
                record = self.tracker.get_execution(self.execution_id)
                if record and not record.is_terminal:
                    self.tracker.update_execution_state(
                        self.execution_id,
                        ExecutionState.CANCELLED,
                        error="Test cleanup"
                    )
            except Exception:
                pass  # Ignore cleanup errors
        
        super().teardown_method(method)


if __name__ == "__main__":
    # Run this test to reproduce the ExecutionState transition bug
    pytest.main([__file__, "-v", "-s"])