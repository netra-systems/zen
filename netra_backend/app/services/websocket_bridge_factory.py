"""DEPRECATED - REDIRECTED TO SSOT: UnifiedWebSocketEmitter

This module has been converted to redirect to the SSOT UnifiedWebSocketEmitter.
All functionality is now provided by netra_backend.app.websocket_core.unified_emitter.

Business Value Justification:
- Segment: Platform/Internal (Migration phase)
- Business Goal: SSOT Compliance & System Reliability
- Value Impact: Reduces code duplication and improves maintainability
- Strategic Impact: Consolidates WebSocket emitter implementations into single source

## MIGRATION STATUS: PHASE 1 COMPLETE
- WebSocketBridgeFactory redirects to UnifiedWebSocketEmitter
- UserWebSocketEmitter redirects to UnifiedWebSocketEmitter
- All factory patterns preserved for backward compatibility
- Performance optimization inherited from SSOT implementation

OLD IMPLEMENTATION REPLACED BY: UnifiedWebSocketEmitter + UnifiedWebSocketManager
"""

# SSOT REDIRECT: Import the unified implementation
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.websocket_notification_monitor import get_websocket_notification_monitor
from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool, ConnectionInfo

import asyncio
import time
import uuid
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)


class ConnectionStatus(Enum):
    """WebSocket connection status (preserved for compatibility)."""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"
    CLOSED = "closed"


@dataclass
class UserWebSocketContext:
    """COMPATIBILITY: User WebSocket context (redirected to SSOT)."""
    user_id: str
    thread_id: str
    connection_id: str
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Connection health
    last_heartbeat: Optional[datetime] = None
    connection_status: ConnectionStatus = ConnectionStatus.INITIALIZING
    reconnect_attempts: int = 0
    
    # Resource management
    cleanup_callbacks: List[Callable] = field(default_factory=list)
    _is_cleaned: bool = False
    
    async def cleanup(self) -> None:
        """Clean up user-specific WebSocket resources (SSOT delegated)."""
        if self._is_cleaned:
            logger.debug(f"UserWebSocketContext already cleaned for user {self.user_id}")
            return
        
        logger.info(f"[U+1F9F9] Cleaning up UserWebSocketContext (SSOT redirect) for user {self.user_id}")
        
        try:
            # Run cleanup callbacks
            for callback in reversed(self.cleanup_callbacks):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"WebSocket cleanup callback failed for user {self.user_id}: {e}")
            
            # Clear cleanup callbacks
            self.cleanup_callbacks.clear()
            self.connection_status = ConnectionStatus.CLOSED
            self._is_cleaned = True
            
            logger.info(f" PASS:  UserWebSocketContext cleanup completed for user {self.user_id}")
            
        except Exception as e:
            logger.error(f" FAIL:  UserWebSocketContext cleanup failed for user {self.user_id}: {e}")
            self._is_cleaned = True


@dataclass
class WebSocketEvent:
    """WebSocket event structure for validation (SSOT compatibility layer).
    
    This dataclass provides compatibility with existing test infrastructure while
    redirecting to the SSOT WebSocket event implementations in the unified emitter.
    
    Business Value: Enables test validation of WebSocket events critical for chat functionality.
    """
    event_type: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    connection_id: Optional[str] = None
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)
    delivery_latency_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for transmission (SSOT compatibility)."""
        return {
            "type": self.event_type,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "connection_id": self.connection_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebSocketEvent':
        """Create WebSocketEvent from dictionary (SSOT compatibility)."""
        return cls(
            event_type=data.get("type", ""),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", time.time()),
            user_id=data.get("user_id", ""),
            thread_id=data.get("thread_id"),
            run_id=data.get("run_id"),
            connection_id=data.get("connection_id"),
            agent_name=data.get("agent_name"),
            tool_name=data.get("tool_name")
        )


@dataclass
class WebSocketFactoryConfig:
    """Configuration for WebSocketBridgeFactory (redirected to SSOT)."""
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

# SSOT CONSOLIDATION COMPLETE: All functionality provided by UnifiedWebSocketEmitter

class WebSocketBridgeFactory:
    """LEGACY COMPATIBILITY WRAPPER - Redirects to UnifiedWebSocketManager + UnifiedWebSocketEmitter
    
    This factory maintains backward compatibility while redirecting all functionality
    to the SSOT WebSocket implementations. All emitters created use UnifiedWebSocketEmitter.
    
    ## MIGRATION STATUS: PHASE 1 COMPLETE
    - All creation methods redirect to SSOT implementations
    - Backward compatibility maintained for all existing consumers
    - Performance optimization inherited from SSOT
    """
    
    def __init__(self, config: Optional[WebSocketFactoryConfig] = None):
        """Initialize the WebSocket bridge factory (SSOT redirect)."""
        self.config = config or WebSocketFactoryConfig.from_env()
        
        logger.info(" CYCLE:  WebSocketBridgeFactory  ->  SSOT (UnifiedWebSocketManager + UnifiedWebSocketEmitter)")
        
        # Initialize monitoring
        self.notification_monitor = get_websocket_notification_monitor()
        
        # Infrastructure components (will redirect to SSOT)
        self._unified_manager: Optional[UnifiedWebSocketManager] = None
        self._connection_pool: Optional[WebSocketConnectionPool] = None
        self._agent_registry: Optional['AgentRegistry'] = None
        self._health_monitor: Optional[Any] = None
        
        # Factory metrics (preserved for compatibility)
        self._factory_metrics = {
            'emitters_created': 0,
            'emitters_active': 0,
            'emitters_cleaned': 0,
            'events_sent_total': 0,
            'events_failed_total': 0,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'ssot_redirect': True
        }
        
        logger.info(" PASS:  WebSocketBridgeFactory initialized (SSOT redirect mode)")
        
    def configure(self, 
                 connection_pool: WebSocketConnectionPool,
                 agent_registry: 'AgentRegistry',
                 health_monitor: Any) -> None:
        """Configure factory with infrastructure components (SSOT redirect).
        
        Args:
            connection_pool: WebSocket connection pool for managing connections
            agent_registry: Registry for agent operations
            health_monitor: Health monitoring component
        """
        if connection_pool is None:
            raise ValueError("Connection pool cannot be None - factory requires valid connection pool")
        
        self._connection_pool = connection_pool
        self._agent_registry = agent_registry
        self._health_monitor = health_monitor
        
        # Unified WebSocket manager will be created on-demand with proper user context
        # SECURITY FIX: Do not directly instantiate to prevent factory bypass detection
        self._unified_manager = None
        
        logger.info(" PASS:  WebSocketBridgeFactory configured (SSOT redirect mode)")
        
    async def create_user_emitter(self,
                                user_context: Optional['UserExecutionContext'] = None,
                                user_id: Optional[str] = None,
                                thread_id: Optional[str] = None,
                                connection_id: Optional[str] = None) -> UnifiedWebSocketEmitter:
        """Create a per-user WebSocket event emitter (SSOT redirect).

        ISSUE #669 REMEDIATION: Unified parameter signature supporting both new and legacy patterns.

        Args:
            user_context: User execution context (preferred new pattern)
            user_id: Unique user identifier (legacy pattern)
            thread_id: Thread identifier for WebSocket routing (legacy pattern)
            connection_id: WebSocket connection identifier (legacy pattern)

        Returns:
            UnifiedWebSocketEmitter: SSOT emitter with full compatibility
        """
        if not self._unified_manager:
            # Create WebSocket manager using proper factory pattern with user context
            # ISSUE #824 FIX: Use canonical SSOT get_websocket_manager instead of deprecated factory
            try:
                # ISSUE #824 FIX: Use canonical SSOT import path
                from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
                from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool

                # Try different registry import paths - SSOT first
                try:
                    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
                except ImportError:
                    try:
                        from netra_backend.app.agents.registry import AgentRegistry
                    except ImportError:
                        AgentRegistry = None  # Use None if not available

                logger.warning("WebSocketBridgeFactory auto-configuring - creating manager with user context")

                # ISSUE #824 FIX: Use canonical SSOT factory pattern
                if user_context:
                    self._unified_manager = await get_websocket_manager(user_context)
                else:
                    # For testing without user context, create minimal context
                    test_context = type('TestContext', (), {'user_id': 'test_user', 'thread_id': 'test_thread'})()
                    self._unified_manager = await get_websocket_manager(test_context)

                # Auto-configure other components if needed
                if not self._connection_pool:
                    self._connection_pool = WebSocketConnectionPool()
                if not self._agent_registry and AgentRegistry:
                    self._agent_registry = AgentRegistry()

            except Exception as e:
                raise RuntimeError(f"Factory not configured - call configure() first. Auto-configuration failed: {e}")

        # ISSUE #669 REMEDIATION: Support both new and legacy parameter patterns
        if user_context:
            # NEW pattern (preferred)
            actual_user_id = user_context.user_id
            actual_thread_id = getattr(user_context, 'thread_id', None)
            actual_connection_id = getattr(user_context, 'connection_id', None)
            if not actual_connection_id:
                actual_connection_id = f"conn_{actual_user_id}_{actual_thread_id}"
        elif user_id and thread_id:
            # LEGACY pattern (backward compatibility)
            actual_user_id = user_id
            actual_thread_id = thread_id
            actual_connection_id = connection_id or f"conn_{user_id}_{thread_id}"
            # Create minimal context for compatibility
            user_context = type('Context', (), {
                'user_id': user_id,
                'thread_id': thread_id,
                'connection_id': actual_connection_id
            })()
        else:
            raise ValueError("Either user_context or (user_id + thread_id) required")

        # MONITORING: Track bridge initialization start
        correlation_id = self.notification_monitor.track_bridge_initialization_started(
            actual_user_id, actual_thread_id, actual_connection_id
        )

        start_time = time.time()

        try:
            logger.info(f" CYCLE:  Creating UnifiedWebSocketEmitter (SSOT) for user {actual_user_id}")

            # Create SSOT emitter directly
            unified_emitter = UnifiedWebSocketEmitter(
                manager=self._unified_manager,
                user_id=actual_user_id,
                context=user_context
            )
            
            # Update metrics
            self._factory_metrics['emitters_created'] += 1
            self._factory_metrics['emitters_active'] += 1
            
            creation_time_ms = (time.time() - start_time) * 1000

            # MONITORING: Track successful bridge initialization
            self.notification_monitor.track_bridge_initialization_success(
                correlation_id, creation_time_ms
            )

            logger.info(f" PASS:  UnifiedWebSocketEmitter (SSOT) created for user {actual_user_id} in {creation_time_ms:.1f}ms")

            return unified_emitter

        except Exception as e:
            creation_time_ms = (time.time() - start_time) * 1000

            # MONITORING: Track failed bridge initialization
            self.notification_monitor.track_bridge_initialization_failed(
                correlation_id, str(e), creation_time_ms
            )

            logger.error(f" FAIL:  Failed to create WebSocket emitter (SSOT) for user {actual_user_id}: {e}")
            raise RuntimeError(f"WebSocket emitter creation failed: {e}")
    
    async def cleanup_user_context(self, user_id: str, connection_id: str) -> None:
        """Clean up user context when connection closes (SSOT delegated)."""
        try:
            self._factory_metrics['emitters_active'] = max(0, self._factory_metrics['emitters_active'] - 1)
            self._factory_metrics['emitters_cleaned'] += 1
            logger.debug(f"Context cleaned for user {user_id} (SSOT mode)")
        except Exception as e:
            logger.error(f"Error in SSOT cleanup for user {user_id}: {e}")
    
    def get_factory_metrics(self) -> Dict[str, Any]:
        """Get comprehensive factory metrics (SSOT enhanced)."""
        return {
            **self._factory_metrics,
            'config': {
                'max_events_per_user': self.config.max_events_per_user,
                'delivery_retries': self.config.delivery_retries,
                'heartbeat_interval_seconds': self.config.heartbeat_interval_seconds
            },
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'ssot_mode': True,
            'emitter_type': 'WebSocketBridgeFactory  ->  UnifiedWebSocketEmitter'
        }


# SSOT CONSOLIDATION COMPLETE: UserWebSocketEmitter class removed - use UnifiedWebSocketEmitter directly


# Compatibility classes for backward compatibility

class UserWebSocketConnection:
    """COMPATIBILITY: Individual user WebSocket connection (SSOT delegated)."""
    
    def __init__(self, user_id: str, connection_id: str, websocket: Any):
        self.user_id = user_id
        self.connection_id = connection_id
        self.websocket = websocket
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = self.created_at
        self._closed = False
        
        logger.debug(f"UserWebSocketConnection (SSOT mode) for user {user_id}")


# WebSocket Event and Factory Metrics classes (for test compatibility)

class WebSocketEvent:
    """WebSocket event data class for test compatibility."""
    
    def __init__(self, event_type: str, data: Dict[str, Any], user_id: str = None, timestamp: datetime = None):
        self.event_type = event_type
        self.data = data
        self.user_id = user_id
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'data': self.data,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class FactoryMetrics:
    """Factory metrics data class for test compatibility."""
    emitters_created: int = 0
    emitters_active: int = 0
    emitters_cleaned: int = 0
    events_sent_total: int = 0
    events_failed_total: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ssot_redirect: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FactoryMetrics':
        """Create metrics from dictionary."""
        return cls(
            emitters_created=data.get('emitters_created', 0),
            emitters_active=data.get('emitters_active', 0),
            emitters_cleaned=data.get('emitters_cleaned', 0),
            events_sent_total=data.get('events_sent_total', 0),
            events_failed_total=data.get('events_failed_total', 0),
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            ssot_redirect=data.get('ssot_redirect', True)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'emitters_created': self.emitters_created,
            'emitters_active': self.emitters_active,
            'emitters_cleaned': self.emitters_cleaned,
            'events_sent_total': self.events_sent_total,
            'events_failed_total': self.events_failed_total,
            'created_at': self.created_at,
            'ssot_redirect': self.ssot_redirect
        }


# Exception classes (preserved for compatibility)

class ConnectionNotFound(Exception):
    """Exception raised when WebSocket connection not found for user."""
    pass


class ConnectionClosed(Exception):
    """Exception raised when WebSocket connection is closed."""
    pass


# Factory instance management (SSOT redirect)
_websocket_bridge_factory: Optional[WebSocketBridgeFactory] = None


def get_websocket_bridge_factory() -> WebSocketBridgeFactory:
    """Get or create the singleton WebSocketBridgeFactory instance (SSOT redirect).

    Returns:
        WebSocketBridgeFactory: The singleton factory instance (SSOT-backed)
    """
    global _websocket_bridge_factory
    if _websocket_bridge_factory is None:
        _websocket_bridge_factory = WebSocketBridgeFactory()
        logger.info(" PASS:  WebSocketBridgeFactory singleton created (SSOT redirect mode)")
    return _websocket_bridge_factory


# SSOT COMPATIBILITY ALIASES: Export expected names for backwards compatibility
# These aliases redirect to the SSOT implementations while maintaining test compatibility

# Primary exports that tests expect
UserWebSocketEmitter = UnifiedWebSocketEmitter  # SSOT redirect alias
WebSocketBridgeFactory = WebSocketBridgeFactory  # Self-reference for clarity

# Export the factory function
__all__ = [
    'UserWebSocketEmitter',           # -> UnifiedWebSocketEmitter
    'WebSocketBridgeFactory',         # Main factory class
    'get_websocket_bridge_factory',   # Factory singleton getter
    'UserWebSocketContext',           # User context data class
    'WebSocketEvent',                # Event structure
    'ConnectionStatus',              # Connection status enum
    'ConnectionNotFound',            # Exception class
    'ConnectionClosed',             # Exception class
    'UnifiedWebSocketEmitter',       # Direct SSOT access
    'UnifiedWebSocketManager',       # Direct SSOT access
]