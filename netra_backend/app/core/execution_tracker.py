"""
Execution Tracker - SSOT Compatibility Layer
=============================================
CRITICAL: This module provides backward compatibility for legacy imports.

 WARNING: [U+FE0F]  DEPRECATED: This module is now a compatibility layer.
    New code should import from:
    `from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, ExecutionState`

SSOT Implementation: netra_backend.app.core.agent_execution_tracker.py

Compatibility Aliases:
- ExecutionState -> AgentExecutionTracker.ExecutionState (9-state comprehensive enum)  
- ExecutionTracker -> AgentExecutionTracker (full consolidation)
- get_execution_tracker() -> get_execution_tracker() from SSOT module

Business Impact:
- Preserves backward compatibility for 40+ test files
- Enables gradual migration to SSOT implementation
- Maintains existing API contracts while consolidating functionality
"""

# SSOT Compatibility Layer - Import from canonical implementation
from netra_backend.app.core.agent_execution_tracker import (
    ExecutionState as _SSOT_ExecutionState,
    AgentExecutionTracker as _SSOT_AgentExecutionTracker,
    ExecutionRecord as _SSOT_ExecutionRecord,
    get_execution_tracker as _ssot_get_execution_tracker,
    initialize_tracker as _ssot_initialize_tracker,
    shutdown_tracker as _ssot_shutdown_tracker
)
from netra_backend.app.logging_config import central_logger
from typing import Any, Dict, List, Optional
from uuid import UUID
import warnings

logger = central_logger.get_logger(__name__)

# BACKWARD COMPATIBILITY ALIAS: ExecutionState -> SSOT ExecutionState
# The SSOT implementation has 9 states (vs 6 here) for comprehensive tracking
ExecutionState = _SSOT_ExecutionState

# Issue deprecation warning for ExecutionState imports
def _warn_execution_state_deprecated():
    warnings.warn(
        "Importing ExecutionState from execution_tracker.py is deprecated. "
        "Use 'from netra_backend.app.core.agent_execution_tracker import ExecutionState' instead.",
        DeprecationWarning,
        stacklevel=3
    )

# BACKWARD COMPATIBILITY ALIAS: ExecutionRecord -> SSOT ExecutionRecord  
# The SSOT implementation has enhanced fields and methods
ExecutionRecord = _SSOT_ExecutionRecord

# Issue deprecation warning for ExecutionRecord imports
def _warn_execution_record_deprecated():
    warnings.warn(
        "Importing ExecutionRecord from execution_tracker.py is deprecated. "
        "Use 'from netra_backend.app.core.agent_execution_tracker import ExecutionRecord' instead.",
        DeprecationWarning,
        stacklevel=3
    )

# BACKWARD COMPATIBILITY CLASS: ExecutionTracker -> SSOT AgentExecutionTracker
# The SSOT implementation has consolidated functionality from multiple tracker classes
class ExecutionTracker(_SSOT_AgentExecutionTracker):
    """
    DEPRECATED: Backward compatibility wrapper around AgentExecutionTracker.
    
     WARNING: [U+FE0F]  This class is now a thin wrapper around the SSOT AgentExecutionTracker.
        New code should use AgentExecutionTracker directly:
        
        from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
        
    The SSOT implementation provides:
    - Enhanced 9-state ExecutionState enum  
    - Consolidated state management methods
    - Circuit breaker functionality
    - WebSocket event integration
    - Timeout management
    """
    
    def __init__(self):
        # Initialize the SSOT AgentExecutionTracker with backward-compatible parameters
        super().__init__(
            heartbeat_timeout=10,
            execution_timeout=30,  # Match original timeout
            cleanup_interval=60
        )
        
        # Issue deprecation warning
        warnings.warn(
            "ExecutionTracker is deprecated. Use AgentExecutionTracker directly:\n"
            "from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Backward compatibility properties mapping
        # Map old property names to new implementation
        self.executions = self._executions
        self.active_executions = self._active_executions
        self.failed_executions = []  # Computed property from metrics
        self.monitoring_task = self._monitor_task
        self.recovery_callbacks = self._death_callbacks + self._timeout_callbacks
        self._lock = None  # SSOT uses different locking mechanism
        self._persistence = None
        
        logger.debug("Created ExecutionTracker compatibility wrapper")
    
    @property
    def failed_executions(self) -> List[UUID]:
        """Backward compatibility property for failed executions."""
        # Compute from metrics
        metrics = self.get_metrics()
        return []  # For now, return empty list - full conversion would need UUID tracking
    
    @failed_executions.setter  
    def failed_executions(self, value: List[UUID]):
        """Setter for backward compatibility (no-op)."""
        pass


# BACKWARD COMPATIBILITY: Redirect to SSOT functions
def get_execution_tracker() -> ExecutionTracker:
    """
    Get the global execution tracker instance.
    
     WARNING: [U+FE0F]  DEPRECATED: Use the SSOT function instead:
        from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
    
    Returns:
        ExecutionTracker: Compatibility wrapper around AgentExecutionTracker
    """
    warnings.warn(
        "get_execution_tracker from execution_tracker.py is deprecated. "
        "Use 'from netra_backend.app.core.agent_execution_tracker import get_execution_tracker' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Get SSOT instance
    ssot_tracker = _ssot_get_execution_tracker()
    
    # If it's already the right type, return it
    if isinstance(ssot_tracker, ExecutionTracker):
        return ssot_tracker
    
    # Create compatibility wrapper
    # Note: This is a bit of a hack, but necessary for backward compatibility
    wrapper = ExecutionTracker.__new__(ExecutionTracker)
    wrapper.__dict__.update(ssot_tracker.__dict__)
    
    # Add compatibility properties
    wrapper.executions = ssot_tracker._executions
    wrapper.active_executions = ssot_tracker._active_executions
    wrapper.failed_executions = []
    wrapper.monitoring_task = ssot_tracker._monitor_task
    wrapper.recovery_callbacks = ssot_tracker._death_callbacks + ssot_tracker._timeout_callbacks
    wrapper._lock = None
    wrapper._persistence = None
    
    return wrapper


async def init_execution_tracker():
    """
    Initialize and start the execution tracker.
    
     WARNING: [U+FE0F]  DEPRECATED: Use the SSOT function instead:
        from netra_backend.app.core.agent_execution_tracker import initialize_tracker
    """
    warnings.warn(
        "init_execution_tracker is deprecated. "
        "Use 'from netra_backend.app.core.agent_execution_tracker import initialize_tracker' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    tracker = await _ssot_initialize_tracker()
    logger.info("Execution tracker initialized and monitoring started (via compatibility layer)")
    return tracker


# Additional compatibility aliases
initialize_tracker = _ssot_initialize_tracker
shutdown_tracker = _ssot_shutdown_tracker