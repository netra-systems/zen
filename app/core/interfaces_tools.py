"""Tool interfaces - Single source of truth.

Consolidated tool execution and registry logic from both simple and comprehensive
implementations. Follows 300-line limit and 8-line functions.
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from abc import ABC, abstractmethod
from datetime import datetime, UTC
import inspect

from app.logging_config import central_logger
from app.core.exceptions_base import NetraException

if TYPE_CHECKING:
    from app.db.models_postgres import User
    from app.schemas import ToolResult, ToolStatus, ToolInput, SimpleToolPayload
    from app.schemas.ToolPermission import ToolExecutionContext, PermissionCheckResult
    from app.services.tool_permission_service import ToolPermissionService

logger = central_logger.get_logger(__name__)


class ToolExecutionResult:
    """Result of tool execution with comprehensive tracking."""
    
    def __init__(self, tool_name: str, user_id: str, status: str, 
                 execution_time_ms: int, result: Any = None, 
                 error_message: str = None, permission_check = None):
        self.tool_name = tool_name
        self.user_id = user_id
        self.status = status
        self.execution_time_ms = execution_time_ms
        self.result = result
        self.error_message = error_message
        self.permission_check = permission_check


class UnifiedTool:
    """Unified tool representation."""
    
    def __init__(self, name: str, handler: Any = None, input_schema: Dict = None):
        self.name = name
        self.handler = handler
        self.input_schema = input_schema


class ToolExecutionEngine:
    """Unified tool execution engine with permission checks and validation."""
    
    def __init__(self, permission_service: Optional['ToolPermissionService'] = None):
        """Initialize tool execution engine."""
        self.permission_service = permission_service
    
    async def execute_tool(self, tool_input: 'ToolInput', tool: Any, kwargs: Dict[str, Any]) -> 'ToolResult':
        """Execute tool with simple interface and return typed result."""
        try:
            result = await self._run_tool_by_interface(tool, kwargs)
            return self._create_success_result(tool_input, result)
        except Exception as e:
            return self._create_error_result(tool_input, str(e))
    
    async def execute_with_state(self, tool: Any, tool_name: str, parameters: Dict[str, Any],
                                state: Any, run_id: str) -> Dict[str, Any]:
        """Execute tool with state and comprehensive error handling."""
        try:
            result = await self._execute_by_tool_type(tool, parameters, state, run_id)
            return self._create_success_response(result, tool_name, run_id)
        except Exception as e:
            return self._create_error_response(e, tool_name, run_id)
    
    async def execute_with_permissions(self, tool: UnifiedTool, arguments: Dict[str, Any],
                                     user: 'User') -> ToolExecutionResult:
        """Execute tool with full permission checking and validation."""
        start_time = datetime.now(UTC)
        
        try:
            validation_error, permission_result = await self._perform_all_validations(
                tool, user, arguments, start_time
            )
            if validation_error:
                return validation_error
            
            return await self._execute_and_record_usage(tool, user, arguments, permission_result, start_time)
            
        except Exception as e:
            return await self._handle_execution_error(tool, user, e, start_time)
    
    # Core execution methods
    
    async def _run_tool_by_interface(self, tool: Any, kwargs: Dict[str, Any]) -> Any:
        """Run tool based on its interface type."""
        if hasattr(tool, 'arun'):
            return await tool.arun(kwargs)
        else:
            return tool(kwargs)
    
    async def _execute_by_tool_type(self, tool: Any, parameters: Dict[str, Any], 
                                   state: Any, run_id: str) -> Any:
        """Execute tool based on its type and interface."""
        from app.agents.production_tool import ProductionTool
        
        if isinstance(tool, ProductionTool):
            return await tool.execute(parameters, state, run_id)
        elif hasattr(tool, 'arun'):
            return await tool.arun(parameters)
        else:
            return tool(parameters)
    
    # Permission and validation methods
    
    async def _perform_all_validations(self, tool: UnifiedTool, user: 'User', 
                                      arguments: Dict[str, Any], start_time: datetime):
        """Perform all validations and return error result if any fail."""
        tool_error = self._validate_tool_exists(tool, user, start_time)
        if tool_error:
            return tool_error, None
        
        if self.permission_service:
            permission_result = await self._check_tool_permissions(tool, user)
            if not permission_result.allowed:
                return self._handle_permission_denied(tool, user, permission_result, start_time), None
        else:
            permission_result = None
        
        self._validate_input_schema(tool, arguments)
        handler_error = self._validate_tool_handler(tool, user, start_time)
        return handler_error, permission_result
    
    async def _check_tool_permissions(self, tool: UnifiedTool, user: 'User') -> 'PermissionCheckResult':
        """Check tool permissions if permission service is available."""
        context = self._create_execution_context(tool, user)
        return await self.permission_service.check_tool_permission(context)
    
    def _create_execution_context(self, tool: UnifiedTool, user: 'User') -> 'ToolExecutionContext':
        """Create execution context for tool validation."""
        from app.schemas.ToolPermission import ToolExecutionContext
        
        return ToolExecutionContext(
            user_id=str(user.id), tool_name=tool.name, requested_action="execute",
            user_plan=getattr(user, 'plan_tier', 'free'), user_roles=getattr(user, 'roles', []),
            feature_flags=getattr(user, 'feature_flags', {}), is_developer=getattr(user, 'is_developer', False)
        )
    
    # Validation helper methods
    
    def _validate_tool_exists(self, tool: UnifiedTool, user: 'User', start_time: datetime) -> Optional[ToolExecutionResult]:
        """Validate tool exists and return error result if not."""
        if not tool:
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            return ToolExecutionResult(
                tool_name=tool.name if tool else "unknown", user_id=str(user.id),
                status="error", error_message="Tool not found", execution_time_ms=execution_time_ms
            )
        return None
    
    def _validate_input_schema(self, tool: UnifiedTool, arguments: Dict[str, Any]) -> None:
        """Validate input arguments against tool schema."""
        if tool.input_schema:
            from jsonschema import validate, ValidationError
            try:
                validate(instance=arguments, schema=tool.input_schema)
            except ValidationError as ve:
                raise NetraException(f"Invalid input: {ve.message}")
    
    def _validate_tool_handler(self, tool: UnifiedTool, user: 'User', start_time: datetime) -> Optional[ToolExecutionResult]:
        """Validate tool has handler and return error result if not."""
        if not tool.handler:
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            return ToolExecutionResult(
                tool_name=tool.name, user_id=str(user.id), status="error",
                error_message=f"Tool '{tool.name}' has no handler", execution_time_ms=execution_time_ms
            )
        return None
    
    def _handle_permission_denied(self, tool: UnifiedTool, user: 'User', 
                                 permission_result: 'PermissionCheckResult', start_time: datetime) -> ToolExecutionResult:
        """Handle permission denied scenario."""
        execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        return ToolExecutionResult(
            tool_name=tool.name, user_id=str(user.id), status="permission_denied",
            error_message=permission_result.reason, permission_check=permission_result,
            execution_time_ms=execution_time_ms
        )
    
    # Execution and recording methods
    
    async def _execute_and_record_usage(self, tool: UnifiedTool, user: 'User', arguments: Dict[str, Any],
                                       permission_result: 'PermissionCheckResult', start_time: datetime) -> ToolExecutionResult:
        """Execute tool handler and record successful usage."""
        result = await self._execute_tool_handler(tool, arguments, user)
        execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        
        if self.permission_service:
            await self._record_successful_usage(tool, user, execution_time_ms)
        
        return self._create_successful_result(tool, user, result, permission_result, execution_time_ms)
    
    async def _execute_tool_handler(self, tool: UnifiedTool, arguments: Dict[str, Any], user: 'User') -> Any:
        """Execute tool handler (async or sync)."""
        if inspect.iscoroutinefunction(tool.handler):
            return await tool.handler(arguments, user)
        else:
            return tool.handler(arguments, user)
    
    async def _record_successful_usage(self, tool: UnifiedTool, user: 'User', execution_time_ms: int) -> None:
        """Record successful tool usage for rate limiting."""
        await self.permission_service.record_tool_usage(
            user_id=str(user.id), tool_name=tool.name, execution_time_ms=execution_time_ms, status="success"
        )
    
    async def _record_error_usage(self, tool: UnifiedTool, user: 'User', execution_time_ms: int) -> None:
        """Record error usage for rate limiting."""
        if tool and self.permission_service:
            await self.permission_service.record_tool_usage(
                user_id=str(user.id), tool_name=tool.name, execution_time_ms=execution_time_ms, status="error"
            )
    
    # Error handling methods
    
    async def _handle_execution_error(self, tool: UnifiedTool, user: 'User', 
                                     error: Exception, start_time: datetime) -> ToolExecutionResult:
        """Handle execution error and create error result."""
        execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        logger.error(f"Tool execution failed: {tool.name if tool else 'unknown'} - {error}", exc_info=True)
        
        await self._record_error_usage(tool, user, execution_time_ms)
        return self._create_error_result_detailed(tool, user, error, execution_time_ms)
    
    # Response creation methods
    
    def _create_success_result(self, tool_input: 'ToolInput', result: Any) -> 'ToolResult':
        """Create successful tool result for simple interface."""
        from app.schemas import ToolResult, ToolStatus, SimpleToolPayload
        
        payload = SimpleToolPayload(result=result)
        return ToolResult(tool_input=tool_input, status=ToolStatus.SUCCESS, payload=payload)
    
    def _create_error_result(self, tool_input: 'ToolInput', message: str) -> 'ToolResult':
        """Create error result for simple interface."""
        from app.schemas import ToolResult, ToolStatus
        
        return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=message)
    
    def _create_success_response(self, result: Any, tool_name: str, run_id: str) -> Dict[str, Any]:
        """Create successful tool execution response."""
        return {
            "success": True, "result": result,
            "metadata": {"tool_name": tool_name, "run_id": run_id}
        }
    
    def _create_error_response(self, error: Exception, tool_name: str, run_id: str) -> Dict[str, Any]:
        """Create error response for tool execution failure."""
        logger.error(f"Tool {tool_name} execution failed: {error}")
        return {
            "success": False, "error": str(error),
            "metadata": {"tool_name": tool_name, "run_id": run_id}
        }
    
    def _create_successful_result(self, tool: UnifiedTool, user: 'User', result: Any,
                                 permission_result: 'PermissionCheckResult', execution_time_ms: int) -> ToolExecutionResult:
        """Create successful execution result."""
        return ToolExecutionResult(
            tool_name=tool.name, user_id=str(user.id), status="success", result=result,
            permission_check=permission_result, execution_time_ms=execution_time_ms
        )
    
    def _create_error_result_detailed(self, tool: UnifiedTool, user: 'User', 
                                     error: Exception, execution_time_ms: int) -> ToolExecutionResult:
        """Create error execution result."""
        return ToolExecutionResult(
            tool_name=tool.name if tool else "unknown", user_id=str(user.id),
            status="error", error_message=str(error), execution_time_ms=execution_time_ms
        )


class ToolRegistry:
    """Unified tool registry merging full-featured and simple implementations."""
    
    def __init__(self, db_session=None):
        """Initialize tool registry."""
        self.db_session = db_session
        self.tools: Dict[str, Any] = {}
        self._tool_configs = self._init_agent_tool_configs()
        self._register_default_tools()
    
    def _init_agent_tool_configs(self) -> Dict[str, List]:
        """Initialize agent-specific tool configurations."""
        return {
            "triage": [], "data": [], "optimizations_core": [],
            "actions_to_meet_goals": [], "reporting": []
        }
    
    def _register_default_tools(self) -> None:
        """Register default synthetic and corpus tools."""
        self._register_synthetic_tools()
        self._register_corpus_tools()
    
    def _register_synthetic_tools(self) -> None:
        """Register synthetic data generation tools."""
        from app.agents.production_tool import ProductionTool
        
        synthetic_tools = ["generate_synthetic_data_batch", "validate_synthetic_data", "store_synthetic_data"]
        for tool_name in synthetic_tools:
            if tool_name not in self.tools:
                self.tools[tool_name] = ProductionTool(tool_name)
    
    def _register_corpus_tools(self) -> None:
        """Register corpus management tools."""
        from app.agents.production_tool import ProductionTool
        
        corpus_tools = [
            "create_corpus", "search_corpus", "update_corpus", "delete_corpus",
            "analyze_corpus", "export_corpus", "import_corpus", "validate_corpus"
        ]
        for tool_name in corpus_tools:
            if tool_name not in self.tools:
                self.tools[tool_name] = ProductionTool(tool_name)
    
    # Tool management methods
    
    def register_tool(self, tool: Any) -> None:
        """Register a single tool."""
        self.tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")
    
    def register_tools(self, tools: List[Any]) -> None:
        """Register list of tools."""
        for tool in tools:
            self.register_tool(tool)
    
    def get_tool(self, tool_name: str) -> Optional[Any]:
        """Get a tool by name."""
        return self.tools.get(tool_name)
    
    def get_tools(self, tool_names: List[str]) -> List[Any]:
        """Get tools for agent-specific tool names."""
        tools = []
        for name in tool_names:
            if name in self._tool_configs:
                tools.extend(self._tool_configs[name])
            elif name in self.tools:
                tools.append(self.tools[name])
        return tools
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool exists."""
        return tool_name in self.tools or tool_name in self._tool_configs
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        all_tools = list(self.tools.keys()) + list(self._tool_configs.keys())
        return sorted(set(all_tools))
    
    def remove_tool(self, tool_name: str) -> bool:
        """Remove a tool from registry."""
        removed = False
        if tool_name in self.tools:
            del self.tools[tool_name]
            removed = True
        if tool_name in self._tool_configs:
            del self._tool_configs[tool_name]
            removed = True
        return removed
    
    def clear_tools(self) -> None:
        """Clear all tools from registry."""
        self.tools.clear()
        self._tool_configs = self._init_agent_tool_configs()
        self._register_default_tools()
    
    def get_tool_count(self) -> int:
        """Get total number of registered tools."""
        return len(self.tools) + sum(len(tools) for tools in self._tool_configs.values())