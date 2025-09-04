"""
AgentExecutionRegistry - SSOT for WebSocket-Agent integration.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Development Velocity
- Value Impact: Eliminates glue code repetition, provides centralized lifecycle management
- Strategic Impact: Single source of truth for agent-WebSocket coordination

Core Features:
- Singleton pattern for unified orchestration
- Context registry to prevent duplicate agent executions
- Connection state tracking with health monitoring
- Configuration management for timeouts and retries
- Idempotent operations with recovery mechanisms
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Set, Any, TYPE_CHECKING, Tuple
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class RegistryConfig:
    """Configuration for Agent Execution Registry."""
    retry_max_attempts: int = 3
    retry_delay_ms: int = 100
    health_check_interval_s: int = 30
    connection_timeout_s: int = 60
    event_delivery_timeout_ms: int = 500
    max_concurrent_contexts: int = 50
    context_cleanup_interval_s: int = 120


@dataclass
class ContextState:
    """Tracks state of an active agent execution context."""
    context_id: str
    agent_name: str
    user_id: str
    thread_id: str
    run_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    websocket_connected: bool = True
    event_count: int = 0
    error_count: int = 0


@dataclass
class ConnectionHealth:
    """Tracks WebSocket connection health metrics."""
    user_id: str
    thread_id: Optional[str]
    connected_at: datetime
    last_heartbeat: datetime
    event_delivery_success_rate: float = 1.0
    consecutive_failures: int = 0
    is_healthy: bool = True


class AgentExecutionRegistry:
    """DEPRECATED: SSOT for WebSocket-Agent integration - replaced with factory patterns.
    
    This class is now deprecated in favor of per-request factory patterns that provide
    complete user isolation and prevent cascade failures between concurrent users.
    
    For new code, use ExecutionEngineFactory and related factory patterns.
    """
    
    # REMOVED: Singleton pattern implementation - replaced with factory patterns  
    # _instance: Optional['AgentExecutionRegistry'] = None
    # _lock = asyncio.Lock()
    
    # Configuration constants
    RETRY_MAX_ATTEMPTS = 3
    RETRY_DELAY_MS = 100
    HEALTH_CHECK_INTERVAL_S = 30
    CONNECTION_TIMEOUT_S = 60
    EVENT_DELIVERY_TIMEOUT_MS = 500
    
    def __new__(cls) -> 'AgentExecutionRegistry':
        """DEPRECATED: Singleton pattern removed - use factory patterns instead.
        
        This method now creates regular instances instead of singletons to prevent
        cascade failures between users.
        """
        # Create regular instance - no singleton pattern
        return super().__new__(cls)
    
    def __init__(self):
        """Initialize registry with thread-safe singleton pattern."""
        if hasattr(self, '_initialized'):
            return
        
        self._initialize_configuration()
        self._initialize_state_tracking()
        self._initialize_health_monitoring()
        self._initialize_operational_state()
        
        self._initialized = True
        logger.info("AgentExecutionRegistry initialized as singleton")
    
    def _initialize_configuration(self) -> None:
        """Initialize registry configuration."""
        self.config = RegistryConfig()
    
    def _initialize_state_tracking(self) -> None:
        """Initialize context and connection state tracking."""
        self.active_contexts: Dict[str, ContextState] = {}
        self.context_lookup: Dict[str, str] = {}  # thread_id -> context_id
        self.connection_health: Dict[str, ConnectionHealth] = {}
        self.connection_states: Dict[str, str] = {}  # user_id -> connection_state
    
    def _initialize_health_monitoring(self) -> None:
        """Initialize health monitoring metrics."""
        self.health_metrics = {
            "total_contexts_created": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "duplicate_prevention_count": 0,
            "health_checks_performed": 0,
            "recovery_operations": 0
        }
    
    def _initialize_operational_state(self) -> None:
        """Initialize operational state variables."""
        self._websocket_manager: Optional['WebSocketManager'] = None
        self._websocket_notifier: Optional['WebSocketNotifier'] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
        self._context_locks: Dict[str, asyncio.Lock] = {}
    
    async def initialize(self) -> None:
        """Initialize registry resources and background tasks."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_health_check())
            logger.info("Started periodic health check task")
    
    async def shutdown(self) -> None:
        """Clean shutdown of registry resources."""
        self._shutdown = True
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clean up active contexts
        await self._cleanup_all_contexts()
        
        # Clear state
        self.active_contexts.clear()
        self.context_lookup.clear()
        self.connection_health.clear()
        self.connection_states.clear()
        self._context_locks.clear()
        
        logger.info("AgentExecutionRegistry shutdown complete")
    
    async def register_context(self, context: 'AgentExecutionContext') -> str:
        """Register new agent execution context with duplicate prevention."""
        context_id = f"ctx_{context.thread_id}_{uuid.uuid4().hex[:8]}"
        
        async with self._lock:
            # Check for existing context in same thread
            if context.thread_id in self.context_lookup:
                existing_id = self.context_lookup[context.thread_id]
                if existing_id in self.active_contexts:
                    self.health_metrics["duplicate_prevention_count"] += 1
                    logger.warning(f"Preventing duplicate context for thread {context.thread_id}")
                    return existing_id
            
            # Create new context state
            context_state = ContextState(
                context_id=context_id,
                agent_name=context.agent_name,
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=context.run_id
            )
            
            # Register context
            self.active_contexts[context_id] = context_state
            self.context_lookup[context.thread_id] = context_id
            self.health_metrics["total_contexts_created"] += 1
            
            logger.info(f"Registered context {context_id} for agent {context.agent_name}")
            return context_id
    
    async def unregister_context(self, context_id: str, success: bool = True) -> None:
        """Unregister agent execution context and update metrics."""
        async with self._lock:
            if context_id not in self.active_contexts:
                return
            
            context_state = self.active_contexts[context_id]
            
            # Update metrics
            if success:
                self.health_metrics["successful_executions"] += 1
            else:
                self.health_metrics["failed_executions"] += 1
            
            # Clean up context
            context_state.is_active = False
            self.context_lookup.pop(context_state.thread_id, None)
            del self.active_contexts[context_id]
            
            logger.info(f"Unregistered context {context_id}, success: {success}")
    
    async def get_context_state(self, context_id: str) -> Optional[ContextState]:
        """Get current state of a registered context."""
        return self.active_contexts.get(context_id)
    
    async def is_context_active(self, thread_id: str) -> bool:
        """Check if a context is active for the given thread."""
        context_id = self.context_lookup.get(thread_id)
        if not context_id:
            return False
        return context_id in self.active_contexts
    
    async def update_context_activity(self, context_id: str) -> None:
        """Update last activity timestamp for context."""
        if context_id in self.active_contexts:
            self.active_contexts[context_id].last_activity = datetime.now(timezone.utc)
            self.active_contexts[context_id].event_count += 1
    
    async def track_connection_health(self, user_id: str, thread_id: Optional[str] = None,
                                    event_success: bool = True) -> None:
        """Track WebSocket connection health for a user."""
        health_key = f"{user_id}_{thread_id or 'default'}"
        
        if health_key not in self.connection_health:
            self.connection_health[health_key] = ConnectionHealth(
                user_id=user_id,
                thread_id=thread_id,
                connected_at=datetime.now(timezone.utc),
                last_heartbeat=datetime.now(timezone.utc)
            )
        
        health = self.connection_health[health_key]
        health.last_heartbeat = datetime.now(timezone.utc)
        
        # Update success rate and failure tracking
        if event_success:
            health.consecutive_failures = 0
            # Improve success rate gradually
            health.event_delivery_success_rate = min(1.0, 
                health.event_delivery_success_rate * 0.95 + 0.05)
        else:
            health.consecutive_failures += 1
            # Reduce success rate
            health.event_delivery_success_rate *= 0.9
        
        # Update health status
        health.is_healthy = (health.consecutive_failures < 3 and 
                           health.event_delivery_success_rate > 0.5)
    
    async def get_health_status(self, user_id: str, thread_id: Optional[str] = None) -> bool:
        """Get health status for a user's WebSocket connection."""
        health_key = f"{user_id}_{thread_id or 'default'}"
        health = self.connection_health.get(health_key)
        return health.is_healthy if health else False
    
    async def set_websocket_manager(self, manager: 'WebSocketManager') -> None:
        """Set WebSocket manager reference."""
        self._websocket_manager = manager
        logger.info("WebSocket manager configured in registry")
    
    async def set_websocket_notifier(self, notifier: 'WebSocketNotifier') -> None:
        """Set WebSocket notifier reference."""
        self._websocket_notifier = notifier
        logger.info("WebSocket notifier configured in registry")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive registry metrics."""
        return {
            "active_contexts": len(self.active_contexts),
            "registered_connections": len(self.connection_health),
            "health_metrics": self.health_metrics.copy(),
            "config": {
                "retry_max_attempts": self.config.retry_max_attempts,
                "retry_delay_ms": self.config.retry_delay_ms,
                "health_check_interval_s": self.config.health_check_interval_s,
                "connection_timeout_s": self.config.connection_timeout_s,
                "event_delivery_timeout_ms": self.config.event_delivery_timeout_ms
            }
        }
    
    async def _periodic_health_check(self) -> None:
        """Periodic health check and cleanup task."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.config.health_check_interval_s)
                
                if self._shutdown:
                    break
                
                await self._cleanup_stale_contexts()
                await self._cleanup_stale_connections()
                self.health_metrics["health_checks_performed"] += 1
                
            except Exception as e:
                logger.error(f"Error in periodic health check: {e}")
    
    async def _cleanup_stale_contexts(self) -> None:
        """Clean up stale or inactive contexts."""
        current_time = datetime.now(timezone.utc)
        stale_contexts = []
        
        for context_id, context_state in self.active_contexts.items():
            # Check if context is stale (no activity for 10 minutes)
            time_since_activity = (current_time - context_state.last_activity).total_seconds()
            if time_since_activity > 600:  # 10 minutes
                stale_contexts.append(context_id)
        
        # Remove stale contexts
        for context_id in stale_contexts:
            await self.unregister_context(context_id, success=False)
            logger.info(f"Cleaned up stale context {context_id}")
    
    async def _cleanup_stale_connections(self) -> None:
        """Clean up stale connection health records."""
        current_time = datetime.now(timezone.utc)
        stale_connections = []
        
        for health_key, health in self.connection_health.items():
            # Remove connections with no heartbeat for 5 minutes
            time_since_heartbeat = (current_time - health.last_heartbeat).total_seconds()
            if time_since_heartbeat > 300:  # 5 minutes
                stale_connections.append(health_key)
        
        # Remove stale connection health records
        for health_key in stale_connections:
            del self.connection_health[health_key]
            logger.debug(f"Cleaned up stale connection health for {health_key}")
    
    async def _cleanup_all_contexts(self) -> None:
        """Clean up all active contexts during shutdown."""
        for context_id in list(self.active_contexts.keys()):
            await self.unregister_context(context_id, success=False)
    
    async def create_execution_context(
        self,
        agent_type: str,
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple['AgentExecutionContext', 'WebSocketNotifier']:
        """Create execution context with deduplication.
        
        Factory method for creating and registering contexts with deduplication.
        Ensures proper WebSocket notification setup.
        """
        thread_id = context.get('thread_id') if context else f"thread_{uuid.uuid4().hex[:8]}"
        
        # Check for existing context to prevent duplicates
        if await self.is_context_active(thread_id):
            return await self._reuse_existing_context(thread_id, user_id, context)
        
        # Create new context
        return await self._create_new_context(agent_type, user_id, thread_id, context)
    
    async def _reuse_existing_context(
        self, 
        thread_id: str, 
        user_id: str, 
        context: Optional[Dict[str, Any]]
    ) -> Tuple['AgentExecutionContext', 'WebSocketNotifier']:
        """Reuse existing context for thread."""
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
        
        logger.warning(f"Context already active for thread {thread_id}, reusing")
        existing_context_id = self.context_lookup[thread_id]
        existing_state = self.active_contexts[existing_context_id]
        
        # Create context object from existing state
        existing_context = AgentExecutionContext(
            run_id=existing_state.run_id,
            thread_id=thread_id,
            user_id=user_id,
            agent_name=existing_state.agent_name,
            metadata=context or {}
        )
        
        # Create WebSocket notifier
        if not self._websocket_manager:
            raise RuntimeError("WebSocket manager not initialized")
        notifier = WebSocketNotifier(self._websocket_manager)
        
        return existing_context, notifier
    
    async def _create_new_context(
        self,
        agent_type: str,
        user_id: str,
        thread_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Tuple['AgentExecutionContext', 'WebSocketNotifier']:
        """Create new execution context and register it."""
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
        
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Create new execution context
        exec_context = AgentExecutionContext(
            run_id=run_id,
            thread_id=thread_id,
            user_id=user_id,
            agent_name=agent_type,
            metadata=context or {}
        )
        
        # Register in orchestrator
        context_id = await self.register_context(exec_context)
        
        # Create WebSocket notifier and send started event
        notifier = await self._create_notifier_and_send_started(exec_context, context_id)
        
        return exec_context, notifier
    
    async def _create_notifier_and_send_started(
        self, 
        exec_context: 'AgentExecutionContext', 
        context_id: str
    ) -> 'WebSocketNotifier':
        """Create notifier and send agent_started event."""
        from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
        
        if not self._websocket_manager:
            raise RuntimeError("WebSocket manager not initialized")
        notifier = WebSocketNotifier(self._websocket_manager)
        
        # Send agent_started event
        try:
            await notifier.send_agent_started(exec_context)
            logger.info(f"Context created and agent_started sent for {context_id}")
        except Exception as e:
            logger.error(f"Failed to send agent_started for {context_id}: {e}")
        
        return notifier
    
    async def ensure_event_delivery(
        self,
        context: 'AgentExecutionContext',
        event_type: str,
        payload: Dict[str, Any]
    ) -> bool:
        """Ensure critical event delivery with retry logic.
        
        Guarantees delivery of critical events with retry and backpressure handling.
        """
        from netra_backend.app.schemas.websocket_models import WebSocketMessage
        
        if not self._websocket_manager:
            logger.error("WebSocket manager not available for event delivery")
            return False
        
        message = WebSocketMessage(type=event_type, payload=payload)
        max_attempts = self.config.retry_max_attempts
        
        # Track delivery attempts
        for attempt in range(max_attempts):
            try:
                # Update context activity
                await self.update_context_activity(context.run_id)
                
                # Attempt delivery
                success = await self._websocket_manager.send_to_thread(
                    context.thread_id, 
                    message.model_dump()
                )
                
                if success:
                    # Track successful delivery
                    await self.track_connection_health(
                        context.user_id, 
                        context.thread_id, 
                        event_success=True
                    )
                    logger.debug(f"Event {event_type} delivered successfully on attempt {attempt + 1}")
                    return True
                
                # Failed delivery - wait before retry
                if attempt < max_attempts - 1:
                    delay = (self.config.retry_delay_ms / 1000) * (2 ** attempt)
                    await asyncio.sleep(delay)
                    logger.debug(f"Event delivery failed, retrying in {delay}s")
                
            except Exception as e:
                logger.error(f"Event delivery attempt {attempt + 1} failed: {e}")
                
                # Track failure
                await self.track_connection_health(
                    context.user_id, 
                    context.thread_id, 
                    event_success=False
                )
                
                if attempt < max_attempts - 1:
                    delay = (self.config.retry_delay_ms / 1000) * (2 ** attempt)
                    await asyncio.sleep(delay)
        
        logger.error(f"Failed to deliver {event_type} after {max_attempts} attempts")
        return False
    
    async def setup_agent_websocket_integration(
        self,
        supervisor: Any,
        registry: Any
    ) -> None:
        """Setup WebSocket integration at startup.
        
        Configures WebSocket manager on registry and enhances tool dispatcher.
        """
        if not self._websocket_manager:
            logger.error("WebSocket manager not initialized in registry")
            return
        
        try:
            # Set WebSocket manager on registry
            if hasattr(registry, 'set_websocket_manager'):
                registry.set_websocket_manager(self._websocket_manager)
                logger.info("WebSocket manager set on agent registry")
            
            # Enhance tool dispatcher if available
            if hasattr(registry, 'tool_dispatcher') and registry.tool_dispatcher:
                from netra_backend.app.agents.unified_tool_execution import (
                    enhance_tool_dispatcher_with_notifications
                )
                enhance_tool_dispatcher_with_notifications(
                    registry.tool_dispatcher, 
                    self._websocket_manager
                )
                logger.info("Tool dispatcher enhanced with WebSocket notifications")
            
            # Configure all registered agents
            if hasattr(registry, 'agents'):
                for agent_name, agent in registry.agents.items():
                    if hasattr(agent, 'websocket_manager'):
                        agent.websocket_manager = self._websocket_manager
                        logger.debug(f"WebSocket manager configured for agent {agent_name}")
            
            # Verify integration
            integration_status = await self._verify_websocket_integration(registry)
            if integration_status:
                logger.info("WebSocket integration setup completed successfully")
            else:
                logger.warning("WebSocket integration setup had issues")
                
        except Exception as e:
            logger.error(f"Failed to setup WebSocket integration: {e}")
            raise
    
    async def complete_execution(
        self,
        context: 'AgentExecutionContext',
        result: Any
    ) -> None:
        """Complete agent execution with proper cleanup.
        
        Sends completion events, updates metrics, and cleans up resources.
        """
        try:
            # Send agent_completed event
            if self._websocket_notifier:
                # Calculate duration
                context_state = await self.get_context_state(context.run_id)
                duration_ms = 0.0
                if context_state:
                    duration = (datetime.now(timezone.utc) - context_state.created_at).total_seconds()
                    duration_ms = duration * 1000
                
                # Send completion notification
                await self._websocket_notifier.send_agent_completed(
                    context, 
                    result=result if isinstance(result, dict) else {"result": str(result)},
                    duration_ms=duration_ms
                )
                logger.info(f"Agent completion event sent for {context.run_id}")
            
            # Unregister context
            await self.unregister_context(context.run_id, success=True)
            
            # Update metrics
            self.health_metrics["successful_executions"] += 1
            
            # Clean up context-specific locks
            if context.run_id in self._context_locks:
                del self._context_locks[context.run_id]
            
            logger.info(f"Execution completed successfully for context {context.run_id}")
            
        except Exception as e:
            logger.error(f"Failed to complete execution for {context.run_id}: {e}")
            # Still try to unregister context
            await self.unregister_context(context.run_id, success=False)
            self.health_metrics["failed_executions"] += 1
            raise
    
    async def _verify_websocket_integration(self, registry: Any) -> bool:
        """Verify WebSocket integration is properly configured."""
        try:
            # In UserContext pattern, websocket_manager is set per-request, not globally
            # So we just log info instead of failing
            if not hasattr(registry, 'websocket_manager') or not registry.websocket_manager:
                logger.info("Registry websocket_manager will be set per-request (UserContext pattern)")
                # Don't fail - this is expected in UserContext architecture
                return True
            
            # Check tool dispatcher enhancement (if dispatcher exists)
            if hasattr(registry, 'tool_dispatcher') and registry.tool_dispatcher:
                # Only check if tool_dispatcher actually exists (not None)
                if not hasattr(registry.tool_dispatcher, '_websocket_manager'):
                    logger.info("Tool dispatcher WebSocket enhancement will be set per-request")
                    # Don't fail - this is expected in UserContext architecture
            
            # Check sample agents have WebSocket manager
            if hasattr(registry, 'agents'):
                agent_count = 0
                configured_count = 0
                for agent_name, agent in registry.agents.items():
                    agent_count += 1
                    if hasattr(agent, 'websocket_manager') and agent.websocket_manager:
                        configured_count += 1
                
                if agent_count > 0 and configured_count == 0:
                    logger.warning("No agents have WebSocket manager configured")
                    return False
                
                logger.info(f"WebSocket integration verified: {configured_count}/{agent_count} agents configured")
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket integration verification failed: {e}")
            return False


# REMOVED: Global singleton instance - replaced with factory patterns
# _registry_instance: Optional[AgentExecutionRegistry] = None


async def get_agent_execution_registry() -> AgentExecutionRegistry:
    """DEPRECATED: Singleton registry function removed - use factory patterns.
    
    This function is deprecated because singleton execution registries prevent
    user isolation and cause cascade failures between concurrent users.
    
    For new code, use:
    - ExecutionEngineFactory.create_execution_engine() for per-user isolation
    - UserWebSocketEmitter for per-request event emission
    - AgentInstanceFactory.create_agent_instance() for agent creation
    
    Business Impact: Factory patterns enable safe concurrent user operations
    and prevent cascade failures that affect all users.
    
    Raises:
        RuntimeError: Always - function is deprecated
    """
    import warnings
    warnings.warn(
        "get_agent_execution_registry() is completely deprecated. "
        "Use ExecutionEngineFactory and factory patterns for user isolation. "
        "Singleton patterns cause cascade failures between users.",
        DeprecationWarning,
        stacklevel=2
    )
    
    logger.error("🚨 DEPRECATED: get_agent_execution_registry() no longer supported")
    logger.error("   Use: ExecutionEngineFactory.create_execution_engine() for per-user isolation")
    logger.error("   Or: UserWebSocketEmitter for per-request event emission")
    raise RuntimeError(
        "get_agent_execution_registry() is deprecated. Use ExecutionEngineFactory and "
        "factory patterns to prevent cascade failures between users."
    )


async def initialize_registry() -> AgentExecutionRegistry:
    """DEPRECATED: Registry initialization removed - use factory patterns.
    
    This function is deprecated because singleton registries prevent user isolation.
    
    Raises:
        RuntimeError: Always - function is deprecated
    """
    logger.error("🚨 DEPRECATED: initialize_registry() no longer supported")
    raise RuntimeError(
        "initialize_registry() is deprecated. Use factory patterns for user isolation."
    )


def extract_thread_id_from_run_id(run_id: str) -> Optional[str]:
    """Extract thread_id from a run_id with format 'run_{thread_id}_{uuid}' or None if invalid.
    
    Args:
        run_id: Run ID in format 'run_{thread_id}_{uuid}' or legacy format
        
    Returns:
        thread_id if extractable, None for legacy format or invalid format
    """
    if not run_id or not run_id.startswith('run_') or len(run_id) <= 4:
        return None
    
    # Remove 'run_' prefix
    run_suffix = run_id[4:]
    
    # Empty suffix is invalid
    if not run_suffix:
        return None
    
    # Split by '_' - should have at least 2 parts for new format
    parts = run_suffix.split('_')
    
    # Legacy format: run_{uuid} (single part after splitting, no underscores)
    if len(parts) == 1:
        logger.debug(f"Legacy run_id format detected: {run_id}")
        return None
    
    # New format: run_{thread_id}_{uuid} (multiple underscores)
    # Join all parts except the last one as thread_id
    # This handles thread_ids that may contain underscores
    if len(parts) >= 2:
        thread_id = '_'.join(parts[:-1])
        # Thread ID should not be empty
        if not thread_id:
            return None
        logger.debug(f"Extracted thread_id '{thread_id}' from run_id '{run_id}'")
        return thread_id
    
    return None


def validate_run_id_format(run_id: str, expected_thread_id: Optional[str] = None) -> bool:
    """Validate run_id format and optionally check thread_id match.
    
    Args:
        run_id: Run ID to validate
        expected_thread_id: Expected thread ID (if provided, validates match)
        
    Returns:
        True if valid format and thread_id matches (if provided)
    """
    if not run_id or not run_id.startswith('run_') or len(run_id) <= 4:
        return False
    
    # Remove 'run_' prefix and check if there's actual content
    run_suffix = run_id[4:]
    if not run_suffix:
        return False
    
    extracted_thread_id = extract_thread_id_from_run_id(run_id)
    
    # If no expected thread_id, just check if it's new format or legacy
    if expected_thread_id is None:
        return True  # Both legacy and new formats are valid
    
    # Check if extracted thread_id matches expected
    return extracted_thread_id == expected_thread_id