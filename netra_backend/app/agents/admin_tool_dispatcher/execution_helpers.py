"""
Modern Execution Helper Functions

Modernized helpers using ExecutionContext, ExecutionResult patterns.
Integrated with standardized execution patterns for consistent agent execution.

Business Value: Standardizes admin tool execution patterns across all tools.
"""
from datetime import UTC, datetime
from typing import Any, Dict, Optional, Union

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.schemas.admin_tool_types import (
    ToolFailureResponse, ToolResponse, ToolSuccessResponse
)
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.schemas.core_enums import ExecutionStatus


def get_current_utc_time() -> datetime:
    """Get current UTC time"""
    return datetime.now(UTC)


def check_validation_result(validation_result: Optional[ToolResponse]) -> bool:
    """Check if validation result exists"""
    return validation_result is not None


def extract_action_from_kwargs(kwargs: Dict[str, Any]) -> str:
    """Extract action from kwargs with default"""
    return kwargs.get('action', 'default')


def create_execution_context(tool_name: str, user, db, action: str, 
                           run_id: str, kwargs: Dict[str, Any]) -> ExecutionContext:
    """Create modern ExecutionContext for tool execution"""
    user_context = _create_user_execution_context(user, db, action, run_id, kwargs)
    return _build_execution_context(tool_name, user_context)


def _create_user_execution_context(user, db, action: str, run_id: str, kwargs: Dict[str, Any]) -> UserExecutionContext:
    """Create UserExecutionContext from parameters"""
    import uuid
    user_id = getattr(user, 'id', None) if user else f"admin_user_{uuid.uuid4().hex[:8]}"
    thread_id = f"admin_tool_{action}_{user_id}"
    
    metadata = {**kwargs, 'action': action, 'user': user, 'db': db}
    
    return UserExecutionContext.from_request(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        db_session=db,
        metadata=metadata
    )


def _build_execution_context(tool_name: str, user_context: UserExecutionContext) -> ExecutionContext:
    """Build ExecutionContext with modern patterns"""
    return ExecutionContext(
        run_id=user_context.run_id, 
        agent_name=tool_name, 
        state=user_context, 
        user_id=user_context.user_id, 
        metadata=user_context.metadata,
        start_time=get_current_utc_time()
    )


def create_execution_result(success: bool, result_data: Optional[Dict[str, Any]] = None,
                          error: Optional[str] = None, execution_time_ms: float = 0.0) -> ExecutionResult:
    """Create modern ExecutionResult"""
    status = _determine_execution_status(success)
    return _build_execution_result(success, status, result_data, error, execution_time_ms)


def _determine_execution_status(success: bool) -> ExecutionStatus:
    """Determine execution status from success flag"""
    return ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED


def _build_execution_result(success: bool, status: ExecutionStatus, result_data: Optional[Dict[str, Any]],
                          error: Optional[str], execution_time_ms: float) -> ExecutionResult:
    """Build ExecutionResult with all parameters"""
    return ExecutionResult(success=success, status=status, result=result_data,
                         error=error, execution_time_ms=execution_time_ms)


async def handle_execution_error(context: ExecutionContext, error: Exception,
                                error_handler: ExecutionErrorHandler) -> ExecutionResult:
    """Handle execution error using modern error handler"""
    return await error_handler.handle_execution_error(error, context)


def calculate_execution_metrics(context: ExecutionContext) -> Dict[str, float]:
    """Calculate execution timing metrics"""
    current_time = get_current_utc_time()
    execution_time = _calculate_time_delta_ms(context.start_time, current_time)
    return {'execution_time_ms': execution_time, 'start_timestamp': context.start_time.timestamp()}


def _calculate_time_delta_ms(start_time: Optional[datetime], end_time: datetime) -> float:
    """Calculate time delta in milliseconds"""
    if not start_time:
        return 0.0
    return (end_time - start_time).total_seconds() * 1000


def record_execution_metrics(context: ExecutionContext, result: ExecutionResult,
                           monitor: Optional[ExecutionMonitor] = None) -> None:
    """Record execution metrics with monitor"""
    if monitor:
        monitor.complete_execution(context, result)
    _log_execution_completion(context, result)


def convert_execution_result_to_tool_response(result: ExecutionResult, tool_name: str,
                                            user_id: str) -> Union[ToolSuccessResponse, ToolFailureResponse]:
    """Convert ExecutionResult to legacy ToolResponse format"""
    if result.success:
        return _create_legacy_success_response(result, tool_name, user_id)
    return _create_legacy_failure_response(result, tool_name, user_id)


def _create_legacy_success_response(result: ExecutionResult, tool_name: str, 
                                   user_id: str) -> ToolSuccessResponse:
    """Create legacy success response from ExecutionResult"""
    response_data = _build_success_response_data(result, tool_name, user_id)
    return ToolSuccessResponse(**response_data)


def _create_legacy_failure_response(result: ExecutionResult, tool_name: str,
                                   user_id: str) -> ToolFailureResponse:
    """Create legacy failure response from ExecutionResult"""
    response_data = _build_failure_response_data(result, tool_name, user_id)
    return ToolFailureResponse(**response_data)


def _build_success_response_data(result: ExecutionResult, tool_name: str,
                               user_id: str) -> Dict[str, Any]:
    """Build success response data from ExecutionResult"""
    base_data = _get_base_response_data(tool_name, user_id, result.execution_time_ms)
    return {**base_data, "status": "COMPLETED", "result": result.result or {}}


def _build_failure_response_data(result: ExecutionResult, tool_name: str,
                               user_id: str) -> Dict[str, Any]:
    """Build failure response data from ExecutionResult"""
    base_data = _get_base_response_data(tool_name, user_id, result.execution_time_ms)
    return {**base_data, "status": "FAILED", "error": result.error or "Unknown error"}


def _get_base_response_data(tool_name: str, user_id: str, 
                          execution_time_ms: float) -> Dict[str, Any]:
    """Get base response data for both success and failure"""
    current_time = get_current_utc_time()
    return {"tool_name": tool_name, "user_id": user_id, 
           "execution_time_ms": execution_time_ms, "completed_at": current_time}


def create_execution_metadata(context: ExecutionContext, action: str) -> Dict[str, Any]:
    """Create execution metadata from context"""
    return {"admin_action": True, "tool": context.agent_name,
           "user_id": context.user_id, "action": action, "run_id": context.run_id}


def _log_execution_completion(context: ExecutionContext, result: ExecutionResult) -> None:
    """Log execution completion with result details"""
    from netra_backend.app.logging_config import central_logger
    status = "SUCCESS" if result.success else "FAILED"
    central_logger.info(f"Tool {context.agent_name} {status} (run_id: {context.run_id})")


def get_safe_user_id(dispatcher) -> str:
    """Safely get user ID from dispatcher"""
    return dispatcher.user.id if dispatcher.user else "unknown"


def get_database_session_manager(context: ExecutionContext) -> DatabaseSessionManager:
    """Get DatabaseSessionManager from UserExecutionContext"""
    user_context = context.state
    if not isinstance(user_context, UserExecutionContext):
        raise ValueError(f"Expected UserExecutionContext in context.state, got {type(user_context)}")
    
    return DatabaseSessionManager(user_context)


def start_execution_monitoring(context: ExecutionContext, 
                             monitor: Optional[ExecutionMonitor] = None) -> None:
    """Start execution monitoring if monitor provided"""
    if monitor:
        monitor.start_execution(context)
    _log_execution_start(context)


def _log_execution_start(context: ExecutionContext) -> None:
    """Log execution start details"""
    from netra_backend.app.logging_config import central_logger
    central_logger.debug(f"Starting {context.agent_name} execution (run_id: {context.run_id})")