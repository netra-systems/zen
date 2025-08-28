"""Agent State Management Module

Handles agent state transitions and validation.
"""

from typing import Dict, List

from netra_backend.app.schemas.agent import SubAgentLifecycle


class AgentStateMixin:
    """Mixin providing agent state management functionality"""
    
    def set_state(self, new_state: SubAgentLifecycle) -> None:
        """Set agent state with transition validation."""
        current_state = self.state
        
        # Validate state transition
        if not self._is_valid_transition(current_state, new_state):
            self._raise_transition_error(current_state, new_state)
        
        self.logger.debug(f"{self.name} transitioning from {current_state} to {new_state}")
        self.state = new_state
    
    def _raise_transition_error(self, from_state: SubAgentLifecycle, to_state: SubAgentLifecycle) -> None:
        """Raise transition error with proper message"""
        raise ValueError(
            f"Invalid state transition from {from_state} to {to_state} "
            f"for agent {self.name}"
        )
    
    def _is_valid_transition(self, from_state: SubAgentLifecycle, to_state: SubAgentLifecycle) -> bool:
        """Validate if state transition is allowed."""
        valid_transitions = self._get_valid_transitions()
        return to_state in valid_transitions.get(from_state, [])
    
    def _get_valid_transitions(self) -> Dict[SubAgentLifecycle, List[SubAgentLifecycle]]:
        """Get mapping of valid state transitions."""
        return {
            SubAgentLifecycle.PENDING: self._get_pending_transitions(),
            SubAgentLifecycle.RUNNING: self._get_running_transitions(), 
            SubAgentLifecycle.COMPLETED: self._get_completed_transitions(),
            SubAgentLifecycle.FAILED: self._get_failed_transitions(),
            SubAgentLifecycle.SHUTDOWN: []  # Terminal state
        }
    
    def _get_pending_transitions(self) -> List[SubAgentLifecycle]:
        """Get valid transitions from PENDING state."""
        return [
            SubAgentLifecycle.RUNNING,
            SubAgentLifecycle.FAILED,
            SubAgentLifecycle.SHUTDOWN
        ]
    
    def _get_running_transitions(self) -> List[SubAgentLifecycle]:
        """Get valid transitions from RUNNING state.""" 
        return [
            SubAgentLifecycle.RUNNING,    # Allow staying in running state
            SubAgentLifecycle.COMPLETED,
            SubAgentLifecycle.FAILED,
            SubAgentLifecycle.SHUTDOWN
        ]
    
    def _get_failed_transitions(self) -> List[SubAgentLifecycle]:
        """Get valid transitions from FAILED state."""
        return [
            SubAgentLifecycle.PENDING,  # Allow retry via pending
            SubAgentLifecycle.RUNNING,  # Allow direct retry
            SubAgentLifecycle.SHUTDOWN
        ]
    
    def _get_completed_transitions(self) -> List[SubAgentLifecycle]:
        """Get valid transitions from COMPLETED state."""
        return [
            SubAgentLifecycle.RUNNING,   # Allow retry from completed state
            SubAgentLifecycle.PENDING,   # Allow reset to pending
            SubAgentLifecycle.SHUTDOWN   # Allow final shutdown
        ]

    def get_state(self) -> SubAgentLifecycle:
        """Get current agent state."""
        return self.state