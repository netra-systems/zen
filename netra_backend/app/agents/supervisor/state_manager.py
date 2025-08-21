"""Enhanced state management logic for supervisor agent."""

from typing import Optional, Tuple
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent_state import CheckpointType, AgentPhase
from netra_backend.app.state_manager_core import StateManagerCore


class AgentStateManager(StateManagerCore):
    """Enhanced agent state manager with atomic persistence and recovery."""
    
    def __init__(self, db_session):
        super().__init__(db_session)
    
    # All methods are now inherited from StateManagerCore and its component managers
    # This maintains backward compatibility while using the modular structure


# Backward compatibility alias
StateManager = AgentStateManager