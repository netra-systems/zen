"""
Modern Execution Helpers for Admin Tool Dispatcher

Helper functions for the modern execution pattern integration.
Split from dispatcher_core.py to maintain 450-line limit.

Business Value: Enables modern agent architecture compliance.
"""
from typing import Dict, Any
from datetime import datetime, UTC
import uuid

from app.agents.base.interface import ExecutionContext, ExecutionResult
from app.schemas.admin_tool_types import (
    ToolResponse, ToolSuccessResponse, ToolFailureResponse, 
    ToolStatus as AdminToolStatus
)


def create_dispatch_context(dispatcher, tool_name: str, kwargs: Dict[str, Any]) -> ExecutionContext:
    """Create execution context for tool dispatch."""
    run_id = str(uuid.uuid4())
    metadata = {"tool_name": tool_name, "kwargs": kwargs}
    return ExecutionContext(
        run_id=run_id,
        agent_name=dispatcher.agent_name,
        state=None,  # DeepAgentState not needed for tool dispatch
        metadata=metadata,
        user_id=dispatcher.user.id if dispatcher.user else None
    )


def validate_tool_access(dispatcher, tool_name: str) -> bool:
    """Validate user has access to the specified tool."""
    if dispatcher._is_admin_tool(tool_name):
        return dispatcher.has_admin_access()
    return True


def convert_response_to_dict(response: ToolResponse) -> Dict[str, Any]:
    """Convert ToolResponse to dictionary format."""
    return {
        "tool_name": response.tool_name,
        "status": response.status.value if hasattr(response.status, 'value') else str(response.status),
        "result": getattr(response, 'result', None),
        "error": getattr(response, 'error', None),
        "execution_time_ms": response.execution_time_ms,
        "user_id": response.user_id
    }


def convert_result_to_response(dispatcher, result: ExecutionResult, tool_name: str) -> ToolResponse:
    """Convert ExecutionResult back to ToolResponse format."""
    current_time = datetime.now(UTC)
    user_id = dispatcher.user.id if dispatcher.user else "unknown"
    
    if result.success:
        return create_success_response_from_result(result, tool_name, current_time, user_id)
    return create_failure_response_from_result(result, tool_name, current_time, user_id)


def create_success_response_from_result(result: ExecutionResult, tool_name: str,
                                      current_time: datetime, user_id: str) -> ToolSuccessResponse:
    """Create success response from execution result."""
    return ToolSuccessResponse(
        tool_name=tool_name,
        status=AdminToolStatus.COMPLETED,
        result=result.result or {},
        message="Tool executed successfully",
        execution_time_ms=result.execution_time_ms,
        started_at=current_time,
        completed_at=current_time,
        user_id=user_id
    )


def create_failure_response_from_result(result: ExecutionResult, tool_name: str,
                                      current_time: datetime, user_id: str) -> ToolFailureResponse:
    """Create failure response from execution result."""
    return ToolFailureResponse(
        tool_name=tool_name,
        status=AdminToolStatus.FAILED,
        error=result.error or "Unknown error occurred",
        execution_time_ms=result.execution_time_ms,
        started_at=current_time,
        completed_at=current_time,
        user_id=user_id
    )


def get_modern_health_status(dispatcher) -> Dict[str, Any]:
    """Get comprehensive health status including modern components."""
    base_stats = dispatcher.get_dispatcher_stats()
    modern_health = {
        "reliability": dispatcher.reliability_manager.get_health_status(),
        "monitor": dispatcher.monitor.get_health_status(),
        "execution_engine": dispatcher.execution_engine.get_health_status()
    }
    return {**base_stats, "modern_components": modern_health}