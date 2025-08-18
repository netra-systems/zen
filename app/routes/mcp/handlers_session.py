"""MCP session handlers."""
from typing import Dict, Any

from app.schemas import UserInDB
from app.services.mcp_service import MCPService
from app.routes.mcp.models import MCPSessionCreateRequest
from app.routes.mcp.utils import (
    build_session_response, handle_session_error, raise_session_not_found
)


async def handle_session_creation(
    request: MCPSessionCreateRequest,
    mcp_service: MCPService,
    current_user: UserInDB
) -> Dict[str, Any]:
    """Create a new MCP session"""
    try:
        return await create_new_session(request, mcp_service)
    except Exception as e:
        return handle_session_error(e, "creating")


async def handle_session_retrieval(
    session_id: str,
    mcp_service: MCPService,
    current_user: UserInDB
) -> Dict[str, Any]:
    """Get session information"""
    try:
        return await get_existing_session(session_id, mcp_service)
    except Exception as e:
        return handle_session_error(e, "getting")


async def handle_session_closure(
    session_id: str,
    mcp_service: MCPService,
    current_user: UserInDB
) -> Dict[str, Any]:
    """Close an MCP session"""
    try:
        return await close_existing_session(session_id, mcp_service)
    except Exception as e:
        return handle_session_error(e, "closing")


async def create_new_session(request: MCPSessionCreateRequest, mcp_service: MCPService) -> Dict[str, Any]:
    """Create new MCP session"""
    session_id = await mcp_service.create_session(
        client_id=request.client_id,
        metadata=request.metadata
    )
    return build_session_response(session_id, "created")


async def get_existing_session(session_id: str, mcp_service: MCPService) -> Dict[str, Any]:
    """Get existing MCP session"""
    session = await mcp_service.get_session(session_id)
    if not session:
        raise_session_not_found()
    return session


async def close_existing_session(session_id: str, mcp_service: MCPService) -> Dict[str, Any]:
    """Close existing MCP session"""
    await mcp_service.close_session(session_id)
    return build_session_response(session_id, "closed")