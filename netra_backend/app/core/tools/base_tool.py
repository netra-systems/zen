"""
Base Tool - SSOT Tool Execution Framework

This module provides the base class for all tool implementations in the Netra platform.
It defines the common interface and execution patterns for tools used by agents.

SSOT Compliance: Canonical base class for all tool implementations.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Base class for all tool implementations.
    
    This class defines the standard interface that all tools must implement
    to be compatible with the agent execution framework.
    """
    
    def __init__(self, tool_name: str, description: str = "", **kwargs):
        """Initialize the base tool.
        
        Args:
            tool_name: Unique identifier for this tool
            description: Human-readable description of tool functionality
            **kwargs: Additional tool-specific configuration
        """
        self.tool_name = tool_name
        self.description = description
        self.config = kwargs
        self.logger = logging.getLogger(f"{__name__}.{tool_name}")
        
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the tool with the given input data.
        
        Args:
            input_data: Input parameters for the tool execution
            context: Optional execution context containing user info, session data, etc.
            
        Returns:
            Dict containing the tool execution results
            
        Raises:
            ToolExecutionError: If tool execution fails
        """
        pass
        
    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data before execution.
        
        Args:
            input_data: Input parameters to validate
            
        Returns:
            True if input is valid, False otherwise
        """
        pass
        
    def get_tool_info(self) -> Dict[str, Any]:
        """Get information about this tool.
        
        Returns:
            Dict containing tool metadata
        """
        return {
            "name": self.tool_name,
            "description": self.description,
            "config": self.config,
            "type": self.__class__.__name__
        }
        
    async def pre_execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> None:
        """Pre-execution hook for setup and validation.
        
        Args:
            input_data: Input parameters for the tool execution
            context: Optional execution context
        """
        if not self.validate_input(input_data):
            raise ToolExecutionError(f"Invalid input data for tool {self.tool_name}")
            
    async def post_execute(self, result: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Post-execution hook for result processing.
        
        Args:
            result: Raw tool execution result
            context: Optional execution context
            
        Returns:
            Processed result
        """
        return result
        
    async def execute_with_hooks(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool with pre/post execution hooks.
        
        Args:
            input_data: Input parameters for the tool execution
            context: Optional execution context
            
        Returns:
            Processed tool execution results
        """
        try:
            await self.pre_execute(input_data, context)
            result = await self.execute(input_data, context)
            return await self.post_execute(result, context)
        except Exception as e:
            self.logger.error(f"Tool execution failed for {self.tool_name}: {e}")
            raise ToolExecutionError(f"Tool {self.tool_name} execution failed: {str(e)}")


class ToolExecutionError(Exception):
    """Exception raised when tool execution fails."""
    pass


class MockTool(BaseTool):
    """Mock tool implementation for testing purposes."""
    
    def __init__(self, tool_name: str = "mock_tool", description: str = "Mock tool for testing", **kwargs):
        super().__init__(tool_name, description, **kwargs)
        self.execution_count = 0
        
    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the mock tool."""
        self.execution_count += 1
        return {
            "status": "success",
            "message": f"Mock tool executed successfully (execution #{self.execution_count})",
            "input_received": input_data,
            "context_received": context
        }
        
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Mock validation always passes."""
        return isinstance(input_data, dict)


# Export classes for use by tests and implementations
__all__ = ['BaseTool', 'ToolExecutionError', 'MockTool']