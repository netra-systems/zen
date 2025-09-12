"""Netra MCP Server Tools Registration - Modular Facade

This module provides backward compatibility while using the new modular architecture.
All functionality has been split into focused modules  <= 300 lines with functions  <= 8 lines.
"""

# Import all modular components for backward compatibility
from netra_backend.app.netra_mcp.modules.agent_tools import AgentTools
from netra_backend.app.netra_mcp.modules.catalog_tools import CatalogTools
from netra_backend.app.netra_mcp.modules.data_tools import DataTools
from netra_backend.app.netra_mcp.modules.netra_mcp_tools_main import NetraMCPTools
from netra_backend.app.netra_mcp.modules.optimization_tools import OptimizationTools
from netra_backend.app.netra_mcp.modules.thread_tools import ThreadTools

# Re-export classes for backward compatibility
__all__ = [
    "NetraMCPTools",
    "AgentTools",
    "OptimizationTools",
    "DataTools",
    "ThreadTools",
    "CatalogTools"
]
