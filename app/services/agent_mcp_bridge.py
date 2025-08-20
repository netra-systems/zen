"""Agent-MCP Bridge Service.

Bridges Netra agents with MCP client functionality, providing tool discovery,
execution, and result transformation. Follows strict 25-line function design.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import asyncio

from app.services.mcp_client_service import MCPClientService
from app.mcp_client import MCPTool, MCPToolResult
from app.agents.mcp_integration.context_manager import MCPAgentContext
from app.core.exceptions_service import ServiceError
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class AgentToolExecutionResult:
    """Result of agent tool execution."""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MCPToolDiscoveryService:
    """Handles tool discovery for agents."""
    
    def __init__(self, mcp_service: MCPClientService):
        self.mcp_service = mcp_service
        self.discovery_cache: Dict[str, List[MCPTool]] = {}
    
    async def discover_tools_for_agent(self, context: MCPAgentContext,
                                      server_name: str) -> List[MCPTool]:
        """Discover available tools for specific agent context."""
        cache_key = f"{server_name}:{context.agent_name}"
        
        if cache_key in self.discovery_cache:
            return self.discovery_cache[cache_key]
        
        return await self._refresh_agent_tool_cache(context, server_name, cache_key)
    
    async def _refresh_agent_tool_cache(self, context: MCPAgentContext,
                                       server_name: str, cache_key: str) -> List[MCPTool]:
        """Refresh tool cache for agent."""
        try:
            all_tools = await self.mcp_service.discover_tools(server_name)
            agent_tools = self._filter_tools_for_agent(context, all_tools)
            return self._cache_and_return_tools(cache_key, agent_tools)
        except Exception as e:
            return self._handle_discovery_error(server_name, e)
    
    def _cache_and_return_tools(self, cache_key: str, agent_tools: List[MCPTool]) -> List[MCPTool]:
        """Cache and return agent tools."""
        self.discovery_cache[cache_key] = agent_tools
        return agent_tools
    
    def _handle_discovery_error(self, server_name: str, error: Exception) -> List[MCPTool]:
        """Handle tool discovery error."""
        logger.error(f"Tool discovery failed for {server_name}: {error}")
        return []
    
    def _filter_tools_for_agent(self, context: MCPAgentContext,
                               tools: List[Dict[str, Any]]) -> List[MCPTool]:
        """Filter tools based on agent permissions."""
        return [self._dict_to_mcp_tool(tool) for tool in tools
                if self._agent_can_use_tool(context, tool)]
    
    def _agent_can_use_tool(self, context: MCPAgentContext, tool: Dict[str, Any]) -> bool:
        """Check if agent can use specific tool."""
        tool_name = tool.get("name", "")
        restricted = context.permission_context.restricted_tools
        allowed = context.permission_context.allowed_tools
        
        if tool_name in restricted:
            return False
        return not allowed or tool_name in allowed
    
    def _dict_to_mcp_tool(self, tool_dict: Dict[str, Any]) -> MCPTool:
        """Convert tool dictionary to MCPTool object."""
        return MCPTool(
            name=tool_dict.get("name", ""),
            description=tool_dict.get("description", ""),
            schema=tool_dict.get("schema", {}),
            server_name=tool_dict.get("server_name", "")
        )


class MCPToolExecutor:
    """Executes MCP tools on behalf of agents."""
    
    def __init__(self, mcp_service: MCPClientService):
        self.mcp_service = mcp_service
    
    async def execute_tool_for_agent(self, context: MCPAgentContext,
                                    server_name: str, tool_name: str,
                                    arguments: Dict[str, Any]) -> AgentToolExecutionResult:
        """Execute MCP tool with agent context."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            self._validate_tool_execution(context, server_name, tool_name)
            result = await self._execute_mcp_tool(server_name, tool_name, arguments)
            return self._create_success_result(result, start_time)
        except Exception as e:
            return self._create_error_result(e, start_time)
    
    def _validate_tool_execution(self, context: MCPAgentContext,
                                server_name: str, tool_name: str) -> None:
        """Validate agent can execute tool."""
        if not self._has_server_access(context, server_name):
            raise ServiceError(f"Agent {context.agent_name} cannot access server {server_name}")
        
        if not self._has_tool_access(context, tool_name):
            raise ServiceError(f"Agent {context.agent_name} cannot use tool {tool_name}")
    
    def _has_server_access(self, context: MCPAgentContext, server_name: str) -> bool:
        """Check if agent has access to server."""
        allowed_servers = context.permission_context.allowed_servers
        return not allowed_servers or server_name in allowed_servers
    
    def _has_tool_access(self, context: MCPAgentContext, tool_name: str) -> bool:
        """Check if agent has access to tool."""
        perm_ctx = context.permission_context
        return (tool_name not in perm_ctx.restricted_tools and
                (not perm_ctx.allowed_tools or tool_name in perm_ctx.allowed_tools))
    
    async def _execute_mcp_tool(self, server_name: str, tool_name: str,
                               arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP tool via service."""
        return await self.mcp_service.execute_tool(server_name, tool_name, arguments)
    
    def _create_success_result(self, result: Dict[str, Any], start_time: float) -> AgentToolExecutionResult:
        """Create successful execution result."""
        execution_time = asyncio.get_event_loop().time() - start_time
        return AgentToolExecutionResult(
            success=True,
            result=result,
            execution_time=execution_time,
            metadata={"execution_type": "mcp_tool"}
        )
    
    def _create_error_result(self, error: Exception, start_time: float) -> AgentToolExecutionResult:
        """Create error execution result."""
        execution_time = asyncio.get_event_loop().time() - start_time
        return AgentToolExecutionResult(
            success=False,
            error=str(error),
            execution_time=execution_time,
            metadata={"execution_type": "mcp_tool_failed"}
        )


class MCPResultTransformer:
    """Transforms MCP results for agent consumption."""
    
    def __init__(self):
        self.transformation_rules = self._load_transformation_rules()
    
    def _load_transformation_rules(self) -> Dict[str, callable]:
        """Load result transformation rules."""
        return {
            "file_read": self._transform_file_content,
            "web_fetch": self._transform_web_content,
            "database_query": self._transform_query_result,
            "system_command": self._transform_command_output
        }
    
    def transform_result(self, tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Transform MCP result for agent consumption."""
        transformer = self._get_transformer(tool_name)
        if transformer:
            return transformer(result)
        return self._default_transform(result)
    
    def _get_transformer(self, tool_name: str) -> Optional[callable]:
        """Get transformer function for tool."""
        for rule_pattern, transformer in self.transformation_rules.items():
            if rule_pattern in tool_name.lower():
                return transformer
        return None
    
    def _default_transform(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Default result transformation."""
        return {
            "status": "success",
            "data": result,
            "type": "mcp_result",
            "formatted": str(result)
        }
    
    def _transform_file_content(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Transform file content result."""
        return {
            "status": "success",
            "content": result.get("content", ""),
            "file_path": result.get("path", ""),
            "type": "file_content"
        }
    
    def _transform_web_content(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Transform web content result."""
        return {
            "status": "success",
            "content": result.get("html", ""),
            "url": result.get("url", ""),
            "type": "web_content"
        }
    
    def _transform_query_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Transform database query result."""
        return {
            "status": "success",
            "rows": result.get("rows", []),
            "columns": result.get("columns", []),
            "type": "query_result"
        }
    
    def _transform_command_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Transform system command output."""
        return {
            "status": "success",
            "output": result.get("stdout", ""),
            "error": result.get("stderr", ""),
            "exit_code": result.get("exit_code", 0),
            "type": "command_output"
        }


class AgentMCPBridge:
    """Main bridge service between agents and MCP clients."""
    
    def __init__(self, mcp_service: Optional[MCPClientService] = None):
        self.mcp_service = mcp_service or MCPClientService()
        self.tool_discovery = MCPToolDiscoveryService(self.mcp_service)
        self.tool_executor = MCPToolExecutor(self.mcp_service)
        self.result_transformer = MCPResultTransformer()
    
    async def discover_tools(self, context: MCPAgentContext,
                            server_name: str) -> List[MCPTool]:
        """Discover available tools for agent."""
        return await self.tool_discovery.discover_tools_for_agent(context, server_name)
    
    async def execute_tool_for_agent(self, context: MCPAgentContext,
                                    server_name: str, tool_name: str,
                                    arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP tool and return transformed result."""
        execution_result = await self.tool_executor.execute_tool_for_agent(
            context, server_name, tool_name, arguments)
        
        if execution_result.success:
            return self.result_transformer.transform_result(tool_name, execution_result.result)
        return self._create_error_response(execution_result)
    
    def _create_error_response(self, execution_result: AgentToolExecutionResult) -> Dict[str, Any]:
        """Create error response for failed execution."""
        return {
            "status": "error",
            "error": execution_result.error,
            "type": "mcp_execution_error",
            "execution_time": execution_result.execution_time
        }
    
    async def get_server_capabilities(self, server_name: str) -> Dict[str, Any]:
        """Get capabilities of MCP server."""
        try:
            servers = await self.mcp_service.list_servers()
            server_info = next((s for s in servers if s["name"] == server_name), None)
            return server_info.get("capabilities", {}) if server_info else {}
        except Exception as e:
            logger.error(f"Failed to get server capabilities: {e}")
            return {}
    
    async def health_check(self, server_name: str) -> bool:
        """Check health of MCP server connection."""
        try:
            await self.mcp_service.discover_tools(server_name)
            return True
        except Exception:
            return False