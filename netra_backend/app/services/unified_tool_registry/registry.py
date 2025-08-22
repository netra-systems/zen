"""
Unified Tool Registry Implementation

Provides centralized tool registration and execution management.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from netra_backend.app.services.unified_tool_registry.models import (
    ToolExecutionResult,
    UnifiedTool,
)

logger = logging.getLogger(__name__)


class UnifiedToolRegistry:
    """
    Centralized registry for all platform tools.
    Manages tool registration, permissions, and execution.
    """
    
    def __init__(self, permission_service=None):
        """Initialize the unified tool registry.
        
        Args:
            permission_service: Optional permission service for access control
        """
        self._tools: Dict[str, UnifiedTool] = {}
        self._tool_handlers: Dict[str, Callable] = {}
        self.permission_service = permission_service
        logger.info("UnifiedToolRegistry initialized")
    
    def register_tool(
        self, 
        tool: UnifiedTool,
        handler: Optional[Callable] = None
    ) -> None:
        """
        Register a tool in the unified registry.
        
        Args:
            tool: The tool to register
            handler: Optional execution handler for the tool
        """
        self._tools[tool.id] = tool
        if handler:
            self._tool_handlers[tool.id] = handler
        logger.debug(f"Registered tool: {tool.id}")
    
    def get_tool(self, tool_id: str) -> Optional[UnifiedTool]:
        """
        Get a tool by its ID.
        
        Args:
            tool_id: The tool identifier
            
        Returns:
            The tool if found, None otherwise
        """
        return self._tools.get(tool_id)
    
    def list_tools(self, category: Optional[str] = None) -> List[UnifiedTool]:
        """
        List available tools, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tools matching the criteria
        """
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools
    
    async def execute_tool(
        self,
        tool_id: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolExecutionResult:
        """
        Execute a tool with given parameters.
        
        Args:
            tool_id: The tool to execute
            params: Tool parameters
            context: Optional execution context
            
        Returns:
            Tool execution result
        """
        tool = self.get_tool(tool_id)
        if not tool:
            return ToolExecutionResult(
                success=False,
                error=f"Tool {tool_id} not found"
            )
        
        handler = self._tool_handlers.get(tool_id)
        if not handler:
            return ToolExecutionResult(
                success=False,
                error=f"No handler registered for tool {tool_id}"
            )
        
        try:
            result = await handler(params, context)
            return ToolExecutionResult(
                success=True,
                result=result
            )
        except Exception as e:
            logger.error(f"Error executing tool {tool_id}: {e}")
            return ToolExecutionResult(
                success=False,
                error=str(e)
            )
    
    def check_permission(
        self, 
        tool_id: str, 
        user_id: str,
        action: str = "execute"
    ) -> bool:
        """
        Check if a user has permission to use a tool.
        
        Args:
            tool_id: The tool identifier
            user_id: The user identifier
            action: The action to check (default: "execute")
            
        Returns:
            True if permitted, False otherwise
        """
        tool = self.get_tool(tool_id)
        if not tool:
            return False
        
        # For now, return True for all permissions
        # This should be integrated with the permission system
        return True
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._tool_handlers.clear()
        logger.info("Tool registry cleared")


# Global registry instance
registry = UnifiedToolRegistry()