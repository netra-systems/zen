"""DEPRECATED: AgentStateTracker - Consolidated into AgentExecutionTracker.

⚠️ DEPRECATION NOTICE ⚠️
This module is deprecated and will be removed. All functionality has been
consolidated into netra_backend.app.core.agent_execution_tracker.AgentExecutionTracker.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: SSOT compliance & maintenance reduction
- Value Impact: Eliminates duplicate execution tracking systems, reducing bugs and complexity
- Strategic Impact: Single source of truth for agent execution tracking ensures consistency

Migration Guide:
OLD: from netra_backend.app.agents.agent_state_tracker import AgentStateTracker
NEW: from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker

All methods and functionality are preserved in AgentExecutionTracker.
"""

import warnings
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker

# Issue deprecation warning on import
warnings.warn(
    "AgentStateTracker is deprecated and will be removed. "
    "Use netra_backend.app.core.agent_execution_tracker.AgentExecutionTracker instead. "
    "All functionality has been consolidated into AgentExecutionTracker.",
    DeprecationWarning,
    stacklevel=2
)

# Create alias for backwards compatibility
AgentStateTracker = AgentExecutionTracker

# Explicit exports to maintain compatibility
__all__ = ['AgentStateTracker']