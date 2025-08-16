"""MCP Context Manager for Agent Integration.

Manages MCP server connections, tool discovery, permissions, and context injection for agents.
Follows strict 300-line limit and 8-line function design.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio

from app.mcp_client import MCPClient, MCPTool, MCPConnection
from app.services.mcp_client_service import MCPClientService
from app.schemas.core_enums import MCPServerStatus, MCPToolExecutionStatus
from app.core.exceptions_service import ServiceError
from app.logging_config import central_logger

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
        return self._cache_not_expired(cache)
    
    def _cache_not_expired(self, cache: MCPToolCache) -> bool:
        """Check if cache has not expired."""
        expiry = cache.last_updated + timedelta(minutes=cache.ttl_minutes)
        return datetime.now() < expiry
    
    async def _refresh_tool_cache(self, server_name: str) -> List[MCPTool]:
        """Refresh tool cache from MCP server."""
        try:
            tools = await self.mcp_service.discover_tools(server_name)
            self._update_cache(server_name, tools)
            return tools
        except Exception as e:
            logger.error(f"Failed to discover tools from {server_name}: {e}")
            return self._get_fallback_tools(server_name)
    
    def _update_cache(self, server_name: str, tools: List[Dict]) -> None:
        """Update tool cache with new tools."""
        mcp_tools = [self._dict_to_mcp_tool(tool) for tool in tools]
        self.tool_cache[server_name] = MCPToolCache(
            tools=mcp_tools,
            last_updated=datetime.now()
        )
    
    def _dict_to_mcp_tool(self, tool_dict: Dict[str, Any]) -> MCPTool:
        """Convert tool dictionary to MCPTool object."""
        return MCPTool(
            name=tool_dict.get("name", ""),
            description=tool_dict.get("description", ""),
            schema=tool_dict.get("schema", {}),
            server_name=tool_dict.get("server_name", "")
        )
    
    def _get_fallback_tools(self, server_name: str) -> List[MCPTool]:
        """Get cached tools as fallback."""
        if server_name in self.tool_cache:
            return self.tool_cache[server_name].tools
        return []


class MCPConnectionPoolManager:
    """Manages MCP server connection pooling."""
    
    def __init__(self, mcp_service: MCPClientService):
        self.mcp_service = mcp_service
        self.connections: Dict[str, MCPConnection] = {}
        self.connection_locks: Dict[str, asyncio.Lock] = {}
    
    async def get_connection(self, server_name: str) -> Optional[MCPConnection]:
        """Get or create connection to MCP server."""
        async with self._get_connection_lock(server_name):
            return await self._get_or_create_connection(server_name)
    
    def _get_connection_lock(self, server_name: str) -> asyncio.Lock:
        """Get connection lock for server."""
        if server_name not in self.connection_locks:
            self.connection_locks[server_name] = asyncio.Lock()
        return self.connection_locks[server_name]
    
    async def _get_or_create_connection(self, server_name: str) -> Optional[MCPConnection]:
        """Get existing or create new connection."""
        if self._has_active_connection(server_name):
            return self.connections[server_name]
        return await self._create_new_connection(server_name)
    
    def _has_active_connection(self, server_name: str) -> bool:
        """Check if active connection exists."""
        return (server_name in self.connections and 
                self.connections[server_name].status == MCPServerStatus.CONNECTED)
    
    async def _create_new_connection(self, server_name: str) -> Optional[MCPConnection]:
        """Create new connection to MCP server."""
        try:
            connection_data = await self.mcp_service.connect_to_server(server_name)
            connection = self._data_to_connection(connection_data)
            self.connections[server_name] = connection
            return connection
        except Exception as e:
            logger.error(f"Failed to connect to {server_name}: {e}")
            return None
    
    def _data_to_connection(self, data: Dict[str, Any]) -> MCPConnection:
        """Convert connection data to MCPConnection."""
        return MCPConnection(
            server_name=data.get("server_name", ""),
            status=MCPServerStatus.CONNECTED,
            capabilities=data.get("capabilities", []),
            metadata=data.get("metadata", {})
        )


class MCPPermissionChecker:
    """Checks MCP tool execution permissions."""
    
    def __init__(self):
        self.default_permissions = self._load_default_permissions()
    
    def _load_default_permissions(self) -> Dict[str, Set[str]]:
        """Load default permission configuration."""
        return {
            "supervisor": {"*"},  # Supervisor can use all tools
            "data_sub_agent": {"data_analysis", "query_tools"},
            "triage_sub_agent": {"diagnostic_tools", "health_check"}
        }
    
    def can_execute_tool(self, context: MCPPermissionContext, 
                        server_name: str, tool_name: str) -> bool:
        """Check if agent can execute specific tool."""
        if self._is_restricted_tool(context, tool_name):
            return False
        return self._has_tool_permission(context, server_name, tool_name)
    
    def _is_restricted_tool(self, context: MCPPermissionContext, tool_name: str) -> bool:
        """Check if tool is explicitly restricted."""
        return tool_name in context.restricted_tools
    
    def _has_tool_permission(self, context: MCPPermissionContext, 
                           server_name: str, tool_name: str) -> bool:
        """Check if agent has permission for tool."""
        if not self._has_server_access(context, server_name):
            return False
        return self._check_tool_access(context, tool_name)
    
    def _has_server_access(self, context: MCPPermissionContext, server_name: str) -> bool:
        """Check if agent has access to server."""
        if not context.allowed_servers:
            return True  # No restrictions
        return server_name in context.allowed_servers
    
    def _check_tool_access(self, context: MCPPermissionContext, tool_name: str) -> bool:
        """Check tool-level access permissions."""
        if "*" in self.default_permissions.get(context.agent_name, set()):
            return True
        return self._has_explicit_tool_access(context, tool_name)
    
    def _has_explicit_tool_access(self, context: MCPPermissionContext, tool_name: str) -> bool:
        """Check for explicit tool access permission."""
        agent_tools = self.default_permissions.get(context.agent_name, set())
        return tool_name in agent_tools or tool_name in context.allowed_tools


class MCPContextManager:
    """Main MCP context manager for agent integration."""
    
    def __init__(self, mcp_service: Optional[MCPClientService] = None):
        self.mcp_service = mcp_service or MCPClientService()
        self.tool_discovery = MCPToolDiscoveryManager(self.mcp_service)
        self.connection_pool = MCPConnectionPoolManager(self.mcp_service)
        self.permission_checker = MCPPermissionChecker()
        self.active_contexts: Dict[str, MCPAgentContext] = {}
    
    async def create_agent_context(self, agent_name: str, user_id: str,
                                  run_id: str, thread_id: str) -> MCPAgentContext:
        """Create MCP context for agent execution."""
        permission_context = self._create_permission_context(agent_name, user_id)
        context = MCPAgentContext(
            run_id=run_id,
            thread_id=thread_id,
            agent_name=agent_name,
            user_id=user_id,
            permission_context=permission_context
        )
        self.active_contexts[run_id] = context
        return context
    
    def _create_permission_context(self, agent_name: str, user_id: str) -> MCPPermissionContext:
        """Create permission context for agent."""
        return MCPPermissionContext(
            agent_name=agent_name,
            user_id=user_id
        )
    
    async def get_available_tools(self, context: MCPAgentContext, 
                                 server_name: str) -> List[MCPTool]:
        """Get available tools for agent context."""
        all_tools = await self.tool_discovery.discover_tools(server_name)
        return self._filter_tools_by_permission(context, server_name, all_tools)
    
    def _filter_tools_by_permission(self, context: MCPAgentContext, 
                                   server_name: str, tools: List[MCPTool]) -> List[MCPTool]:
        """Filter tools based on agent permissions."""
        return [tool for tool in tools 
                if self.permission_checker.can_execute_tool(
                    context.permission_context, server_name, tool.name)]
    
    async def execute_tool_with_context(self, context: MCPAgentContext,
                                       server_name: str, tool_name: str,
                                       arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP tool with agent context."""
        if not self._validate_tool_execution(context, server_name, tool_name):
            raise ServiceError(f"Permission denied for tool {tool_name}")
        return await self._execute_tool_safely(context, server_name, tool_name, arguments)
    
    def _validate_tool_execution(self, context: MCPAgentContext,
                                server_name: str, tool_name: str) -> bool:
        """Validate tool execution permissions."""
        return self.permission_checker.can_execute_tool(
            context.permission_context, server_name, tool_name)
    
    async def _execute_tool_safely(self, context: MCPAgentContext,
                                  server_name: str, tool_name: str,
                                  arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with error handling."""
        try:
            self._track_tool_execution(context, tool_name)
            return await self.mcp_service.execute_tool(server_name, tool_name, arguments)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            raise ServiceError(f"Tool execution failed: {str(e)}")
    
    def _track_tool_execution(self, context: MCPAgentContext, tool_name: str) -> None:
        """Track active tool execution."""
        context.active_tools[tool_name] = MCPToolExecutionStatus.RUNNING
    
    def cleanup_context(self, run_id: str) -> None:
        """Cleanup agent context after execution."""
        if run_id in self.active_contexts:
            del self.active_contexts[run_id]
            logger.debug(f"Cleaned up MCP context for run {run_id}")