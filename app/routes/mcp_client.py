"""MCP Client API Routes.

FastAPI routes for MCP client operations including server management,
tool execution, and resource access.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer

from app.services.service_locator import get_service
from app.services.service_interfaces import IMCPClientService
from app.schemas.mcp_client import (
    RegisterServerRequest, RegisterServerResponse,
    ConnectServerRequest, ConnectServerResponse,
    ListServersResponse, DiscoverToolsResponse,
    ExecuteToolRequest, ExecuteToolResponse,
    GetResourcesResponse, FetchResourceRequest, FetchResourceResponse,
    ClearCacheRequest, ClearCacheResponse
)
from app.core.exceptions_service import ServiceError
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/api/mcp-client", tags=["MCP Client"])


def get_mcp_client_service() -> IMCPClientService:
    """Get MCP client service dependency."""
    return get_service(IMCPClientService)


@router.post("/servers", response_model=RegisterServerResponse)
async def register_server(
    request: RegisterServerRequest,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Register a new external MCP server."""
    try:
        success = await mcp_service.register_server(request.config.model_dump())
        
        if success:
            return RegisterServerResponse(
                success=True,
                server_id="generated_id",  # Would be actual server ID
                message=f"Server '{request.name}' registered successfully"
            )
        else:
            raise HTTPException(status_code=400, detail="Server registration failed")
            
    except ServiceError as e:
        logger.error(f"Service error registering server: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error registering server: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/servers", response_model=ListServersResponse)
async def list_servers(
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """List all registered MCP servers."""
    try:
        servers = await mcp_service.list_servers()
        return ListServersResponse(servers=servers)
        
    except ServiceError as e:
        logger.error(f"Service error listing servers: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error listing servers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/servers/{server_name}/connect", response_model=ConnectServerResponse)
async def connect_to_server(
    server_name: str,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Connect to an MCP server."""
    try:
        connection = await mcp_service.connect_to_server(server_name)
        
        return ConnectServerResponse(
            success=True,
            connection=connection,
            message=f"Connected to server '{server_name}'"
        )
        
    except ServiceError as e:
        logger.error(f"Service error connecting to server: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error connecting to server: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/servers/{server_name}/tools", response_model=DiscoverToolsResponse)
async def discover_tools(
    server_name: str,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """List tools from external server."""
    try:
        tools = await mcp_service.discover_tools(server_name)
        return DiscoverToolsResponse(tools=tools)
        
    except ServiceError as e:
        logger.error(f"Service error discovering tools: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error discovering tools: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tools/execute", response_model=ExecuteToolResponse)
async def execute_tool(
    request: ExecuteToolRequest,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Execute tool from external server."""
    try:
        result = await mcp_service.execute_tool(
            request.server_name,
            request.tool_name,
            request.arguments
        )
        
        return ExecuteToolResponse(
            success=True,
            result=result,
            message=f"Tool '{request.tool_name}' executed successfully"
        )
        
    except ServiceError as e:
        logger.error(f"Service error executing tool: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error executing tool: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/servers/{server_name}/resources", response_model=GetResourcesResponse)
async def get_resources(
    server_name: str,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """List resources from external server."""
    try:
        resources = await mcp_service.get_resources(server_name)
        return GetResourcesResponse(resources=resources)
        
    except ServiceError as e:
        logger.error(f"Service error getting resources: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting resources: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/resources/read", response_model=FetchResourceResponse)
async def fetch_resource(
    request: FetchResourceRequest,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Read resource from external server."""
    try:
        resource = await mcp_service.fetch_resource(
            request.server_name,
            request.uri
        )
        
        return FetchResourceResponse(
            success=True,
            resource=resource,
            message=f"Resource '{request.uri}' fetched successfully"
        )
        
    except ServiceError as e:
        logger.error(f"Service error fetching resource: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error fetching resource: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/cache", response_model=ClearCacheResponse)
async def clear_cache(
    server_name: Optional[str] = None,
    cache_type: Optional[str] = None,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Clear MCP client cache."""
    try:
        await mcp_service.clear_cache(server_name)
        
        cache_desc = f"for server '{server_name}'" if server_name else "all"
        return ClearCacheResponse(
            success=True,
            message=f"Cache cleared {cache_desc}",
            cleared_entries=0  # Would track actual count
        )
        
    except ServiceError as e:
        logger.error(f"Service error clearing cache: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")