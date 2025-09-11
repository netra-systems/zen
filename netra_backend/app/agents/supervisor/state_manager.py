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
from netra_backend.app.services.user_execution_context import UserExecutionContext


class AgentStateManager:
    """
    Agent State Manager migrated to UserExecutionContext pattern.
    
    This class provides state management using UserExecutionContext for secure user isolation.
    Deprecated methods maintain backward compatibility with deprecation warnings.
    The actual state management functionality has been consolidated into the unified system.
    """
    
    def __init__(self):
        self.contexts: Dict[str, UserExecutionContext] = {}
    
    async def get_context(self, agent_id: str) -> Optional[UserExecutionContext]:
        """Get user execution context by agent ID."""
        return self.contexts.get(agent_id)
    
    async def get_state(self, agent_id: str) -> Optional[UserExecutionContext]:
        """Get agent state by ID - deprecated, use get_context instead."""
        import warnings
        warnings.warn(
            "get_state is deprecated, use get_context instead for UserExecutionContext pattern",
            DeprecationWarning,
            stacklevel=2
        )
        return self.contexts.get(agent_id)
    
    async def save_context(self, agent_id: str, user_context: UserExecutionContext) -> bool:
        """Save user execution context."""
        self.contexts[agent_id] = user_context
        return True
    
    async def save_state(self, agent_id: str, user_context: UserExecutionContext) -> bool:
        """Save agent state - deprecated, use save_context instead."""
        import warnings
        warnings.warn(
            "save_state is deprecated, use save_context instead for UserExecutionContext pattern",
            DeprecationWarning,
            stacklevel=2
        )
        self.contexts[agent_id] = user_context
        return True
    
    async def delete_context(self, agent_id: str) -> bool:
        """Delete user execution context."""
        if agent_id in self.contexts:
            del self.contexts[agent_id]
            return True
        return False
    
    async def delete_state(self, agent_id: str) -> bool:
        """Delete agent state - deprecated, use delete_context instead."""
        import warnings
        warnings.warn(
            "delete_state is deprecated, use delete_context instead for UserExecutionContext pattern",
            DeprecationWarning,
            stacklevel=2
        )
        if agent_id in self.contexts:
            del self.contexts[agent_id]
            return True
        return False
    
    async def checkpoint_state(self, agent_id: str) -> bool:
        """Create a checkpoint of agent state."""
        # Stub implementation for backward compatibility
        return True
    
    async def restore_context(self, agent_id: str, checkpoint_id: str) -> Optional[UserExecutionContext]:
        """Restore user execution context from checkpoint."""
        # Stub implementation for backward compatibility
        return self.contexts.get(agent_id)
    
    async def restore_state(self, agent_id: str, checkpoint_id: str) -> Optional[UserExecutionContext]:
        """Restore agent state from checkpoint - deprecated, use restore_context instead."""
        import warnings
        warnings.warn(
            "restore_state is deprecated, use restore_context instead for UserExecutionContext pattern",
            DeprecationWarning,
            stacklevel=2
        )
        return self.contexts.get(agent_id)


class StateManager(AgentStateManager):
    """Alias for AgentStateManager for backward compatibility."""
    pass


__all__ = [
    "AgentStateManager",
    "StateManager",
]