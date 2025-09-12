"""TODO tracker module for supervisor observability.

Handles TODO task state tracking and data building.
Each function must be  <= 8 lines as per architecture requirements.
"""

import time
from typing import Any, Dict


class TodoTracker:
    """Tracks TODO task states and builds logging data."""

    def __init__(self):
        self._todo_states: Dict[str, Dict[str, Any]] = {}

    def record_todo_state(self, task_id: str, description: str, priority: str, status: str) -> None:
        """Record TODO task state."""
        self._todo_states[task_id] = {
            "description": description,
            "priority": priority,
            "status": status,
            "created_time": time.time()
        }

    def update_todo_status(self, task_id: str, status: str) -> None:
        """Update TODO task status."""
        if task_id in self._todo_states:
            self._todo_states[task_id]["status"] = status

    def get_todo_states(self) -> Dict[str, Dict[str, Any]]:
        """Get current TODO task states."""
        return self._todo_states.copy()

    def build_todo_event_data(self, action: str, task_id: str, description: str, 
                             priority: str, status: str, correlation_id: str) -> Dict[str, Any]:
        """Build TODO event data structure."""
        return self._create_todo_base_data(action, task_id, description, priority, status, correlation_id)

    def _create_todo_base_data(self, action: str, task_id: str, description: str, 
                              priority: str, status: str, correlation_id: str) -> Dict[str, Any]:
        """Create base TODO data structure."""
        base_fields = self._create_todo_base_fields(action, task_id, description)
        meta_fields = self._create_todo_meta_fields(priority, status, correlation_id)
        return {**base_fields, **meta_fields, "timestamp": time.time()}

    def _create_todo_base_fields(self, action: str, task_id: str, description: str) -> Dict[str, Any]:
        """Create base TODO fields."""
        return {
            "type": "supervisor_todo",
            "action": action,
            "task_id": task_id,
            "task_description": description
        }

    def _create_todo_meta_fields(self, priority: str, status: str, correlation_id: str) -> Dict[str, Any]:
        """Create TODO metadata fields."""
        return {
            "priority": priority,
            "status": status,
            "correlation_id": correlation_id
        }

    def build_todo_status_data(self, action: str, task_id: str, correlation_id: str) -> Dict[str, Any]:
        """Build TODO status change data."""
        task_data = self._todo_states.get(task_id, {})
        description = task_data.get("description", "")
        priority = task_data.get("priority", "medium")
        status = task_data.get("status", "unknown")
        return self._create_todo_base_data(action, task_id, description, priority, status, correlation_id)

    def build_todo_failure_data(self, task_id: str, correlation_id: str, error_msg: str) -> Dict[str, Any]:
        """Build TODO failure data."""
        base_data = self.build_todo_status_data("task_failed", task_id, correlation_id)
        base_data["error_message"] = error_msg
        return base_data

    def get_task_data(self, task_id: str) -> Dict[str, Any]:
        """Get task data for a specific task ID."""
        return self._todo_states.get(task_id, {})

    def has_task(self, task_id: str) -> bool:
        """Check if task exists."""
        return task_id in self._todo_states

    def remove_task(self, task_id: str) -> None:
        """Remove task from tracking."""
        self._todo_states.pop(task_id, None)