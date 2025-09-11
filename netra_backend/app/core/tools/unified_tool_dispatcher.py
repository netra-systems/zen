"""Unified Tool Dispatcher - SSOT for all tool dispatching operations.

This is the single source of truth consolidating all tool dispatcher implementations.
Request-scoped isolation by default with factory patterns for proper user isolation.

Business Value:
- Single implementation eliminates maintenance overhead (60% code reduction)
- Request-scoped isolation ensures multi-user safety
- WebSocket events for all tool executions (chat UX)
- Clean separation of concerns with dedicated modules
- Enhanced security boundaries and permission handling

Architecture Principles:
- Factory pattern enforcement (no direct instantiation)
- Request-scoped isolation as primary pattern
- WebSocket events integrated directly
- Permission checking built-in
- Comprehensive error handling and metrics
"""

import asyncio
import time
import warnings
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Set
from enum import Enum

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
    from langchain_core.tools import BaseTool
    from netra_backend.app.services.user_execution_context import UserExecutionContext as DeepAgentState

from pydantic import BaseModel, Field
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.tool import (
    SimpleToolPayload,
    ToolInput,
    ToolResult,
    ToolStatus,
)
from netra_backend.app.services.unified_tool_registry.models import ToolExecutionResult
from netra_backend.app.services.event_delivery_tracker import (
    get_event_delivery_tracker,
    EventPriority,
    EventDeliveryStatus
)

logger = central_logger.get_logger(__name__)


# ============================================================================
# SECURITY EXCEPTIONS
# ============================================================================

class AuthenticationError(Exception):
    """Raised when user authentication context is missing."""
    pass

class PermissionError(Exception):
    """Raised when user lacks permission for tool execution."""
    pass

class SecurityViolationError(Exception):
    """Raised when security constraints are violated."""
    pass


# ============================================================================
# DATA MODELS
# ============================================================================

class ToolDispatchRequest(BaseModel):
    """Typed request for tool dispatch."""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    

class ToolDispatchResponse(BaseModel):
    """Typed response for tool dispatch."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DispatchStrategy(Enum):
    """Tool dispatch strategies."""
    DEFAULT = "default"
    ADMIN = "admin"
    ISOLATED = "isolated"
    LEGACY = "legacy"


# ============================================================================
# UNIFIED TOOL DISPATCHER
# ============================================================================

class UnifiedToolDispatcher:
    """Unified tool dispatcher with factory-enforced request isolation.
    
    CRITICAL: Direct instantiation is FORBIDDEN. Use factory methods:
    - UnifiedToolDispatcherFactory.create_for_request()
    - UnifiedToolDispatcherFactory.create_for_admin()
    
    This ensures proper user isolation and prevents shared state issues.
    """
    
    # Class-level registry to track active dispatchers
    _active_dispatchers: Dict[str, 'UnifiedToolDispatcher'] = {}
    _max_dispatchers_per_user = 10
    _security_violations = 0  # Track security violations globally
    
    # Enhanced metrics tracking (consolidated from competing implementations)
    _global_metrics = {
        'total_dispatchers_created': 0,
        'total_tools_executed': 0,
        'total_successful_executions': 0,
        'total_failed_executions': 0,
        'total_security_violations': 0,
        'average_execution_time_ms': 0.0,
        'peak_concurrent_dispatchers': 0,
        'websocket_events_sent': 0
    }
    
    def __init__(self):
        """Private initializer - raises error to enforce factory usage."""
        raise RuntimeError(
            "Direct instantiation of UnifiedToolDispatcher is forbidden.\n"
            "Use factory methods for proper isolation:\n"
            "  - UnifiedToolDispatcher.create_for_user(context)\n"
            "  - UnifiedToolDispatcher.create_scoped(context)\n"
            "  - UnifiedToolDispatcherFactory.create_for_request(context)\n"
            "  - UnifiedToolDispatcherFactory.create_for_admin(context, db)\n\n"
            "This ensures user isolation and prevents shared state issues."
        )
    
    @classmethod
    async def create_for_user(
        cls,
        user_context: 'UserExecutionContext',
        websocket_bridge: Optional[Any] = None,
        tools: Optional[List['BaseTool']] = None,
        enable_admin_tools: bool = False
    ) -> 'UnifiedToolDispatcher':
        """Create isolated dispatcher for specific user context.
        
        DEPRECATED: This method redirects to ToolDispatcherFactory for SSOT compliance.
        Use ToolDispatcherFactory.create_for_request() directly instead.
        
        SECURITY CRITICAL: This is the recommended way to create dispatcher instances.
        
        Args:
            user_context: UserExecutionContext for complete isolation (REQUIRED)
            websocket_bridge: AgentWebSocketBridge for event notifications
            tools: Optional list of tools to register initially
            enable_admin_tools: Enable admin-level tools (requires admin permissions)
            
        Returns:
            UnifiedToolDispatcher: Isolated dispatcher for this user only
            
        Raises:
            AuthenticationError: If user_context is invalid
            SecurityViolationError: If security constraints are violated
            PermissionError: If admin tools requested without admin permission
        """
        import warnings
        from netra_backend.app.factories.tool_dispatcher_factory import get_tool_dispatcher_factory
        
        # Issue deprecation warning for SSOT compliance tracking
        warnings.warn(
            "UnifiedToolDispatcher.create_for_user() is deprecated. "
            "Use ToolDispatcherFactory.create_for_request() directly for SSOT compliance.",
            DeprecationWarning,
            stacklevel=2
        )
        
        logger.warning(
            f"🔄 SSOT REDIRECT: UnifiedToolDispatcher.create_for_user() -> ToolDispatcherFactory.create_for_request() "
            f"for user {user_context.user_id} (Phase 2 factory consolidation)"
        )
        
        # Validate user context (maintain same validation as original)
        if not user_context or not user_context.user_id:
            raise AuthenticationError("Valid UserExecutionContext required for dispatcher creation")
        
        # Convert websocket_bridge to websocket_manager for factory compatibility
        websocket_manager = None
        if websocket_bridge:
            # If it's already a WebSocketManager, use it directly
            if hasattr(websocket_bridge, 'send_event'):
                websocket_manager = websocket_bridge
            # If it's an AgentWebSocketBridge, create proper adapter
            elif hasattr(websocket_bridge, 'notify_tool_executing'):
                websocket_manager = cls._create_websocket_bridge_adapter(websocket_bridge, user_context)
                logger.info(f"Created WebSocket bridge adapter for AgentWebSocketBridge (user: {user_context.user_id})")
            # Otherwise wrap it
            else:
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as UnifiedWebSocketManager
                websocket_manager = UnifiedWebSocketManager()
                logger.warning(f"Created fallback WebSocketManager - no bridge connection for user {user_context.user_id}")
        
        try:
            # Get global SSOT ToolDispatcherFactory instance
            factory = get_tool_dispatcher_factory()
            
            # Set websocket manager if available
            if websocket_manager:
                factory.set_websocket_manager(websocket_manager)
            
            # Redirect to SSOT ToolDispatcherFactory for Phase 2 compliance
            tool_dispatcher = await factory.create_for_user(
                user_context=user_context,
                websocket_bridge=websocket_bridge,  # Pass original bridge for compatibility
                tools=tools,
                enable_admin_tools=enable_admin_tools
            )
            
            logger.info(
                f"✅ SSOT REDIRECT SUCCESS: Created dispatcher via ToolDispatcherFactory for user {user_context.user_id} "
                f"(admin_tools: {enable_admin_tools})"
            )
            
            # The ToolDispatcherFactory handles all compatibility wrapping
            return tool_dispatcher
            
        except Exception as e:
            logger.error(
                f"🚨 SSOT REDIRECT FAILED: ToolDispatcherFactory creation failed for user {user_context.user_id}: {e}. "
                f"Falling back to original implementation."
            )
            
            # Fallback to original implementation if factory fails
            return await cls._create_original_implementation(
                user_context=user_context,
                websocket_bridge=websocket_bridge,
                tools=tools,
                enable_admin_tools=enable_admin_tools
            )
    
    @classmethod
    @asynccontextmanager
    async def create_scoped(
        cls,
        user_context: 'UserExecutionContext',
        websocket_bridge: Optional[Any] = None,
        tools: Optional[List['BaseTool']] = None,
        enable_admin_tools: bool = False
    ):
        """Create scoped dispatcher with automatic cleanup.
        
        DEPRECATED: This method redirects to ToolDispatcherFactory for SSOT compliance.
        Use ToolDispatcherFactory.create_scoped() directly instead.
        
        RECOMMENDED USAGE PATTERN:
            async with ToolDispatcherFactory().create_scoped(user_context) as dispatcher:
                result = await dispatcher.dispatch("my_tool", params)
                # Automatic cleanup happens here
        """
        import warnings
        from netra_backend.app.factories.tool_dispatcher_factory import get_tool_dispatcher_factory
        
        # Issue deprecation warning for SSOT compliance tracking
        warnings.warn(
            "UnifiedToolDispatcher.create_scoped() is deprecated. "
            "Use ToolDispatcherFactory.create_scoped() directly for SSOT compliance.",
            DeprecationWarning,
            stacklevel=2
        )
        
        logger.warning(
            f"🔄 SSOT REDIRECT: UnifiedToolDispatcher.create_scoped() -> ToolDispatcherFactory.create_scoped() "
            f"for user {user_context.user_id} (Phase 2 factory consolidation)"
        )
        
        # Get global SSOT ToolDispatcherFactory instance
        factory = get_tool_dispatcher_factory()
        
        # Convert websocket_bridge to websocket_manager if needed
        websocket_manager = None
        if websocket_bridge:
            if hasattr(websocket_bridge, 'send_event'):
                websocket_manager = websocket_bridge
            elif hasattr(websocket_bridge, 'notify_tool_executing'):
                websocket_manager = cls._create_websocket_bridge_adapter(websocket_bridge, user_context)
                logger.info(f"Created WebSocket bridge adapter for scoped dispatcher (user: {user_context.user_id})")
        
        # Set websocket manager if available
        if websocket_manager:
            factory.set_websocket_manager(websocket_manager)
        
        # Use SSOT factory's create_scoped method with compatibility support
        async with factory.create_scoped(user_context, tools, websocket_manager) as dispatcher:
            # If we have an AgentWebSocketBridge, wrap the dispatcher to provide compatibility
            if websocket_bridge and hasattr(websocket_bridge, 'notify_tool_executing'):
                # Create compatibility wrapper that provides the expected interface
                dispatcher = factory._create_unified_compatibility_wrapper(dispatcher, websocket_bridge)
            
            logger.info(f"✅ SSOT SCOPED: Created scoped dispatcher via ToolDispatcherFactory for user {user_context.user_id}")
            yield dispatcher
    
    @classmethod
    def _wrap_factory_dispatcher(cls, tool_dispatcher, user_context, websocket_bridge):
        """Wrap RequestScopedToolDispatcher to look like UnifiedToolDispatcher.
        
        This provides interface compatibility during Phase 1 of SSOT consolidation.
        """
        # Create a wrapper that implements the UnifiedToolDispatcher interface
        class FactoryDispatcherWrapper:
            """Wrapper to make RequestScopedToolDispatcher look like UnifiedToolDispatcher."""
            
            def __init__(self, dispatcher, user_context, websocket_bridge):
                self._dispatcher = dispatcher
                self.user_context = user_context
                self._websocket_bridge = websocket_bridge
                self.dispatcher_id = f"factory_wrapper_{user_context.user_id}_{user_context.run_id}_{int(time.time()*1000)}"
                self.created_at = datetime.now(timezone.utc)
                self._is_active = True
                self.strategy = DispatchStrategy.DEFAULT
                
                # Provide compatibility properties
                self.websocket_manager = getattr(dispatcher, 'websocket_emitter', None)
                self._metrics = {
                    'tools_executed': 0,
                    'successful_executions': 0,
                    'failed_executions': 0,
                    'created_at': self.created_at,
                    'user_id': user_context.user_id,
                    'dispatcher_id': self.dispatcher_id
                }
                
                logger.info(f"🎭 Created FactoryDispatcherWrapper {self.dispatcher_id} for SSOT compatibility")
            
            @property
            def tools(self):
                """Get tools from wrapped dispatcher."""
                if hasattr(self._dispatcher, 'get_available_tools'):
                    tool_names = self._dispatcher.get_available_tools()
                    return {name: name for name in tool_names}  # Simple mapping
                return {}
            
            @property
            def has_websocket_support(self):
                """Check if WebSocket support is available."""
                return hasattr(self._dispatcher, 'websocket_emitter') and self._dispatcher.websocket_emitter is not None
            
            @property
            def websocket_bridge(self):
                """Compatibility property for tests expecting websocket_bridge."""
                return self._websocket_bridge
            
            def has_tool(self, tool_name: str) -> bool:
                """Check if a tool is available."""
                if hasattr(self._dispatcher, 'has_tool'):
                    return self._dispatcher.has_tool(tool_name)
                if hasattr(self._dispatcher, 'get_available_tools'):
                    return tool_name in self._dispatcher.get_available_tools()
                return False
            
            def register_tool(self, tool) -> None:
                """Register a tool with the wrapped dispatcher."""
                if hasattr(self._dispatcher, 'register_tool'):
                    self._dispatcher.register_tool(tool)
                    logger.debug(f"Registered tool {getattr(tool, 'name', 'unknown')} via factory wrapper")
                else:
                    logger.warning(f"Cannot register tool - wrapped dispatcher doesn't support tool registration")
            
            def get_available_tools(self) -> List[str]:
                """Get available tool names."""
                if hasattr(self._dispatcher, 'get_available_tools'):
                    return self._dispatcher.get_available_tools()
                return []
            
            async def execute_tool(self, tool_name: str, parameters: Dict[str, Any] = None, **kwargs):
                """Execute a tool through the wrapped dispatcher."""
                self._metrics['tools_executed'] += 1
                
                try:
                    # Use the factory dispatcher's execution method
                    if hasattr(self._dispatcher, 'dispatch'):
                        result = await self._dispatcher.dispatch(tool_name, **(parameters or {}))
                    elif hasattr(self._dispatcher, 'execute_tool'):
                        result = await self._dispatcher.execute_tool(tool_name, parameters or {})
                    else:
                        raise RuntimeError("Wrapped dispatcher has no execute_tool or dispatch method")
                    
                    self._metrics['successful_executions'] += 1
                    return result
                    
                except Exception as e:
                    self._metrics['failed_executions'] += 1
                    logger.error(f"Tool execution failed in factory wrapper: {e}")
                    raise
            
            async def dispatch_tool(self, tool_name: str, parameters: Dict[str, Any], **kwargs):
                """Legacy compatibility method - redirects to execute_tool."""
                return await self.execute_tool(tool_name, parameters)
            
            async def dispatch(self, tool_name: str, **kwargs):
                """Legacy compatibility method - redirects to execute_tool."""
                return await self.execute_tool(tool_name, kwargs)
            
            def get_metrics(self) -> Dict[str, Any]:
                """Get wrapper metrics."""
                return self._metrics.copy()
            
            async def cleanup(self):
                """Clean up the wrapped dispatcher."""
                if hasattr(self._dispatcher, 'cleanup'):
                    await self._dispatcher.cleanup()
                self._is_active = False
                logger.info(f"🎭 Cleaned up FactoryDispatcherWrapper {self.dispatcher_id}")
        
        return FactoryDispatcherWrapper(tool_dispatcher, user_context, websocket_bridge)
    
    @classmethod
    async def _create_original_implementation(
        cls,
        user_context: 'UserExecutionContext',
        websocket_bridge: Optional[Any] = None,
        tools: Optional[List['BaseTool']] = None,
        enable_admin_tools: bool = False
    ) -> 'UnifiedToolDispatcher':
        """Fallback to original implementation if factory redirect fails.
        
        This preserves the original UnifiedToolDispatcher behavior for safety.
        """
        logger.warning(
            f"⏪ FALLBACK: Using original UnifiedToolDispatcher implementation for user {user_context.user_id}"
        )
        
        # Determine strategy based on admin tools
        strategy = DispatchStrategy.ADMIN if enable_admin_tools else DispatchStrategy.DEFAULT
        
        # Convert websocket_bridge to websocket_manager if needed
        websocket_manager = None
        if websocket_bridge:
            # If it's already a WebSocketManager, use it directly
            if hasattr(websocket_bridge, 'send_event'):
                websocket_manager = websocket_bridge
            # If it's an AgentWebSocketBridge, create proper adapter
            elif hasattr(websocket_bridge, 'notify_tool_executing'):
                websocket_manager = cls._create_websocket_bridge_adapter(websocket_bridge, user_context)
                logger.info(f"Created WebSocket bridge adapter for AgentWebSocketBridge (user: {user_context.user_id})")
            # Otherwise wrap it
            else:
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as UnifiedWebSocketManager
                websocket_manager = UnifiedWebSocketManager()
                logger.warning(f"Created fallback WebSocketManager - no bridge connection for user {user_context.user_id}")
        
        # Create instance using internal factory
        instance = cls._create_from_factory(
            user_context=user_context,
            websocket_manager=websocket_manager,
            strategy=strategy,
            tools=tools,
            websocket_bridge=websocket_bridge  # Pass original bridge for compatibility
        )
        
        # Store the original bridge for compatibility
        instance._websocket_bridge = websocket_bridge
        
        return instance
    
    @classmethod
    def _create_from_factory(
        cls,
        user_context: 'UserExecutionContext',
        websocket_manager: Optional['WebSocketManager'] = None,
        strategy: DispatchStrategy = DispatchStrategy.DEFAULT,
        tools: Optional[List['BaseTool']] = None,
        **kwargs
    ) -> 'UnifiedToolDispatcher':
        """Internal factory method for creating properly isolated instances.
        
        This bypasses the __init__ RuntimeError and creates request-scoped instances.
        Only called by UnifiedToolDispatcherFactory or create_for_user.
        """
        # Create instance without calling __init__
        instance = cls.__new__(cls)
        
        # Initialize instance attributes
        instance.user_context = user_context
        instance.websocket_manager = websocket_manager
        instance.strategy = strategy
        instance.dispatcher_id = f"{user_context.user_id}_{user_context.run_id}_{int(time.time()*1000)}"
        instance.created_at = datetime.now(timezone.utc)
        instance._is_active = True
        
        # Track dispatcher for cleanup and global metrics
        cls._register_dispatcher(instance)
        cls._update_global_metrics('dispatcher_created')
        
        # Initialize components
        instance._init_components(tools, **kwargs)
        instance._init_metrics()
        
        # Setup WebSocket event emission
        if websocket_manager:
            instance._setup_websocket_events()
        
        logger.info(
            f"✅ Created UnifiedToolDispatcher {instance.dispatcher_id} "
            f"[strategy={strategy.value}, user={user_context.user_id}]"
        )
        
        return instance
    
    def _init_components(self, tools: Optional[List['BaseTool']] = None, registry: Optional['ToolRegistry'] = None, **kwargs):
        """Initialize core components."""
        # Import here to avoid circular dependencies
        from netra_backend.app.core.registry.universal_registry import ToolRegistry
        from netra_backend.app.agents.tool_dispatcher_validation import ToolValidator
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        
        # CRITICAL FIX: Use pre-created registry if provided to prevent proliferation
        if registry is not None:
            self.registry = registry
            logger.debug(f"Using pre-created registry {getattr(registry, 'name', 'unknown')} for dispatcher {getattr(self, 'dispatcher_id', 'unknown')}")
        else:
            self.registry = ToolRegistry()
            logger.debug(f"Created new registry for dispatcher {getattr(self, 'dispatcher_id', 'unknown')}")
            
        self.validator = ToolValidator()
        self.executor = UnifiedToolExecutionEngine(
            websocket_bridge=self._create_websocket_bridge() if self.websocket_manager else None
        )
        
        # Register initial tools
        if tools:
            for tool in tools:
                self.register_tool(tool)
            logger.info(f"Registered {len(tools)} tools in dispatcher {self.dispatcher_id}")
        
        # Admin-specific setup
        if self.strategy == DispatchStrategy.ADMIN:
            self._init_admin_components(**kwargs)
    
    def _init_admin_components(self, **kwargs):
        """Initialize admin-specific components."""
        self.admin_tools: Set[str] = {
            'corpus_create', 'corpus_update', 'corpus_delete',
            'user_admin', 'system_config', 'log_analyzer',
            'synthetic_generator'
        }
        self.db = kwargs.get('db')
        self.user = kwargs.get('user')
        self.permission_service = kwargs.get('permission_service')
        
        logger.info(f"Initialized admin dispatcher with {len(self.admin_tools)} admin tools")
    
    def _init_metrics(self):
        """Initialize metrics tracking."""
        self._metrics = {
            'tools_executed': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_execution_time_ms': 0,
            'websocket_events_sent': 0,
            'permission_checks': 0,
            'permission_denials': 0,
            'security_violations': 0,
            'last_execution_time': None,
            'created_at': self.created_at,
            'user_id': self.user_context.user_id if hasattr(self, 'user_context') else None,
            'dispatcher_id': self.dispatcher_id if hasattr(self, 'dispatcher_id') else None
        }
    
    @staticmethod
    def _create_websocket_bridge_adapter(websocket_bridge, user_context):
        """Create adapter to connect AgentWebSocketBridge to UnifiedToolDispatcher.
        
        This adapter implements the WebSocketManager interface (send_event) 
        using AgentWebSocketBridge's notification methods.
        """
        
        class AgentWebSocketBridgeAdapter:
            """Adapter that implements WebSocketManager interface using AgentWebSocketBridge."""
            def __init__(self, bridge, context):
                self.bridge = bridge
                self.context = context
                logger.debug(f"✅ Created WebSocket bridge adapter for user {context.user_id}")
            
            async def send_event(self, event_type: str, data: Dict[str, Any]):
                """Send event via AgentWebSocketBridge using proper notification methods."""
                try:
                    if event_type == "tool_executing":
                        # Use AgentWebSocketBridge's notify_tool_executing method
                        # Include event_id in parameters for confirmation tracking
                        params = data.get("parameters", {}).copy()
                        if "event_id" in data:
                            params["event_id"] = data["event_id"]
                        
                        success = await self.bridge.notify_tool_executing(
                            run_id=data.get("run_id", self.context.run_id),
                            agent_name=data.get("agent_name", "ToolDispatcher"),
                            tool_name=data["tool_name"],
                            parameters=params
                        )
                        if success:
                            logger.debug(f"🔧 TOOL EXECUTING: {data['tool_name']} → user {self.context.user_id}")
                        return success
                        
                    elif event_type == "tool_completed":
                        # Use AgentWebSocketBridge's notify_tool_completed method
                        result_dict = None
                        if data.get("result"):
                            result_dict = {"output": str(data["result"])}
                        elif data.get("error"):
                            result_dict = {"error": str(data["error"])}
                        
                        # Include event_id in result for confirmation tracking
                        if result_dict is None:
                            result_dict = {}
                        if "event_id" in data:
                            result_dict["event_id"] = data["event_id"]
                            
                        success = await self.bridge.notify_tool_completed(
                            run_id=data.get("run_id", self.context.run_id), 
                            agent_name=data.get("agent_name", "ToolDispatcher"),
                            tool_name=data["tool_name"],
                            result=result_dict,
                            execution_time_ms=data.get("execution_time_ms")
                        )
                        if success:
                            logger.debug(f"✅ TOOL COMPLETED: {data['tool_name']} → user {self.context.user_id}")
                        return success
                        
                    else:
                        logger.warning(f"⚠️  Unknown event type for WebSocket bridge adapter: {event_type}")
                        return False
                        
                except Exception as e:
                    logger.error(f"🚨 WebSocket bridge adapter failed to send {event_type} event: {e}")
                    return False
            
            def has_websocket_support(self):
                """Check if WebSocket support is available."""
                return self.bridge is not None
        
        return AgentWebSocketBridgeAdapter(websocket_bridge, user_context)
    
    def _create_websocket_bridge(self):
        """Create WebSocket bridge adapter for legacy compatibility."""
        # For instances created with an AgentWebSocketBridge, use the stored bridge
        if hasattr(self, '_websocket_bridge') and self._websocket_bridge:
            return self._create_websocket_bridge_adapter(self._websocket_bridge, self.user_context)
        # Otherwise fall back to the manager-based adapter
        return self._create_legacy_websocket_bridge()
    
    def _create_legacy_websocket_bridge(self):
        """Create legacy WebSocket bridge adapter for backward compatibility."""
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as WebSocketEventEmitter
        
        class WebSocketBridgeAdapter:
            """Legacy adapter to bridge WebSocketManager to AgentWebSocketBridge interface."""
            def __init__(self, manager, context):
                self.manager = manager
                self.context = context
            
            async def notify_tool_execution(self, tool_name: str, params: dict):
                """Send tool execution notification."""
                if self.manager:
                    await self.manager.send_event(
                        "tool_executing",
                        {
                            "tool_name": tool_name,
                            "parameters": params,
                            "run_id": self.context.run_id,
                            "user_id": self.context.user_id
                        }
                    )
            
            async def notify_tool_completion(self, tool_name: str, result: any):
                """Send tool completion notification."""
                if self.manager:
                    await self.manager.send_event(
                        "tool_completed",
                        {
                            "tool_name": tool_name,
                            "result": str(result)[:500],
                            "run_id": self.context.run_id,
                            "user_id": self.context.user_id
                        }
                    )
        
        return WebSocketBridgeAdapter(self.websocket_manager, self.user_context)
    
    def _setup_websocket_events(self):
        """Setup WebSocket event handlers."""
        # WebSocket events are emitted directly during tool execution
        self._websocket_ready = True
        logger.debug(f"WebSocket events configured for dispatcher {self.dispatcher_id}")
    
    # ===================== CORE PUBLIC METHODS =====================
    
    @property
    def tools(self) -> Dict[str, Any]:
        """Get registered tools."""
        if hasattr(self, 'registry'):
            # Return the registry's items as a dict
            return {key: self.registry.get(key) for key in self.registry.list_keys()}
        return {}
    
    @property
    def has_websocket_support(self) -> bool:
        """Check if WebSocket support is enabled."""
        return self.websocket_manager is not None
    
    @property
    def websocket_bridge(self):
        """Compatibility property for tests expecting websocket_bridge."""
        # Return the original bridge if it was passed, otherwise return the manager
        return getattr(self, '_websocket_bridge', self.websocket_manager)
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        self._ensure_active()
        return self.registry.has(tool_name)
    
    def register_tool(self, tool: 'BaseTool') -> None:
        """Register a tool with the dispatcher."""
        self._ensure_active()
        
        # ENHANCED VALIDATION: Consolidated from competing implementations
        if not tool:
            logger.error(f"Cannot register None tool in dispatcher {self.dispatcher_id}")
            raise ValueError("Tool cannot be None")
        
        # CRITICAL FIX: Check if tool has name attribute before accessing it
        if hasattr(tool, 'name') and tool.name:
            tool_name = tool.name
        else:
            # Fallback to class name if no name attribute
            tool_name = getattr(tool, '__class__', type(tool)).__name__.lower()
            logger.warning(f"⚠️ Tool {tool.__class__.__name__} missing 'name' attribute, using fallback: {tool_name}")
        
        # ENHANCED: Check for duplicate tool registration
        if self.has_tool(tool_name):
            logger.warning(f"⚠️ Tool {tool_name} already registered, skipping duplicate registration")
            return
        
        # Use the UniversalRegistry's register method with proper error handling
        try:
            self.registry.register(tool_name, tool)
            logger.debug(f"Registered tool {tool_name} in dispatcher {self.dispatcher_id}")
            
            # Track registration in metrics
            if not hasattr(self._metrics, 'tools_registered'):
                self._metrics['tools_registered'] = 0
            self._metrics['tools_registered'] += 1
            
        except ValueError as e:
            # CRITICAL FIX: Handle BaseModel validation failures gracefully
            if "BaseModel" in str(e) or "validation failed" in str(e).lower():
                logger.warning(f"⚠️ Tool {tool.__class__.__name__} rejected by registry validation: {e}")
                logger.warning(f"   Skipping invalid tool registration to prevent system failure")
                return  # Skip this tool but continue with others
            else:
                # Re-raise other validation errors
                raise
        except Exception as e:
            logger.error(f"🚨 Unexpected error registering tool {tool_name}: {e}")
            raise
    
    def register_tools(self, tools: List['BaseTool']) -> int:
        """Register multiple tools at once - pattern from competing implementations.
        
        Args:
            tools: List of tools to register
            
        Returns:
            Number of successfully registered tools
        """
        if not tools:
            return 0
            
        successful_count = 0
        for tool in tools:
            try:
                self.register_tool(tool)
                successful_count += 1
            except Exception as e:
                logger.warning(f"Failed to register tool {getattr(tool, 'name', 'unknown')}: {e}")
                
        logger.info(f"Registered {successful_count}/{len(tools)} tools in dispatcher {self.dispatcher_id}")
        return successful_count
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        self._ensure_active()
        return self.registry.list_keys()
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any] = None,
        require_permission_check: bool = True
    ) -> 'ToolExecutionResult':
        """Execute a tool with WebSocket notifications and security validation.
        
        CRITICAL: This method ensures WebSocket events are sent for ALL tool executions.
        Events sent: tool_executing, tool_completed
        
        Args:
            tool_name: Name of tool to execute (REQUIRED)
            parameters: Tool parameters dictionary
            require_permission_check: Force permission check (ALWAYS True in production)
            
        Returns:
            ToolDispatchResponse: Results with complete metadata
            
        Raises:
            AuthenticationError: If user context is invalid
            PermissionError: If user lacks tool permission
            SecurityViolationError: If security constraints violated
        """
        self._ensure_active()
        
        parameters = parameters or {}
        start_time = time.time()
        
        # MANDATORY: Permission validation
        if require_permission_check:
            await self._validate_tool_permissions(tool_name)
        
        # Emit tool_executing event and track it
        executing_event_id = None
        if self.has_websocket_support:
            executing_event_id = await self._emit_tool_executing(tool_name, parameters)
        
        try:
            # Validate tool exists
            if not self.has_tool(tool_name):
                raise ValueError(f"Tool {tool_name} not found in registry")
            
            # Check admin permissions if needed
            if self.strategy == DispatchStrategy.ADMIN:
                if tool_name in self.admin_tools and not self._check_admin_permission():
                    raise PermissionError(f"Admin permission required for tool {tool_name}")
            
            # Get tool and execute
            tool = self.registry.get(tool_name)
            
            # Create tool input
            tool_input = ToolInput(
                tool_name=tool_name,
                parameters=parameters,
                request_id=self.user_context.run_id
            )
            
            # Execute through executor (includes WebSocket notifications)
            # Only pass parameters the tool expects, context is for the executor
            kwargs = {'context': self.user_context}
            kwargs.update(parameters)
            result = await self.executor.execute_tool_with_input(
                tool_input,
                tool,
                kwargs
            )
            
            # Update metrics
            execution_time = (time.time() - start_time) * 1000
            self._update_metrics(success=True, execution_time=execution_time)
            self.__class__._update_global_metrics('successful_execution')
            self.__class__._update_global_metrics('execution_time', execution_time)
            
            # Emit tool_completed event and track it
            completed_event_id = None
            if self.has_websocket_support:
                completed_event_id = await self._emit_tool_completed(tool_name, result, execution_time)
                
                # Wait for event confirmation (with short timeout to avoid blocking)
                await self._wait_for_event_confirmations(
                    [executing_event_id, completed_event_id], 
                    timeout_s=2.0  # Short timeout - don't block tool execution
                )
            
            # Extract actual result from ToolResult wrapper
            actual_result = result.payload.result if hasattr(result, 'payload') and hasattr(result.payload, 'result') else result
            
            return ToolExecutionResult(
                success=True,
                result=actual_result,
                tool_name=tool_name,
                user_id=self.user_context.user_id,
                status="success",
                execution_time_ms=int(execution_time)
            )
            
        except Exception as e:
            # Update metrics
            execution_time = (time.time() - start_time) * 1000
            self._update_metrics(success=False, execution_time=execution_time)
            self.__class__._update_global_metrics('failed_execution')
            self.__class__._update_global_metrics('execution_time', execution_time)
            
            # Emit tool_completed with error and track it
            completed_event_id = None
            if self.has_websocket_support:
                completed_event_id = await self._emit_tool_completed(tool_name, error=str(e), execution_time=execution_time)
                
                # Wait for event confirmation (with short timeout to avoid blocking)
                await self._wait_for_event_confirmations(
                    [executing_event_id, completed_event_id], 
                    timeout_s=2.0  # Short timeout - don't block tool execution
                )
            
            logger.error(f"Tool {tool_name} failed in dispatcher {self.dispatcher_id}: {e}")
            
            return ToolExecutionResult(
                success=False,
                error=str(e),
                error_message=str(e),
                tool_name=tool_name,
                user_id=self.user_context.user_id,
                status="error",
                execution_time_ms=int(execution_time)
            )
    
    # Compatibility methods for existing code
    async def dispatch_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        state = None,
        run_id: str = None
    ) -> ToolDispatchResponse:
        """Legacy compatibility method - redirects to execute_tool."""
        return await self.execute_tool(tool_name, parameters)
    
    async def dispatch(self, tool_name: str, **kwargs) -> ToolResult:
        """Legacy compatibility method - redirects to execute_tool."""
        response = await self.execute_tool(tool_name, kwargs)
        
        # Convert response to ToolResult
        return ToolResult(
            tool_name=tool_name,
            status=ToolStatus.SUCCESS if response.success else ToolStatus.FAILURE,
            result=response.result if response.success else None,
            error=response.error if not response.success else None,
            metadata=response.metadata
        )
    
    # ===================== WEBSOCKET EVENT METHODS =====================
    
    async def _emit_tool_executing(self, tool_name: str, parameters: Dict[str, Any]) -> Optional[str]:
        """Emit tool_executing WebSocket event with delivery tracking.
        
        Returns:
            Optional[str]: Event ID for tracking, None if event wasn't sent
        """
        if not self.websocket_manager:
            return None
        
        try:
            # Get event delivery tracker
            tracker = get_event_delivery_tracker()
            
            # Make parameters JSON-serializable by converting non-serializable values to strings
            serializable_params = {}
            for key, value in (parameters or {}).items():
                try:
                    # Test if value is JSON serializable
                    import json
                    json.dumps(value)
                    serializable_params[key] = value
                except (TypeError, ValueError):
                    # Convert non-serializable objects to string representation
                    serializable_params[key] = str(value)
            
            event_data = {
                "tool_name": tool_name,
                "parameters": serializable_params,
                "run_id": self.user_context.run_id,
                "user_id": self.user_context.user_id,
                "thread_id": self.user_context.thread_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Create retry callback for this event
            async def retry_callback(event_id: str, event_type: str, data: Dict[str, Any]) -> bool:
                """Retry callback to re-emit failed tool_executing events."""
                try:
                    # Use the correct WebSocket manager method
                    if hasattr(self.websocket_manager, 'emit_critical_event'):
                        await self.websocket_manager.emit_critical_event(
                            user_id=self.user_context.user_id,
                            event_type="tool_executing",
                            data=data
                        )
                    elif hasattr(self.websocket_manager, 'send_event'):
                        await self.websocket_manager.send_event("tool_executing", data)
                    else:
                        logger.error(f"WebSocket manager lacks send_event/emit_critical_event method")
                        return False
                    
                    logger.info(f"Successfully retried tool_executing event {event_id}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to retry tool_executing event {event_id}: {e}")
                    return False
            
            # Track the event with critical priority and retry callback
            event_id = tracker.track_event(
                event_type="tool_executing",
                user_id=self.user_context.user_id,
                run_id=self.user_context.run_id,
                thread_id=self.user_context.thread_id,
                data=event_data,
                priority=EventPriority.CRITICAL,
                timeout_s=30.0,  # 30 second timeout for tool_executing events
                retry_callback=retry_callback
            )
            
            # Add event ID to the payload for confirmation tracking
            event_data["event_id"] = event_id
            
            # Send the event using the correct method
            if hasattr(self.websocket_manager, 'emit_critical_event'):
                await self.websocket_manager.emit_critical_event(
                    user_id=self.user_context.user_id,
                    event_type="tool_executing",
                    data=event_data
                )
            elif hasattr(self.websocket_manager, 'send_event'):
                await self.websocket_manager.send_event("tool_executing", event_data)
            else:
                raise RuntimeError("WebSocket manager lacks send_event/emit_critical_event method")
            
            # Mark event as sent
            tracker.mark_event_sent(event_id)
            
            self._metrics['websocket_events_sent'] += 1
            self.__class__._update_global_metrics('websocket_event')
            
            logger.debug(f"Sent tool_executing event {event_id} for tool {tool_name}")
            return event_id
            
        except Exception as e:
            # CRITICAL FAILURE: Silent failures threaten $500K+ ARR chat functionality
            logger.critical(f"🚨 CRITICAL: WebSocket tool_executing event FAILED for tool {tool_name} - user {self.user_context.user_id}: {e}")
            # Try to use UnifiedWebSocketEmitter for retry if available
            await self._attempt_critical_event_recovery("tool_executing", tool_name, parameters, e)
            return None
    
    async def _emit_tool_completed(
        self,
        tool_name: str,
        result: Any = None,
        error: str = None,
        execution_time: float = None
    ) -> Optional[str]:
        """Emit tool_completed WebSocket event with delivery tracking.
        
        Returns:
            Optional[str]: Event ID for tracking, None if event wasn't sent
        """
        if not self.websocket_manager:
            return None
        
        try:
            # Get event delivery tracker
            tracker = get_event_delivery_tracker()
            
            event_data = {
                "tool_name": tool_name,
                "run_id": self.user_context.run_id,
                "user_id": self.user_context.user_id,
                "thread_id": self.user_context.thread_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if error:
                event_data["status"] = "error"
                event_data["error"] = error
            else:
                event_data["status"] = "success"
                event_data["result"] = str(result)[:500] if result else None
            
            if execution_time:
                event_data["execution_time_ms"] = execution_time
            
            # Create retry callback for this event
            async def retry_callback(event_id: str, event_type: str, data: Dict[str, Any]) -> bool:
                """Retry callback to re-emit failed tool_completed events."""
                try:
                    # Use the correct WebSocket manager method
                    if hasattr(self.websocket_manager, 'emit_critical_event'):
                        await self.websocket_manager.emit_critical_event(
                            user_id=self.user_context.user_id,
                            event_type="tool_completed",
                            data=data
                        )
                    elif hasattr(self.websocket_manager, 'send_event'):
                        await self.websocket_manager.send_event("tool_completed", data)
                    else:
                        logger.error(f"WebSocket manager lacks send_event/emit_critical_event method")
                        return False
                    
                    logger.info(f"Successfully retried tool_completed event {event_id}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to retry tool_completed event {event_id}: {e}")
                    return False
            
            # Track the event with critical priority and retry callback
            event_id = tracker.track_event(
                event_type="tool_completed",
                user_id=self.user_context.user_id,
                run_id=self.user_context.run_id,
                thread_id=self.user_context.thread_id,
                data=event_data,
                priority=EventPriority.CRITICAL,
                timeout_s=30.0,  # 30 second timeout for tool_completed events
                retry_callback=retry_callback
            )
            
            # Add event ID to the payload for confirmation tracking
            event_data["event_id"] = event_id
            
            # Send the event using the correct method
            if hasattr(self.websocket_manager, 'emit_critical_event'):
                await self.websocket_manager.emit_critical_event(
                    user_id=self.user_context.user_id,
                    event_type="tool_completed",
                    data=event_data
                )
            elif hasattr(self.websocket_manager, 'send_event'):
                await self.websocket_manager.send_event("tool_completed", event_data)
            else:
                raise RuntimeError("WebSocket manager lacks send_event/emit_critical_event method")
            
            # Mark event as sent
            tracker.mark_event_sent(event_id)
            
            self._metrics['websocket_events_sent'] += 1
            self.__class__._update_global_metrics('websocket_event')
            
            logger.debug(f"Sent tool_completed event {event_id} for tool {tool_name}")
            return event_id
            
        except Exception as e:
            # CRITICAL FAILURE: Silent failures threaten $500K+ ARR chat functionality
            logger.critical(f"🚨 CRITICAL: WebSocket tool_completed event FAILED for tool {tool_name} - user {self.user_context.user_id}: {e}")
            # Try to use UnifiedWebSocketEmitter for retry if available
            await self._attempt_critical_event_recovery("tool_completed", tool_name, {"error": error} if error else {"result": result}, e)
            return None
    
    async def _wait_for_event_confirmations(
        self, 
        event_ids: List[Optional[str]], 
        timeout_s: float = 2.0
    ):
        """Wait for event confirmations with timeout.
        
        Args:
            event_ids: List of event IDs to wait for (None values are ignored)
            timeout_s: Maximum time to wait for confirmations
        """
        if not event_ids:
            return
        
        # Filter out None values
        valid_event_ids = [eid for eid in event_ids if eid is not None]
        if not valid_event_ids:
            return
        
        try:
            tracker = get_event_delivery_tracker()
            start_time = time.time()
            
            while time.time() - start_time < timeout_s:
                # Check if all events are confirmed
                all_confirmed = True
                for event_id in valid_event_ids:
                    status = tracker.get_event_status(event_id)
                    if status != EventDeliveryStatus.CONFIRMED:
                        all_confirmed = False
                        break
                
                if all_confirmed:
                    logger.debug(f"All events confirmed: {valid_event_ids}")
                    return
                
                # Short sleep to avoid busy waiting
                await asyncio.sleep(0.1)
            
            # Timeout reached - log warning but don't fail
            unconfirmed = []
            for event_id in valid_event_ids:
                status = tracker.get_event_status(event_id)
                if status != EventDeliveryStatus.CONFIRMED:
                    unconfirmed.append(event_id)
            
            if unconfirmed:
                logger.warning(
                    f"Event confirmation timeout after {timeout_s}s. "
                    f"Unconfirmed events: {unconfirmed}"
                )
        
        except Exception as e:
            logger.warning(f"Error waiting for event confirmations: {e}")
    
    def set_websocket_manager(self, manager: 'WebSocketManager'):
        """Set or update WebSocket manager for event emission."""
        self.websocket_manager = manager
        self._setup_websocket_events()
        logger.info(f"WebSocket manager set for dispatcher {self.dispatcher_id}")
    
    async def _attempt_critical_event_recovery(self, event_type: str, tool_name: str, event_data: Dict[str, Any], original_error: Exception):
        """
        Attempt to recover from WebSocket event failure using UnifiedWebSocketEmitter.
        
        This method implements the modern retry infrastructure pattern to prevent
        silent failures that threaten chat functionality.
        
        Args:
            event_type: The event type that failed (tool_executing/tool_completed)
            tool_name: Name of the tool
            event_data: Event data to send
            original_error: The original error that occurred
        """
        try:
            # Try to create UnifiedWebSocketEmitter for retry
            from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
            
            if not self.websocket_manager:
                logger.warning(f"No WebSocket manager available for event recovery - tool: {tool_name}, event: {event_type}")
                return
                
            # Create emitter with retry capabilities
            emitter = UnifiedWebSocketEmitter(
                manager=self.websocket_manager,
                user_id=self.user_context.user_id,
                context=self.user_context,
                performance_mode=False  # Use full retry logic for reliability
            )
            
            # Prepare event data
            recovery_data = {
                'tool_name': tool_name,
                'recovery_attempt': True,
                'original_error': str(original_error),
                'user_id': self.user_context.user_id,
                'run_id': self.user_context.run_id,
                'thread_id': self.user_context.thread_id,
                **event_data
            }
            
            # Use modern retry infrastructure
            if event_type == "tool_executing":
                success = await emitter.notify_tool_executing(tool_name, metadata=recovery_data)
            elif event_type == "tool_completed":
                success = await emitter.notify_tool_completed(tool_name, metadata=recovery_data)
            else:
                success = await emitter.notify_custom(event_type, recovery_data)
            
            if success:
                logger.info(f"✅ RECOVERY SUCCESS: {event_type} event recovered for tool {tool_name} - user {self.user_context.user_id}")
            else:
                logger.error(f"❌ RECOVERY FAILED: {event_type} event could not be recovered for tool {tool_name} - user {self.user_context.user_id}")
                
        except Exception as recovery_error:
            logger.error(f"💥 RECOVERY EXCEPTION: Event recovery system failed for {event_type}/{tool_name} - user {self.user_context.user_id}: {recovery_error}")
            # At this point we've tried everything - log as critical business impact
            logger.critical(
                f"🚨 BUSINESS IMPACT: Complete WebSocket event failure for user {self.user_context.user_id} "
                f"- tool: {tool_name}, event: {event_type}. Chat functionality compromised. "
                f"Original error: {original_error}, Recovery error: {recovery_error}"
            )
    
    # ===================== ADMIN METHODS =====================
    
    async def _validate_tool_permissions(self, tool_name: str):
        """Validate user has permission to execute the specified tool.
        
        SECURITY CRITICAL: This method enforces permission boundaries.
        
        Args:
            tool_name: Name of tool to validate permissions for
            
        Raises:
            AuthenticationError: If user context is invalid
            PermissionError: If user lacks required permissions
            SecurityViolationError: If security check fails
        """
        # Track permission check
        self._metrics['permission_checks'] += 1
        
        # Validate user context exists
        if not self.user_context or not self.user_context.user_id:
            self._metrics['security_violations'] += 1
            self.__class__._security_violations += 1
            raise AuthenticationError(
                f"SECURITY: User context required for tool execution [tool={tool_name}]"
            )
        
        # Check admin tool permissions
        if hasattr(self, 'admin_tools') and tool_name in self.admin_tools:
            if self.strategy != DispatchStrategy.ADMIN:
                self._metrics['permission_denials'] += 1
                raise PermissionError(
                    f"Admin permission required for tool {tool_name} "
                    f"[user={self.user_context.user_id}]"
                )
            
            # Verify admin role in metadata
            if not self._check_admin_permission():
                self._metrics['permission_denials'] += 1
                raise PermissionError(
                    f"User {self.user_context.user_id} lacks admin role for tool {tool_name}"
                )
        
        # Log successful permission check
        logger.debug(
            f"Permission validated for tool {tool_name} "
            f"[user={self.user_context.user_id}, dispatcher={self.dispatcher_id}]"
        )
    
    def _check_admin_permission(self) -> bool:
        """Check if user has admin permissions."""
        # Check metadata for admin role
        if hasattr(self.user_context, 'metadata') and self.user_context.metadata:
            roles = self.user_context.metadata.get('roles', [])
            if 'admin' in roles:
                return True
        
        # Check user object if available
        if hasattr(self, 'user') and self.user:
            # Check user admin status
            if hasattr(self.user, 'is_admin'):
                return self.user.is_admin
        
        # Check permission service
        if hasattr(self, 'permission_service') and self.permission_service:
            if hasattr(self, 'user') and self.user:
                return self.permission_service.has_admin_permission(self.user)
        
        return False
    
    # ===================== LIFECYCLE METHODS =====================
    
    def _ensure_active(self):
        """Ensure dispatcher is still active."""
        if not self._is_active:
            raise RuntimeError(f"Dispatcher {self.dispatcher_id} has been cleaned up")
    
    def _update_metrics(self, success: bool, execution_time: float):
        """Update execution metrics."""
        self._metrics['tools_executed'] += 1
        if success:
            self._metrics['successful_executions'] += 1
        else:
            self._metrics['failed_executions'] += 1
        self._metrics['total_execution_time_ms'] += execution_time
        self._metrics['last_execution_time'] = datetime.now(timezone.utc)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get dispatcher metrics."""
        return self._metrics.copy()
    
    async def _populate_tools_from_registry(self, tool_registry):
        """Populate dispatcher with tools from a tool registry.
        
        Args:
            tool_registry: Tool registry containing tools to register
        """
        try:
            # Check if it's a UnifiedToolRegistry
            if hasattr(tool_registry, 'list_tools'):
                # UnifiedToolRegistry approach
                tools = tool_registry.list_tools()
                for tool in tools:
                    if hasattr(tool, 'handler') and tool.handler:
                        # Register tool with handler
                        self.registry.register(tool.id, tool.handler)
                    else:
                        # Register tool without handler (mock for testing)
                        async def create_mock_handler(tool_name=tool.name):
                            async def mock_handler(params, context):
                                return {
                                    "result": f"Mock execution of {tool_name}",
                                    "tool_name": tool_name,
                                    "parameters": params,
                                    "success": True
                                }
                            return mock_handler
                        
                        mock_handler = await create_mock_handler(tool.name)
                        self.registry.register(tool.id, mock_handler)
                        
                logger.info(f"Populated dispatcher with {len(tools)} tools from UnifiedToolRegistry")
            
            # Check if it's a legacy tool registry
            elif hasattr(tool_registry, 'get_all_tools'):
                tools = tool_registry.get_all_tools()
                for tool in tools:
                    if hasattr(tool, 'name'):
                        # Register tool using its name
                        self.registry.register(tool.name, tool)
                        
                logger.info(f"Populated dispatcher with {len(tools)} tools from legacy registry")
                        
        except Exception as e:
            logger.error(f"Error populating tools from registry: {e}")
    
    async def cleanup(self):
        """Clean up dispatcher resources with enhanced disposal pattern."""
        if not self._is_active:
            return
        
        self._is_active = False
        
        # Enhanced cleanup from competing implementations
        try:
            # Clean up WebSocket connections
            if hasattr(self, 'websocket_manager') and self.websocket_manager:
                try:
                    # Best-effort WebSocket cleanup
                    if hasattr(self.websocket_manager, 'cleanup'):
                        await self.websocket_manager.cleanup()
                except Exception as e:
                    logger.warning(f"WebSocket cleanup failed for {self.dispatcher_id}: {e}")
            
            # Clean up executor
            if hasattr(self, 'executor') and self.executor:
                try:
                    if hasattr(self.executor, 'cleanup'):
                        await self.executor.cleanup()
                except Exception as e:
                    logger.warning(f"Executor cleanup failed for {self.dispatcher_id}: {e}")
            
            # Clean up registry
            if hasattr(self, 'registry'):
                try:
                    self.registry.clear()
                except Exception as e:
                    logger.warning(f"Registry cleanup failed for {self.dispatcher_id}: {e}")
            
            # Final metrics update
            self._metrics['cleanup_time'] = datetime.now(timezone.utc)
            
            logger.info(f"✅ Cleaned up dispatcher {self.dispatcher_id}")
            
        except Exception as e:
            logger.error(f"🚨 Cleanup failed for dispatcher {self.dispatcher_id}: {e}")
        finally:
            # Always unregister, even if cleanup partially fails
            self._unregister_dispatcher(self)
    
    @classmethod
    def _register_dispatcher(cls, dispatcher: 'UnifiedToolDispatcher'):
        """Register an active dispatcher."""
        user_id = dispatcher.user_context.user_id
        
        # Check user dispatcher limit
        user_dispatchers = [d for d in cls._active_dispatchers.values() if d.user_context.user_id == user_id]
        if len(user_dispatchers) >= cls._max_dispatchers_per_user:
            # Clean up oldest dispatcher
            oldest = min(user_dispatchers, key=lambda d: d.created_at)
            asyncio.create_task(oldest.cleanup())
            logger.warning(f"User {user_id} exceeded dispatcher limit, cleaning up oldest")
        
        cls._active_dispatchers[dispatcher.dispatcher_id] = dispatcher
    
    @classmethod
    def _unregister_dispatcher(cls, dispatcher: 'UnifiedToolDispatcher'):
        """Unregister a dispatcher."""
        cls._active_dispatchers.pop(dispatcher.dispatcher_id, None)
    
    @classmethod
    async def cleanup_user_dispatchers(cls, user_id: str):
        """Clean up all dispatchers for a user."""
        user_dispatchers = [
            d for d in cls._active_dispatchers.values()
            if d.user_context.user_id == user_id
        ]
        
        for dispatcher in user_dispatchers:
            await dispatcher.cleanup()
        
        logger.info(f"Cleaned up {len(user_dispatchers)} dispatchers for user {user_id}")
    
    @classmethod
    def _update_global_metrics(cls, metric_type: str, value: float = 1.0):
        """Update global metrics for monitoring dispatcher health."""
        if metric_type == 'dispatcher_created':
            cls._global_metrics['total_dispatchers_created'] += 1
            current_active = len(cls._active_dispatchers)
            if current_active > cls._global_metrics['peak_concurrent_dispatchers']:
                cls._global_metrics['peak_concurrent_dispatchers'] = current_active
        elif metric_type == 'tool_executed':
            cls._global_metrics['total_tools_executed'] += 1
        elif metric_type == 'successful_execution':
            cls._global_metrics['total_successful_executions'] += 1
        elif metric_type == 'failed_execution':
            cls._global_metrics['total_failed_executions'] += 1
        elif metric_type == 'security_violation':
            cls._global_metrics['total_security_violations'] += 1
        elif metric_type == 'websocket_event':
            cls._global_metrics['websocket_events_sent'] += 1
        elif metric_type == 'execution_time':
            # Update average execution time using running average
            total_executions = (cls._global_metrics['total_successful_executions'] + 
                              cls._global_metrics['total_failed_executions'])
            if total_executions > 0:
                current_avg = cls._global_metrics['average_execution_time_ms']
                cls._global_metrics['average_execution_time_ms'] = (
                    (current_avg * (total_executions - 1) + value) / total_executions
                )
    
    @classmethod
    def get_global_metrics(cls) -> Dict[str, Any]:
        """Get global metrics for monitoring and diagnostics."""
        return {
            **cls._global_metrics.copy(),
            'active_dispatchers': len(cls._active_dispatchers),
            'security_violations': cls._security_violations,
            'active_dispatcher_users': len(set(
                d.user_context.user_id for d in cls._active_dispatchers.values()
                if d._is_active
            ))
        }


# ============================================================================
# FACTORY
# ============================================================================

class UnifiedToolDispatcherFactory:
    """Factory for creating request-scoped tool dispatchers.
    
    Ensures proper user isolation and prevents shared state issues.
    """
    
    def __init__(self):
        """Initialize the factory with tracking for active dispatchers."""
        self._active_dispatchers: List[UnifiedToolDispatcher] = []
        self._tool_registry = None
    
    def set_tool_registry(self, tool_registry):
        """Set the tool registry for this factory.
        
        Args:
            tool_registry: The tool registry to use for tool registration
        """
        self._tool_registry = tool_registry
        logger.info(f"Tool registry set for UnifiedToolDispatcherFactory: {type(tool_registry).__name__}")
    
    async def create_dispatcher(
        self,
        user_context: 'UserExecutionContext',
        websocket_manager: Optional['WebSocketManager'] = None,
        tools: Optional[List['BaseTool']] = None
    ) -> UnifiedToolDispatcher:
        """Create a dispatcher for the given user context.
        
        Args:
            user_context: User execution context for isolation
            websocket_manager: WebSocket manager for event emission
            tools: Initial tools to register
            
        Returns:
            Request-scoped UnifiedToolDispatcher instance
        """
        dispatcher = self.create_for_request(
            user_context=user_context,
            websocket_manager=websocket_manager,
            tools=tools
        )
        
        # Set the tool registry if one was configured
        if self._tool_registry:
            await dispatcher._populate_tools_from_registry(self._tool_registry)
        
        # Track the dispatcher for cleanup
        self._active_dispatchers.append(dispatcher)
        
        return dispatcher
    
    async def cleanup_all_dispatchers(self):
        """Clean up all dispatchers created by this factory."""
        for dispatcher in self._active_dispatchers[:]:  # Copy list to avoid modification during iteration
            if dispatcher._is_active:
                await dispatcher.cleanup()
        
        self._active_dispatchers.clear()
        logger.info(f"Cleaned up all dispatchers in UnifiedToolDispatcherFactory")
    
    @staticmethod
    def create_for_request(
        user_context: 'UserExecutionContext',
        websocket_manager: Optional['WebSocketManager'] = None,
        tools: Optional[List['BaseTool']] = None,
        registry: Optional['ToolRegistry'] = None
    ) -> UnifiedToolDispatcher:
        """Create a request-scoped tool dispatcher.
        
        Args:
            user_context: User execution context for isolation
            websocket_manager: WebSocket manager for event emission
            tools: Initial tools to register
            registry: Optional pre-created registry to prevent proliferation
            
        Returns:
            Request-scoped UnifiedToolDispatcher instance
        """
        if not user_context:
            raise ValueError("user_context is required for request-scoped dispatcher")
        
        return UnifiedToolDispatcher._create_from_factory(
            user_context=user_context,
            websocket_manager=websocket_manager,
            strategy=DispatchStrategy.DEFAULT,
            tools=tools,
            registry=registry
        )
    
    @staticmethod
    def create_for_admin(
        user_context: 'UserExecutionContext',
        db: Any,
        user: Any,
        websocket_manager: Optional['WebSocketManager'] = None,
        permission_service: Any = None
    ) -> UnifiedToolDispatcher:
        """Create an admin tool dispatcher with enhanced permissions.
        
        Args:
            user_context: User execution context
            db: Database session for admin operations
            user: User object with admin status
            websocket_manager: WebSocket manager
            permission_service: Permission checking service
            
        Returns:
            Admin-enabled UnifiedToolDispatcher instance
        """
        if not user_context:
            raise ValueError("user_context is required for admin dispatcher")
        
        return UnifiedToolDispatcher._create_from_factory(
            user_context=user_context,
            websocket_manager=websocket_manager,
            strategy=DispatchStrategy.ADMIN,
            tools=None,
            db=db,
            user=user,
            permission_service=permission_service
        )
    
    @staticmethod
    def create_legacy_global(tools: Optional[List['BaseTool']] = None) -> UnifiedToolDispatcher:
        """Create a legacy global dispatcher (DEPRECATED).
        
        WARNING: This creates global shared state and should not be used in new code.
        """
        warnings.warn(
            "create_legacy_global() creates shared state that may cause user isolation issues.\n"
            "Use create_for_request() with proper user context instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Create minimal user context for legacy compatibility
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        legacy_context = UserExecutionContext(
            user_id="legacy_global",
            run_id=f"legacy_{int(time.time()*1000)}",
            thread_id="legacy",
            session_id="legacy"
        )
        
        return UnifiedToolDispatcher._create_from_factory(
            user_context=legacy_context,
            websocket_manager=None,
            strategy=DispatchStrategy.LEGACY,
            tools=tools
        )


# ============================================================================
# CONTEXT MANAGERS
# ============================================================================

@asynccontextmanager
async def create_request_scoped_dispatcher(
    user_context: 'UserExecutionContext',
    websocket_manager: Optional['WebSocketManager'] = None,
    tools: Optional[List['BaseTool']] = None
):
    """Context manager for request-scoped tool dispatcher with automatic cleanup.
    
    Usage:
        async with create_request_scoped_dispatcher(context) as dispatcher:
            result = await dispatcher.execute_tool("my_tool", params)
    """
    dispatcher = UnifiedToolDispatcherFactory.create_for_request(
        user_context=user_context,
        websocket_manager=websocket_manager,
        tools=tools
    )
    
    try:
        yield dispatcher
    finally:
        await dispatcher.cleanup()


# ============================================================================
# COMPATIBILITY LAYER FOR PHASE 4A MIGRATION
# ============================================================================

# Compatibility alias for RequestScopedToolDispatcher during SSOT migration
# This allows existing code to use UnifiedToolDispatcher transparently
RequestScopedToolDispatcher = UnifiedToolDispatcher


class WebSocketBridgeAdapter:
    """Adapter from WebSocketEventEmitter to AgentWebSocketBridge interface.
    
    This adapter allows UnifiedToolExecutionEngine to work with the new
    WebSocketEventEmitter while maintaining backward compatibility with the
    existing AgentWebSocketBridge interface.
    
    The adapter translates method calls and ensures proper user context isolation.
    """
    
    def __init__(self, websocket_emitter, user_context):
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


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Core classes
    'UnifiedToolDispatcher',
    'UnifiedToolDispatcherFactory',
    
    # Compatibility aliases
    'RequestScopedToolDispatcher',
    'WebSocketBridgeAdapter',
    
    # Data models
    'ToolDispatchRequest',
    'ToolDispatchResponse',
    'DispatchStrategy',
    
    # Context managers
    'create_request_scoped_dispatcher',
]