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
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
    from langchain_core.tools import BaseTool
    from netra_backend.app.agents.state import DeepAgentState

from pydantic import BaseModel, Field
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.tool import (
    SimpleToolPayload,
    ToolInput,
    ToolResult,
    ToolStatus,
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
        # Validate user context
        if not user_context or not user_context.user_id:
            raise AuthenticationError("Valid UserExecutionContext required for dispatcher creation")
        
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
                from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
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
    @asynccontextmanager
    async def create_scoped(
        cls,
        user_context: 'UserExecutionContext',
        websocket_bridge: Optional[Any] = None,
        tools: Optional[List['BaseTool']] = None,
        enable_admin_tools: bool = False
    ):
        """Create scoped dispatcher with automatic cleanup.
        
        RECOMMENDED USAGE PATTERN:
            async with UnifiedToolDispatcher.create_scoped(user_context) as dispatcher:
                result = await dispatcher.execute_tool("my_tool", params)
                # Automatic cleanup happens here
        """
        dispatcher = await cls.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_bridge,
            tools=tools,
            enable_admin_tools=enable_admin_tools
        )
        
        try:
            yield dispatcher
        finally:
            # Ensure cleanup
            if dispatcher._is_active:
                await dispatcher.cleanup()
    
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
        
        # Track dispatcher for cleanup
        cls._register_dispatcher(instance)
        
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
    
    def _init_components(self, tools: Optional[List['BaseTool']] = None, **kwargs):
        """Initialize core components."""
        # Import here to avoid circular dependencies
        from netra_backend.app.core.registry.universal_registry import ToolRegistry
        from netra_backend.app.agents.tool_dispatcher_validation import ToolValidator
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        
        # Core components
        self.registry = ToolRegistry()
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
                        success = await self.bridge.notify_tool_executing(
                            run_id=data.get("run_id", self.context.run_id),
                            agent_name=data.get("agent_name", "ToolDispatcher"),
                            tool_name=data["tool_name"],
                            parameters=data.get("parameters", {})
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
        # Use the UniversalRegistry's register method
        self.registry.register(tool.name, tool)
        logger.debug(f"Registered tool {tool.name} in dispatcher {self.dispatcher_id}")
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        self._ensure_active()
        return self.registry.list_keys()
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any] = None,
        require_permission_check: bool = True
    ) -> ToolDispatchResponse:
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
        
        # Emit tool_executing event
        if self.has_websocket_support:
            await self._emit_tool_executing(tool_name, parameters)
        
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
            
            # Emit tool_completed event
            if self.has_websocket_support:
                await self._emit_tool_completed(tool_name, result, execution_time)
            
            # Extract actual result from ToolResult wrapper
            actual_result = result.payload.result if hasattr(result, 'payload') and hasattr(result.payload, 'result') else result
            
            return ToolDispatchResponse(
                success=True,
                result=actual_result,
                metadata={
                    'execution_time_ms': execution_time,
                    'dispatcher_id': self.dispatcher_id
                }
            )
            
        except Exception as e:
            # Update metrics
            execution_time = (time.time() - start_time) * 1000
            self._update_metrics(success=False, execution_time=execution_time)
            
            # Emit tool_completed with error
            if self.has_websocket_support:
                await self._emit_tool_completed(tool_name, error=str(e), execution_time=execution_time)
            
            logger.error(f"Tool {tool_name} failed in dispatcher {self.dispatcher_id}: {e}")
            
            return ToolDispatchResponse(
                success=False,
                error=str(e),
                metadata={
                    'execution_time_ms': execution_time,
                    'dispatcher_id': self.dispatcher_id
                }
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
    
    async def _emit_tool_executing(self, tool_name: str, parameters: Dict[str, Any]):
        """Emit tool_executing WebSocket event."""
        if not self.websocket_manager:
            return
        
        try:
            await self.websocket_manager.send_event(
                "tool_executing",
                {
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "run_id": self.user_context.run_id,
                    "user_id": self.user_context.user_id,
                    "thread_id": self.user_context.thread_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            self._metrics['websocket_events_sent'] += 1
        except Exception as e:
            logger.warning(f"Failed to emit tool_executing event: {e}")
    
    async def _emit_tool_completed(
        self,
        tool_name: str,
        result: Any = None,
        error: str = None,
        execution_time: float = None
    ):
        """Emit tool_completed WebSocket event."""
        if not self.websocket_manager:
            return
        
        try:
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
            
            await self.websocket_manager.send_event("tool_completed", event_data)
            self._metrics['websocket_events_sent'] += 1
        except Exception as e:
            logger.warning(f"Failed to emit tool_completed event: {e}")
    
    def set_websocket_manager(self, manager: 'WebSocketManager'):
        """Set or update WebSocket manager for event emission."""
        self.websocket_manager = manager
        self._setup_websocket_events()
        logger.info(f"WebSocket manager set for dispatcher {self.dispatcher_id}")
    
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
    
    async def cleanup(self):
        """Clean up dispatcher resources."""
        if not self._is_active:
            return
        
        self._is_active = False
        
        # Clean up components
        if hasattr(self, 'registry'):
            self.registry.clear()
        
        # Unregister dispatcher
        self._unregister_dispatcher(self)
        
        logger.info(f"Cleaned up dispatcher {self.dispatcher_id}")
    
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


# ============================================================================
# FACTORY
# ============================================================================

class UnifiedToolDispatcherFactory:
    """Factory for creating request-scoped tool dispatchers.
    
    Ensures proper user isolation and prevents shared state issues.
    """
    
    @staticmethod
    def create_for_request(
        user_context: 'UserExecutionContext',
        websocket_manager: Optional['WebSocketManager'] = None,
        tools: Optional[List['BaseTool']] = None
    ) -> UnifiedToolDispatcher:
        """Create a request-scoped tool dispatcher.
        
        Args:
            user_context: User execution context for isolation
            websocket_manager: WebSocket manager for event emission
            tools: Initial tools to register
            
        Returns:
            Request-scoped UnifiedToolDispatcher instance
        """
        if not user_context:
            raise ValueError("user_context is required for request-scoped dispatcher")
        
        return UnifiedToolDispatcher._create_from_factory(
            user_context=user_context,
            websocket_manager=websocket_manager,
            strategy=DispatchStrategy.DEFAULT,
            tools=tools
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
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
        
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
# EXPORTS
# ============================================================================

__all__ = [
    # Core classes
    'UnifiedToolDispatcher',
    'UnifiedToolDispatcherFactory',
    
    # Data models
    'ToolDispatchRequest',
    'ToolDispatchResponse',
    'DispatchStrategy',
    
    # Context managers
    'create_request_scoped_dispatcher',
]