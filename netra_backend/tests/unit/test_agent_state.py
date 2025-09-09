"""
Unit Tests for Agent State Management

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure consistent agent behavior and reliable state transitions
- Value Impact: Proper state management prevents agent deadlocks and ensures predictable behavior
- Strategic Impact: Platform reliability depends on consistent agent lifecycle management

These tests validate the business logic of agent state transitions without external dependencies.
Testing state validation, transition rules, and error handling ensures reliable agent execution.
"""

import pytest
from unittest.mock import Mock, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.agent_state import AgentStateMixin
from netra_backend.app.schemas.agent import SubAgentLifecycle


class MockAgent(AgentStateMixin):
    """Mock agent class for testing state mixin."""
    
    def __init__(self, name: str = "test_agent"):
        self.name = name
        self.state = SubAgentLifecycle.PENDING
        self.logger = MagicMock()


class TestAgentState(SSotBaseTestCase):
    """Test agent state management functionality."""

    def setup_method(self, method=None):
        """Setup test method with mock agent."""
        super().setup_method(method)
        self.agent = MockAgent("state_test_agent")

    @pytest.mark.unit
    def test_set_state_valid_transition_pending_to_running(self):
        """Test valid state transition from PENDING to RUNNING.
        
        BVJ: Agents must transition from pending to running for execution.
        """
        self.agent.state = SubAgentLifecycle.PENDING
        
        self.agent.set_state(SubAgentLifecycle.RUNNING)
        
        assert self.agent.state == SubAgentLifecycle.RUNNING
        
        # Verify logging occurred
        self.agent.logger.debug.assert_called_once()
        log_message = self.agent.logger.debug.call_args[0][0]
        assert "transitioning from pending to running" in log_message.lower()
        
        self.record_metric("pending_to_running_transition", True)

    @pytest.mark.unit
    def test_set_state_valid_transition_running_to_completed(self):
        """Test valid state transition from RUNNING to COMPLETED.
        
        BVJ: Successful agent execution must transition to completed state.
        """
        self.agent.state = SubAgentLifecycle.RUNNING
        
        self.agent.set_state(SubAgentLifecycle.COMPLETED)
        
        assert self.agent.state == SubAgentLifecycle.COMPLETED
        self.record_metric("running_to_completed_transition", True)

    @pytest.mark.unit
    def test_set_state_valid_transition_running_to_failed(self):
        """Test valid state transition from RUNNING to FAILED.
        
        BVJ: Failed agent execution must transition to failed state for error handling.
        """
        self.agent.state = SubAgentLifecycle.RUNNING
        
        self.agent.set_state(SubAgentLifecycle.FAILED)
        
        assert self.agent.state == SubAgentLifecycle.FAILED
        self.record_metric("running_to_failed_transition", True)

    @pytest.mark.unit
    def test_set_state_valid_transition_failed_to_pending(self):
        """Test valid state transition from FAILED to PENDING for retry.
        
        BVJ: Failed agents must be retryable by transitioning back to pending.
        """
        self.agent.state = SubAgentLifecycle.FAILED
        
        self.agent.set_state(SubAgentLifecycle.PENDING)
        
        assert self.agent.state == SubAgentLifecycle.PENDING
        self.record_metric("failed_to_pending_retry", True)

    @pytest.mark.unit
    def test_set_state_valid_transition_completed_to_running(self):
        """Test valid state transition from COMPLETED to RUNNING for re-execution.
        
        BVJ: Completed agents must support re-execution for new requests.
        """
        self.agent.state = SubAgentLifecycle.COMPLETED
        
        self.agent.set_state(SubAgentLifecycle.RUNNING)
        
        assert self.agent.state == SubAgentLifecycle.RUNNING
        self.record_metric("completed_to_running_reexecution", True)

    @pytest.mark.unit
    def test_set_state_invalid_transition_raises_error(self):
        """Test that invalid state transitions raise appropriate errors.
        
        BVJ: Invalid transitions must be prevented to maintain system consistency.
        """
        self.agent.state = SubAgentLifecycle.COMPLETED
        
        # Try invalid transition (completed to pending is valid, so use shutdown to pending)
        self.agent.state = SubAgentLifecycle.SHUTDOWN
        
        with self.expect_exception(ValueError, "Invalid state transition"):
            self.agent.set_state(SubAgentLifecycle.PENDING)
        
        # State should remain unchanged
        assert self.agent.state == SubAgentLifecycle.SHUTDOWN
        self.record_metric("invalid_transition_prevented", True)

    @pytest.mark.unit
    def test_set_state_shutdown_terminal_state(self):
        """Test that SHUTDOWN state is terminal with no valid transitions.
        
        BVJ: Shutdown agents must remain shutdown to prevent resource leaks.
        """
        self.agent.state = SubAgentLifecycle.RUNNING
        
        # Transition to shutdown (valid)
        self.agent.set_state(SubAgentLifecycle.SHUTDOWN)
        assert self.agent.state == SubAgentLifecycle.SHUTDOWN
        
        # Try to transition from shutdown (should fail)
        with self.expect_exception(ValueError):
            self.agent.set_state(SubAgentLifecycle.RUNNING)
        
        # State should remain shutdown
        assert self.agent.state == SubAgentLifecycle.SHUTDOWN
        self.record_metric("shutdown_terminal_state_enforced", True)

    @pytest.mark.unit
    def test_get_valid_transitions_pending(self):
        """Test valid transitions from PENDING state.
        
        BVJ: Pending state must support startup paths and early termination.
        """
        valid_transitions = self.agent._get_valid_transitions()
        pending_transitions = valid_transitions[SubAgentLifecycle.PENDING]
        
        expected_transitions = [
            SubAgentLifecycle.RUNNING,
            SubAgentLifecycle.FAILED,
            SubAgentLifecycle.SHUTDOWN
        ]
        
        assert set(pending_transitions) == set(expected_transitions)
        self.record_metric("pending_transitions_correct", True)

    @pytest.mark.unit
    def test_get_valid_transitions_running(self):
        """Test valid transitions from RUNNING state.
        
        BVJ: Running state must support all execution outcomes and self-loops.
        """
        valid_transitions = self.agent._get_valid_transitions()
        running_transitions = valid_transitions[SubAgentLifecycle.RUNNING]
        
        expected_transitions = [
            SubAgentLifecycle.RUNNING,    # Self-transition for continued execution
            SubAgentLifecycle.COMPLETED,
            SubAgentLifecycle.FAILED,
            SubAgentLifecycle.SHUTDOWN
        ]
        
        assert set(running_transitions) == set(expected_transitions)
        self.record_metric("running_transitions_correct", True)

    @pytest.mark.unit
    def test_get_valid_transitions_failed(self):
        """Test valid transitions from FAILED state.
        
        BVJ: Failed state must support retry mechanisms and termination.
        """
        valid_transitions = self.agent._get_valid_transitions()
        failed_transitions = valid_transitions[SubAgentLifecycle.FAILED]
        
        expected_transitions = [
            SubAgentLifecycle.PENDING,  # Retry via pending
            SubAgentLifecycle.RUNNING,  # Direct retry
            SubAgentLifecycle.SHUTDOWN
        ]
        
        assert set(failed_transitions) == set(expected_transitions)
        self.record_metric("failed_transitions_correct", True)

    @pytest.mark.unit
    def test_get_valid_transitions_completed(self):
        """Test valid transitions from COMPLETED state.
        
        BVJ: Completed state must support re-execution and termination.
        """
        valid_transitions = self.agent._get_valid_transitions()
        completed_transitions = valid_transitions[SubAgentLifecycle.COMPLETED]
        
        expected_transitions = [
            SubAgentLifecycle.RUNNING,   # Re-execution
            SubAgentLifecycle.PENDING,   # Reset for new execution
            SubAgentLifecycle.SHUTDOWN   # Final termination
        ]
        
        assert set(completed_transitions) == set(expected_transitions)
        self.record_metric("completed_transitions_correct", True)

    @pytest.mark.unit
    def test_get_valid_transitions_shutdown(self):
        """Test that SHUTDOWN state has no valid transitions.
        
        BVJ: Terminal shutdown state prevents resource leaks and state corruption.
        """
        valid_transitions = self.agent._get_valid_transitions()
        shutdown_transitions = valid_transitions[SubAgentLifecycle.SHUTDOWN]
        
        assert shutdown_transitions == []
        self.record_metric("shutdown_no_transitions", True)

    @pytest.mark.unit
    def test_is_valid_transition_checks(self):
        """Test transition validation logic for edge cases.
        
        BVJ: Accurate transition validation prevents invalid state changes.
        """
        # Test valid transition
        assert self.agent._is_valid_transition(
            SubAgentLifecycle.PENDING, 
            SubAgentLifecycle.RUNNING
        ) is True
        
        # Test invalid transition
        assert self.agent._is_valid_transition(
            SubAgentLifecycle.SHUTDOWN, 
            SubAgentLifecycle.RUNNING
        ) is False
        
        # Test self-transition (valid for running)
        assert self.agent._is_valid_transition(
            SubAgentLifecycle.RUNNING,
            SubAgentLifecycle.RUNNING
        ) is True
        
        # Test self-transition (invalid for most states)
        assert self.agent._is_valid_transition(
            SubAgentLifecycle.PENDING,
            SubAgentLifecycle.PENDING
        ) is False
        
        self.record_metric("transition_validation_accurate", True)

    @pytest.mark.unit
    def test_get_state_returns_current_state(self):
        """Test that get_state returns the current agent state.
        
        BVJ: State introspection enables monitoring and debugging.
        """
        # Test with different states
        for state in [SubAgentLifecycle.PENDING, SubAgentLifecycle.RUNNING, 
                      SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED,
                      SubAgentLifecycle.SHUTDOWN]:
            self.agent.state = state
            assert self.agent.get_state() == state
        
        self.record_metric("state_introspection_accurate", True)

    @pytest.mark.unit
    def test_raise_transition_error_message_format(self):
        """Test transition error message includes relevant information.
        
        BVJ: Clear error messages enable faster debugging and troubleshooting.
        """
        from_state = SubAgentLifecycle.COMPLETED
        to_state = SubAgentLifecycle.PENDING
        agent_name = "diagnostic_agent"
        
        # Create agent with specific name
        test_agent = MockAgent(agent_name)
        
        with pytest.raises(ValueError) as exc_info:
            test_agent._raise_transition_error(from_state, to_state)
        
        error_message = str(exc_info.value)
        assert "Invalid state transition" in error_message
        assert str(from_state) in error_message
        assert str(to_state) in error_message  
        assert agent_name in error_message
        
        self.record_metric("error_message_informative", True)

    @pytest.mark.unit
    def test_state_transition_logging_contains_agent_name(self):
        """Test that state transition logging includes agent name.
        
        BVJ: Agent-specific logging enables targeted monitoring and debugging.
        """
        agent_name = "cost_optimization_agent"
        test_agent = MockAgent(agent_name)
        test_agent.state = SubAgentLifecycle.PENDING
        
        test_agent.set_state(SubAgentLifecycle.RUNNING)
        
        # Verify logging call included agent name
        test_agent.logger.debug.assert_called_once()
        log_message = test_agent.logger.debug.call_args[0][0]
        assert agent_name in log_message
        
        self.record_metric("agent_name_in_logs", True)

    def test_execution_timing_under_threshold(self):
        """Verify test execution performance meets requirements.
        
        BVJ: Fast unit tests enable rapid development cycles.
        """
        # Unit tests must execute under 100ms
        self.assert_execution_time_under(0.1)
        
        # Verify business metrics were recorded
        self.assert_metrics_recorded(
            "pending_to_running_transition",
            "running_to_completed_transition",
            "running_to_failed_transition",
            "failed_to_pending_retry",
            "invalid_transition_prevented",
            "shutdown_terminal_state_enforced",
            "pending_transitions_correct",
            "running_transitions_correct",
            "failed_transitions_correct",
            "completed_transitions_correct",
            "shutdown_no_transitions",
            "transition_validation_accurate",
            "state_introspection_accurate",
            "error_message_informative",
            "agent_name_in_logs"
        )