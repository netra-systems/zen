"""
UnifiedToolRegistry - A comprehensive tool registry implementation

This module provides a unified tool registry that implements all expected
tool management methods while leveraging the UniversalRegistry SSOT pattern.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
import logging
from datetime import datetime, timezone

from netra_backend.app.core.registry.universal_registry import ToolRegistry
from netra_backend.app.services.unified_tool_registry.models import (
    UnifiedTool, 
    ToolExecutionResult
)
from netra_backend.app.core.exceptions_tools import (
    ToolTypeValidationException,
    ToolNameValidationException,
    ToolHandlerValidationException,
    ToolNotFoundException,
    ToolExecutionException,
    ToolPermissionException
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class UnifiedToolRegistry(ToolRegistry):
    """
    Comprehensive tool registry that extends ToolRegistry with tool-specific operations.
    
    This class provides:
    - Tool registration and retrieval by ID
    - Category-based tool organization and filtering
    - Tool execution with handlers
    - Permission checking
    - Tool handler management
    - Category descriptions and metadata
    
    Business Value:
    - Centralized tool management across the platform
    - Type-safe tool operations with Pydantic models
    - Execution isolation with proper error handling
    - Business-friendly categorization and discovery
    """
    
    def __init__(self):
        super().__init__()
        
        # Additional storage for tool-specific functionality
        self._tools: Dict[str, UnifiedTool] = {}
        self._tool_handlers: Dict[str, Callable] = {}
        
        # Category metadata for business-friendly descriptions
        self._category_descriptions = {
            "analysis": "Analysis tools for data insights and metrics",
            "optimization": "Optimization tools for cost and performance improvements",
            "monitoring": "Monitoring and alerting tools",
            "reporting": "Reporting and visualization tools",
            "data_management": "Data collection and management tools",
            "system": "System administration and configuration tools",
            "testing": "Testing and validation tools",
            "default": "Miscellaneous tools"
        }
        
        logger.info("UnifiedToolRegistry initialized")
    
    def register_tool(self, tool: UnifiedTool, handler: Optional[Callable] = None) -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool: UnifiedTool instance to register
            handler: Optional async execution handler for the tool
            
        Raises:
            ToolTypeValidationException: If tool is not a UnifiedTool instance
            ToolNameValidationException: If tool name is invalid
            ToolHandlerValidationException: If handler is not callable
        """
        # Validate tool type
        if not isinstance(tool, UnifiedTool):
            raise ToolTypeValidationException(
                message=f"Invalid tool type: {type(tool).__name__}",
                tool_id=getattr(tool, 'id', None),
                tool_name=getattr(tool, 'name', None),
                expected_type="UnifiedTool",
                actual_type=type(tool).__name__
            )
        
        # Validate tool name
        if not tool.name or not tool.name.strip():
            raise ToolNameValidationException(
                message="Tool name cannot be empty",
                tool_id=tool.id,
                tool_name=tool.name,
                invalid_name=tool.name,
                validation_rule="non_empty_name"
            )
        
        # Store in both our local storage and parent registry
        try:
            self._tools[tool.id] = tool
            super().register(tool.id, tool)
        except Exception as e:
            raise ToolTypeValidationException(
                message=f"Failed to register tool in parent registry: {str(e)}",
                tool_id=tool.id,
                tool_name=tool.name,
                details={'parent_error': str(e)}
            )
        
        # Validate and store handler if provided
        if handler is not None:
            if not callable(handler):
                raise ToolHandlerValidationException(
                    message="Tool handler must be callable",
                    tool_id=tool.id,
                    tool_name=tool.name,
                    handler_type=type(handler).__name__,
                    validation_issue="not_callable"
                )
            self._tool_handlers[tool.id] = handler
        
        logger.debug(f"Registered tool {tool.id} with handler: {handler is not None}")
    
    def get_tool(self, tool_id: str) -> Optional[UnifiedTool]:
        """
        Get a tool by ID.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            UnifiedTool instance or None if not found
        """
        return self._tools.get(tool_id)
    
    def list_tools(self, category: Optional[str] = None) -> List[UnifiedTool]:
        """
        List all tools, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of UnifiedTool instances
        """
        tools = list(self._tools.values())
        
        if category is not None:
            tools = [tool for tool in tools if tool.category == category]
        
        # Sort by name for consistent ordering
        return sorted(tools, key=lambda t: t.name)
    
    def get_tool_categories(self) -> List[Dict[str, Any]]:
        """
        Get all tool categories with counts and descriptions.
        
        Returns:
            List of category dictionaries with name, count, and description
        """
        if not self._tools:
            return []
        
        # Count tools per category
        category_counts: Dict[str, int] = {}
        for tool in self._tools.values():
            category = getattr(tool, 'category', 'default')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Build category list with descriptions
        categories = []
        for category_name, count in category_counts.items():
            description = self._category_descriptions.get(
                category_name, 
                f"{category_name.title()} tools"
            )
            
            categories.append({
                "name": category_name,
                "count": count,
                "description": description
            })
        
        # Sort by name for consistent ordering
        return sorted(categories, key=lambda c: c["name"])
    
    async def execute_tool(self, 
                          tool_id: str, 
                          parameters: Dict[str, Any],
                          context: Dict[str, Any]) -> ToolExecutionResult:
        """
        Execute a tool with the given parameters and context.
        
        Args:
            tool_id: Tool identifier
            parameters: Tool execution parameters
            context: Execution context (user, request info, etc.)
            
        Returns:
            ToolExecutionResult with success status, result, or error
        """
        start_time = datetime.now(timezone.utc)
        
        # Check if tool exists
        tool = self.get_tool(tool_id)
        if not tool:
            # Could raise ToolNotFoundException in strict mode, but for now return result
            return ToolExecutionResult(
                success=False,
                error=f"Tool {tool_id} not found",
                tool_name=tool_id,
                execution_time_ms=0
            )
        
        # Check if handler exists
        handler = self._tool_handlers.get(tool_id)
        if not handler:
            return ToolExecutionResult(
                success=False,
                error=f"No handler registered for tool {tool_id}",
                tool_name=tool.name,
                execution_time_ms=0
            )
        
        # Execute the tool with enhanced exception handling
        try:
            result = await handler(parameters, context)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return ToolExecutionResult(
                success=True,
                result=result,
                tool_name=tool.name,
                user_id=context.get("user"),
                status="success",
                execution_time_ms=int(execution_time)
            )
            
        except ToolExecutionException as e:
            # Re-raise specific tool exceptions for proper handling
            raise e
            
        except PermissionError as e:
            # Convert permission errors to specific exceptions
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            raise ToolPermissionException(
                message=f"Permission denied executing tool {tool_id}",
                tool_id=tool_id,
                tool_name=tool.name,
                user_id=context.get("user"),
                details={
                    'original_error': str(e),
                    'execution_time': execution_time
                }
            )
            
        except TimeoutError as e:
            # Convert timeout errors to execution exceptions
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            raise ToolExecutionException(
                message=f"Tool execution timed out for {tool_id}",
                tool_id=tool_id,
                tool_name=tool.name,
                user_id=context.get("user"),
                execution_error="timeout",
                execution_time=execution_time,
                input_args=parameters
            )
            
        except ValueError as e:
            # Convert validation errors to execution exceptions
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            raise ToolExecutionException(
                message=f"Invalid parameters for tool {tool_id}: {str(e)}",
                tool_id=tool_id,
                tool_name=tool.name,
                user_id=context.get("user"),
                execution_error="invalid_parameters",
                execution_time=execution_time,
                input_args=parameters
            )
            
        except Exception as e:
            # Convert all other exceptions to ToolExecutionException
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.error(f"Tool execution failed for {tool_id}: {str(e)}")
            
            raise ToolExecutionException(
                message=f"Tool execution failed for {tool_id}: {str(e)}",
                tool_id=tool_id,
                tool_name=tool.name,
                user_id=context.get("user"),
                execution_error=str(e),
                execution_time=execution_time,
                input_args=parameters,
                details={
                    'exception_type': type(e).__name__,
                    'original_error': str(e)
                }
            )
    
    def check_permission(self, 
                        tool_id: str, 
                        user_id: str, 
                        action: str = "execute") -> bool:
        """
        Check if user has permission to perform action on tool.
        
        Args:
            tool_id: Tool identifier
            user_id: User identifier
            action: Action to check permission for (e.g., "execute")
            
        Returns:
            True if permission granted, False otherwise
            
        Raises:
            ToolNotFoundException: If tool doesn't exist (in strict mode)
        """
        # Check if tool exists
        tool = self.get_tool(tool_id)
        if not tool:
            # For compatibility, return False instead of raising exception
            # In strict mode, we could raise ToolNotFoundException
            return False
        
        # For now, always return True for existing tools
        # This can be extended with actual permission logic later
        return True
    
    def check_permission_strict(self, 
                               tool_id: str, 
                               user_id: str, 
                               action: str = "execute") -> bool:
        """
        Check if user has permission to perform action on tool (strict mode).
        
        Args:
            tool_id: Tool identifier
            user_id: User identifier
            action: Action to check permission for (e.g., "execute")
            
        Returns:
            True if permission granted
            
        Raises:
            ToolNotFoundException: If tool doesn't exist
            ToolPermissionException: If permission is denied
        """
        # Check if tool exists
        tool = self.get_tool(tool_id)
        if not tool:
            raise ToolNotFoundException(
                message=f"Tool {tool_id} not found",
                tool_id=tool_id,
                user_id=user_id,
                registry_name=self.name
            )
        
        # For now, always grant permission for existing tools
        # This can be extended with actual permission logic later
        # Example permission check that would raise exception:
        # if some_permission_check_fails:
        #     raise ToolPermissionException(
        #         message=f"User {user_id} lacks permission to {action} tool {tool_id}",
        #         tool_id=tool_id,
        #         tool_name=tool.name,
        #         user_id=user_id,
        #         required_permission=action
        #     )
        
        return True
    
    def clear(self) -> None:
        """Clear all tools from the registry."""
        self._tools.clear()
        self._tool_handlers.clear()
        super().clear()
        logger.info("UnifiedToolRegistry cleared")
    
    # Additional utility methods
    
    def has_tool(self, tool_id: str) -> bool:
        """Check if a tool is registered."""
        return tool_id in self._tools
    
    def get_tool_handler(self, tool_id: str) -> Optional[Callable]:
        """Get the execution handler for a tool."""
        return self._tool_handlers.get(tool_id)
    
    def remove_tool(self, tool_id: str) -> bool:
        """
        Remove a tool from the registry.
        
        Args:
            tool_id: Tool identifier to remove
            
        Returns:
            True if removed, False if not found
        """
        if tool_id not in self._tools:
            return False
        
        del self._tools[tool_id]
        self._tool_handlers.pop(tool_id, None)
        super().remove(tool_id)
        
        logger.debug(f"Removed tool {tool_id}")
        return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get registry metrics including tool-specific data."""
        base_metrics = super().get_metrics()
        
        # Add tool-specific metrics
        tool_metrics = {
            "total_tools": len(self._tools),
            "tools_with_handlers": len(self._tool_handlers),
            "categories": len(set(tool.category for tool in self._tools.values())),
            "tools_by_category": {}
        }
        
        # Count tools per category
        for tool in self._tools.values():
            category = tool.category
            tool_metrics["tools_by_category"][category] = (
                tool_metrics["tools_by_category"].get(category, 0) + 1
            )
        
        # Merge metrics
        base_metrics.update(tool_metrics)
        return base_metrics