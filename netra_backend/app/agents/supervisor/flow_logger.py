"""Supervisor flow logger for pipeline observability.

Provides structured logging for supervisor execution flows with correlation tracking.
Each function must be  <= 8 lines as per architecture requirements.
"""
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.supervisor.flow_data_builders import (
    build_base_log_entry,
    build_spec_decision_data,
    build_spec_flow_start_data,
    build_spec_step_completion_data,
    build_spec_step_data,
    build_spec_todo_data,
    build_spec_todo_failure_data,
    build_spec_todo_status_data,
)
from netra_backend.app.core.serialization.unified_json_handler import backend_json_handler
from netra_backend.app.logging_config import central_logger

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


class SupervisorPipelineLogger:
    """Manages structured logging for supervisor execution flows."""
    
    def __init__(self, correlation_id: str, run_id: str):
        self.correlation_id = correlation_id
        self.run_id = run_id
        self.flow_state = FlowState.PENDING
        self.start_time = time.time()
        self.todos: Dict[str, Dict[str, Any]] = {}
        self.agent_executions: List[Dict[str, Any]] = []

    def log_flow_start(self, pipeline_name: str, steps: List[str]) -> None:
        """Log the start of a supervisor flow."""
        self.flow_state = FlowState.STARTED
        flow_data = self._build_flow_start_data(pipeline_name, steps)
        self._log_structured_data("supervisor_flow_start", flow_data)

    def _build_flow_start_data(self, pipeline_name: str, steps: List[str]) -> Dict[str, Any]:
        """Build flow start data structure."""
        return {
            "pipeline_name": pipeline_name,
            "steps": steps,
            "step_count": len(steps),
            "estimated_duration": len(steps) * 30  # 30s per step estimate
        }

    def log_agent_start(self, agent_name: str, step_number: int) -> None:
        """Log the start of an agent execution."""
        self.flow_state = FlowState.AGENT_EXECUTING
        agent_data = self._build_agent_start_data(agent_name, step_number)
        self._log_structured_data("supervisor_agent_start", agent_data)

    def _build_agent_start_data(self, agent_name: str, step_number: int) -> Dict[str, Any]:
        """Build agent start data structure."""
        return {
            "agent_name": agent_name,
            "step_number": step_number,
            "step_started_at": time.time()
        }

    def log_agent_completion(self, agent_name: str, success: bool, duration: float) -> None:
        """Log the completion of an agent execution."""
        self.flow_state = FlowState.AGENT_COMPLETED
        completion_data = self._build_agent_completion_data(agent_name, success, duration)
        self._log_structured_data("supervisor_agent_completion", completion_data)

    def _build_agent_completion_data(self, agent_name: str, success: bool, duration: float) -> Dict[str, Any]:
        """Build agent completion data structure."""
        return {
            "agent_name": agent_name,
            "success": success,
            "duration_seconds": round(duration, 2),
            "status": "success" if success else "failed"
        }

    def log_inter_agent_communication(self, from_agent: str, to_agent: str, message_type: str) -> None:
        """Log communication between agents."""
        comm_data = self._build_communication_data(from_agent, to_agent, message_type)
        self._log_structured_data("supervisor_inter_agent_comm", comm_data)

    def _build_communication_data(self, from_agent: str, to_agent: str, message_type: str) -> Dict[str, Any]:
        """Build inter-agent communication data structure."""
        return {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "comm_timestamp": time.time()
        }

    def create_todo(self, todo_id: str, description: str, agent_name: str) -> None:
        """Create a new TODO item in the flow."""
        todo_data = self._build_todo_data(description, agent_name, TodoState.CREATED)
        self.todos[todo_id] = todo_data
        self._log_structured_data("supervisor_todo_created", {**todo_data, "todo_id": todo_id})

    def _build_todo_data(self, description: str, agent_name: str, state: TodoState) -> Dict[str, Any]:
        """Build TODO data structure."""
        return {
            "description": description,
            "agent_name": agent_name,
            "state": state.value,
            "created_at": time.time()
        }

    def update_todo_state(self, todo_id: str, new_state: TodoState) -> None:
        """Update TODO item state."""
        if todo_id not in self.todos:
            return
        self._update_todo_timestamps(todo_id, new_state)
        self._log_todo_state_change(todo_id, new_state)

    def _update_todo_timestamps(self, todo_id: str, new_state: TodoState) -> None:
        """Update TODO timestamps for state change."""
        self.todos[todo_id]["state"] = new_state.value
        if new_state == TodoState.IN_PROGRESS:
            self.todos[todo_id]["started_at"] = time.time()
        elif new_state in [TodoState.COMPLETED, TodoState.FAILED]:
            self.todos[todo_id]["completed_at"] = time.time()

    def _log_todo_state_change(self, todo_id: str, new_state: TodoState) -> None:
        """Log TODO state transition."""
        state_data = {**self.todos[todo_id], "todo_id": todo_id, "new_state": new_state.value}
        self._log_structured_data("supervisor_todo_state_change", state_data)

    def log_pipeline_execution(self, step_name: str, status: str, metrics: Dict[str, Any]) -> None:
        """Log pipeline step execution with metrics."""
        execution_data = self._build_pipeline_execution_data(step_name, status, metrics)
        self._log_structured_data("supervisor_pipeline_execution", execution_data)

    def _build_pipeline_execution_data(self, step_name: str, status: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Build pipeline execution data structure."""
        return {
            "step_name": step_name,
            "status": status,
            "metrics": metrics,
            "execution_timestamp": time.time()
        }

    def log_flow_completion(self, success: bool, total_steps: int, failed_steps: int) -> None:
        """Log the completion of the entire flow."""
        self.flow_state = FlowState.COMPLETED if success else FlowState.FAILED
        completion_data = self._build_flow_completion_data(success, total_steps, failed_steps)
        self._log_structured_data("supervisor_flow_completion", completion_data)

    def _build_flow_completion_data(self, success: bool, total_steps: int, failed_steps: int) -> Dict[str, Any]:
        """Build flow completion data structure."""
        base_data = self._create_completion_base_data(success, total_steps, failed_steps)
        timing_data = self._create_completion_timing_data()
        return {**base_data, **timing_data}

    def _create_completion_base_data(self, success: bool, total_steps: int, failed_steps: int) -> Dict[str, Any]:
        """Create completion base data fields."""
        return {
            "success": success,
            "total_steps": total_steps,
            "failed_steps": failed_steps
        }

    def _create_completion_timing_data(self) -> Dict[str, Any]:
        """Create completion timing data fields."""
        duration = time.time() - self.start_time
        return {
            "total_duration_seconds": round(duration, 2),
            "final_state": self.flow_state.value
        }

    def get_flow_summary(self) -> Dict[str, Any]:
        """Get a summary of the current flow state."""
        return self._build_flow_summary()

    def _build_flow_summary(self) -> Dict[str, Any]:
        """Build comprehensive flow summary."""
        base_data = self._create_summary_base_data()
        timing_data = self._create_summary_timing_data()
        count_data = self._create_summary_count_data()
        return {**base_data, **timing_data, **count_data}

    def _create_summary_base_data(self) -> Dict[str, Any]:
        """Create summary base identification data."""
        return {
            "correlation_id": self.correlation_id,
            "run_id": self.run_id,
            "current_state": self.flow_state.value
        }

    def _create_summary_timing_data(self) -> Dict[str, Any]:
        """Create summary timing data."""
        duration = time.time() - self.start_time
        return {"duration_seconds": round(duration, 2)}

    def _create_summary_count_data(self) -> Dict[str, Any]:
        """Create summary count data."""
        return {
            "todo_count": len(self.todos),
            "agent_execution_count": len(self.agent_executions)
        }

    def _log_structured_data(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log structured data with consistent format."""
        log_entry = self._build_base_log_entry(event_type, data)
        logger.info(f"SupervisorFlow: {backend_json_handler.dumps(log_entry)}")

    def _build_base_log_entry(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build base log entry structure."""
        return build_base_log_entry(event_type, self.correlation_id, self.run_id, 
                                   self.flow_state.value, data)

    # Enhanced TODO tracking methods with spec compliance
    def log_todo_added(self, task_id: str, description: str, 
                      priority: str = "medium", dependencies: Optional[List[str]] = None) -> None:
        """Log task addition to TODO list with priority and dependencies."""
        todo_data = build_spec_todo_data("task_added", task_id, description, priority, dependencies)
        self._log_structured_data("supervisor_todo", todo_data)

    def log_todo_started(self, task_id: str) -> None:
        """Log task started from TODO list."""
        todo_data = build_spec_todo_status_data("task_started", task_id, "in_progress")
        self._log_structured_data("supervisor_todo", todo_data)

    def log_todo_completed(self, task_id: str) -> None:
        """Log task completion from TODO list."""
        todo_data = build_spec_todo_status_data("task_completed", task_id, "completed")
        self._log_structured_data("supervisor_todo", todo_data)

    def log_todo_failed(self, task_id: str, error: str) -> None:
        """Log task failure from TODO list with error details."""
        todo_data = build_spec_todo_failure_data("task_failed", task_id, error)
        self._log_structured_data("supervisor_todo", todo_data)

    def log_flow_started(self, flow_id: str, total_steps: int) -> None:
        """Log supervisor flow initiation with step count."""
        flow_data = build_spec_flow_start_data(flow_id, total_steps)
        self._log_structured_data("supervisor_flow", flow_data)

    def log_step_started(self, flow_id: str, step_name: str, step_type: str) -> None:
        """Log flow step initiation with type classification."""
        step_data = build_spec_step_data("step_started", flow_id, step_name, step_type)
        self._log_structured_data("supervisor_flow", step_data)

    def log_step_completed(self, flow_id: str, step_name: str, duration: float) -> None:
        """Log flow step completion with timing metrics."""
        step_data = build_spec_step_completion_data(flow_id, step_name, duration)
        self._log_structured_data("supervisor_flow", step_data)

    def log_decision_made(self, flow_id: str, decision: str, reason: str) -> None:
        """Log supervisor decision point with reasoning."""
        decision_data = build_spec_decision_data(flow_id, decision, reason)
        self._log_structured_data("supervisor_flow", decision_data)


