"""Enhanced state management logic for supervisor agent."""

from typing import Optional, Tuple
from app.agents.state import DeepAgentState
from app.schemas.agent_state import CheckpointType, AgentPhase
from .state_manager_core import StateManagerCore


class StateManager(StateManagerCore):
    """Enhanced state manager with atomic persistence and recovery."""
    
    def __init__(self, db_session_factory):
        super().__init__(db_session_factory)
    
    # All methods are now inherited from StateManagerCore and its component managers
    # This maintains backward compatibility while using the modular structure