"""MCP tools handlers."""
import time
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.schemas import UserInDB
from netra_backend.app.services.mcp_service import MCPService
from netra_backend.app.routes.mcp.models import MCPToolCallRequest
from netra_backend.app.routes.mcp.helpers import (
    extract_tools_from_app, get_tool_function,
    record_successful_execution, record_failed_execution
)
from netra_backend.app.routes.mcp.utils import (
    filter_by_category, build_list_response, handle_list_error,
    calculate_execution_time, build_tool_result
)
from netra_backend.app.logging_config import CentralLogger

logger = CentralLogger()


async def handle_tools_listing(
    category: Optional[str],
    mcp_service: MCPService,
    current_user: Optional[UserInDB]
) -> Dict[str, Any]:
    """List available MCP tools"""
    try:
        return build_tools_response(mcp_service, category)
    except Exception as e:
        return handle_list_error(e, "tools")


async def handle_tool_call(
    request: MCPToolCallRequest,
    db: AsyncSession,
    mcp_service: MCPService,
    current_user: UserInDB
) -> Dict[str, Any]:
    """Execute an MCP tool"""
    start_time = time.time()
    try:
        return await process_tool_execution(request, db, mcp_service, current_user, start_time)
    except HTTPException:
        raise
    except Exception as e:
        await handle_tool_execution_error(request, db, mcp_service, current_user, e, start_time)


def build_tools_response(mcp_service: MCPService, category: Optional[str]) -> Dict[str, Any]:
    """Build tools list response"""
    app = mcp_service.get_fastmcp_app()
    tools = extract_tools_from_app(app)
    if category:
        tools = filter_by_category(tools, category)
    return build_list_response(tools, "tools")


async def execute_tool(request, mcp_service):
    """Execute MCP tool with provided arguments"""
    server = mcp_service.get_mcp_server()
    tool_func = get_tool_function(server, request.tool_name)
    return await tool_func(**request.arguments)


async def process_tool_execution(request, db, mcp_service, current_user, start_time) -> Dict[str, Any]:
    """Process successful tool execution"""
    result = await execute_tool(request, mcp_service)
    execution_time_ms = calculate_execution_time(start_time)
    await record_successful_execution(
        request, db, mcp_service, current_user, result, execution_time_ms
    )
    return build_tool_result(request.tool_name, result)


async def handle_tool_execution_error(
    request, db, mcp_service, current_user, error, start_time
) -> None:
    """Handle tool execution error"""
    logger.error(f"Error calling tool: {error}", exc_info=True)
    await record_failed_execution(
        request, db, mcp_service, current_user, error, start_time
    )
    raise_tool_execution_error(error)


def raise_tool_execution_error(error) -> None:
    """Raise tool execution HTTP exception"""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(error)
    )