"""MCP Client Connection Manager.

Handles connection establishment to external MCP servers using different transports.
Modular component extracted to maintain 300-line limit compliance.
"""

import hashlib
from typing import Dict, Any
from datetime import datetime, timezone

from app.schemas.core_enums import MCPServerStatus
from app.core.exceptions_service import ServiceError
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MCPConnectionManager:
    """Manages connections to external MCP servers."""
    
    def __init__(self):
        self.connections: Dict[str, Any] = {}
    
    async def establish_connection(self, server) -> Dict[str, Any]:
        """Establish connection to MCP server based on transport."""
        connection_id = self._generate_connection_id(server.name)
        
        if server.transport == "stdio":
            return await self._connect_stdio(server, connection_id)
        elif server.transport == "http":
            return await self._connect_http(server, connection_id)
        elif server.transport == "websocket":
            return await self._connect_websocket(server, connection_id)
        else:
            raise ServiceError(f"Unsupported transport: {server.transport}")
    
    def _generate_connection_id(self, server_name: str) -> str:
        """Generate unique connection ID."""
        timestamp = str(datetime.now(timezone.utc).timestamp())
        return hashlib.sha256(f"{server_name}_{timestamp}".encode()).hexdigest()[:16]
    
    async def _connect_stdio(self, server, connection_id: str) -> Dict[str, Any]:
        """Connect to MCP server via stdio transport."""
        # Placeholder implementation - would use asyncio subprocess
        return self._build_connection_response(server, connection_id, "stdio")
    
    async def _connect_http(self, server, connection_id: str) -> Dict[str, Any]:
        """Connect to MCP server via HTTP transport."""
        # Placeholder implementation - would use httpx
        return self._build_connection_response(server, connection_id, "http")
    
    async def _connect_websocket(self, server, connection_id: str) -> Dict[str, Any]:
        """Connect to MCP server via WebSocket transport."""
        # Placeholder implementation - would use websockets
        return self._build_connection_response(server, connection_id, "websocket")
    
    def _build_connection_response(self, server, connection_id: str, transport: str) -> Dict[str, Any]:
        """Build standardized connection response."""
        return {
            "id": connection_id,
            "server_name": server.name,
            "transport": transport,
            "session_id": f"{transport}_{connection_id}",
            "capabilities": {"tools": True, "resources": True},
            "status": "connected",
            "created_at": datetime.now(timezone.utc)
        }
    
    def store_connection(self, server_name: str, connection: Dict[str, Any]):
        """Store active connection."""
        self.connections[server_name] = connection
    
    def get_connection(self, server_name: str) -> Dict[str, Any]:
        """Get active connection by server name."""
        return self.connections.get(server_name)
    
    def remove_connection(self, server_name: str) -> bool:
        """Remove connection by server name."""
        return self.connections.pop(server_name, None) is not None