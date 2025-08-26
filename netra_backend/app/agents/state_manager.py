"""
Agent State Manager: Compatibility module for test imports.

This module provides backward compatibility for test files that import
AgentStateManager from the agents.state_manager module.
"""

# Re-export from supervisor module for backward compatibility
from netra_backend.app.agents.supervisor.state_manager import (
    AgentStateManager,
    StateManager,
)

__all__ = [
    "AgentStateManager",
    "StateManager",
]