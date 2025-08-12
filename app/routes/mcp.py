"""
MCP Routes

FastAPI routes for Model Context Protocol server.
"""

from typing import Optional, Dict, Any
import os

from fastapi import APIRouter, Depends, WebSocket, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_async_db
from app.dependencies import get_agent_service, get_thread_service, get_corpus_service, get_security_service
from app.auth.auth_dependencies import get_current_user_optional
from app.schemas import UserInDB
from app.services.mcp_service import MCPService
from app.services.synthetic_data_service import SyntheticDataService
from app.services.supply_catalog_service import SupplyCatalogService
from app.mcp.transports.http_transport import HttpTransport
from app.mcp.transports.websocket_transport import WebSocketTransport
from app.logging_config import CentralLogger

logger = CentralLogger()

router = APIRouter(prefix="/mcp", tags=["MCP"])

# Global MCP service instance (initialized on first request)
_mcp_service: Optional[MCPService] = None


async def get_mcp_service(
    agent_service=Depends(get_agent_service),
    thread_service=Depends(get_thread_service),
    corpus_service=Depends(get_corpus_service),
    security_service=Depends(get_security_service)
) -> MCPService:
    """Get or create MCP service instance"""
    global _mcp_service
    
    if _mcp_service is None:
        # Create synthetic data and supply catalog services
        # These would normally come from dependencies
        synthetic_data_service = SyntheticDataService()
        supply_catalog_service = SupplyCatalogService()
        
        _mcp_service = MCPService(
            agent_service=agent_service,
            thread_service=thread_service,
            corpus_service=corpus_service,
            synthetic_data_service=synthetic_data_service,
            security_service=security_service,
            supply_catalog_service=supply_catalog_service
        )
        
        logger.info("MCP service initialized")
        
    return _mcp_service


# HTTP Transport routes
http_transport = None


@router.on_event("startup")
async def setup_http_transport():
    """Setup HTTP transport on startup"""
    global http_transport
    
    if os.getenv("MCP_ENABLED", "true").lower() == "true":
        # Get MCP service (this will initialize it)
        mcp_service = await get_mcp_service(
            agent_service=None,  # Will be injected per request
            thread_service=None,
            corpus_service=None,
            security_service=None
        )
        
        # Create HTTP transport with MCP server
        http_transport = HttpTransport(mcp_service.get_mcp_server())
        
        # Include HTTP transport routes
        router.include_router(http_transport.get_router())
        
        logger.info("MCP HTTP transport initialized")


# WebSocket endpoint
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    api_key: Optional[str] = Query(None, description="API key for authentication"),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """
    WebSocket endpoint for MCP
    
    Connect with: ws://localhost:8000/mcp/ws?api_key=YOUR_KEY
    """
    ws_transport = WebSocketTransport(mcp_service.get_mcp_server())
    await ws_transport.handle_websocket(websocket, api_key)


@router.get("/status")
async def get_mcp_status(
    user: Optional[UserInDB] = Depends(get_current_user_optional),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """Get MCP server status"""
    server = mcp_service.get_mcp_server()
    
    return {
        "enabled": True,
        "server": {
            "name": server.config.server_name,
            "version": server.config.server_version,
            "protocol_version": server.config.protocol_version
        },
        "capabilities": {
            "tools": server.config.enable_tools,
            "resources": server.config.enable_resources,
            "prompts": server.config.enable_prompts,
            "sampling": server.config.enable_sampling
        },
        "sessions": {
            "active": len(server.sessions),
            "max": server.config.max_sessions
        },
        "transports": ["stdio", "http", "websocket"],
        "authenticated": user is not None
    }


@router.post("/register-client")
async def register_mcp_client(
    name: str,
    client_type: str,
    permissions: Optional[list[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db_session: AsyncSession = Depends(get_async_db),
    user: UserInDB = Depends(get_current_user_optional),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """Register a new MCP client"""
    if not user or "admin" not in getattr(user, "roles", []):
        raise HTTPException(status_code=403, detail="Admin access required")
        
    client = await mcp_service.register_client(
        db_session=db_session,
        name=name,
        client_type=client_type,
        permissions=permissions,
        metadata=metadata
    )
    
    return {
        "client_id": client.id,
        "name": client.name,
        "client_type": client.client_type,
        "permissions": client.permissions,
        "created_at": client.created_at.isoformat()
    }


@router.get("/tools")
async def list_available_tools(
    category: Optional[str] = None,
    user: Optional[UserInDB] = Depends(get_current_user_optional),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """List available MCP tools"""
    server = mcp_service.get_mcp_server()
    tools = await server.tool_registry.list_tools()
    
    if category:
        tools = [t for t in tools if t.get("category") == category]
        
    return {
        "tools": tools,
        "count": len(tools)
    }


@router.get("/resources")
async def list_available_resources(
    user: Optional[UserInDB] = Depends(get_current_user_optional),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """List available MCP resources"""
    server = mcp_service.get_mcp_server()
    resources = await server.resource_manager.list_resources()
    
    return {
        "resources": resources,
        "count": len(resources)
    }


@router.get("/prompts")
async def list_available_prompts(
    category: Optional[str] = None,
    user: Optional[UserInDB] = Depends(get_current_user_optional),
    mcp_service: MCPService = Depends(get_mcp_service)
):
    """List available MCP prompts"""
    server = mcp_service.get_mcp_server()
    prompts = await server.prompt_manager.list_prompts()
    
    if category:
        prompts = [p for p in prompts if p.get("category") == category]
        
    return {
        "prompts": prompts,
        "count": len(prompts)
    }


@router.get("/config")
async def get_mcp_config(
    user: Optional[UserInDB] = Depends(get_current_user_optional)
):
    """Get MCP configuration for clients"""
    base_url = os.getenv("MCP_BASE_URL", "http://localhost:8000")
    
    # Configuration for different clients
    configs = {
        "claude": {
            "mcpServers": {
                "netra": {
                    "command": "python",
                    "args": ["-m", "app.mcp.transports.stdio_transport"],
                    "env": {
                        "NETRA_API_KEY": "${NETRA_API_KEY}",
                        "NETRA_BASE_URL": base_url
                    }
                }
            }
        },
        "cursor": {
            "mcp": {
                "servers": {
                    "netra": {
                        "transport": "stdio",
                        "command": "python -m app.mcp.transports.stdio_transport"
                    }
                }
            }
        },
        "http": {
            "endpoint": f"{base_url}/mcp",
            "transport": "http",
            "authentication": "Bearer token or API key"
        },
        "websocket": {
            "endpoint": f"ws://{base_url.replace('http://', '').replace('https://', '')}/mcp/ws",
            "transport": "websocket",
            "authentication": "Query parameter: api_key"
        }
    }
    
    return configs

async def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute MCP tool for testing."""
    from app.services import mcp_service
    return await mcp_service.execute_tool(tool_name, params)