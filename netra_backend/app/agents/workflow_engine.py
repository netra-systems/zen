"""
Workflow Engine: Compatibility module for test imports.

This module provides backward compatibility for test files that import
WorkflowEngine from the agents.workflow_engine module.
"""

# Re-export from supervisor module for backward compatibility
from netra_backend.app.agents.supervisor.workflow_execution import SupervisorWorkflowExecutor

# Compatibility alias
WorkflowEngine = SupervisorWorkflowExecutor

__all__ = [
    "WorkflowEngine",
    "SupervisorWorkflowExecutor",
]