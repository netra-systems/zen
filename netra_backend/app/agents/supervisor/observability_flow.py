"""Supervisor flow observability module.

Provides SupervisorFlowLogger for tracking TODO lists and flow state.
Each function must be  <= 8 lines as per architecture requirements.
"""

import time
import uuid
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.supervisor.observability_flow_builders import (
    FlowDataBuilder,
)
from netra_backend.app.agents.supervisor.observability_todo_tracker import TodoTracker
from netra_backend.app.core.serialization.unified_json_handler import backend_json_handler
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SupervisorObservabilityLogger:
    """Manages flow observability for supervisor operations."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.log_format = "json"
        self._active_flows: Dict[str, Dict[str, Any]] = {}
        self.data_builder = FlowDataBuilder()
        self.todo_tracker = TodoTracker()

    def generate_flow_id(self) -> str:
        """Generate unique flow ID for tracking."""
        return f"flow_{str(uuid.uuid4())[:8]}"

    def start_flow(self, flow_id: str, correlation_id: str, total_steps: int) -> None:
        """Start tracking a supervisor flow."""
        if not self.enabled:
            return
        self._record_flow_start(flow_id, correlation_id, total_steps)
        self._log_flow_event("flow_started", flow_id, correlation_id)

    def _record_flow_start(self, flow_id: str, correlation_id: str, total_steps: int) -> None:
        """Record flow start data."""
        flow_data = self._build_flow_start_data(correlation_id, total_steps)
        self._active_flows[flow_id] = flow_data

    def _build_flow_start_data(self, correlation_id: str, total_steps: int) -> Dict[str, Any]:
        """Build flow start data dictionary."""
        base_data = {"correlation_id": correlation_id, "total_steps": total_steps}
        timing_data = {"completed_steps": 0, "start_time": time.time(), "current_phase": "initialization"}
        return {**base_data, **timing_data}

    def step_started(self, flow_id: str, step_name: str, step_type: str) -> None:
        """Log step start event."""
        if not self.enabled or flow_id not in self._active_flows:
            return
        self._update_flow_phase(flow_id, step_name)
        self._log_step_event("step_started", flow_id, step_name, step_type)

    def _update_flow_phase(self, flow_id: str, step_name: str) -> None:
        """Update current flow phase."""
        if flow_id in self._active_flows:
            self._active_flows[flow_id]["current_phase"] = step_name

    def step_completed(self, flow_id: str, step_name: str, step_type: str) -> None:
        """Log step completion event."""
        if not self.enabled or flow_id not in self._active_flows:
            return
        self._increment_completed_steps(flow_id)
        self._log_step_event("step_completed", flow_id, step_name, step_type)

    def _increment_completed_steps(self, flow_id: str) -> None:
        """Increment completed steps counter."""
        if flow_id in self._active_flows:
            self._active_flows[flow_id]["completed_steps"] += 1

    def complete_flow(self, flow_id: str) -> None:
        """Complete and cleanup flow tracking."""
        if not self.enabled or flow_id not in self._active_flows:
            return
        correlation_id = self._active_flows[flow_id]["correlation_id"]
        self._log_flow_event("flow_completed", flow_id, correlation_id)
        del self._active_flows[flow_id]

    def log_decision(self, flow_id: str, decision_point: str, chosen_path: str) -> None:
        """Log decision point in flow."""
        if not self.enabled:
            return
        data = self.data_builder.build_decision_data(self._active_flows, flow_id, decision_point, chosen_path)
        self._log_json_data("Supervisor decision", data)

    def log_parallel_execution(self, flow_id: str, agent_names: List[str]) -> None:
        """Log parallel execution start."""
        if not self.enabled:
            return
        data = self.data_builder.build_parallel_data(self._active_flows, flow_id, agent_names)
        self._log_json_data("Supervisor parallel execution", data)

    def log_sequential_execution(self, flow_id: str, agent_sequence: List[str]) -> None:
        """Log sequential execution plan."""
        if not self.enabled:
            return
        data = self.data_builder.build_sequential_data(self._active_flows, flow_id, agent_sequence)
        self._log_json_data("Supervisor sequential execution", data)

    def log_retry_attempt(self, flow_id: str, step_name: str, attempt_num: int) -> None:
        """Log retry attempt."""
        if not self.enabled:
            return
        data = self.data_builder.build_retry_data(self._active_flows, flow_id, step_name, attempt_num)
        self._log_json_data("Supervisor retry", data)

    def log_fallback_triggered(self, flow_id: str, failed_step: str, fallback_step: str) -> None:
        """Log fallback mechanism triggered."""
        if not self.enabled:
            return
        data = self.data_builder.build_fallback_data(self._active_flows, flow_id, failed_step, fallback_step)
        self._log_json_data("Supervisor fallback", data)

    def add_todo_task(self, task_id: str, description: str, priority: str, correlation_id: str) -> None:
        """Log TODO task addition."""
        if not self.enabled:
            return
        self.todo_tracker.record_todo_state(task_id, description, priority, "pending")
        data = self.todo_tracker.build_todo_event_data("task_added", task_id, description, priority, "pending", correlation_id)
        self._log_json_data("Supervisor TODO", data)

    def start_todo_task(self, task_id: str, correlation_id: str) -> None:
        """Log TODO task start."""
        if not self.enabled:
            return
        self.todo_tracker.update_todo_status(task_id, "in_progress")
        data = self.todo_tracker.build_todo_status_data("task_started", task_id, correlation_id)
        self._log_json_data("Supervisor TODO", data)

    def complete_todo_task(self, task_id: str, correlation_id: str) -> None:
        """Log TODO task completion."""
        if not self.enabled:
            return
        self.todo_tracker.update_todo_status(task_id, "completed")
        data = self.todo_tracker.build_todo_status_data("task_completed", task_id, correlation_id)
        self._log_json_data("Supervisor TODO", data)

    def fail_todo_task(self, task_id: str, correlation_id: str, error_msg: str = "") -> None:
        """Log TODO task failure."""
        if not self.enabled:
            return
        self.todo_tracker.update_todo_status(task_id, "failed")
        data = self.todo_tracker.build_todo_failure_data(task_id, correlation_id, error_msg)
        self._log_json_data("Supervisor TODO", data)

    def _log_flow_event(self, event: str, flow_id: str, correlation_id: str) -> None:
        """Log flow event with state data."""
        data = self.data_builder.build_flow_event_data(self._active_flows, event, flow_id, correlation_id)
        self._log_json_data("Supervisor flow", data)

    def _log_step_event(self, event: str, flow_id: str, step_name: str, step_type: str) -> None:
        """Log step event with context."""
        data = self.data_builder.build_step_event_data(self._active_flows, event, flow_id, step_name, step_type)
        self._log_json_data("Supervisor flow", data)

    def _log_json_data(self, log_prefix: str, data: Dict[str, Any]) -> None:
        """Log data as JSON format."""
        if self.log_format == "json":
            logger.info(f"{log_prefix}: {backend_json_handler.dumps(data)}")

    def get_active_flows(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active flows."""
        return self._active_flows.copy()

    def get_todo_states(self) -> Dict[str, Dict[str, Any]]:
        """Get current TODO task states."""
        return self.todo_tracker.get_todo_states()


# Global supervisor flow logger instance
_supervisor_flow_logger: Optional[SupervisorObservabilityLogger] = None


def get_supervisor_flow_logger() -> SupervisorObservabilityLogger:
    """Get the global supervisor flow logger instance."""
    global _supervisor_flow_logger
    if _supervisor_flow_logger is None:
        _supervisor_flow_logger = SupervisorObservabilityLogger()
    return _supervisor_flow_logger