"""MCP Client API Routes.

FastAPI routes for MCP client operations including server management,
tool execution, and resource access.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer

from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.mcp_client import (
    ClearCacheRequest,
    ClearCacheResponse,
    ConnectServerRequest,
    ConnectServerResponse,
    DiscoverToolsResponse,
    ExecuteToolRequest,
    ExecuteToolResponse,
    FetchResourceRequest,
    FetchResourceResponse,
    GetResourcesResponse,
    ListServersResponse,
    RegisterServerRequest,
    RegisterServerResponse,
)
from netra_backend.app.services.service_interfaces import IMCPClientService
from netra_backend.app.services.service_locator import get_service

logger = central_logger.get_logger(__name__)
security = HTTPBearer()

# IMPORTANT: Do NOT add prefix here - managed centrally in app_factory_route_configs.py
# See SPEC/learnings/router_double_prefix_pattern.xml
router = APIRouter(tags=["MCP Client"])


def get_mcp_client_service() -> IMCPClientService:
    """Get MCP client service dependency."""
    return get_service(IMCPClientService)


def _build_register_success_response(request: RegisterServerRequest) -> RegisterServerResponse:
    """Build successful registration response."""
    return RegisterServerResponse(
        success=True, server_id="generated_id",
        message=f"Server '{request.name}' registered successfully"
    )

def _handle_register_failure() -> None:
    """Handle registration failure."""
    raise HTTPException(status_code=400, detail="Server registration failed")

def _handle_register_service_error(e: ServiceError) -> None:
    """Handle service error during registration."""
    logger.error(f"Service error registering server: {e}")
    raise HTTPException(status_code=400, detail=str(e))

def _handle_register_unexpected_error(e: Exception) -> None:
    """Handle unexpected error during registration."""
    logger.error(f"Unexpected error registering server: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/servers", response_model=RegisterServerResponse)
async def register_server(
    request: RegisterServerRequest, mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Register a new external MCP server."""
    return await _process_server_registration(request, mcp_service)


def _handle_register_success(request: RegisterServerRequest, success: bool) -> RegisterServerResponse:
    """Handle successful registration result"""
    if success:
        return _build_register_success_response(request)
    _handle_register_failure()


def _handle_list_service_error(e: ServiceError) -> None:
    """Handle service error during server listing."""
    logger.error(f"Service error listing servers: {e}")
    raise HTTPException(status_code=400, detail=str(e))

def _handle_list_unexpected_error(e: Exception) -> None:
    """Handle unexpected error during server listing."""
    logger.error(f"Unexpected error listing servers: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/servers", response_model=ListServersResponse)
async def list_servers(
    mcp_service: IMCPClientService = Depends(get_mcp_client_service), token: str = Depends(security)
):
    """List all registered MCP servers."""
    return await _process_server_listing(mcp_service)


def _build_connect_response(server_name: str, connection) -> ConnectServerResponse:
    """Build connection response."""
    return ConnectServerResponse(
        success=True, connection=connection, message=f"Connected to server '{server_name}'"
    )

def _handle_connect_service_error(e: ServiceError) -> None:
    """Handle service error during connection."""
    logger.error(f"Service error connecting to server: {e}")
    raise HTTPException(status_code=400, detail=str(e))

def _handle_connect_unexpected_error(e: Exception) -> None:
    """Handle unexpected error during connection."""
    logger.error(f"Unexpected error connecting to server: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/servers/{server_name}/connect", response_model=ConnectServerResponse)
async def connect_to_server(
    server_name: str, mcp_service: IMCPClientService = Depends(get_mcp_client_service), token: str = Depends(security)
):
    """Connect to an MCP server."""
    return await _process_server_connection(server_name, mcp_service)


def _handle_discover_service_error(e: ServiceError) -> None:
    """Handle service error during tool discovery."""
    logger.error(f"Service error discovering tools: {e}")
    raise HTTPException(status_code=400, detail=str(e))

def _handle_discover_unexpected_error(e: Exception) -> None:
    """Handle unexpected error during tool discovery."""
    logger.error(f"Unexpected error discovering tools: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/servers/{server_name}/tools", response_model=DiscoverToolsResponse)
async def discover_tools(
    server_name: str, mcp_service: IMCPClientService = Depends(get_mcp_client_service), token: str = Depends(security)
):
    """List tools from external server."""
    return await _process_tool_discovery(server_name, mcp_service)


def _build_execute_response(request: ExecuteToolRequest, result) -> ExecuteToolResponse:
    """Build tool execution response."""
    return ExecuteToolResponse(
        success=True, result=result, message=f"Tool '{request.tool_name}' executed successfully"
    )

def _handle_execute_service_error(e: ServiceError) -> None:
    """Handle service error during tool execution."""
    logger.error(f"Service error executing tool: {e}")
    raise HTTPException(status_code=400, detail=str(e))

def _handle_execute_unexpected_error(e: Exception) -> None:
    """Handle unexpected error during tool execution."""
    logger.error(f"Unexpected error executing tool: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/tools/execute", response_model=ExecuteToolResponse)
async def execute_tool(
    request: ExecuteToolRequest, mcp_service: IMCPClientService = Depends(get_mcp_client_service), token: str = Depends(security)
):
    """Execute tool from external server."""
    return await _process_tool_execution(request, mcp_service)


def _handle_resources_service_error(e: ServiceError) -> None:
    """Handle service error during resource retrieval."""
    logger.error(f"Service error getting resources: {e}")
    raise HTTPException(status_code=400, detail=str(e))

def _handle_resources_unexpected_error(e: Exception) -> None:
    """Handle unexpected error during resource retrieval."""
    logger.error(f"Unexpected error getting resources: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/servers/{server_name}/resources", response_model=GetResourcesResponse)
async def get_resources(
    server_name: str, mcp_service: IMCPClientService = Depends(get_mcp_client_service), token: str = Depends(security)
):
    """List resources from external server."""
    return await _process_resource_listing(server_name, mcp_service)


def _build_fetch_response(request: FetchResourceRequest, resource) -> FetchResourceResponse:
    """Build resource fetch response."""
    return FetchResourceResponse(
        success=True, resource=resource, message=f"Resource '{request.uri}' fetched successfully"
    )

def _handle_fetch_service_error(e: ServiceError) -> None:
    """Handle service error during resource fetching."""
    logger.error(f"Service error fetching resource: {e}")
    raise HTTPException(status_code=400, detail=str(e))

def _handle_fetch_unexpected_error(e: Exception) -> None:
    """Handle unexpected error during resource fetching."""
    logger.error(f"Unexpected error fetching resource: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/resources/read", response_model=FetchResourceResponse)
async def fetch_resource(
    request: FetchResourceRequest, mcp_service: IMCPClientService = Depends(get_mcp_client_service), token: str = Depends(security)
):
    """Read resource from external server."""
    return await _process_resource_fetching(request, mcp_service)


def _build_cache_description(server_name: Optional[str]) -> str:
    """Build cache description for response."""
    return f"for server '{server_name}'" if server_name else "all"

def _build_cache_response(server_name: Optional[str]) -> ClearCacheResponse:
    """Build cache clear response."""
    cache_desc = _build_cache_description(server_name)
    return ClearCacheResponse(success=True, message=f"Cache cleared {cache_desc}", cleared_entries=0)

def _handle_cache_service_error(e: ServiceError) -> None:
    """Handle service error during cache clearing."""
    logger.error(f"Service error clearing cache: {e}")
    raise HTTPException(status_code=400, detail=str(e))

def _handle_cache_unexpected_error(e: Exception) -> None:
    """Handle unexpected error during cache clearing."""
    logger.error(f"Unexpected error clearing cache: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")


# Unified error handlers (25-line limit compliance)
def _handle_register_error(e: Exception) -> None:
    """Handle registration error"""
    if isinstance(e, ServiceError):
        _handle_register_service_error(e)
    else:
        _handle_register_unexpected_error(e)

def _handle_list_error(e: Exception) -> None:
    """Handle listing error"""
    if isinstance(e, ServiceError):
        _handle_list_service_error(e)
    else:
        _handle_list_unexpected_error(e)

def _handle_connect_error(e: Exception) -> None:
    """Handle connection error"""
    if isinstance(e, ServiceError):
        _handle_connect_service_error(e)
    else:
        _handle_connect_unexpected_error(e)

def _handle_discover_error(e: Exception) -> None:
    """Handle discovery error"""
    if isinstance(e, ServiceError):
        _handle_discover_service_error(e)
    else:
        _handle_discover_unexpected_error(e)

def _handle_execute_error(e: Exception) -> None:
    """Handle execution error"""
    if isinstance(e, ServiceError):
        _handle_execute_service_error(e)
    else:
        _handle_execute_unexpected_error(e)

def _handle_resources_error(e: Exception) -> None:
    """Handle resources error"""
    if isinstance(e, ServiceError):
        _handle_resources_service_error(e)
    else:
        _handle_resources_unexpected_error(e)

def _handle_fetch_error(e: Exception) -> None:
    """Handle fetch error"""
    if isinstance(e, ServiceError):
        _handle_fetch_service_error(e)
    else:
        _handle_fetch_unexpected_error(e)

def _handle_cache_error(e: Exception) -> None:
    """Handle cache error"""
    if isinstance(e, ServiceError):
        _handle_cache_service_error(e)
    else:
        _handle_cache_unexpected_error(e)


# Helper functions to maintain 25-line limit

async def _process_server_registration(request: RegisterServerRequest, mcp_service: IMCPClientService) -> RegisterServerResponse:
    """Process server registration request"""
    try:
        success = await mcp_service.register_server(request.config.model_dump())
        return _handle_register_success(request, success)
    except (ServiceError, Exception) as e:
        _handle_register_error(e)


async def _process_server_listing(mcp_service: IMCPClientService) -> ListServersResponse:
    """Process server listing request"""
    try:
        servers = await mcp_service.list_servers()
        return ListServersResponse(servers=servers)
    except (ServiceError, Exception) as e:
        _handle_list_error(e)


async def _process_server_connection(server_name: str, mcp_service: IMCPClientService) -> ConnectServerResponse:
    """Process server connection request"""
    try:
        connection = await mcp_service.connect_to_server(server_name)
        return _build_connect_response(server_name, connection)
    except (ServiceError, Exception) as e:
        _handle_connect_error(e)


async def _process_tool_discovery(server_name: str, mcp_service: IMCPClientService) -> DiscoverToolsResponse:
    """Process tool discovery request"""
    try:
        tools = await mcp_service.discover_tools(server_name)
        return DiscoverToolsResponse(tools=tools)
    except (ServiceError, Exception) as e:
        _handle_discover_error(e)


async def _process_tool_execution(request: ExecuteToolRequest, mcp_service: IMCPClientService) -> ExecuteToolResponse:
    """Process tool execution request"""
    try:
        result = await mcp_service.execute_tool(request.server_name, request.tool_name, request.arguments)
        return _build_execute_response(request, result)
    except (ServiceError, Exception) as e:
        _handle_execute_error(e)


async def _process_resource_listing(server_name: str, mcp_service: IMCPClientService) -> GetResourcesResponse:
    """Process resource listing request"""
    try:
        resources = await mcp_service.get_resources(server_name)
        return GetResourcesResponse(resources=resources)
    except (ServiceError, Exception) as e:
        _handle_resources_error(e)


async def _process_resource_fetching(request: FetchResourceRequest, mcp_service: IMCPClientService) -> FetchResourceResponse:
    """Process resource fetching request"""
    try:
        resource = await mcp_service.fetch_resource(request.server_name, request.uri)
        return _build_fetch_response(request, resource)
    except (ServiceError, Exception) as e:
        _handle_fetch_error(e)


async def _process_cache_clearing(server_name: Optional[str], mcp_service: IMCPClientService) -> ClearCacheResponse:
    """Process cache clearing request"""
    try:
        await mcp_service.clear_cache(server_name)
        return _build_cache_response(server_name)
    except (ServiceError, Exception) as e:
        _handle_cache_error(e)

@router.delete("/cache", response_model=ClearCacheResponse)
async def clear_cache(
    server_name: Optional[str] = None, cache_type: Optional[str] = None,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service), token: str = Depends(security)
):
    """Clear MCP client cache."""
    return await _process_cache_clearing(server_name, mcp_service)


# Additional endpoints expected by frontend

@router.get("/servers/{server_name}/status")
async def get_server_status(
    server_name: str,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Get MCP server status."""
    try:
        # Mock implementation - return basic server info
        return {
            "success": True,
            "data": {
                "name": server_name,
                "status": "connected",
                "version": "1.0.0"
            }
        }
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get server status")


@router.post("/servers/{server_name}/disconnect")
async def disconnect_server(
    server_name: str,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Disconnect from MCP server."""
    try:
        # Mock implementation 
        return {"success": True, "message": f"Disconnected from server '{server_name}'"}
    except Exception as e:
        logger.error(f"Error disconnecting server: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect server")


@router.get("/tools")
async def discover_all_tools(
    server: Optional[str] = None,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Discover tools from all servers or specific server."""
    try:
        # Mock implementation - return empty tools list
        return {"success": True, "data": []}
    except Exception as e:
        logger.error(f"Error discovering tools: {e}")
        raise HTTPException(status_code=500, detail="Failed to discover tools")


@router.get("/tools/{server_name}/{tool_name}/schema")
async def get_tool_schema(
    server_name: str,
    tool_name: str,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Get schema for specific tool."""
    try:
        # Mock implementation
        return {"type": "object", "properties": {}, "required": []}
    except Exception as e:
        logger.error(f"Error getting tool schema: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tool schema")


@router.get("/resources")
async def list_resources_by_server(
    server: str,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """List resources from specific server via query param."""
    try:
        # Mock implementation - return empty resources list
        return {"success": True, "data": []}
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        raise HTTPException(status_code=500, detail="Failed to list resources")


@router.post("/resources/fetch")
async def fetch_resource_by_uri(
    request: dict,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Fetch resource by URI."""
    try:
        # Mock implementation
        return {"success": True, "data": None, "message": "Resource not found"}
    except Exception as e:
        logger.error(f"Error fetching resource: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch resource")


@router.post("/cache/clear")
async def clear_cache_post(
    request: dict,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Clear cache via POST request."""
    try:
        server_name = request.get("server_name")
        return await _process_cache_clearing(server_name, mcp_service)
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.get("/health")
async def mcp_health_check(token: str = Depends(security)):
    """MCP service health check."""
    return {"status": "healthy", "message": "MCP service is running"}


@router.get("/servers/{server_name}/health")
async def server_health_check(
    server_name: str,
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Check health of specific MCP server."""
    try:
        # Mock implementation
        return {"status": "healthy", "server": server_name}
    except Exception as e:
        logger.error(f"Error checking server health: {e}")
        raise HTTPException(status_code=500, detail="Failed to check server health")


@router.get("/connections")
async def get_server_connections(
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Get all server connections."""
    try:
        # Mock implementation - return empty connections
        return {"success": True, "data": []}
    except Exception as e:
        logger.error(f"Error getting connections: {e}")
        raise HTTPException(status_code=500, detail="Failed to get connections")


@router.post("/connections/refresh")
async def refresh_all_connections(
    mcp_service: IMCPClientService = Depends(get_mcp_client_service),
    token: str = Depends(security)
):
    """Refresh all server connections."""
    try:
        # Mock implementation
        return {"success": True, "message": "All connections refreshed"}
    except Exception as e:
        logger.error(f"Error refreshing connections: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh connections")