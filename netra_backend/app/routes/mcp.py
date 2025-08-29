"""
MCP API Routes - Compatibility Module

This module provides MCP client functionality through the existing
mcp_client router implementation.
"""

# Import from working implementation  
from netra_backend.app.routes.mcp_client import router
from netra_backend.app.schemas.mcp_client import (
    ExecuteToolRequest as MCPToolCallRequest,
    FetchResourceRequest as MCPResourceReadRequest,
    ConnectServerRequest as MCPSessionCreateRequest,
    RegisterServerRequest as MCPClientCreateRequest,
)

# For backward compatibility, create a simple service getter
def get_mcp_service():
    """Get MCP service - delegates to service locator in mcp_client routes."""
    from netra_backend.app.services.service_locator import get_service
    from netra_backend.app.services.service_interfaces import IMCPClientService
    return get_service(IMCPClientService)

# Maintain backward compatibility
__all__ = [
    "router",
    "MCPClientCreateRequest",
    "MCPSessionCreateRequest",
    "MCPToolCallRequest", 
    "MCPResourceReadRequest",
    "get_mcp_service"
]