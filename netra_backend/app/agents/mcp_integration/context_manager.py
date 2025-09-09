"""MCP Context Manager for Agent Context and Tool Execution Management.

Provides standardized context management for MCP operations with proper user isolation
and resource management. Follows SSOT principles and 25-line function limits.

Business Value: Enables secure MCP operations with proper user context isolation,
ensuring tool executions are properly scoped and tracked for audit/compliance.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.mcp_client_service import MCPClientService

logger = central_logger.get_logger(__name__)


@dataclass
class MCPAgentContext:
    """Context for MCP agent execution with user isolation."""
    agent_name: str
    user_id: str
    run_id: str
    thread_id: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    active_tools: List[str] = field(default_factory=list)
    tool_results: Dict[str, Any] = field(default_factory=dict)
    
    def add_tool_result(self, tool_name: str, result: Any) -> None:
        """Add tool execution result to context."""
        self.tool_results[tool_name] = result
        if tool_name not in self.active_tools:
            self.active_tools.append(tool_name)
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of context for monitoring."""
        return {
            "agent_name": self.agent_name,
            "user_id": self.user_id,
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "created_at": self.created_at,
            "tools_executed": len(self.active_tools),
            "has_results": bool(self.tool_results)
        }


class MCPContextManager:
    """Manages MCP agent contexts with proper user isolation.
    
    Provides context creation, tool execution, and cleanup for MCP operations.
    Ensures proper user isolation and resource management.
    """
    
    def __init__(self, mcp_service: Optional[MCPClientService] = None):
        self.mcp_service = mcp_service or MCPClientService()
        self.active_contexts: Dict[str, MCPAgentContext] = {}
        self.context_lock = asyncio.Lock()
    
    async def create_agent_context(self, agent_name: str, user_id: str, 
                                 run_id: str, thread_id: str) -> MCPAgentContext:
        """Create new MCP agent context with proper isolation."""
        async with self.context_lock:
            context = MCPAgentContext(
                agent_name=agent_name,
                user_id=user_id,
                run_id=run_id,
                thread_id=thread_id
            )
            self.active_contexts[run_id] = context
            logger.info(f"Created MCP context for {agent_name} (user: {user_id}, run: {run_id})")
            return context
    
    async def get_available_tools(self, context: MCPAgentContext, 
                                server_name: str) -> List[Any]:
        """Get available tools for MCP server with context validation."""
        self._validate_context(context)
        try:
            tools = await self._discover_server_tools(server_name, context)
            logger.debug(f"Discovered {len(tools)} tools for server {server_name}")
            return tools
        except Exception as e:
            return await self._handle_tool_discovery_error(server_name, context, e)
    
    def _validate_context(self, context: MCPAgentContext) -> None:
        """Validate context is active and valid."""
        if context.run_id not in self.active_contexts:
            raise ServiceError(f"Context {context.run_id} not found or expired")
    
    async def _discover_server_tools(self, server_name: str, 
                                   context: MCPAgentContext) -> List[Any]:
        """Discover tools for server using MCP service."""
        if not self.mcp_service:
            raise ServiceError("MCP service not available")
        
        # For now, return mock tools - this would be replaced with actual MCP discovery
        mock_tools = await self._get_mock_tools_for_server(server_name)
        context.metadata[f"tools_{server_name}"] = [tool.name for tool in mock_tools]
        return mock_tools
    
    async def _get_mock_tools_for_server(self, server_name: str) -> List[Any]:
        """Get mock tools for server (placeholder for actual MCP integration)."""
        from types import SimpleNamespace
        
        tool_mappings = {
            "filesystem": ["read_file", "write_file", "list_directory"],
            "web_scraper": ["scrape_url", "extract_links", "get_page_content"],
            "database": ["query_data", "insert_record", "update_record"]
        }
        
        tool_names = tool_mappings.get(server_name, ["generic_tool"])
        return [SimpleNamespace(name=name) for name in tool_names]
    
    async def _handle_tool_discovery_error(self, server_name: str, 
                                         context: MCPAgentContext, 
                                         error: Exception) -> List[Any]:
        """Handle tool discovery error with fallback."""
        logger.error(f"Tool discovery failed for {server_name}: {error}")
        context.metadata[f"discovery_error_{server_name}"] = str(error)
        return []
    
    async def execute_tool_with_context(self, context: MCPAgentContext,
                                      server_name: str, tool_name: str,
                                      arguments: Dict[str, Any]) -> Any:
        """Execute MCP tool with proper context and user isolation."""
        self._validate_context(context)
        self._validate_tool_execution_params(server_name, tool_name)
        
        try:
            result = await self._perform_tool_execution(context, server_name, tool_name, arguments)
            context.add_tool_result(f"{server_name}.{tool_name}", result)
            logger.info(f"Tool {server_name}.{tool_name} executed successfully for {context.run_id}")
            return result
        except Exception as e:
            return await self._handle_tool_execution_error(context, server_name, tool_name, e)
    
    def _validate_tool_execution_params(self, server_name: str, tool_name: str) -> None:
        """Validate tool execution parameters."""
        if not server_name or not tool_name:
            raise ServiceError("Server name and tool name are required")
    
    async def _perform_tool_execution(self, context: MCPAgentContext,
                                    server_name: str, tool_name: str,
                                    arguments: Dict[str, Any]) -> Any:
        """Perform actual tool execution (placeholder for MCP integration)."""
        # Mock execution - this would be replaced with actual MCP tool execution
        execution_result = {
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments,
            "user_id": context.user_id,
            "run_id": context.run_id,
            "result": f"Mock result for {tool_name}",
            "executed_at": datetime.now().isoformat()
        }
        
        # Simulate execution delay
        await asyncio.sleep(0.1)
        return execution_result
    
    async def _handle_tool_execution_error(self, context: MCPAgentContext,
                                         server_name: str, tool_name: str,
                                         error: Exception) -> Any:
        """Handle tool execution error with context preservation."""
        error_message = f"Tool execution failed: {server_name}.{tool_name}: {error}"
        logger.error(error_message)
        context.metadata[f"error_{server_name}_{tool_name}"] = str(error)
        raise ServiceError(error_message)
    
    def cleanup_context(self, run_id: str) -> None:
        """Cleanup MCP context and associated resources."""
        if run_id in self.active_contexts:
            context = self.active_contexts.pop(run_id)
            self._log_context_cleanup(context)
            logger.info(f"Cleaned up MCP context for run {run_id}")
        else:
            logger.warning(f"Attempted to cleanup non-existent context {run_id}")
    
    def _log_context_cleanup(self, context: MCPAgentContext) -> None:
        """Log context cleanup details for audit."""
        summary = context.get_context_summary()
        logger.debug(f"Context cleanup summary: {summary}")
    
    def get_active_contexts_count(self) -> int:
        """Get count of active contexts for monitoring."""
        return len(self.active_contexts)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of context manager."""
        return {
            "active_contexts": self.get_active_contexts_count(),
            "mcp_service_available": self.mcp_service is not None,
            "status": "healthy" if self.mcp_service else "degraded"
        }