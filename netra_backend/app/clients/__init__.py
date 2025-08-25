"""Client modules for external service communication."""

from netra_backend.app.clients.auth_client_core import AuthServiceClient, auth_client
from netra_backend.app.clients.mcp_client import MCPClient, get_mcp_client, initialize_mcp_client

__all__ = [
    "AuthServiceClient", 
    "auth_client",
    "MCPClient", 
    "get_mcp_client", 
    "initialize_mcp_client"
]