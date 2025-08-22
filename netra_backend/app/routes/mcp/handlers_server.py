"""MCP server handlers."""
from typing import Any, Dict, Optional

from netra_backend.app.db.models_postgres import User as UserInDB
from netra_backend.app.routes.mcp.utils import handle_server_info_error
from netra_backend.app.services.mcp_service import MCPService


async def handle_server_info(
    mcp_service: MCPService, 
    current_user: Optional[UserInDB]
) -> Dict[str, Any]:
    """Get MCP server information"""
    try:
        return await build_server_info(mcp_service, current_user)
    except Exception as e:
        return handle_server_info_error(e)


async def build_server_info(mcp_service: MCPService, current_user: Optional[UserInDB]) -> Dict[str, Any]:
    """Build server info with authentication status"""
    info = await mcp_service.get_server_info()
    info["authenticated"] = current_user is not None
    return info