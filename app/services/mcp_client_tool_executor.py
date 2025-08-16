"""MCP Client Tool Executor.

Handles tool discovery and execution on external MCP servers.
Modular component extracted to maintain 300-line limit compliance.
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime

from app.services.database.mcp_client_repository import MCPToolExecutionRepository
from app.schemas.core_enums import MCPToolExecutionStatus
from app.core.exceptions_service import ServiceError
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MCPToolExecutor:
    """Handles tool discovery and execution for MCP servers."""
    
    def __init__(self):
        self.tool_repo = MCPToolExecutionRepository()
        self.cache: Dict[str, Any] = {}
    
    async def discover_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Discover tools from an MCP server."""
        try:
            cache_key = f"{server_name}:tools"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Mock tool discovery - would call actual MCP server
            tools = await self._mock_tool_discovery(server_name)
            self.cache[cache_key] = tools
            return tools
        except Exception as e:
            logger.error(f"Failed to discover tools from {server_name}: {e}")
            raise ServiceError(f"Tool discovery failed: {str(e)}")
    
    async def _mock_tool_discovery(self, server_name: str) -> List[Dict[str, Any]]:
        """Mock implementation of tool discovery."""
        return [
            {
                "name": "read_file",
                "description": "Read a file from the filesystem",
                "server_name": server_name,
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"]
                }
            },
            {
                "name": "write_file", 
                "description": "Write content to a file",
                "server_name": server_name,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                }
            }
        ]
    
    async def execute_tool(self, db, server_name: str, tool_name: str, 
                          arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on an MCP server."""
        try:
            start_time = datetime.now()
            
            execution = await self.tool_repo.create_execution(
                db, server_name, tool_name, arguments
            )
            
            try:
                result = await self._execute_tool_on_server(
                    server_name, tool_name, arguments
                )
                
                execution_time_ms = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )
                
                await self.tool_repo.update_execution_result(
                    db, execution.id, result, MCPToolExecutionStatus.COMPLETED,
                    execution_time_ms
                )
                
                return {
                    "tool_name": tool_name,
                    "server_name": server_name,
                    "content": result,
                    "is_error": False,
                    "execution_time_ms": execution_time_ms
                }
                
            except Exception as tool_error:
                await self.tool_repo.update_execution_result(
                    db, execution.id, {}, MCPToolExecutionStatus.FAILED,
                    error_message=str(tool_error)
                )
                raise
                
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name} on {server_name}: {e}")
            raise ServiceError(f"Tool execution failed: {str(e)}")
    
    async def _execute_tool_on_server(self, server_name: str, tool_name: str,
                                    arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute tool on actual MCP server."""
        # Mock implementation - would call actual MCP server
        await asyncio.sleep(0.1)  # Simulate network delay
        return [{"type": "text", "text": f"Mock result for {tool_name}"}]
    
    def clear_tool_cache(self, server_name: str = None):
        """Clear tool cache for specific server or all."""
        if server_name:
            keys_to_remove = [k for k in self.cache.keys() 
                            if k.startswith(f"{server_name}:tools")]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            self.cache.clear()