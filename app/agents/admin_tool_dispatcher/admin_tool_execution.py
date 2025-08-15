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
from datetime import datetime

if TYPE_CHECKING:
    from .dispatcher_core import AdminToolDispatcher

logger = central_logger


async def dispatch_admin_tool(dispatcher: "AdminToolDispatcher", 
                             tool_name: str, 
                             tool_input: ToolInput,
                             **kwargs) -> ToolResponse:
    """Main admin tool dispatch function split into smaller functions"""
    start_time = datetime.utcnow()
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
        started_at=start_time, completed_at=datetime.utcnow(), user_id="unknown",
        error="Admin tools not available - insufficient permissions"
    )


def create_access_denied_response(tool_name: str, start_time: datetime) -> ToolFailureResponse:
    """Create response for access denied"""
    execution_time = calculate_execution_time(start_time)
    return ToolFailureResponse(
        tool_name=tool_name, status=ToolStatus.FAILED, execution_time_ms=execution_time,
        started_at=start_time, completed_at=datetime.utcnow(), user_id="unknown",
        error=f"Admin tool {tool_name} not found or not accessible"
    )


async def execute_admin_tool_safely(dispatcher: "AdminToolDispatcher", 
                                   tool_name: str, 
                                   start_time: datetime,
                                   **kwargs) -> ToolResponse:
    """Execute admin tool with error handling"""
    try:
        result = await execute_admin_tool_by_name(dispatcher, tool_name, **kwargs)
        return create_successful_response(dispatcher, tool_name, start_time, result, **kwargs)
    except Exception as e:
        return create_error_response(dispatcher, tool_name, start_time, e)


async def execute_admin_tool_by_name(dispatcher: "AdminToolDispatcher", 
                                    tool_name: str, 
                                    **kwargs) -> dict:
    """Execute admin tool by name"""
    from .tool_handlers import execute_admin_tool
    
    action = kwargs.get('action', 'default')
    return await execute_admin_tool(
        tool_name, dispatcher.user, dispatcher.db, action, **kwargs
    )


def create_successful_response(dispatcher: "AdminToolDispatcher", 
                              tool_name: str, 
                              start_time: datetime,
                              result: dict,
                              **kwargs) -> ToolSuccessResponse:
    """Create successful tool response"""
    timing = calculate_response_timing(start_time)
    log_successful_execution(dispatcher, tool_name, kwargs.get('action', 'default'))
    return build_success_response(dispatcher, tool_name, timing, result, kwargs)


def calculate_response_timing(start_time: datetime) -> dict:
    """Calculate response timing information."""
    completed_time = datetime.utcnow()
    execution_time_ms = (completed_time - start_time).total_seconds() * 1000
    return {"completed_time": completed_time, "execution_time_ms": execution_time_ms}


def build_success_response(dispatcher: "AdminToolDispatcher", tool_name: str,
                          timing: dict, result: dict, kwargs: dict) -> ToolSuccessResponse:
    """Build the actual success response object."""
    return ToolSuccessResponse(
        tool_name=tool_name, status=ToolStatus.COMPLETED,
        execution_time_ms=timing["execution_time_ms"], started_at=timing.get("start_time"),
        completed_at=timing["completed_time"], user_id=dispatcher.user.id,
        result=result, metadata=create_success_metadata(dispatcher, tool_name, kwargs)
    )


def log_successful_execution(dispatcher: "AdminToolDispatcher", 
                            tool_name: str, 
                            action: str) -> None:
    """Log successful admin tool execution"""
    logger.info(f"Admin tool {tool_name} executed by {dispatcher.user.email}: {action}")


def create_success_metadata(dispatcher: "AdminToolDispatcher", 
                           tool_name: str, 
                           kwargs: dict) -> dict:
    """Create metadata for successful response"""
    return {
        "admin_action": True,
        "tool": tool_name,
        "user": dispatcher.user.email,
        "action": kwargs.get('action', 'default')
    }


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
    return ToolFailureResponse(
        tool_name=tool_name, status=ToolStatus.FAILED,
        execution_time_ms=timing["execution_time_ms"], started_at=start_time,
        completed_at=timing["completed_time"], error=str(error),
        user_id=get_user_id_safe(dispatcher), is_recoverable=False
    )


def log_failed_execution(tool_name: str, error: Exception) -> None:
    """Log failed admin tool execution"""
    logger.error(f"Admin tool {tool_name} failed: {error}", exc_info=True)


def calculate_execution_time(start_time: datetime) -> float:
    """Calculate execution time in milliseconds"""
    end_time = datetime.utcnow()
    return (end_time - start_time).total_seconds() * 1000


def get_user_id_safe(dispatcher: "AdminToolDispatcher") -> str:
    """Safely get user ID from dispatcher"""
    return dispatcher.user.id if dispatcher.user else "unknown"


async def validate_tool_input_safely(tool_name: str, **kwargs) -> str | None:
    """Validate tool input parameters and return error if any"""
    from .validation import validate_tool_input
    return validate_tool_input(tool_name, **kwargs)