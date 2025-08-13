"""
Tool Execution Engine

Handles the execution of tools with permission checking, validation, and error handling.
"""
from typing import Dict, Any
from datetime import datetime, UTC
import inspect

from app.schemas.ToolPermission import ToolExecutionContext, PermissionCheckResult
from app.services.tool_permission_service import ToolPermissionService
from app.db.models_postgres import User
from app.logging_config import central_logger
from app.core.exceptions import NetraException

from .models import UnifiedTool, ToolExecutionResult

logger = central_logger


class ToolExecutionEngine:
    """Handles secure tool execution with permission checks and validation"""
    
    def __init__(self, permission_service: ToolPermissionService):
        self.permission_service = permission_service
    
    async def execute_tool(
        self, 
        tool: UnifiedTool,
        arguments: Dict[str, Any],
        user: User,
        db_session = None
    ) -> ToolExecutionResult:
        """Execute a tool with full permission checking and validation"""
        start_time = datetime.now(UTC)
        
        # Create execution context
        context = ToolExecutionContext(
            user_id=str(user.id),
            tool_name=tool.name,
            requested_action="execute",
            user_plan=getattr(user, 'plan_tier', 'free'),
            user_roles=getattr(user, 'roles', []),
            feature_flags=getattr(user, 'feature_flags', {}),
            is_developer=getattr(user, 'is_developer', False),
        )
        
        try:
            # Check if tool exists
            if not tool:
                return ToolExecutionResult(
                    tool_name=tool.name if tool else "unknown",
                    user_id=str(user.id),
                    status="error",
                    error_message="Tool not found",
                    execution_time_ms=0
                )
            
            # Check permissions
            permission_result = await self.permission_service.check_tool_permission(context)
            
            if not permission_result.allowed:
                return ToolExecutionResult(
                    tool_name=tool.name,
                    user_id=str(user.id),
                    status="permission_denied",
                    error_message=permission_result.reason,
                    permission_check=permission_result,
                    execution_time_ms=int((datetime.now(UTC) - start_time).total_seconds() * 1000)
                )
            
            # Validate input schema (basic validation)
            if tool.input_schema:
                from jsonschema import validate, ValidationError
                try:
                    validate(instance=arguments, schema=tool.input_schema)
                except ValidationError as ve:
                    raise NetraException(f"Invalid input: {ve.message}")
            
            # Execute tool handler
            if not tool.handler:
                return ToolExecutionResult(
                    tool_name=tool.name,
                    user_id=str(user.id),
                    status="error",
                    error_message=f"Tool '{tool.name}' has no handler",
                    execution_time_ms=int((datetime.now(UTC) - start_time).total_seconds() * 1000)
                )
            
            # Execute handler (async or sync)
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(arguments, user)
            else:
                result = tool.handler(arguments, user)
            
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            
            # Record usage for rate limiting
            await self.permission_service.record_tool_usage(
                user_id=str(user.id),
                tool_name=tool.name,
                execution_time_ms=execution_time_ms,
                status="success"
            )
            
            execution_result = ToolExecutionResult(
                tool_name=tool.name,
                user_id=str(user.id),
                status="success",
                result=result,
                permission_check=permission_result,
                execution_time_ms=execution_time_ms
            )
            
            return execution_result
            
        except Exception as e:
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            logger.error(f"Tool execution failed: {tool.name if tool else 'unknown'} - {e}", exc_info=True)
            
            # Record usage even for failed executions
            if tool:
                await self.permission_service.record_tool_usage(
                    user_id=str(user.id),
                    tool_name=tool.name,
                    execution_time_ms=execution_time_ms,
                    status="error"
                )
            
            return ToolExecutionResult(
                tool_name=tool.name if tool else "unknown",
                user_id=str(user.id),
                status="error",
                error_message=str(e),
                execution_time_ms=execution_time_ms
            )