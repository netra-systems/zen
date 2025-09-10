"""
User-Scoped WebSocketEventRouter Factory - Complete User Isolation for Event Routing

Business Value Justification (BVJ):
- Segment: Platform/Core Infrastructure
- Business Goal: $500K+ ARR Protection through Event Routing Isolation
- Value Impact: Prevents singleton-based event routing sharing that causes cross-user event leakage
- Strategic Impact: Ensures secure per-user event routing with guaranteed connection isolation

This module provides the foundational factory pattern to replace the WebSocketEventRouter singleton
with per-user instances, preventing cross-user event routing that blocks chat functionality.

CRITICAL BUSINESS CONTEXT:
- Each user execution must get completely isolated event routing instances
- Shared event routing between users causes events to go to wrong users (security breach)
- Factory patterns ensure each user gets fresh, isolated routing component instances
- This factory enables EventRouter isolation critical for WebSocket event delivery security

SINGLETON VIOLATION RESOLUTION:
This factory directly addresses the EventRouter singleton violations identified in:
- Cross-user event routing causing events to reach wrong users
- Shared connection pools mixing user connections
- Event broadcasting reaching unintended recipients
- Connection state confusion between concurrent users

ARCHITECTURE COMPLIANCE:
@compliance CLAUDE.md - WebSocket events enable substantive chat interactions (Section 6)
@compliance SPEC/core.xml - Single Source of Truth event routing patterns
@compliance SPEC/type_safety.xml - Strongly typed event routing interfaces

Migration Phase: Phase 1 - Foundation Implementation (Parallel to Singleton)
GitHub Issue: https://github.com/netra-systems/netra-apex/issues/232
"""

import asyncio
import threading
import weakref
from typing import Any, Dict, Optional, Set, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.user_execution_context import UserExecutionContext
from netra_backend.app.services.websocket_event_router import (
    WebSocketEventRouter,
    ConnectionInfo,
    get_websocket_router
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

logger = central_logger.get_logger(__name__)


@dataclass
class UserEventRoutingRegistry:
    """
    Per-user event routing registry with complete connection isolation.
    
    This registry maintains all event routing state for a single user execution context,
    ensuring complete isolation from other users' routing states and connections.
    """
    user_context: UserExecutionContext
    router: WebSocketEventRouter
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    routing_count: int = field(default=0)
    last_access: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Initialize registry with user context validation."""
        if not isinstance(self.user_context, UserExecutionContext):
            raise ValueError("UserEventRoutingRegistry requires valid UserExecutionContext")
        
        logger.debug(
            f"UserEventRoutingRegistry created for user {self.user_context.user_id[:8]}... "
            f"(request: {self.user_context.request_id[:8]}...)"
        )
    
    def get_isolation_key(self) -> str:
        """Get unique isolation key for this user registry."""
        return self.user_context.get_scoped_key("event_router")
    
    def is_expired(self, max_age_seconds: int = 3600) -> bool:  # 1 hour default
        """Check if registry has exceeded maximum age."""
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > max_age_seconds
    
    def update_access_time(self):
        """Update last access time for this registry."""
        # Since this is a frozen dataclass, we need to use object.__setattr__
        object.__setattr__(self, 'last_access', datetime.now(timezone.utc))


class UserScopedWebSocketEventRouter:
    """
    User-scoped WebSocket event router providing complete isolation between user executions.
    
    This class replaces the singleton WebSocketEventRouter pattern with per-user instances,
    ensuring that each user's event routing and connections are completely isolated from other
    users, preventing cross-user event leakage and ensuring secure event delivery.
    
    Key Features:
    - Complete user isolation through UserExecutionContext
    - Per-user connection pools with independent lifecycles
    - Event routing isolated per user
    - Connection state management isolated per user
    - Thread-safe operations with user-scoped locking
    - Automatic cleanup to prevent memory leaks
    """
    
    def __init__(self, user_context: UserExecutionContext, websocket_manager: Optional[UnifiedWebSocketManager] = None):
        """
        Initialize user-scoped WebSocket event router.
        
        Args:
            user_context: UserExecutionContext for complete isolation
            websocket_manager: Optional WebSocket manager for actual routing
            
        Raises:
            ValueError: If user_context is invalid
        """
        if not isinstance(user_context, UserExecutionContext):
            raise ValueError("UserScopedWebSocketEventRouter requires valid UserExecutionContext")
        
        self.user_context = user_context
        self.registry = UserEventRoutingRegistry(
            user_context=user_context,
            router=WebSocketEventRouter(websocket_manager)
        )
        self._lock = asyncio.Lock()
        
        logger.info(
            f"UserScopedWebSocketEventRouter initialized for user {user_context.user_id[:8]}... "
            f"(isolation_key: {self.registry.get_isolation_key()})"
        )
    
    async def register_connection(self, connection_id: str, thread_id: Optional[str] = None) -> bool:
        """
        Register a WebSocket connection for this user.
        
        Args:
            connection_id: Unique connection identifier
            thread_id: Optional thread/conversation identifier
            
        Returns:
            bool: True if registration successful
        """
        async with self._lock:
            self.registry.update_access_time()
            
            # Ensure connection belongs to this user by validating user_id
            result = await self.registry.router.register_connection(
                user_id=self.user_context.user_id,
                connection_id=connection_id,
                thread_id=thread_id
            )
            
            if result:
                logger.debug(
                    f"Connection registered for user {self.user_context.user_id[:8]}...: "
                    f"{connection_id}"
                )
            else:
                logger.error(
                    f"🚨 CRITICAL: Failed to register connection {connection_id} "
                    f"for user {self.user_context.user_id[:8]}..."
                )
            
            return result
    
    async def unregister_connection(self, connection_id: str) -> bool:
        """
        Remove a connection from this user's pool.
        
        Args:
            connection_id: Connection identifier to remove
            
        Returns:
            bool: True if removal successful
        """
        async with self._lock:
            self.registry.update_access_time()
            
            result = await self.registry.router.unregister_connection(connection_id)
            
            if result:
                logger.debug(
                    f"Connection unregistered for user {self.user_context.user_id[:8]}...: "
                    f"{connection_id}"
                )
            
            return result
    
    async def route_event(self, connection_id: str, event: Dict[str, Any]) -> bool:
        """
        Route event to specific connection for this user.
        
        Args:
            connection_id: Specific connection to send to
            event: Event payload to send
            
        Returns:
            bool: True if event sent successfully
        """
        async with self._lock:
            self.registry.update_access_time()
            self.registry.routing_count += 1
            
            # Add user context to event for validation
            enriched_event = event.copy()
            enriched_event.update({
                'user_id': self.user_context.user_id,
                'request_id': self.user_context.request_id
            })
            
            result = await self.registry.router.route_event(
                user_id=self.user_context.user_id,
                connection_id=connection_id,
                event=enriched_event
            )
            
            if result:
                logger.debug(
                    f"Event routed for user {self.user_context.user_id[:8]}...: "
                    f"{event.get('type', 'unknown')} -> {connection_id}"
                )
            else:
                logger.warning(
                    f"Failed to route event for user {self.user_context.user_id[:8]}...: "
                    f"{event.get('type', 'unknown')} -> {connection_id}"
                )
            
            return result
    
    async def broadcast_to_user(self, event: Dict[str, Any]) -> int:
        """
        Broadcast event to all connections for this user.
        
        Args:
            event: Event payload
            
        Returns:
            int: Number of successful sends
        """
        async with self._lock:
            self.registry.update_access_time()
            self.registry.routing_count += 1
            
            # Add user context to event for validation
            enriched_event = event.copy()
            enriched_event.update({
                'user_id': self.user_context.user_id,
                'request_id': self.user_context.request_id
            })
            
            result = await self.registry.router.broadcast_to_user(
                user_id=self.user_context.user_id,
                event=enriched_event
            )
            
            logger.debug(
                f"Event broadcasted for user {self.user_context.user_id[:8]}...: "
                f"{event.get('type', 'unknown')} (sent to {result} connections)"
            )
            
            return result
    
    async def get_user_connections(self) -> List[str]:
        """
        Get all connection IDs for this user.
        
        Returns:
            List of connection IDs
        """
        async with self._lock:
            self.registry.update_access_time()
            return await self.registry.router.get_user_connections(self.user_context.user_id)
    
    async def cleanup_stale_connections(self) -> int:
        """
        Clean up inactive connections for this user.
        
        Returns:
            int: Number of connections cleaned up
        """
        async with self._lock:
            self.registry.update_access_time()
            return await self.registry.router.cleanup_stale_connections()
    
    async def get_router_stats(self) -> Dict[str, Any]:
        """
        Get router statistics for this user.
        
        Returns:
            Dictionary with user-specific router statistics
        """
        async with self._lock:
            self.registry.update_access_time()
            stats = await self.registry.router.get_stats()
            
            # Add user-specific metadata
            stats.update({
                "user_id_prefix": self.user_context.user_id[:8] + "...",
                "isolation_key": self.registry.get_isolation_key(),
                "registry_routing_count": self.registry.routing_count,
                "registry_created_at": self.registry.created_at.isoformat(),
                "registry_last_access": self.registry.last_access.isoformat(),
                "registry_age_seconds": (datetime.now(timezone.utc) - self.registry.created_at).total_seconds()
            })
            
            return stats
    
    def get_user_context(self) -> UserExecutionContext:
        """Get the user execution context for this router."""
        return self.user_context
    
    async def validate_user_access(self, connection_id: str) -> bool:
        """
        Validate that a connection belongs to this user.
        
        Args:
            connection_id: Connection ID to validate
            
        Returns:
            bool: True if connection belongs to this user
        """
        async with self._lock:
            connections = await self.get_user_connections()
            is_valid = connection_id in connections
            
            if not is_valid:
                logger.critical(
                    f"🚨 CRITICAL SECURITY: Connection {connection_id} does not belong to user "
                    f"{self.user_context.user_id[:8]}... - potential cross-user access attempt"
                )
            
            return is_valid


class WebSocketEventRouterFactory:
    """
    Factory for creating user-scoped WebSocketEventRouter instances.
    
    This factory manages the lifecycle of UserScopedWebSocketEventRouter instances,
    providing automatic cleanup and memory management to prevent resource leaks.
    """
    
    def __init__(self):
        """Initialize factory with user registry tracking."""
        self._user_routers: Dict[str, weakref.ReferenceType] = {}
        self._lock = threading.RLock()
        self._websocket_manager: Optional[UnifiedWebSocketManager] = None
        
        logger.info("WebSocketEventRouterFactory initialized")
    
    def set_websocket_manager(self, websocket_manager: UnifiedWebSocketManager):
        """
        Set the WebSocket manager for all future router instances.
        
        Args:
            websocket_manager: UnifiedWebSocketManager instance
        """
        with self._lock:
            self._websocket_manager = websocket_manager
            logger.info("WebSocketManager set for EventRouterFactory")
    
    def create_for_user(self, user_context: UserExecutionContext) -> UserScopedWebSocketEventRouter:
        """
        Create or get user-scoped WebSocket event router.
        
        Args:
            user_context: UserExecutionContext for isolation
            
        Returns:
            UserScopedWebSocketEventRouter for the user
        """
        with self._lock:
            isolation_key = user_context.get_scoped_key("event_router")
            
            # Check if we already have a router for this user context
            if isolation_key in self._user_routers:
                existing_ref = self._user_routers[isolation_key]
                existing_router = existing_ref()
                
                if existing_router is not None:
                    logger.debug(
                        f"Reusing existing EventRouter for user {user_context.user_id[:8]}..."
                    )
                    return existing_router
                else:
                    # Clean up dead reference
                    del self._user_routers[isolation_key]
            
            # Create new user-scoped router
            router = UserScopedWebSocketEventRouter(
                user_context=user_context,
                websocket_manager=self._websocket_manager
            )
            
            # Store weak reference for cleanup tracking
            self._user_routers[isolation_key] = weakref.ref(router)
            
            logger.info(
                f"Created new UserScopedWebSocketEventRouter for user {user_context.user_id[:8]}... "
                f"(total active: {len(self._user_routers)})"
            )
            
            return router
    
    async def cleanup_expired_routers(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up expired user routers.
        
        Args:
            max_age_seconds: Maximum age before cleanup (default: 1 hour)
            
        Returns:
            Number of routers cleaned up
        """
        with self._lock:
            expired_keys = []
            
            for isolation_key, router_ref in self._user_routers.items():
                router = router_ref()
                
                if router is None:
                    # Dead reference
                    expired_keys.append(isolation_key)
                elif router.registry.is_expired(max_age_seconds):
                    # Expired router - clean up connections
                    try:
                        await router.cleanup_stale_connections()
                    except Exception as e:
                        logger.warning(f"Error cleaning up expired router connections: {e}")
                    expired_keys.append(isolation_key)
            
            # Clean up expired references
            for key in expired_keys:
                del self._user_routers[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired event routers")
            
            return len(expired_keys)
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """
        Get factory statistics.
        
        Returns:
            Dictionary with factory statistics
        """
        with self._lock:
            active_count = 0
            total_connections = 0
            total_routings = 0
            
            for router_ref in self._user_routers.values():
                router = router_ref()
                if router is not None:
                    active_count += 1
                    total_routings += router.registry.routing_count
                    # Note: getting connection count would require async operation
            
            return {
                "active_routers": active_count,
                "total_tracked": len(self._user_routers),
                "total_routings": total_routings,
                "has_websocket_manager": self._websocket_manager is not None,
                "dead_references": len(self._user_routers) - active_count
            }
    
    def get_user_router_if_exists(self, user_context: UserExecutionContext) -> Optional[UserScopedWebSocketEventRouter]:
        """
        Get existing user router if it exists.
        
        Args:
            user_context: UserExecutionContext to look up
            
        Returns:
            UserScopedWebSocketEventRouter if exists, None otherwise
        """
        with self._lock:
            isolation_key = user_context.get_scoped_key("event_router")
            
            if isolation_key in self._user_routers:
                router_ref = self._user_routers[isolation_key]
                return router_ref()
            
            return None


# Global factory instance for creating user-scoped routers
_factory_instance: Optional[WebSocketEventRouterFactory] = None
_factory_lock = threading.RLock()


def get_event_router_factory() -> WebSocketEventRouterFactory:
    """
    Get the global WebSocketEventRouterFactory instance.
    
    Returns:
        WebSocketEventRouterFactory instance
    """
    global _factory_instance
    
    with _factory_lock:
        if _factory_instance is None:
            _factory_instance = WebSocketEventRouterFactory()
        
        return _factory_instance


def create_user_event_router(user_context: UserExecutionContext) -> UserScopedWebSocketEventRouter:
    """
    Create user-scoped WebSocket event router for the given context.
    
    Args:
        user_context: UserExecutionContext for isolation
        
    Returns:
        UserScopedWebSocketEventRouter instance
    """
    factory = get_event_router_factory()
    return factory.create_for_user(user_context)


async def route_user_event(event: Dict[str, Any],
                          user_context: UserExecutionContext,
                          connection_id: str) -> bool:
    """
    Convenience function to route an event for a specific user.
    
    Args:
        event: Event data to route
        user_context: UserExecutionContext for isolation
        connection_id: Connection ID to route to
        
    Returns:
        bool: True if event was routed successfully
    """
    router = create_user_event_router(user_context)
    return await router.route_event(connection_id, event)


async def broadcast_user_event(event: Dict[str, Any],
                              user_context: UserExecutionContext) -> int:
    """
    Convenience function to broadcast an event to all connections for a specific user.
    
    Args:
        event: Event data to broadcast
        user_context: UserExecutionContext for isolation
        
    Returns:
        int: Number of successful sends
    """
    router = create_user_event_router(user_context)
    return await router.broadcast_to_user(event)


# Backward Compatibility Bridge
def get_websocket_router_with_context(user_context: Optional[UserExecutionContext] = None,
                                     websocket_manager: Optional[UnifiedWebSocketManager] = None) -> Union[WebSocketEventRouter, UserScopedWebSocketEventRouter]:
    """
    Backward compatibility function that routes to appropriate router.
    
    If user_context is provided, uses user-scoped router.
    Otherwise, falls back to singleton router for backward compatibility.
    
    Args:
        user_context: Optional UserExecutionContext for user-scoped access
        websocket_manager: Optional WebSocket manager
        
    Returns:
        Event router instance (user-scoped or singleton)
    """
    if user_context is not None:
        return create_user_event_router(user_context)
    else:
        # Fallback to singleton for backward compatibility
        logger.warning(
            "Using singleton WebSocketEventRouter - consider migrating to user-scoped access"
        )
        return get_websocket_router(websocket_manager)


# SSOT Exports
__all__ = [
    # Core classes
    "UserScopedWebSocketEventRouter",
    "WebSocketEventRouterFactory",
    "UserEventRoutingRegistry",
    
    # Factory functions
    "get_event_router_factory",
    "create_user_event_router",
    "route_user_event",
    "broadcast_user_event",
    
    # Compatibility functions
    "get_websocket_router_with_context"
]