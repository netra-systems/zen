"""
WebSocket Manager Migration Adapter - Backward Compatibility Layer

This module provides a backward compatibility layer for the migration from singleton
WebSocket manager to the factory pattern. It maintains the existing API while 
internally using the new factory pattern for security.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable secure migration without breaking existing code
- Value Impact: Zero-downtime migration from vulnerable singleton to secure factory pattern
- Revenue Impact: Prevents catastrophic security breaches while maintaining system stability

CRITICAL SECURITY MIGRATION:
This adapter eliminates the singleton anti-pattern that was causing:
- Message cross-contamination between users
- Shared state corruption affecting all users
- Connection hijacking vulnerabilities
- Memory leak accumulation

The adapter provides:
1. Backward compatibility for existing get_websocket_manager() calls
2. Automatic UserExecutionContext creation for legacy usage
3. Migration warnings to track singleton usage
4. Gradual transition support

IMPORTANT: This is a transitional component. Once all code is migrated to use
the factory pattern directly, this adapter should be removed.
"""

import asyncio
import uuid
import warnings
from datetime import datetime
from typing import Dict, Optional, Any, Set
from contextlib import contextmanager
import weakref
import threading

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    IsolatedWebSocketManager,
    get_websocket_manager_factory
)
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# DEPRECATED WebSocketManagerAdapter removed for SSOT compliance - use WebSocketManagerFactory directly

# Keep the migration functions for backward compatibility
class _LegacyWebSocketManagerAdapter:
    """
    DEPRECATED: Migration adapter that delegates to WebSocketManagerFactory.
    
    This class is now just an alias for backward compatibility.
    All functionality delegates to the canonical WebSocketManagerFactory.
    
    DEPRECATION WARNING: This class will be removed in future versions.
    Use WebSocketManagerFactory directly instead.
    
    SSOT COMPLIANCE: This ensures only one canonical factory exists.
    """
    
    def __init__(self):
        """Initialize the migration adapter (DEPRECATED)."""
        warnings.warn(
            "WebSocketManagerAdapter is deprecated. Use WebSocketManagerFactory directly.",
            DeprecationWarning,
            stacklevel=2
        )
        self._factory = get_websocket_manager_factory()
        self._legacy_stats = {
            "singleton_calls": 0,
            "contexts_created": 0,
            "managers_created": 0,
            "warnings_issued": 1  # First warning already issued
        }
        
        logger.warning("WebSocketManagerAdapter is DEPRECATED. Use WebSocketManagerFactory instead.")
    
    # ============================================================================
    # DELEGATION METHODS (SSOT COMPLIANCE - Alias for WebSocketManagerFactory)
    # ============================================================================
    
    def create_isolated_manager(self, user_id: str, connection_id: str) -> IsolatedWebSocketManager:
        """Delegate to main factory (DEPRECATED)."""
        warnings.warn("Use WebSocketManagerFactory.create_isolated_manager instead", DeprecationWarning)
        return self._factory.create_isolated_manager(user_id, connection_id)
    
    def get_manager_by_user(self, user_id: str) -> Optional[IsolatedWebSocketManager]:
        """Delegate to main factory (DEPRECATED)."""
        warnings.warn("Use WebSocketManagerFactory.get_manager_by_user instead", DeprecationWarning)
        return self._factory.get_manager_by_user(user_id)
    
    def get_active_connections_count(self) -> int:
        """Delegate to main factory (DEPRECATED)."""
        warnings.warn("Use WebSocketManagerFactory.get_active_connections_count instead", DeprecationWarning)
        return self._factory.get_active_connections_count()
    
    def get_manager(self) -> IsolatedWebSocketManager:
        """Create a default manager for legacy usage (DEPRECATED)."""
        warnings.warn("get_manager() is deprecated. Use create_isolated_manager() instead", DeprecationWarning)
        # Create a default manager for legacy usage
        import uuid
        user_id = f"legacy_user_{uuid.uuid4().hex[:8]}"
        connection_id = f"legacy_conn_{uuid.uuid4().hex[:8]}"
        return self._factory.create_isolated_manager(user_id, connection_id)
    
    def _show_migration_warning(self, method_name: str, caller_info: str = "") -> None:
        """Show migration warning once per call site."""
        warning_key = f"{method_name}:{caller_info}"
        if warning_key not in self._usage_warnings_shown:
            self._usage_warnings_shown.add(warning_key)
            self._legacy_stats["warnings_issued"] += 1
            
            warning_msg = (
                f"MIGRATION WARNING: {method_name} is using legacy singleton pattern. "
                f"This will be deprecated. Please migrate to WebSocketManagerFactory. "
                f"Call site: {caller_info}"
            )
            
            logger.warning(warning_msg)
            warnings.warn(warning_msg, DeprecationWarning, stacklevel=3)
    
    def _create_default_user_context(self, connection_info: Optional[Dict] = None) -> UserExecutionContext:
        """
        Create a default UserExecutionContext for legacy usage.
        
        SECURITY NOTE: This creates a unique context per call, ensuring isolation
        even for legacy singleton usage.
        
        Args:
            connection_info: Optional connection information
            
        Returns:
            UserExecutionContext with generated unique identifiers
        """
        # Generate unique identifiers for this legacy context
        context_id = str(uuid.uuid4())
        
        # Extract user info from connection if available
        user_id = "legacy_user"
        connection_id = None
        
        if connection_info:
            user_id = connection_info.get("user_id", f"legacy_{context_id[:8]}")
            connection_id = connection_info.get("connection_id", f"conn_{context_id[:8]}")
        else:
            user_id = f"legacy_{context_id[:8]}"
            connection_id = f"conn_{context_id[:8]}"
        
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{context_id[:8]}",
            run_id=f"run_{context_id[:8]}",
            request_id=f"req_{context_id[:8]}",
            websocket_client_id=connection_id
        )
        
        self._legacy_stats["contexts_created"] += 1
        return context
    
    def _get_or_create_manager(self, context_key: str, user_context: UserExecutionContext) -> IsolatedWebSocketManager:
        """
        Get or create an isolated manager for a context key.
        
        Args:
            context_key: Unique key for the context
            user_context: User execution context
            
        Returns:
            Isolated WebSocket manager instance
        """
        with self._legacy_lock:
            if context_key in self._legacy_managers:
                manager = self._legacy_managers[context_key]
                if manager._is_active:
                    return manager
                else:
                    # Clean up inactive manager
                    del self._legacy_managers[context_key]
                    self._legacy_contexts.pop(context_key, None)
            
            # Create new isolated manager
            manager = self._factory.create_manager(user_context)
            self._legacy_managers[context_key] = manager
            self._legacy_contexts[context_key] = user_context
            self._legacy_stats["managers_created"] += 1
            
            logger.info(f"Created isolated manager for legacy context key: {context_key}")
            return manager
    
    # Backward compatibility methods - these maintain the old interface
    
    async def connect_user(self, user_id: str, websocket, connection_metadata: Optional[Dict] = None) -> str:
        """
        Connect a user using legacy interface.
        
        SECURITY: Creates isolated manager per user_id for security.
        """
        self._show_migration_warning("connect_user", f"user_id={user_id[:8]}...")
        self._legacy_stats["singleton_calls"] += 1
        
        # Create context for this connection
        connection_info = {
            "user_id": user_id,
            "connection_id": f"conn_{user_id}_{datetime.utcnow().timestamp()}"
        }
        if connection_metadata:
            connection_info.update(connection_metadata)
        
        user_context = self._create_default_user_context(connection_info)
        context_key = f"{user_id}:{user_context.websocket_connection_id}"
        
        # Get isolated manager for this user
        manager = self._get_or_create_manager(context_key, user_context)
        
        # Create WebSocket connection object
        connection = WebSocketConnection(
            connection_id=user_context.websocket_connection_id,
            user_id=user_id,
            websocket=websocket,
            connected_at=datetime.utcnow()
        )
        
        # Add to isolated manager
        await manager.add_connection(connection)
        
        logger.info(f"Legacy connect_user: {user_id[:8]}... -> isolated manager {id(manager)}")
        return user_context.websocket_connection_id
    
    async def disconnect_user(self, user_id: str, websocket, code: int = 1000, reason: str = "Normal closure") -> None:
        """
        Disconnect a user using legacy interface.
        """
        self._show_migration_warning("disconnect_user", f"user_id={user_id[:8]}...")
        self._legacy_stats["singleton_calls"] += 1
        
        with self._legacy_lock:
            # Find managers for this user
            user_managers = []
            for context_key, manager in self._legacy_managers.items():
                if manager.user_context.user_id == user_id:
                    user_managers.append((context_key, manager))
            
            # Disconnect from all user's managers
            for context_key, manager in user_managers:
                try:
                    # Find connection with matching websocket
                    for conn_id in manager.get_user_connections():
                        connection = manager.get_connection(conn_id)
                        if connection and connection.websocket == websocket:
                            await manager.remove_connection(conn_id)
                            logger.info(f"Legacy disconnect_user: removed connection {conn_id}")
                            break
                    
                    # Clean up manager if no connections remain
                    if not manager.get_user_connections():
                        await manager.cleanup_all_connections()
                        del self._legacy_managers[context_key]
                        self._legacy_contexts.pop(context_key, None)
                        logger.info(f"Cleaned up isolated manager for user {user_id[:8]}...")
                        
                except Exception as e:
                    logger.error(f"Error during legacy disconnect for user {user_id[:8]}...: {e}")
    
    def get_user_connections(self, user_id: str) -> Set[str]:
        """
        Get user connections using legacy interface.
        """
        self._show_migration_warning("get_user_connections", f"user_id={user_id[:8]}...")
        self._legacy_stats["singleton_calls"] += 1
        
        all_connections = set()
        with self._legacy_lock:
            for manager in self._legacy_managers.values():
                if manager.user_context.user_id == user_id:
                    all_connections.update(manager.get_user_connections())
        
        return all_connections
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> None:
        """
        Send message to user using legacy interface.
        
        SECURITY: Each user has isolated managers, so no cross-contamination possible.
        """
        self._show_migration_warning("send_to_user", f"user_id={user_id[:8]}...")
        self._legacy_stats["singleton_calls"] += 1
        
        sent_count = 0
        with self._legacy_lock:
            user_managers = [
                manager for manager in self._legacy_managers.values()
                if manager.user_context.user_id == user_id
            ]
        
        for manager in user_managers:
            try:
                await manager.send_to_user(message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send message via isolated manager for user {user_id[:8]}...: {e}")
        
        if sent_count == 0:
            logger.warning(f"No active isolated managers found for user {user_id[:8]}...")
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to specific connection using legacy interface.
        """
        self._show_migration_warning("send_to_connection", f"conn_id={connection_id[:8]}...")
        self._legacy_stats["singleton_calls"] += 1
        
        with self._legacy_lock:
            # Find manager containing this connection
            for manager in self._legacy_managers.values():
                connection = manager.get_connection(connection_id)
                if connection and connection.websocket:
                    try:
                        # CRITICAL FIX: Use safe serialization to handle WebSocketState enums and other complex objects
                        from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely
                        safe_message = _serialize_message_safely(message)
                        await connection.websocket.send_json(safe_message)
                        logger.debug(f"Sent message to connection {connection_id[:8]}... via isolated manager")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to send to connection {connection_id[:8]}...: {e}")
                        return False
        
        logger.warning(f"Connection {connection_id[:8]}... not found in any isolated manager")
        return False
    
    async def broadcast_to_all(self, message: Dict[str, Any], exclude_users: Optional[Set[str]] = None) -> None:
        """
        Broadcast to all users using legacy interface.
        
        SECURITY: Broadcasts to isolated managers, maintaining user isolation.
        """
        self._show_migration_warning("broadcast_to_all", "global_broadcast")
        self._legacy_stats["singleton_calls"] += 1
        
        if exclude_users is None:
            exclude_users = set()
        
        broadcast_count = 0
        with self._legacy_lock:
            for manager in self._legacy_managers.values():
                user_id = manager.user_context.user_id
                if user_id not in exclude_users:
                    try:
                        await manager.send_to_user(message)
                        broadcast_count += 1
                    except Exception as e:
                        logger.error(f"Failed to broadcast to user {user_id[:8]}...: {e}")
        
        logger.info(f"Legacy broadcast completed: {broadcast_count} users reached")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics using legacy interface.
        """
        self._show_migration_warning("get_stats", "global_stats")
        self._legacy_stats["singleton_calls"] += 1
        
        total_connections = 0
        active_users = set()
        
        with self._legacy_lock:
            for manager in self._legacy_managers.values():
                total_connections += len(manager.get_user_connections())
                active_users.add(manager.user_context.user_id)
        
        return {
            "migration_adapter_stats": self._legacy_stats.copy(),
            "active_connections": total_connections,
            "total_connections": total_connections,  # For backward compatibility
            "unique_users": len(active_users),
            "isolated_managers": len(self._legacy_managers),
            "contexts_managed": len(self._legacy_contexts),
            "uptime_seconds": 0,  # Not tracked in adapter
            "messages_sent": 0,   # Not tracked in adapter
            "messages_received": 0,  # Not tracked in adapter
            "errors_handled": 0,  # Not tracked in adapter
            "migration_status": {
                "is_legacy_adapter": True,
                "warnings_issued": self._legacy_stats["warnings_issued"],
                "unique_warning_sites": len(self._usage_warnings_shown),
                "recommended_action": "Migrate to WebSocketManagerFactory"
            }
        }
    
    def get_adapter_metrics(self) -> Dict[str, Any]:
        """
        Get migration adapter specific metrics.
        """
        with self._legacy_lock:
            active_managers = len([m for m in self._legacy_managers.values() if m._is_active])
            
            return {
                "legacy_usage_stats": self._legacy_stats.copy(),
                "active_isolated_managers": active_managers,
                "total_contexts_created": len(self._legacy_contexts),
                "warning_sites_detected": len(self._usage_warnings_shown),
                "migration_progress": {
                    "total_legacy_calls": self._legacy_stats["singleton_calls"],
                    "isolated_managers_in_use": active_managers,
                    "security_improvement": "100% - All legacy usage is now isolated"
                },
                "recommendations": [
                    "Replace get_websocket_manager() calls with WebSocketManagerFactory",
                    "Pass UserExecutionContext to all WebSocket operations", 
                    "Remove singleton usage to eliminate migration warnings",
                    "Review and update all files using legacy WebSocket patterns"
                ]
            }


# Global adapter instance (singleton for backward compatibility)
_adapter_instance: Optional[WebSocketManagerAdapter] = None
_adapter_lock = threading.RLock()


def get_legacy_websocket_manager() -> WebSocketManagerAdapter:
    """
    Get the legacy WebSocket manager adapter.
    
    This function maintains backward compatibility by providing the same interface
    as get_websocket_manager() while using secure factory pattern internally.
    
    Returns:
        WebSocketManagerAdapter instance
    """
    global _adapter_instance
    with _adapter_lock:
        if _adapter_instance is None:
            _adapter_instance = WebSocketManagerAdapter()
        return _adapter_instance


def migrate_singleton_usage(user_context: UserExecutionContext) -> IsolatedWebSocketManager:
    """
    Helper function to migrate from singleton to factory pattern.
    
    Use this function to migrate existing singleton usage:
    
    OLD:
    ```python
    ws_manager = get_websocket_manager()
    await ws_manager.send_to_user(user_id, message)
    ```
    
    NEW:
    ```python
    ws_manager = migrate_singleton_usage(user_context)
    await ws_manager.send_to_user(message)  # user_id from context
    ```
    
    Args:
        user_context: User execution context for isolation
        
    Returns:
        Isolated WebSocket manager instance
    """
    factory = get_websocket_manager_factory()
    return factory.create_manager(user_context)


__all__ = [
    "get_legacy_websocket_manager",
    "migrate_singleton_usage"
]

# DEPRECATED: WebSocketManagerAdapter removed for SSOT compliance
# Use WebSocketManagerFactory directly from websocket_manager_factory module