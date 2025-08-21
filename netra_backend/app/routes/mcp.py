"""
MCP API Routes - Legacy Compatibility Module

This module maintains backward compatibility while delegating to the new
modular MCP package. All functionality has been moved to focused
modules under 300 lines each.
"""

# Import from modular implementation  
from netra_backend.app.mcp.main import router
from netra_backend.app.mcp.models import (
    MCPClientCreateRequest,
    MCPSessionCreateRequest,
    MCPToolCallRequest,
    MCPResourceReadRequest,
    MCPPromptGetRequest
)
from netra_backend.app.mcp.service_factory import get_mcp_service

# Maintain backward compatibility
__all__ = [
    "router",
    "MCPClientCreateRequest",
    "MCPSessionCreateRequest",
    "MCPToolCallRequest", 
    "MCPResourceReadRequest",
    "MCPPromptGetRequest",
    "get_mcp_service"
]