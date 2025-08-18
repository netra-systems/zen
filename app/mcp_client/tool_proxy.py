"""
MCP Tool Proxy Module

Proxies tool execution to external MCP servers.
Compliant with 300-line limit and 8-line function requirements.
"""

import json
import hashlib
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.core.exceptions import NetraException, ErrorCode, ErrorSeverity
from app.core.async_retry_logic import _retry_with_backoff
from app.mcp_client.models import MCPTool, MCPToolResult, MCPConnection


class MCPToolProxy:
    """Proxy for executing tools on external MCP servers."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self._tool_cache: Dict[str, List[MCPTool]] = {}
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
    
    async def discover_tools(self, connection: MCPConnection) -> List[MCPTool]:
        """Discover available tools from MCP server."""
        cache_key = f"{connection.server_name}:tools"
        if cache_key in self._tool_cache:
            return self._tool_cache[cache_key]
        
        return await self._discover_and_cache_tools(connection, cache_key)
    
    async def execute_tool(self, connection: MCPConnection, tool_name: str, 
                          arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute tool on external MCP server with retry logic."""
        start_time = datetime.now()
        try:
            return await self._execute_tool_safely(connection, tool_name, arguments, start_time)
        except Exception as e:
            return self._create_error_result(tool_name, connection.server_name, e, start_time)
    
    def validate_arguments(self, tool: MCPTool, arguments: Dict[str, Any]) -> bool:
        """Validate tool arguments against schema."""
        try:
            self._validate_required_fields(tool.input_schema, arguments)
            self._validate_field_types(tool.input_schema, arguments)
            return True
        except Exception:
            return False
    
    def transform_result(self, raw_result: Dict[str, Any]) -> MCPToolResult:
        """Transform raw server response to structured result."""
        return self._build_tool_result_from_raw(raw_result)

    def _build_tool_result_from_raw(self, raw_result: Dict[str, Any]) -> MCPToolResult:
        """Build MCPToolResult from raw response data."""
        result_data = self._extract_result_data(raw_result)
        return MCPToolResult(**result_data)
    
    def _extract_result_data(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract result data from raw response."""
        return {
            "tool_name": raw_result.get("tool_name", "unknown"),
            "server_name": raw_result.get("server_name", "unknown"),
            "content": self._extract_content(raw_result),
            "is_error": raw_result.get("isError", False),
            "error_message": raw_result.get("error"),
            "execution_time_ms": raw_result.get("execution_time_ms", 0)
        }
    
    async def _discover_and_cache_tools(self, connection: MCPConnection, cache_key: str) -> List[MCPTool]:
        """Discover tools and cache them."""
        tools = await self._fetch_tools_from_server(connection)
        self._tool_cache[cache_key] = tools
        return tools
    
    async def _execute_tool_safely(self, connection: MCPConnection, tool_name: str, 
                                  arguments: Dict[str, Any], start_time: datetime) -> MCPToolResult:
        """Execute tool with validation and retry."""
        tool = await self._get_tool_definition(connection, tool_name)
        self._validate_tool_arguments(tool, arguments)
        result = await self._execute_with_retry(connection, tool_name, arguments)
        return self._create_success_result(tool_name, connection.server_name, result, start_time)
    
    async def _fetch_tools_from_server(self, connection: MCPConnection) -> List[MCPTool]:
        """Fetch tool list from MCP server."""
        request = self._build_list_tools_request()
        response = await self._send_request(connection, request)
        return self._parse_tools_response(response, connection.server_name)
    
    async def _get_tool_definition(self, connection: MCPConnection, tool_name: str) -> MCPTool:
        """Get specific tool definition."""
        tools = await self.discover_tools(connection)
        tool = next((t for t in tools if t.name == tool_name), None)
        if not tool:
            raise NetraException(f"Tool {tool_name} not found", ErrorCode.NOT_FOUND)
        return tool
    
    def _validate_tool_arguments(self, tool: MCPTool, arguments: Dict[str, Any]) -> None:
        """Validate arguments against tool schema."""
        if not self.validate_arguments(tool, arguments):
            raise NetraException("Invalid tool arguments", ErrorCode.VALIDATION_ERROR)
    
    async def _execute_with_retry(self, connection: MCPConnection, 
                                 tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with retry logic."""
        request = self._build_tool_call_request(tool_name, arguments)
        return await _retry_with_backoff(
            self._send_request, self.max_retries, self.base_delay, 
            self.backoff_factor, (Exception,), connection, request
        )
    
    def _create_success_result(self, tool_name: str, server_name: str, 
                              result: Dict[str, Any], start_time: datetime) -> MCPToolResult:
        """Create successful tool result."""
        execution_time = self._calculate_execution_time(start_time)
        return MCPToolResult(
            tool_name=tool_name, server_name=server_name,
            content=result.get("content", []), execution_time_ms=execution_time
        )
    
    def _create_error_result(self, tool_name: str, server_name: str, 
                           error: Exception, start_time: datetime) -> MCPToolResult:
        """Create error tool result."""
        execution_time = self._calculate_execution_time(start_time)
        return MCPToolResult(
            tool_name=tool_name, server_name=server_name, content=[],
            is_error=True, error_message=str(error), execution_time_ms=execution_time
        )
    
    def _validate_required_fields(self, schema: Dict[str, Any], arguments: Dict[str, Any]) -> None:
        """Validate required fields in arguments."""
        required = schema.get("required", [])
        missing = [field for field in required if field not in arguments]
        if missing:
            raise NetraException(f"Missing required fields: {missing}", ErrorCode.VALIDATION_ERROR)
    
    def _validate_field_types(self, schema: Dict[str, Any], arguments: Dict[str, Any]) -> None:
        """Validate field types according to schema."""
        properties = schema.get("properties", {})
        for field, value in arguments.items():
            if field in properties:
                self._validate_single_field_type(field, value, properties[field])
    
    def _validate_single_field_type(self, field: str, value: Any, field_schema: Dict[str, Any]) -> None:
        """Validate single field type."""
        expected_type = field_schema.get("type")
        if expected_type and not self._is_type_valid(value, expected_type):
            raise NetraException(f"Invalid type for field {field}", ErrorCode.VALIDATION_ERROR)
    
    def _is_type_valid(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected JSON schema type."""
        type_map = {
            "string": str, "number": (int, float), "integer": int,
            "boolean": bool, "array": list, "object": dict
        }
        expected_python_type = type_map.get(expected_type)
        return isinstance(value, expected_python_type) if expected_python_type else True
    
    def _extract_content(self, raw_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract content from raw result."""
        content = raw_result.get("content", [])
        if not isinstance(content, list):
            content = [{"type": "text", "text": str(content)}]
        return content
    
    def _build_list_tools_request(self) -> Dict[str, Any]:
        """Build JSON-RPC request for listing tools."""
        return {
            "jsonrpc": "2.0",
            "id": self._generate_request_id(),
            "method": "tools/list"
        }
    
    def _build_tool_call_request(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Build JSON-RPC request for tool execution."""
        return {
            "jsonrpc": "2.0",
            "id": self._generate_request_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        return hashlib.md5(f"{datetime.now().isoformat()}".encode()).hexdigest()[:8]
    
    def _calculate_execution_time(self, start_time: datetime) -> int:
        """Calculate execution time in milliseconds."""
        return int((datetime.now() - start_time).total_seconds() * 1000)
    
    def _parse_tools_response(self, response: Dict[str, Any], server_name: str) -> List[MCPTool]:
        """Parse tools list response."""
        tools_data = response.get("result", {}).get("tools", [])
        return [self._create_tool_from_data(tool_data, server_name) for tool_data in tools_data]
    
    def _create_tool_from_data(self, tool_data: Dict[str, Any], server_name: str) -> MCPTool:
        """Create MCPTool from server response data."""
        return MCPTool(
            name=tool_data["name"], description=tool_data.get("description", ""),
            server_name=server_name, input_schema=tool_data.get("inputSchema", {}),
            output_schema=tool_data.get("outputSchema"), metadata=tool_data.get("metadata")
        )
    
    async def _send_request(self, connection: MCPConnection, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request to MCP server."""
        # This would be implemented by the transport layer
        # For now, raise an exception indicating this needs transport implementation
        raise NotImplementedError("Transport layer integration required")