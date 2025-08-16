"""MCP Integration Package.

This package provides integration between Netra agents and external Model Context Protocol (MCP) servers.
All modules follow strict 300-line and 8-line function limits for modular design.
"""

from .context_manager import MCPContextManager

__all__ = [
    "MCPContextManager"
]