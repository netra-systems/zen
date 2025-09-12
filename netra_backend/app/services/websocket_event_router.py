"""
WebSocketEventRouter - Infrastructure for routing events to specific user connections.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: User Isolation & Event Security  
- Value Impact: Prevents cross-user event leakage, ensures proper event routing
- Strategic Impact: Enables secure multi-user chat functionality with guaranteed event isolation

This router manages WebSocket connection pools and routes events to specific user connections,
providing the infrastructure layer for per-user event emission without being a singleton itself.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager

logger = central_logger.get_logger(__name__)


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    connection_id: str
    user_id: str
    thread_id: Optional[str]
    connected_at: datetime
    last_activity: datetime
    
    def is_active(self) -> bool:
        """Check if connection is still active based on recent activity."""
        # Consider connection active if last activity was within 5 minutes
        return (datetime.now(timezone.utc) - self.last_activity).seconds < 300


class WebSocketEventRouter:
    """Routes events to specific user connections.
    
    This class manages the WebSocket connection pool and provides routing
    functionality to ensure events reach only their intended recipients.
    
    Unlike the old singleton bridge, this class focuses solely on routing
    infrastructure and does not emit events itself.
    """
    
    def __init__(self, websocket_manager: Optional[WebSocketManager]):
        """Initialize router with WebSocket manager dependency.
        
        Args:
            websocket_manager: Optional WebSocket manager instance for actual connection management
        """
        self.websocket_manager = websocket_manager
        
        # Connection tracking - user_id -> List[ConnectionInfo]
        self.connection_pool: Dict[str, List[ConnectionInfo]] = {}
        
        # Connection ID to user mapping for quick lookups
        self.connection_to_user: Dict[str, str] = {}
        
        # Lock for thread-safe connection management
        self._pool_lock = asyncio.Lock()
        
        logger.info("WebSocketEventRouter initialized")
    
    async def register_connection(self, user_id: str, connection_id: str, 
                                 thread_id: Optional[str] = None) -> bool:
        """Register a user's WebSocket connection.
        
        Args:
            user_id: User identifier
            connection_id: Unique connection identifier
            thread_id: Optional thread/conversation identifier
            
        Returns:
            bool: True if registration successful
        """
        async with self._pool_lock:
            try:
                # Create connection info
                conn_info = ConnectionInfo(
                    connection_id=connection_id,
                    user_id=user_id,
                    thread_id=thread_id,
                    connected_at=datetime.now(timezone.utc),
                    last_activity=datetime.now(timezone.utc)
                )
                
                # Add to pool
                if user_id not in self.connection_pool:
                    self.connection_pool[user_id] = []
                
                self.connection_pool[user_id].append(conn_info)
                self.connection_to_user[connection_id] = user_id
                
                logger.info(f"Registered connection {connection_id} for user {user_id}")
                return True
                
            except Exception as e:
                logger.critical(f" ALERT:  CRITICAL: Failed to register connection {connection_id} for user {user_id[:8]}...: {e}")
                logger.critical(f" ALERT:  BUSINESS VALUE FAILURE: WebSocket connection registration failed")
                logger.critical(f" ALERT:  Impact: User will not receive real-time agent events")
                # LOUD ERROR: Log stack trace for debugging
                import traceback
                logger.critical(f" ALERT:  Stack trace: {traceback.format_exc()}")
                return False
    
    async def unregister_connection(self, connection_id: str) -> bool:
        """Remove a connection from the pool.
        
        Args:
            connection_id: Connection identifier to remove
            
        Returns:
            bool: True if removal successful
        """
        async with self._pool_lock:
            try:
                # Find user for this connection
                user_id = self.connection_to_user.get(connection_id)
                if not user_id:
                    logger.warning(f"Connection {connection_id} not found in registry")
                    return False
                
                # Remove from user's connection list
                if user_id in self.connection_pool:
                    self.connection_pool[user_id] = [
                        conn for conn in self.connection_pool[user_id] 
                        if conn.connection_id != connection_id
                    ]
                    
                    # Clean up empty user entries
                    if not self.connection_pool[user_id]:
                        del self.connection_pool[user_id]
                
                # Remove from connection-to-user mapping
                del self.connection_to_user[connection_id]
                
                logger.info(f"Unregistered connection {connection_id} for user {user_id}")
                return True
                
            except Exception as e:
                logger.error(f" ALERT:  ERROR: Failed to unregister connection {connection_id}: {e}")
                logger.error(f" ALERT:  IMPACT: Connection pool may have stale entries")
                logger.error(f" ALERT:  This could lead to memory leaks or incorrect event routing")
                # LOUD ERROR: Log stack trace for debugging
                import traceback
                logger.error(f" ALERT:  Stack trace: {traceback.format_exc()}")
                return False
    
    async def route_event(self, user_id: str, connection_id: str, event: Dict[str, Any]) -> bool:
        """Route event to specific user connection.
        
        Args:
            user_id: Target user identifier
            connection_id: Specific connection to send to
            event: Event payload to send
            
        Returns:
            bool: True if event sent successfully
        """
        try:
            # Validate connection belongs to user
            if not await self._validate_connection(user_id, connection_id):
                logger.critical(f" ALERT:  CRITICAL SECURITY: Invalid connection {connection_id} for user {user_id[:8]}...")
                logger.critical(f" ALERT:  SECURITY BREACH ATTEMPT: Connection validation failed")
                logger.critical(f" ALERT:  Impact: Potential cross-user event leakage prevented")
                logger.critical(f" ALERT:  This indicates a serious security issue requiring immediate investigation")
                return False
            
            # Update last activity
            await self._update_connection_activity(connection_id)
            
            # Route through WebSocket manager to specific connection
            success = await self._send_to_connection(connection_id, event)
            
            if success:
                logger.debug(f"Routed event {event.get('type', 'unknown')} to {user_id}:{connection_id}")
            else:
                logger.warning(f"Failed to route event to {user_id}:{connection_id}")
                
            return success
            
        except Exception as e:
            logger.critical(f" ALERT:  CRITICAL: Error routing event to {user_id[:8]}...:{connection_id}: {e}")
            logger.critical(f" ALERT:  BUSINESS VALUE FAILURE: Event routing failed")
            logger.critical(f" ALERT:  Impact: User will not receive this real-time update")
            logger.critical(f" ALERT:  Event type: {event.get('type', 'unknown')}")
            # LOUD ERROR: Log stack trace for debugging
            import traceback
            logger.critical(f" ALERT:  Stack trace: {traceback.format_exc()}")
            return False
    
    async def broadcast_to_user(self, user_id: str, event: Dict[str, Any]) -> int:
        """Broadcast event to all connections for a user.
        
        Args:
            user_id: User to broadcast to
            event: Event payload
            
        Returns:
            int: Number of successful sends
        """
        successful_sends = 0
        
        user_connections = self.connection_pool.get(user_id, [])
        if not user_connections:
            logger.error(f" ALERT:  ERROR: No connections found for user {user_id[:8]}...")
            logger.error(f" ALERT:  BUSINESS VALUE IMPACT: User will not receive event")
            logger.error(f" ALERT:  Event type: {event.get('type', 'unknown')}")
            logger.error(f" ALERT:  This indicates disconnected user or connection pool corruption")
            return 0
        
        for conn_info in user_connections:
            try:
                if await self.route_event(user_id, conn_info.connection_id, event):
                    successful_sends += 1
            except Exception as e:
                logger.error(f" ALERT:  ERROR: Failed to broadcast to connection {conn_info.connection_id}: {e}")
                logger.error(f" ALERT:  BUSINESS VALUE IMPACT: One connection missed the event")
                logger.error(f" ALERT:  User: {user_id[:8]}..., Event: {event.get('type', 'unknown')}")
                # Log stack trace for debugging
                import traceback
                logger.error(f" ALERT:  Stack trace: {traceback.format_exc()}")
        
        logger.debug(f"Broadcasted to {successful_sends}/{len(user_connections)} connections for user {user_id}")
        return successful_sends
    
    async def get_user_connections(self, user_id: str) -> List[str]:
        """Get all connection IDs for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of connection IDs
        """
        connections = self.connection_pool.get(user_id, [])
        return [conn.connection_id for conn in connections if conn.is_active()]
    
    async def cleanup_stale_connections(self) -> int:
        """Clean up inactive connections.
        
        Returns:
            int: Number of connections cleaned up
        """
        cleaned_count = 0
        
        async with self._pool_lock:
            users_to_remove = []
            
            for user_id, connections in self.connection_pool.items():
                active_connections = []
                
                for conn in connections:
                    if conn.is_active():
                        active_connections.append(conn)
                    else:
                        # Remove from connection-to-user mapping
                        if conn.connection_id in self.connection_to_user:
                            del self.connection_to_user[conn.connection_id]
                        cleaned_count += 1
                        logger.debug(f"Cleaned up stale connection {conn.connection_id}")
                
                if active_connections:
                    self.connection_pool[user_id] = active_connections
                else:
                    users_to_remove.append(user_id)
            
            # Remove empty user entries
            for user_id in users_to_remove:
                del self.connection_pool[user_id]
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} stale connections")
        
        return cleaned_count
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get router statistics.
        
        Returns:
            Dictionary with router statistics
        """
        total_connections = sum(len(conns) for conns in self.connection_pool.values())
        active_connections = sum(
            len([c for c in conns if c.is_active()]) 
            for conns in self.connection_pool.values()
        )
        
        return {
            "total_users": len(self.connection_pool),
            "total_connections": total_connections,
            "active_connections": active_connections,
            "connections_per_user": {
                user_id: len(conns) 
                for user_id, conns in self.connection_pool.items()
            }
        }
    
    # Private helper methods
    
    async def _validate_connection(self, user_id: str, connection_id: str) -> bool:
        """Validate that connection belongs to user."""
        return self.connection_to_user.get(connection_id) == user_id
    
    async def _update_connection_activity(self, connection_id: str) -> None:
        """Update last activity timestamp for connection."""
        user_id = self.connection_to_user.get(connection_id)
        if not user_id:
            return
        
        user_connections = self.connection_pool.get(user_id, [])
        for conn in user_connections:
            if conn.connection_id == connection_id:
                conn.last_activity = datetime.now(timezone.utc)
                break
    
    async def _send_to_connection(self, connection_id: str, event: Dict[str, Any]) -> bool:
        """Send event to specific connection via WebSocket manager."""
        try:
            # Check if WebSocket manager is available
            if not self.websocket_manager:
                logger.critical(f" ALERT:  CRITICAL: Cannot send event to connection {connection_id}: WebSocket manager not initialized")
                logger.critical(f" ALERT:  BUSINESS VALUE FAILURE: WebSocket infrastructure missing")
                logger.critical(f" ALERT:  Impact: All real-time events will fail")
                logger.critical(f" ALERT:  This is a SYSTEM FAILURE requiring immediate attention")
                return False
            
            # Extract thread_id from event or connection info if needed
            thread_id = event.get('thread_id')
            if not thread_id:
                # Try to get thread_id from connection info
                user_id = self.connection_to_user.get(connection_id)
                if user_id:
                    user_connections = self.connection_pool.get(user_id, [])
                    for conn in user_connections:
                        if conn.connection_id == connection_id:
                            thread_id = conn.thread_id
                            break
            
            # Send via WebSocket manager (this API may need adjustment based on actual manager)
            if hasattr(self.websocket_manager, 'send_to_connection'):
                return await self.websocket_manager.send_to_connection(connection_id, event)
            elif hasattr(self.websocket_manager, 'send_message_to_thread') and thread_id:
                return await self.websocket_manager.send_message_to_thread(thread_id, event)
            else:
                logger.critical(f" ALERT:  CRITICAL: WebSocket manager does not have expected send methods")
                logger.critical(f" ALERT:  BUSINESS VALUE FAILURE: WebSocket manager API mismatch")
                logger.critical(f" ALERT:  Impact: All real-time events will fail")
                logger.critical(f" ALERT:  Manager type: {type(self.websocket_manager).__name__}")
                logger.critical(f" ALERT:  Available methods: {[m for m in dir(self.websocket_manager) if not m.startswith('_')]}")
                return False
                
        except Exception as e:
            logger.critical(f" ALERT:  CRITICAL: Failed to send event to connection {connection_id}: {e}")
            logger.critical(f" ALERT:  BUSINESS VALUE FAILURE: WebSocket send operation failed")
            logger.critical(f" ALERT:  Impact: User will not receive this real-time update")
            logger.critical(f" ALERT:  Event type: {event.get('type', 'unknown')}")
            # LOUD ERROR: Log stack trace for debugging
            import traceback
            logger.critical(f" ALERT:  Stack trace: {traceback.format_exc()}")
            return False


# Module-level router instance factory
_router_instance: Optional[WebSocketEventRouter] = None


def get_websocket_router(websocket_manager=None) -> WebSocketEventRouter:
    """Get the WebSocket event router instance.
    
    Args:
        websocket_manager: Optional WebSocket manager instance for dependency injection
        
    Returns:
        WebSocketEventRouter: Router instance
    """
    global _router_instance
    
    if _router_instance is None:
        if websocket_manager is None:
            # SECURITY FIX: This should only be called with proper context
            # Log warning when fallback is used
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("WebSocketEventRouter: No WebSocket manager provided, using factory pattern")
            
            # Create router without manager - it will need to be initialized later
            _router_instance = WebSocketEventRouter(None)
        else:
            _router_instance = WebSocketEventRouter(websocket_manager)
    
    return _router_instance


def reset_websocket_router() -> None:
    """Reset the router instance (for testing)."""
    global _router_instance
    _router_instance = None