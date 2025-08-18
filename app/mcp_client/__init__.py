"""MCP Client Package - External MCP Server Integration.

This package provides MCP client functionality to connect Netra to external
Model Context Protocol servers, enabling tool discovery, execution, and
resource access from external providers.

Architecture:
- client_core: Main MCPClient class and protocol handling
- models: Pydantic models for type safety  
- connection_manager: Connection pooling and management
- tool_proxy: Tool discovery and execution proxy
- resource_proxy: Resource fetching and caching
- security: Authentication and authorization
- cache: Performance optimization through caching

All modules follow strict 300-line and 8-line function limits.
"""

from .client_core import MCPClient, MCPClientError, MCPConnectionError, MCPProtocolError
from .models import (
    MCPServerConfig,
    MCPConnection,
    MCPTool,
    MCPToolResult,
    MCPResource,
    ConnectionStatus,
    MCPTransport,
    MCPAuthConfig,
    MCPRetryConfig,
)

__all__ = [
    "MCPClient",
    "MCPClientError",
    "MCPConnectionError", 
    "MCPProtocolError",
    "MCPServerConfig", 
    "MCPConnection",
    "MCPTool",
    "MCPToolResult",
    "MCPResource",
    "ConnectionStatus",
    "MCPTransport",
    "MCPAuthConfig",
    "MCPRetryConfig",
]