"""
WebSocket Manager Factory - Secure Multi-User WebSocket Management

This module provides a factory pattern implementation to replace the singleton
WebSocket manager that was causing critical security vulnerabilities. The factory
creates isolated WebSocket manager instances per user connection, ensuring complete
user isolation and preventing message cross-contamination.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Eliminate critical security vulnerabilities in WebSocket communication
- Value Impact: Enables safe multi-user AI interactions without data leakage
- Revenue Impact: Prevents catastrophic security breaches that could destroy business

SECURITY CRITICAL: This implementation addresses the following vulnerabilities:
1. Message cross-contamination between users
2. Shared state mutations affecting all users
3. Connection hijacking possibilities
4. Memory leak accumulation
5. Race conditions in concurrent operations
6. Broadcast information leakage

Architecture Pattern: Factory + Isolation + Lifecycle Management
- WebSocketManagerFactory: Creates isolated manager instances
- IsolatedWebSocketManager: Per-connection manager with private state
- ConnectionLifecycleManager: Handles connection lifecycle and cleanup
- UserExecutionContext: Enforces user isolation at all levels
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Any, List
from dataclasses import dataclass, field
import weakref
from threading import RLock
import logging

from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class FactoryMetrics:
    """Metrics for monitoring factory performance and security."""
    managers_created: int = 0
    managers_active: int = 0
    managers_cleaned_up: int = 0
    users_with_active_managers: int = 0
    resource_limit_hits: int = 0
    total_connections_managed: int = 0
    security_violations_detected: int = 0
    average_manager_lifetime_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for monitoring."""
        return {
            "managers_created": self.managers_created,
            "managers_active": self.managers_active,
            "managers_cleaned_up": self.managers_cleaned_up,
            "users_with_active_managers": self.users_with_active_managers,
            "resource_limit_hits": self.resource_limit_hits,
            "total_connections_managed": self.total_connections_managed,
            "security_violations_detected": self.security_violations_detected,
            "average_manager_lifetime_seconds": self.average_manager_lifetime_seconds
        }


@dataclass
class ManagerMetrics:
    """Metrics for individual WebSocket manager instances."""
    connections_managed: int = 0
    messages_sent_total: int = 0
    messages_failed_total: int = 0
    last_activity: Optional[datetime] = None
    manager_age_seconds: float = 0.0
    cleanup_scheduled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for monitoring."""
        return {
            "connections_managed": self.connections_managed,
            "messages_sent_total": self.messages_sent_total,
            "messages_failed_total": self.messages_failed_total,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "manager_age_seconds": self.manager_age_seconds,
            "cleanup_scheduled": self.cleanup_scheduled
        }


class ConnectionLifecycleManager:
    """
    Manages the lifecycle of WebSocket connections with automatic cleanup.
    
    This class handles:
    - Connection registration and health monitoring
    - Automatic cleanup of expired connections
    - Resource leak prevention
    - Connection state validation
    - Security audit logging
    """
    
    def __init__(self, user_context: UserExecutionContext, ws_manager: 'IsolatedWebSocketManager'):
        """
        Initialize connection lifecycle manager.
        
        Args:
            user_context: User execution context for this connection
            ws_manager: The isolated WebSocket manager to manage
        """
        self.user_context = user_context
        self.ws_manager = ws_manager
        self._managed_connections: Set[str] = set()
        self._connection_health: Dict[str, datetime] = {}
        self._cleanup_timer: Optional[asyncio.Task] = None
        self._health_monitor_func = None
        self._is_active = True
        
        # Start health monitoring (deferred if no event loop)
        self._start_health_monitoring()
        
        logger.info(f"ConnectionLifecycleManager initialized for user {user_context.user_id[:8]}...")
    
    def register_connection(self, conn: WebSocketConnection) -> None:
        """
        Register a connection for lifecycle management.
        
        Args:
            conn: WebSocket connection to manage
            
        Raises:
            ValueError: If connection doesn't belong to this user context
        """
        # SECURITY: Validate connection belongs to this user
        if conn.user_id != self.user_context.user_id:
            logger.critical(
                f"SECURITY VIOLATION: Attempted to register connection for user {conn.user_id} "
                f"in manager for user {self.user_context.user_id}. This indicates a potential "
                f"connection hijacking attempt or context isolation failure."
            )
            raise ValueError(
                f"Connection user_id {conn.user_id} does not match context user_id {self.user_context.user_id}. "
                f"This violates user isolation requirements."
            )
        
        self._managed_connections.add(conn.connection_id)
        self._connection_health[conn.connection_id] = datetime.utcnow()
        
        logger.info(
            f"Registered connection {conn.connection_id} for user {self.user_context.user_id[:8]}... "
            f"(Total managed: {len(self._managed_connections)})"
        )
    
    def health_check_connection(self, conn_id: str) -> bool:
        """
        Check if a connection is healthy and responsive.
        
        Args:
            conn_id: Connection ID to check
            
        Returns:
            True if connection is healthy, False otherwise
        """
        if conn_id not in self._managed_connections:
            return False
        
        # Update last seen time
        self._connection_health[conn_id] = datetime.utcnow()
        
        # Get connection from manager
        connection = self.ws_manager.get_connection(conn_id)
        if not connection or not connection.websocket:
            logger.warning(f"Connection {conn_id} has no valid websocket")
            return False
        
        # TODO: Add more sophisticated health checks
        # - WebSocket state validation
        # - Ping/pong test
        # - Response time measurement
        
        return True
    
    async def auto_cleanup_expired(self) -> int:
        """
        Automatically cleanup expired connections.
        
        Returns:
            Number of connections cleaned up
        """
        if not self._is_active:
            return 0
        
        # Ensure health monitoring is started now that we have an event loop
        await self._ensure_health_monitoring_started()
        
        expired_connections = []
        cutoff_time = datetime.utcnow() - timedelta(minutes=30)  # 30-minute timeout
        
        for conn_id, last_health in self._connection_health.items():
            if last_health < cutoff_time:
                expired_connections.append(conn_id)
        
        cleaned_count = 0
        for conn_id in expired_connections:
            try:
                await self.ws_manager.remove_connection(conn_id)
                self._managed_connections.discard(conn_id)
                self._connection_health.pop(conn_id, None)
                cleaned_count += 1
                
                logger.info(f"Auto-cleaned expired connection {conn_id}")
                
            except Exception as e:
                logger.error(f"Failed to auto-cleanup connection {conn_id}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Auto-cleanup completed: {cleaned_count} expired connections removed")
        
        return cleaned_count
    
    async def force_cleanup_all(self) -> None:
        """Force cleanup of all managed connections."""
        self._is_active = False
        
        # Cancel health monitoring
        if self._cleanup_timer and not self._cleanup_timer.done():
            self._cleanup_timer.cancel()
            try:
                await self._cleanup_timer
            except asyncio.CancelledError:
                pass
        
        # Cleanup all connections
        connection_ids = list(self._managed_connections)
        for conn_id in connection_ids:
            try:
                await self.ws_manager.remove_connection(conn_id)
            except Exception as e:
                logger.error(f"Failed to cleanup connection {conn_id} during force cleanup: {e}")
        
        self._managed_connections.clear()
        self._connection_health.clear()
        
        logger.info(
            f"Force cleanup completed for user {self.user_context.user_id[:8]}... "
            f"({len(connection_ids)} connections cleaned)"
        )
    
    def _start_health_monitoring(self) -> None:
        """Start background health monitoring task."""
        async def health_monitor():
            while self._is_active:
                try:
                    await asyncio.sleep(60)  # Check every minute
                    if self._is_active:
                        await self.auto_cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
        
        # Defer task creation - only create when event loop is available
        try:
            self._cleanup_timer = asyncio.create_task(health_monitor())
        except RuntimeError:
            # No event loop running - defer until first async operation
            self._cleanup_timer = None
            self._health_monitor_func = health_monitor
    
    async def _ensure_health_monitoring_started(self) -> None:
        """Ensure health monitoring is started when async operations begin."""
        if self._cleanup_timer is None and self._health_monitor_func is not None and self._is_active:
            try:
                self._cleanup_timer = asyncio.create_task(self._health_monitor_func())
                self._health_monitor_func = None  # Clear reference
            except RuntimeError:
                # Still no event loop - will try again later
                pass


class IsolatedWebSocketManager:
    """
    User-isolated WebSocket manager with completely private state.
    
    This class provides the same interface as UnifiedWebSocketManager but with
    complete user isolation. Each instance manages connections for only one user
    and maintains private state that cannot be accessed by other users.
    
    SECURITY FEATURES:
    - Private connection dictionary (no shared state)
    - Private message queue and error recovery
    - UserExecutionContext enforcement on all operations
    - Connection-scoped lifecycle management
    - Isolated error handling and metrics
    """
    
    def __init__(self, user_context: UserExecutionContext):
        """
        Initialize isolated WebSocket manager for a specific user.
        
        Args:
            user_context: User execution context for isolation
            
        Raises:
            ValueError: If user_context is invalid
        """
        if not isinstance(user_context, UserExecutionContext):
            raise ValueError("user_context must be a UserExecutionContext instance")
        
        self.user_context = user_context
        self._connections: Dict[str, WebSocketConnection] = {}
        self._connection_ids: Set[str] = set()
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._manager_lock = asyncio.Lock()
        self.created_at = datetime.utcnow()
        self._is_active = True
        
        # Metrics tracking
        self._metrics = ManagerMetrics()
        self._metrics.last_activity = self.created_at
        
        # Connection lifecycle manager
        self._lifecycle_manager = ConnectionLifecycleManager(user_context, self)
        
        # Error recovery system (isolated per user)
        self._message_recovery_queue: List[Dict] = []
        self._connection_error_count: int = 0
        self._last_error_time: Optional[datetime] = None
        
        logger.info(
            f"IsolatedWebSocketManager created for user {user_context.user_id[:8]}... "
            f"(manager_id: {id(self)})"
        )
    
    def _validate_active(self) -> None:
        """Validate that this manager is still active."""
        if not self._is_active:
            raise RuntimeError(
                f"WebSocket manager for user {self.user_context.user_id} is no longer active. "
                f"This manager has been cleaned up and should not be used."
            )
    
    def _update_activity(self) -> None:
        """Update last activity timestamp."""
        self._metrics.last_activity = datetime.utcnow()
        self._metrics.manager_age_seconds = (
            datetime.utcnow() - self.created_at
        ).total_seconds()
    
    async def add_connection(self, connection: WebSocketConnection) -> None:
        """
        Add a WebSocket connection to this isolated manager.
        
        Args:
            connection: WebSocket connection to add
            
        Raises:
            ValueError: If connection doesn't belong to this user
            RuntimeError: If manager is not active
        """
        self._validate_active()
        
        # SECURITY: Strict user validation
        if connection.user_id != self.user_context.user_id:
            logger.critical(
                f"SECURITY VIOLATION: Attempted to add connection for user {connection.user_id} "
                f"to manager for user {self.user_context.user_id}. This indicates a potential "
                f"context isolation failure or malicious activity."
            )
            raise ValueError(
                f"Connection user_id {connection.user_id} does not match manager user_id {self.user_context.user_id}. "
                f"This violates user isolation requirements."
            )
        
        async with self._manager_lock:
            self._connections[connection.connection_id] = connection
            self._connection_ids.add(connection.connection_id)
            
            # Update metrics
            self._metrics.connections_managed = len(self._connections)
            self._update_activity()
            
            # Register with lifecycle manager
            self._lifecycle_manager.register_connection(connection)
            
            logger.info(
                f"Added connection {connection.connection_id} to isolated manager "
                f"for user {self.user_context.user_id[:8]}... "
                f"(Total connections: {len(self._connections)})"
            )
    
    async def remove_connection(self, connection_id: str) -> None:
        """
        Remove a WebSocket connection from this isolated manager.
        
        Args:
            connection_id: Connection ID to remove
        """
        self._validate_active()
        
        async with self._manager_lock:
            if connection_id in self._connections:
                connection = self._connections[connection_id]
                
                # SECURITY: Verify this connection belongs to our user
                if connection.user_id != self.user_context.user_id:
                    logger.critical(
                        f"SECURITY VIOLATION: Attempted to remove connection {connection_id} "
                        f"for user {connection.user_id} from manager for user {self.user_context.user_id}. "
                        f"This should be impossible and indicates a serious bug."
                    )
                    return
                
                del self._connections[connection_id]
                self._connection_ids.discard(connection_id)
                
                # Update metrics
                self._metrics.connections_managed = len(self._connections)
                self._update_activity()
                
                logger.info(
                    f"Removed connection {connection_id} from isolated manager "
                    f"for user {self.user_context.user_id[:8]}... "
                    f"(Remaining connections: {len(self._connections)})"
                )
            else:
                logger.debug(f"Connection {connection_id} not found for removal")
    
    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """
        Get a specific connection from this isolated manager.
        
        Args:
            connection_id: Connection ID to retrieve
            
        Returns:
            WebSocketConnection if found, None otherwise
        """
        self._validate_active()
        return self._connections.get(connection_id)
    
    def get_user_connections(self) -> Set[str]:
        """
        Get all connection IDs for this user.
        
        Returns:
            Set of connection IDs
        """
        self._validate_active()
        return self._connection_ids.copy()
    
    def is_connection_active(self, user_id: str) -> bool:
        """
        Check if user has active WebSocket connections.
        CRITICAL for authentication event validation.
        
        Args:
            user_id: User ID to check (must match this manager's user)
            
        Returns:
            True if user has at least one active connection, False otherwise
            
        Raises:
            ValueError: If user_id doesn't match this manager's user
        """
        self._validate_active()
        
        # SECURITY: Validate that the requested user_id matches this manager's user
        if user_id != self.user_context.user_id:
            logger.warning(
                f"SECURITY WARNING: Requested connection status for user {user_id} "
                f"from isolated manager for user {self.user_context.user_id}. "
                f"This violates user isolation."
            )
            return False
        
        # Check if we have any connections
        if not self._connection_ids:
            return False
        
        # Check if at least one connection is still valid
        for conn_id in self._connection_ids:
            connection = self.get_connection(conn_id)
            if connection and connection.websocket:
                # TODO: Add more sophisticated health check if websocket has state
                return True
        
        return False
    
    async def send_to_user(self, message: Dict[str, Any]) -> None:
        """
        Send a message to all connections for this user.
        
        Args:
            message: Message to send
            
        Raises:
            RuntimeError: If manager is not active
        """
        self._validate_active()
        
        async with self._manager_lock:
            connection_ids = list(self._connection_ids)
            
            if not connection_ids:
                logger.warning(
                    f"No connections available for user {self.user_context.user_id[:8]}... "
                    f"Message type: {message.get('type', 'unknown')}"
                )
                # Store for recovery
                self._message_recovery_queue.append({
                    **message,
                    'failed_at': datetime.utcnow().isoformat(),
                    'failure_reason': 'no_connections'
                })
                self._metrics.messages_failed_total += 1
                return
            
            successful_sends = 0
            failed_connections = []
            
            for conn_id in connection_ids:
                connection = self._connections.get(conn_id)
                if connection and connection.websocket:
                    try:
                        await connection.websocket.send_json(message)
                        successful_sends += 1
                        logger.debug(f"Sent message to connection {conn_id}")
                        
                    except Exception as e:
                        logger.error(
                            f"Failed to send message to connection {conn_id} "
                            f"for user {self.user_context.user_id[:8]}...: {e}"
                        )
                        failed_connections.append(conn_id)
                else:
                    logger.warning(f"Invalid connection {conn_id} - removing from manager")
                    failed_connections.append(conn_id)
            
            # Update metrics
            if successful_sends > 0:
                self._metrics.messages_sent_total += successful_sends
            if failed_connections:
                self._metrics.messages_failed_total += len(failed_connections)
            
            self._update_activity()
            
            # Clean up failed connections
            for conn_id in failed_connections:
                try:
                    await self.remove_connection(conn_id)
                except Exception as e:
                    logger.error(f"Failed to cleanup connection {conn_id}: {e}")
            
            if successful_sends == 0:
                logger.error(
                    f"Complete message delivery failure for user {self.user_context.user_id[:8]}... "
                    f"Message type: {message.get('type', 'unknown')}"
                )
    
    async def emit_critical_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit a critical event to this user with guaranteed delivery tracking.
        
        Args:
            event_type: Type of event (e.g., 'agent_started', 'tool_executing')
            data: Event payload
            
        Raises:
            ValueError: If event parameters are invalid
            RuntimeError: If manager is not active
        """
        self._validate_active()
        
        # Validate parameters
        if not event_type or not event_type.strip():
            raise ValueError("event_type cannot be empty for critical event")
        
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "critical": True,
            "user_context": {
                "user_id": self.user_context.user_id,
                "request_id": self.user_context.request_id
            }
        }
        
        try:
            await self.send_to_user(message)
            logger.debug(
                f"Successfully emitted critical event {event_type} "
                f"to user {self.user_context.user_id[:8]}..."
            )
        except Exception as e:
            logger.critical(
                f"CRITICAL EVENT EMISSION FAILURE: Failed to emit {event_type} "
                f"to user {self.user_context.user_id[:8]}...: {e}"
            )
            # Store for recovery
            self._message_recovery_queue.append({
                **message,
                'failed_at': datetime.utcnow().isoformat(),
                'failure_reason': f'emission_error: {e}'
            })
            raise
    
    async def cleanup_all_connections(self) -> None:
        """Clean up all connections and deactivate this manager."""
        logger.info(f"Cleaning up isolated manager for user {self.user_context.user_id[:8]}...")
        
        # Mark as inactive
        self._is_active = False
        self._metrics.cleanup_scheduled = True
        
        # Use lifecycle manager for cleanup
        await self._lifecycle_manager.force_cleanup_all()
        
        # Clear our internal state
        async with self._manager_lock:
            self._connections.clear()
            self._connection_ids.clear()
            
            # Clear recovery queue
            self._message_recovery_queue.clear()
        
        logger.info(f"Cleanup completed for isolated manager for user {self.user_context.user_id[:8]}...")
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for this manager.
        
        Returns:
            Dictionary containing manager metrics
        """
        self._update_activity()
        
        return {
            "user_context": self.user_context.to_dict(),
            "manager_id": id(self),
            "is_active": self._is_active,
            "metrics": self._metrics.to_dict(),
            "connections": {
                "total": len(self._connections),
                "connection_ids": list(self._connection_ids)
            },
            "recovery_queue_size": len(self._message_recovery_queue),
            "error_count": self._connection_error_count,
            "last_error": self._last_error_time.isoformat() if self._last_error_time else None
        }


class WebSocketManagerFactory:
    """
    Factory for creating isolated WebSocket manager instances per user connection.
    
    This factory ensures complete user isolation by creating separate manager instances
    for each user context. It enforces resource limits, handles cleanup, and provides
    comprehensive monitoring for security and performance.
    
    SECURITY FEATURES:
    - Per-connection isolation keys (not just per-user)
    - Resource limit enforcement (max managers per user)
    - Automatic cleanup of expired managers
    - Thread-safe factory operations
    - Comprehensive security metrics and monitoring
    """
    
    def __init__(self, max_managers_per_user: int = 5, connection_timeout_seconds: int = 1800):
        """
        Initialize the WebSocket manager factory.
        
        Args:
            max_managers_per_user: Maximum number of managers per user (default: 5)
            connection_timeout_seconds: Timeout for idle connections (default: 30 minutes)
        """
        self._active_managers: Dict[str, IsolatedWebSocketManager] = {}
        self._user_manager_count: Dict[str, int] = {}
        self._manager_creation_time: Dict[str, datetime] = {}
        self._factory_lock = RLock()  # Use RLock for thread safety
        
        # Configuration
        self.max_managers_per_user = max_managers_per_user
        self.connection_timeout_seconds = connection_timeout_seconds
        
        # Metrics
        self._factory_metrics = FactoryMetrics()
        
        # Background cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        # Defer background cleanup start to avoid event loop issues in tests
        self._cleanup_started = False
        
        logger.info(
            f"WebSocketManagerFactory initialized - "
            f"max_managers_per_user: {max_managers_per_user}, "
            f"connection_timeout: {connection_timeout_seconds}s"
        )
    
    def _generate_isolation_key(self, user_context: UserExecutionContext) -> str:
        """
        Generate a unique isolation key for a user context.
        
        The isolation key ensures that each connection gets its own manager instance,
        providing the strongest possible isolation.
        
        Args:
            user_context: User execution context
            
        Returns:
            Unique isolation key
        """
        # Use connection-specific isolation (stronger than per-user)
        if user_context.websocket_connection_id:
            return f"{user_context.user_id}:{user_context.websocket_connection_id}"
        else:
            # Fallback to request-based isolation
            return f"{user_context.user_id}:{user_context.request_id}"
    
    def create_manager(self, user_context: UserExecutionContext) -> IsolatedWebSocketManager:
        """
        Create an isolated WebSocket manager for a user context.
        
        Args:
            user_context: User execution context for the manager
            
        Returns:
            New isolated WebSocket manager instance
            
        Raises:
            ValueError: If user_context is invalid
            RuntimeError: If resource limits are exceeded
        """
        if not isinstance(user_context, UserExecutionContext):
            raise ValueError("user_context must be a UserExecutionContext instance")
        
        isolation_key = self._generate_isolation_key(user_context)
        user_id = user_context.user_id
        
        # Start background cleanup if not already started
        if not self._cleanup_started:
            self._start_background_cleanup()
        
        with self._factory_lock:
            # Check if manager already exists
            if isolation_key in self._active_managers:
                existing_manager = self._active_managers[isolation_key]
                if existing_manager._is_active:
                    logger.info(f"Returning existing manager for isolation key: {isolation_key}")
                    return existing_manager
                else:
                    # Clean up inactive manager
                    self._cleanup_manager_internal(isolation_key)
            
            # Check resource limits
            current_count = self._user_manager_count.get(user_id, 0)
            if current_count >= self.max_managers_per_user:
                self._factory_metrics.resource_limit_hits += 1
                logger.warning(
                    f"Resource limit exceeded for user {user_id[:8]}... "
                    f"({current_count}/{self.max_managers_per_user} managers)"
                )
                raise RuntimeError(
                    f"User {user_id} has reached the maximum number of WebSocket managers "
                    f"({self.max_managers_per_user}). Please close existing connections first."
                )
            
            # Create new isolated manager
            manager = IsolatedWebSocketManager(user_context)
            
            # Register manager
            self._active_managers[isolation_key] = manager
            self._user_manager_count[user_id] = current_count + 1
            self._manager_creation_time[isolation_key] = datetime.utcnow()
            
            # Update metrics
            self._factory_metrics.managers_created += 1
            self._factory_metrics.managers_active = len(self._active_managers)
            self._factory_metrics.users_with_active_managers = len(
                [count for count in self._user_manager_count.values() if count > 0]
            )
            
            logger.info(
                f"Created isolated WebSocket manager for user {user_id[:8]}... "
                f"(isolation_key: {isolation_key}, manager_id: {id(manager)})"
            )
            
            return manager
    
    def get_manager(self, isolation_key: str) -> Optional[IsolatedWebSocketManager]:
        """
        Get an existing manager by isolation key.
        
        Args:
            isolation_key: Isolation key for the manager
            
        Returns:
            Manager instance if found and active, None otherwise
        """
        with self._factory_lock:
            manager = self._active_managers.get(isolation_key)
            if manager and manager._is_active:
                return manager
            elif manager:
                # Clean up inactive manager
                self._cleanup_manager_internal(isolation_key)
            return None
    
    async def cleanup_manager(self, isolation_key: str) -> bool:
        """
        Clean up a specific manager by isolation key.
        
        Args:
            isolation_key: Isolation key for the manager to clean up
            
        Returns:
            True if manager was cleaned up, False if not found
        """
        with self._factory_lock:
            manager = self._active_managers.get(isolation_key)
            if not manager:
                return False
            
            # Clean up manager connections
            try:
                await manager.cleanup_all_connections()
            except Exception as e:
                logger.error(f"Error during manager cleanup: {e}")
            
            # Remove from tracking
            self._cleanup_manager_internal(isolation_key)
            
            logger.info(f"Cleaned up manager with isolation key: {isolation_key}")
            return True
    
    def _cleanup_manager_internal(self, isolation_key: str) -> None:
        """
        Internal cleanup of manager tracking (called with lock held).
        
        Args:
            isolation_key: Isolation key for the manager
        """
        if isolation_key not in self._active_managers:
            return
        
        manager = self._active_managers[isolation_key]
        user_id = manager.user_context.user_id
        
        # Remove from active managers
        del self._active_managers[isolation_key]
        
        # Update user count
        if user_id in self._user_manager_count:
            self._user_manager_count[user_id] -= 1
            if self._user_manager_count[user_id] <= 0:
                del self._user_manager_count[user_id]
        
        # Remove creation time
        self._manager_creation_time.pop(isolation_key, None)
        
        # Update metrics
        self._factory_metrics.managers_cleaned_up += 1
        self._factory_metrics.managers_active = len(self._active_managers)
        self._factory_metrics.users_with_active_managers = len(
            [count for count in self._user_manager_count.values() if count > 0]
        )
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive factory statistics.
        
        Returns:
            Dictionary containing factory metrics and status
        """
        with self._factory_lock:
            # Calculate average manager lifetime
            if self._factory_metrics.managers_cleaned_up > 0:
                total_lifetime = sum(
                    (datetime.utcnow() - created).total_seconds()
                    for created in self._manager_creation_time.values()
                )
                active_count = len(self._manager_creation_time)
                if active_count > 0:
                    avg_lifetime = total_lifetime / (self._factory_metrics.managers_cleaned_up + active_count)
                    self._factory_metrics.average_manager_lifetime_seconds = avg_lifetime
            
            return {
                "factory_metrics": self._factory_metrics.to_dict(),
                "configuration": {
                    "max_managers_per_user": self.max_managers_per_user,
                    "connection_timeout_seconds": self.connection_timeout_seconds
                },
                "current_state": {
                    "active_managers": len(self._active_managers),
                    "users_with_managers": len(self._user_manager_count),
                    "isolation_keys": list(self._active_managers.keys())
                },
                "user_distribution": dict(self._user_manager_count),
                "oldest_manager_age_seconds": (
                    min(
                        (datetime.utcnow() - created).total_seconds()
                        for created in self._manager_creation_time.values()
                    ) if self._manager_creation_time else 0
                )
            }
    
    def enforce_resource_limits(self, user_id: str) -> bool:
        """
        Check and enforce resource limits for a specific user.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user is within limits, False if limits exceeded
        """
        with self._factory_lock:
            current_count = self._user_manager_count.get(user_id, 0)
            return current_count < self.max_managers_per_user
    
    async def _background_cleanup(self) -> None:
        """Background task to cleanup expired managers."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._cleanup_expired_managers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background cleanup error: {e}")
    
    async def _cleanup_expired_managers(self) -> None:
        """Clean up managers that have been idle for too long."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.connection_timeout_seconds)
        expired_keys = []
        
        with self._factory_lock:
            for key, created_time in self._manager_creation_time.items():
                manager = self._active_managers.get(key)
                if manager and manager._metrics.last_activity and manager._metrics.last_activity < cutoff_time:
                    expired_keys.append(key)
                elif created_time < cutoff_time and (not manager or not manager._is_active):
                    expired_keys.append(key)
        
        # Clean up expired managers
        for key in expired_keys:
            try:
                await self.cleanup_manager(key)
                logger.info(f"Auto-cleaned expired manager: {key}")
            except Exception as e:
                logger.error(f"Failed to cleanup expired manager {key}: {e}")
        
        if expired_keys:
            logger.info(f"Background cleanup completed: {len(expired_keys)} managers cleaned")
    
    def _start_background_cleanup(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_started:
            return
            
        try:
            if not self._cleanup_task or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._background_cleanup())
                self._cleanup_started = True
        except RuntimeError:
            # No event loop running - will start later when needed
            pass
    
    async def shutdown(self) -> None:
        """Shutdown the factory and clean up all managers."""
        logger.info("Shutting down WebSocketManagerFactory...")
        
        # Cancel background cleanup
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clean up all active managers
        with self._factory_lock:
            isolation_keys = list(self._active_managers.keys())
        
        for key in isolation_keys:
            try:
                await self.cleanup_manager(key)
            except Exception as e:
                logger.error(f"Error cleaning up manager {key} during shutdown: {e}")
        
        logger.info("WebSocketManagerFactory shutdown completed")


# Global factory instance
_factory_instance: Optional[WebSocketManagerFactory] = None
_factory_lock = RLock()


def get_websocket_manager_factory() -> WebSocketManagerFactory:
    """
    Get the global WebSocket manager factory instance.
    
    Returns:
        WebSocket manager factory instance
    """
    global _factory_instance
    with _factory_lock:
        if _factory_instance is None:
            _factory_instance = WebSocketManagerFactory()
        return _factory_instance


def create_websocket_manager(user_context: UserExecutionContext) -> IsolatedWebSocketManager:
    """
    Create an isolated WebSocket manager for a user context.
    
    This is the main factory function that applications should use to create
    WebSocket managers with proper user isolation.
    
    Args:
        user_context: User execution context for the manager
        
    Returns:
        Isolated WebSocket manager instance
        
    Raises:
        ValueError: If user_context is invalid
        RuntimeError: If resource limits are exceeded
    """
    factory = get_websocket_manager_factory()
    return factory.create_manager(user_context)


__all__ = [
    "WebSocketManagerFactory",
    "IsolatedWebSocketManager", 
    "ConnectionLifecycleManager",
    "FactoryMetrics",
    "ManagerMetrics",
    "get_websocket_manager_factory",
    "create_websocket_manager"
]