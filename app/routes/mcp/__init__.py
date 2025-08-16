"""
MCP Routes Module

Modular MCP API endpoints split into focused components under 300-line limit.
Each module handles specific MCP functionality with single responsibility.
"""

from .main import router
from .models import (
    MCPClientCreateRequest,
    MCPSessionCreateRequest,
    MCPToolCallRequest,
    MCPResourceReadRequest,
    MCPPromptGetRequest
)
from .service_factory import get_mcp_service
from .handlers import MCPHandlers, execute_tool

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