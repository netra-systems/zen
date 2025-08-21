"""MCP client handlers."""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import User as UserInDB
from netra_backend.app.routes.mcp.helpers import check_admin_access
from netra_backend.app.routes.mcp.models import MCPClientCreateRequest
from netra_backend.app.routes.mcp.utils import handle_client_registration_error
from netra_backend.app.services.mcp_service import MCPService


async def handle_client_registration(
    request: MCPClientCreateRequest,
    db: AsyncSession,
    mcp_service: MCPService,
    current_user: UserInDB
):
    """Register a new MCP client"""
    try:
        check_admin_access(current_user)
        return await create_client(request, db, mcp_service)
    except HTTPException:
        raise
    except Exception as e:
        return handle_client_registration_error(e)


async def create_client(request, db, mcp_service):
    """Create MCP client with provided parameters"""
    client_params = build_client_params(request)
    return await mcp_service.register_client(
        db_session=db, **client_params
    )


def build_client_params(request) -> dict:
    """Build client parameters dictionary"""
    return {
        "name": request.name,
        "client_type": request.client_type,
        **build_client_extra_params(request)
    }


def build_client_extra_params(request) -> dict:
    """Build extra client parameters"""
    return {
        "api_key": request.api_key,
        "permissions": request.permissions,
        "metadata": request.metadata
    }