"""Agent Observability Module

Handles agent logging, metrics, and observability functionality.
"""

import time
from typing import Any

from netra_backend.app.llm.observability import (
    log_agent_communication,
    log_agent_input,
    log_agent_output,
)
from netra_backend.app.schemas.agent_models import AgentExecutionMetrics
from netra_backend.app.schemas.agent_result_types import TypedAgentResult


class AgentObservabilityMixin:
    """Mixin providing agent observability functionality"""
    
    def get_execution_metrics(self) -> AgentExecutionMetrics:
        """Get execution metrics for the agent."""
        return getattr(self, '_execution_metrics', AgentExecutionMetrics(execution_time_ms=0.0))
    
    def _create_failure_result(self, error_message: str, start_time: float) -> TypedAgentResult:
        """Create a failure result with metrics."""
        execution_time = (time.time() - start_time) * 1000
        return TypedAgentResult(
            success=False,
            agent_name=self.name,
            execution_time_ms=execution_time,
            error_message=error_message,
            metrics=self.get_execution_metrics()
        )
    
    def _create_success_result(self, start_time: float, result_data=None) -> TypedAgentResult:
        """Create a success result with metrics."""
        execution_time = (time.time() - start_time) * 1000
        return TypedAgentResult(
            success=True,
            agent_name=self.name,
            execution_time_ms=execution_time,
            result_data=result_data,
            metrics=self.get_execution_metrics()
        )
    
    def _log_agent_start(self, run_id: str) -> None:
        """Log agent starting communication."""
        if not self._subagent_logging_enabled:
            return
        log_agent_communication("system", self.name, self.correlation_id, "agent_start")
    
    def _log_agent_completion(self, run_id: str, status: str) -> None:
        """Log agent completion communication."""
        if not self._subagent_logging_enabled:
            return
        log_agent_communication(self.name, "system", self.correlation_id, f"agent_{status}")
    
    def log_input_from_agent(self, from_agent: str, data: Any) -> None:
        """Log input data received from another agent."""
        if not self._subagent_logging_enabled:
            return
        data_size = self._calculate_data_size(data)
        log_agent_input(from_agent, self.name, data_size, self.correlation_id)
    
    def log_output_to_agent(self, to_agent: str, data: Any, status: str = "success") -> None:
        """Log output data sent to another agent."""
        if not self._subagent_logging_enabled:
            return
        data_size = self._calculate_data_size(data)
        log_agent_output(to_agent, self.name, data_size, status, self.correlation_id)
    
    def _calculate_data_size(self, data: Any) -> int:
        """Calculate size of data for logging."""
        try:
            if isinstance(data, str):
                return len(data)
            if isinstance(data, (list, dict)):
                import json
                return len(json.dumps(data))
            return len(str(data))
        except Exception:
            return 0