"""Execution tracking package for agent death detection and recovery.

This package provides comprehensive execution tracking to prevent and detect
agent death scenarios that cause silent failures and infinite loading states.

Key Components:
- ExecutionRegistry: Central tracking of all agent executions
- HeartbeatMonitor: Detects dead/stuck agents via heartbeats  
- TimeoutManager: Enforces execution timeouts
- ExecutionTracker: Orchestrates tracking and recovery

Business Value: Eliminates silent failures that cause 100% UX degradation.
"""

# SSOT Compatibility Layer: Import from SSOT implementation where available
try:
    from netra_backend.app.agents.execution_tracking.registry import ExecutionRegistry
    from netra_backend.app.agents.execution_tracking.heartbeat import HeartbeatMonitor
    from netra_backend.app.agents.execution_tracking.tracker import ExecutionTracker
    
    # TimeoutManager functionality is now consolidated in SSOT AgentExecutionTracker
    from netra_backend.app.core.agent_execution_tracker import TimeoutConfig as TimeoutManager
    
    __all__ = [
        "ExecutionRegistry",
        "HeartbeatMonitor", 
        "TimeoutManager",
        "ExecutionTracker"
    ]
except ImportError as e:
    # Fallback if some modules are missing
    import warnings
    warnings.warn(f"Execution tracking module import failed: {e}. Using SSOT fallbacks.", ImportWarning)
    
    from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker as ExecutionTracker
    from netra_backend.app.core.agent_execution_tracker import TimeoutConfig as TimeoutManager
    
    __all__ = ["ExecutionTracker", "TimeoutManager"]