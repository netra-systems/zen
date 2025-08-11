"""
Model Context Protocol (MCP) Server Implementation for Netra AI Platform

This module implements the MCP server that enables integration with AI assistants
like Claude Code, Cursor, Gemini CLI, and other MCP-compatible clients.
"""

from .server import MCPServer
from .handlers.request_handler import RequestHandler
from .tools.tool_registry import ToolRegistry
from .resources.resource_manager import ResourceManager

__version__ = "1.0.0"
__all__ = ["MCPServer", "RequestHandler", "ToolRegistry", "ResourceManager"]