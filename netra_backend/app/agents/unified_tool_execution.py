"""Unified tool execution engine - SSOT for all tool execution.

This module consolidates all tool execution functionality into a single SSOT,
merging the best features from:
- unified_tool_execution.py (WebSocket notifications)
- tool_dispatcher_execution.py (core delegation pattern)
- core/interfaces_tools.py (permission checks and validation)

Business Value: Single coherent tool execution system with real-time notifications.
"""

import asyncio
import inspect
import time
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.tool_models import ToolExecutionResult, UnifiedTool
from netra_backend.app.logging_config import central_logger

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
    from netra_backend.app.db.models_postgres import User
    from netra_backend.app.schemas.tool import (
        SimpleToolPayload,
        ToolExecuteResponse,
        ToolInput,
        ToolResult,
        ToolStatus,
    )
    from netra_backend.app.schemas.tool_permission import (
        PermissionCheckResult,
        ToolExecutionContext,
    )
    from netra_backend.app.services.tool_permission_service import ToolPermissionService
    from netra_backend.app.websocket_core import WebSocketManager

logger = central_logger.get_logger(__name__)


class UnifiedToolExecutionEngine:
    """Single source of truth for all tool execution with WebSocket notifications.
    
    This class consolidates:
    1. Core tool execution from interfaces_tools.py
    2. WebSocket notifications from unified_tool_execution.py
    3. Delegation pattern from tool_dispatcher_execution.py
    4. Permission checks and validation
    """
    
    def __init__(
        self,
        websocket_manager: Optional['WebSocketManager'] = None,
        permission_service: Optional['ToolPermissionService'] = None
    ):
        """Initialize unified tool execution engine."""
        self.websocket_manager = websocket_manager
        self.websocket_notifier = None
        if websocket_manager:
            from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
            self.websocket_notifier = WebSocketNotifier(websocket_manager)
        
        self.permission_service = permission_service
        
        # Metrics tracking
        self._active_executions: Dict[str, Dict] = {}
        self._execution_metrics = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_duration_ms': 0
        }
    
    # Core execution methods with WebSocket notifications
    
    async def execute_tool_with_input(
        self,
        tool_input: 'ToolInput',
        tool: Any,
        kwargs: Dict[str, Any]
    ) -> 'ToolResult':
        """Execute tool with simple interface and WebSocket notifications."""
        context = kwargs.get('context')
        tool_name = getattr(tool, 'name', str(tool))
        start_time = time.time()
        execution_id = f"{tool_name}_{int(start_time * 1000)}"
        
        # Track active execution
        self._active_executions[execution_id] = {
            'tool_name': tool_name,
            'start_time': start_time,
            'context': context
        }
        
        # Send executing notification
        if context and self.websocket_notifier:
            await self._send_tool_executing(context, tool_name, tool_input)
        
        try:
            # Execute tool by interface type
            result = await self._run_tool_by_interface(tool, kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            # Update metrics
            self._execution_metrics['successful_executions'] += 1
            
            # Send completed notification
            if context and self.websocket_notifier:
                await self._send_tool_completed(
                    context, tool_name, result, duration_ms, "success"
                )
            
            return self._create_success_result(tool_input, result)
            
        except asyncio.TimeoutError as te:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Tool {tool_name} timed out after {duration_ms:.0f}ms")
            
            # Update metrics
            self._execution_metrics['failed_executions'] += 1
            
            # Send timeout notification
            if context and self.websocket_notifier:
                await self._send_tool_completed(
                    context, tool_name, str(te), duration_ms, "timeout"
                )
            
            return self._create_error_result(tool_input, f"Timeout after {duration_ms:.0f}ms")
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_type = type(e).__name__
            logger.error(f"Tool {tool_name} failed with {error_type}: {e}")
            
            # Update metrics
            self._execution_metrics['failed_executions'] += 1
            
            # Send error notification
            if context and self.websocket_notifier:
                await self._send_tool_completed(
                    context, tool_name, str(e), duration_ms, "error", error_type
                )
            
            return self._create_error_result(tool_input, str(e))
            
        finally:
            # Clean up tracking
            if execution_id in self._active_executions:
                exec_info = self._active_executions.pop(execution_id)
                duration_ms = (time.time() - exec_info['start_time']) * 1000
                self._execution_metrics['total_duration_ms'] += duration_ms
                self._execution_metrics['total_executions'] += 1
    
    async def execute_with_state(
        self,
        tool: Any,
        tool_name: str,
        parameters: Dict[str, Any],
        state: Any,
        run_id: str
    ) -> Dict[str, Any]:
        """Execute tool with state and comprehensive error handling."""
        # Validate inputs
        if not tool_name:
            raise ValueError("Tool name is required for execution")
        if not run_id:
            run_id = str(uuid.uuid4())
            logger.warning(f"No run_id provided for {tool_name}, generated: {run_id}")
        
        start_time = time.time()
        execution_id = f"{run_id}_{tool_name}_{int(start_time * 1000)}"
        
        # Get or create context for notifications
        context = None
        if self.websocket_notifier:
            context = self._get_or_create_context(state, run_id, tool_name)
            await self._send_tool_executing(context, tool_name, parameters)
        
        try:
            # Execute by tool type
            result = await self._execute_by_tool_type(tool, parameters, state, run_id)
            duration_ms = (time.time() - start_time) * 1000
            
            # Send completed notification
            if context and self.websocket_notifier:
                await self._send_tool_completed(
                    context, tool_name, result, duration_ms, "success"
                )
            
            logger.debug(f"Tool {tool_name} completed in {duration_ms:.0f}ms")
            return self._create_success_response(result, tool_name, run_id)
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_type = type(e).__name__
            logger.error(f"Tool {tool_name} failed after {duration_ms:.0f}ms with {error_type}: {e}")
            
            # Send error notification
            if context and self.websocket_notifier:
                await self._send_tool_completed(
                    context, tool_name, str(e), duration_ms, "error", error_type
                )
            
            return self._create_error_response(e, tool_name, run_id)
    
    async def execute_with_permissions(
        self,
        tool: UnifiedTool,
        arguments: Dict[str, Any],
        user: 'User'
    ) -> ToolExecutionResult:
        """Execute tool with full permission checking and validation."""
        start_time = datetime.now(UTC)
        
        try:
            # Perform all validations
            validation_error, permission_result = await self._perform_all_validations(
                tool, user, arguments, start_time
            )
            if validation_error:
                return validation_error
            
            # Execute and record usage
            return await self._execute_and_record_usage(
                tool, user, arguments, permission_result, start_time
            )
            
        except Exception as e:
            return await self._handle_execution_error(tool, user, e, start_time)
    
    # Interface method for ToolExecutionEngineInterface compatibility
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> 'ToolExecuteResponse':
        """Execute a tool by name with parameters - implements interface."""
        try:
            from netra_backend.app.agents.production_tool import ProductionTool
            
            tool = ProductionTool(tool_name)
            result = await self._run_tool_by_interface(tool, parameters)
            
            return self._create_success_tool_response(result, tool_name)
            
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return self._create_error_tool_response(e, tool_name)
    
    # Private execution methods
    
    async def _run_tool_by_interface(self, tool: Any, kwargs: Dict[str, Any]) -> Any:
        """Run tool based on its interface type."""
        if hasattr(tool, 'arun'):
            return await tool.arun(kwargs)
        elif asyncio.iscoroutinefunction(tool):
            return await tool(kwargs)
        else:
            return tool(kwargs)
    
    async def _execute_by_tool_type(
        self,
        tool: Any,
        parameters: Dict[str, Any],
        state: Any,
        run_id: str
    ) -> Any:
        """Execute tool based on its type and interface."""
        from netra_backend.app.agents.production_tool import ProductionTool
        
        if isinstance(tool, ProductionTool):
            return await tool.execute(parameters, state, run_id)
        elif hasattr(tool, 'arun'):
            return await tool.arun(parameters)
        else:
            return tool(parameters)
    
    # Permission and validation methods
    
    async def _perform_all_validations(
        self,
        tool: UnifiedTool,
        user: 'User',
        arguments: Dict[str, Any],
        start_time: datetime
    ):
        """Perform all validations and return error result if any fail."""
        # Validate tool exists
        if not tool:
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            error = ToolExecutionResult(
                tool_name="unknown",
                user_id=str(user.id),
                status="error",
                error_message="Tool not found",
                execution_time_ms=execution_time_ms
            )
            return error, None
        
        # Check permissions if service available
        permission_result = None
        if self.permission_service:
            permission_result = await self._check_tool_permissions(tool, user)
            if not permission_result.allowed:
                return self._handle_permission_denied(
                    tool, user, permission_result, start_time
                ), None
        
        # Validate input schema
        try:
            self._validate_input_schema(tool, arguments)
        except NetraException as ve:
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            error = ToolExecutionResult(
                tool_name=tool.name,
                user_id=str(user.id),
                status="error",
                error_message=str(ve),
                execution_time_ms=execution_time_ms
            )
            return error, None
        
        # Validate tool has handler
        if not tool.handler:
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            error = ToolExecutionResult(
                tool_name=tool.name,
                user_id=str(user.id),
                status="error",
                error_message=f"Tool '{tool.name}' has no handler",
                execution_time_ms=execution_time_ms
            )
            return error, None
        
        return None, permission_result
    
    async def _check_tool_permissions(
        self,
        tool: UnifiedTool,
        user: 'User'
    ) -> 'PermissionCheckResult':
        """Check tool permissions if permission service is available."""
        from netra_backend.app.schemas.tool_permission import ToolExecutionContext
        
        context = ToolExecutionContext(
            user_id=str(user.id),
            tool_name=tool.name,
            requested_action="execute",
            user_plan=getattr(user, 'plan_tier', 'free'),
            user_roles=getattr(user, 'roles', []),
            feature_flags=getattr(user, 'feature_flags', {}),
            is_developer=getattr(user, 'is_developer', False)
        )
        
        return await self.permission_service.check_tool_permission(context)
    
    def _validate_input_schema(self, tool: UnifiedTool, arguments: Dict[str, Any]) -> None:
        """Validate input arguments against tool schema."""
        if tool.input_schema:
            from jsonschema import ValidationError, validate
            try:
                validate(instance=arguments, schema=tool.input_schema)
            except ValidationError as ve:
                raise NetraException(f"Invalid input: {ve.message}")
    
    def _handle_permission_denied(
        self,
        tool: UnifiedTool,
        user: 'User',
        permission_result: 'PermissionCheckResult',
        start_time: datetime
    ) -> ToolExecutionResult:
        """Handle permission denied scenario."""
        execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        return ToolExecutionResult(
            tool_name=tool.name,
            user_id=str(user.id),
            status="permission_denied",
            error_message=permission_result.reason,
            permission_check=permission_result,
            execution_time_ms=execution_time_ms
        )
    
    # Execution and recording methods
    
    async def _execute_and_record_usage(
        self,
        tool: UnifiedTool,
        user: 'User',
        arguments: Dict[str, Any],
        permission_result: 'PermissionCheckResult',
        start_time: datetime
    ) -> ToolExecutionResult:
        """Execute tool handler and record successful usage."""
        # Execute handler (async or sync)
        if inspect.iscoroutinefunction(tool.handler):
            result = await tool.handler(arguments, user)
        else:
            result = tool.handler(arguments, user)
        
        execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        
        # Record usage if permission service available
        if self.permission_service:
            await self.permission_service.record_tool_usage(
                user_id=str(user.id),
                tool_name=tool.name,
                execution_time_ms=execution_time_ms,
                status="success"
            )
        
        return ToolExecutionResult(
            tool_name=tool.name,
            user_id=str(user.id),
            status="success",
            result=result,
            permission_check=permission_result,
            execution_time_ms=execution_time_ms
        )
    
    async def _handle_execution_error(
        self,
        tool: UnifiedTool,
        user: 'User',
        error: Exception,
        start_time: datetime
    ) -> ToolExecutionResult:
        """Handle execution error and create error result."""
        execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        logger.error(f"Tool execution failed: {tool.name if tool else 'unknown'} - {error}", exc_info=True)
        
        # Record error usage
        if tool and self.permission_service:
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
            error_message=str(error),
            execution_time_ms=execution_time_ms
        )
    
    # WebSocket notification methods
    
    async def _send_tool_executing(
        self,
        context: 'AgentExecutionContext',
        tool_name: str,
        tool_input: Any
    ) -> None:
        """Send tool executing notification with enhanced metadata."""
        if not self.websocket_notifier or not context:
            return
        
        try:
            # Extract contextual information
            tool_purpose = self._get_tool_purpose(tool_name, tool_input)
            estimated_duration = self._estimate_tool_duration(tool_name, tool_input)
            params_summary = self._create_parameters_summary(tool_input)
            
            await self.websocket_notifier.send_tool_executing(
                context,
                tool_name,
                tool_purpose=tool_purpose,
                estimated_duration_ms=estimated_duration,
                parameters_summary=params_summary
            )
        except Exception as e:
            logger.warning(f"Failed to send tool_executing notification: {e}")
    
    async def _send_tool_completed(
        self,
        context: 'AgentExecutionContext',
        tool_name: str,
        result: Any,
        duration_ms: float,
        status: str,
        error_type: str = None
    ) -> None:
        """Send tool completed notification with result."""
        if not self.websocket_notifier or not context:
            return
        
        try:
            result_dict = {
                "status": status,
                "duration_ms": duration_ms,
                "tool_name": tool_name
            }
            
            if status == "success":
                result_dict["output"] = str(result)[:500] if result else None
            elif status in ["error", "timeout"]:
                result_dict["error"] = str(result)
                if error_type:
                    result_dict["error_type"] = error_type
                    result_dict["recoverable"] = error_type not in [
                        "MemoryError", "SystemError", "KeyboardInterrupt"
                    ]
            
            await self.websocket_notifier.send_tool_completed(
                context, tool_name, result_dict
            )
        except Exception as e:
            logger.warning(f"Failed to send tool_completed notification: {e}")
    
    def _get_or_create_context(
        self,
        state: Any,
        run_id: str,
        tool_name: str
    ) -> 'AgentExecutionContext':
        """Get existing WebSocket context from agent or create new one."""
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        from netra_backend.app.agents.utils import extract_thread_id
        
        # Try to get context from the agent that called this tool
        if hasattr(state, '_websocket_context') and state._websocket_context:
            original_context = state._websocket_context
            return AgentExecutionContext(
                agent_name=f"{original_context.agent_name}[{tool_name}]",
                run_id=original_context.run_id,
                thread_id=original_context.thread_id,
                user_id=original_context.user_id,
                retry_count=original_context.retry_count,
                max_retries=original_context.max_retries
            )
        
        # Create new context if agent context not available
        thread_id = extract_thread_id(state, run_id)
        return AgentExecutionContext(
            agent_name=f"ToolExecutor[{tool_name}]",
            run_id=run_id,
            thread_id=thread_id,
            user_id=getattr(state, 'user_id', run_id)
        )
    
    # Helper methods for contextual information
    
    def _get_tool_purpose(self, tool_name: str, tool_input: Any) -> str:
        """Generate contextual purpose description for tools."""
        purpose_mappings = {
            "search": "Finding relevant information",
            "query": "Retrieving data from database",
            "analyze": "Performing data analysis",
            "generate": "Creating content or reports",
            "validate": "Checking data integrity",
            "optimize": "Improving performance",
            "export": "Exporting results",
            "import": "Loading external data",
            "llm": "Processing with AI model",
            "calculation": "Computing metrics",
            "transformation": "Converting data format"
        }
        
        for pattern, purpose in purpose_mappings.items():
            if pattern.lower() in tool_name.lower():
                return purpose
        
        return f"Executing {tool_name} operation"
    
    def _estimate_tool_duration(self, tool_name: str, tool_input: Any) -> int:
        """Estimate tool execution duration in milliseconds."""
        duration_estimates = {
            "search": 3000,
            "query": 2000,
            "analyze": 15000,
            "generate": 8000,
            "validate": 2000,
            "optimize": 30000,
            "export": 5000,
            "import": 10000,
            "llm": 12000,
            "calculation": 5000,
            "transformation": 3000
        }
        
        for pattern, duration in duration_estimates.items():
            if pattern.lower() in tool_name.lower():
                return duration
        
        return 5000  # Default 5 seconds
    
    def _create_parameters_summary(self, tool_input: Any) -> str:
        """Create user-friendly summary of tool parameters."""
        if not tool_input:
            return "No parameters"
        
        try:
            # Handle different tool input formats
            if hasattr(tool_input, "model_dump"):
                params = tool_input.model_dump()
            elif hasattr(tool_input, "__dict__"):
                params = tool_input.__dict__
            elif isinstance(tool_input, dict):
                params = tool_input
            else:
                return str(tool_input)[:100]
            
            # Extract key information
            summary_parts = []
            
            if "query" in params:
                summary_parts.append(f"Query: {str(params['query'])[:50]}")
            if "table_name" in params:
                summary_parts.append(f"Table: {params['table_name']}")
            if "limit" in params:
                summary_parts.append(f"Limit: {params['limit']}")
            if "filters" in params and params["filters"]:
                summary_parts.append(f"Filters: {len(params['filters'])} applied")
            
            if summary_parts:
                return "; ".join(summary_parts)
            else:
                key_items = list(params.items())[:3]
                return "; ".join([f"{k}: {str(v)[:30]}" for k, v in key_items])
            
        except Exception:
            return "Complex parameters"
    
    # Response creation methods
    
    def _create_success_result(self, tool_input: 'ToolInput', result: Any) -> 'ToolResult':
        """Create successful tool result."""
        from netra_backend.app.schemas.tool import (
            SimpleToolPayload,
            ToolResult,
            ToolStatus,
        )
        
        payload = SimpleToolPayload(result=result)
        return ToolResult(tool_input=tool_input, status=ToolStatus.SUCCESS, payload=payload)
    
    def _create_error_result(self, tool_input: 'ToolInput', message: str) -> 'ToolResult':
        """Create error result."""
        from netra_backend.app.schemas.tool import ToolResult, ToolStatus
        
        return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=message)
    
    def _create_success_response(self, result: Any, tool_name: str, run_id: str) -> Dict[str, Any]:
        """Create successful tool execution response."""
        return {
            "success": True,
            "result": result,
            "metadata": {"tool_name": tool_name, "run_id": run_id}
        }
    
    def _create_error_response(self, error: Exception, tool_name: str, run_id: str) -> Dict[str, Any]:
        """Create error response for tool execution failure."""
        return {
            "success": False,
            "error": str(error),
            "metadata": {"tool_name": tool_name, "run_id": run_id}
        }
    
    def _create_success_tool_response(self, result: Any, tool_name: str) -> 'ToolExecuteResponse':
        """Create successful tool execution response for interface."""
        from netra_backend.app.schemas.tool import ToolExecuteResponse
        
        return ToolExecuteResponse(
            success=True,
            data=result,
            message="Tool executed successfully",
            metadata={"tool_name": tool_name}
        )
    
    def _create_error_tool_response(self, error: Exception, tool_name: str) -> 'ToolExecuteResponse':
        """Create error tool execution response for interface."""
        from netra_backend.app.schemas.tool import ToolExecuteResponse
        
        return ToolExecuteResponse(
            success=False,
            data=None,
            message=str(error),
            metadata={"tool_name": tool_name}
        )
    
    # Metrics methods
    
    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get execution metrics for monitoring."""
        return {
            **self._execution_metrics,
            'active_executions': len(self._active_executions),
            'active_tools': list(self._active_executions.keys())
        }
    
    async def send_progress_update(
        self,
        context: 'AgentExecutionContext',
        tool_name: str,
        progress_percentage: float,
        status_message: str = None
    ) -> None:
        """Send granular progress update for long-running tools."""
        if not self.websocket_notifier or not context:
            return
        
        try:
            estimated_remaining = self._calculate_remaining_time(tool_name, progress_percentage)
            
            await self.websocket_notifier.send_periodic_update(
                context,
                operation_name=tool_name,
                progress_percentage=progress_percentage,
                status_message=status_message,
                estimated_remaining_ms=estimated_remaining,
                current_step=f"Processing: {progress_percentage:.0f}% complete"
            )
        except Exception as e:
            logger.warning(f"Failed to send progress update: {e}")
    
    def _calculate_remaining_time(self, tool_name: str, progress_percentage: float) -> int:
        """Calculate estimated remaining time based on progress."""
        if progress_percentage <= 0 or progress_percentage >= 100:
            return 0
        
        # Find active execution for this tool
        for exec_id, exec_info in self._active_executions.items():
            if exec_info['tool_name'] == tool_name:
                elapsed = time.time() - exec_info['start_time']
                total_estimated = elapsed / (progress_percentage / 100)
                remaining = total_estimated - elapsed
                return int(remaining * 1000)
        
        # Fallback estimation
        estimated_total = self._estimate_tool_duration(tool_name, None)
        remaining = estimated_total * (1 - progress_percentage / 100)
        return int(remaining)


def enhance_tool_dispatcher_with_notifications(tool_dispatcher, websocket_manager):
    """Enhance existing tool dispatcher with unified execution engine.
    
    This function replaces the dispatcher's executor with the unified engine.
    """
    if hasattr(tool_dispatcher, 'executor'):
        # Check if already enhanced
        if isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine):
            logger.debug("Tool dispatcher already using unified execution engine")
            return tool_dispatcher
        
        # Get permission service if available
        permission_service = None
        if hasattr(tool_dispatcher.executor, 'permission_service'):
            permission_service = tool_dispatcher.executor.permission_service
        
        # Replace executor with unified engine
        unified_executor = UnifiedToolExecutionEngine(websocket_manager, permission_service)
        
        # Preserve any existing core engine reference
        if hasattr(tool_dispatcher.executor, '_core_engine'):
            # The unified engine doesn't need a separate core engine
            pass
        
        # Store original executor for testing/validation
        tool_dispatcher._original_executor = tool_dispatcher.executor
        tool_dispatcher.executor = unified_executor
        
        # Mark as enhanced for validation
        tool_dispatcher._websocket_enhanced = True
        
        logger.info("Enhanced tool dispatcher with unified execution engine")
    else:
        logger.warning("Tool dispatcher does not have executor attribute")
    
    return tool_dispatcher