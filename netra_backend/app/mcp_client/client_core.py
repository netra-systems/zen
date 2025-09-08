"""MCP Client Core - Main client class for external MCP server integration.

Provides the main MCPClient class that handles connection management,
protocol negotiation, and session management for external MCP servers.
This enables Netra to connect to external tools and resources.

Key Features:
- Async-first implementation with proper error handling
- Multiple simultaneous server connections
- Protocol negotiation and session management
- Strong typing with Pydantic models
- Comprehensive logging and monitoring

Line count: <300 lines (architectural requirement)
Function limit: ≤8 lines per function (architectural requirement)
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from netra_backend.app.core.exceptions import NetraException, ServiceError
from netra_backend.app.core.unified_logging import UnifiedLogger
from netra_backend.app.mcp_client.models import (
    ConnectionStatus,
    MCPConnection,
    MCPOperationContext,
    MCPResource,
    MCPServerConfig,
    MCPTool,
    MCPToolResult,
    MCPTransport,
)

logger = UnifiedLogger()


class MCPClientError(NetraException):
    """MCP Client specific exceptions."""
    
    def __init__(self, message: str, server_name: Optional[str] = None):
        super().__init__(message)
        self.server_name = server_name


class MCPConnectionError(MCPClientError):
    """MCP connection specific exceptions."""
    pass


class MCPProtocolError(MCPClientError):
    """MCP protocol specific exceptions."""
    pass


class MCPClient:
    """Main MCP client for connecting to external MCP servers.
    
    Manages connections, protocol negotiation, and provides unified interface
    for tool execution and resource access across multiple external servers.
    """
    
    def __init__(self):
        """Initialize MCP client with empty connection pool."""
        self._connections: Dict[str, MCPConnection] = {}
        self._active_sessions: Set[str] = set()
        self._connection_lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize MCP client infrastructure."""
        if self._initialized:
            return
        logger.info("Initializing MCP client")
        self._initialized = True
    
    async def shutdown(self) -> None:
        """Shutdown all connections and cleanup resources."""
        logger.info("Shutting down MCP client")
        await self._disconnect_all()
        self._initialized = False
    
    async def connect(self, server_config: MCPServerConfig) -> MCPConnection:
        """Connect to external MCP server with configuration."""
        await self._validate_connection_request(server_config)
        connection = await self._create_connection(server_config)
        await self._establish_connection(connection, server_config)
        await self._negotiate_protocol(connection)
        await self._register_connection(connection)
        return connection
    
    async def disconnect(self, connection: MCPConnection) -> None:
        """Disconnect from MCP server and cleanup resources."""
        await self._validate_disconnect_request(connection)
        await self._close_connection(connection)
        await self._unregister_connection(connection)
        logger.info(f"Disconnected from server: {connection.server_name}")
    
    async def discover_tools(self, connection: MCPConnection) -> List[MCPTool]:
        """Discover available tools from connected MCP server."""
        await self._validate_connection_active(connection)
        context = self._create_operation_context(connection, "discover_tools")
        tools = await self._request_tools_list(connection, context)
        await self._process_tools_response(tools, connection)
        return tools
    
    async def execute_tool(
        self, 
        connection: MCPConnection, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> MCPToolResult:
        """Execute tool on external MCP server with arguments."""
        await self._validate_tool_execution(connection, tool_name, arguments)
        return await self._perform_tool_execution(connection, tool_name, arguments)

    async def _perform_tool_execution(
        self, 
        connection: MCPConnection, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> MCPToolResult:
        """Perform the actual tool execution steps."""
        context = self._create_operation_context(connection, "execute_tool")
        return await self._execute_tool_with_context(connection, tool_name, arguments, context)

    async def _execute_tool_with_context(
        self, 
        connection: MCPConnection, 
        tool_name: str, 
        arguments: Dict[str, Any], 
        context: MCPOperationContext
    ) -> MCPToolResult:
        """Execute tool with context and process result."""
        result = await self._send_tool_execution(connection, tool_name, arguments, context)
        await self._process_tool_result(result, connection, tool_name)
        return result
    
    async def get_resource(self, connection: MCPConnection, uri: str) -> MCPResource:
        """Get resource from external MCP server by URI."""
        await self._validate_resource_request(connection, uri)
        context = self._create_operation_context(connection, "get_resource")
        resource = await self._request_resource(connection, uri, context)
        await self._process_resource_response(resource, connection)
        return resource
    
    async def list_resources(self, connection: MCPConnection) -> List[MCPResource]:
        """List available resources from connected MCP server."""
        await self._validate_connection_active(connection)
        context = self._create_operation_context(connection, "list_resources")
        resources = await self._request_resources_list(connection, context)
        await self._process_resources_response(resources, connection)
        return resources
    
    async def get_connection(self, server_name: str) -> Optional[MCPConnection]:
        """Get active connection by server name."""
        return self._connections.get(server_name)
    
    async def list_connections(self) -> List[MCPConnection]:
        """List all active connections."""
        return list(self._connections.values())
    
    async def _validate_connection_request(self, config: MCPServerConfig) -> None:
        """Validate connection request parameters."""
        if config.name in self._connections:
            raise MCPConnectionError(f"Already connected to server: {config.name}")
        if not self._initialized:
            raise MCPClientError("MCP client not initialized")
    
    async def _create_connection(self, config: MCPServerConfig) -> MCPConnection:
        """Create new connection object."""
        return MCPConnection(
            server_name=config.name,
            transport=config.transport,
            status=ConnectionStatus.CONNECTING,
            created_at=datetime.now(timezone.utc)
        )
    
    async def _establish_connection(self, connection: MCPConnection, config: MCPServerConfig) -> None:
        """Establish transport-specific connection."""
        try:
            await self._connect_transport(connection, config)
            connection.status = ConnectionStatus.CONNECTED
        except Exception as e:
            connection.status = ConnectionStatus.FAILED
            raise MCPConnectionError(f"Failed to connect to {config.name}: {str(e)}")
    
    async def _negotiate_protocol(self, connection: MCPConnection) -> None:
        """Negotiate MCP protocol version and capabilities."""
        try:
            capabilities = await self._exchange_capabilities(connection)
            connection.capabilities = capabilities
        except Exception as e:
            raise MCPProtocolError(f"Protocol negotiation failed: {str(e)}")
    
    async def _register_connection(self, connection: MCPConnection) -> None:
        """Register connection in active connections pool."""
        async with self._connection_lock:
            self._connections[connection.server_name] = connection
            self._active_sessions.add(connection.session_id or connection.id)
        logger.info(f"Connected to MCP server: {connection.server_name}")
    
    async def _validate_disconnect_request(self, connection: MCPConnection) -> None:
        """Validate disconnect request."""
        if connection.server_name not in self._connections:
            raise MCPConnectionError(f"Connection not found: {connection.server_name}")
    
    async def _close_connection(self, connection: MCPConnection) -> None:
        """Close transport connection."""
        try:
            await self._disconnect_transport(connection)
            connection.status = ConnectionStatus.DISCONNECTED
        except Exception as e:
            logger.error(f"Error closing connection {connection.server_name}: {str(e)}")
    
    async def _unregister_connection(self, connection: MCPConnection) -> None:
        """Remove connection from active pool."""
        async with self._connection_lock:
            self._connections.pop(connection.server_name, None)
            self._active_sessions.discard(connection.session_id or connection.id)
    
    async def _validate_connection_active(self, connection: MCPConnection) -> None:
        """Validate connection is active and usable."""
        if connection.status != ConnectionStatus.CONNECTED:
            raise MCPConnectionError(f"Connection not active: {connection.server_name}")
    
    def _create_operation_context(self, connection: MCPConnection, operation: str) -> MCPOperationContext:
        """Create operation context for tracking."""
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        return MCPOperationContext(
            server_name=connection.server_name,
            operation_type=operation,
            trace_id=UnifiedIdGenerator.generate_base_id("mcp_trace")
        )
    
    async def _validate_tool_execution(self, connection: MCPConnection, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Validate tool execution request."""
        await self._validate_connection_active(connection)
        if not tool_name or not isinstance(tool_name, str):
            raise MCPClientError("Invalid tool name")
    
    async def _validate_resource_request(self, connection: MCPConnection, uri: str) -> None:
        """Validate resource request."""
        await self._validate_connection_active(connection)
        if not uri or not isinstance(uri, str):
            raise MCPClientError("Invalid resource URI")
    
    async def _disconnect_all(self) -> None:
        """Disconnect all active connections."""
        connections = list(self._connections.values())
        for connection in connections:
            try:
                await self.disconnect(connection)
            except Exception as e:
                logger.error(f"Error disconnecting {connection.server_name}: {str(e)}")
    
    # Transport-specific methods (to be implemented by transport clients)
    async def _connect_transport(self, connection: MCPConnection, config: MCPServerConfig) -> None:
        """Connect using transport-specific implementation."""
        raise NotImplementedError("Transport connection not implemented")
    
    async def _disconnect_transport(self, connection: MCPConnection) -> None:
        """Disconnect using transport-specific implementation."""
        raise NotImplementedError("Transport disconnection not implemented")
    
    async def _exchange_capabilities(self, connection: MCPConnection) -> Dict[str, Any]:
        """Exchange capabilities with server."""
        raise NotImplementedError("Capability exchange not implemented")
    
    async def _request_tools_list(self, connection: MCPConnection, context: MCPOperationContext) -> List[MCPTool]:
        """Request tools list from server."""
        raise NotImplementedError("Tools list request not implemented")
    
    async def _send_tool_execution(
        self, 
        connection: MCPConnection, 
        tool_name: str, 
        arguments: Dict[str, Any],
        context: MCPOperationContext
    ) -> MCPToolResult:
        """Send tool execution request."""
        raise NotImplementedError("Tool execution not implemented")
    
    async def _request_resource(
        self, 
        connection: MCPConnection, 
        uri: str, 
        context: MCPOperationContext
    ) -> MCPResource:
        """Request resource from server."""
        raise NotImplementedError("Resource request not implemented")
    
    async def _request_resources_list(
        self, 
        connection: MCPConnection, 
        context: MCPOperationContext
    ) -> List[MCPResource]:
        """Request resources list from server."""
        raise NotImplementedError("Resources list request not implemented")
    
    async def _process_tools_response(self, tools: List[MCPTool], connection: MCPConnection) -> None:
        """Process tools response."""
        logger.info(f"Discovered {len(tools)} tools from {connection.server_name}")
    
    async def _process_tool_result(self, result: MCPToolResult, connection: MCPConnection, tool_name: str) -> None:
        """Process tool execution result."""
        status = "failed" if result.is_error else "succeeded"
        logger.info(f"Tool {tool_name} {status} for {connection.server_name}")
    
    async def _process_resource_response(self, resource: MCPResource, connection: MCPConnection) -> None:
        """Process resource response."""
        logger.info(f"Retrieved resource {resource.uri} from {connection.server_name}")
    
    async def _process_resources_response(self, resources: List[MCPResource], connection: MCPConnection) -> None:
        """Process resources list response."""
        logger.info(f"Listed {len(resources)} resources from {connection.server_name}")