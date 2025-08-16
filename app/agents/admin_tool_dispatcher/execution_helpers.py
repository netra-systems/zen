"""
Execution Helper Functions

Additional helpers to ensure all admin tool execution functions 
are ≤8 lines including multi-line signatures.
"""
from typing import Optional, Dict, Any
from datetime import datetime, UTC
from app.schemas.admin_tool_types import ToolResponse, ToolSuccessResponse, ToolFailureResponse


def get_current_utc_time() -> datetime:
    """Get current UTC time"""
    return datetime.now(UTC)


def check_validation_result(validation_result: Optional[ToolResponse]) -> bool:
    """Check if validation result exists"""
    return validation_result is not None


def extract_action_from_kwargs(kwargs: Dict[str, Any]) -> str:
    """Extract action from kwargs with default"""
    return kwargs.get('action', 'default')


def build_execute_params(tool_name: str, user, db, action: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Build parameters for tool execution"""
    base_params = _get_base_execute_params(tool_name, user, db, action)
    return {**base_params, **kwargs}


def _get_base_execute_params(tool_name: str, user, db, action: str) -> Dict[str, Any]:
    """Get base execution parameters"""
    return {
        "tool_name": tool_name,
        "user": user,
        "db": db, 
        "action": action
    }


def handle_execution_success(dispatcher, tool_name: str, start_time: datetime, 
                           result: dict, kwargs: Dict[str, Any]) -> ToolSuccessResponse:
    """Handle successful tool execution"""
    from .admin_tool_execution import create_successful_response
    return create_successful_response(dispatcher, tool_name, start_time, result, **kwargs)


def handle_execution_error(dispatcher, tool_name: str, 
                         start_time: datetime, error: Exception) -> ToolFailureResponse:
    """Handle tool execution error"""
    from .admin_tool_execution import create_error_response
    return create_error_response(dispatcher, tool_name, start_time, error)


def build_timing_metadata(start_time: datetime) -> Dict[str, Any]:
    """Build timing metadata for responses"""
    completed_time = datetime.now(UTC)
    execution_time_ms = _calculate_execution_time_ms(start_time, completed_time)
    return _create_timing_dict(start_time, completed_time, execution_time_ms)


def _calculate_execution_time_ms(start_time: datetime, completed_time: datetime) -> float:
    """Calculate execution time in milliseconds"""
    return (completed_time - start_time).total_seconds() * 1000


def _create_timing_dict(start_time: datetime, completed_time: datetime, execution_time_ms: float) -> Dict[str, Any]:
    """Create timing dictionary"""
    return {
        "completed_time": completed_time,
        "execution_time_ms": execution_time_ms,
        "start_time": start_time
    }


def build_success_response_data(dispatcher, tool_name: str, timing: Dict[str, Any],
                               result: dict, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Build success response data"""
    base_data = _build_base_response_data(tool_name, timing, dispatcher.user.id)
    success_data = _build_success_specific_data(result, dispatcher, tool_name, kwargs)
    return {**base_data, **success_data}


def _build_base_response_data(tool_name: str, timing: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Build base response data common to success and error"""
    return {
        "tool_name": tool_name,
        "execution_time_ms": timing["execution_time_ms"],
        "started_at": timing.get("start_time"),
        "completed_at": timing["completed_time"],
        "user_id": user_id
    }


def _build_success_specific_data(result: dict, dispatcher, tool_name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Build success-specific response data"""
    from .admin_tool_execution import create_success_metadata
    return {
        "status": "COMPLETED",
        "result": result,
        "metadata": create_success_metadata(dispatcher, tool_name, kwargs)
    }


def build_error_response_data(dispatcher, tool_name: str, timing: Dict[str, Any],
                             error: Exception, start_time: datetime) -> Dict[str, Any]:
    """Build error response data"""
    from .admin_tool_execution import get_user_id_safe
    base_data = _build_base_response_data(tool_name, timing, get_user_id_safe(dispatcher))
    error_data = _build_error_specific_data(error, start_time, timing)
    return {**base_data, **error_data}


def _build_error_specific_data(error: Exception, start_time: datetime, timing: Dict[str, Any]) -> Dict[str, Any]:
    """Build error-specific response data"""
    return {
        "status": "FAILED",
        "started_at": start_time,
        "error": str(error),
        "is_recoverable": False
    }


def create_metadata_dict(dispatcher, tool_name: str, action: str) -> Dict[str, Any]:
    """Create metadata dictionary"""
    return {
        "admin_action": True,
        "tool": tool_name,
        "user": dispatcher.user.email,
        "action": action
    }


def log_successful_tool_execution(dispatcher, tool_name: str, action: str) -> None:
    """Log successful tool execution"""
    from app.logging_config import central_logger
    central_logger.info(f"Admin tool {tool_name} executed by {dispatcher.user.email}: {action}")


def log_failed_tool_execution(tool_name: str, error: Exception) -> None:
    """Log failed tool execution"""
    from app.logging_config import central_logger
    central_logger.error(f"Admin tool {tool_name} failed: {error}", exc_info=True)


def get_safe_user_id(dispatcher) -> str:
    """Safely get user ID from dispatcher"""
    return dispatcher.user.id if dispatcher.user else "unknown"


def calculate_timing_ms(start_time: datetime) -> float:
    """Calculate execution time in milliseconds"""
    end_time = datetime.now(UTC)
    return (end_time - start_time).total_seconds() * 1000