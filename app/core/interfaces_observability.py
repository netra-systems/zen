"""Observability interfaces - Single source of truth.

Consolidated supervisor flow logging with comprehensive TODO tracking,
metrics collection, and structured observability features.
Follows 300-line limit and 8-line functions.
"""

import time
import json
import uuid
from typing import Dict, Any, Optional, List
from enum import Enum

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class FlowState(Enum):
    """Flow execution states."""
    PENDING = "pending"
    STARTED = "started"
    AGENT_EXECUTING = "agent_executing"
    AGENT_COMPLETED = "agent_completed"
    COMPLETED = "completed"
    FAILED = "failed"


class TodoState(Enum):
    """TODO item states within supervisor flows."""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CoreSupervisorFlowLogger:
    """Unified supervisor flow logger with comprehensive tracking and observability."""
    
    def __init__(self, correlation_id: Optional[str] = None, run_id: Optional[str] = None, enabled: bool = True):
        """Initialize flow logger with tracking capabilities."""
        self.correlation_id = correlation_id or f"corr_{str(uuid.uuid4())[:8]}"
        self.run_id = run_id or f"run_{str(uuid.uuid4())[:8]}"
        self.enabled = enabled
        self.flow_state = FlowState.PENDING
        self.start_time = time.time()
        self.log_format = "json"
        
        # Tracking data structures
        self.todos: Dict[str, Dict[str, Any]] = {}
        self.agent_executions: List[Dict[str, Any]] = []
        self._active_flows: Dict[str, Dict[str, Any]] = {}
    
    # Flow lifecycle methods
    
    def generate_flow_id(self) -> str:
        """Generate unique flow ID for tracking."""
        return f"flow_{str(uuid.uuid4())[:8]}"
    
    def log_flow_start(self, pipeline_name: str, steps: List[str]) -> None:
        """Log the start of a supervisor flow."""
        self.flow_state = FlowState.STARTED
        flow_data = self._build_flow_start_data(pipeline_name, steps)
        self._log_structured_data("supervisor_flow_start", flow_data)
    
    def start_flow(self, flow_id: str, correlation_id: str, total_steps: int) -> None:
        """Start tracking a supervisor flow with observability."""
        if not self.enabled:
            return
        self._record_flow_start(flow_id, correlation_id, total_steps)
        self._log_flow_event("flow_started", flow_id, correlation_id)
    
    def log_flow_completion(self, success: bool, total_steps: int, failed_steps: int) -> None:
        """Log the completion of the entire flow."""
        self.flow_state = FlowState.COMPLETED if success else FlowState.FAILED
        completion_data = self._build_flow_completion_data(success, total_steps, failed_steps)
        self._log_structured_data("supervisor_flow_completion", completion_data)
    
    def complete_flow(self, flow_id: str) -> None:
        """Complete and cleanup flow tracking."""
        if not self.enabled or flow_id not in self._active_flows:
            return
        correlation_id = self._active_flows[flow_id]["correlation_id"]
        self._log_flow_event("flow_completed", flow_id, correlation_id)
        del self._active_flows[flow_id]
    
    # Agent execution methods
    
    def log_agent_start(self, agent_name: str, step_number: int) -> None:
        """Log the start of an agent execution."""
        self.flow_state = FlowState.AGENT_EXECUTING
        agent_data = self._build_agent_start_data(agent_name, step_number)
        self._log_structured_data("supervisor_agent_start", agent_data)
    
    def log_agent_completion(self, agent_name: str, success: bool, duration: float) -> None:
        """Log the completion of an agent execution."""
        self.flow_state = FlowState.AGENT_COMPLETED
        completion_data = self._build_agent_completion_data(agent_name, success, duration)
        self._log_structured_data("supervisor_agent_completion", completion_data)
    
    def step_started(self, flow_id: str, step_name: str, step_type: str) -> None:
        """Log step start event."""
        if not self.enabled or flow_id not in self._active_flows:
            return
        self._update_flow_phase(flow_id, step_name)
        self._log_step_event("step_started", flow_id, step_name, step_type)
    
    def step_completed(self, flow_id: str, step_name: str, step_type: str) -> None:
        """Log step completion event."""
        if not self.enabled or flow_id not in self._active_flows:
            return
        self._increment_completed_steps(flow_id)
        self._log_step_event("step_completed", flow_id, step_name, step_type)
    
    # TODO tracking methods
    
    def create_todo(self, todo_id: str, description: str, agent_name: str) -> None:
        """Create a new TODO item in the flow."""
        todo_data = self._build_todo_data(description, agent_name, TodoState.CREATED)
        self.todos[todo_id] = todo_data
        self._log_structured_data("supervisor_todo_created", {**todo_data, "todo_id": todo_id})
    
    def add_todo_task(self, task_id: str, description: str, priority: str, correlation_id: str) -> None:
        """Log TODO task addition with priority tracking."""
        if not self.enabled:
            return
        todo_data = self._build_todo_task_data("task_added", task_id, description, priority, "pending", correlation_id)
        self._log_json_data("Supervisor TODO", todo_data)
    
    def update_todo_state(self, todo_id: str, new_state: TodoState) -> None:
        """Update TODO item state with timestamp tracking."""
        if todo_id not in self.todos:
            return
        self._update_todo_timestamps(todo_id, new_state)
        self._log_todo_state_change(todo_id, new_state)
    
    def start_todo_task(self, task_id: str, correlation_id: str) -> None:
        """Log TODO task start."""
        if not self.enabled:
            return
        todo_data = self._build_todo_status_data("task_started", task_id, correlation_id)
        self._log_json_data("Supervisor TODO", todo_data)
    
    def complete_todo_task(self, task_id: str, correlation_id: str) -> None:
        """Log TODO task completion."""
        if not self.enabled:
            return
        todo_data = self._build_todo_status_data("task_completed", task_id, correlation_id)
        self._log_json_data("Supervisor TODO", todo_data)
    
    def fail_todo_task(self, task_id: str, correlation_id: str, error_msg: str = "") -> None:
        """Log TODO task failure."""
        if not self.enabled:
            return
        todo_data = self._build_todo_failure_data(task_id, correlation_id, error_msg)
        self._log_json_data("Supervisor TODO", todo_data)
    
    # Decision and execution tracking
    
    def log_decision(self, flow_id: str, decision_point: str, chosen_path: str) -> None:
        """Log decision point in flow."""
        if not self.enabled:
            return
        decision_data = self._build_decision_data(flow_id, decision_point, chosen_path)
        self._log_json_data("Supervisor decision", decision_data)
    
    def log_parallel_execution(self, flow_id: str, agent_names: List[str]) -> None:
        """Log parallel execution start."""
        if not self.enabled:
            return
        parallel_data = self._build_parallel_execution_data(flow_id, agent_names)
        self._log_json_data("Supervisor parallel execution", parallel_data)
    
    def log_retry_attempt(self, flow_id: str, step_name: str, attempt_num: int) -> None:
        """Log retry attempt."""
        if not self.enabled:
            return
        retry_data = self._build_retry_data(flow_id, step_name, attempt_num)
        self._log_json_data("Supervisor retry", retry_data)
    
    def log_fallback_triggered(self, flow_id: str, failed_step: str, fallback_step: str) -> None:
        """Log fallback mechanism triggered."""
        if not self.enabled:
            return
        fallback_data = self._build_fallback_data(flow_id, failed_step, fallback_step)
        self._log_json_data("Supervisor fallback", fallback_data)
    
    # Data building helper methods
    
    def _build_flow_start_data(self, pipeline_name: str, steps: List[str]) -> Dict[str, Any]:
        """Build flow start data structure."""
        return {
            "pipeline_name": pipeline_name, "steps": steps, "step_count": len(steps),
            "estimated_duration": len(steps) * 30  # 30s per step estimate
        }
    
    def _build_agent_start_data(self, agent_name: str, step_number: int) -> Dict[str, Any]:
        """Build agent start data structure."""
        return {"agent_name": agent_name, "step_number": step_number, "step_started_at": time.time()}
    
    def _build_agent_completion_data(self, agent_name: str, success: bool, duration: float) -> Dict[str, Any]:
        """Build agent completion data structure."""
        return {
            "agent_name": agent_name, "success": success,
            "duration_seconds": round(duration, 2), "status": "success" if success else "failed"
        }
    
    def _build_flow_completion_data(self, success: bool, total_steps: int, failed_steps: int) -> Dict[str, Any]:
        """Build flow completion data structure."""
        duration = time.time() - self.start_time
        return {
            "success": success, "total_steps": total_steps, "failed_steps": failed_steps,
            "total_duration_seconds": round(duration, 2), "final_state": self.flow_state.value
        }
    
    def _build_todo_data(self, description: str, agent_name: str, state: TodoState) -> Dict[str, Any]:
        """Build TODO data structure."""
        return {
            "description": description, "agent_name": agent_name,
            "state": state.value, "created_at": time.time()
        }
    
    def _build_todo_task_data(self, event: str, task_id: str, description: str, 
                             priority: str, status: str, correlation_id: str) -> Dict[str, Any]:
        """Build TODO task event data."""
        return {
            "event": event, "task_id": task_id, "description": description,
            "priority": priority, "status": status, "correlation_id": correlation_id,
            "timestamp": time.time()
        }
    
    def _build_todo_status_data(self, event: str, task_id: str, correlation_id: str) -> Dict[str, Any]:
        """Build TODO status update data."""
        return {"event": event, "task_id": task_id, "correlation_id": correlation_id, "timestamp": time.time()}
    
    def _build_todo_failure_data(self, task_id: str, correlation_id: str, error_msg: str) -> Dict[str, Any]:
        """Build TODO failure data."""
        return {
            "event": "task_failed", "task_id": task_id, "correlation_id": correlation_id,
            "error_message": error_msg, "timestamp": time.time()
        }
    
    def _build_decision_data(self, flow_id: str, decision_point: str, chosen_path: str) -> Dict[str, Any]:
        """Build decision point data."""
        return {
            "flow_id": flow_id, "decision_point": decision_point,
            "chosen_path": chosen_path, "timestamp": time.time()
        }
    
    def _build_parallel_execution_data(self, flow_id: str, agent_names: List[str]) -> Dict[str, Any]:
        """Build parallel execution data."""
        return {"flow_id": flow_id, "agent_names": agent_names, "agent_count": len(agent_names), "timestamp": time.time()}
    
    def _build_retry_data(self, flow_id: str, step_name: str, attempt_num: int) -> Dict[str, Any]:
        """Build retry attempt data."""
        return {"flow_id": flow_id, "step_name": step_name, "attempt_number": attempt_num, "timestamp": time.time()}
    
    def _build_fallback_data(self, flow_id: str, failed_step: str, fallback_step: str) -> Dict[str, Any]:
        """Build fallback trigger data."""
        return {
            "flow_id": flow_id, "failed_step": failed_step,
            "fallback_step": fallback_step, "timestamp": time.time()
        }
    
    # State management helper methods
    
    def _record_flow_start(self, flow_id: str, correlation_id: str, total_steps: int) -> None:
        """Record flow start data."""
        flow_data = {
            "correlation_id": correlation_id, "total_steps": total_steps,
            "completed_steps": 0, "start_time": time.time(), "current_phase": "initialization"
        }
        self._active_flows[flow_id] = flow_data
    
    def _update_flow_phase(self, flow_id: str, step_name: str) -> None:
        """Update current flow phase."""
        if flow_id in self._active_flows:
            self._active_flows[flow_id]["current_phase"] = step_name
    
    def _increment_completed_steps(self, flow_id: str) -> None:
        """Increment completed steps counter."""
        if flow_id in self._active_flows:
            self._active_flows[flow_id]["completed_steps"] += 1
    
    def _update_todo_timestamps(self, todo_id: str, new_state: TodoState) -> None:
        """Update TODO timestamps for state change."""
        self.todos[todo_id]["state"] = new_state.value
        if new_state == TodoState.IN_PROGRESS:
            self.todos[todo_id]["started_at"] = time.time()
        elif new_state in [TodoState.COMPLETED, TodoState.FAILED]:
            self.todos[todo_id]["completed_at"] = time.time()
    
    # Logging helper methods
    
    def _log_structured_data(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log structured data with consistent format."""
        log_entry = self._build_base_log_entry(event_type, data)
        logger.info(f"SupervisorFlow: {json.dumps(log_entry)}")
    
    def _build_base_log_entry(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build base log entry structure."""
        return {
            "event_type": event_type, "correlation_id": self.correlation_id,
            "run_id": self.run_id, "flow_state": self.flow_state.value,
            "timestamp": time.time(), "data": data
        }
    
    def _log_flow_event(self, event: str, flow_id: str, correlation_id: str) -> None:
        """Log flow event with state data."""
        data = {
            "event": event, "flow_id": flow_id, "correlation_id": correlation_id,
            "flow_state": self._active_flows.get(flow_id, {}), "timestamp": time.time()
        }
        self._log_json_data("Supervisor flow", data)
    
    def _log_step_event(self, event: str, flow_id: str, step_name: str, step_type: str) -> None:
        """Log step event with context."""
        data = {
            "event": event, "flow_id": flow_id, "step_name": step_name,
            "step_type": step_type, "timestamp": time.time()
        }
        self._log_json_data("Supervisor flow", data)
    
    def _log_todo_state_change(self, todo_id: str, new_state: TodoState) -> None:
        """Log TODO state transition."""
        state_data = {**self.todos[todo_id], "todo_id": todo_id, "new_state": new_state.value}
        self._log_structured_data("supervisor_todo_state_change", state_data)
    
    def _log_json_data(self, log_prefix: str, data: Dict[str, Any]) -> None:
        """Log data as JSON format."""
        if self.log_format == "json":
            logger.info(f"{log_prefix}: {json.dumps(data)}")
    
    # Status and summary methods
    
    def get_flow_summary(self) -> Dict[str, Any]:
        """Get a summary of the current flow state."""
        duration = time.time() - self.start_time
        return {
            "correlation_id": self.correlation_id, "run_id": self.run_id,
            "current_state": self.flow_state.value, "duration_seconds": round(duration, 2),
            "todo_count": len(self.todos), "agent_execution_count": len(self.agent_executions)
        }
    
    def get_active_flows(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active flows."""
        return self._active_flows.copy()
    
    def get_todo_states(self) -> Dict[str, Dict[str, Any]]:
        """Get current TODO task states."""
        return self.todos.copy()


# Global supervisor flow logger instance
_supervisor_flow_logger: Optional[CoreSupervisorFlowLogger] = None


def get_supervisor_flow_logger() -> CoreSupervisorFlowLogger:
    """Get the global supervisor flow logger instance."""
    global _supervisor_flow_logger
    if _supervisor_flow_logger is None:
        _supervisor_flow_logger = CoreSupervisorFlowLogger()
    return _supervisor_flow_logger


def create_supervisor_flow_logger(correlation_id: Optional[str] = None, 
                                 run_id: Optional[str] = None, enabled: bool = True) -> CoreSupervisorFlowLogger:
    """Create a new supervisor flow logger instance."""
    return CoreSupervisorFlowLogger(correlation_id, run_id, enabled)