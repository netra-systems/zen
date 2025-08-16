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
    return {
        "tool_name": tool_name,
        "user": user,
        "db": db, 
        "action": action,
        **kwargs
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
    execution_time_ms = (completed_time - start_time).total_seconds() * 1000
    return {
        "completed_time": completed_time,
        "execution_time_ms": execution_time_ms,
        "start_time": start_time
    }


def build_success_response_data(dispatcher, tool_name: str, timing: Dict[str, Any],
                               result: dict, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Build success response data"""
    from .admin_tool_execution import create_success_metadata
    return {
        "tool_name": tool_name,
        "status": "COMPLETED",
        "execution_time_ms": timing["execution_time_ms"],
        "started_at": timing.get("start_time"),
        "completed_at": timing["completed_time"],
        "user_id": dispatcher.user.id,
        "result": result,
        "metadata": create_success_metadata(dispatcher, tool_name, kwargs)
    }


def build_error_response_data(dispatcher, tool_name: str, timing: Dict[str, Any],
                             error: Exception, start_time: datetime) -> Dict[str, Any]:
    """Build error response data"""
    from .admin_tool_execution import get_user_id_safe
    return {
        "tool_name": tool_name,
        "status": "FAILED", 
        "execution_time_ms": timing["execution_time_ms"],
        "started_at": start_time,
        "completed_at": timing["completed_time"],
        "error": str(error),
        "user_id": get_user_id_safe(dispatcher),
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