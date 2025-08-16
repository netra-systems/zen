"""
MCP Transport Clients package.
Provides transport implementations for Model Context Protocol communication.
"""

from .base import (
    MCPTransport,
    MCPTransportError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPProtocolError
)

from .stdio_client import (
    StdioTransport,
    StdioTransportError
)

from .http_client import (
    HttpTransport,
    HttpTransportError,
    HttpAuthenticationError
)

from .websocket_client import (
    WebSocketTransport,
    WebSocketTransportError
)

__all__ = [
    # Base classes
    "MCPTransport",
    "MCPTransportError",
    "MCPConnectionError",
    "MCPTimeoutError",
    "MCPProtocolError",
    
    # STDIO Transport
    "StdioTransport",
    "StdioTransportError",
    
    # HTTP Transport
    "HttpTransport",
    "HttpTransportError",
    "HttpAuthenticationError",
    
    # WebSocket Transport
    "WebSocketTransport",
    "WebSocketTransportError",
]