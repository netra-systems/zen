"""Core dispatcher logic and initialization for tool dispatching."""
import time
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
    """Core tool dispatcher with modular architecture
    
    DEPRECATED WARNING: Direct instantiation of ToolDispatcher creates global state risks
    and may cause user isolation issues in concurrent environments.
    
    RECOMMENDED MIGRATION PATH:
    1. Use ToolDispatcher.create_request_scoped_dispatcher() for new code
    2. Use ToolDispatcher.create_scoped_dispatcher_context() for request handling
    3. Migrate existing code to request-scoped patterns to prevent user data leaks
    
    REMOVAL TIMELINE: Global state methods will be deprecated in version 2.1.0
    and removed in version 3.0.0 (planned for Q2 2025).
    
    CRITICAL SECURITY NOTES:
    - Direct instantiation shares tool state between concurrent requests
    - WebSocket bridges may deliver events to wrong users
    - User context isolation is not guaranteed
    - Memory leaks possible with long-running processes
    """
    
    def __init__(self, tools: List[BaseTool] = None, websocket_bridge: Optional['AgentWebSocketBridge'] = None):
        """Initialize tool dispatcher with optional AgentWebSocketBridge support.
        
        DEPRECATED: This constructor creates global state that may cause user isolation issues.
        Use create_request_scoped_dispatcher() or create_scoped_dispatcher_context() instead.
        
        Args:
            tools: List of tools to register initially
            websocket_bridge: AgentWebSocketBridge for real-time notifications (critical for chat)
            
        Migration Guide:
            # OLD (unsafe global pattern):
            dispatcher = ToolDispatcher(tools, websocket_bridge)
            
            # NEW (safe request-scoped pattern):
            dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
                user_context=user_context,
                tools=tools,
                websocket_manager=websocket_manager
            )
            
            # OR use context manager for automatic cleanup:
            async with ToolDispatcher.create_scoped_dispatcher_context(user_context) as dispatcher:
                result = await dispatcher.dispatch("my_tool", param="value")
        """
        # Emit deprecation warning for direct instantiation
        warnings.warn(
            "Direct ToolDispatcher instantiation is deprecated and may cause user isolation issues. "
            "Use ToolDispatcher.create_request_scoped_dispatcher() for new code or "
            "ToolDispatcher.create_scoped_dispatcher_context() for request handling. "
            "Global state will be removed in v3.0.0 (Q2 2025). "
            "See netra_backend/app/agents/request_scoped_tool_dispatcher.py for migration examples.",
            DeprecationWarning,
            stacklevel=2
        )
        
        logger.warning("🚨 DEPRECATED: ToolDispatcher direct instantiation uses global state")
        logger.warning("⚠️ This may cause user isolation issues in concurrent scenarios")
        logger.warning("📋 MIGRATION: Use create_request_scoped_dispatcher() for safer patterns")
        logger.warning("📅 REMOVAL: Global state will be removed in v3.0.0 (Q2 2025)")
        
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
        """Register a tool function with the dispatcher - public interface for tests.
        
        DEPRECATED: Registering tools on global dispatcher instance may cause user isolation issues.
        Tools registered on global instances are shared across all users and requests.
        
        SECURITY RISKS with global tool registration:
        - Tools become available to all users (potential privilege escalation)
        - Tool state shared between concurrent requests
        - No user-specific tool configuration possible
        - Memory leaks from tools that don't clean up properly
        
        Migration Example:
            # OLD (unsafe global registration):
            dispatcher.register_tool("my_tool", my_tool_func)
            
            # NEW (safe request-scoped registration):
            async with ToolDispatcher.create_scoped_dispatcher_context(user_context) as dispatcher:
                dispatcher.register_tool("my_tool", my_tool_func)  # Scoped to this request only
        """
        # Emit deprecation warning
        warnings.warn(
            f"ToolDispatcher.register_tool() called on global instance for tool '{tool_name}'. "
            f"This registers the tool globally for all users and may cause security issues. "
            f"Use create_request_scoped_dispatcher() for user-specific tool registration. "
            f"Global state methods will be removed in v3.0.0 (Q2 2025).",
            DeprecationWarning,
            stacklevel=2
        )
        
        logger.warning(f"🚨 GLOBAL TOOL REGISTRATION: register_tool('{tool_name}') on shared ToolDispatcher")
        logger.warning("⚠️ This tool will be available to ALL users - potential security risk")
        logger.warning("📋 MIGRATION: Use RequestScopedToolDispatcher for user-specific tools")
        
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
        """Dispatch tool execution with proper typing
        
        DEPRECATED: This method uses global state and may cause user isolation issues.
        Use create_request_scoped_dispatcher() with proper user context instead.
        
        SECURITY WARNING: Global dispatcher state can lead to:
        - Tool results delivered to wrong users
        - User data leaking between concurrent requests
        - WebSocket events sent to incorrect sessions
        - Memory corruption in high-concurrency scenarios
        
        Migration Example:
            # OLD (unsafe):
            result = await dispatcher.dispatch("my_tool", param="value")
            
            # NEW (safe):
            async with ToolDispatcher.create_scoped_dispatcher_context(user_context) as dispatcher:
                result = await dispatcher.dispatch("my_tool", param="value")
        """
        # Emit deprecation warning
        warnings.warn(
            f"ToolDispatcher.dispatch() called on global instance for tool '{tool_name}'. "
            f"This may cause user isolation issues. Use create_request_scoped_dispatcher() instead. "
            f"Global state methods will be removed in v3.0.0 (Q2 2025).",
            DeprecationWarning,
            stacklevel=2
        )
        
        logger.warning(f"🚨 GLOBAL STATE USAGE: dispatch('{tool_name}') called on shared ToolDispatcher")
        logger.warning("⚠️ This may cause user isolation issues in concurrent scenarios")
        logger.warning("📋 MIGRATION: Use RequestScopedToolDispatcher for better isolation")
        
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
        """Dispatch a tool with parameters - method expected by sub-agents
        
        DEPRECATED: This method uses global state and may cause user isolation issues.
        Use create_request_scoped_dispatcher() with proper user context instead.
        
        CRITICAL SECURITY RISKS with global state:
        - Agent state may leak between users in concurrent requests
        - Run IDs may be mixed up between different user sessions
        - Tool execution may happen in wrong user context
        - Memory corruption possible with shared DeepAgentState
        
        Migration Example:
            # OLD (unsafe global state):
            response = await dispatcher.dispatch_tool(tool_name, params, state, run_id)
            
            # NEW (safe request-scoped):
            async with ToolDispatcher.create_scoped_dispatcher_context(user_context) as dispatcher:
                response = await dispatcher.dispatch_tool(tool_name, params, state, run_id)
        """
        # Emit deprecation warning
        warnings.warn(
            f"ToolDispatcher.dispatch_tool() called on global instance for tool '{tool_name}' with run_id '{run_id}'. "
            f"This may cause user isolation issues and agent state leaks. "
            f"Use create_request_scoped_dispatcher() instead. "
            f"Global state methods will be removed in v3.0.0 (Q2 2025).",
            DeprecationWarning,
            stacklevel=2
        )
        
        logger.warning(f"🚨 GLOBAL STATE USAGE: dispatch_tool('{tool_name}', run_id='{run_id}') on shared ToolDispatcher")
        logger.warning("⚠️ This may cause agent state leaks and user isolation issues")
        logger.warning("📋 MIGRATION: Use RequestScopedToolDispatcher for proper user context isolation")
        
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
        
        🟢 RECOMMENDED SECURE PATTERN: Use this method for new code instead of ToolDispatcher().
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
            # Secure pattern - each user gets isolated dispatcher
            dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
                user_context=user_context,
                tools=user_specific_tools,
                websocket_manager=websocket_manager
            )
            result = await dispatcher.dispatch("my_tool", param="value")
        """
        # Import here to avoid circular imports
        from netra_backend.app.agents.tool_executor_factory import create_isolated_tool_dispatcher
        
        logger.info(f"🏭✅ Creating SECURE request-scoped dispatcher for user {user_context.user_id}")
        logger.info("🔒 User context isolation enabled - no global state risks")
        
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
        
        🟢 RECOMMENDED SECURE PATTERN: Use this for request handling with guaranteed cleanup.
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
            # RECOMMENDED PATTERN - automatic cleanup guaranteed
            async with ToolDispatcher.create_scoped_dispatcher_context(user_context) as dispatcher:
                # All operations are user-scoped and secure
                result = await dispatcher.dispatch("my_tool", param="value")
                tool_result = await dispatcher.dispatch_tool("other_tool", params, state, run_id)
                # Automatic cleanup happens here - no memory leaks
                
        ⚠️ IMPORTANT: Always use this context manager for request handling to ensure:
        - User data doesn't leak between requests
        - WebSocket events are properly routed
        - Resources are cleaned up even if exceptions occur
        """
        # Import here to avoid circular imports
        from netra_backend.app.agents.tool_executor_factory import isolated_tool_dispatcher_scope
        
        logger.info(f"🏭✅ Creating SECURE scoped dispatcher context for user {user_context.user_id}")
        logger.info("🔒 Automatic cleanup enabled - memory and security safe")
        
        return isolated_tool_dispatcher_scope(
            user_context=user_context,
            tools=tools,
            websocket_manager=websocket_manager
        )
    
    # ===================== MIGRATION AND COMPATIBILITY METHODS =====================
    
    @staticmethod
    def detect_unsafe_usage_patterns() -> Dict[str, Any]:
        """Detect unsafe ToolDispatcher usage patterns in the current call stack.
        
        This utility method helps identify code that's using deprecated global patterns.
        Useful for migration assessment and security audits.
        
        Returns:
            Dict containing analysis of current usage patterns and security risks
            
        Example:
            security_analysis = ToolDispatcher.detect_unsafe_usage_patterns()
            if security_analysis['has_unsafe_patterns']:
                logger.warning(f"Found unsafe patterns: {security_analysis['risks']}")
        """
        import inspect
        import traceback
        
        analysis = {
            'has_unsafe_patterns': False,
            'risks': [],
            'call_stack_analysis': [],
            'migration_recommendations': []
        }
        
        # Analyze call stack for unsafe patterns
        try:
            stack = inspect.stack()
            for frame_info in stack[1:]:  # Skip current frame
                filename = frame_info.filename
                line_number = frame_info.lineno
                function_name = frame_info.function
                
                # Check for direct ToolDispatcher instantiation
                if 'ToolDispatcher(' in str(frame_info.code_context):
                    analysis['has_unsafe_patterns'] = True
                    analysis['risks'].append(f"Direct ToolDispatcher instantiation in {filename}:{line_number}")
                    analysis['migration_recommendations'].append(
                        f"Replace ToolDispatcher() with ToolDispatcher.create_request_scoped_dispatcher() "
                        f"at {filename}:{line_number}"
                    )
                
                analysis['call_stack_analysis'].append({
                    'file': filename,
                    'line': line_number,
                    'function': function_name,
                    'context': str(frame_info.code_context) if frame_info.code_context else None
                })
        except Exception as e:
            analysis['call_stack_analysis'] = [f"Error analyzing call stack: {e}"]
        
        return analysis
    
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
            'recommended_migration': 'RequestScopedToolDispatcher',
            'security_risks': self._assess_security_risks(),
            'migration_urgency': 'HIGH' if self.is_using_global_state() else 'LOW'
        }
    
    def _assess_security_risks(self) -> List[str]:
        """Assess security risks of current dispatcher configuration."""
        risks = []
        
        if self.is_using_global_state():
            risks.append("Global state may cause user isolation issues")
            risks.append("WebSocket events may be delivered to wrong users")
            risks.append("Tool state shared between concurrent requests")
        
        if self.get_websocket_bridge() is None:
            risks.append("WebSocket bridge is None - events will be lost")
        
        if hasattr(self, 'registry') and len(self.registry.tools) > 0:
            risks.append(f"Global tool registry has {len(self.registry.tools)} tools accessible to all users")
        
        return risks
    
    async def force_secure_migration_check(self) -> Dict[str, Any]:
        """Force a security check and provide migration guidance.
        
        This method performs a comprehensive security assessment of the current
        ToolDispatcher instance and provides specific migration guidance.
        
        Returns:
            Dict with security analysis and specific migration steps
        """
        logger.warning("🔍 SECURITY AUDIT: Performing forced migration check")
        
        analysis = {
            'timestamp': time.time(),
            'security_status': 'UNSAFE' if self.is_using_global_state() else 'SAFE',
            'isolation_status': self.get_isolation_status(),
            'usage_patterns': self.detect_unsafe_usage_patterns(),
            'migration_required': self.is_using_global_state(),
            'migration_steps': []
        }
        
        if self.is_using_global_state():
            analysis['migration_steps'] = [
                "1. Replace ToolDispatcher() with ToolDispatcher.create_request_scoped_dispatcher()",
                "2. Ensure user_context is properly provided to factory method",
                "3. Use async context manager for automatic cleanup",
                "4. Test concurrent request handling to verify user isolation",
                "5. Monitor logs for remaining deprecation warnings"
            ]
            
            logger.error("🚨 SECURITY RISK: Global ToolDispatcher instance detected")
            logger.error("⚠️ Migration required to prevent user isolation issues")
        else:
            logger.info("✅ SECURITY OK: Using safe request-scoped patterns")
        
        return analysis
    
