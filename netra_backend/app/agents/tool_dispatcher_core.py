"""Core dispatcher logic and initialization for tool dispatching."""
import warnings
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher_registry import ToolRegistry
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
    """Core tool dispatcher with modular architecture"""
    
    def __init__(self, tools: List[BaseTool] = None, websocket_bridge: Optional['AgentWebSocketBridge'] = None):
        """Initialize tool dispatcher with optional AgentWebSocketBridge support.
        
        Args:
            tools: List of tools to register initially
            websocket_bridge: AgentWebSocketBridge for real-time notifications (critical for chat)
        """
        self._init_components(websocket_bridge)
        self._register_initial_tools(tools)
    
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
        """Register a tool function with the dispatcher - public interface for tests."""
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
        """Dispatch tool execution with proper typing"""
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
        """Dispatch a tool with parameters - method expected by sub-agents"""
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
        
        RECOMMENDED: Use this method for new code instead of creating ToolDispatcher directly.
        This method creates proper per-request isolation and eliminates global state issues.
        
        Args:
            user_context: UserExecutionContext for complete isolation
            tools: Optional list of tools to register initially
            websocket_manager: Optional WebSocket manager for event routing
            
        Returns:
            RequestScopedToolDispatcher: Isolated dispatcher for this request
            
        Raises:
            ValueError: If user_context is invalid or dependencies are unavailable
        """
        # Import here to avoid circular imports
        from netra_backend.app.agents.tool_executor_factory import create_isolated_tool_dispatcher
        
        logger.info(f"🏭 Creating request-scoped dispatcher for user {user_context.user_id}")
        
        return await create_isolated_tool_dispatcher(
            user_context=user_context,
            tools=tools,
            websocket_manager=websocket_manager
        )
    
    @staticmethod
    async def create_scoped_dispatcher_context(
        user_context,  # UserExecutionContext type hint avoided
        tools: List[BaseTool] = None,
        websocket_manager = None  # WebSocketManager type hint avoided
    ):
        """Create scoped dispatcher context manager with automatic cleanup.
        
        RECOMMENDED: Use this for request handling to ensure proper cleanup.
        
        Args:
            user_context: UserExecutionContext for complete isolation
            tools: Optional list of tools to register initially
            websocket_manager: Optional WebSocket manager for event routing
            
        Returns:
            AsyncContextManager: Scoped dispatcher with automatic cleanup
            
        Example:
            async with ToolDispatcher.create_scoped_dispatcher_context(context) as dispatcher:
                result = await dispatcher.dispatch("my_tool", param1="value1")
                # Automatic cleanup happens here
        """
        # Import here to avoid circular imports
        from netra_backend.app.agents.tool_executor_factory import isolated_tool_dispatcher_scope
        
        logger.info(f"🏭 Creating scoped dispatcher context for user {user_context.user_id}")
        
        return isolated_tool_dispatcher_scope(
            user_context=user_context,
            tools=tools,
            websocket_manager=websocket_manager
        )
    
    # ===================== MIGRATION AND COMPATIBILITY METHODS =====================
    
    def _emit_global_state_warning(self, method_name: str) -> None:
        """Emit warning about global state usage."""
        warnings.warn(
            f"ToolDispatcher.{method_name}() uses global state and may cause user isolation issues. "
            f"Consider using ToolDispatcher.create_request_scoped_dispatcher() for new code. "
            f"See netra_backend/app/agents/request_scoped_tool_dispatcher.py for details.",
            UserWarning,
            stacklevel=3
        )
        
        logger.warning(f"⚠️ GLOBAL STATE USAGE: {method_name} called on shared ToolDispatcher instance")
        logger.warning(f"⚠️ This may cause user isolation issues in concurrent scenarios")
        logger.warning(f"⚠️ Consider migrating to RequestScopedToolDispatcher for better isolation")
    
    async def dispatch_with_isolation_warning(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """Dispatch tool execution with isolation warning."""
        self._emit_global_state_warning("dispatch")
        return await self.dispatch(tool_name, **kwargs)
    
    async def dispatch_tool_with_isolation_warning(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> ToolDispatchResponse:
        """Dispatch tool with state and isolation warning."""
        self._emit_global_state_warning("dispatch_tool")
        return await self.dispatch_tool(tool_name, parameters, state, run_id)
    
    def is_using_global_state(self) -> bool:
        """Check if this dispatcher is using global state (shared executor)."""
        return hasattr(self, 'executor') and hasattr(self.executor, 'websocket_bridge')
    
    def get_isolation_status(self) -> Dict[str, Any]:
        """Get isolation status for debugging and monitoring."""
        return {
            'is_global_instance': self.is_using_global_state(),
            'websocket_bridge_shared': self.get_websocket_bridge() is not None,
            'has_websocket_support': self.has_websocket_support,
            'executor_type': type(self.executor).__name__ if hasattr(self, 'executor') else None,
            'warning_needed': self.is_using_global_state(),
            'recommended_migration': 'RequestScopedToolDispatcher'
        }
    
