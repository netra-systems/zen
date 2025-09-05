"""Unified WebSocket Manager - SSOT for WebSocket connection management.

This module is the single source of truth for WebSocket connection management.
"""

import asyncio
from typing import Dict, Optional, Set, Any
from dataclasses import dataclass
from datetime import datetime

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection."""
    connection_id: str
    user_id: str
    websocket: Any
    connected_at: datetime
    metadata: Dict[str, Any] = None


class RegistryCompat:
    """Compatibility registry for legacy tests."""
    
    def __init__(self, manager):
        self.manager = manager
    
    async def register_connection(self, user_id: str, connection_info):
        """Register a connection for test compatibility."""
        # Convert ConnectionInfo to WebSocketConnection format for the unified manager
        websocket_conn = WebSocketConnection(
            connection_id=connection_info.connection_id,
            user_id=user_id,
            websocket=connection_info.websocket,
            connected_at=connection_info.connected_at,
            metadata={"connection_info": connection_info}
        )
        await self.manager.add_connection(websocket_conn)
        # Store connection info for tests that expect it
        if not hasattr(self.manager, '_connection_infos'):
            self.manager._connection_infos = {}
        self.manager._connection_infos[connection_info.connection_id] = connection_info
    
    def get_user_connections(self, user_id: str):
        """Get user connections for test compatibility."""
        if hasattr(self.manager, '_connection_infos') and user_id in self.manager._user_connections:
            conn_ids = self.manager._user_connections[user_id]
            return [self.manager._connection_infos.get(conn_id) for conn_id in conn_ids if conn_id in self.manager._connection_infos]
        return []


class UnifiedWebSocketManager:
    """Unified WebSocket connection manager - SSOT with enhanced thread safety.
    
    ENHANCED: Eliminates race conditions by providing connection-level isolation:
    - Per-user connection locks prevent race conditions during concurrent operations
    - Thread-safe connection management with user-specific isolation
    - Connection state validation prevents silent failures
    """
    
    def __init__(self):
        self._connections: Dict[str, WebSocketConnection] = {}
        self._user_connections: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        
        # RACE CONDITION FIX: Add per-user connection locks
        self._user_connection_locks: Dict[str, asyncio.Lock] = {}
        self._connection_lock_creation_lock = asyncio.Lock()
        
        # Add compatibility registry for legacy tests
        self.registry = RegistryCompat(self)
        
        # Add compatibility for legacy tests expecting connection_manager
        self._connection_manager = self
        self.connection_manager = self
        self.active_connections = {}  # Compatibility mapping
        self.connection_registry = {}  # Registry for connection objects
        
        # Enhanced error handling and recovery system
        self._message_recovery_queue: Dict[str, List[Dict]] = {}  # user_id -> [messages]
        self._connection_error_count: Dict[str, int] = {}  # user_id -> error_count
        self._last_error_time: Dict[str, datetime] = {}  # user_id -> last_error_timestamp
        self._error_recovery_enabled = True
        
        # Background task monitoring system
        self._background_tasks: Dict[str, asyncio.Task] = {}  # task_name -> task
        self._task_failures: Dict[str, int] = {}  # task_name -> failure_count
        self._task_last_failure: Dict[str, datetime] = {}  # task_name -> last_failure_time
        self._monitoring_enabled = True
        self._monitoring_lock = asyncio.Lock()  # Synchronization for monitoring state changes
        
        # Task registry for recovery and restart capabilities
        self._task_registry: Dict[str, Dict[str, Any]] = {}  # task_name -> {func, args, kwargs, meta}
        self._shutdown_requested = False  # Track intentional shutdown vs error-based disable
        self._last_health_check = datetime.utcnow()
        self._health_check_failures = 0
        
        logger.info("UnifiedWebSocketManager initialized with connection-level thread safety and enhanced error handling")
    
    async def _get_user_connection_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create user-specific connection lock for thread safety.
        
        Args:
            user_id: User identifier for connection lock isolation
            
        Returns:
            User-specific asyncio Lock for connection operations
        """
        if user_id not in self._user_connection_locks:
            async with self._connection_lock_creation_lock:
                # Double-check locking pattern
                if user_id not in self._user_connection_locks:
                    self._user_connection_locks[user_id] = asyncio.Lock()
                    logger.debug(f"Created user-specific connection lock for user: {user_id}")
        return self._user_connection_locks[user_id]
    
    async def add_connection(self, connection: WebSocketConnection) -> None:
        """Add a new WebSocket connection with thread safety."""
        # Use user-specific lock for connection operations
        user_lock = await self._get_user_connection_lock(connection.user_id)
        
        async with user_lock:
            async with self._lock:
                self._connections[connection.connection_id] = connection
                if connection.user_id not in self._user_connections:
                    self._user_connections[connection.user_id] = set()
                self._user_connections[connection.user_id].add(connection.connection_id)
                
                # Update compatibility mapping for legacy tests
                if connection.user_id not in self.active_connections:
                    self.active_connections[connection.user_id] = []
                # Create a simple connection info object for compatibility
                conn_info = type('ConnectionInfo', (), {
                    'websocket': connection.websocket,
                    'user_id': connection.user_id,
                    'connection_id': connection.connection_id
                })()
                self.active_connections[connection.user_id].append(conn_info)
                
                logger.info(f"Added connection {connection.connection_id} for user {connection.user_id} (thread-safe)")
                
                # CRITICAL FIX: Process any queued messages for this user after connection established
                # This prevents race condition where messages are sent before connection is ready
                if connection.user_id in self._message_recovery_queue:
                    queued_messages = self._message_recovery_queue.get(connection.user_id, [])
                    if queued_messages:
                        logger.info(f"Processing {len(queued_messages)} queued messages for user {connection.user_id}")
                        # Process outside the lock to prevent deadlock
                        asyncio.create_task(self._process_queued_messages(connection.user_id))
    
    async def remove_connection(self, connection_id: str) -> None:
        """Remove a WebSocket connection with thread safety."""
        # First get the connection to determine user_id
        connection = self._connections.get(connection_id)
        if not connection:
            logger.debug(f"Connection {connection_id} not found for removal")
            return
        
        # Use user-specific lock for connection operations
        user_lock = await self._get_user_connection_lock(connection.user_id)
        
        async with user_lock:
            async with self._lock:
                if connection_id in self._connections:
                    connection = self._connections[connection_id]
                    del self._connections[connection_id]
                    if connection.user_id in self._user_connections:
                        self._user_connections[connection.user_id].discard(connection_id)
                        if not self._user_connections[connection.user_id]:
                            del self._user_connections[connection.user_id]
                    
                    # Update compatibility mapping
                    if connection.user_id in self.active_connections:
                        self.active_connections[connection.user_id] = [
                            c for c in self.active_connections[connection.user_id]
                            if c.connection_id != connection_id
                        ]
                        if not self.active_connections[connection.user_id]:
                            del self.active_connections[connection.user_id]
                    
                    logger.info(f"Removed connection {connection_id} (thread-safe)")
    
    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """Get a specific connection."""
        return self._connections.get(connection_id)
    
    def get_user_connections(self, user_id: str) -> Set[str]:
        """Get all connections for a user."""
        return self._user_connections.get(user_id, set()).copy()
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> None:
        """Send a message to all connections for a user with thread safety and loud error handling."""
        # Use user-specific lock to prevent race conditions during message sending
        user_lock = await self._get_user_connection_lock(user_id)
        
        async with user_lock:
            connection_ids = self.get_user_connections(user_id)
            if not connection_ids:
                # LOUD ERROR: No connections available for user
                logger.critical(
                    f"CRITICAL ERROR: No WebSocket connections found for user {user_id}. "
                    f"User will not receive message: {message.get('type', 'unknown')}"
                )
                # Store message for potential recovery
                await self._store_failed_message(user_id, message, "no_connections")
                return
            
            failed_connections = []
            successful_sends = 0
            
            for conn_id in connection_ids:
                connection = self.get_connection(conn_id)
                if connection and connection.websocket:
                    try:
                        await connection.websocket.send_json(message)
                        logger.debug(f"Sent message to connection {conn_id} (thread-safe)")
                        successful_sends += 1
                    except Exception as e:
                        # ENHANCED ERROR: More detailed logging for WebSocket send failures
                        logger.critical(
                            f"WEBSOCKET SEND FAILURE: Failed to send {message.get('type', 'unknown')} "
                            f"to connection {conn_id} for user {user_id}: {e}. "
                            f"Connection state: {self._get_connection_diagnostics(connection)}"
                        )
                        failed_connections.append((conn_id, str(e)))
                else:
                    # LOUD ERROR: Connection exists but websocket is None/invalid
                    logger.critical(
                        f"INVALID CONNECTION: Connection {conn_id} for user {user_id} "
                        f"has no valid WebSocket. Connection: {connection}"
                    )
                    failed_connections.append((conn_id, "invalid_websocket"))
            
            # If all connections failed, this is critical
            if successful_sends == 0:
                logger.critical(
                    f"COMPLETE MESSAGE DELIVERY FAILURE: All {len(connection_ids)} connections "
                    f"failed for user {user_id}. Message type: {message.get('type', 'unknown')}. "
                    f"Failed connections: {[f'{conn_id}: {error}' for conn_id, error in failed_connections]}"
                )
                # Store message for recovery
                await self._store_failed_message(user_id, message, "all_connections_failed")
            elif failed_connections:
                # Partial failure - log warning
                logger.warning(
                    f"PARTIAL MESSAGE DELIVERY: {successful_sends}/{len(connection_ids)} "
                    f"connections succeeded for user {user_id}. "
                    f"Failed: {[f'{conn_id}: {error}' for conn_id, error in failed_connections]}"
                )
            
            # Remove failed connections outside the send loop to avoid race conditions
            for failed_conn_id, error in failed_connections:
                try:
                    await self.remove_connection(failed_conn_id)
                    logger.info(f"Removed failed connection {failed_conn_id} due to: {error}")
                except Exception as e:
                    # LOUD ERROR: Failed to clean up failed connection
                    logger.critical(
                        f"CLEANUP FAILURE: Failed to remove failed connection {failed_conn_id} "
                        f"for user {user_id}: {e}. This may cause connection leaks."
                    )
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to a thread (compatibility method).
        Routes to send_to_user using thread_id as user_id.
        """
        try:
            await self.send_to_user(thread_id, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send to thread {thread_id}: {e}")
            return False
    
    async def emit_critical_event(self, user_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit a critical event to a specific user with guaranteed delivery tracking.
        This is the main interface for sending WebSocket events.
        
        CRITICAL FIX: Adds retry logic for staging/production environments to handle
        race conditions during connection establishment.
        
        Args:
            user_id: Target user ID
            event_type: Event type (e.g., 'agent_started', 'tool_executing')
            data: Event payload
        """
        # Validate critical event parameters
        if not user_id or not user_id.strip():
            logger.critical(f"INVALID USER_ID: Cannot emit {event_type} to empty user_id")
            raise ValueError(f"user_id cannot be empty for critical event {event_type}")
        
        if not event_type or not event_type.strip():
            logger.critical(f"INVALID EVENT_TYPE: Cannot emit empty event_type to user {user_id}")
            raise ValueError(f"event_type cannot be empty for user {user_id}")
        
        # CRITICAL FIX: Add retry logic for staging/production
        from shared.isolated_environment import get_env
        environment = get_env().get("ENVIRONMENT", "development").lower()
        
        # Retry configuration based on environment
        max_retries = 1  # Default for development
        retry_delay = 0.5  # seconds
        
        if environment in ["staging", "production"]:
            max_retries = 3  # More retries for cloud environments
            retry_delay = 1.0  # Longer delay for Cloud Run
        
        # Try with retries
        for attempt in range(max_retries):
            # Check connection health before sending critical events
            if self.is_connection_active(user_id):
                # Connection exists, try to send
                message = {
                    "type": event_type,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat(),
                    "critical": True,
                    "attempt": attempt + 1 if attempt > 0 else None
                }
                
                try:
                    await self.send_to_user(user_id, message)
                    # Success! Return immediately
                    return
                except Exception as e:
                    logger.error(f"Failed to send critical event {event_type} to user {user_id} on attempt {attempt + 1}: {e}")
                    # Continue to retry
            
            # No connection yet, wait before retry (except on last attempt)
            if attempt < max_retries - 1:
                logger.warning(
                    f"No active connection for user {user_id} on attempt {attempt + 1}/{max_retries}. "
                    f"Waiting {retry_delay}s before retry..."
                )
                await asyncio.sleep(retry_delay)
        
        # All retries failed
        logger.critical(
            f"CONNECTION HEALTH CHECK FAILED: No active connections for user {user_id} "
            f"after {max_retries} attempts when trying to emit critical event {event_type}. "
            f"User will not receive this critical update."
        )
        
        # Store for recovery instead of silently failing
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "critical": True
        }
        await self._store_failed_message(user_id, message, "no_active_connections_after_retry")
        # Don't return silently - emit to user notification system
        await self._emit_connection_error_notification(user_id, event_type)
        
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "critical": True
        }
        
        try:
            await self.send_to_user(user_id, message)
            logger.debug(f"Successfully emitted critical event {event_type} to user {user_id}")
        except Exception as e:
            # CRITICAL: Failure to emit critical events must be highly visible
            logger.critical(
                f"CRITICAL EVENT EMISSION FAILURE: Failed to emit {event_type} "
                f"to user {user_id}: {e}. This breaks the user experience."
            )
            # Store for recovery
            await self._store_failed_message(user_id, message, f"emission_error: {e}")
            # Notify user of the error
            await self._emit_system_error_notification(user_id, event_type, str(e))
            raise
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connections."""
        for connection in list(self._connections.values()):
            try:
                await connection.websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {connection.connection_id}: {e}")
                await self.remove_connection(connection.connection_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self._connections),
            "unique_users": len(self._user_connections),
            "connections_by_user": {
                user_id: len(conns) 
                for user_id, conns in self._user_connections.items()
            }
        }
    
    def is_connection_active(self, user_id: str) -> bool:
        """
        Check if user has active WebSocket connections.
        CRITICAL for authentication event validation.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user has at least one active connection, False otherwise
        """
        connection_ids = self.get_user_connections(user_id)
        if not connection_ids:
            return False
        
        # Check if at least one connection is still valid
        for conn_id in connection_ids:
            connection = self.get_connection(conn_id)
            if connection and connection.websocket:
                # TODO: Add more sophisticated health check if websocket has state
                return True
        
        return False
    
    def get_connection_health(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed connection health information for a user.
        
        Args:
            user_id: User ID to check
            
        Returns:
            Dictionary with connection health details
        """
        connection_ids = self.get_user_connections(user_id)
        total_connections = len(connection_ids)
        active_connections = 0
        connection_details = []
        
        for conn_id in connection_ids:
            connection = self.get_connection(conn_id)
            if connection:
                is_active = connection.websocket is not None
                if is_active:
                    active_connections += 1
                    
                connection_details.append({
                    'connection_id': conn_id,
                    'active': is_active,
                    'connected_at': connection.connected_at.isoformat(),
                    'metadata': connection.metadata or {}
                })
        
        return {
            'user_id': user_id,
            'total_connections': total_connections,
            'active_connections': active_connections,
            'has_active_connections': active_connections > 0,
            'connections': connection_details
        }
    
    async def connect_user(self, user_id: str, websocket: Any) -> Any:
        """Legacy compatibility method for connecting a user."""
        import uuid
        from datetime import datetime
        connection_id = str(uuid.uuid4())
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=websocket,
            connected_at=datetime.now()
        )
        await self.add_connection(connection)
        
        # Return a ConnectionInfo-like object for compatibility
        conn_info = type('ConnectionInfo', (), {
            'user_id': user_id,
            'connection_id': connection_id,
            'websocket': websocket
        })()
        
        # Store in connection registry for compatibility
        self.connection_registry[connection_id] = conn_info
        
        return conn_info
    
    async def disconnect_user(self, user_id: str, websocket: Any, code: int = 1000, reason: str = "Normal closure") -> None:
        """Legacy compatibility method for disconnecting a user."""
        # Find the connection by user_id and websocket
        connection_ids = self.get_user_connections(user_id)
        for conn_id in connection_ids:
            connection = self.get_connection(conn_id)
            if connection and connection.websocket == websocket:
                await self.remove_connection(conn_id)
                # Clean up connection registry
                if conn_id in self.connection_registry:
                    del self.connection_registry[conn_id]
                logger.info(f"Disconnected user {user_id} with code {code}: {reason}")
                return
        logger.warning(f"Connection not found for user {user_id} during disconnect")
    
    async def find_connection(self, user_id: str, websocket: Any) -> Optional[Any]:
        """Find a connection for the given user_id and websocket."""
        connection_ids = self.get_user_connections(user_id)
        for conn_id in connection_ids:
            connection = self.get_connection(conn_id)
            if connection and connection.websocket == websocket:
                # Return a ConnectionInfo-like object for compatibility
                return type('ConnectionInfo', (), {
                    'user_id': user_id,
                    'connection_id': conn_id,
                    'websocket': websocket
                })()
        return None
    
    async def handle_message(self, user_id: str, websocket: Any, message: Dict[str, Any]) -> bool:
        """Handle a message from a user (compatibility method)."""
        try:
            # For compatibility, just log the message handling
            logger.debug(f"Handling message from {user_id}: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to handle message from {user_id}: {e}")
            return False
    
    async def connect_to_job(self, websocket: Any, job_id: str) -> Any:
        """Connect to a job (room-like functionality for compatibility)."""
        import uuid
        from datetime import datetime
        
        # Validate job_id
        if not isinstance(job_id, str):
            logger.warning(f"Invalid job_id type: {type(job_id)}, converting to string")
            job_id = f"job_{id(websocket)}"
        
        # Check for invalid job_id patterns (object representations)
        if "<" in job_id or "object at" in job_id or "WebSocket" in job_id:
            logger.warning(f"Invalid job_id detected: {job_id}, generating new one")
            job_id = f"job_{uuid.uuid4().hex[:8]}"
        
        # Create a user_id based on job_id and websocket
        user_id = f"job_{job_id}_{id(websocket)}"
        
        # Create connection
        connection_id = str(uuid.uuid4())
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=websocket,
            connected_at=datetime.now(),
            metadata={"job_id": job_id, "connection_type": "job"}
        )
        await self.add_connection(connection)
        
        # Initialize core and room_manager for compatibility
        if not hasattr(self, 'core'):
            self.core = type('Core', (), {})()
            self.core.room_manager = type('RoomManager', (), {})()
            self.core.room_manager.rooms = {}
            self.core.room_manager.room_connections = {}
        
        # Add to room
        if job_id not in self.core.room_manager.rooms:
            self.core.room_manager.rooms[job_id] = set()
            self.core.room_manager.room_connections[job_id] = set()
        
        self.core.room_manager.rooms[job_id].add(connection_id)
        self.core.room_manager.room_connections[job_id].add(user_id)
        
        # Add get_stats method to room_manager
        def get_stats():
            return {
                "room_connections": {
                    room_id: list(connections) for room_id, connections in self.core.room_manager.room_connections.items()
                }
            }
        
        def get_room_connections(room_id: str):
            return list(self.core.room_manager.room_connections.get(room_id, set()))
        
        self.core.room_manager.get_stats = get_stats
        self.core.room_manager.get_room_connections = get_room_connections
        
        # Return a ConnectionInfo-like object for compatibility
        conn_info = type('ConnectionInfo', (), {
            'user_id': user_id,
            'connection_id': connection_id,
            'websocket': websocket,
            'job_id': job_id
        })()
        
        # Store in connection registry for compatibility
        self.connection_registry[connection_id] = conn_info
        
        return conn_info
    
    async def disconnect_from_job(self, job_id: str, websocket: Any) -> None:
        """Disconnect from a job."""
        user_id = f"job_{job_id}_{id(websocket)}"
        await self.disconnect_user(user_id, websocket)
    
    # ============================================================================
    # ENHANCED ERROR HANDLING AND RECOVERY METHODS
    # ============================================================================
    
    def _get_connection_diagnostics(self, connection: WebSocketConnection) -> Dict[str, Any]:
        """Get detailed diagnostics for a connection."""
        try:
            websocket = connection.websocket
            return {
                'has_websocket': websocket is not None,
                'websocket_type': type(websocket).__name__ if websocket else None,
                'connection_age_seconds': (datetime.utcnow() - connection.connected_at).total_seconds(),
                'metadata_present': bool(connection.metadata),
                # Add more WebSocket-specific diagnostics if available
                'websocket_state': getattr(websocket, 'client_state', 'unknown') if websocket else None,
            }
        except Exception as e:
            return {'diagnostics_error': str(e)}
    
    async def _store_failed_message(self, user_id: str, message: Dict[str, Any], 
                                   failure_reason: str) -> None:
        """Store failed message for potential recovery."""
        if not self._error_recovery_enabled:
            return
        
        try:
            if user_id not in self._message_recovery_queue:
                self._message_recovery_queue[user_id] = []
            
            # Add failure metadata
            failed_message = {
                **message,
                'failure_reason': failure_reason,
                'failed_at': datetime.utcnow().isoformat(),
                'recovery_attempts': 0
            }
            
            self._message_recovery_queue[user_id].append(failed_message)
            
            # Increment error count
            self._connection_error_count[user_id] = self._connection_error_count.get(user_id, 0) + 1
            self._last_error_time[user_id] = datetime.utcnow()
            
            # Limit queue size to prevent memory issues
            max_queue_size = 50
            if len(self._message_recovery_queue[user_id]) > max_queue_size:
                self._message_recovery_queue[user_id] = self._message_recovery_queue[user_id][-max_queue_size:]
            
            logger.info(f"Stored failed message for user {user_id}: {failure_reason}")
            
        except Exception as e:
            logger.error(f"Failed to store failed message for recovery: {e}")
    
    async def _emit_connection_error_notification(self, user_id: str, failed_event_type: str) -> None:
        """Emit a user-visible error notification about connection issues."""
        try:
            error_message = {
                "type": "connection_error",
                "data": {
                    "message": f"Connection issue detected. Your {failed_event_type} update may be delayed.",
                    "event_type": failed_event_type,
                    "user_friendly_message": "We're having trouble connecting to you. Please refresh your browser if you don't see updates soon.",
                    "severity": "warning",
                    "action_required": "Consider refreshing the page if issues persist",
                    "support_code": f"CONN_ERR_{user_id[:8]}_{failed_event_type}"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "critical": True
            }
            
            # Try to send the error notification (even though connection might be bad)
            # This might reach the user if there are other active connections
            connection_ids = self.get_user_connections(user_id)
            for conn_id in connection_ids:
                connection = self.get_connection(conn_id)
                if connection and connection.websocket:
                    try:
                        await connection.websocket.send_json(error_message)
                        logger.info(f"Sent connection error notification to user {user_id}")
                        return
                    except Exception:
                        continue  # Try next connection
            
            # If we can't send via WebSocket, log for external monitoring
            logger.critical(
                f"USER_NOTIFICATION_FAILED: Could not notify user {user_id} about connection error. "
                f"User may experience blank screen or missing updates. Support code: {error_message['data']['support_code']}"
            )
            
        except Exception as e:
            logger.error(f"Failed to emit connection error notification: {e}")
    
    async def _emit_system_error_notification(self, user_id: str, failed_event_type: str, 
                                            error_details: str) -> None:
        """Emit a user-visible system error notification."""
        try:
            error_message = {
                "type": "system_error",
                "data": {
                    "message": f"A system error occurred while processing your {failed_event_type}.",
                    "user_friendly_message": "Something went wrong on our end. Our team has been notified. Please try again in a few moments.",
                    "event_type": failed_event_type,
                    "severity": "error",
                    "action_required": "Try refreshing the page or contact support if the problem persists",
                    "support_code": f"SYS_ERR_{user_id[:8]}_{failed_event_type}_{datetime.utcnow().strftime('%H%M%S')}"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "critical": True
            }
            
            # Attempt to send error notification
            await self.send_to_user(user_id, error_message)
            
        except Exception as e:
            logger.critical(
                f"SYSTEM_ERROR_NOTIFICATION_FAILED: Could not notify user {user_id} "
                f"about system error in {failed_event_type}: {e}. "
                f"User may be unaware of the failure. Error details: {error_details}"
            )
    
    async def attempt_message_recovery(self, user_id: str) -> int:
        """Attempt to recover failed messages for a user when they reconnect."""
        if not self._error_recovery_enabled or user_id not in self._message_recovery_queue:
            return 0
        
        failed_messages = self._message_recovery_queue[user_id]
        recovered_count = 0
        
        # Only attempt recovery if user has active connections now
        if not self.is_connection_active(user_id):
            logger.debug(f"Skipping message recovery for {user_id} - no active connections")
            return 0
        
        for message in failed_messages[:]:  # Copy list to avoid modification during iteration
            try:
                # Increment recovery attempts
                message['recovery_attempts'] = message.get('recovery_attempts', 0) + 1
                
                # Skip messages with too many recovery attempts
                if message['recovery_attempts'] > 3:
                    logger.warning(f"Abandoning message recovery after 3 attempts: {message.get('type', 'unknown')}")
                    failed_messages.remove(message)
                    continue
                
                # Attempt to send the message
                recovery_message = {k: v for k, v in message.items() 
                                  if k not in ['failure_reason', 'failed_at', 'recovery_attempts']}
                recovery_message['recovered'] = True
                recovery_message['original_failure'] = message['failure_reason']
                
                await self.send_to_user(user_id, recovery_message)
                failed_messages.remove(message)
                recovered_count += 1
                
                logger.info(f"Recovered message for user {user_id}: {message.get('type', 'unknown')}")
                
            except Exception as e:
                logger.warning(f"Message recovery attempt failed for user {user_id}: {e}")
        
        if recovered_count > 0:
            logger.info(f"Message recovery completed for user {user_id}: {recovered_count} messages recovered")
        
        return recovered_count
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics for monitoring."""
        total_users_with_errors = len(self._connection_error_count)
        total_error_count = sum(self._connection_error_count.values())
        total_queued_messages = sum(len(queue) for queue in self._message_recovery_queue.values())
        
        # Recent errors (last 5 minutes)
        recent_errors = 0
        cutoff_time = datetime.utcnow()
        for error_time in self._last_error_time.values():
            if (cutoff_time - error_time).total_seconds() < 300:  # 5 minutes
                recent_errors += 1
        
        return {
            'total_users_with_errors': total_users_with_errors,
            'total_error_count': total_error_count,
            'total_queued_messages': total_queued_messages,
            'recent_errors_5min': recent_errors,
            'error_recovery_enabled': self._error_recovery_enabled,
            'users_with_queued_messages': len(self._message_recovery_queue),
            'error_details': {
                user_id: {
                    'error_count': self._connection_error_count.get(user_id, 0),
                    'last_error': self._last_error_time.get(user_id, '').isoformat() if self._last_error_time.get(user_id) else None,
                    'queued_messages': len(self._message_recovery_queue.get(user_id, []))
                }
                for user_id in set(list(self._connection_error_count.keys()) + list(self._message_recovery_queue.keys()))
            }
        }
    
    async def cleanup_error_data(self, older_than_hours: int = 24) -> Dict[str, int]:
        """Clean up old error data to prevent memory leaks."""
        cutoff_time = datetime.utcnow()
        
        # Clean up old error times
        old_error_users = []
        for user_id, error_time in self._last_error_time.items():
            if (cutoff_time - error_time).total_seconds() > (older_than_hours * 3600):
                old_error_users.append(user_id)
        
        for user_id in old_error_users:
            del self._last_error_time[user_id]
            if user_id in self._connection_error_count:
                del self._connection_error_count[user_id]
        
        # Clean up old recovery queues for users with no recent activity
        old_queue_users = []
        for user_id, messages in self._message_recovery_queue.items():
            # Remove old messages from queue
            current_messages = []
            for message in messages:
                failed_at_str = message.get('failed_at', '')
                try:
                    failed_at = datetime.fromisoformat(failed_at_str.replace('Z', '+00:00'))
                    if (cutoff_time - failed_at).total_seconds() <= (older_than_hours * 3600):
                        current_messages.append(message)
                except (ValueError, AttributeError):
                    # Keep message if we can't parse the date
                    current_messages.append(message)
            
            if current_messages:
                self._message_recovery_queue[user_id] = current_messages
            else:
                old_queue_users.append(user_id)
        
        for user_id in old_queue_users:
            del self._message_recovery_queue[user_id]
        
        return {
            'cleaned_error_users': len(old_error_users),
            'cleaned_queue_users': len(old_queue_users),
            'remaining_error_users': len(self._connection_error_count),
            'remaining_queue_users': len(self._message_recovery_queue)
        }
    
    # ============================================================================
    # BACKGROUND TASK MONITORING SYSTEM
    # ============================================================================
    
    async def start_monitored_background_task(self, task_name: str, coro_func, *args, **kwargs) -> str:
        """Start a background task with monitoring and automatic restart."""
        async with self._monitoring_lock:
            if not self._monitoring_enabled:
                logger.warning("Background task monitoring is disabled")
                return ""
            
            # Store task definition in registry for potential recovery
            self._task_registry[task_name] = {
                'func': coro_func,
                'args': args,
                'kwargs': kwargs,
                'created_at': datetime.utcnow(),
                'restart_count': 0
            }
            
            # Stop existing task if it exists
            if task_name in self._background_tasks:
                await self.stop_background_task(task_name)
            
            # Create monitored task
            task = asyncio.create_task(
                self._run_monitored_task(task_name, coro_func, *args, **kwargs)
            )
            
            self._background_tasks[task_name] = task
            logger.info(f"Started monitored background task: {task_name}")
            return task_name
    
    async def _run_monitored_task(self, task_name: str, coro_func, *args, **kwargs):
        """Run a task with monitoring and error handling."""
        failure_count = 0
        max_failures = 3
        base_delay = 1.0
        max_delay = 60.0
        
        while self._monitoring_enabled:
            try:
                if asyncio.iscoroutinefunction(coro_func):
                    await coro_func(*args, **kwargs)
                else:
                    # If it's a regular function, run it
                    result = coro_func(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        await result
                
                # Reset failure count on successful execution
                failure_count = 0
                if task_name in self._task_failures:
                    del self._task_failures[task_name]
                if task_name in self._task_last_failure:
                    del self._task_last_failure[task_name]
                
                logger.debug(f"Background task {task_name} completed successfully")
                break  # Task completed successfully
                
            except asyncio.CancelledError:
                logger.info(f"Background task {task_name} was cancelled")
                break
                
            except Exception as e:
                failure_count += 1
                self._task_failures[task_name] = failure_count
                self._task_last_failure[task_name] = datetime.utcnow()
                
                # LOUD ERROR: Background task failures are critical for system health
                logger.critical(
                    f"BACKGROUND TASK FAILURE: {task_name} failed (attempt {failure_count}/{max_failures}): {e}. "
                    f"Error type: {type(e).__name__}. "
                    f"This may affect system functionality."
                )
                
                if failure_count >= max_failures:
                    logger.critical(
                        f"BACKGROUND TASK ABANDONED: {task_name} failed {max_failures} times. "
                        f"Task will not be restarted automatically. Manual intervention required."
                    )
                    # Notify system administrators of critical task failure
                    await self._notify_admin_of_task_failure(task_name, e, failure_count)
                    break
                
                # Calculate exponential backoff delay
                delay = min(base_delay * (2 ** (failure_count - 1)), max_delay)
                logger.warning(f"Restarting {task_name} in {delay:.1f}s after failure {failure_count}")
                
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    logger.info(f"Background task {task_name} restart was cancelled")
                    break
    
    async def stop_background_task(self, task_name: str) -> bool:
        """Stop a background task by name."""
        if task_name not in self._background_tasks:
            logger.warning(f"Background task {task_name} not found")
            return False
        
        task = self._background_tasks[task_name]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error while stopping background task {task_name}: {e}")
        
        del self._background_tasks[task_name]
        logger.info(f"Stopped background task: {task_name}")
        return True
    
    async def _notify_admin_of_task_failure(self, task_name: str, error: Exception, failure_count: int):
        """Notify system administrators of critical background task failure."""
        try:
            # This would integrate with alerting systems in production
            alert_message = {
                "type": "critical_task_failure",
                "task_name": task_name,
                "error": str(error),
                "error_type": type(error).__name__,
                "failure_count": failure_count,
                "timestamp": datetime.utcnow().isoformat(),
                "requires_manual_intervention": True,
                "impact": "System functionality may be degraded"
            }
            
            # Log at critical level for monitoring systems
            logger.critical(
                f"ADMIN ALERT REQUIRED: Background task {task_name} has failed permanently. "
                f"Alert: {alert_message}"
            )
            
            # TODO: Integrate with actual alerting systems:
            # - Send to PagerDuty/OpsGenie
            # - Email notification to on-call engineers
            # - Slack/Teams notification
            # - Create monitoring dashboard alert
            
        except Exception as e:
            logger.error(f"Failed to send admin notification for task failure: {e}")
    
    def get_background_task_status(self) -> Dict[str, Any]:
        """Get status of all background tasks."""
        task_status = {}
        
        for task_name, task in self._background_tasks.items():
            task_status[task_name] = {
                'running': not task.done(),
                'cancelled': task.cancelled(),
                'exception': str(task.exception()) if task.done() and task.exception() else None,
                'failure_count': self._task_failures.get(task_name, 0),
                'last_failure': self._task_last_failure.get(task_name, '').isoformat() if self._task_last_failure.get(task_name) else None
            }
        
        return {
            'monitoring_enabled': self._monitoring_enabled,
            'total_tasks': len(self._background_tasks),
            'running_tasks': len([t for t in self._background_tasks.values() if not t.done()]),
            'failed_tasks': len(self._task_failures),
            'tasks': task_status
        }
    
    async def _process_queued_messages(self, user_id: str) -> None:
        """Process queued messages for a user after connection established.
        
        This is called when a new connection is established to deliver
        any messages that were attempted while the user had no connections.
        """
        if user_id not in self._message_recovery_queue:
            return
        
        messages = self._message_recovery_queue.get(user_id, [])
        if not messages:
            return
        
        logger.info(f"Processing {len(messages)} queued messages for user {user_id}")
        
        # Clear the queue first to prevent re-processing
        self._message_recovery_queue[user_id] = []
        
        # Small delay to ensure connection is fully established
        await asyncio.sleep(0.1)
        
        # Send each queued message
        for msg in messages:
            try:
                # Remove recovery metadata before sending
                clean_msg = {k: v for k, v in msg.items() 
                           if k not in ['failure_reason', 'failed_at', 'recovery_attempts']}
                
                # Add a flag indicating this is a recovered message
                clean_msg['recovered'] = True
                
                await self.send_to_user(user_id, clean_msg)
                logger.debug(f"Successfully delivered queued message type '{clean_msg.get('type')}' to user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to deliver queued message to user {user_id}: {e}")
        
        logger.info(f"Completed processing queued messages for user {user_id}")
    
    async def health_check_background_tasks(self) -> Dict[str, Any]:
        """Perform health check on background tasks and restart failed ones."""
        health_report = {
            'healthy_tasks': 0,
            'unhealthy_tasks': 0,
            'restarted_tasks': [],
            'failed_restarts': []
        }
        
        for task_name, task in list(self._background_tasks.items()):
            if task.done() and not task.cancelled():
                # Task completed unexpectedly - try to restart
                logger.warning(f"Background task {task_name} completed unexpectedly - attempting restart")
                
                try:
                    # Remove the completed task
                    del self._background_tasks[task_name]
                    
                    # This would need the original function and args to restart
                    # For now, just mark as needing manual restart
                    health_report['unhealthy_tasks'] += 1
                    health_report['failed_restarts'].append({
                        'task_name': task_name,
                        'reason': 'Cannot restart - original function not stored'
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to restart background task {task_name}: {e}")
                    health_report['failed_restarts'].append({
                        'task_name': task_name,
                        'reason': str(e)
                    })
            else:
                health_report['healthy_tasks'] += 1
        
        return health_report
    
    async def shutdown_background_monitoring(self):
        """Shutdown all background tasks."""
        async with self._monitoring_lock:
            self._shutdown_requested = True
            self._monitoring_enabled = False
            
            # Cancel all tasks
            for task_name in list(self._background_tasks.keys()):
                await self.stop_background_task(task_name)
            
            logger.info("Background task monitoring shutdown complete")
    
    async def enable_background_monitoring(self, restart_previous_tasks: bool = True) -> Dict[str, Any]:
        """
        Re-enable background task monitoring with optional task recovery.
        
        CRITICAL FIX: Prevents permanent disable of monitoring system by providing
        a safe way to restart monitoring after shutdown or errors.
        
        Args:
            restart_previous_tasks: Whether to restart tasks that were registered before shutdown
            
        Returns:
            Dictionary with recovery status and counts
        """
        recovery_status = {
            'monitoring_enabled': False,
            'tasks_restarted': 0,
            'tasks_failed_restart': 0,
            'failed_tasks': [],
            'health_check_reset': False,
            'previous_state': {
                'was_shutdown': self._shutdown_requested,
                'had_failures': len(self._task_failures) > 0
            }
        }
        
        async with self._monitoring_lock:
            if self._monitoring_enabled:
                logger.info("Background monitoring is already enabled")
                recovery_status['monitoring_enabled'] = True
                return recovery_status
            
            # Reset monitoring state
            self._monitoring_enabled = True
            self._shutdown_requested = False
            self._health_check_failures = 0
            self._last_health_check = datetime.utcnow()
            recovery_status['health_check_reset'] = True
            
            logger.info("Background task monitoring re-enabled")
            recovery_status['monitoring_enabled'] = True
            
            # Optionally restart registered tasks
            if restart_previous_tasks and self._task_registry:
                logger.info(f"Attempting to restart {len(self._task_registry)} registered tasks")
                
                for task_name, task_config in list(self._task_registry.items()):
                    try:
                        # Increment restart count
                        task_config['restart_count'] = task_config.get('restart_count', 0) + 1
                        
                        # Don't restart tasks that have failed too many times
                        if task_config['restart_count'] > 5:
                            logger.warning(f"Skipping restart of {task_name} - too many restart attempts ({task_config['restart_count']})")
                            continue
                        
                        # Restart the task
                        restart_result = await self.start_monitored_background_task(
                            task_name,
                            task_config['func'],
                            *task_config['args'],
                            **task_config['kwargs']
                        )
                        
                        if restart_result:
                            recovery_status['tasks_restarted'] += 1
                            logger.info(f"Successfully restarted task: {task_name}")
                        else:
                            recovery_status['tasks_failed_restart'] += 1
                            recovery_status['failed_tasks'].append(task_name)
                            logger.error(f"Failed to restart task: {task_name}")
                        
                    except Exception as e:
                        recovery_status['tasks_failed_restart'] += 1
                        recovery_status['failed_tasks'].append(task_name)
                        logger.error(f"Exception while restarting task {task_name}: {e}")
            
            # Clear old failure data for a fresh start
            self._task_failures.clear()
            self._task_last_failure.clear()
            
            logger.info(
                f"Monitoring recovery complete: {recovery_status['tasks_restarted']} tasks restarted, "
                f"{recovery_status['tasks_failed_restart']} failed"
            )
            
        return recovery_status


# SECURITY FIX: Replace singleton with factory pattern
# Global instance removed to prevent multi-user data leakage
# Use create_websocket_manager(user_context) instead

def get_websocket_manager() -> UnifiedWebSocketManager:
    """
    DEPRECATED: Get the global WebSocket manager instance.
    
    WARNING: This function creates a non-isolated manager instance that can cause
    CRITICAL SECURITY VULNERABILITIES in multi-user environments. It should only
    be used for backward compatibility in legacy code that cannot be immediately
    migrated to the factory pattern.
    
    For new code, use:
    - create_websocket_manager(user_context) for isolated managers
    - WebSocketManagerFactory for advanced factory operations
    
    Returns:
        UnifiedWebSocketManager: A NEW instance (not singleton) for basic compatibility
    """
    from netra_backend.app.logging_config import central_logger
    import warnings
    
    logger = central_logger.get_logger(__name__)
    
    warnings.warn(
        "SECURITY WARNING: Using deprecated get_websocket_manager() function. "
        "This creates a non-isolated manager that can leak data between users. "
        "Migrate to create_websocket_manager(user_context) for proper isolation.",
        UserWarning,
        stacklevel=2
    )
    
    # Return a NEW instance each time to prevent shared state
    # This is still not ideal but safer than a true singleton
    return UnifiedWebSocketManager()