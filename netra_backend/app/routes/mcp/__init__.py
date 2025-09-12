"""
MCP Routes Module

Modular MCP API endpoints split into focused components under 450-line limit.
Each module handles specific MCP functionality with single responsibility.

Provides conditional MCP imports with graceful degradation when dependencies unavailable.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# MCP availability flag
MCP_AVAILABLE = False
MCP_ERROR = None

try:
    # Test core MCP dependencies first
    import fastmcp
    import mcp
    from mcp.types import Tool, TextContent, ImageContent
    
    # If we get here, MCP is available - import MCP components
    from netra_backend.app.routes.mcp.handlers import MCPHandlers, execute_tool
    from netra_backend.app.routes.mcp.main import router
    from netra_backend.app.routes.mcp.models import (
        MCPClientCreateRequest,
        MCPPromptGetRequest,
        MCPResourceReadRequest,
        MCPSessionCreateRequest,
        MCPToolCallRequest,
    )
    from netra_backend.app.routes.mcp.service_factory import get_mcp_service
    
    MCP_AVAILABLE = True
    logger.info(" PASS:  MCP dependencies available - Full MCP integration enabled")
    
except ImportError as e:
    MCP_ERROR = str(e)
    logger.warning(f" WARNING: [U+FE0F] MCP dependencies not available: {e}")
    logger.info(" CYCLE:  Running in MCP-disabled mode - Core functionality preserved")
    
    # Provide fallback exports to prevent import errors
    router = None
    MCPHandlers = None
    execute_tool = None
    MCPClientCreateRequest = None
    MCPPromptGetRequest = None
    MCPResourceReadRequest = None
    MCPSessionCreateRequest = None
    MCPToolCallRequest = None
    get_mcp_service = None

except Exception as e:
    MCP_ERROR = str(e)
    logger.error(f" FAIL:  MCP dependency check failed: {e}")
    logger.info(" CYCLE:  Running in MCP-disabled mode - Core functionality preserved")
    
    # Provide fallback exports to prevent import errors
    router = None
    MCPHandlers = None
    execute_tool = None
    MCPClientCreateRequest = None
    MCPPromptGetRequest = None
    MCPResourceReadRequest = None
    MCPSessionCreateRequest = None
    MCPToolCallRequest = None
    get_mcp_service = None


def is_mcp_available() -> bool:
    """Check if MCP dependencies are available."""
    return MCP_AVAILABLE


def get_mcp_status() -> Dict[str, Any]:
    """Get detailed MCP availability status."""
    return {
        "available": MCP_AVAILABLE,
        "error": MCP_ERROR,
        "fastmcp_available": MCP_AVAILABLE,
        "mcp_types_available": MCP_AVAILABLE,
        "mode": "enabled" if MCP_AVAILABLE else "disabled"
    }

__all__ = [
    "router",
    "MCPClientCreateRequest",
    "MCPSessionCreateRequest", 
    "MCPToolCallRequest",
    "MCPResourceReadRequest",
    "MCPPromptGetRequest",
    "get_mcp_service",
    "MCPHandlers",
    "execute_tool",
    "is_mcp_available",
    "get_mcp_status",
    "MCP_AVAILABLE"
]