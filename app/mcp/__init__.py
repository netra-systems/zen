"""
Model Context Protocol (MCP) Server Implementation for Netra AI Platform

This module implements the MCP server using FastMCP 2 that enables integration 
with AI assistants like Claude Desktop, Cursor, Gemini CLI, and other MCP-compatible clients.
"""

from .netra_mcp_server import NetraMCPServer

__version__ = "2.0.0"
__all__ = ["NetraMCPServer"]