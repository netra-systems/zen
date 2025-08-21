"""MCP Integration Package.

This package provides integration between Netra agents and external Model Context Protocol (MCP) servers.
All modules follow strict 450-line and 25-line function limits for modular design.
"""

from netra_backend.app.agents.mcp_integration.context_manager import MCPContextManager
from netra_backend.app.agents.mcp_integration.execution_orchestrator import MCPExecutionOrchestrator
from netra_backend.app.agents.mcp_integration.mcp_intent_detector import MCPIntentDetector
from netra_backend.app.agents.mcp_integration.base_mcp_agent import BaseMCPAgent

__all__ = [
    "MCPContextManager",
    "MCPExecutionOrchestrator", 
    "MCPIntentDetector",
    "BaseMCPAgent"
]