"""
MCP Routes Module

Modular MCP API endpoints split into focused components under 450-line limit.
Each module handles specific MCP functionality with single responsibility.
"""

from netra_backend.app.main import router
from netra_backend.app.models import (
    MCPClientCreateRequest,
    MCPSessionCreateRequest,
    MCPToolCallRequest,
    MCPResourceReadRequest,
    MCPPromptGetRequest
)
from netra_backend.app.service_factory import get_mcp_service
from netra_backend.app.handlers import MCPHandlers, execute_tool

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