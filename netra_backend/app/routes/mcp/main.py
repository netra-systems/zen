"""
MCP Main Router

Main FastAPI router for MCP endpoints with delegated handlers.
Maintains clean API structure under 450-line limit.
"""

from typing import Optional

from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.auth_integration.auth import (
    get_current_user,
    get_current_user_optional,
)
from netra_backend.app.db.models_postgres import User as UserInDB
from netra_backend.app.dependencies import DbDep
from netra_backend.app.routes.mcp.handlers import MCPHandlers
from netra_backend.app.routes.mcp.models import (
    MCPClientCreateRequest,
    MCPPromptGetRequest,
    MCPResourceReadRequest,
    MCPSessionCreateRequest,
    MCPToolCallRequest,
)
from netra_backend.app.routes.mcp.websocket_handler import MCPWebSocketHandler
from netra_backend.app.services.mcp_models import MCPClient
from netra_backend.app.services.service_factory import get_mcp_service

router = APIRouter(
    tags=["MCP"],
    redirect_slashes=False  # Disable automatic trailing slash redirects
)


@router.get("/info")
async def get_server_info(
    mcp_service = Depends(get_mcp_service),
    current_user: Optional[UserInDB] = Depends(get_current_user_optional)
):
    """Get MCP server information"""
    return await MCPHandlers.get_server_info(mcp_service, current_user)


@router.get("/status")
async def get_mcp_status(
    mcp_service = Depends(get_mcp_service),
    user: Optional[UserInDB] = Depends(get_current_user_optional)
):
    """Get MCP server status"""
    return await MCPHandlers.get_server_info(mcp_service, user)


@router.get("/servers")
async def list_servers(
    mcp_service = Depends(get_mcp_service),
    user: Optional[UserInDB] = Depends(get_current_user_optional)
):
    """
    List available MCP servers - Bridge endpoint for frontend compatibility.
    
    The frontend expects to manage external MCP servers, but backend
    provides MCP capabilities directly. This endpoint translates between
    the two architectural models.
    """
    # Return a virtual "server" representing the backend's MCP capabilities
    return {
        "data": [
            {
                "name": "netra-mcp",
                "status": "connected",
                "version": "1.0.0",
                "capabilities": {
                    "tools": True,
                    "resources": True,
                    "prompts": True
                },
                "description": "Netra internal MCP service"
            }
        ],
        "status": "success"
    }


@router.get("/servers/{server_name}/status")
async def get_server_status(
    server_name: str,
    mcp_service = Depends(get_mcp_service),
    user: Optional[UserInDB] = Depends(get_current_user_optional)
):
    """
    Get specific MCP server status - Bridge endpoint for frontend compatibility.
    """
    # Since we only have one virtual "server", always return its status
    if server_name == "netra-mcp":
        info = await MCPHandlers.get_server_info(mcp_service, user)
        return {
            "data": {
                "name": "netra-mcp",
                "status": "connected",
                "version": info.get("version", "1.0.0"),
                "capabilities": info.get("capabilities", {}),
                "description": "Netra internal MCP service",
                "info": info
            },
            "status": "success"
        }
    else:
        # Frontend might request other servers that don't exist
        return {
            "data": None,
            "status": "not_found",
            "message": f"Server '{server_name}' not found"
        }


@router.post("/clients")
async def register_client(
    request: MCPClientCreateRequest,
    db: DbDep,
    mcp_service = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
) -> MCPClient:
    """Register a new MCP client"""
    return await MCPHandlers.register_client(request, db, mcp_service, current_user)


@router.post("/sessions")
async def create_session(
    request: MCPSessionCreateRequest,
    mcp_service = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
):
    """Create a new MCP session"""
    return await MCPHandlers.create_session(request, mcp_service, current_user)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    mcp_service = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
):
    """Get session information"""
    return await MCPHandlers.get_session(session_id, mcp_service, current_user)


@router.delete("/sessions/{session_id}")
async def close_session(
    session_id: str,
    mcp_service = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
):
    """Close an MCP session"""
    return await MCPHandlers.close_session(session_id, mcp_service, current_user)


@router.get("/tools")
async def list_tools(
    category: Optional[str] = None,
    mcp_service = Depends(get_mcp_service),
    current_user: Optional[UserInDB] = Depends(get_current_user_optional)
):
    """List available MCP tools"""
    return await MCPHandlers.list_tools(category, mcp_service, current_user)


@router.get("/tools/discover")
async def discover_tools(
    category: Optional[str] = None,
    mcp_service = Depends(get_mcp_service),
    current_user: Optional[UserInDB] = Depends(get_current_user_optional)
):
    """Discover available MCP tools - alias for list_tools for frontend compatibility"""
    # Frontend expects /tools/discover, backend implements as /tools
    # This endpoint bridges the API contract mismatch
    result = await MCPHandlers.list_tools(category, mcp_service, current_user)
    # Wrap in expected format if needed
    if isinstance(result, list):
        return {"data": result, "status": "success"}
    return result


@router.post("/tools/call")
async def call_tool(
    request: MCPToolCallRequest,
    db: DbDep,
    mcp_service = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
):
    """Execute an MCP tool"""
    return await MCPHandlers.call_tool(request, db, mcp_service, current_user)


@router.get("/resources")
async def list_resources(
    mcp_service = Depends(get_mcp_service),
    current_user: Optional[UserInDB] = Depends(get_current_user_optional)
):
    """List available MCP resources"""
    return await MCPHandlers.list_resources(mcp_service, current_user)


@router.post("/resources/read")
async def read_resource(
    request: MCPResourceReadRequest,
    mcp_service = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
):
    """Read an MCP resource"""
    return await MCPHandlers.read_resource(request, mcp_service, current_user)


@router.get("/prompts")
async def list_prompts(
    category: Optional[str] = None,
    mcp_service = Depends(get_mcp_service),
    current_user: Optional[UserInDB] = Depends(get_current_user_optional)
):
    """List available MCP prompts"""
    return await MCPHandlers.list_prompts(category, mcp_service, current_user)


@router.post("/prompts/get")
async def get_prompt(
    request: MCPPromptGetRequest,
    mcp_service = Depends(get_mcp_service),
    current_user: UserInDB = Depends(get_current_user)
):
    """Get an MCP prompt"""
    return await MCPHandlers.get_prompt(request, mcp_service, current_user)


@router.get("/config")
async def get_mcp_config(
    user: Optional[UserInDB] = Depends(get_current_user_optional)
):
    """Get MCP configuration for clients"""
    return MCPHandlers.get_mcp_config(user)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    api_key: Optional[str] = None
):
    """WebSocket endpoint for MCP"""
    # Manually create MCP service for WebSocket endpoint
    # FastAPI Depends() doesn't work properly with WebSocket endpoints
    from netra_backend.app.routes.mcp.service_factory import create_mcp_service_for_websocket
    mcp_service = await create_mcp_service_for_websocket(websocket)
    handler = MCPWebSocketHandler(mcp_service)
    await handler.handle_websocket(websocket, api_key)

@router.post("")
@router.post("/", include_in_schema=False)
async def handle_mcp_message(
    request: dict,
    mcp_service = Depends(get_mcp_service)
):
    """Handle MCP JSON-RPC message"""
    from fastapi import HTTPException

    from netra_backend.app.services.mcp_request_handler import handle_request
    
    result = await handle_request(request)
    
    # If response contains error, return appropriate HTTP status
    if "error" in result:
        error_code = result["error"].get("code", -32603)
        if error_code == -32600:  # Invalid Request
            raise HTTPException(status_code=400, detail=result["error"]["message"])
        elif error_code == -32601:  # Method not found
            raise HTTPException(status_code=404, detail=result["error"]["message"])
        else:
            raise HTTPException(status_code=422, detail=result["error"]["message"])
    
    return result

