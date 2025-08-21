"""
Execution Pattern Helpers for Admin Tool Dispatcher

Modern execution pattern helper functions extracted to maintain 450-line limit.
Provides ExecutionResult and ExecutionContext pattern support.

Business Value: Enables modern agent architecture compliance.
"""
from datetime import UTC, datetime
from typing import Any, Dict

from netra_backend.app.agents.base.interface import ExecutionResult
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import ExecutionStatus

logger = central_logger


def create_execution_result_from_response(response: Dict[str, Any], 
                                         execution_time_ms: float) -> ExecutionResult:
    """Create ExecutionResult from dispatcher response"""
    success = response.get("success", False)
    if success:
        return _create_success_execution_result(response, execution_time_ms)
    return _create_error_execution_result(response, execution_time_ms)


def _create_success_execution_result(response: Dict[str, Any], 
                                   execution_time_ms: float) -> ExecutionResult:
    """Create successful execution result"""
    return ExecutionResult(
        success=True,
        status=ExecutionStatus.COMPLETED,
        result=response,
        execution_time_ms=execution_time_ms
    )


def _create_error_execution_result(response: Dict[str, Any], 
                                 execution_time_ms: float) -> ExecutionResult:
    """Create error execution result"""
    return ExecutionResult(
        success=False,
        status=ExecutionStatus.FAILED,
        error=response.get("error", "Unknown error"),
        execution_time_ms=execution_time_ms
    )


def track_execution_completion(dispatcher: "AdminToolDispatcher", 
                              tool_name: str, start_time: datetime) -> None:
    """Track execution completion metrics"""
    execution_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
    update_execution_metrics(dispatcher, f"{tool_name}_execution_time", execution_time)


def update_execution_metrics(dispatcher: "AdminToolDispatcher", 
                            metric_name: str, value: Any) -> None:
    """Update execution metrics tracking"""
    if hasattr(dispatcher, '_execution_metrics'):
        dispatcher._execution_metrics[metric_name] = value
        dispatcher._execution_metrics['last_updated'] = datetime.now(UTC).isoformat()


def track_audit_success(audit_data: Dict[str, Any]) -> None:
    """Track successful audit logging"""
    logger.debug(f"Audit logged for operation: {audit_data.get('operation')}")


def track_audit_failure(audit_data: Dict[str, Any], error: str) -> None:
    """Track failed audit logging"""
    logger.error(f"Audit logging failed for {audit_data.get('operation')}: {error}")


def log_with_execution_result(audit_logger, audit_data: Dict[str, Any]) -> None:
    """Log with execution result pattern"""
    try:
        audit_logger.log(audit_data)
        track_audit_success(audit_data)
    except Exception as e:
        track_audit_failure(audit_data, str(e))


def execute_with_tracking(dispatcher: "AdminToolDispatcher", 
                         tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute with execution tracking"""
    start_time = datetime.now(UTC)
    result = dispatcher.tool_dispatcher.execute_tool(tool_name, params)
    track_execution_completion(dispatcher, tool_name, start_time)
    return result