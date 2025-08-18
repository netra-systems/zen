"""Netra MCP Server Tools Registration - Modular Facade

This module provides backward compatibility while using the new modular architecture.
All functionality has been split into focused modules ≤300 lines with functions ≤8 lines.
"""

# Import all modular components for backward compatibility
from .netra_mcp_tools_main import NetraMCPTools
from .agent_tools import AgentTools
from .optimization_tools import OptimizationTools
from .data_tools import DataTools
from .thread_tools import ThreadTools
from .catalog_tools import CatalogTools


# Re-export classes for backward compatibility
__all__ = [
    "NetraMCPTools",
    "AgentTools",
    "OptimizationTools",
    "DataTools",
    "ThreadTools",
    "CatalogTools"
]
