"""Supervisor observability convenience functions for flow and TODO tracking.

Provides global access functions for supervisor flow logging without requiring
direct instance management. Each function must be  <= 8 lines as per architecture requirements.
"""
from typing import List, Optional

from netra_backend.app.agents.supervisor.flow_logger import SupervisorPipelineLogger

# Global supervisor flow logger instance
_global_flow_logger: Optional[SupervisorPipelineLogger] = None


def set_global_flow_logger(correlation_id: str, run_id: str) -> SupervisorPipelineLogger:
    """Set and return the global supervisor flow logger instance."""
    global _global_flow_logger
    _global_flow_logger = SupervisorPipelineLogger(correlation_id, run_id)
    return _global_flow_logger


def get_global_flow_logger() -> Optional[SupervisorPipelineLogger]:
    """Get the global supervisor flow logger instance."""
    return _global_flow_logger


# Convenience functions for direct logging without instance management
def log_todo_added(task_id: str, description: str, priority: str = "medium", 
                  dependencies: Optional[List[str]] = None) -> None:
    """Log task addition to supervisor TODO list."""
    if _global_flow_logger:
        _global_flow_logger.log_todo_added(task_id, description, priority, dependencies)


def log_todo_started(task_id: str) -> None:
    """Log task started in supervisor TODO list."""
    if _global_flow_logger:
        _global_flow_logger.log_todo_started(task_id)


def log_todo_completed(task_id: str) -> None:
    """Log task completion in supervisor TODO list."""
    if _global_flow_logger:
        _global_flow_logger.log_todo_completed(task_id)


def log_todo_failed(task_id: str, error: str) -> None:
    """Log task failure in supervisor TODO list."""
    if _global_flow_logger:
        _global_flow_logger.log_todo_failed(task_id, error)


def log_flow_started(flow_id: str, total_steps: int) -> None:
    """Log supervisor flow initiation."""
    if _global_flow_logger:
        _global_flow_logger.log_flow_started(flow_id, total_steps)


def log_step_started(flow_id: str, step_name: str, step_type: str) -> None:
    """Log supervisor flow step initiation."""
    if _global_flow_logger:
        _global_flow_logger.log_step_started(flow_id, step_name, step_type)


def log_step_completed(flow_id: str, step_name: str, duration: float) -> None:
    """Log supervisor flow step completion."""
    if _global_flow_logger:
        _global_flow_logger.log_step_completed(flow_id, step_name, duration)


def log_decision_made(flow_id: str, decision: str, reason: str) -> None:
    """Log supervisor decision with reasoning."""
    if _global_flow_logger:
        _global_flow_logger.log_decision_made(flow_id, decision, reason)