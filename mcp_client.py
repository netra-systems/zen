"""MCP client module - compatibility layer."""

# Re-export from the actual implementation
from netra_backend.app.clients.mcp_client import (
    MCPClient,
    MCPError, 
    MCPConnectionError,
    get_mcp_client,
    initialize_mcp_client
)

from typing import Dict, Any, List, Optional


class MCPTool:
    """MCP tool definition and execution wrapper."""
    
    def __init__(self, name: str, description: str = "", parameters: Optional[Dict[str, Any]] = None):
        """Initialize MCP tool.
        
        Args:
            name: Tool name
            description: Tool description
            parameters: Tool parameters schema
        """
        self.name = name
        self.description = description
        self.parameters = parameters or {}
        
    async def execute(self, client: MCPClient, **kwargs) -> Dict[str, Any]:
        """Execute tool via MCP client.
        
        Args:
            client: MCP client instance
            **kwargs: Tool execution parameters
            
        Returns:
            Tool execution result
        """
        return await client.execute_tool(self.name, kwargs)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


__all__ = [
    "MCPClient",
    "MCPError", 
    "MCPConnectionError",
    "MCPTool",
    "get_mcp_client",
    "initialize_mcp_client"
]