"""RequestScopedToolDispatcher for per-request isolated tool execution.

This module provides the RequestScopedToolDispatcher class that eliminates global state
issues by creating isolated tool execution environments per request.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & User Isolation
- Value Impact: Enables safe concurrent user handling with zero tool execution context leakage
- Strategic Impact: Foundation for reliable multi-tenant production deployment

Key Architecture Principles:
- Per-request isolation (NO global state)
- Bound to specific UserExecutionContext
- Uses isolated UnifiedToolExecutionEngine per request
- WebSocket events routed to correct user only
- Automatic resource cleanup after request completion
- Thread-safe with comprehensive error handling

The RequestScopedToolDispatcher replaces the singleton ToolDispatcher pattern 
for concurrent user scenarios while maintaining full API compatibility.
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from contextlib import asynccontextmanager

if TYPE_CHECKING:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.registry.universal_registry import ToolRegistry
from netra_backend.app.agents.tool_dispatcher_validation import ToolValidator
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.websocket_core import (
    WebSocketEventEmitter,
)
# WebSocketEventEmitterFactory is actually UnifiedWebSocketEmitter
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as WebSocketEventEmitterFactory
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.tool import (
    SimpleToolPayload,
    ToolInput,
    ToolResult,
    ToolStatus,
)

logger = central_logger.get_logger(__name__)


class RequestScopedToolDispatcher:
    """Per-request tool dispatcher with complete user isolation.
    
    This dispatcher is created per request and contains NO GLOBAL STATE.
    Each instance handles tool execution for a single user request with:
    - Request-scoped tool executor (UnifiedToolExecutionEngine)
    - Isolated WebSocket event emission (WebSocketEventEmitter)
    - User-specific tool execution tracking
    - Automatic resource cleanup
    - Complete isolation between concurrent users
    
    Key Design Principles:
    - NO shared state between instances
    - Each request gets its own dispatcher instance
    - All tool execution state is request-scoped and cleaned up
    - UserExecutionContext drives all isolation
    - WebSocket events routed to correct user only
    - Fail-fast on invalid contexts
    
    Business Value:
    - Prevents cross-user tool execution leakage
    - Enables reliable concurrent user tool execution
    - Maintains tool functionality while ensuring user privacy
    - Eliminates race conditions from singleton pattern
    """
    
    def __init__(
        self,
        user_context: UserExecutionContext,
        tools: List[Any] = None,
        websocket_emitter: Optional[WebSocketEventEmitter] = None
    ):
        """Initialize per-request tool dispatcher.
        
        Args:
            user_context: Immutable user execution context for this request
            tools: Optional list of tools to register initially
            websocket_emitter: Optional WebSocket event emitter for this request
            
        Raises:
            TypeError: If user_context is not a UserExecutionContext
            ValueError: If any required parameters are invalid
        """
        # Validate user context immediately
        self.user_context = validate_user_context(user_context)
        
        # Request-scoped metadata (must be created first)
        self.dispatcher_id = f"{user_context.user_id}_{user_context.run_id}_{int(time.time()*1000)}"
        self.created_at = datetime.now(timezone.utc)
        self._is_active = True
        
        # Initialize components with request isolation
        self._init_components(websocket_emitter)
        self._register_initial_tools(tools)
        
        # Request-scoped metrics
        self._metrics = {
            'tools_executed': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_execution_time_ms': 0,
            'last_execution_time': None,
            'created_at': self.created_at,
            'context_id': user_context.get_correlation_id()
        }
        
        logger.info(f"✅ Created RequestScopedToolDispatcher {self.dispatcher_id} for user {user_context.user_id}")
        
        # Verify user context isolation
        try:
            user_context.verify_isolation()
            logger.debug(f"✅ ISOLATION VERIFIED: {self._get_log_prefix()}")
        except Exception as e:
            logger.error(f"🚨 ISOLATION VIOLATION: {self._get_log_prefix()} - {e}")
            raise ValueError(f"User context failed isolation verification: {e}")
    
    def _get_log_prefix(self) -> str:
        """Get consistent logging prefix for this dispatcher instance."""
        return f"[{self.user_context.get_correlation_id()}]"
    
    def _ensure_not_disposed(self) -> None:
        """Ensure dispatcher hasn't been disposed."""
        if not self._is_active:
            raise RuntimeError(f"RequestScopedToolDispatcher {self._get_log_prefix()} has been disposed")
    
    def _init_components(self, websocket_emitter: Optional[WebSocketEventEmitter]) -> None:
        """Initialize dispatcher components with request isolation."""
        # Request-scoped tool registry
        self.registry = ToolRegistry()
        
        # Store WebSocket emitter for this request
        self.websocket_emitter = websocket_emitter
        
        # Create request-scoped tool executor
        # NOTE: We create a "compatibility bridge" that adapts WebSocketEventEmitter 
        # to the AgentWebSocketBridge interface expected by UnifiedToolExecutionEngine
        websocket_bridge = self._create_websocket_bridge_adapter() if websocket_emitter else None
        
        self.executor = UnifiedToolExecutionEngine(websocket_bridge=websocket_bridge)
        
        # Request-scoped validator
        self.validator = ToolValidator()
        
        logger.debug(f"Initialized components for RequestScopedToolDispatcher {self.dispatcher_id}")
    
    def _create_websocket_bridge_adapter(self) -> 'WebSocketBridgeAdapter':
        """Create adapter from WebSocketEventEmitter to AgentWebSocketBridge interface.
        
        This adapter allows UnifiedToolExecutionEngine to work with the new
        WebSocketEventEmitter while maintaining backward compatibility.
        """
        return WebSocketBridgeAdapter(self.websocket_emitter, self.user_context)
    
    def _register_initial_tools(self, tools: List[Any]) -> None:
        """Register initial tools if provided."""
        if tools:
            self.registry.register_tools(tools)
    
    @property
    def tools(self) -> Dict[str, Any]:
        """Expose tools registry for compatibility."""
        return self.registry.tools
    
    @property
    def has_websocket_support(self) -> bool:
        """Check if WebSocket support is enabled."""
        return self.websocket_emitter is not None
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool exists in this request's registry."""
        self._ensure_not_disposed()
        return self.registry.has_tool(tool_name)
    
    def register_tool(self, tool_name: str, tool_func, description: str = None) -> None:
        """Register a tool function with this request's dispatcher."""
        self._ensure_not_disposed()
        
        from langchain_core.tools import BaseTool
        
        # Create a simple tool wrapper if needed
        if not isinstance(tool_func, BaseTool):
            desc = description or f"Dynamic tool: {tool_name}"
            
            class DynamicTool(BaseTool):
                name: str = tool_name
                description: str = desc
                
                def _run(self, *args, **kwargs):
                    return tool_func(*args, **kwargs)
                
                async def _arun(self, *args, **kwargs):
                    if hasattr(tool_func, '__call__'):
                        import asyncio
                        if asyncio.iscoroutinefunction(tool_func):
                            return await tool_func(*args, **kwargs)
                        else:
                            return tool_func(*args, **kwargs)
                    return tool_func(*args, **kwargs)
            
            tool_func = DynamicTool()
        
        self.registry.register_tool(tool_func)
        logger.debug(f"Registered tool {tool_name} in {self._get_log_prefix()}")
    
    async def dispatch(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """Dispatch tool execution with complete request isolation."""
        self._ensure_not_disposed()
        
        start_time = time.time()
        tool_input = self._create_tool_input(tool_name, kwargs)
        
        # Validate tool exists
        if not self.has_tool(tool_name):
            return self._create_error_result(tool_input, f"Tool {tool_name} not found")
        
        # Update metrics
        self._metrics['tools_executed'] += 1
        self._metrics['last_execution_time'] = datetime.now(timezone.utc)
        
        try:
            # Execute tool via isolated executor
            tool = self.registry.get_tool(tool_name)
            result = await self.executor.execute_tool_with_input(tool_input, tool, kwargs)
            
            # Update success metrics
            execution_time_ms = (time.time() - start_time) * 1000
            self._metrics['successful_executions'] += 1
            self._metrics['total_execution_time_ms'] += execution_time_ms
            
            logger.debug(f"✅ Tool {tool_name} executed successfully in {execution_time_ms:.1f}ms {self._get_log_prefix()}")
            return result
            
        except Exception as e:
            # Update failure metrics
            execution_time_ms = (time.time() - start_time) * 1000
            self._metrics['failed_executions'] += 1
            self._metrics['total_execution_time_ms'] += execution_time_ms
            
            logger.error(f"🚨 Tool {tool_name} failed in {execution_time_ms:.1f}ms {self._get_log_prefix()}: {e}")
            return self._create_error_result(tool_input, f"Tool execution failed: {e}")
    
    async def dispatch_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> Dict[str, Any]:
        """Dispatch tool with state - method expected by sub-agents."""
        self._ensure_not_disposed()
        
        # Validate run_id matches our context for security
        if run_id != self.user_context.run_id:
            logger.error(f"🚨 RUN_ID MISMATCH: {self._get_log_prefix()} expected {self.user_context.run_id}, got {run_id}")
            return self._create_tool_not_found_response(tool_name, run_id)
        
        if not self.has_tool(tool_name):
            return self._create_tool_not_found_response(tool_name, run_id)
        
        start_time = time.time()
        
        try:
            # Execute via isolated executor with state
            tool = self.registry.get_tool(tool_name)
            result = await self.executor.execute_with_state(tool, tool_name, parameters, state, run_id)
            
            # Update metrics
            execution_time_ms = (time.time() - start_time) * 1000
            self._metrics['successful_executions'] += 1
            self._metrics['total_execution_time_ms'] += execution_time_ms
            
            return result
            
        except Exception as e:
            # Update failure metrics
            execution_time_ms = (time.time() - start_time) * 1000
            self._metrics['failed_executions'] += 1
            self._metrics['total_execution_time_ms'] += execution_time_ms
            
            logger.error(f"🚨 Tool dispatch failed {self._get_log_prefix()}: {e}")
            return {
                "success": False,
                "error": str(e),
                "metadata": {"tool_name": tool_name, "run_id": run_id}
            }
    
    def _create_tool_input(self, tool_name: str, kwargs: Dict[str, Any]) -> ToolInput:
        """Create tool input from parameters."""
        return ToolInput(tool_name=tool_name, kwargs=kwargs)
    
    def _create_error_result(self, tool_input: ToolInput, message: str) -> ToolResult:
        """Create error result for tool execution."""
        return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=message)
    
    def _create_tool_not_found_response(self, tool_name: str, run_id: str) -> Dict[str, Any]:
        """Create response for tool not found scenario."""
        logger.warning(f"Tool {tool_name} not found for run_id {run_id} in {self._get_log_prefix()}")
        return {
            "success": False,
            "error": f"Tool {tool_name} not found"
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics for this request."""
        self._ensure_not_disposed()
        
        # Calculate derived metrics
        success_rate = 0.0
        avg_execution_time = 0.0
        
        total_executions = self._metrics['successful_executions'] + self._metrics['failed_executions']
        if total_executions > 0:
            success_rate = self._metrics['successful_executions'] / total_executions
            avg_execution_time = self._metrics['total_execution_time_ms'] / total_executions
        
        return {
            **self._metrics,
            'dispatcher_id': self.dispatcher_id,
            'user_id': self.user_context.user_id,
            'run_id': self.user_context.run_id,
            'success_rate': success_rate,
            'avg_execution_time_ms': avg_execution_time,
            'uptime_seconds': (datetime.now(timezone.utc) - self.created_at).total_seconds(),
            'total_tools_registered': len(self.registry.tools),
            'has_websocket_support': self.has_websocket_support,
            'is_active': self._is_active
        }
    
    def get_context(self) -> UserExecutionContext:
        """Get the bound user execution context."""
        return self.user_context
    
    async def cleanup(self) -> None:
        """Clean up dispatcher resources.
        
        This should be called when the request is complete to ensure
        proper resource cleanup and prevent memory leaks.
        """
        if not self._is_active:
            return
        
        try:
            logger.info(f"Cleaning up RequestScopedToolDispatcher {self.dispatcher_id}")
            
            # Dispose WebSocket emitter if we have one
            if self.websocket_emitter:
                try:
                    await self.websocket_emitter.dispose()
                except Exception as e:
                    logger.error(f"Error disposing WebSocket emitter: {e}")
            
            # Clear all state
            self.registry.tools.clear()
            self._metrics.clear()
            
            # Mark as inactive
            self._is_active = False
            
            logger.info(f"✅ Cleaned up RequestScopedToolDispatcher {self.dispatcher_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up RequestScopedToolDispatcher {self.dispatcher_id}: {e}")
            raise
    
    def is_active(self) -> bool:
        """Check if this dispatcher is still active."""
        return self._is_active
    
    async def __aenter__(self) -> 'RequestScopedToolDispatcher':
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.cleanup()


class WebSocketBridgeAdapter:
    """Adapter from WebSocketEventEmitter to AgentWebSocketBridge interface.
    
    This adapter allows UnifiedToolExecutionEngine to work with the new
    WebSocketEventEmitter while maintaining backward compatibility with the
    existing AgentWebSocketBridge interface.
    
    The adapter translates method calls and ensures proper user context isolation.
    """
    
    def __init__(self, websocket_emitter: WebSocketEventEmitter, user_context: UserExecutionContext):
        """Initialize the adapter.
        
        Args:
            websocket_emitter: The WebSocketEventEmitter to adapt
            user_context: User context for validation and agent name generation
        """
        self.websocket_emitter = websocket_emitter
        self.user_context = user_context
    
    async def notify_tool_executing(
        self,
        run_id: str,
        agent_name: str,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Notify that a tool is executing."""
        return await self.websocket_emitter.notify_tool_executing(
            run_id, agent_name, tool_name, parameters
        )
    
    async def notify_tool_completed(
        self,
        run_id: str,
        agent_name: str,
        tool_name: str,
        result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None
    ) -> bool:
        """Notify that a tool has completed."""
        return await self.websocket_emitter.notify_tool_completed(
            run_id, agent_name, tool_name, result, execution_time_ms
        )
    
    async def notify_agent_started(
        self,
        run_id: str,
        agent_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Notify that an agent has started."""
        return await self.websocket_emitter.notify_agent_started(
            run_id, agent_name, context
        )
    
    async def notify_agent_thinking(
        self,
        run_id: str,
        agent_name: str,
        reasoning: str,
        step_number: Optional[int] = None,
        progress_percentage: Optional[float] = None
    ) -> bool:
        """Notify that an agent is thinking."""
        return await self.websocket_emitter.notify_agent_thinking(
            run_id, agent_name, reasoning, step_number, progress_percentage
        )
    
    async def notify_agent_completed(
        self,
        run_id: str,
        agent_name: str,
        result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None
    ) -> bool:
        """Notify that an agent has completed."""
        return await self.websocket_emitter.notify_agent_completed(
            run_id, agent_name, result, execution_time_ms
        )
    
    async def notify_agent_error(
        self,
        run_id: str,
        agent_name: str,
        error: str,
        error_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Notify of an agent error."""
        return await self.websocket_emitter.notify_agent_error(
            run_id, agent_name, error, error_context
        )
    
    async def notify_progress_update(
        self,
        run_id: str,
        agent_name: str,
        progress: Dict[str, Any]
    ) -> bool:
        """Notify of a progress update."""
        return await self.websocket_emitter.notify_progress_update(
            run_id, agent_name, progress
        )
    
    async def notify_custom(
        self,
        run_id: str,
        agent_name: str,
        notification_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """Send custom notification."""
        return await self.websocket_emitter.notify_custom(
            run_id, agent_name, notification_type, data
        )


# Convenience functions for easy creation

async def create_request_scoped_tool_dispatcher(
    user_context: UserExecutionContext,
    tools: List[Any] = None,
    websocket_emitter: Optional[WebSocketEventEmitter] = None
) -> RequestScopedToolDispatcher:
    """Create a RequestScopedToolDispatcher for the given user context.
    
    Args:
        user_context: User execution context to bind dispatcher to
        tools: Optional list of tools to register initially
        websocket_emitter: Optional WebSocket emitter for events
        
    Returns:
        Configured RequestScopedToolDispatcher instance
    """
    return RequestScopedToolDispatcher(user_context, tools, websocket_emitter)


@asynccontextmanager
async def request_scoped_tool_dispatcher_scope(
    user_context: UserExecutionContext,
    tools: List[Any] = None,
    websocket_emitter: Optional[WebSocketEventEmitter] = None
):
    """Create scoped RequestScopedToolDispatcher with automatic cleanup.
    
    This is the recommended way to create request-scoped dispatchers as it ensures
    proper resource cleanup even if exceptions occur.
    
    Args:
        user_context: User execution context to bind dispatcher to
        tools: Optional list of tools to register initially
        websocket_emitter: Optional WebSocket emitter for events
        
    Yields:
        RequestScopedToolDispatcher: Configured dispatcher with automatic cleanup
        
    Example:
        async with request_scoped_tool_dispatcher_scope(context) as dispatcher:
            result = await dispatcher.dispatch("my_tool", param1="value1")
            # Automatic cleanup happens here
    """
    dispatcher = None
    try:
        dispatcher = await create_request_scoped_tool_dispatcher(
            user_context, tools, websocket_emitter
        )
        logger.debug(f"📦 SCOPED DISPATCHER: {dispatcher._get_log_prefix()} created with auto-cleanup")
        yield dispatcher
    finally:
        if dispatcher:
            await dispatcher.cleanup()
            logger.debug(f"📦 SCOPED DISPATCHER: {dispatcher._get_log_prefix()} disposed")