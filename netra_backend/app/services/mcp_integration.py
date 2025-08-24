"""
MCP (Model Context Protocol) Integration Service

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: AI Agent Interoperability & Development Velocity
- Value Impact: Enables seamless integration with MCP-compatible AI tools
- Strategic Impact: Essential for multi-agent workflows and tool composition

Provides MCP client management, tool integration, and resource handling.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MCPClientStatus(str, Enum):
    """Status of MCP client connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class MCPMessageType(str, Enum):
    """MCP message types."""
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    LIST_TOOLS = "listTools"
    CALL_TOOL = "callTool"
    LIST_RESOURCES = "listResources"
    READ_RESOURCE = "readResource"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    category: str = "general"
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResource:
    """MCP resource definition."""
    uri: str
    name: str
    mime_type: str = "text/plain"
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPMessage:
    """MCP protocol message."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    
    @classmethod
    def create_request(cls, method: str, params: Optional[Dict[str, Any]] = None,
                      message_id: Optional[str] = None) -> 'MCPMessage':
        """Create a request message."""
        return cls(
            id=message_id or str(uuid.uuid4()),
            method=method,
            params=params or {}
        )
    
    @classmethod
    def create_response(cls, message_id: Union[str, int], result: Any = None,
                       error: Optional[Dict[str, Any]] = None) -> 'MCPMessage':
        """Create a response message."""
        return cls(
            id=message_id,
            result=result,
            error=error
        )
    
    @classmethod
    def create_notification(cls, method: str, params: Optional[Dict[str, Any]] = None) -> 'MCPMessage':
        """Create a notification message."""
        return cls(
            method=method,
            params=params or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"jsonrpc": self.jsonrpc}
        
        if self.id is not None:
            result["id"] = self.id
        if self.method is not None:
            result["method"] = self.method
        if self.params is not None:
            result["params"] = self.params
        if self.result is not None:
            result["result"] = self.result
        if self.error is not None:
            result["error"] = self.error
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """Create from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error")
        )


class MCPClient:
    """MCP protocol client."""
    
    def __init__(self, client_id: str, transport_url: str):
        self.client_id = client_id
        self.transport_url = transport_url
        self.status = MCPClientStatus.DISCONNECTED
        self.capabilities: Dict[str, Any] = {}
        self.server_info: Dict[str, Any] = {}
        self.available_tools: Dict[str, MCPTool] = {}
        self.available_resources: Dict[str, MCPResource] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.connection_task: Optional[asyncio.Task] = None
        self.last_activity = time.time()
        
        # Register default handlers
        self.message_handlers.update({
            "initialized": self._handle_initialized,
            "listTools": self._handle_list_tools,
            "listResources": self._handle_list_resources,
            "notification": self._handle_notification
        })
    
    async def connect(self) -> bool:
        """Connect to MCP server."""
        try:
            self.status = MCPClientStatus.CONNECTING
            logger.info(f"Connecting MCP client {self.client_id} to {self.transport_url}")
            
            # Initialize connection
            init_message = MCPMessage.create_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": True, "listChanged": True}
                    },
                    "clientInfo": {
                        "name": "netra-mcp-client",
                        "version": "1.0.0"
                    }
                }
            )
            
            # Send initialization (simplified - would use actual transport)
            response = await self._send_message(init_message)
            
            if response and not response.error:
                self.server_info = response.result.get("serverInfo", {})
                self.capabilities = response.result.get("capabilities", {})
                self.status = MCPClientStatus.CONNECTED
                
                # Send initialized notification
                initialized_msg = MCPMessage.create_notification("initialized")
                await self._send_message(initialized_msg)
                
                # Discover available tools and resources
                await self._discover_tools()
                await self._discover_resources()
                
                logger.info(f"MCP client {self.client_id} connected successfully")
                return True
            else:
                error_msg = response.error if response else "No response received"
                logger.error(f"MCP initialization failed: {error_msg}")
                self.status = MCPClientStatus.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect MCP client {self.client_id}: {e}")
            self.status = MCPClientStatus.ERROR
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        try:
            self.status = MCPClientStatus.DISCONNECTED
            
            # Cancel pending requests
            for future in self.pending_requests.values():
                future.cancel()
            self.pending_requests.clear()
            
            if self.connection_task:
                self.connection_task.cancel()
                try:
                    await self.connection_task
                except asyncio.CancelledError:
                    pass
            
            logger.info(f"MCP client {self.client_id} disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting MCP client {self.client_id}: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call an MCP tool."""
        try:
            if tool_name not in self.available_tools:
                logger.error(f"Tool {tool_name} not available on MCP client {self.client_id}")
                return None
            
            message = MCPMessage.create_request(
                "tools/call",
                {
                    "name": tool_name,
                    "arguments": arguments
                }
            )
            
            response = await self._send_message(message)
            
            if response and not response.error:
                self.last_activity = time.time()
                return response.result
            else:
                error_msg = response.error if response else "No response received"
                logger.error(f"Tool call failed: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return None
    
    async def read_resource(self, resource_uri: str) -> Optional[Dict[str, Any]]:
        """Read an MCP resource."""
        try:
            message = MCPMessage.create_request(
                "resources/read",
                {"uri": resource_uri}
            )
            
            response = await self._send_message(message)
            
            if response and not response.error:
                self.last_activity = time.time()
                return response.result
            else:
                error_msg = response.error if response else "No response received"
                logger.error(f"Resource read failed: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"Error reading resource {resource_uri}: {e}")
            return None
    
    async def _send_message(self, message: MCPMessage) -> Optional[MCPMessage]:
        """Send message to MCP server."""
        try:
            # Simplified transport - in production would use actual WebSocket/HTTP
            await asyncio.sleep(0.01)  # Simulate network call
            
            # Mock successful response for non-error scenarios
            if message.method == "initialize":
                return MCPMessage.create_response(
                    message.id,
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {"listChanged": True},
                            "resources": {"listChanged": True}
                        },
                        "serverInfo": {
                            "name": "mock-mcp-server",
                            "version": "1.0.0"
                        }
                    }
                )
            elif message.method == "tools/list":
                return MCPMessage.create_response(
                    message.id,
                    {
                        "tools": [
                            {
                                "name": "example_tool",
                                "description": "Example MCP tool",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "input": {"type": "string"}
                                    }
                                }
                            }
                        ]
                    }
                )
            elif message.method == "resources/list":
                return MCPMessage.create_response(
                    message.id,
                    {
                        "resources": [
                            {
                                "uri": "example://resource",
                                "name": "Example Resource",
                                "mimeType": "text/plain"
                            }
                        ]
                    }
                )
            elif message.method == "tools/call":
                return MCPMessage.create_response(
                    message.id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Tool executed with args: {message.params.get('arguments', {})}"
                            }
                        ]
                    }
                )
            else:
                # Default success response
                return MCPMessage.create_response(message.id, {"status": "ok"})
                
        except Exception as e:
            logger.error(f"Error sending MCP message: {e}")
            return MCPMessage.create_response(
                message.id,
                error={"code": -1, "message": str(e)}
            )
    
    async def _discover_tools(self) -> None:
        """Discover available tools."""
        try:
            message = MCPMessage.create_request("tools/list")
            response = await self._send_message(message)
            
            if response and not response.error:
                tools_data = response.result.get("tools", [])
                for tool_data in tools_data:
                    tool = MCPTool(
                        name=tool_data["name"],
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {})
                    )
                    self.available_tools[tool.name] = tool
                
                logger.info(f"Discovered {len(self.available_tools)} tools for MCP client {self.client_id}")
                
        except Exception as e:
            logger.error(f"Error discovering tools: {e}")
    
    async def _discover_resources(self) -> None:
        """Discover available resources."""
        try:
            message = MCPMessage.create_request("resources/list")
            response = await self._send_message(message)
            
            if response and not response.error:
                resources_data = response.result.get("resources", [])
                for resource_data in resources_data:
                    resource = MCPResource(
                        uri=resource_data["uri"],
                        name=resource_data.get("name", ""),
                        mime_type=resource_data.get("mimeType", "text/plain"),
                        description=resource_data.get("description", "")
                    )
                    self.available_resources[resource.uri] = resource
                
                logger.info(f"Discovered {len(self.available_resources)} resources for MCP client {self.client_id}")
                
        except Exception as e:
            logger.error(f"Error discovering resources: {e}")
    
    async def _handle_initialized(self, message: MCPMessage) -> None:
        """Handle initialized notification."""
        logger.debug(f"MCP client {self.client_id} initialized")
    
    async def _handle_list_tools(self, message: MCPMessage) -> None:
        """Handle list tools request."""
        tools_list = [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for tool in self.available_tools.values()
        ]
        
        response = MCPMessage.create_response(message.id, {"tools": tools_list})
        await self._send_message(response)
    
    async def _handle_list_resources(self, message: MCPMessage) -> None:
        """Handle list resources request."""
        resources_list = [
            {
                "uri": resource.uri,
                "name": resource.name,
                "mimeType": resource.mime_type,
                "description": resource.description
            }
            for resource in self.available_resources.values()
        ]
        
        response = MCPMessage.create_response(message.id, {"resources": resources_list})
        await self._send_message(response)
    
    async def _handle_notification(self, message: MCPMessage) -> None:
        """Handle notification message."""
        logger.debug(f"Received notification from MCP client {self.client_id}: {message.method}")
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get client information and status."""
        return {
            "client_id": self.client_id,
            "transport_url": self.transport_url,
            "status": self.status,
            "server_info": self.server_info,
            "capabilities": self.capabilities,
            "available_tools": list(self.available_tools.keys()),
            "available_resources": list(self.available_resources.keys()),
            "last_activity": self.last_activity
        }


class MCPIntegrationService:
    """Main MCP integration service."""
    
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.tool_registry: Dict[str, str] = {}  # tool_name -> client_id
        self.resource_registry: Dict[str, str] = {}  # resource_uri -> client_id
        self.integration_stats = {
            "clients_created": 0,
            "tools_called": 0,
            "resources_read": 0,
            "errors": 0
        }
    
    async def create_client(self, client_id: str, transport_url: str) -> bool:
        """Create a new MCP client."""
        try:
            if client_id in self.clients:
                logger.warning(f"MCP client {client_id} already exists")
                return False
            
            client = MCPClient(client_id, transport_url)
            
            if await client.connect():
                self.clients[client_id] = client
                self._register_client_tools(client)
                self._register_client_resources(client)
                self.integration_stats["clients_created"] += 1
                
                logger.info(f"Created MCP client {client_id}")
                return True
            else:
                logger.error(f"Failed to connect MCP client {client_id}")
                return False
                
        except Exception as e:
            self.integration_stats["errors"] += 1
            logger.error(f"Error creating MCP client {client_id}: {e}")
            return False
    
    async def remove_client(self, client_id: str) -> bool:
        """Remove an MCP client."""
        try:
            client = self.clients.get(client_id)
            if not client:
                return False
            
            await client.disconnect()
            del self.clients[client_id]
            
            # Clean up registries
            self.tool_registry = {k: v for k, v in self.tool_registry.items() if v != client_id}
            self.resource_registry = {k: v for k, v in self.resource_registry.items() if v != client_id}
            
            logger.info(f"Removed MCP client {client_id}")
            return True
            
        except Exception as e:
            self.integration_stats["errors"] += 1
            logger.error(f"Error removing MCP client {client_id}: {e}")
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call an MCP tool."""
        try:
            client_id = self.tool_registry.get(tool_name)
            if not client_id:
                logger.error(f"Tool {tool_name} not registered")
                return None
            
            client = self.clients.get(client_id)
            if not client:
                logger.error(f"MCP client {client_id} not found")
                return None
            
            result = await client.call_tool(tool_name, arguments)
            if result:
                self.integration_stats["tools_called"] += 1
            else:
                self.integration_stats["errors"] += 1
            
            return result
            
        except Exception as e:
            self.integration_stats["errors"] += 1
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return None
    
    async def read_resource(self, resource_uri: str) -> Optional[Dict[str, Any]]:
        """Read an MCP resource."""
        try:
            client_id = self.resource_registry.get(resource_uri)
            if not client_id:
                logger.error(f"Resource {resource_uri} not registered")
                return None
            
            client = self.clients.get(client_id)
            if not client:
                logger.error(f"MCP client {client_id} not found")
                return None
            
            result = await client.read_resource(resource_uri)
            if result:
                self.integration_stats["resources_read"] += 1
            else:
                self.integration_stats["errors"] += 1
            
            return result
            
        except Exception as e:
            self.integration_stats["errors"] += 1
            logger.error(f"Error reading MCP resource {resource_uri}: {e}")
            return None
    
    def _register_client_tools(self, client: MCPClient) -> None:
        """Register tools from a client."""
        for tool_name in client.available_tools.keys():
            self.tool_registry[tool_name] = client.client_id
        
        logger.debug(f"Registered {len(client.available_tools)} tools from client {client.client_id}")
    
    def _register_client_resources(self, client: MCPClient) -> None:
        """Register resources from a client."""
        for resource_uri in client.available_resources.keys():
            self.resource_registry[resource_uri] = client.client_id
        
        logger.debug(f"Registered {len(client.available_resources)} resources from client {client.client_id}")
    
    def list_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all available MCP tools."""
        tools = {}
        
        for tool_name, client_id in self.tool_registry.items():
            client = self.clients.get(client_id)
            if client and tool_name in client.available_tools:
                tool = client.available_tools[tool_name]
                tools[tool_name] = {
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                    "client_id": client_id,
                    "category": tool.category
                }
        
        return tools
    
    def list_available_resources(self) -> Dict[str, Dict[str, Any]]:
        """List all available MCP resources."""
        resources = {}
        
        for resource_uri, client_id in self.resource_registry.items():
            client = self.clients.get(client_id)
            if client and resource_uri in client.available_resources:
                resource = client.available_resources[resource_uri]
                resources[resource_uri] = {
                    "name": resource.name,
                    "mime_type": resource.mime_type,
                    "description": resource.description,
                    "client_id": client_id
                }
        
        return resources
    
    def get_client_status(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an MCP client."""
        client = self.clients.get(client_id)
        return client.get_client_info() if client else None
    
    def list_clients(self) -> Dict[str, Dict[str, Any]]:
        """List all MCP clients."""
        return {
            client_id: client.get_client_info()
            for client_id, client in self.clients.items()
        }
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration service statistics."""
        stats = self.integration_stats.copy()
        stats["active_clients"] = len(self.clients)
        stats["registered_tools"] = len(self.tool_registry)
        stats["registered_resources"] = len(self.resource_registry)
        return stats


# Global MCP integration service
_mcp_integration_service: Optional[MCPIntegrationService] = None

def get_mcp_integration_service() -> MCPIntegrationService:
    """Get global MCP integration service instance."""
    global _mcp_integration_service
    if _mcp_integration_service is None:
        _mcp_integration_service = MCPIntegrationService()
    return _mcp_integration_service

async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convenience function to call an MCP tool."""
    service = get_mcp_integration_service()
    return await service.call_tool(tool_name, arguments)

async def read_mcp_resource(resource_uri: str) -> Optional[Dict[str, Any]]:
    """Convenience function to read an MCP resource."""
    service = get_mcp_integration_service()
    return await service.read_resource(resource_uri)