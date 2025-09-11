"""DEPRECATED: AgentExecutionTimeoutManager - Consolidated into AgentExecutionTracker.

⚠️ DEPRECATION NOTICE ⚠️
This module is deprecated and will be removed. All functionality has been
consolidated into netra_backend.app.core.agent_execution_tracker.AgentExecutionTracker.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: SSOT compliance & maintenance reduction
- Value Impact: Eliminates duplicate timeout management systems, reducing bugs and complexity
- Strategic Impact: Single source of truth for timeout handling ensures consistency across all agent executions

Migration Guide:
OLD: from netra_backend.app.agents.execution_timeout_manager import AgentExecutionTimeoutManager
NEW: from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker

All timeout management, circuit breaker patterns, and timeout configuration 
are now available in AgentExecutionTracker.
"""

import warnings
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker

# Issue deprecation warning on import
warnings.warn(
    "AgentExecutionTimeoutManager is deprecated and will be removed. "
    "Use netra_backend.app.core.agent_execution_tracker.AgentExecutionTracker instead. "
    "All timeout management functionality has been consolidated into AgentExecutionTracker.",
    DeprecationWarning,
    stacklevel=2
)

# Create alias for backwards compatibility
AgentExecutionTimeoutManager = AgentExecutionTracker

# Explicit exports to maintain compatibility
__all__ = ['AgentExecutionTimeoutManager']