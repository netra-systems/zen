"""
MCP Routes Module

Modular MCP API endpoints split into focused components under 450-line limit.
Each module handles specific MCP functionality with single responsibility.
"""

from netra_backend.app.routes.mcp.main import router
from netra_backend.app.routes.mcp.models import (
    MCPClientCreateRequest,
    MCPSessionCreateRequest,
    MCPToolCallRequest,
    MCPResourceReadRequest,
    MCPPromptGetRequest
)
from netra_backend.app.services.service_factory import get_mcp_service
from netra_backend.app.routes.mcp.handlers import MCPHandlers, execute_tool

__all__ = [
    "router",
    "MCPClientCreateRequest",
    "MCPSessionCreateRequest", 
    "MCPToolCallRequest",
    "MCPResourceReadRequest",
    "MCPPromptGetRequest",
    "get_mcp_service",
    "MCPHandlers",
    "execute_tool"
]