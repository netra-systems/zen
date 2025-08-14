"""Netra MCP Server Core Implementation"""

from fastmcp import FastMCP

from app.logging_config import CentralLogger
from .netra_mcp_tools import NetraMCPTools
from .netra_mcp_resources import NetraMCPResources
from .netra_mcp_prompts import NetraMCPPrompts

logger = CentralLogger()


class NetraMCPServer:
    """
    Main MCP Server for Netra using FastMCP 2
    
    Exposes Netra's optimization capabilities through MCP protocol.
    """
    
    def __init__(self, name: str = "netra-mcp-server", version: str = "1.0.0"):
        """Initialize the Netra MCP server"""
        self.mcp = FastMCP(
            name=name,
            version=version
        )
        
        # Store service references (will be injected)
        self.agent_service = None
        self.thread_service = None
        self.corpus_service = None
        self.synthetic_data_service = None
        self.security_service = None
        self.supply_catalog_service = None
        self.llm_manager = None
        
        # Initialize registration modules
        self.tools = NetraMCPTools(self.mcp)
        self.resources = NetraMCPResources(self.mcp)
        self.prompts = NetraMCPPrompts(self.mcp)
        
        # Register all tools, resources, and prompts
        self._register_components()
        
    def set_services(
        self,
        agent_service=None,
        thread_service=None,
        corpus_service=None,
        synthetic_data_service=None,
        security_service=None,
        supply_catalog_service=None,
        llm_manager=None
    ):
        """Inject service dependencies"""
        if agent_service:
            self.agent_service = agent_service
        if thread_service:
            self.thread_service = thread_service
        if corpus_service:
            self.corpus_service = corpus_service
        if synthetic_data_service:
            self.synthetic_data_service = synthetic_data_service
        if security_service:
            self.security_service = security_service
        if supply_catalog_service:
            self.supply_catalog_service = supply_catalog_service
        if llm_manager:
            self.llm_manager = llm_manager
            
        logger.info("MCP Server services configured")
    
    def _register_components(self):
        """Register all MCP components"""
        # Register tools
        self.tools.register_all(self)
        
        # Register resources
        self.resources.register_all(self)
        
        # Register prompts
        self.prompts.register_all(self)
        
        logger.info("MCP Server components registered")
    
    def get_app(self):
        """Get the FastMCP app instance for running"""
        return self.mcp