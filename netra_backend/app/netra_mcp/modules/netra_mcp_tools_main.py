"""Main Netra MCP Tools - Orchestrates all tool registration functionality"""

from netra_backend.app.agent_tools import AgentTools
from netra_backend.app.optimization_tools import OptimizationTools
from netra_backend.app.data_tools import DataTools
from netra_backend.app.thread_tools import ThreadTools
from netra_backend.app.catalog_tools import CatalogTools


class NetraMCPTools:
    """Tool registration for Netra MCP Server - orchestrates all tool modules"""
    
    def __init__(self, mcp_instance):
        self.mcp = mcp_instance
        self._initialize_tool_modules()
        
    def _initialize_tool_modules(self) -> None:
        """Initialize all tool modules"""
        self.agent_tools = AgentTools(self.mcp)
        self.optimization_tools = OptimizationTools(self.mcp)
        self.data_tools = DataTools(self.mcp)
        self.thread_tools = ThreadTools(self.mcp)
        self.catalog_tools = CatalogTools(self.mcp)
        
    def register_all(self, server):
        """Register all tools with the MCP server"""
        self.agent_tools.register_all(server)
        self.optimization_tools.register_all(server)
        self.data_tools.register_all(server)
        self.thread_tools.register_all(server)
        self.catalog_tools.register_all(server)