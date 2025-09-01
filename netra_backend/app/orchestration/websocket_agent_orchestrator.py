"""
WebSocketAgentOrchestrator - SSOT for WebSocket-Agent integration.

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
from typing import Dict, Optional, Set, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class OrchestratorConfig:
    """Configuration for WebSocket Agent Orchestrator."""
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


class WebSocketAgentOrchestrator:
    """SSOT for WebSocket-Agent integration with centralized lifecycle management."""
    
    _instance: Optional['WebSocketAgentOrchestrator'] = None
    _lock = asyncio.Lock()
    
    # Configuration constants
    RETRY_MAX_ATTEMPTS = 3
    RETRY_DELAY_MS = 100
    HEALTH_CHECK_INTERVAL_S = 30
    CONNECTION_TIMEOUT_S = 60
    EVENT_DELIVERY_TIMEOUT_MS = 500
    
    def __new__(cls) -> 'WebSocketAgentOrchestrator':
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize orchestrator with thread-safe singleton pattern."""
        if hasattr(self, '_initialized'):
            return
        
        self._initialize_configuration()
        self._initialize_state_tracking()
        self._initialize_health_monitoring()
        self._initialize_operational_state()
        
        self._initialized = True
        logger.info("WebSocketAgentOrchestrator initialized as singleton")
    
    def _initialize_configuration(self) -> None:
        """Initialize orchestrator configuration."""
        self.config = OrchestratorConfig()
    
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
        """Initialize orchestrator resources and background tasks."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_health_check())
            logger.info("Started periodic health check task")
    
    async def shutdown(self) -> None:
        """Clean shutdown of orchestrator resources."""
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
        
        logger.info("WebSocketAgentOrchestrator shutdown complete")
    
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
        logger.info("WebSocket manager configured in orchestrator")
    
    async def set_websocket_notifier(self, notifier: 'WebSocketNotifier') -> None:
        """Set WebSocket notifier reference."""
        self._websocket_notifier = notifier
        logger.info("WebSocket notifier configured in orchestrator")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator metrics."""
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


# Global singleton instance
_orchestrator_instance: Optional[WebSocketAgentOrchestrator] = None


async def get_websocket_agent_orchestrator() -> WebSocketAgentOrchestrator:
    """Get singleton WebSocket Agent Orchestrator instance."""
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        async with WebSocketAgentOrchestrator._lock:
            if _orchestrator_instance is None:
                _orchestrator_instance = WebSocketAgentOrchestrator()
                await _orchestrator_instance.initialize()
    
    return _orchestrator_instance


async def initialize_orchestrator() -> WebSocketAgentOrchestrator:
    """Initialize orchestrator singleton (convenience function)."""
    return await get_websocket_agent_orchestrator()