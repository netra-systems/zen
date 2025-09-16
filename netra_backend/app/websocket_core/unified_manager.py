"""Unified WebSocket Manager - SSOT for WebSocket connection management.

This module is the single source of truth for WebSocket connection management.
Refactored to use extracted modules for validation, message processing, and user context handling.
"""

import asyncio
import json
import time
import weakref
from enum import Enum
from typing import Dict, Optional, Set, Any, List, Union
from dataclasses import dataclass
from datetime import datetime, timezone

from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import (
    UserID, ThreadID, ConnectionID, WebSocketID, RequestID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id
)

# Import extracted modules
from netra_backend.app.websocket_core.connection_validator import (
    WebSocketConnectionValidator, ConnectionValidationResult, ConnectionLimitCheckResult
)
from netra_backend.app.websocket_core.message_validator import (
    WebSocketMessageValidator, MessageValidationResult, MessageDeliveryResult
)
from netra_backend.app.websocket_core.user_context_handler import (
    WebSocketUserContextHandler, UserIsolationResult, UserIsolationViolation
)

# Import shared types and functions
from netra_backend.app.websocket_core.types import (
    WebSocketConnection,
    WebSocketManagerMode,
    serialize_message_safely as _serialize_message_safely,
    _get_enum_key_representation
)

# Import SSOT MessageQueue
from netra_backend.app.websocket_core.message_queue import (
    get_message_queue_registry,
    MessageQueue,
    MessagePriority
)

logger = get_logger(__name__)

# Connection limits enforcement
MAX_CONNECTIONS_PER_USER = 10


class RegistryCompat:
    """Compatibility registry for legacy tests with circular reference prevention."""

    def __init__(self, manager):
        # Use weakref to prevent circular reference manager <-> registry
        self._manager_ref = weakref.ref(manager)

    @property
    def manager(self):
        """Get manager from weak reference, preventing circular reference memory leaks."""
        manager = self._manager_ref()
        if manager is None:
            raise RuntimeError("WebSocket manager has been garbage collected")
        return manager

    async def register_connection(self, user_id: str, connection_info):
        """Register a connection for test compatibility."""
        # Convert ConnectionInfo to WebSocketConnection format for the unified manager
        thread_id = getattr(connection_info, 'thread_id', None)
        websocket_conn = WebSocketConnection(
            connection_id=connection_info.connection_id,
            user_id=user_id,
            websocket=connection_info.websocket,
            connected_at=connection_info.connected_at,
            thread_id=thread_id,
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


class _UnifiedWebSocketManagerImplementation:
    """Unified WebSocket connection manager - SSOT with enhanced thread safety.

    Refactored to use extracted modules for:
    - Connection validation (connection_validator.py)
    - Message validation and processing (message_validator.py)
    - User context and isolation management (user_context_handler.py)
    """

    def __init__(self, mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED,
                 user_context: Optional[Any] = None, config: Optional[Dict[str, Any]] = None,
                 _ssot_authorization_token: Optional[str] = None):
        """Initialize UnifiedWebSocketManager with extracted modules."""

        self.mode = mode
        self.user_context = user_context
        self.config = config or {}

        # Initialize extracted module handlers
        self._connection_validator = WebSocketConnectionValidator()
        self._message_validator = WebSocketMessageValidator()
        self._user_context_handler = WebSocketUserContextHandler(user_context)

        # Core connection management
        self._connections: Dict[str, WebSocketConnection] = {}
        self._user_connections: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

        # Message queue integration
        self._message_queue_registry = get_message_queue_registry()
        self._connection_message_queues: Dict[str, MessageQueue] = {}

        # Compatibility for legacy tests
        self.active_connections: Dict[str, List] = {}

        # Background task monitoring
        self._background_tasks: Dict[str, asyncio.Task] = {}
        self._monitoring_enabled = True
        self._monitoring_lock = asyncio.Lock()
        self._shutdown_requested = False

        # Initialize mode-specific features
        if mode == WebSocketManagerMode.ISOLATED:
            self._initialize_isolated_mode(user_context)
        else:
            self._initialize_unified_mode()

        # Create compatibility registry
        self.registry = RegistryCompat(self)

        logger.info(f"WebSocket manager initialized in {mode.value} mode")

    def _initialize_unified_mode(self):
        """Initialize unified mode with full feature set."""
        self._error_recovery_enabled = True
        self._task_failures: Dict[str, int] = {}
        self._task_last_failure: Dict[str, datetime] = {}
        self._task_registry: Dict[str, Dict[str, Any]] = {}
        self._last_health_check = datetime.now(timezone.utc)
        self._health_check_failures = 0

        logger.debug("WebSocket manager initialized in unified mode")

    def _initialize_isolated_mode(self, user_context):
        """Initialize isolated mode for user-specific operation."""
        self._connection_ids: Set[str] = set()

        logger.debug(f"WebSocket manager initialized in isolated mode for user {getattr(user_context, 'user_id', 'unknown')}")

    async def add_connection(self, connection: WebSocketConnection) -> None:
        """Add a new WebSocket connection with thread safety and validation."""
        connection_start_time = time.time()

        # Log connection attempt
        connection_context = self._connection_validator.create_connection_context_log(
            connection=connection,
            existing_connections_count=len(self._connections),
            user_existing_connections=len(self._user_connections.get(connection.user_id, set())),
            has_queued_messages=connection.user_id in self._message_validator._message_recovery_queue,
            manager_mode=self.mode.value,
            stage="connection_addition_start"
        )

        logger.info(f"GOLDEN PATH CONNECTION ADD: Adding connection {connection.connection_id} for user {connection.user_id[:8] if connection.user_id else 'unknown'}...")
        logger.info(f"CONNECTION ADD CONTEXT: {json.dumps(connection_context, indent=2)}")

        # Validate connection
        validation_result = self._connection_validator.validate_connection_basic(connection)
        if not validation_result.is_valid:
            self._connection_validator.log_validation_failure(validation_result)
            raise ValueError(validation_result.error_message)

        # Check connection limits
        current_user_connections = len(self._user_connections.get(connection.user_id, set()))
        limit_check = self._connection_validator.check_connection_limits(connection, current_user_connections)
        if not limit_check.within_limits:
            raise ValueError(f"User {connection.user_id} exceeded maximum connections per user limit ({limit_check.max_allowed}). Current: {limit_check.current_connections}")

        # Get user-specific lock for thread safety
        user_lock = await self._connection_validator.get_user_connection_lock(connection.user_id)

        async with user_lock:
            async with self._lock:
                # Generate isolation token
                isolation_token = self._connection_validator.generate_isolation_token(connection)

                # Validate token uniqueness and fix collisions if needed
                isolation_token = self._connection_validator.validate_isolation_token_uniqueness(
                    connection, isolation_token,
                    self._user_context_handler._event_isolation_tokens,
                    self._connections
                )

                # Register isolation token
                self._user_context_handler.register_isolation_token(connection.connection_id, isolation_token)

                # Create message queue for connection
                message_queue = self._message_queue_registry.create_message_queue(
                    connection_id=connection.connection_id,
                    user_id=connection.user_id,
                    max_size=1000
                )
                self._connection_message_queues[connection.connection_id] = message_queue
                message_queue.set_message_processor(self._process_queued_message)

                # Store connection
                self._connections[connection.connection_id] = connection
                if connection.user_id not in self._user_connections:
                    self._user_connections[connection.user_id] = set()
                self._user_connections[connection.user_id].add(connection.connection_id)

                # Update compatibility mapping
                if connection.user_id not in self.active_connections:
                    self.active_connections[connection.user_id] = []
                conn_info = type('ConnectionInfo', (), {
                    'websocket': connection.websocket,
                    'user_id': connection.user_id,
                    'connection_id': connection.connection_id
                })()
                self.active_connections[connection.user_id].append(conn_info)

        # Process queued messages
        await self._message_validator.process_queued_messages(
            connection.user_id, self.send_to_user
        )

        # Log successful connection
        connection_duration = time.time() - connection_start_time
        self._connection_validator.log_connection_success(
            connection=connection,
            total_connections=len(self._connections),
            user_total_connections=len(self._user_connections[connection.user_id]),
            connection_duration=connection_duration,
            active_users=len(self._user_connections),
            manager_mode=self.mode.value
        )

    async def _process_queued_message(self, queued_message):
        """Process a message from the SSOT MessageQueue"""
        from netra_backend.app.websocket_core.message_queue import QueuedMessage

        if isinstance(queued_message, QueuedMessage):
            await self.send_to_user(
                user_id=queued_message.user_id,
                message=queued_message.message_data
            )
        else:
            # Handle legacy message format
            user_id = queued_message.get('user_id')
            message_data = queued_message.get('message', queued_message)
            await self.send_to_user(user_id=user_id, message=message_data)

    async def remove_connection(self, connection_id: Union[str, ConnectionID]) -> None:
        """Remove a WebSocket connection with thread safety and cleanup."""
        validated_connection_id = str(connection_id)

        connection = self._connections.get(validated_connection_id)
        if not connection:
            logger.debug(f"Connection {validated_connection_id} not found for removal")
            return

        user_lock = await self._connection_validator.get_user_connection_lock(connection.user_id)

        async with user_lock:
            async with self._lock:
                # Remove from connections
                if validated_connection_id in self._connections:
                    del self._connections[validated_connection_id]

                # Remove from user connections
                if connection.user_id in self._user_connections:
                    self._user_connections[connection.user_id].discard(validated_connection_id)
                    if not self._user_connections[connection.user_id]:
                        del self._user_connections[connection.user_id]

                # Cleanup isolation token
                self._user_context_handler.unregister_isolation_token(validated_connection_id)

                # Cleanup message queue
                if validated_connection_id in self._connection_message_queues:
                    del self._connection_message_queues[validated_connection_id]

                # Update compatibility mapping
                if connection.user_id in self.active_connections:
                    self.active_connections[connection.user_id] = [
                        conn for conn in self.active_connections[connection.user_id]
                        if getattr(conn, 'connection_id', None) != validated_connection_id
                    ]
                    if not self.active_connections[connection.user_id]:
                        del self.active_connections[connection.user_id]

        logger.debug(f"Removed connection {validated_connection_id} for user {connection.user_id}")

    async def send_to_user(self, user_id: Union[str, UserID], message: Dict[str, Any]) -> None:
        """Send a message to all connections for a user with validation."""
        # Validate message and prevent contamination
        validation_result = self._message_validator.validate_message_for_user(user_id, message)
        if not validation_result.is_valid:
            logger.error(f"Message validation failed for user {validation_result.user_id}: {validation_result.error_message}")
            return

        # Use sanitized message if contamination was detected
        final_message = validation_result.message
        validated_user_id = validation_result.user_id

        # Get user connections
        user_lock = await self._connection_validator.get_user_connection_lock(validated_user_id)

        async with user_lock:
            connection_ids = self.get_user_connections(validated_user_id)

            if not connection_ids:
                # Handle case where no connections exist
                delivery_context = self._message_validator.validate_delivery_context(
                    validated_user_id, final_message, connection_ids
                )

                if delivery_context['log_level'] == 'critical':
                    logger.critical(f"CRITICAL ERROR: No WebSocket connections found for user {validated_user_id}")
                else:
                    logger.debug(f"No connections for user {validated_user_id} during {delivery_context['description']}")

                # Store for recovery
                await self._message_validator.store_failed_message(
                    validated_user_id, final_message, "no_connections"
                )
                return

            # Send to all connections
            failed_connections = []
            successful_sends = 0

            for conn_id in connection_ids:
                connection = self.get_connection(conn_id)
                if connection and connection.websocket:
                    try:
                        safe_message = self._message_validator.create_safe_message(final_message)
                        await connection.websocket.send_json(safe_message)
                        successful_sends += 1
                        logger.debug(f"Sent message to connection {conn_id}")
                    except Exception as e:
                        logger.critical(f"WEBSOCKET SEND FAILURE: Failed to send to connection {conn_id}: {e}")
                        failed_connections.append((conn_id, str(e)))
                else:
                    logger.critical(f"INVALID CONNECTION: Connection {conn_id} has no valid WebSocket")
                    failed_connections.append((conn_id, "invalid_websocket"))

            # Handle delivery results
            delivery_result = self._message_validator.create_message_delivery_result(
                successful_sends, failed_connections, len(connection_ids),
                validated_user_id, final_message.get('type', 'unknown')
            )

            if failed_connections:
                self._message_validator.log_delivery_failure(delivery_result)

                # Store message for recovery if all failed
                if successful_sends == 0:
                    await self._message_validator.store_failed_message(
                        validated_user_id, final_message, "all_connections_failed"
                    )

                # Schedule cleanup of failed connections
                asyncio.create_task(self._cleanup_failed_connections(failed_connections))

    async def _cleanup_failed_connections(self, failed_connections: List[tuple]) -> None:
        """Cleanup failed connections in background to avoid deadlocks."""
        for failed_conn_id, error in failed_connections:
            try:
                await self.remove_connection(failed_conn_id)
                logger.info(f"Removed failed connection {failed_conn_id} due to: {error}")
            except Exception as e:
                logger.critical(f"CLEANUP FAILURE: Failed to remove connection {failed_conn_id}: {e}")

    def get_connection(self, connection_id: Union[str, ConnectionID]) -> Optional[WebSocketConnection]:
        """Get a specific connection."""
        return self._connections.get(str(connection_id))

    def get_user_connections(self, user_id: Union[str, UserID]) -> Set[str]:
        """Get all connections for a user."""
        return self._user_connections.get(str(user_id), set()).copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            'total_connections': len(self._connections),
            'active_users': len(self._user_connections),
            'mode': self.mode.value,
            'contamination_stats': self._message_validator.get_contamination_stats(),
            'recovery_queue_stats': self._message_validator.get_recovery_queue_stats(),
            'user_context_info': self._user_context_handler.get_user_context_info()
        }

    async def shutdown(self):
        """Shutdown the WebSocket manager."""
        async with self._lock:
            self._shutdown_requested = True

            # Close all connections
            for connection in list(self._connections.values()):
                try:
                    if connection.websocket:
                        await connection.websocket.close()
                except Exception as e:
                    logger.error(f"Error closing connection {connection.connection_id}: {e}")

            # Clear all data structures
            self._connections.clear()
            self._user_connections.clear()
            self._connection_message_queues.clear()
            self.active_connections.clear()

            # Cancel background tasks
            for task in self._background_tasks.values():
                if not task.done():
                    task.cancel()

            logger.info("WebSocket manager shutdown complete")

    # Compatibility methods for existing code
    def is_connection_active(self, user_id: Union[str, UserID]) -> bool:
        """Check if user has active connections."""
        return len(self.get_user_connections(user_id)) > 0

    async def emit_agent_event(self, user_id: Union[str, UserID], event_type: str, data: Dict[str, Any]) -> None:
        """Emit an agent event to a user."""
        # Process business event
        processed_event = self._message_validator.process_business_event(event_type, data)
        if processed_event:
            await self.send_to_user(user_id, processed_event)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected users."""
        for user_id in list(self._user_connections.keys()):
            try:
                await self.send_to_user(user_id, message)
            except Exception as e:
                logger.error(f"Failed to broadcast to user {user_id}: {e}")

    # Additional compatibility aliases
    async def connect_user(self, user_id: str, websocket: Any, connection_id: str = None, thread_id: str = None) -> str:
        """Connect a user (compatibility method)."""
        if not connection_id:
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
            id_manager = UnifiedIDManager()
            connection_id = id_manager.generate_id(IDType.CONNECTION)

        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=websocket,
            connected_at=datetime.now(timezone.utc),
            thread_id=thread_id
        )

        await self.add_connection(connection)
        return connection_id

    async def disconnect_user(self, user_id: str, websocket: Any = None, code: int = 1000, reason: str = "Normal closure") -> None:
        """Disconnect a user (compatibility method)."""
        connection_ids = self.get_user_connections(user_id)
        for conn_id in connection_ids:
            await self.remove_connection(conn_id)


# Create factory function for external access
def get_websocket_manager(user_context=None, mode=WebSocketManagerMode.UNIFIED, **kwargs):
    """Factory function to create WebSocket manager instances."""
    return _UnifiedWebSocketManagerImplementation(mode=mode, user_context=user_context, **kwargs)


# Export implementation for compatibility
UnifiedWebSocketManager = _UnifiedWebSocketManagerImplementation