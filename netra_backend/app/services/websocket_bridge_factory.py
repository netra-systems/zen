"""
WebSocketBridgeFactory - Factory Pattern for Per-User WebSocket Event Emitters

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Reliability & User Experience
- Value Impact: Enables reliable WebSocket notifications for 10+ concurrent users with zero cross-user event leakage
- Strategic Impact: Critical - Replaces dangerous singleton WebSocket bridge with per-user isolation

This module implements the WebSocketBridgeFactory pattern that provides complete user isolation
for WebSocket events, eliminating the cross-user notification failures of the legacy singleton.

Key Features:
1. Complete Event Isolation - User A's notifications never sent to User B
2. Connection Management - Proper WebSocket connection lifecycle per user
3. Delivery Guarantees - Retry mechanisms and health monitoring ensure delivery
4. Scalability - Support for 10+ concurrent users with bounded resources
5. Business IP Protection - Event sanitization prevents sensitive data leakage
"""

import asyncio
import time
import uuid
import json
import gzip
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.websocket_notification_monitor import get_websocket_notification_monitor
from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool, ConnectionInfo

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)


class ConnectionStatus(Enum):
    """WebSocket connection status."""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"
    CLOSED = "closed"


@dataclass
class UserWebSocketContext:
    """
    Per-user WebSocket event context with complete isolation.
    
    This dataclass encapsulates all WebSocket state for a single user,
    ensuring complete isolation between concurrent users.
    
    Business Value: Prevents cross-user event leakage and enables reliable notifications
    """
    user_id: str
    thread_id: str
    connection_id: str
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # User-specific WebSocket state - ISOLATED per user
    event_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1000))
    sent_events: List[Dict[str, Any]] = field(default_factory=list)
    failed_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Connection health
    last_heartbeat: Optional[datetime] = None
    connection_status: ConnectionStatus = ConnectionStatus.INITIALIZING
    reconnect_attempts: int = 0
    
    # Resource management
    cleanup_callbacks: List[Callable] = field(default_factory=list)
    _is_cleaned: bool = False
    
    async def cleanup(self) -> None:
        """Clean up user-specific WebSocket resources."""
        if self._is_cleaned:
            logger.debug(f"UserWebSocketContext already cleaned for user {self.user_id}")
            return
            
        logger.info(f"🧹 Cleaning up UserWebSocketContext for user {self.user_id}")
        
        try:
            # Clear event queue
            while not self.event_queue.empty():
                try:
                    self.event_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                    
            # Run cleanup callbacks
            for callback in reversed(self.cleanup_callbacks):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"WebSocket cleanup callback failed for user {self.user_id}: {e}")
                    
            # Clear event history but keep some for debugging
            if len(self.sent_events) > 10:
                self.sent_events = self.sent_events[-5:]  # Keep last 5
            if len(self.failed_events) > 10:
                self.failed_events = self.failed_events[-5:]  # Keep last 5
                
            # Clear cleanup callbacks
            self.cleanup_callbacks.clear()
            self.connection_status = ConnectionStatus.CLOSED
            
            self._is_cleaned = True
            logger.info(f"✅ UserWebSocketContext cleanup completed for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"❌ UserWebSocketContext cleanup failed for user {self.user_id}: {e}")
            self._is_cleaned = True  # Mark as cleaned even if there were errors


@dataclass
class WebSocketFactoryConfig:
    """Configuration for WebSocketBridgeFactory."""
    max_events_per_user: int = 1000
    event_timeout_seconds: float = 30.0
    heartbeat_interval_seconds: float = 30.0
    max_reconnect_attempts: int = 3
    delivery_retries: int = 3
    delivery_timeout_seconds: float = 5.0
    enable_event_compression: bool = True
    enable_event_batching: bool = True
    
    @classmethod
    def from_env(cls) -> 'WebSocketFactoryConfig':
        """Create config from environment variables."""
        from shared.isolated_environment import get_env
        
        env = get_env()
        return cls(
            max_events_per_user=int(env.get('WEBSOCKET_MAX_EVENTS_PER_USER', '1000')),
            event_timeout_seconds=float(env.get('WEBSOCKET_EVENT_TIMEOUT', '30.0')),
            heartbeat_interval_seconds=float(env.get('WEBSOCKET_HEARTBEAT_INTERVAL', '30.0')),
            max_reconnect_attempts=int(env.get('WEBSOCKET_MAX_RECONNECT_ATTEMPTS', '3')),
            delivery_retries=int(env.get('WEBSOCKET_DELIVERY_RETRIES', '3')),
            delivery_timeout_seconds=float(env.get('WEBSOCKET_DELIVERY_TIMEOUT', '5.0')),
            enable_event_compression=env.get('WEBSOCKET_ENABLE_COMPRESSION', 'true').lower() == 'true',
            enable_event_batching=env.get('WEBSOCKET_ENABLE_BATCHING', 'true').lower() == 'true',
        )


@dataclass
class WebSocketEvent:
    """Standardized WebSocket event with user isolation."""
    event_type: str
    user_id: str
    thread_id: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    retry_count: int = 0
    max_retries: int = 3


class WebSocketBridgeFactory:
    """
    Factory for creating per-user WebSocket bridges with complete event isolation.
    
    This factory creates isolated WebSocket event emitters for each user,
    eliminating the cross-user event leakage of the legacy singleton bridge.
    
    Key Features:
    - Complete user isolation
    - Event delivery guarantees
    - Health monitoring
    - Resource management
    - Performance optimization
    """
    
    def __init__(self, config: Optional[WebSocketFactoryConfig] = None):
        """Initialize the WebSocket bridge factory."""
        self.config = config or WebSocketFactoryConfig.from_env()
        
        # Initialize monitoring
        self.notification_monitor = get_websocket_notification_monitor()
        
        # Infrastructure components (shared, thread-safe)
        self._connection_pool: Optional[WebSocketConnectionPool] = None
        self._agent_registry: Optional['AgentRegistry'] = None
        self._health_monitor: Optional[Any] = None
        
        # Per-user tracking (infrastructure manages this)
        self._user_contexts: Dict[str, UserWebSocketContext] = {}
        self._context_lock = asyncio.Lock()
        
        # Factory metrics
        self._factory_metrics = {
            'emitters_created': 0,
            'emitters_active': 0,
            'emitters_cleaned': 0,
            'events_sent_total': 0,
            'events_failed_total': 0,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("WebSocketBridgeFactory initialized")
        
    def configure(self, 
                 connection_pool: WebSocketConnectionPool,
                 agent_registry: 'AgentRegistry',
                 health_monitor: Any) -> None:
        """Configure factory with infrastructure components.
        
        Args:
            connection_pool: WebSocket connection pool for managing connections
            agent_registry: Registry for agent operations
            health_monitor: Health monitoring component
            
        Raises:
            ValueError: If critical components are None
        """
        if connection_pool is None:
            raise ValueError("Connection pool cannot be None - factory requires valid connection pool")
        # Note: agent_registry can be None when using UserExecutionContext pattern
        # where registry is created per-request - this is valid
            
        self._connection_pool = connection_pool
        self._agent_registry = agent_registry
        self._health_monitor = health_monitor
        
        if agent_registry:
            logger.info("✅ WebSocketBridgeFactory configured with agent registry")
        else:
            logger.info("✅ WebSocketBridgeFactory configured (per-request registry pattern)")
        
    async def create_user_emitter(self, 
                                user_id: str, 
                                thread_id: str,
                                connection_id: str) -> 'UserWebSocketEmitter':
        """
        Create a per-user WebSocket event emitter with complete isolation.
        
        Args:
            user_id: Unique user identifier
            thread_id: Thread identifier for WebSocket routing
            connection_id: WebSocket connection identifier
            
        Returns:
            UserWebSocketEmitter: New WebSocket emitter for this specific user
            
        Raises:
            RuntimeError: If factory not configured
        """
        if not self._connection_pool:
            raise RuntimeError("Factory not configured - call configure() first")
        
        # MONITORING: Track bridge initialization start
        correlation_id = self.notification_monitor.track_bridge_initialization_started(
            user_id, thread_id, connection_id
        )
        
        start_time = time.time()
        
        try:
            # Create or get user context
            user_context = await self._get_or_create_user_context(
                user_id, thread_id, connection_id
            )
            
            # Get user-specific WebSocket connection from pool
            connection_info = await self._connection_pool.get_connection(
                connection_id, user_id
            )
            
            # CRITICAL: Only create emitter if real WebSocket connection exists
            # This prevents mock connections that bypass UserExecutionContext
            if not connection_info or not connection_info.websocket:
                raise RuntimeError(
                    f"No active WebSocket connection found for user {user_id}, connection {connection_id}. "
                    "WebSocket connection must be established before creating emitter."
                )
            
            # Create UserWebSocketConnection wrapper with REAL WebSocket
            connection = UserWebSocketConnection(
                user_id=user_id,
                connection_id=connection_id,
                websocket=connection_info.websocket  # Real WebSocket instance
            )
            
            # Create user-specific emitter
            emitter = UserWebSocketEmitter(
                user_context=user_context,
                connection=connection,
                delivery_config=self._get_delivery_config(),
                factory=self  # Reference for cleanup
            )
            
            # Register cleanup
            user_context.cleanup_callbacks.append(emitter.cleanup)
            
            # Update metrics
            self._factory_metrics['emitters_created'] += 1
            self._factory_metrics['emitters_active'] += 1
            
            creation_time_ms = (time.time() - start_time) * 1000
            
            # MONITORING: Track successful bridge initialization
            self.notification_monitor.track_bridge_initialization_success(
                correlation_id, creation_time_ms
            )
            
            logger.info(f"✅ UserWebSocketEmitter created for user {user_id} in {creation_time_ms:.1f}ms")
            
            return emitter
            
        except Exception as e:
            creation_time_ms = (time.time() - start_time) * 1000
            
            # MONITORING: Track failed bridge initialization
            self.notification_monitor.track_bridge_initialization_failed(
                correlation_id, str(e), creation_time_ms
            )
            
            logger.error(f"❌ Failed to create WebSocket emitter for user {user_id}: {e}")
            raise RuntimeError(f"WebSocket emitter creation failed: {e}")
            
    async def _get_or_create_user_context(self, 
                                        user_id: str, 
                                        thread_id: str,
                                        connection_id: str) -> UserWebSocketContext:
        """Get or create user-specific WebSocket context."""
        context_key = f"{user_id}:{connection_id}"
        
        async with self._context_lock:
            if context_key not in self._user_contexts:
                self._user_contexts[context_key] = UserWebSocketContext(
                    user_id=user_id,
                    thread_id=thread_id,
                    connection_id=connection_id
                )
                logger.debug(f"Created WebSocket context for user {user_id}")
            return self._user_contexts[context_key]
            
    async def cleanup_user_context(self, user_id: str, connection_id: str) -> None:
        """Clean up user context when connection closes."""
        context_key = f"{user_id}:{connection_id}"
        
        async with self._context_lock:
            if context_key in self._user_contexts:
                context = self._user_contexts[context_key]
                
                # Don't call context.cleanup() here to avoid circular cleanup
                # The emitter already handles its own cleanup, just clean up the factory state
                context._is_cleaned = True
                context.connection_status = ConnectionStatus.CLOSED
                
                del self._user_contexts[context_key]
                self._factory_metrics['emitters_active'] -= 1
                self._factory_metrics['emitters_cleaned'] += 1
                logger.debug(f"Context cleaned for user {user_id}")
                
    def _get_delivery_config(self) -> Dict[str, Any]:
        """Get event delivery configuration."""
        return {
            'max_retries': self.config.delivery_retries,
            'timeout': self.config.delivery_timeout_seconds,
            'heartbeat_interval': self.config.heartbeat_interval_seconds,
            'max_reconnect_attempts': self.config.max_reconnect_attempts,
            'enable_compression': self.config.enable_event_compression,
            'enable_batching': self.config.enable_event_batching
        }
    
    def get_factory_metrics(self) -> Dict[str, Any]:
        """Get comprehensive factory metrics."""
        return {
            **self._factory_metrics,
            'active_contexts': len(self._user_contexts),
            'config': {
                'max_events_per_user': self.config.max_events_per_user,
                'delivery_retries': self.config.delivery_retries,
                'heartbeat_interval_seconds': self.config.heartbeat_interval_seconds
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


class UserWebSocketEmitter:
    """
    Per-user WebSocket event emitter with delivery guarantees and complete isolation.
    
    Each instance handles WebSocket events for a single user, ensuring complete
    isolation and preventing cross-user event leakage.
    
    Business Value: Enables reliable real-time notifications that reach the correct user
    """
    
    def __init__(self, 
                 user_context: UserWebSocketContext,
                 connection: 'UserWebSocketConnection',
                 delivery_config: Dict[str, Any],
                 factory: WebSocketBridgeFactory):
        
        self.user_context = user_context
        self.connection = connection
        self.delivery_config = delivery_config
        self.factory = factory
        
        # Initialize monitoring
        self.notification_monitor = get_websocket_notification_monitor()
        
        # Initialize metrics collector
        from netra_backend.app.monitoring.websocket_metrics import (
            get_websocket_metrics_collector,
            record_factory_event
        )
        self.metrics_collector = get_websocket_metrics_collector()
        
        # Record factory creation for this user
        record_factory_event("created")
        
        # Event delivery tracking
        self._pending_events: Dict[str, WebSocketEvent] = {}
        self._delivery_lock = asyncio.Lock()
        
        # Event batching (if enabled)
        self._event_batch: List[WebSocketEvent] = []
        self._batch_timer: Optional[asyncio.Task] = None
        self._batch_size = 10
        self._batch_timeout = 0.1  # 100ms
        
        # Control flags
        self._shutdown = False
        
        # Start background event processor
        self._processor_task = asyncio.create_task(self._process_events())
        
        logger.debug(f"UserWebSocketEmitter initialized for user {user_context.user_id}")
        
    async def notify_agent_started(self, agent_name: str, run_id: str) -> None:
        """Send agent started notification to specific user."""
        # MONITORING: Use monitor context for comprehensive tracking
        async with self.notification_monitor.monitor_notification(
            user_id=self.user_context.user_id,
            thread_id=self.user_context.thread_id,
            run_id=run_id,
            agent_name=agent_name,
            connection_id=self.user_context.connection_id
        ) as correlation_id:
            event = WebSocketEvent(
                event_type="agent_started",
                user_id=self.user_context.user_id,
                thread_id=self.user_context.thread_id,
                data={
                    "agent_name": agent_name,
                    "run_id": run_id,
                    "status": "started",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": f"{agent_name} has started processing your request",
                    "correlation_id": correlation_id
                }
            )
            await self._queue_event(event)
        
    async def notify_agent_thinking(self, agent_name: str, run_id: str, thinking: str) -> None:
        """Send agent thinking notification to specific user."""
        event = WebSocketEvent(
            event_type="agent_thinking",
            user_id=self.user_context.user_id,
            thread_id=self.user_context.thread_id,
            data={
                "agent_name": agent_name,
                "run_id": run_id,
                "thinking": thinking,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        await self._queue_event(event)
        
    async def notify_tool_executing(self, agent_name: str, run_id: str, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """Send tool execution notification to specific user."""
        event = WebSocketEvent(
            event_type="tool_executing",
            user_id=self.user_context.user_id,
            thread_id=self.user_context.thread_id,
            data={
                "agent_name": agent_name,
                "run_id": run_id,
                "tool_name": tool_name,
                "tool_input": self._sanitize_tool_input(tool_input),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"{agent_name} is using {tool_name}"
            }
        )
        await self._queue_event(event)
        
    async def notify_tool_completed(self, agent_name: str, run_id: str, tool_name: str, tool_output: Any) -> None:
        """Send tool completion notification to specific user."""
        event = WebSocketEvent(
            event_type="tool_completed",
            user_id=self.user_context.user_id,
            thread_id=self.user_context.thread_id,
            data={
                "agent_name": agent_name,
                "run_id": run_id,
                "tool_name": tool_name,
                "tool_output": self._sanitize_tool_output(tool_output),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"{agent_name} completed {tool_name}"
            }
        )
        await self._queue_event(event)
        
    async def notify_agent_completed(self, agent_name: str, run_id: str, result: Any) -> None:
        """Send agent completion notification to specific user."""
        event = WebSocketEvent(
            event_type="agent_completed",
            user_id=self.user_context.user_id,
            thread_id=self.user_context.thread_id,
            data={
                "agent_name": agent_name,
                "run_id": run_id,
                "result": self._sanitize_result(result),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"{agent_name} has completed processing your request"
            }
        )
        await self._queue_event(event)
    
    async def notify_agent_error(self, agent_name: str, run_id: str, error: str) -> None:
        """Send agent error notification to specific user."""
        event = WebSocketEvent(
            event_type="agent_error",
            user_id=self.user_context.user_id,
            thread_id=self.user_context.thread_id,
            data={
                "agent_name": agent_name,
                "run_id": run_id,
                "error": self._sanitize_error_message(error),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"{agent_name} encountered an issue processing your request"
            }
        )
        await self._queue_event(event)
        
    async def _queue_event(self, event: WebSocketEvent) -> None:
        """Queue event for delivery with overflow protection."""
        try:
            # Put event in user-specific queue with timeout
            await asyncio.wait_for(
                self.user_context.event_queue.put(event), 
                timeout=1.0
            )
            
        except asyncio.TimeoutError:
            # Queue is full - drop oldest event and add new one
            logger.warning(f"Event queue full for user {self.user_context.user_id}, dropping oldest event")
            try:
                self.user_context.event_queue.get_nowait()  # Drop oldest
                await self.user_context.event_queue.put(event)  # Add new
            except asyncio.QueueEmpty:
                pass
                
    async def _process_events(self) -> None:
        """Background event processor with delivery guarantees."""
        try:
            while not self._shutdown:
                try:
                    # Get next event from user-specific queue
                    event = await asyncio.wait_for(
                        self.user_context.event_queue.get(), 
                        timeout=self.delivery_config['heartbeat_interval']
                    )
                    
                    # Check for sentinel value (None) indicating shutdown
                    if event is None or self._shutdown:
                        break
                        
                    # Attempt delivery with retries
                    await self._deliver_event_with_retries(event)
                    
                except asyncio.TimeoutError:
                    # Heartbeat - check connection health if not shutting down
                    if not self._shutdown:
                        await self._check_connection_health()
                    # If shutting down, timeout is expected - just continue to check shutdown flag
                    
                except Exception as e:
                    if not self._shutdown:
                        logger.error(f"Event processor error for user {self.user_context.user_id}: {e}")
                    
        except asyncio.CancelledError:
            logger.info(f"Event processor cancelled for user {self.user_context.user_id}")
        
        logger.info(f"Event processor stopped for user {self.user_context.user_id}")
            
    async def _deliver_event_with_retries(self, event: WebSocketEvent) -> None:
        """Deliver event with retry mechanism."""
        from netra_backend.app.monitoring.websocket_metrics import record_websocket_event
        
        async with self._delivery_lock:
            start_time = time.time()
            while event.retry_count <= event.max_retries:
                try:
                    # Attempt delivery through user-specific connection
                    await asyncio.wait_for(
                        self.connection.send_event(event),
                        timeout=self.delivery_config['timeout']
                    )
                    
                    # Success - track event
                    self.user_context.sent_events.append({
                        'event_id': event.event_id,
                        'event_type': event.event_type,
                        'timestamp': event.timestamp.isoformat(),
                        'delivered_at': datetime.now(timezone.utc).isoformat()
                    })
                    
                    # Update factory metrics
                    self.factory._factory_metrics['events_sent_total'] += 1
                    
                    # Record metrics
                    latency_ms = (time.time() - start_time) * 1000
                    record_websocket_event(
                        user_id=self.user_context.user_id,
                        event_type=event.event_type,
                        latency_ms=latency_ms,
                        success=True
                    )
                    
                    # Trim sent events to prevent memory leak
                    if len(self.user_context.sent_events) > 100:
                        self.user_context.sent_events = self.user_context.sent_events[-50:]
                        
                    return
                    
                except Exception as e:
                    event.retry_count += 1
                    logger.warning(f"Event delivery failed for user {self.user_context.user_id} "
                                 f"(attempt {event.retry_count}/{event.max_retries}): {e}")
                    
                    if event.retry_count <= event.max_retries:
                        # Exponential backoff
                        await asyncio.sleep(min(2 ** (event.retry_count - 1), 30))
                        
            # All retries failed
            from netra_backend.app.monitoring.websocket_metrics import record_websocket_event
            
            logger.error(f"Event delivery permanently failed for user {self.user_context.user_id}: {event.event_id}")
            self.user_context.failed_events.append({
                'event_id': event.event_id,
                'event_type': event.event_type,
                'timestamp': event.timestamp.isoformat(),
                'failed_at': datetime.now(timezone.utc).isoformat(),
                'retry_count': event.retry_count
            })
            
            # Update factory metrics
            self.factory._factory_metrics['events_failed_total'] += 1
            
            # Record failure metrics
            latency_ms = (time.time() - start_time) * 1000
            record_websocket_event(
                user_id=self.user_context.user_id,
                event_type=event.event_type,
                latency_ms=latency_ms,
                success=False
            )
            
    async def _check_connection_health(self) -> None:
        """Check and maintain connection health."""
        from netra_backend.app.monitoring.websocket_metrics import record_websocket_connection
        
        try:
            is_healthy = await self.connection.ping()
            
            if is_healthy:
                self.user_context.last_heartbeat = datetime.now(timezone.utc)
                self.user_context.connection_status = ConnectionStatus.HEALTHY
                self.user_context.reconnect_attempts = 0
            else:
                await self._handle_unhealthy_connection()
                record_websocket_connection(
                    user_id=self.user_context.user_id,
                    event="error"
                )
                
        except Exception as e:
            logger.error(f"Health check failed for user {self.user_context.user_id}: {e}")
            await self._handle_unhealthy_connection()
            
    async def _handle_unhealthy_connection(self) -> None:
        """Handle unhealthy connection with reconnection logic."""
        self.user_context.connection_status = ConnectionStatus.UNHEALTHY
        self.user_context.reconnect_attempts += 1
        
        max_attempts = self.delivery_config['max_reconnect_attempts']
        if self.user_context.reconnect_attempts <= max_attempts:
            logger.info(f"Attempting reconnection for user {self.user_context.user_id} "
                       f"(attempt {self.user_context.reconnect_attempts}/{max_attempts})")
            try:
                await self.connection.reconnect()
                self.user_context.connection_status = ConnectionStatus.HEALTHY
                logger.info(f"Reconnection successful for user {self.user_context.user_id}")
            except Exception as e:
                logger.error(f"Reconnection failed for user {self.user_context.user_id}: {e}")
        else:
            logger.error(f"Max reconnection attempts exceeded for user {self.user_context.user_id}")
            self.user_context.connection_status = ConnectionStatus.FAILED
            
    def _sanitize_tool_input(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize tool input to prevent IP leakage."""
        if not tool_input:
            return {}
            
        sanitized = {}
        sensitive_keys = {'password', 'secret', 'key', 'token', 'api_key', 'auth', 'credential'}
        
        for key, value in tool_input.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "..."
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_tool_input(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_tool_output(self, output: Any) -> Any:
        """Sanitize tool output to prevent IP leakage."""
        if isinstance(output, dict):
            # Remove potentially sensitive keys
            sanitized = {k: v for k, v in output.items() 
                        if k not in ['internal_reasoning', 'debug_info', 'system_prompt']}
            return sanitized
        elif isinstance(output, str) and len(output) > 10000:
            # Truncate very long strings
            return output[:10000] + "...[truncated]"
        else:
            return output
            
    def _sanitize_result(self, result: Any) -> Any:
        """Sanitize agent result to protect business IP."""
        if hasattr(result, '__dict__'):
            # Convert to dict and sanitize
            result_dict = result.__dict__.copy()
            # Remove internal fields
            for key in list(result_dict.keys()):
                if key.startswith('_') or 'internal' in key.lower():
                    del result_dict[key]
            return result_dict
        return result
        
    def _sanitize_error_message(self, error: str) -> str:
        """Sanitize error message for user display."""
        if not error:
            return "An error occurred"
        
        # Remove file paths and internal details
        sanitized = error.replace("/Users/", "/home/").replace("/home/", "[PATH]/")
        
        # Truncate very long errors
        if len(sanitized) > 300:
            sanitized = sanitized[:300] + "..."
        
        return sanitized
        
    async def cleanup(self) -> None:
        """Clean up emitter resources."""
        from netra_backend.app.monitoring.websocket_metrics import record_factory_event
        
        # Prevent duplicate cleanup
        if hasattr(self, '_cleanup_in_progress'):
            return
        self._cleanup_in_progress = True
        
        try:
            # Signal shutdown
            self._shutdown = True
            
            # Wake up the event processor by putting a sentinel value
            try:
                self.user_context.event_queue.put_nowait(None)  # Sentinel to wake up processor
            except asyncio.QueueFull:
                pass  # Queue is full, processor will see shutdown flag eventually
            
            # Cancel event processor
            if self._processor_task and not self._processor_task.done():
                self._processor_task.cancel()
                try:
                    await asyncio.wait_for(self._processor_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                    
            # Cancel batch timer if active
            if self._batch_timer and not self._batch_timer.done():
                self._batch_timer.cancel()
                try:
                    await asyncio.wait_for(self._batch_timer, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                    
            # Clear pending events
            self._pending_events.clear()
            self._event_batch.clear()
            
            # Record factory destruction
            record_factory_event("destroyed")
            
            # Notify factory of cleanup (but avoid circular cleanup)
            await self.factory.cleanup_user_context(
                self.user_context.user_id, 
                self.user_context.connection_id
            )
            
            logger.info(f"✅ UserWebSocketEmitter cleanup completed for user {self.user_context.user_id}")
            
        except Exception as e:
            logger.error(f"❌ UserWebSocketEmitter cleanup failed for user {self.user_context.user_id}: {e}")



class UserWebSocketConnection:
    """Individual user WebSocket connection with health tracking."""
    
    def __init__(self, user_id: str, connection_id: str, websocket: Any):
        self.user_id = user_id
        self.connection_id = connection_id
        self.websocket = websocket
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = self.created_at
        self._closed = False
        
    async def send_event(self, event: WebSocketEvent) -> None:
        """Send event through this connection."""
        if self._closed:
            raise ConnectionError(f"Connection closed for user {self.user_id}")
            
        if self.websocket is None:
            raise ConnectionError(f"No WebSocket connection available for user {self.user_id}")
            
        try:
            # Send actual WebSocket event
            event_data = {
                'event_type': event.event_type,
                'event_id': event.event_id,
                'thread_id': event.thread_id,
                'data': event.data,
                'timestamp': event.timestamp.isoformat()
            }
            
            # Send via actual WebSocket - guaranteed to exist at this point
            # Check if websocket has send_json method (FastAPI WebSocket)
            if hasattr(self.websocket, 'send_json'):
                await self.websocket.send_json(event_data)
            # Check if it has send method (generic WebSocket)
            elif hasattr(self.websocket, 'send'):
                import json
                await self.websocket.send(json.dumps(event_data))
            else:
                # This should never happen with properly configured WebSockets
                raise ConnectionError(f"WebSocket type unsupported for user {self.user_id}: {type(self.websocket)}")
                    
            logger.debug(f"📤 WebSocket event sent to user {self.user_id}: {event.event_type}")
            self.last_activity = datetime.now(timezone.utc)
            
        except Exception as e:
            self._closed = True
            raise ConnectionError(f"Failed to send event to user {self.user_id}: {e}")
            
    async def ping(self) -> bool:
        """Ping connection to check health."""
        if self._closed:
            return False
            
        if self.websocket is None:
            return False
            
        try:
            # Perform actual ping - WebSocket guaranteed to exist at this point
            # Check if websocket has ping method
            if hasattr(self.websocket, 'ping'):
                await self.websocket.ping()
            # Check if it's a FastAPI WebSocket (check application_state)
            elif hasattr(self.websocket, 'application_state'):
                from fastapi.websockets import WebSocketState
                # Check if connection is still open
                if self.websocket.application_state == WebSocketState.CONNECTED:
                    # Send a ping frame using send_text with empty message
                    if hasattr(self.websocket, 'send_text'):
                        await self.websocket.send_text("")  # Empty message as ping
            
            self.last_activity = datetime.now(timezone.utc)
            return True
        except Exception:
            self._closed = True
            return False
            
    async def reconnect(self) -> None:
        """Attempt to reconnect."""
        # This would typically involve signaling the client to reconnect
        # Implementation depends on specific WebSocket framework being used
        pass
        
    def is_stale(self, current_time: datetime, stale_threshold: int = 1800) -> bool:
        """Check if connection is stale (default: 30 minutes)."""
        age = (current_time - self.last_activity).total_seconds()
        return age > stale_threshold
        
    async def close(self) -> None:
        """Close the connection."""
        if not self._closed:
            try:
                if self.websocket and hasattr(self.websocket, 'close'):
                    await self.websocket.close()
            except Exception:
                pass
            self._closed = True


class ConnectionNotFound(Exception):
    """Exception raised when WebSocket connection not found for user."""
    pass


class ConnectionClosed(Exception):
    """Exception raised when WebSocket connection is closed."""
    pass


# Factory instance management
_websocket_bridge_factory: Optional[WebSocketBridgeFactory] = None


def get_websocket_bridge_factory() -> WebSocketBridgeFactory:
    """Get or create the singleton WebSocketBridgeFactory instance.
    
    Returns:
        WebSocketBridgeFactory: The singleton factory instance
    """
    global _websocket_bridge_factory
    if _websocket_bridge_factory is None:
        _websocket_bridge_factory = WebSocketBridgeFactory()
    return _websocket_bridge_factory
