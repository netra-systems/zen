"""MCP Context Manager for Agent Integration.

Manages MCP server connections, tool discovery, permissions, and context injection for agents.
Follows strict 450-line limit and 25-line function design.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio

from app.mcp_client import MCPTool, MCPConnection
from app.services.mcp_client_service import MCPClientService
from app.schemas.core_enums import MCPServerStatus, MCPToolExecutionStatus, ExecutionStatus
from app.core.exceptions_service import ServiceError
from app.logging_config import central_logger
from app.agents.base import BaseExecutionInterface, ExecutionMonitor, ExecutionErrorHandler
from app.agents.base.interface import ExecutionContext, ExecutionResult

logger = central_logger.get_logger(__name__)


@dataclass
class MCPToolCache:
    """Cached MCP tool information."""
    tools: List[MCPTool] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    ttl_minutes: int = 30


@dataclass
class MCPPermissionContext:
    """Permission context for MCP tool access."""
    agent_name: str
    user_id: str
    allowed_servers: Set[str] = field(default_factory=set)
    allowed_tools: Set[str] = field(default_factory=set)
    restricted_tools: Set[str] = field(default_factory=set)


@dataclass 
class MCPAgentContext:
    """Agent context for MCP operations."""
    run_id: str
    thread_id: str
    agent_name: str
    user_id: str
    permission_context: MCPPermissionContext
    active_tools: Dict[str, str] = field(default_factory=dict)


class MCPToolDiscoveryManager:
    """Manages MCP tool discovery and caching."""
    
    def __init__(self, mcp_service: MCPClientService):
        self.mcp_service = mcp_service
        self.tool_cache: Dict[str, MCPToolCache] = {}
    
    async def discover_tools(self, server_name: str) -> List[MCPTool]:
        """Discover tools from MCP server with caching."""
        if self._is_cache_valid(server_name):
            return self.tool_cache[server_name].tools
        return await self._refresh_tool_cache(server_name)
    
    def _is_cache_valid(self, server_name: str) -> bool:
        """Check if tool cache is still valid."""
        if server_name not in self.tool_cache:
            return False
        cache = self.tool_cache[server_name]
        expiry = cache.last_updated + timedelta(minutes=cache.ttl_minutes)
        return datetime.now() < expiry
    
    async def _refresh_tool_cache(self, server_name: str) -> List[MCPTool]:
        """Refresh tool cache from MCP server."""
        try:
            tools = await self.mcp_service.discover_tools(server_name)
            mcp_tools = [self._dict_to_mcp_tool(tool) for tool in tools]
            self.tool_cache[server_name] = MCPToolCache(tools=mcp_tools, last_updated=datetime.now())
            return mcp_tools
        except Exception as e:
            logger.error(f"Failed to discover tools from {server_name}: {e}")
            return self.tool_cache.get(server_name, MCPToolCache()).tools
    
    def _dict_to_mcp_tool(self, tool_dict: Dict[str, Any]) -> MCPTool:
        """Convert tool dictionary to MCPTool object."""
        return MCPTool(
            name=tool_dict.get("name", ""), description=tool_dict.get("description", ""),
            schema=tool_dict.get("schema", {}), server_name=tool_dict.get("server_name", "")
        )


class MCPConnectionPoolManager:
    """Manages MCP server connection pooling."""
    
    def __init__(self, mcp_service: MCPClientService):
        self.mcp_service = mcp_service
        self.connections: Dict[str, MCPConnection] = {}
        self.connection_locks: Dict[str, asyncio.Lock] = {}
    
    async def get_connection(self, server_name: str) -> Optional[MCPConnection]:
        """Get or create connection to MCP server."""
        if server_name not in self.connection_locks:
            self.connection_locks[server_name] = asyncio.Lock()
        async with self.connection_locks[server_name]:
            return await self._get_or_create_connection(server_name)
    
    async def _get_or_create_connection(self, server_name: str) -> Optional[MCPConnection]:
        """Get existing or create new connection."""
        if (server_name in self.connections and 
            self.connections[server_name].status == MCPServerStatus.CONNECTED):
            return self.connections[server_name]
        return await self._create_new_connection(server_name)
    
    async def _create_new_connection(self, server_name: str) -> Optional[MCPConnection]:
        """Create new connection to MCP server."""
        try:
            connection_data = await self.mcp_service.connect_to_server(server_name)
            connection = MCPConnection(
                server_name=connection_data.get("server_name", ""), status=MCPServerStatus.CONNECTED,
                capabilities=connection_data.get("capabilities", []), metadata=connection_data.get("metadata", {})
            )
            self.connections[server_name] = connection
            return connection
        except Exception as e:
            logger.error(f"Failed to connect to {server_name}: {e}")
            return None


class MCPPermissionChecker:
    """Checks MCP tool execution permissions."""
    
    def __init__(self):
        self.default_permissions = {
            "supervisor": {"*"}, "data_sub_agent": {"data_analysis", "query_tools"},
            "triage_sub_agent": {"diagnostic_tools", "health_check"}
        }
    
    def can_execute_tool(self, context: MCPPermissionContext, 
                        server_name: str, tool_name: str) -> bool:
        """Check if agent can execute specific tool."""
        if tool_name in context.restricted_tools:
            return False
        if context.allowed_servers and server_name not in context.allowed_servers:
            return False
        if "*" in self.default_permissions.get(context.agent_name, set()):
            return True
        agent_tools = self.default_permissions.get(context.agent_name, set())
        return tool_name in agent_tools or tool_name in context.allowed_tools


class MCPContextManager(BaseExecutionInterface):
    """Main MCP context manager for agent integration."""
    
    def __init__(self, mcp_service: Optional[MCPClientService] = None):
        super().__init__("MCP_Context_Manager")
        self.mcp_service = mcp_service or MCPClientService()
        self.tool_discovery = MCPToolDiscoveryManager(self.mcp_service)
        self.connection_pool = MCPConnectionPoolManager(self.mcp_service)
        self.permission_checker = MCPPermissionChecker()
        self.active_contexts: Dict[str, MCPAgentContext] = {}
        self.execution_monitor = ExecutionMonitor()
        self.error_handler = ExecutionErrorHandler()
    
    async def create_agent_context(self, agent_name: str, user_id: str,
                                  run_id: str, thread_id: str) -> MCPAgentContext:
        """Create MCP context for agent execution."""
        permission_context = MCPPermissionContext(agent_name=agent_name, user_id=user_id)
        context = MCPAgentContext(
            run_id=run_id, thread_id=thread_id, agent_name=agent_name,
            user_id=user_id, permission_context=permission_context
        )
        self.active_contexts[run_id] = context
        return context
    
    async def create_agent_context_with_monitoring(self, agent_name: str, user_id: str,
                                                 run_id: str, thread_id: str) -> MCPAgentContext:
        """Create MCP context with execution monitoring enabled."""
        context = await self.create_agent_context(agent_name, user_id, run_id, thread_id)
        exec_context = ExecutionContext(run_id=run_id, agent_name=agent_name, state=None)
        self.execution_monitor.start_execution(exec_context)
        return context
    
    async def get_available_tools(self, context: MCPAgentContext, 
                                 server_name: str) -> List[MCPTool]:
        """Get available tools for agent context."""
        all_tools = await self.tool_discovery.discover_tools(server_name)
        return self._filter_tools_by_permission(context, server_name, all_tools)
    
    def _filter_tools_by_permission(self, context: MCPAgentContext, 
                                   server_name: str, tools: List[MCPTool]) -> List[MCPTool]:
        """Filter tools based on agent permissions."""
        filtered_tools = []
        for tool in tools:
            if self._check_tool_permission(context, server_name, tool):
                filtered_tools.append(tool)
        return filtered_tools
    
    def _check_tool_permission(self, context: MCPAgentContext, 
                              server_name: str, tool: MCPTool) -> bool:
        """Check if tool execution is permitted."""
        return self.permission_checker.can_execute_tool(
            context.permission_context, server_name, tool.name)
    
    async def execute_tool_with_context(self, context: MCPAgentContext,
                                       server_name: str, tool_name: str,
                                       arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP tool with agent context."""
        if not self.permission_checker.can_execute_tool(context.permission_context, server_name, tool_name):
            raise ServiceError(f"Permission denied for tool {tool_name}")
        return await self._execute_tool_safely(context, server_name, tool_name, arguments)
    
    async def _execute_tool_safely(self, context: MCPAgentContext,
                                  server_name: str, tool_name: str,
                                  arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with error handling."""
        try:
            context.active_tools[tool_name] = MCPToolExecutionStatus.RUNNING
            result = await self.mcp_service.execute_tool(server_name, tool_name, arguments)
            context.active_tools[tool_name] = MCPToolExecutionStatus.COMPLETED
            return result
        except Exception as e:
            context.active_tools[tool_name] = MCPToolExecutionStatus.FAILED
            await self._handle_execution_error(e, context)
            raise ServiceError(f"Tool execution failed: {str(e)}")
    
    async def _handle_execution_error(self, error: Exception, context: MCPAgentContext) -> None:
        """Handle tool execution error with structured error handling."""
        exec_context = ExecutionContext(run_id=context.run_id, agent_name=context.agent_name, state=None)
        await self.error_handler.handle_execution_error(error, exec_context)
        self.execution_monitor.record_error(exec_context, error)
    
    def cleanup_context(self, run_id: str) -> None:
        """Cleanup agent context after execution."""
        if run_id in self.active_contexts:
            context = self.active_contexts[run_id]
            exec_context = ExecutionContext(run_id=context.run_id, agent_name=context.agent_name, state=None)
            result = ExecutionResult(success=True, status=ExecutionStatus.COMPLETED)
            self.execution_monitor.complete_execution(exec_context, result)
            del self.active_contexts[run_id]
            logger.debug(f"Cleaned up MCP context for run {run_id}")
    
    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get execution metrics from monitoring."""
        return self.execution_monitor.get_health_status()
    
    async def execute_core_logic(self, context) -> Dict[str, Any]:
        """Execute core MCP logic (required by BaseExecutionInterface)."""
        return {"status": "mcp_context_ready", "context_id": context.run_id}
    
    async def validate_preconditions(self, context) -> bool:
        """Validate MCP execution preconditions."""
        return self.mcp_service is not None