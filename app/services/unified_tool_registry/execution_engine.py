"""
Tool Execution Engine

Handles the execution of tools with permission checking, validation, and error handling.
"""
from typing import Dict, Any
from datetime import datetime, UTC
import inspect

from app.schemas.Tool import ToolExecutionEngineInterface, ToolExecuteResponse
from app.schemas.ToolPermission import ToolExecutionContext, PermissionCheckResult
from app.services.tool_permission_service import ToolPermissionService
from app.db.models_postgres import User
from app.logging_config import central_logger
from app.core.exceptions_base import NetraException

from .models import UnifiedTool, ToolExecutionResult

logger = central_logger


class ToolExecutionEngine(ToolExecutionEngineInterface):
    """Handles secure tool execution with permission checks and validation"""
    
    def __init__(self, permission_service: ToolPermissionService):
        self.permission_service = permission_service
    
    def _create_execution_context(self, tool: UnifiedTool, user: User) -> ToolExecutionContext:
        """Create execution context for tool validation"""
        return ToolExecutionContext(
            user_id=str(user.id),
            tool_name=tool.name,
            requested_action="execute",
            user_plan=getattr(user, 'plan_tier', 'free'),
            user_roles=getattr(user, 'roles', []),
            feature_flags=getattr(user, 'feature_flags', {}),
            is_developer=getattr(user, 'is_developer', False),
        )
    
    def _validate_tool_exists(self, tool: UnifiedTool, user: User) -> ToolExecutionResult | None:
        """Validate tool exists and return error result if not"""
        if not tool:
            return ToolExecutionResult(
                tool_name=tool.name if tool else "unknown",
                user_id=str(user.id),
                status="error",
                error_message="Tool not found",
                execution_time_ms=0
            )
        return None
    
    def _handle_permission_denied(
        self, tool: UnifiedTool, user: User, permission_result: PermissionCheckResult, start_time: datetime
    ) -> ToolExecutionResult:
        """Handle permission denied scenario"""
        execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        return ToolExecutionResult(
            tool_name=tool.name,
            user_id=str(user.id),
            status="permission_denied",
            error_message=permission_result.reason,
            permission_check=permission_result,
            execution_time_ms=execution_time_ms
        )
    
    def _validate_input_schema(self, tool: UnifiedTool, arguments: Dict[str, Any]) -> None:
        """Validate input arguments against tool schema"""
        if tool.input_schema:
            from jsonschema import validate, ValidationError
            try:
                validate(instance=arguments, schema=tool.input_schema)
            except ValidationError as ve:
                raise NetraException(f"Invalid input: {ve.message}")
    
    def _validate_tool_handler(self, tool: UnifiedTool, user: User, start_time: datetime) -> ToolExecutionResult | None:
        """Validate tool has handler and return error result if not"""
        if not tool.handler:
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            return ToolExecutionResult(
                tool_name=tool.name,
                user_id=str(user.id),
                status="error",
                error_message=f"Tool '{tool.name}' has no handler",
                execution_time_ms=execution_time_ms
            )
        return None
    
    async def _execute_handler(self, tool: UnifiedTool, arguments: Dict[str, Any], user: User) -> Any:
        """Execute tool handler (async or sync)"""
        if inspect.iscoroutinefunction(tool.handler):
            return await tool.handler(arguments, user)
        else:
            return tool.handler(arguments, user)
    
    async def _record_successful_usage(
        self, tool: UnifiedTool, user: User, execution_time_ms: int
    ) -> None:
        """Record successful tool usage for rate limiting"""
        await self.permission_service.record_tool_usage(
            user_id=str(user.id),
            tool_name=tool.name,
            execution_time_ms=execution_time_ms,
            status="success"
        )
    
    def _create_successful_result(
        self, tool: UnifiedTool, user: User, result: Any, 
        permission_result: PermissionCheckResult, execution_time_ms: int
    ) -> ToolExecutionResult:
        """Create successful execution result"""
        return ToolExecutionResult(
            tool_name=tool.name,
            user_id=str(user.id),
            status="success",
            result=result,
            permission_check=permission_result,
            execution_time_ms=execution_time_ms
        )
    
    async def _record_error_usage(
        self, tool: UnifiedTool, user: User, execution_time_ms: int
    ) -> None:
        """Record error usage for rate limiting"""
        if tool:
            await self.permission_service.record_tool_usage(
                user_id=str(user.id),
                tool_name=tool.name,
                execution_time_ms=execution_time_ms,
                status="error"
            )
    
    def _create_error_result(
        self, tool: UnifiedTool, user: User, error: Exception, execution_time_ms: int
    ) -> ToolExecutionResult:
        """Create error execution result"""
        return ToolExecutionResult(
            tool_name=tool.name if tool else "unknown",
            user_id=str(user.id),
            status="error",
            error_message=str(error),
            execution_time_ms=execution_time_ms
        )
    
    async def _handle_execution_error(
        self, tool: UnifiedTool, user: User, error: Exception, start_time: datetime
    ) -> ToolExecutionResult:
        """Handle execution error and create error result"""
        execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        logger.error(f"Tool execution failed: {tool.name if tool else 'unknown'} - {error}", exc_info=True)
        await self._record_error_usage(tool, user, execution_time_ms)
        return self._create_error_result(tool, user, error, execution_time_ms)
    
    async def _check_tool_and_permissions(
        self, tool: UnifiedTool, user: User, start_time: datetime
    ) -> tuple[ToolExecutionResult | None, PermissionCheckResult | None]:
        """Check tool existence and permissions"""
        tool_error = self._validate_tool_exists(tool, user)
        if tool_error:
            return tool_error, None
        
        permission_result = await self.permission_service.check_tool_permission(
            self._create_execution_context(tool, user)
        )
        if not permission_result.allowed:
            return self._handle_permission_denied(tool, user, permission_result, start_time), None
        
        return None, permission_result
    
    def _check_input_and_handler(
        self, tool: UnifiedTool, user: User, arguments: Dict[str, Any], start_time: datetime
    ) -> ToolExecutionResult | None:
        """Check input schema and handler validity"""
        self._validate_input_schema(tool, arguments)
        return self._validate_tool_handler(tool, user, start_time)
    
    async def _perform_validations(
        self, tool: UnifiedTool, user: User, arguments: Dict[str, Any], start_time: datetime
    ) -> tuple[ToolExecutionResult | None, PermissionCheckResult | None]:
        """Perform all validations and return error result if any fail"""
        permission_error, permission_result = await self._check_tool_and_permissions(tool, user, start_time)
        if permission_error:
            return permission_error, None
        
        handler_error = self._check_input_and_handler(tool, user, arguments, start_time)
        return handler_error, permission_result
    
    async def _execute_and_record(
        self, tool: UnifiedTool, user: User, arguments: Dict[str, Any], 
        permission_result: PermissionCheckResult, start_time: datetime
    ) -> ToolExecutionResult:
        """Execute tool handler and record successful usage"""
        result = await self._execute_handler(tool, arguments, user)
        execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        await self._record_successful_usage(tool, user, execution_time_ms)
        return self._create_successful_result(tool, user, result, permission_result, execution_time_ms)
    
    async def execute_unified_tool(
        self, 
        tool: UnifiedTool,
        arguments: Dict[str, Any],
        user: User,
        db_session = None
    ) -> ToolExecutionResult:
        """Execute a tool with full permission checking and validation"""
        start_time = datetime.now(UTC)
        
        try:
            validation_error, permission_result = await self._perform_validations(
                tool, user, arguments, start_time
            )
            if validation_error:
                return validation_error
            
            return await self._execute_and_record(tool, user, arguments, permission_result, start_time)
            
        except Exception as e:
            return await self._handle_execution_error(tool, user, e, start_time)
    
    # Interface Implementation Method
    async def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> ToolExecuteResponse:
        """Execute a tool by name with parameters - implements ToolExecutionEngineInterface"""
        from .unified_tool_registry import UnifiedToolRegistry
        
        # Get tool from registry  
        registry = UnifiedToolRegistry(self.permission_service)
        tool = registry.get_tool(tool_name)
        
        if not tool:
            return ToolExecuteResponse(
                success=False,
                message=f"Tool '{tool_name}' not found",
                metadata={"tool_name": tool_name}
            )
        
        # Create mock user for interface compatibility
        mock_user = self._create_mock_user_for_interface()
        
        # Execute tool using existing comprehensive method
        result = await self.execute_unified_tool(tool, parameters, mock_user)
        
        # Convert ToolExecutionResult to ToolExecuteResponse
        return self._convert_execution_result_to_response(result, tool_name)
    
    def _create_mock_user_for_interface(self) -> User:
        """Create mock user for interface method compatibility"""
        # This is a temporary solution for interface compatibility
        # In production, proper user should be passed through context
        mock_user = User()
        mock_user.id = "interface_user"
        mock_user.plan_tier = "free"
        mock_user.roles = []
        mock_user.feature_flags = {}
        mock_user.is_developer = False
        return mock_user
    
    def _convert_execution_result_to_response(
        self, 
        result: ToolExecutionResult, 
        tool_name: str
    ) -> ToolExecuteResponse:
        """Convert ToolExecutionResult to ToolExecuteResponse"""
        return ToolExecuteResponse(
            success=(result.status == "success"),
            data=result.result if result.status == "success" else None,
            message=result.error_message if result.status != "success" else "Success",
            metadata={
                "tool_name": tool_name,
                "execution_time_ms": result.execution_time_ms,
                "status": result.status
            }
        )