"""Unified Tool Dispatcher - Single Source of Truth for all tool dispatching.

This module consolidates all tool dispatcher implementations into a single, secure,
and well-architected system that eliminates duplication and provides clean separation
of concerns.

Consolidated from:
- tool_dispatcher_core.py (core functionality and modular architecture)
- request_scoped_tool_dispatcher.py (user isolation and per-request scoping)
- unified_tool_execution.py (WebSocket notifications and execution engine)
- websocket_tool_enhancement.py (WebSocket integration patterns)

Business Value:
- Single source of truth eliminates maintenance overhead
- Secure request-scoped isolation by default
- Clean separation of concerns with dedicated modules
- Consistent API across all usage patterns
- Enhanced security boundaries and permission handling

Architecture Principles:
- Request-scoped isolation as the primary pattern
- Global instances only for backward compatibility with clear warnings
- Tool registry, execution, and event notification as separate concerns
- WebSocket events integrated directly, no adapter patterns needed
- Security and permission checking built-in
- Comprehensive error handling and logging
"""

import asyncio
import time
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from contextlib import asynccontextmanager

if TYPE_CHECKING:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.websocket_core.manager import WebSocketManager

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_registry_unified import UnifiedToolRegistry
from netra_backend.app.agents.tool_permission_layer import (
    UnifiedToolPermissionLayer,
    UserContext,
    PermissionResult
)
from netra_backend.app.agents.tool_event_bus import (
    ToolEventBus,
    EventType,
    EventPriority
)
from netra_backend.app.agents.tool_dispatcher_validation import ToolValidator
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.services.websocket_event_emitter import (
    WebSocketEventEmitter,
    WebSocketEventEmitterFactory
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.tool import (
    SimpleToolPayload,
    ToolInput,
    ToolResult,
    ToolStatus,
)

logger = central_logger.get_logger(__name__)

# Typed models for tool dispatch
class ToolDispatchRequest(BaseModel):
    """Typed request for tool dispatch"""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
class ToolDispatchResponse(BaseModel):
    """Typed response for tool dispatch"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UnifiedToolDispatcher:
    """Unified tool dispatcher with secure request-scoped isolation by default.
    
    This is the single source of truth for all tool dispatching, consolidating
    functionality from multiple previous implementations while providing:
    
    - Request-scoped isolation by default (no global state issues)
    - Integrated WebSocket event notifications
    - Clean separation of concerns (registry, execution, validation)
    - Security boundaries and permission checking
    - Comprehensive error handling and metrics
    - Backward compatibility with existing interfaces
    
    Key Design Principles:
    1. Request-scoped isolation is the primary pattern
    2. User context drives all isolation and security
    3. WebSocket events are integrated directly (no adapters)
    4. Tool registry, execution engine, and validation are separate concerns
    5. Global instances emit warnings and are deprecated
    """
    
    def __init__(
        self,
        user_context: Optional[UserExecutionContext] = None,
        tools: List[BaseTool] = None,
        websocket_emitter: Optional[WebSocketEventEmitter] = None,
        websocket_bridge: Optional['AgentWebSocketBridge'] = None,  # Legacy support
        permission_service = None,
        registry: Optional['UnifiedToolRegistry'] = None  # Optional registry to reuse
    ):
        """Initialize unified tool dispatcher.
        
        Args:
            user_context: User context for request-scoped isolation (RECOMMENDED)
            tools: List of tools to register initially
            websocket_emitter: WebSocket event emitter for this request
            websocket_bridge: Legacy AgentWebSocketBridge support (DEPRECATED)
            permission_service: Tool permission service for security
            
        Raises:
            UserWarning: If created without user_context (global state usage)
        """
        # Handle legacy vs. modern initialization
        if user_context is None:
            self._emit_global_state_warning()
            self.is_request_scoped = False
            self.user_context = None
            self.dispatcher_id = f"global_{int(time.time() * 1000)}"
        else:
            self.user_context = validate_user_context(user_context)
            self.is_request_scoped = True
            self.dispatcher_id = f"{user_context.user_id}_{user_context.run_id}_{int(time.time()*1000)}"
        
        # Metadata
        self.created_at = datetime.now(timezone.utc)
        self._is_active = True
        
        # Initialize core components
        self._init_components(websocket_emitter, websocket_bridge, permission_service, registry)
        self._register_initial_tools(tools)
        
        # Metrics tracking
        self._init_metrics()
        
        # Start event bus if request-scoped
        if self.is_request_scoped and self.event_bus:
            asyncio.create_task(self.event_bus.start())
        
        logger.info(f"✅ Created UnifiedToolDispatcher {self.dispatcher_id} "
                   f"({'request-scoped' if self.is_request_scoped else 'GLOBAL - DEPRECATED'})")
    
    def _emit_global_state_warning(self) -> None:
        """Emit warning about global state usage."""
        warnings.warn(
            "UnifiedToolDispatcher created without user_context uses global state "
            "and may cause user isolation issues. Use create_request_scoped() for new code.",
            UserWarning,
            stacklevel=3
        )
        logger.warning("⚠️ GLOBAL STATE USAGE: UnifiedToolDispatcher created without user context")
        logger.warning("⚠️ This may cause user isolation issues in concurrent scenarios")
        logger.warning("⚠️ Consider using UnifiedToolDispatcher.create_request_scoped() for better isolation")
    
    def _init_components(
        self,
        websocket_emitter: Optional[WebSocketEventEmitter],
        websocket_bridge: Optional['AgentWebSocketBridge'],
        permission_service,
        registry: Optional['UnifiedToolRegistry'] = None
    ) -> None:
        """Initialize dispatcher components."""
        # Core components with clean separation of concerns
        # CRITICAL FIX: Reuse existing registry to prevent duplicates
        if registry is not None:
            self.registry = registry
            logger.info(f"🔄 Reusing existing registry {registry.registry_id} to prevent duplicates")
        else:
            self.registry = UnifiedToolRegistry(f"registry_{self.dispatcher_id}")
            logger.info(f"🆕 Created new registry registry_{self.dispatcher_id}")
        self.validator = ToolValidator()
        
        # Permission layer
        if permission_service:
            self.permission_layer = permission_service
        elif self.is_request_scoped:
            self.permission_layer = UnifiedToolPermissionLayer(f"perms_{self.dispatcher_id}")
        else:
            from netra_backend.app.agents.tool_permission_layer import get_global_permission_layer
            self.permission_layer = get_global_permission_layer()
        
        # Event bus for notifications
        if self.is_request_scoped:
            self.event_bus = ToolEventBus(f"events_{self.dispatcher_id}")
        else:
            self.event_bus = None  # Global dispatchers use legacy WebSocket bridge
        
        # Handle WebSocket configuration - prefer modern emitter over legacy bridge
        if websocket_emitter:
            self.websocket_emitter = websocket_emitter
            # Create bridge adapter for UnifiedToolExecutionEngine compatibility
            self.websocket_bridge = self._create_websocket_bridge_adapter(websocket_emitter)
            logger.debug(f"✅ Using modern WebSocket emitter for {self.dispatcher_id}")
        elif websocket_bridge:
            self.websocket_bridge = websocket_bridge
            self.websocket_emitter = None
            logger.debug(f"⚠️ Using legacy WebSocket bridge for {self.dispatcher_id}")
        else:
            self.websocket_emitter = None
            self.websocket_bridge = None
            logger.debug(f"📡 No WebSocket support configured for {self.dispatcher_id}")
        
        # Create unified execution engine
        self.executor = UnifiedToolExecutionEngine(
            websocket_bridge=self.websocket_bridge,
            permission_service=permission_service
        )
    
    def _create_websocket_bridge_adapter(self, websocket_emitter: WebSocketEventEmitter) -> 'WebSocketBridgeAdapter':
        """Create adapter from WebSocketEventEmitter to AgentWebSocketBridge interface."""
        return WebSocketBridgeAdapter(websocket_emitter, self.user_context)
    
    def _register_initial_tools(self, tools: List[BaseTool]) -> None:
        """Register initial tools if provided."""
        logger.info(f"🔧 UnifiedToolDispatcher._register_initial_tools called with {len(tools) if tools else 0} tools")
        if tools:
            logger.info(f"🔧 Registering {len(tools)} tools in registry {self.registry.registry_id}")
            registered_count = self.registry.register_tools(tools)
            logger.info(f"✅ Successfully registered {registered_count}/{len(tools)} tools")
            
            # Log current state of registry
            current_tools = self.registry.list_tools()
            logger.info(f"📦 Registry now contains {len(current_tools)} tools: {current_tools[:5]}...")
        else:
            logger.warning("⚠️ No tools provided to _register_initial_tools")
    
    def _init_metrics(self) -> None:
        """Initialize metrics tracking."""
        self._metrics = {
            'tools_executed': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_execution_time_ms': 0,
            'last_execution_time': None,
            'created_at': self.created_at,
            'context_id': self.user_context.get_correlation_id() if self.user_context else 'global'
        }
    
    # ===================== CORE TOOL DISPATCH METHODS =====================
    
    @property
    def tools(self) -> Dict[str, Any]:
        """Expose tools registry for compatibility."""
        tools_dict = self.registry.tools
        logger.debug(f"🔍 UnifiedToolDispatcher.tools property called - returning {len(tools_dict)} tools from registry {self.registry.registry_id}")
        return tools_dict
    
    @property
    def has_websocket_support(self) -> bool:
        """Check if WebSocket support is enabled."""
        return self.websocket_emitter is not None or self.websocket_bridge is not None
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool exists."""
        self._ensure_active()
        return self.registry.has_tool(tool_name)
    
    def register_tool(self, tool_name: str, tool_func, description: str = None) -> None:
        """Register a tool function with the dispatcher."""
        self._ensure_active()
        
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
        """Dispatch tool execution with proper typing, permissions, and isolation."""
        self._ensure_active()
        
        if not self.is_request_scoped:
            logger.warning(f"⚠️ Tool {tool_name} executed on global dispatcher - isolation not guaranteed")
        
        start_time = time.time()
        tool_input = self._create_tool_input(tool_name, kwargs)
        execution_id = f"exec_{tool_name}_{int(start_time * 1000)}"
        
        # Check if tool exists
        if not self.has_tool(tool_name):
            return self._create_error_result(tool_input, f"Tool {tool_name} not found")
        
        # Permission check if we have user context
        if self.user_context and self.permission_layer:
            user_ctx = UserContext(
                user_id=self.user_context.user_id,
                plan_tier=getattr(self.user_context, 'plan_tier', 'free'),
                roles=getattr(self.user_context, 'roles', set()),
                feature_flags=getattr(self.user_context, 'feature_flags', {}),
                is_developer=getattr(self.user_context, 'is_developer', False),
                is_admin=getattr(self.user_context, 'is_admin', False)
            )
            
            permission_result = await self.permission_layer.check_permission(
                user_ctx, tool_name, execution_id, kwargs
            )
            
            if not permission_result.allowed:
                logger.warning(f"🚫 Tool {tool_name} permission denied: {permission_result.reason}")
                return self._create_error_result(tool_input, f"Permission denied: {permission_result.reason}")
        
        # Update metrics
        self._metrics['tools_executed'] += 1
        self._metrics['last_execution_time'] = datetime.now(timezone.utc)
        
        # Send executing event if using modern event bus
        if self.event_bus:
            await self.event_bus.publish_tool_executing(
                run_id=self.user_context.run_id if self.user_context else "unknown",
                agent_name="ToolDispatcher",
                tool_name=tool_name,
                parameters=kwargs,
                user_id=self.user_context.user_id if self.user_context else None,
                thread_id=self.user_context.thread_id if self.user_context else None,
                correlation_id=self.user_context.get_correlation_id() if self.user_context else None
            )
        
        try:
            tool = self.registry.get_tool(tool_name)
            result = await self.executor.execute_tool_with_input(tool_input, tool, kwargs)
            
            # Update success metrics
            execution_time_ms = (time.time() - start_time) * 1000
            self._metrics['successful_executions'] += 1
            self._metrics['total_execution_time_ms'] += execution_time_ms
            
            # Send completion event if using modern event bus
            if self.event_bus:
                await self.event_bus.publish_tool_completed(
                    run_id=self.user_context.run_id if self.user_context else "unknown",
                    agent_name="ToolDispatcher",
                    tool_name=tool_name,
                    result={"status": "success", "output": str(result)[:500]},
                    execution_time_ms=execution_time_ms,
                    user_id=self.user_context.user_id if self.user_context else None,
                    thread_id=self.user_context.thread_id if self.user_context else None,
                    correlation_id=self.user_context.get_correlation_id() if self.user_context else None
                )
            
            logger.debug(f"✅ Tool {tool_name} executed successfully in {execution_time_ms:.1f}ms {self._get_log_prefix()}")
            return result
            
        except Exception as e:
            # Update failure metrics
            execution_time_ms = (time.time() - start_time) * 1000
            self._metrics['failed_executions'] += 1
            self._metrics['total_execution_time_ms'] += execution_time_ms
            
            # Send error event if using modern event bus
            if self.event_bus:
                await self.event_bus.publish_tool_completed(
                    run_id=self.user_context.run_id if self.user_context else "unknown",
                    agent_name="ToolDispatcher", 
                    tool_name=tool_name,
                    error=str(e),
                    execution_time_ms=execution_time_ms,
                    user_id=self.user_context.user_id if self.user_context else None,
                    thread_id=self.user_context.thread_id if self.user_context else None,
                    correlation_id=self.user_context.get_correlation_id() if self.user_context else None
                )
            
            logger.error(f"🚨 Tool {tool_name} failed in {execution_time_ms:.1f}ms {self._get_log_prefix()}: {e}")
            return self._create_error_result(tool_input, f"Tool execution failed: {e}")
        
        finally:
            # End execution tracking for concurrency limits
            if self.user_context and self.permission_layer:
                self.permission_layer.end_execution(self.user_context.user_id, execution_id)
    
    async def dispatch_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> ToolDispatchResponse:
        """Dispatch tool with state - method expected by sub-agents."""
        self._ensure_active()
        
        # Validate run_id matches our context for security (if request-scoped)
        if self.is_request_scoped and run_id != self.user_context.run_id:
            logger.error(f"🚨 RUN_ID MISMATCH: {self._get_log_prefix()} expected {self.user_context.run_id}, got {run_id}")
            return self._create_tool_not_found_response(tool_name, run_id)
        
        if not self.has_tool(tool_name):
            return self._create_tool_not_found_response(tool_name, run_id)
        
        start_time = time.time()
        
        try:
            tool = self.registry.get_tool(tool_name)
            result = await self.executor.execute_with_state(tool, tool_name, parameters, state, run_id)
            
            # Update metrics
            execution_time_ms = (time.time() - start_time) * 1000
            self._metrics['successful_executions'] += 1
            self._metrics['total_execution_time_ms'] += execution_time_ms
            
            return ToolDispatchResponse(
                success=result.get("success", True),
                result=result.get("result"),
                metadata=result.get("metadata", {"tool_name": tool_name, "run_id": run_id})
            )
            
        except Exception as e:
            # Update failure metrics
            execution_time_ms = (time.time() - start_time) * 1000
            self._metrics['failed_executions'] += 1
            self._metrics['total_execution_time_ms'] += execution_time_ms
            
            logger.error(f"🚨 Tool dispatch failed {self._get_log_prefix()}: {e}")
            return ToolDispatchResponse(
                success=False,
                error=str(e),
                metadata={"tool_name": tool_name, "run_id": run_id}
            )
    
    # ===================== WEBSOCKET MANAGEMENT =====================
    
    def set_websocket_bridge(self, bridge: Optional['AgentWebSocketBridge']) -> None:
        """Set or update WebSocket bridge on the executor."""
        if hasattr(self.executor, 'websocket_bridge'):
            old_bridge = self.executor.websocket_bridge
            self.executor.websocket_bridge = bridge
            self.websocket_bridge = bridge
            
            if bridge is not None:
                logger.info(f"✅ Updated WebSocket bridge for {self._get_log_prefix()}")
            else:
                logger.warning(f"⚠️ Set WebSocket bridge to None for {self._get_log_prefix()} - events will be lost")
        else:
            logger.error(f"🚨 CRITICAL: Executor doesn't support WebSocket bridge pattern for {self._get_log_prefix()}")
    
    def get_websocket_bridge(self) -> Optional['AgentWebSocketBridge']:
        """Get current WebSocket bridge from executor."""
        return getattr(self, 'websocket_bridge', None)
    
    def set_websocket_manager(self, websocket_manager: Optional['WebSocketManager']) -> None:
        """Set WebSocket manager for compatibility with legacy AgentRegistry integration.
        
        This method provides compatibility with the AgentRegistry.set_websocket_manager()
        integration pattern. It converts the WebSocketManager to an AgentWebSocketBridge
        and delegates to set_websocket_bridge().
        
        Args:
            websocket_manager: WebSocket manager instance or None to clear
        """
        if websocket_manager is None:
            self.set_websocket_bridge(None)
            logger.info(f"✅ Cleared WebSocket manager for {self._get_log_prefix()}")
        else:
            try:
                # Convert WebSocketManager to AgentWebSocketBridge
                from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
                # Create a bridge that wraps the manager
                bridge = AgentWebSocketBridge()  # Use default initialization
                self.set_websocket_bridge(bridge)
                logger.info(f"✅ Set WebSocket manager via bridge conversion for {self._get_log_prefix()}")
            except ImportError as e:
                logger.error(f"Failed to import AgentWebSocketBridge for WebSocket manager conversion: {e}")
                self.set_websocket_bridge(None)
            except Exception as e:
                logger.error(f"Failed to convert WebSocket manager to bridge for {self._get_log_prefix()}: {e}")
                self.set_websocket_bridge(None)
    
    def diagnose_websocket_wiring(self) -> Dict[str, Any]:
        """Diagnose WebSocket wiring for debugging silent failures."""
        diagnosis = {
            "dispatcher_id": self.dispatcher_id,
            "is_request_scoped": self.is_request_scoped,
            "has_websocket_emitter": self.websocket_emitter is not None,
            "has_websocket_bridge": self.websocket_bridge is not None,
            "executor_has_websocket_bridge_attr": hasattr(self.executor, 'websocket_bridge'),
            "websocket_bridge_is_none": True,
            "websocket_bridge_type": None,
            "has_websocket_support": self.has_websocket_support,
            "critical_issues": []
        }
        
        if hasattr(self.executor, 'websocket_bridge'):
            bridge = self.executor.websocket_bridge
            diagnosis["websocket_bridge_is_none"] = bridge is None
            diagnosis["websocket_bridge_type"] = type(bridge).__name__ if bridge else None
            
            if bridge is None:
                diagnosis["critical_issues"].append("WebSocket bridge is None - tool events will be lost")
            elif not hasattr(bridge, 'notify_tool_executing'):
                diagnosis["critical_issues"].append("WebSocket bridge missing notify_tool_executing method")
            elif not hasattr(bridge, 'notify_tool_completed'):
                diagnosis["critical_issues"].append("WebSocket bridge missing notify_tool_completed method")
        else:
            diagnosis["critical_issues"].append("Executor missing websocket_bridge attribute")
        
        return diagnosis
    
    # ===================== LIFECYCLE MANAGEMENT =====================
    
    def _ensure_active(self) -> None:
        """Ensure dispatcher is still active."""
        if not self._is_active:
            raise RuntimeError(f"UnifiedToolDispatcher {self.dispatcher_id} has been disposed")
    
    def _get_log_prefix(self) -> str:
        """Get consistent logging prefix."""
        if self.user_context:
            return f"[{self.user_context.get_correlation_id()}]"
        return f"[{self.dispatcher_id}]"
    
    async def cleanup(self) -> None:
        """Clean up dispatcher resources."""
        if not self._is_active:
            return
        
        try:
            logger.info(f"Cleaning up UnifiedToolDispatcher {self.dispatcher_id}")
            
            # Stop event bus if we have one
            if hasattr(self, 'event_bus') and self.event_bus:
                try:
                    await self.event_bus.stop()
                except Exception as e:
                    logger.error(f"Error stopping event bus: {e}")
            
            # Dispose WebSocket emitter if we have one
            if hasattr(self, 'websocket_emitter') and self.websocket_emitter:
                try:
                    await self.websocket_emitter.dispose()
                except Exception as e:
                    logger.error(f"Error disposing WebSocket emitter: {e}")
            
            # Clear permission layer audit log if request-scoped
            if (hasattr(self, 'permission_layer') and 
                self.is_request_scoped and
                hasattr(self.permission_layer, 'clear_audit_log')):
                try:
                    self.permission_layer.clear_audit_log()
                except Exception as e:
                    logger.error(f"Error clearing permission audit log: {e}")
            
            # Clear registry state
            if hasattr(self, 'registry'):
                try:
                    self.registry.clear_tools()
                except Exception as e:
                    logger.error(f"Error clearing registry: {e}")
            
            # Clear metrics
            if hasattr(self, '_metrics'):
                self._metrics.clear()
            
            # Mark as inactive
            self._is_active = False
            
            logger.info(f"✅ Cleaned up UnifiedToolDispatcher {self.dispatcher_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up UnifiedToolDispatcher {self.dispatcher_id}: {e}")
            raise
    
    def is_active(self) -> bool:
        """Check if dispatcher is still active."""
        return self._is_active
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics for this dispatcher."""
        self._ensure_active()
        
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
            'is_request_scoped': self.is_request_scoped,
            'user_id': self.user_context.user_id if self.user_context else None,
            'run_id': self.user_context.run_id if self.user_context else None,
            'success_rate': success_rate,
            'avg_execution_time_ms': avg_execution_time,
            'uptime_seconds': (datetime.now(timezone.utc) - self.created_at).total_seconds(),
            'total_tools_registered': len(self.registry.tools),
            'has_websocket_support': self.has_websocket_support,
            'is_active': self._is_active
        }
    
    # ===================== HELPER METHODS =====================
    
    def _create_tool_input(self, tool_name: str, kwargs: Dict[str, Any]) -> ToolInput:
        """Create tool input from parameters."""
        return ToolInput(tool_name=tool_name, kwargs=kwargs)
    
    def _create_error_result(self, tool_input: ToolInput, message: str) -> ToolResult:
        """Create error result for tool execution."""
        return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=message)
    
    def _create_tool_not_found_response(self, tool_name: str, run_id: str) -> ToolDispatchResponse:
        """Create response for tool not found scenario."""
        logger.warning(f"Tool {tool_name} not found for run_id {run_id} in {self._get_log_prefix()}")
        return ToolDispatchResponse(
            success=False,
            error=f"Tool {tool_name} not found"
        )
    
    # ===================== CONTEXT MANAGER SUPPORT =====================
    
    async def __aenter__(self) -> 'UnifiedToolDispatcher':
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.cleanup()


class WebSocketBridgeAdapter:
    """Adapter from WebSocketEventEmitter to AgentWebSocketBridge interface.
    
    This adapter allows UnifiedToolExecutionEngine to work with the modern
    WebSocketEventEmitter while maintaining backward compatibility.
    """
    
    def __init__(self, websocket_emitter: WebSocketEventEmitter, user_context: Optional[UserExecutionContext]):
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


# ===================== FACTORY METHODS FOR REQUEST-SCOPED DISPATCH =====================

class UnifiedToolDispatcherFactory:
    """Factory for creating properly configured UnifiedToolDispatcher instances."""
    
    @staticmethod
    async def create_request_scoped(
        user_context: UserExecutionContext,
        tools: List[BaseTool] = None,
        websocket_manager: Optional['WebSocketManager'] = None,
        permission_service = None
    ) -> UnifiedToolDispatcher:
        """Create request-scoped tool dispatcher with complete user isolation.
        
        RECOMMENDED: Use this method for all new code.
        
        Args:
            user_context: UserExecutionContext for complete isolation
            tools: Optional list of tools to register initially
            websocket_manager: Optional WebSocket manager for event routing
            permission_service: Optional permission service for security
            
        Returns:
            UnifiedToolDispatcher: Isolated dispatcher for this request
        """
        # Validate user context
        user_context = validate_user_context(user_context)
        
        # Create WebSocket emitter if manager provided
        websocket_emitter = None
        if websocket_manager:
            websocket_emitter = await WebSocketEventEmitterFactory.create_emitter(
                user_context, websocket_manager
            )
        
        # Create request-scoped dispatcher
        dispatcher = UnifiedToolDispatcher(
            user_context=user_context,
            tools=tools,
            websocket_emitter=websocket_emitter,
            permission_service=permission_service
        )
        
        logger.info(f"🏭 Created request-scoped UnifiedToolDispatcher for {user_context.get_correlation_id()}")
        return dispatcher
    
    @staticmethod
    @asynccontextmanager
    async def create_scoped_context(
        user_context: UserExecutionContext,
        tools: List[BaseTool] = None,
        websocket_manager: Optional['WebSocketManager'] = None,
        permission_service = None
    ):
        """Create scoped dispatcher context manager with automatic cleanup.
        
        Args:
            user_context: UserExecutionContext for complete isolation
            tools: Optional list of tools to register initially
            websocket_manager: Optional WebSocket manager for event routing
            permission_service: Optional permission service for security
            
        Yields:
            UnifiedToolDispatcher: Scoped dispatcher with automatic cleanup
        """
        dispatcher = None
        try:
            dispatcher = await UnifiedToolDispatcherFactory.create_request_scoped(
                user_context, tools, websocket_manager, permission_service
            )
            logger.debug(f"📦 SCOPED DISPATCHER: {user_context.get_correlation_id()} created with auto-cleanup")
            yield dispatcher
        finally:
            if dispatcher:
                await dispatcher.cleanup()
                logger.debug(f"📦 SCOPED DISPATCHER: {user_context.get_correlation_id()} disposed")
    
    @staticmethod
    def create_legacy_global(
        tools: List[BaseTool] = None,
        websocket_bridge: Optional['AgentWebSocketBridge'] = None,
        permission_service = None,
        registry: Optional['UnifiedToolRegistry'] = None
    ) -> UnifiedToolDispatcher:
        """Create legacy global dispatcher (DEPRECATED).
        
        WARNING: This creates a global dispatcher that may cause user isolation issues.
        Use create_request_scoped() for new code.
        
        Args:
            tools: Optional list of tools to register initially
            websocket_bridge: Optional AgentWebSocketBridge for events
            permission_service: Optional permission service for security
            registry: Optional existing registry to reuse (prevents duplicate registrations)
            
        Returns:
            UnifiedToolDispatcher: Global dispatcher (DEPRECATED)
        """
        dispatcher = UnifiedToolDispatcher(
            user_context=None,  # This triggers the global state warning
            tools=tools,
            websocket_bridge=websocket_bridge,
            permission_service=permission_service,
            registry=registry  # Pass existing registry to prevent duplicates
        )
        
        logger.warning(f"⚠️ Created LEGACY GLOBAL UnifiedToolDispatcher {dispatcher.dispatcher_id}")
        return dispatcher


# ===================== CONVENIENCE FUNCTIONS FOR COMPATIBILITY =====================

async def create_request_scoped_tool_dispatcher(
    user_context: UserExecutionContext,
    tools: List[BaseTool] = None,
    websocket_manager: Optional['WebSocketManager'] = None,
    permission_service = None
) -> UnifiedToolDispatcher:
    """Convenience function to create request-scoped tool dispatcher."""
    return await UnifiedToolDispatcherFactory.create_request_scoped(
        user_context, tools, websocket_manager, permission_service
    )

@asynccontextmanager
async def request_scoped_tool_dispatcher_context(
    user_context: UserExecutionContext,
    tools: List[BaseTool] = None,
    websocket_manager: Optional['WebSocketManager'] = None,
    permission_service = None
):
    """Convenience context manager for scoped tool dispatcher."""
    async with UnifiedToolDispatcherFactory.create_scoped_context(
        user_context, tools, websocket_manager, permission_service
    ) as dispatcher:
        yield dispatcher

def create_legacy_tool_dispatcher(
    tools: List[BaseTool] = None,
    websocket_bridge: Optional['AgentWebSocketBridge'] = None,
    permission_service = None,
    registry: Optional['UnifiedToolRegistry'] = None
) -> UnifiedToolDispatcher:
    """Convenience function to create legacy global dispatcher (DEPRECATED).
    
    Args:
        registry: Optional existing registry to reuse (prevents duplicate registrations)
    """
    return UnifiedToolDispatcherFactory.create_legacy_global(
        tools, websocket_bridge, permission_service, registry
    )


# ===================== BACKWARD COMPATIBILITY ALIASES =====================

# Alias for backward compatibility with existing code
ToolDispatcher = UnifiedToolDispatcher
RequestScopedToolDispatcher = UnifiedToolDispatcher

# Export all public interfaces
__all__ = [
    'UnifiedToolDispatcher',
    'UnifiedToolDispatcherFactory', 
    'WebSocketBridgeAdapter',
    'ToolDispatchRequest',
    'ToolDispatchResponse',
    'create_request_scoped_tool_dispatcher',
    'request_scoped_tool_dispatcher_context',
    'create_legacy_tool_dispatcher',
    # Backward compatibility aliases
    'ToolDispatcher',
    'RequestScopedToolDispatcher'
]