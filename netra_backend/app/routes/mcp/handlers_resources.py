"""MCP resources handlers."""
from typing import Any, Dict, Optional

from fastapi import HTTPException

from netra_backend.app.db.models_postgres import User as UserInDB
from netra_backend.app.routes.mcp.helpers import (
    extract_resources_from_app,
    get_resource_function,
)
from netra_backend.app.routes.mcp.models import MCPResourceReadRequest
from netra_backend.app.routes.mcp.utils import (
    build_list_response,
    build_resource_result,
    handle_list_error,
    handle_resource_error,
)
from netra_backend.app.services.mcp_service import MCPService


async def handle_resources_listing(
    mcp_service: MCPService,
    current_user: Optional[UserInDB]
) -> Dict[str, Any]:
    """List available MCP resources"""
    try:
        return build_resources_response(mcp_service)
    except Exception as e:
        return handle_list_error(e, "resources")


async def handle_resource_read(
    request: MCPResourceReadRequest,
    mcp_service: MCPService,
    current_user: UserInDB
) -> Dict[str, Any]:
    """Read an MCP resource"""
    try:
        return await read_mcp_resource(request, mcp_service)
    except HTTPException:
        raise
    except Exception as e:
        return handle_resource_error(e)


def build_resources_response(mcp_service: MCPService) -> Dict[str, Any]:
    """Build resources list response"""
    app = mcp_service.get_fastmcp_app()
    resources = extract_resources_from_app(app)
    return build_list_response(resources, "resources")


async def read_mcp_resource(request: MCPResourceReadRequest, mcp_service: MCPService) -> Dict[str, Any]:
    """Read MCP resource by URI"""
    server = mcp_service.get_mcp_server()
    resource_func = get_resource_function(server, request.uri)
    result = await resource_func()
    return build_resource_result(request.uri, result)