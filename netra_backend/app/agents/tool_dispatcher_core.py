"""Core dispatcher logic and initialization for tool dispatching."""
import time
import warnings
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.registry.universal_registry import ToolRegistry
from netra_backend.app.agents.tool_dispatcher_validation import ToolValidator
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

class ToolDispatcher:
    """Core tool dispatcher with request-scoped architecture.
    
    REQUIRED: Use factory methods for instantiation:
    - ToolDispatcher.create_request_scoped_dispatcher() for isolated instances
    - ToolDispatcher.create_scoped_dispatcher_context() for automatic cleanup
    
    Direct instantiation is no longer supported to ensure user isolation.
    """
    
    def __init__(self, tools: List[BaseTool] = None, websocket_bridge: Optional['AgentWebSocketBridge'] = None):
        """Private initializer - use factory methods instead.
        
        Direct instantiation is prevented to ensure user isolation.
        Use ToolDispatcher.create_request_scoped_dispatcher() or
        ToolDispatcher.create_scoped_dispatcher_context() instead.
        """
        raise RuntimeError(
            "Direct ToolDispatcher instantiation is no longer supported. "
            "Use ToolDispatcher.create_request_scoped_dispatcher(user_context) or "
            "ToolDispatcher.create_scoped_dispatcher_context(user_context) for proper user isolation."
        )
    
    @classmethod
    def _init_from_factory(cls, tools: List[BaseTool] = None, websocket_bridge: Optional['AgentWebSocketBridge'] = None):
        """Internal factory initializer for creating request-scoped instances.
        
        This method bypasses the __init__ RuntimeError and is only called
        by the factory methods to create properly isolated instances.
        """
        instance = cls.__new__(cls)
        instance._init_components(websocket_bridge)
        instance._register_initial_tools(tools)
        return instance
    
    @property
    def tools(self) -> Dict[str, Any]:
        """Expose tools registry"""
        return self.registry.tools
    
    @property
    def has_websocket_support(self) -> bool:
        """Check if WebSocket support is enabled through bridge."""
        return hasattr(self.executor, 'websocket_bridge') and self.executor.websocket_bridge is not None
    
    
    def _init_components(self, websocket_bridge: Optional['AgentWebSocketBridge'] = None) -> None:
        """Initialize dispatcher components with AgentWebSocketBridge support built-in."""
        self.registry = ToolRegistry()
        # Always use UnifiedToolExecutionEngine - no more enhancement pattern
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        self.executor = UnifiedToolExecutionEngine(websocket_bridge=websocket_bridge)
        self.validator = ToolValidator()
    
    def _register_initial_tools(self, tools: List[BaseTool]) -> None:
        """Register initial tools if provided"""
        if tools:
            self.registry.register_tools(tools)
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool exists"""
        return self.registry.has_tool(tool_name)
    
    def register_tool(self, tool_name: str, tool_func, description: str = None) -> None:
        """Register a tool - only available on request-scoped instances.
        
        This method should only be called on instances created via factory methods.
        """
        from langchain_core.tools import BaseTool
        
        # Create a simple tool wrapper if needed
        if not isinstance(tool_func, BaseTool):
            # Create a simple BaseTool wrapper
            desc = description or f"Dynamic tool: {tool_name}"
            
            class DynamicTool(BaseTool):
                name: str = tool_name
                description: str = desc
                
                def _run(self, *args, **kwargs):
                    return tool_func(*args, **kwargs)
                
                async def _arun(self, *args, **kwargs):
                    if hasattr(tool_func, '__call__'):
                        # Check if it's a coroutine function
                        import asyncio
                        if asyncio.iscoroutinefunction(tool_func):
                            return await tool_func(*args, **kwargs)
                        else:
                            return tool_func(*args, **kwargs)
                    return tool_func(*args, **kwargs)
            
            tool_func = DynamicTool()
        
        self.registry.register_tool(tool_func)
    
    async def dispatch(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """Dispatch tool execution - only available on request-scoped instances.
        
        This method should only be called on instances created via factory methods.
        """
        tool_input = self._create_tool_input(tool_name, kwargs)
        if not self.has_tool(tool_name):
            return self._create_error_result(tool_input, f"Tool {tool_name} not found")
        
        tool = self.registry.get_tool(tool_name)
        return await self.executor.execute_tool_with_input(tool_input, tool, kwargs)
    
    def _create_tool_input(self, tool_name: str, kwargs: Dict[str, Any]) -> ToolInput:
        """Create tool input from parameters"""
        return ToolInput(tool_name=tool_name, kwargs=kwargs)
    
    def _create_error_result(self, tool_input: ToolInput, message: str) -> ToolResult:
        """Create error result for tool execution"""
        return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=message)
    
    async def dispatch_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> ToolDispatchResponse:
        """Dispatch a tool with parameters - only available on request-scoped instances.
        
        This method should only be called on instances created via factory methods.
        """
        if not self.has_tool(tool_name):
            return self._create_tool_not_found_response(tool_name, run_id)
        
        tool = self.registry.get_tool(tool_name)
        return await self.executor.execute_with_state(tool, tool_name, parameters, state, run_id)
    
    def _create_tool_not_found_response(self, tool_name: str, run_id: str) -> ToolDispatchResponse:
        """Create response for tool not found scenario"""
        logger.warning(f"Tool {tool_name} not found for run_id {run_id}")
        return ToolDispatchResponse(
            success=False,
            error=f"Tool {tool_name} not found"
        )
    
    async def _execute_tool(self, tool_input: ToolInput, tool: Any, kwargs: Dict[str, Any]) -> ToolResult:
        """Execute tool via executor"""
        return await self.executor.execute_tool_with_input(tool_input, tool, kwargs)
    
    def set_websocket_bridge(self, bridge: Optional['AgentWebSocketBridge']) -> None:
        """Set or update WebSocket bridge on the executor.
        
        This method allows updating the bridge after initialization,
        which is critical for proper WebSocket event delivery.
        """
        if hasattr(self.executor, 'websocket_bridge'):
            old_bridge = self.executor.websocket_bridge
            self.executor.websocket_bridge = bridge
            
            if bridge is not None:
                logger.info("✅ Updated ToolDispatcher executor WebSocket bridge")
            else:
                logger.warning("⚠️ Set ToolDispatcher executor WebSocket bridge to None - events will be lost")
            
            if old_bridge is None and bridge is not None:
                logger.info("🔧 Fixed missing WebSocket bridge on ToolDispatcher - events now enabled")
        else:
            logger.error("🚨 CRITICAL: ToolDispatcher executor doesn't support WebSocket bridge pattern")
    
    def get_websocket_bridge(self) -> Optional['AgentWebSocketBridge']:
        """Get current WebSocket bridge from executor."""
        if hasattr(self.executor, 'websocket_bridge'):
            return self.executor.websocket_bridge
        return None
    
    def diagnose_websocket_wiring(self) -> Dict[str, Any]:
        """Diagnose WebSocket wiring for debugging silent failures."""
        diagnosis = {
            "dispatcher_has_executor": hasattr(self, 'executor'),
            "executor_type": type(self.executor).__name__ if hasattr(self, 'executor') else None,
            "executor_has_websocket_bridge_attr": False,
            "websocket_bridge_is_none": True,
            "websocket_bridge_type": None,
            "has_websocket_support": self.has_websocket_support,
            "critical_issues": []
        }
        
        if hasattr(self, 'executor'):
            diagnosis["executor_has_websocket_bridge_attr"] = hasattr(self.executor, 'websocket_bridge')
            
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
        else:
            diagnosis["critical_issues"].append("ToolDispatcher missing executor")
        
        return diagnosis
    
    # ===================== FACTORY METHODS FOR REQUEST-SCOPED DISPATCH =====================
    
    @staticmethod
    async def create_request_scoped_dispatcher(
        user_context,  # UserExecutionContext type hint avoided to prevent circular imports
        tools: List[BaseTool] = None,
        websocket_manager = None  # WebSocketManager type hint avoided
    ):
        """Create request-scoped tool dispatcher with complete user isolation.
        
        DEPRECATED: This method redirects to ToolDispatcherFactory for SSOT compliance.
        Use ToolDispatcherFactory.create_for_request() directly instead.
        
        🟢 RECOMMENDED SECURE PATTERN: Use ToolDispatcherFactory for new code.
        This factory method creates proper per-request isolation and eliminates global state risks.
        
        ✅ SECURITY BENEFITS:
        - Complete user context isolation (no data leaks)
        - Request-scoped tool registry (tools not shared between users)
        - Proper WebSocket event routing (events go to correct user)
        - Automatic cleanup on request completion
        - Memory-safe concurrent request handling
        
        🔒 USER ISOLATION GUARANTEES:
        - Each user gets their own tool dispatcher instance
        - No shared state between concurrent requests
        - WebSocket events are user-scoped and secure
        - Tool execution happens in proper user context
        
        Args:
            user_context: UserExecutionContext for complete isolation (REQUIRED)
            tools: Optional list of tools to register for this user only
            websocket_manager: Optional WebSocket manager for secure event routing
            
        Returns:
            RequestScopedToolDispatcher: Isolated dispatcher for this specific request
            
        Raises:
            ValueError: If user_context is invalid or dependencies are unavailable
            
        Example:
            # DEPRECATED - use ToolDispatcherFactory instead
            dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
                user_context=user_context,
                tools=user_specific_tools,
                websocket_manager=websocket_manager
            )
            result = await dispatcher.dispatch("my_tool", param="value")
            
            # RECOMMENDED - use SSOT factory
            from netra_backend.app.factories import create_tool_dispatcher
            dispatcher = await create_tool_dispatcher(
                user_context=user_context,
                tools=user_specific_tools,
                websocket_manager=websocket_manager
            )
        """
        import warnings
        
        # Issue deprecation warning for Phase 2 consolidation
        warnings.warn(
            "ToolDispatcher.create_request_scoped_dispatcher() is deprecated. "
            "Use ToolDispatcherFactory.create_for_request() for SSOT compliance.",
            DeprecationWarning,
            stacklevel=2
        )
        
        logger.warning(
            f"🔄 DEPRECATED: ToolDispatcher.create_request_scoped_dispatcher() -> ToolDispatcherFactory.create_for_request() "
            f"for user {user_context.user_id} (Phase 2 factory consolidation)"
        )
        
        # Import here to avoid circular imports - now using SSOT factory
        from netra_backend.app.factories.tool_dispatcher_factory import create_tool_dispatcher
        
        logger.info(f"🏭✅ Creating SSOT request-scoped dispatcher for user {user_context.user_id}")
        logger.info("🔒 User context isolation enabled via SSOT factory - no global state risks")
        
        return await create_tool_dispatcher(
            user_context=user_context,
            tools=tools,
            websocket_manager=websocket_manager
        )
    
    @staticmethod
    def create_scoped_dispatcher_context(
        user_context,  # UserExecutionContext type hint avoided
        tools: List[BaseTool] = None,
        websocket_manager = None  # WebSocketManager type hint avoided
    ):
        """Create scoped dispatcher context manager with automatic cleanup.
        
        DEPRECATED: This method redirects to ToolDispatcherFactory for SSOT compliance.
        Use ToolDispatcherFactory.create_scoped() directly instead.
        
        🟢 RECOMMENDED SECURE PATTERN: Use ToolDispatcherFactory for request handling with guaranteed cleanup.
        This context manager ensures proper resource cleanup and prevents memory leaks.
        
        ✅ AUTOMATIC SAFETY FEATURES:
        - Guaranteed resource cleanup on context exit
        - Exception-safe disposal of user-scoped resources
        - WebSocket connection cleanup to prevent event leaks
        - Memory-safe handling of tool state
        - Database session cleanup if applicable
        
        🔒 SECURITY GUARANTEES:
        - User context is automatically disposed after use
        - No lingering references to user data
        - WebSocket events cannot leak to other users
        - Tool state is properly isolated and cleaned up
        
        Args:
            user_context: UserExecutionContext for complete isolation (REQUIRED)
            tools: Optional list of tools to register for this request only
            websocket_manager: Optional WebSocket manager for secure event routing
            
        Returns:
            AsyncContextManager[RequestScopedToolDispatcher]: Context manager with automatic cleanup
            
        Raises:
            ValueError: If user_context is invalid
            RuntimeError: If cleanup fails (logs warning but doesn't propagate)
            
        Example:
            # DEPRECATED PATTERN - use ToolDispatcherFactory instead
            async with ToolDispatcher.create_scoped_dispatcher_context(user_context) as dispatcher:
                result = await dispatcher.dispatch("my_tool", param="value")
                # Automatic cleanup happens here
                
            # RECOMMENDED PATTERN - use SSOT factory
            from netra_backend.app.factories import tool_dispatcher_scope
            async with tool_dispatcher_scope(user_context) as dispatcher:
                result = await dispatcher.dispatch("my_tool", param="value")
                # Automatic cleanup happens here - no memory leaks
                
        ⚠️ IMPORTANT: Always use context managers for request handling to ensure:
        - User data doesn't leak between requests
        - WebSocket events are properly routed
        - Resources are cleaned up even if exceptions occur
        """
        import warnings
        
        # Issue deprecation warning for Phase 2 consolidation
        warnings.warn(
            "ToolDispatcher.create_scoped_dispatcher_context() is deprecated. "
            "Use ToolDispatcherFactory.create_scoped() for SSOT compliance.",
            DeprecationWarning,
            stacklevel=2
        )
        
        logger.warning(
            f"🔄 DEPRECATED: ToolDispatcher.create_scoped_dispatcher_context() -> ToolDispatcherFactory.create_scoped() "
            f"for user {user_context.user_id} (Phase 2 factory consolidation)"
        )
        
        # Import here to avoid circular imports - now using SSOT factory
        from netra_backend.app.factories.tool_dispatcher_factory import tool_dispatcher_scope
        
        logger.info(f"🏭✅ Creating SSOT scoped dispatcher context for user {user_context.user_id}")
        logger.info("🔒 Automatic cleanup enabled via SSOT factory - memory and security safe")
        
        return tool_dispatcher_scope(
            user_context=user_context,
            tools=tools,
            websocket_manager=websocket_manager
        )
    
    # Legacy compatibility methods removed - use factory methods only

# ============================================================================
# BACKWARD COMPATIBILITY EXPORTS
# ============================================================================

# Compatibility alias for existing code that imports ToolDispatcherCore
ToolDispatcherCore = ToolDispatcher
    
