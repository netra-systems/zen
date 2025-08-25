"""Client modules for external service communication."""

from netra_backend.app.clients.auth_client_core import AuthServiceClient as AuthClient
from netra_backend.app.clients.mcp_client import MCPClient, get_mcp_client, initialize_mcp_client

__all__ = [
    "AuthClient", 
    "MCPClient", 
    "get_mcp_client", 
    "initialize_mcp_client"
]