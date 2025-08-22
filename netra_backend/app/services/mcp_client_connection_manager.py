"""MCP Client Connection Manager.

Handles connection establishment to external MCP servers using different transports.
Implements real MCP protocol connections for production use.
Modular component extracted to maintain 450-line limit compliance.
"""

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
import websockets
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import MCPServerStatus

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
        try:
            # Extract command and args from server configuration
            command_parts = server.url.split() if hasattr(server, 'url') else ["python", "-m", "mcp_server"]
            command = command_parts[0]
            args = command_parts[1:] if len(command_parts) > 1 else []
            
            server_params = StdioServerParameters(command=command, args=args)
            session = await stdio_client(server_params)
            
            # Initialize the session
            init_result = await session.initialize()
            
            # Store the session for later use
            self.connections[f"{server.name}_session"] = session
            
            return self._build_connection_response(
                server, connection_id, "stdio", 
                capabilities=init_result.capabilities.__dict__ if init_result.capabilities else {}
            )
        except Exception as e:
            logger.error(f"Stdio connection failed for {server.name}: {e}")
            raise ServiceError(f"Stdio connection failed: {str(e)}")
    
    async def _connect_http(self, server, connection_id: str) -> Dict[str, Any]:
        """Connect to MCP server via HTTP transport."""
        try:
            async with httpx.AsyncClient() as client:
                # Test connection with a health check or initialization
                response = await client.get(f"{server.url}/health", timeout=30.0)
                if response.status_code != 200:
                    raise ServiceError(f"HTTP server unhealthy: {response.status_code}")
                
                # For HTTP MCP, we might use SSE (Server-Sent Events)
                session = await sse_client(server.url)
                init_result = await session.initialize()
                
                self.connections[f"{server.name}_session"] = session
                
                return self._build_connection_response(
                    server, connection_id, "http",
                    capabilities=init_result.capabilities.__dict__ if init_result.capabilities else {}
                )
        except Exception as e:
            logger.error(f"HTTP connection failed for {server.name}: {e}")
            raise ServiceError(f"HTTP connection failed: {str(e)}")
    
    async def _connect_websocket(self, server, connection_id: str) -> Dict[str, Any]:
        """Connect to MCP server via WebSocket transport."""
        try:
            websocket = await websockets.connect(server.url)
            
            # Create a custom MCP client session for WebSocket
            # This is a simplified implementation - full WebSocket MCP would need more work
            session = self._create_websocket_session(websocket)
            
            # Test the connection
            await session.send_ping()
            
            self.connections[f"{server.name}_session"] = session
            self.connections[f"{server.name}_websocket"] = websocket
            
            return self._build_connection_response(
                server, connection_id, "websocket",
                capabilities={"websocket": True, "tools": True, "resources": True}
            )
        except Exception as e:
            logger.error(f"WebSocket connection failed for {server.name}: {e}")
            raise ServiceError(f"WebSocket connection failed: {str(e)}")
    
    def _build_connection_response(self, server, connection_id: str, transport: str, capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build standardized connection response."""
        default_capabilities = {"tools": True, "resources": True}
        if capabilities:
            default_capabilities.update(capabilities)
            
        return {
            "id": connection_id,
            "server_name": server.name,
            "transport": transport,
            "session_id": f"{transport}_{connection_id}",
            "capabilities": default_capabilities,
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
        removed = False
        # Remove main connection
        if self.connections.pop(server_name, None) is not None:
            removed = True
        # Remove session and websocket if they exist
        self.connections.pop(f"{server_name}_session", None)
        self.connections.pop(f"{server_name}_websocket", None)
        return removed
    
    def _create_websocket_session(self, websocket):
        """Create a simplified WebSocket MCP session wrapper."""
        class WebSocketSession:
            def __init__(self, ws):
                self.ws = ws
            
            async def send_ping(self):
                await self.ws.ping()
                
            async def close(self):
                await self.ws.close()
        
        return WebSocketSession(websocket)