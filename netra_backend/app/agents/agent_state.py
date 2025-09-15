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


class AgentState:
    """
    SSOT-compliant Agent State Management class

    Provides centralized state management for agents with proper multi-user isolation
    and state transition validation capabilities.
    """

    def __init__(self, agent_name: str, user_id: str, initial_state: SubAgentLifecycle = SubAgentLifecycle.PENDING):
        """Initialize agent state with user isolation."""
        self.agent_name = agent_name
        self.user_id = user_id
        self.state = initial_state
        self.state_history = [{'state': initial_state, 'timestamp': self._get_timestamp()}]
        self.metadata = {}

    def set_state(self, new_state: SubAgentLifecycle, metadata: Dict = None) -> None:
        """Set agent state with transition validation and history tracking."""
        current_state = self.state

        # Validate state transition using mixin logic
        if not self._is_valid_transition(current_state, new_state):
            self._raise_transition_error(current_state, new_state)

        # Update state and history
        self.state = new_state
        state_entry = {
            'state': new_state,
            'timestamp': self._get_timestamp(),
            'previous_state': current_state
        }
        if metadata:
            state_entry['metadata'] = metadata

        self.state_history.append(state_entry)

        # Update metadata if provided
        if metadata:
            self.metadata.update(metadata)

    def get_state(self) -> SubAgentLifecycle:
        """Get current agent state."""
        return self.state

    def get_state_history(self) -> List[Dict]:
        """Get complete state transition history."""
        return self.state_history.copy()

    def get_metadata(self) -> Dict:
        """Get agent state metadata."""
        return self.metadata.copy()

    def reset_state(self, new_initial_state: SubAgentLifecycle = SubAgentLifecycle.PENDING):
        """Reset agent state to initial or specified state."""
        self.state = new_initial_state
        self.state_history = [{'state': new_initial_state, 'timestamp': self._get_timestamp(), 'action': 'reset'}]
        self.metadata = {}

    def _get_timestamp(self) -> float:
        """Get current timestamp for state tracking."""
        import time
        return time.time()

    def _raise_transition_error(self, from_state: SubAgentLifecycle, to_state: SubAgentLifecycle) -> None:
        """Raise transition error with proper message"""
        raise ValueError(
            f"Invalid state transition from {from_state} to {to_state} "
            f"for agent {self.agent_name} (user: {self.user_id})"
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

    @classmethod
    def create_for_agent(cls, agent_name: str, user_id: str, initial_state: SubAgentLifecycle = SubAgentLifecycle.PENDING):
        """Factory method to create agent state for specific agent and user."""
        return cls(agent_name=agent_name, user_id=user_id, initial_state=initial_state)

    def __repr__(self) -> str:
        """String representation of agent state."""
        return f"AgentState(agent='{self.agent_name}', user='{self.user_id}', state={self.state})"