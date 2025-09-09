"""MCP Client Service implementation.

Main service for connecting to external MCP servers and executing tools/resources.
Implements IMCPClientService interface with modular architecture compliance.
"""

import asyncio
from typing import Any, Dict, List, Optional

from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.app.database import get_db
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import MCPServerStatus
from netra_backend.app.schemas.mcp_client import MCPServerConfig
from netra_backend.app.services.database.mcp_client_repository import (
    MCPClientRepository,
)
from netra_backend.app.services.mcp_client_connection_manager import (
    MCPConnectionManager,
)
from netra_backend.app.services.mcp_client_resource_manager import MCPResourceManager
from netra_backend.app.services.mcp_client_tool_executor import ServiceMCPToolExecutor
from netra_backend.app.services.service_interfaces import IMCPClientService

logger = central_logger.get_logger(__name__)


class MCPClientService(IMCPClientService):
    """Main MCP Client Service implementation."""
    
    def __init__(self):
        self.server_repo = MCPClientRepository()
        self.connection_manager = MCPConnectionManager()
        self.tool_executor = ServiceMCPToolExecutor()
        self.resource_manager = MCPResourceManager()
    
    async def register_server(self, server_config: Dict[str, Any]) -> bool:
        """Register an external MCP server."""
        try:
            config = MCPServerConfig(**server_config)
            async with get_db() as db:
                server = await self.server_repo.create_server(db, config)
                logger.info(f"Registered MCP server: {config.name}")
                return True
        except Exception as e:
            logger.error(f"Failed to register server: {e}")
            raise ServiceError(f"Server registration failed: {str(e)}")
    
    async def connect_to_server(self, server_name: str) -> Dict[str, Any]:
        """Connect to a specific MCP server with timeout protection."""
        try:
            # CRITICAL FIX: Add 30-second timeout to prevent hanging connections
            return await asyncio.wait_for(
                self._connect_to_server_internal(server_name),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.error(f"Connection to server {server_name} timed out after 30 seconds")
            raise ServiceError(f"Connection timeout: {server_name} failed to connect within 30 seconds")
        except Exception as e:
            logger.error(f"Failed to connect to server {server_name}: {e}")
            raise ServiceError(f"Connection failed: {str(e)}")
    
    async def _connect_to_server_internal(self, server_name: str) -> Dict[str, Any]:
        """Internal connection method with database operations."""
        async with get_db() as db:
            server = await self.server_repo.get_server_by_name(db, server_name)
            if not server:
                raise ServiceError(f"Server '{server_name}' not found")
            
            connection = await self.connection_manager.establish_connection(server)
            self.connection_manager.store_connection(server_name, connection)
            
            await self.server_repo.update_server_status(
                db, server.id, MCPServerStatus.CONNECTED
            )
            
            return connection
    
    async def list_servers(self) -> List[Dict[str, Any]]:
        """List all registered MCP servers."""
        try:
            async with get_db() as db:
                servers = await self.server_repo.list_servers(db)
                return [self._server_to_dict(server) for server in servers]
        except Exception as e:
            logger.error(f"Failed to list servers: {e}")
            raise ServiceError(f"Failed to list servers: {str(e)}")
    
    def _server_to_dict(self, server) -> Dict[str, Any]:
        """Convert server model to dictionary."""
        return {
            "id": server.id,
            "name": server.name,
            "url": server.url,
            "transport": server.transport,
            "status": server.status,
            "capabilities": server.capabilities,
            "metadata": server.metadata_,
            "last_health_check": server.last_health_check,
            "created_at": server.created_at,
            "updated_at": server.updated_at
        }
    
    async def discover_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Discover tools from an MCP server."""
        return await self.tool_executor.discover_tools(server_name)
    
    async def execute_tool(self, server_name: str, tool_name: str, 
                          arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on an MCP server with timeout protection."""
        try:
            # CRITICAL FIX: Add 30-second timeout to prevent hanging tool executions
            return await asyncio.wait_for(
                self._execute_tool_internal(server_name, tool_name, arguments),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.error(f"Tool execution timed out: {tool_name} on {server_name} after 30 seconds")
            raise ServiceError(f"Tool execution timeout: {tool_name} on {server_name}")
    
    async def _execute_tool_internal(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Internal tool execution method."""
        async with get_db() as db:
            return await self.tool_executor.execute_tool(
                db, server_name, tool_name, arguments
            )
    
    async def get_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """Get resources from an MCP server."""
        return await self.resource_manager.get_resources(server_name)
    
    async def fetch_resource(self, server_name: str, uri: str) -> Dict[str, Any]:
        """Fetch a specific resource from an MCP server."""
        async with get_db() as db:
            return await self.resource_manager.fetch_resource(db, server_name, uri)
    
    async def clear_cache(self, server_name: Optional[str] = None):
        """Clear MCP client cache."""
        try:
            self.tool_executor.clear_tool_cache(server_name)
            self.resource_manager.clear_resource_cache(server_name)
            
            log_msg = f"Cleared cache for server: {server_name}" if server_name else "Cleared all MCP client cache"
            logger.info(log_msg)
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise ServiceError(f"Cache clear failed: {str(e)}")