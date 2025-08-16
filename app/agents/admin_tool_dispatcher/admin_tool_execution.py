# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Refactor admin_tool_dispatcher.py - Split massive _dispatch_admin_tool function
# Git: anthony-aug-13-2 | Refactoring for modularity
# Change: Create | Scope: Module | Risk: Low
# Session: admin-tool-refactor | Seq: 4
# Review: Pending | Score: 95
# ================================
"""
Admin Tool Execution Module

This module handles the admin tool execution logic split from the massive
_dispatch_admin_tool function to comply with 8-line function limits.
"""
from typing import TYPE_CHECKING, Optional
from app.schemas import ToolInput
from app.schemas.admin_tool_types import (
    ToolResponse, ToolSuccessResponse, ToolFailureResponse,
    ToolStatus
)
from app.logging_config import central_logger
from datetime import datetime, UTC

if TYPE_CHECKING:
    from .dispatcher_core import AdminToolDispatcher

logger = central_logger


async def dispatch_admin_tool(dispatcher, tool_name: str, tool_input, **kwargs):
    """Main admin tool dispatch function split into smaller functions"""
    from .execution_helpers import get_current_utc_time
    start_time = get_current_utc_time()
    validation_result = await validate_tool_permissions(dispatcher, tool_name, start_time)
    if validation_result:
        return validation_result
    return await execute_admin_tool_safely(dispatcher, tool_name, start_time, **kwargs)


async def validate_tool_permissions(dispatcher: "AdminToolDispatcher", 
                                   tool_name: str, start_time: datetime) -> Optional[ToolResponse]:
    """Validate tool permissions and access."""
    if not check_admin_tools_enabled(dispatcher):
        return create_permission_denied_response(tool_name, start_time)
    if not validate_tool_access(dispatcher, tool_name):
        return create_access_denied_response(tool_name, start_time)
    return None


def check_admin_tools_enabled(dispatcher: "AdminToolDispatcher") -> bool:
    """Check if admin tools are enabled for this dispatcher"""
    return dispatcher.admin_tools_enabled


def validate_tool_access(dispatcher: "AdminToolDispatcher", tool_name: str) -> bool:
    """Validate tool access permissions"""
    from .validation import validate_admin_tool_access
    return validate_admin_tool_access(dispatcher.user, tool_name)


def create_permission_denied_response(tool_name: str, start_time: datetime) -> ToolFailureResponse:
    """Create response for permission denied"""
    return ToolFailureResponse(
        tool_name=tool_name, status=ToolStatus.FAILED, execution_time_ms=0.0,
        started_at=start_time, completed_at=datetime.now(UTC), user_id="unknown",
        error="Admin tools not available - insufficient permissions"
    )


def create_access_denied_response(tool_name: str, start_time: datetime) -> ToolFailureResponse:
    """Create response for access denied"""
    execution_time = calculate_execution_time(start_time)
    return ToolFailureResponse(
        tool_name=tool_name, status=ToolStatus.FAILED, execution_time_ms=execution_time,
        started_at=start_time, completed_at=datetime.now(UTC), user_id="unknown",
        error=f"Admin tool {tool_name} not found or not accessible"
    )


async def execute_admin_tool_safely(dispatcher, tool_name: str, start_time, **kwargs):
    """Execute admin tool with error handling"""
    from .execution_helpers import handle_execution_success, handle_execution_error
    try:
        result = await execute_admin_tool_by_name(dispatcher, tool_name, **kwargs)
        return handle_execution_success(dispatcher, tool_name, start_time, result, kwargs)
    except Exception as e:
        return handle_execution_error(dispatcher, tool_name, start_time, e)


async def execute_admin_tool_by_name(dispatcher, tool_name: str, **kwargs):
    """Execute admin tool by name"""
    from .tool_handlers import execute_admin_tool
    from .execution_helpers import extract_action_from_kwargs
    action = extract_action_from_kwargs(kwargs)
    return await execute_admin_tool(tool_name, dispatcher.user, dispatcher.db, action, **kwargs)


def create_successful_response(dispatcher, tool_name: str, start_time, result: dict, **kwargs):
    """Create successful tool response"""
    from .execution_helpers import build_timing_metadata, log_successful_tool_execution
    timing = build_timing_metadata(start_time)
    log_successful_tool_execution(dispatcher, tool_name, kwargs.get('action', 'default'))
    return build_success_response(dispatcher, tool_name, timing, result, kwargs)


def calculate_response_timing(start_time: datetime) -> dict:
    """Calculate response timing information."""
    completed_time = datetime.now(UTC)
    execution_time_ms = (completed_time - start_time).total_seconds() * 1000
    return {"completed_time": completed_time, "execution_time_ms": execution_time_ms}


def build_success_response(dispatcher: "AdminToolDispatcher", tool_name: str,
                          timing: dict, result: dict, kwargs: dict) -> ToolSuccessResponse:
    """Build the actual success response object."""
    from .execution_helpers import build_success_response_data
    response_data = build_success_response_data(dispatcher, tool_name, timing, result, kwargs)
    return ToolSuccessResponse(**response_data)


def log_successful_execution(dispatcher: "AdminToolDispatcher", 
                            tool_name: str, 
                            action: str) -> None:
    """Log successful admin tool execution"""
    from .execution_helpers import log_successful_tool_execution
    log_successful_tool_execution(dispatcher, tool_name, action)


def create_success_metadata(dispatcher: "AdminToolDispatcher", 
                           tool_name: str, 
                           kwargs: dict) -> dict:
    """Create metadata for successful response"""
    from .execution_helpers import create_metadata_dict
    action = kwargs.get('action', 'default')
    return create_metadata_dict(dispatcher, tool_name, action)


def create_error_response(dispatcher: "AdminToolDispatcher", 
                         tool_name: str, 
                         start_time: datetime,
                         error: Exception) -> ToolFailureResponse:
    """Create error response for failed execution"""
    timing = calculate_response_timing(start_time)
    log_failed_execution(tool_name, error)
    return build_error_response(dispatcher, tool_name, timing, error, start_time)


def build_error_response(dispatcher: "AdminToolDispatcher", tool_name: str,
                        timing: dict, error: Exception, start_time: datetime) -> ToolFailureResponse:
    """Build the actual error response object."""
    from .execution_helpers import build_error_response_data
    response_data = build_error_response_data(dispatcher, tool_name, timing, error, start_time)
    return ToolFailureResponse(**response_data)


def log_failed_execution(tool_name: str, error: Exception) -> None:
    """Log failed admin tool execution"""
    from .execution_helpers import log_failed_tool_execution
    log_failed_tool_execution(tool_name, error)


def calculate_execution_time(start_time: datetime) -> float:
    """Calculate execution time in milliseconds"""
    from .execution_helpers import calculate_timing_ms
    return calculate_timing_ms(start_time)


def get_user_id_safe(dispatcher: "AdminToolDispatcher") -> str:
    """Safely get user ID from dispatcher"""
    from .execution_helpers import get_safe_user_id
    return get_safe_user_id(dispatcher)


async def validate_tool_input_safely(tool_name: str, **kwargs) -> str | None:
    """Validate tool input parameters and return error if any"""
    from .validation import validate_tool_input
    return validate_tool_input(tool_name, **kwargs)