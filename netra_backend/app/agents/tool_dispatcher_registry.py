"""Tool registration and management for the dispatcher."""
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool
from netra_backend.app.schemas.Tool import ToolRegistryInterface
from netra_backend.app.agents.production_tool import ProductionTool
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class ToolRegistry(ToolRegistryInterface):
    """Manages tool registration and retrieval"""
    
    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register default synthetic and corpus tools"""
        self._register_synthetic_tools()
        self._register_corpus_tools()
    
    def _register_synthetic_tools(self) -> None:
        """Register synthetic data generation tools"""
        synthetic_tools = self._get_synthetic_tool_names()
        self._register_tool_batch(synthetic_tools)
    
    def _get_synthetic_tool_names(self) -> List[str]:
        """Get list of synthetic tool names"""
        return [
            "generate_synthetic_data_batch",
            "validate_synthetic_data", 
            "store_synthetic_data"
        ]
    
    def _register_corpus_tools(self) -> None:
        """Register corpus management tools"""
        corpus_tools = self._get_corpus_tool_names()
        self._register_tool_batch(corpus_tools)
    
    def _get_corpus_tool_names(self) -> List[str]:
        """Get list of corpus tool names"""
        return [
            "create_corpus", "search_corpus", "update_corpus", "delete_corpus",
            "analyze_corpus", "export_corpus", "import_corpus", "validate_corpus"
        ]
    
    def _register_tool_batch(self, tool_names: List[str]) -> None:
        """Register batch of tools if not already present"""
        for tool_name in tool_names:
            if tool_name not in self.tools:
                self.tools[tool_name] = ProductionTool(tool_name)
    
    def register_tools(self, tools: List[BaseTool]) -> None:
        """Register list of tools"""
        for tool in tools:
            self.register_tool(tool)
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a single tool"""
        self.tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool exists"""
        return tool_name in self.tools
    
    def get_tool(self, tool_name: str) -> Optional[Any]:
        """Get a tool by name"""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self.tools.keys())
    
    def remove_tool(self, tool_name: str) -> bool:
        """Remove a tool from registry"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            return True
        return False
    
    def clear_tools(self) -> None:
        """Clear all tools from registry"""
        self.tools.clear()
        self._register_default_tools()
    
    def get_tool_count(self) -> int:
        """Get total number of registered tools"""
        return len(self.tools)