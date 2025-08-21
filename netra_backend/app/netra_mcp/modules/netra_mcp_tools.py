"""Netra MCP Server Tools Registration - Modular Facade

This module provides backward compatibility while using the new modular architecture.
All functionality has been split into focused modules ≤300 lines with functions ≤8 lines.
"""

# Import all modular components for backward compatibility
from netra_backend.app.netra_mcp_tools_main import NetraMCPTools
from netra_backend.app.agent_tools import AgentTools
from netra_backend.app.optimization_tools import OptimizationTools
from netra_backend.app.data_tools import DataTools
from netra_backend.app.thread_tools import ThreadTools
from netra_backend.app.catalog_tools import CatalogTools


# Re-export classes for backward compatibility
__all__ = [
    "NetraMCPTools",
    "AgentTools",
    "OptimizationTools",
    "DataTools",
    "ThreadTools",
    "CatalogTools"
]
