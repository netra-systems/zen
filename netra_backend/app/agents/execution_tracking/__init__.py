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

from netra_backend.app.agents.execution_tracking.registry import ExecutionRegistry
from netra_backend.app.agents.execution_tracking.heartbeat import HeartbeatMonitor
from netra_backend.app.agents.execution_tracking.timeout import TimeoutManager
from netra_backend.app.agents.execution_tracking.tracker import ExecutionTracker

__all__ = [
    "ExecutionRegistry",
    "HeartbeatMonitor", 
    "TimeoutManager",
    "ExecutionTracker"
]