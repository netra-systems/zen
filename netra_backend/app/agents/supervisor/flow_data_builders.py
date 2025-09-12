"""Data structure builders for supervisor flow observability.

Provides spec-compliant data structure builders for TODO and flow events.
Each function must be  <= 8 lines as per architecture requirements.
"""
import time
from typing import Any, Dict, List, Optional


def build_spec_todo_data(action: str, task_id: str, description: str,
                        priority: str, dependencies: Optional[List[str]]) -> Dict[str, Any]:
    """Build spec-compliant TODO event data structure."""
    base_data = _create_todo_base_data(action, task_id, description)
    meta_data = _create_todo_meta_data(priority, dependencies, action)
    return {**base_data, **meta_data}

def _create_todo_base_data(action: str, task_id: str, description: str) -> Dict[str, Any]:
    """Create base TODO data fields."""
    return {
        "action": action,
        "task_id": task_id,
        "task_description": description
    }

def _create_todo_meta_data(priority: str, dependencies: Optional[List[str]], action: str) -> Dict[str, Any]:
    """Create TODO metadata fields."""
    return {
        "priority": priority,
        "dependencies": dependencies or [],
        "status": "pending" if action == "task_added" else None
    }


def build_spec_todo_status_data(action: str, task_id: str, status: str) -> Dict[str, Any]:
    """Build spec-compliant TODO status change data."""
    return {
        "action": action,
        "task_id": task_id,
        "status": status
    }


def build_spec_todo_failure_data(action: str, task_id: str, error: str) -> Dict[str, Any]:
    """Build spec-compliant TODO failure event data."""
    return {
        "action": action,
        "task_id": task_id,
        "status": "failed",
        "error": error
    }


def build_spec_flow_start_data(flow_id: str, total_steps: int) -> Dict[str, Any]:
    """Build spec-compliant flow initialization data."""
    return {
        "event": "flow_started",
        "flow_id": flow_id,
        "state_summary": {"total_steps": total_steps, "completed_steps": 0}
    }


def build_spec_step_data(event: str, flow_id: str, step_name: str, step_type: str) -> Dict[str, Any]:
    """Build spec-compliant flow step event data."""
    return {
        "event": event,
        "flow_id": flow_id,
        "step_name": step_name,
        "step_type": step_type
    }


def build_spec_step_completion_data(flow_id: str, step_name: str, duration: float) -> Dict[str, Any]:
    """Build spec-compliant step completion data with timing."""
    return {
        "event": "step_completed",
        "flow_id": flow_id,
        "step_name": step_name,
        "duration_seconds": round(duration, 2)
    }


def build_spec_decision_data(flow_id: str, decision: str, reason: str) -> Dict[str, Any]:
    """Build spec-compliant decision event data."""
    return {
        "event": "decision_made",
        "flow_id": flow_id,
        "decision": decision,
        "reason": reason
    }


def build_base_log_entry(event_type: str, correlation_id: str, run_id: str,
                        flow_state: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Build base log entry structure."""
    base_fields = _create_log_base_fields(event_type, correlation_id, run_id)
    state_fields = _create_log_state_fields(flow_state, data)
    return {**base_fields, **state_fields}

def _create_log_base_fields(event_type: str, correlation_id: str, run_id: str) -> Dict[str, Any]:
    """Create base log entry fields."""
    return {
        "type": event_type,
        "correlation_id": correlation_id,
        "run_id": run_id
    }

def _create_log_state_fields(flow_state: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create state and data fields for log entry."""
    return {
        "flow_state": flow_state,
        "timestamp": time.time(),
        **data
    }