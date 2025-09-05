"""
Supervisor State Manager Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - Provide state management for agent execution
- Value Impact: Ensures consistent agent state across executions
- Strategic Impact: Reduces state-related bugs and improves reliability

This module provides state management functionality for the supervisor agent system.
"""

from typing import Any, Dict, Optional
from netra_backend.app.agents.state import DeepAgentState


class AgentStateManager:
    """
    Agent State Manager for backward compatibility.
    
    This class provides minimal functionality for tests that still import AgentStateManager.
    The actual state management functionality has been consolidated into the unified system.
    """
    
    def __init__(self):
        self.states: Dict[str, DeepAgentState] = {}
    
    async def get_state(self, agent_id: str) -> Optional[DeepAgentState]:
        """Get agent state by ID."""
        return self.states.get(agent_id)
    
    async def save_state(self, agent_id: str, state: DeepAgentState) -> bool:
        """Save agent state."""
        self.states[agent_id] = state
        return True
    
    async def delete_state(self, agent_id: str) -> bool:
        """Delete agent state."""
        if agent_id in self.states:
            del self.states[agent_id]
            return True
        return False
    
    async def checkpoint_state(self, agent_id: str) -> bool:
        """Create a checkpoint of agent state."""
        # Stub implementation for backward compatibility
        return True
    
    async def restore_state(self, agent_id: str, checkpoint_id: str) -> Optional[DeepAgentState]:
        """Restore agent state from checkpoint."""
        # Stub implementation for backward compatibility
        return self.states.get(agent_id)


class StateManager(AgentStateManager):
    """Alias for AgentStateManager for backward compatibility."""
    pass


__all__ = [
    "AgentStateManager",
    "StateManager",
]