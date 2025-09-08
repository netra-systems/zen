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
import os
import psutil
import time
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.tool_models import ToolExecutionResult, UnifiedTool
# WebSocket exceptions module was deleted - using standard exceptions
from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.websocket_notification_monitor import get_websocket_notification_monitor
from shared.isolated_environment import IsolatedEnvironment

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
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
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

logger = central_logger.get_logger(__name__)


async def enhance_tool_dispatcher_with_notifications(
    tool_dispatcher,
    websocket_manager=None,
    enable_notifications=True
):
    """
    Enhance tool dispatcher with WebSocket notifications.
    
    This function replaces the tool dispatcher's executor with a 
    UnifiedToolExecutionEngine that has WebSocket notification capabilities.
    
    Args:
        tool_dispatcher: The ToolDispatcher instance to enhance
        websocket_manager: Optional WebSocket manager for notifications
        enable_notifications: Whether to enable notifications (default True)
    
    Returns:
        The enhanced tool dispatcher
    """
    # Check if already enhanced to prevent double enhancement
    if hasattr(tool_dispatcher, '_websocket_enhanced') and tool_dispatcher._websocket_enhanced:
        logger.debug("Tool dispatcher already enhanced with WebSocket notifications")
        return tool_dispatcher
    
    # Create enhanced executor with WebSocket support
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    
    # Create WebSocket bridge if manager provided
    websocket_bridge = None
    if websocket_manager and enable_notifications:
        websocket_bridge = AgentWebSocketBridge()
        # CRITICAL FIX: Use the correct private member name
        websocket_bridge._websocket_manager = websocket_manager
    
    # Replace executor with enhanced version
    enhanced_executor = UnifiedToolExecutionEngine(
        websocket_bridge=websocket_bridge,
        permission_service=getattr(tool_dispatcher.executor, 'permission_service', None) if hasattr(tool_dispatcher, 'executor') else None
    )
    
    # Store reference to websocket manager for compatibility
    if websocket_manager:
        enhanced_executor.websocket_manager = websocket_manager
    
    # Replace the executor
    tool_dispatcher.executor = enhanced_executor
    
    # Mark as enhanced to prevent double enhancement
    tool_dispatcher._websocket_enhanced = True
    
    logger.info("✅ Tool dispatcher enhanced with WebSocket notifications")
    return tool_dispatcher


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
        websocket_bridge: Optional['AgentWebSocketBridge'] = None,
        permission_service: Optional['ToolPermissionService'] = None
    ):
        """Initialize unified tool execution engine."""
        self.websocket_bridge = websocket_bridge
        # Compatibility alias for tests expecting websocket_notifier
        self.websocket_notifier = websocket_bridge
        self.permission_service = permission_service
        
        # Initialize monitoring system
        self.notification_monitor = get_websocket_notification_monitor()
        
        # Security and resource management
        self.env = IsolatedEnvironment()
        self.default_timeout = float(self.env.get('AGENT_DEFAULT_TIMEOUT', '30.0'))
        self.max_memory_mb = int(self.env.get('AGENT_MAX_MEMORY_MB', '512'))
        self.max_concurrent_per_user = int(self.env.get('AGENT_MAX_CONCURRENT_PER_USER', '10'))
        self.rate_limit_per_minute = int(self.env.get('AGENT_RATE_LIMIT_PER_MINUTE', '100'))
        
        # Metrics tracking
        self._active_executions: Dict[str, Dict] = {}
        self._user_execution_counts: Dict[str, int] = {}
        self._user_request_timestamps: Dict[str, List[float]] = {}
        self._execution_metrics = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'timeout_executions': 0,
            'security_violations': 0,
            'total_duration_ms': 0
        }
        
        # Process monitoring
        self._process = psutil.Process(os.getpid())
        
        logger.info(f"🔒 Security controls initialized: timeout={self.default_timeout}s, memory={self.max_memory_mb}MB, concurrent={self.max_concurrent_per_user}")
    
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
        
        # CRITICAL: Always attempt to send executing notification
        await self._send_tool_executing(context, tool_name, tool_input)
        
        try:
            # Execute tool by interface type
            result = await self._run_tool_by_interface(tool, kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            # Update metrics
            self._execution_metrics['successful_executions'] += 1
            
            # CRITICAL: Always attempt to send completed notification
            await self._send_tool_completed(
                context, tool_name, result, duration_ms, "success"
            )
            
            return self._create_success_result(tool_input, result)
            
        except asyncio.TimeoutError as te:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Tool {tool_name} timed out after {duration_ms:.0f}ms")
            
            # Update metrics
            self._execution_metrics['failed_executions'] += 1
            
            # CRITICAL: Always attempt to send timeout notification
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
            
            # CRITICAL: Always attempt to send error notification
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
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            # Generate fallback thread_id for tool execution without context using SSOT
            base_thread_id = UnifiedIDManager.generate_thread_id()
            fallback_thread_id = f"tool_execution_{tool_name}_{base_thread_id}"
            run_id = UnifiedIDManager.generate_run_id(fallback_thread_id)
            logger.warning(f"No run_id provided for {tool_name}, generated: {run_id}")
        
        start_time = time.time()
        execution_id = f"{run_id}_{tool_name}_{int(start_time * 1000)}"
        
        # Get or create context for notifications
        context = None
        if self.websocket_bridge:
            context = self._get_or_create_context(state, run_id, tool_name)
            await self._send_tool_executing(context, tool_name, parameters)
        
        try:
            # Execute by tool type
            result = await self._execute_by_tool_type(tool, parameters, state, run_id)
            duration_ms = (time.time() - start_time) * 1000
            
            # Send completed notification
            if context and self.websocket_bridge:
                await self._send_tool_completed(
                    context, tool_name, result, duration_ms, "success"
                )
            
            logger.debug(f"Tool {tool_name} completed in {duration_ms:.0f}ms")
            return self._create_success_response(result, tool_name, run_id)
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_type = type(e).__name__
            logger.error(f"Tool {tool_name} failed after {duration_ms:.0f}ms with {error_type}: {e}")
            
            # CRITICAL: Always attempt to send error notification
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
        # Remove context from kwargs before passing to tool
        tool_kwargs = {k: v for k, v in kwargs.items() if k != 'context'}
        
        # For BaseTool instances, they expect specific arguments
        from langchain_core.tools import BaseTool
        if isinstance(tool, BaseTool):
            # BaseTool.arun expects the input as a single argument or dict
            # For our custom tools, we need to pass context via kwargs
            context = kwargs.get('context')
            if tool_kwargs:
                # If there are parameters, pass them as tool input, context via kwargs
                return await tool.arun(tool_kwargs, context=context)
            else:
                # If no parameters, pass empty dict, context via kwargs
                return await tool.arun({}, context=context)
        elif hasattr(tool, 'arun'):
            return await tool.arun(**tool_kwargs)
        elif asyncio.iscoroutinefunction(tool):
            return await tool(**tool_kwargs)
        else:
            return tool(**tool_kwargs)
    
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
        """Send tool executing notification via AgentWebSocketBridge."""
        # CRITICAL: Always attempt to notify, with fallback
        if not context:
            error_msg = f"Tool {tool_name} executing without context - USER WILL NOT SEE PROGRESS"
            logger.critical(f"🚨 CONTEXT VALIDATION FAILURE: {error_msg}")
            
            # MONITORING: Track failure
            self.notification_monitor.track_silent_failure_detected(
                user_id="unknown",
                thread_id="unknown", 
                context=error_msg
            )
            
            # LOUD FAILURE: Raise exception instead of silent return
            raise ValueError(
                validation_error="Missing execution context",
                user_id="unknown"
            )
            
        if not self.websocket_bridge:
            error_msg = f"Tool {tool_name} executing for run_id {context.run_id} - EVENTS WILL BE LOST"
            logger.critical(f"🚨 WEBSOCKET BRIDGE UNAVAILABLE: {error_msg}")
            logger.critical(f"🚨 Thread {context.thread_id} will not receive any tool progress notifications")
            
            # MONITORING: Track failure
            self.notification_monitor.track_silent_failure_detected(
                user_id=context.user_id,
                thread_id=context.thread_id,
                context=error_msg
            )
            
            # LOUD FAILURE: Raise exception instead of silent return
            error_details = f"operation=tool_executing({tool_name}), user_id={context.user_id}, thread_id={context.thread_id}"
            raise ConnectionError(f"WebSocket notification failed: {error_details}")
        
        # MONITORING: Track notification attempt
        correlation_id = self.notification_monitor.track_notification_attempted(
            user_id=context.user_id,
            thread_id=context.thread_id, 
            run_id=context.run_id,
            agent_name=getattr(context, 'agent_name', 'ToolDispatcher'),
            tool_name=tool_name,
            connection_id=getattr(context, 'connection_id', None)
        )
        
        try:
            # Extract contextual information
            params_summary = self._create_parameters_summary(tool_input)
            
            # DEFENSIVE: Validate bridge has required method before calling
            if not hasattr(self.websocket_bridge, 'notify_tool_executing'):
                logger.critical(f"🚨 BRIDGE MISSING METHOD: notify_tool_executing not found")
                
                # MONITORING: Track method missing failure
                self.notification_monitor.track_notification_failed(
                    correlation_id, "Bridge missing notify_tool_executing method", "method_missing"
                )
                return
            
            start_time = time.time()
            result = await self.websocket_bridge.notify_tool_executing(
                run_id=context.run_id,
                agent_name=getattr(context, 'agent_name', 'ToolDispatcher'),
                tool_name=tool_name,
                parameters={"summary": params_summary} if params_summary else None
            )
            delivery_time_ms = (time.time() - start_time) * 1000
            
            # DEFENSIVE: Check if notification succeeded
            if result is False:
                logger.warning(f"⚠️ Tool executing notification failed for {tool_name} (returned False)")
                
                # MONITORING: Track notification failure
                self.notification_monitor.track_notification_failed(
                    correlation_id, "WebSocket bridge returned False", "bridge_rejected"
                )
            else:
                # MONITORING: Track successful delivery
                self.notification_monitor.track_notification_delivered(correlation_id, delivery_time_ms)
                
        except Exception as e:
            logger.error(f"🚨 EXCEPTION in tool_executing notification for {tool_name}: {e}")
            logger.error("🚨 User will not see tool execution start - check WebSocket connectivity")
            
            # MONITORING: Track notification exception
            self.notification_monitor.track_notification_failed(
                correlation_id, str(e), type(e).__name__
            )
    
    async def _send_tool_completed(
        self,
        context: 'AgentExecutionContext',
        tool_name: str,
        result: Any,
        duration_ms: float,
        status: str,
        error_type: str = None
    ) -> None:
        """Send tool completed notification via AgentWebSocketBridge."""
        # CRITICAL: Always attempt to notify, with fallback
        if not context:
            error_msg = f"Tool {tool_name} completed without context - USER WILL NOT SEE RESULTS"
            logger.critical(f"🚨 CONTEXT VALIDATION FAILURE: {error_msg}")
            
            # MONITORING: Track failure
            self.notification_monitor.track_silent_failure_detected(
                user_id="unknown",
                thread_id="unknown",
                context=error_msg
            )
            
            # LOUD FAILURE: Raise exception
            raise ValueError(
                validation_error="Missing execution context for tool completion",
                user_id="unknown"
            )
            
        if not self.websocket_bridge:
            error_msg = f"Tool {tool_name} completed for run_id {context.run_id} - RESULTS WILL BE LOST"
            logger.critical(f"🚨 WEBSOCKET BRIDGE UNAVAILABLE: {error_msg}")
            logger.critical(f"🚨 Thread {context.thread_id} status: {status}, duration: {duration_ms:.0f}ms")
            
            # MONITORING: Track failure
            self.notification_monitor.track_silent_failure_detected(
                user_id=context.user_id,
                thread_id=context.thread_id,
                context=error_msg
            )
            
            # LOUD FAILURE: Raise exception
            error_details = f"operation=tool_completed({tool_name}), user_id={context.user_id}, thread_id={context.thread_id}"
            raise ConnectionError(f"WebSocket notification failed: {error_details}")
        
        # MONITORING: Track notification attempt  
        correlation_id = self.notification_monitor.track_notification_attempted(
            user_id=context.user_id,
            thread_id=context.thread_id,
            run_id=context.run_id,
            agent_name=getattr(context, 'agent_name', 'ToolDispatcher'),
            tool_name=tool_name,
            connection_id=getattr(context, 'connection_id', None)
        )
        
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
            
            # DEFENSIVE: Validate bridge has required method before calling
            if not hasattr(self.websocket_bridge, 'notify_tool_completed'):
                logger.critical(f"🚨 BRIDGE MISSING METHOD: notify_tool_completed not found")
                
                # MONITORING: Track method missing failure
                self.notification_monitor.track_notification_failed(
                    correlation_id, "Bridge missing notify_tool_completed method", "method_missing"
                )
                return
            
            start_time = time.time()
            notification_result = await self.websocket_bridge.notify_tool_completed(
                run_id=context.run_id,
                agent_name=getattr(context, 'agent_name', 'ToolDispatcher'),
                tool_name=tool_name,
                result=result_dict,
                execution_time_ms=duration_ms
            )
            notification_time_ms = (time.time() - start_time) * 1000
            
            # DEFENSIVE: Check if notification succeeded
            if notification_result is False:
                logger.warning(f"⚠️ Tool completed notification failed for {tool_name} (returned False)")
                
                # MONITORING: Track notification failure
                self.notification_monitor.track_notification_failed(
                    correlation_id, "WebSocket bridge returned False for completion", "bridge_rejected"
                )
            else:
                # MONITORING: Track successful delivery
                self.notification_monitor.track_notification_delivered(correlation_id, notification_time_ms)
                
        except Exception as e:
            logger.error(f"🚨 EXCEPTION in tool_completed notification for {tool_name}: {e}")
            logger.error("🚨 User will not see tool completion - check WebSocket connectivity")
            
            # MONITORING: Track notification exception
            self.notification_monitor.track_notification_failed(
                correlation_id, str(e), type(e).__name__
            )
    
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
                agent_name=f"{original_getattr(context, 'agent_name', 'ToolDispatcher')}[{tool_name}]",
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
        if not self.websocket_bridge or not context:
            return
        
        try:
            estimated_remaining = self._calculate_remaining_time(tool_name, progress_percentage)
            
            progress_data = {
                "percentage": progress_percentage,
                "message": status_message or f"Processing: {progress_percentage:.0f}% complete",
                "estimated_remaining_ms": estimated_remaining,
                "current_step": f"Processing: {progress_percentage:.0f}% complete"
            }
            
            await self.websocket_bridge.notify_progress_update(
                run_id=context.run_id,
                agent_name=getattr(context, 'agent_name', 'ToolDispatcher'),
                progress=progress_data
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
    
    async def force_cleanup_user_executions(self, user_id: str) -> int:
        """Force cleanup of stuck executions for a user (emergency recovery).
        
        This method addresses the agent death scenario by providing
        a way to clean up stuck executions that never properly finished.
        
        Returns:
            Number of executions cleaned up
        """
        cleanup_count = 0
        executions_to_remove = []
        
        for execution_id, exec_info in self._active_executions.items():
            if exec_info.get('user_id') == user_id:
                # Check if execution has been running too long
                runtime = time.time() - exec_info['start_time']
                if runtime > self.default_timeout * 3:  # 3x normal timeout
                    executions_to_remove.append(execution_id)
                    cleanup_count += 1
        
        # Remove stuck executions
        for execution_id in executions_to_remove:
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]
                logger.warning(f"🧨 Cleaned up stuck execution: {execution_id}")
        
        # Reset user execution count
        if user_id in self._user_execution_counts:
            old_count = self._user_execution_counts[user_id]
            del self._user_execution_counts[user_id]
            logger.warning(f"🧨 Reset user execution count for {user_id}: {old_count} -> 0")
        
        if cleanup_count > 0:
            logger.info(f"🧨 Emergency cleanup completed for user {user_id}: {cleanup_count} executions cleaned")
        
        return cleanup_count
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check that detects actual processing capability.
        
        This addresses the health service blindness described in the bug report
        by checking not just if the service is running, but if it can actually
        process agent requests successfully.
        """
        status = "healthy"
        issues = []
        
        try:
            # Check memory usage
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            if memory_mb > self.max_memory_mb * 0.9:  # 90% of limit
                status = "degraded"
                issues.append(f"High memory usage: {memory_mb:.1f}MB/{self.max_memory_mb}MB")
            
            if memory_mb > self.max_memory_mb:
                status = "unhealthy"
                issues.append(f"Memory limit exceeded: {memory_mb:.1f}MB/{self.max_memory_mb}MB")
            
            # Check for stuck executions
            stuck_count = 0
            now = time.time()
            
            for exec_info in self._active_executions.values():
                runtime = now - exec_info['start_time']
                if runtime > self.default_timeout * 2:  # 2x normal timeout
                    stuck_count += 1
            
            if stuck_count > 0:
                status = "degraded"
                issues.append(f"Stuck executions detected: {stuck_count}")
            
            # Check security violations
            if self._execution_metrics['security_violations'] > 10:
                status = "degraded"
                issues.append(f"High security violations: {self._execution_metrics['security_violations']}")
            
            # Test basic execution capability
            try:
                test_start = time.time()
                async with asyncio.timeout(5.0):  # 5 second test timeout
                    # Simple test execution
                    test_result = "test_passed"
                test_duration = time.time() - test_start
                
                if test_duration > 2.0:  # Should complete quickly
                    status = "degraded"
                    issues.append(f"Slow processing capability: {test_duration:.1f}s")
                    
            except asyncio.TimeoutError:
                status = "unhealthy"
                issues.append("Processing capability test timed out")
            except Exception as e:
                status = "unhealthy"
                issues.append(f"Processing capability test failed: {e}")
            
        except Exception as e:
            status = "unhealthy"
            issues.append(f"Health check failed: {e}")
        
        return {
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "issues": issues,
            "metrics": await self.get_security_status(),
            "can_process_agents": status != "unhealthy",
            "processing_capability_verified": "Processing capability test" not in str(issues)
        }
    
    async def emergency_shutdown_all_executions(self) -> Dict[str, Any]:
        """Emergency shutdown of all active executions.
        
        This is a last resort recovery mechanism for when the system
        is overwhelmed or in an inconsistent state.
        
        Returns:
            Dictionary with shutdown statistics
        """
        logger.critical("🚨 EMERGENCY SHUTDOWN: Terminating all active executions")
        
        shutdown_count = len(self._active_executions)
        user_counts = self._user_execution_counts.copy()
        
        # Clear all tracking
        self._active_executions.clear()
        self._user_execution_counts.clear()
        self._user_request_timestamps.clear()
        
        # Reset metrics except for permanent counters
        self._execution_metrics['failed_executions'] += shutdown_count
        
        logger.critical(f"🚨 Emergency shutdown completed: {shutdown_count} executions terminated")
        
        return {
            "shutdown_executions": shutdown_count,
            "affected_users": len(user_counts),
            "user_counts": user_counts,
            "timestamp": datetime.now(UTC).isoformat(),
            "reason": "emergency_shutdown"
        }


# BACKWARD COMPATIBILITY: EnhancedToolExecutionEngine alias
# This maintains backward compatibility per SSOT consolidation report
# EnhancedToolExecutionEngine is a thin wrapper (alias) for UnifiedToolExecutionEngine
# See: reports/TOOL_EXECUTION_CONSOLIDATION_REPORT.md - "backward compatibility wrapper"
EnhancedToolExecutionEngine = UnifiedToolExecutionEngine

logger.debug("✅ EnhancedToolExecutionEngine registered as backward compatibility alias for UnifiedToolExecutionEngine")

