"""
Tool Execution Logic for Unified Tools API
"""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models_postgres import User
from app.services.unified_tool_registry import ToolExecutionResult
from app.logging_config import central_logger
from netra_backend.app.schemas import ToolExecutionRequest

logger = central_logger


def build_tool_execution_params(
    request: ToolExecutionRequest, current_user: User
) -> Dict[str, Any]:
    """Build tool execution parameters."""
    return {
        "tool_name": request.tool_name, "arguments": request.arguments,
        "user": current_user
    }


async def execute_tool_through_registry(
    tool_registry, request: ToolExecutionRequest, current_user: User
) -> ToolExecutionResult:
    """Execute tool through registry."""
    params = build_tool_execution_params(request, current_user)
    return await tool_registry.execute_tool(**params)


def build_base_tool_response(result: ToolExecutionResult) -> Dict[str, Any]:
    """Build base tool execution response."""
    return {
        "tool_name": result.tool_name,
        "status": result.status,
        "execution_time_ms": result.execution_time_ms,
        "timestamp": result.created_at.isoformat()
    }


def add_result_or_error(response: Dict[str, Any], result: ToolExecutionResult) -> None:
    """Add result or error to response based on status."""
    if result.status == "success":
        response["result"] = result.result
    else:
        response["error"] = result.error_message


def create_permission_info(permission_check) -> Dict[str, Any]:
    """Create permission info dictionary."""
    return {
        "required_permissions": permission_check.required_permissions,
        "missing_permissions": permission_check.missing_permissions,
        "upgrade_path": permission_check.upgrade_path,
        "rate_limit_status": permission_check.rate_limit_status
    }


def add_permission_info_if_denied(
    response: Dict[str, Any], result: ToolExecutionResult
) -> None:
    """Add permission info if access was denied."""
    if result.status == "permission_denied" and result.permission_check:
        response["permission_info"] = create_permission_info(result.permission_check)


def format_tool_execution_response(result: ToolExecutionResult) -> Dict[str, Any]:
    """Format complete tool execution response."""
    response = build_base_tool_response(result)
    add_result_or_error(response, result)
    add_permission_info_if_denied(response, result)
    return response


async def process_tool_execution(
    tool_registry, request: ToolExecutionRequest, current_user: User, db: AsyncSession
) -> Dict[str, Any]:
    """Process tool execution and logging."""
    result = await execute_tool_through_registry(tool_registry, request, current_user)
    await log_tool_execution_to_db(tool_registry, result, db)
    return format_tool_execution_response(result)


# Import needed to avoid circular dependency
from netra_backend.app.database_utils import log_tool_execution_to_db