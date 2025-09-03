"""Enhanced state management logic for supervisor agent."""

from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.state_manager_core import StateManagerCore
from netra_backend.app.schemas.agent_state import AgentPhase, CheckpointType


class AgentStateManager(StateManagerCore):
    """Enhanced agent state manager with atomic persistence and recovery."""
    
    def __init__(self, db_session):
        super().__init__(db_session)
    
    # All methods are now inherited from StateManagerCore and its component managers
    # This maintains backward compatibility while using the modular structure


class SessionlessAgentStateManager:
    """Agent state manager that doesn't store db_session globally.
    
    Instead, it accepts sessions as method parameters to ensure proper
    isolation between requests.
    """
    
    def __init__(self):
        # No db_session stored - sessions passed to methods
        pass
    
    async def initialize_state_with_session(self, session: AsyncSession, 
                                          prompt: str, thread_id: str, 
                                          user_id: str, run_id: str) -> DeepAgentState:
        """Initialize agent state with recovery support using provided session."""
        # Create temporary state manager with this session for this operation
        temp_state_manager = AgentStateManager(session)
        return await temp_state_manager.initialize_state(prompt, thread_id, user_id, run_id)
    
    async def save_state_checkpoint_with_session(self, session: AsyncSession,
                                               state: DeepAgentState, run_id: str,
                                               thread_id: str, user_id: str,
                                               checkpoint_type=None, agent_phase=None) -> bool:
        """Save state checkpoint using provided session."""
        from netra_backend.app.schemas.agent_state import CheckpointType
        if checkpoint_type is None:
            checkpoint_type = CheckpointType.AUTO
            
        # Create temporary state manager with this session for this operation
        temp_state_manager = AgentStateManager(session)
        return await temp_state_manager.save_state_checkpoint(
            state, run_id, thread_id, user_id, checkpoint_type, agent_phase)
    
    async def handle_agent_crash_recovery_with_session(self, session: AsyncSession,
                                                       run_id: str, thread_id: str,
                                                       failure_reason: str):
        """Handle agent crash recovery using provided session."""
        # Create temporary state manager with this session for this operation
        temp_state_manager = AgentStateManager(session)
        return await temp_state_manager.handle_agent_crash_recovery(run_id, thread_id, failure_reason)


# Backward compatibility alias
StateManager = AgentStateManager