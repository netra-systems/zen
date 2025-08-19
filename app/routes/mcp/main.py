"""
MCP Main Router

Main FastAPI router for MCP endpoints with delegated handlers.
Maintains clean API structure under 300-line limit.
"""

from typing import Optional
from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbDep
from app.auth_integration.auth import get_current_user, get_current_user_optional
from app.schemas import UserInDB
from app.services.mcp_models import MCPClient

from .models import (
    MCPClientCreateRequest,
    MCPSessionCreateRequest,
    MCPToolCallRequest,
    MCPResourceReadRequest,
    MCPPromptGetRequest
)
from .service_factory import get_mcp_service
from .handlers import MCPHandlers
from .websocket_handler import MCPWebSocketHandler

router = APIRouter(tags=["MCP"])


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
    api_key: Optional[str] = None,
    mcp_service = Depends(get_mcp_service)
):
    """WebSocket endpoint for MCP"""
    handler = MCPWebSocketHandler(mcp_service)
    await handler.handle_websocket(websocket, api_key)

@router.post("/")
async def handle_mcp_message(
    request: dict,
    mcp_service = Depends(get_mcp_service)
):
    """Handle MCP JSON-RPC message"""
    from app.services.mcp_request_handler import handle_request
    from fastapi import HTTPException
    
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

