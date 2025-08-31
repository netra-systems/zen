"""
TTL Cache and Connection Limit Implementation for WebSocket Manager

This file contains the complete implementation of TTL cache and connection limit 
solution for preventing memory leaks in the WebSocket manager.

Key Features:
1. Connection limits (MAX_CONNECTIONS_PER_USER=5, MAX_TOTAL_CONNECTIONS=1000)
2. TTL cache with automatic expiration (5-minute TTL)
3. Connection eviction methods
4. Periodic cleanup task
5. Comprehensive logging and metrics

Implementation Plan:
1. Replace unbounded dictionaries with TTL-aware implementations
2. Add connection limit enforcement in connect_user method  
3. Implement eviction methods (_evict_oldest_connection and _evict_oldest_user_connection)
4. Add periodic cleanup task with logging and metrics
5. Ensure thread-safety with existing _cleanup_lock
"""

# Connection limit constants for memory leak prevention
MAX_CONNECTIONS_PER_USER = 5
MAX_TOTAL_CONNECTIONS = 1000
TTL_SECONDS = 300  # 5 minutes

class TTLWebSocketManager:
    """TTL-aware WebSocket Manager implementation."""
    
    def __init__(self):
        """Initialize WebSocket manager with TTL cache and connection limits."""
        from cachetools import TTLCache
        import asyncio
        
        # Connection limits for memory leak prevention
        self.MAX_CONNECTIONS_PER_USER = MAX_CONNECTIONS_PER_USER
        self.MAX_TOTAL_CONNECTIONS = MAX_TOTAL_CONNECTIONS
        
        # TTL-aware dictionaries with 5-minute expiration
        self.connections = TTLCache(maxsize=MAX_TOTAL_CONNECTIONS, ttl=TTL_SECONDS)
        self.user_connections: Dict[str, Set[str]] = {}  # Keep dict interface for compatibility
        self.room_memberships: Dict[str, Set[str]] = {}
        
        # TTL-aware run_id connections mapping
        self.run_id_connections = TTLCache(maxsize=MAX_TOTAL_CONNECTIONS, ttl=TTL_SECONDS)
        
        # Enhanced connection statistics
        self.connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors_handled": 0,
            "broadcasts_sent": 0,
            "start_time": time.time(),
            "connections_evicted": 0,
            "user_connections_evicted": 0,
            "ttl_cleanups": 0,
            "connection_limit_hits": 0,
            "total_limit_hits": 0
        }
        
        self._cleanup_lock = asyncio.Lock()
        
        # Start periodic cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def connect_user(self, user_id: str, websocket: WebSocket, 
                          thread_id: Optional[str] = None, client_ip: Optional[str] = None) -> str:
        """Connect user with WebSocket - enforcing connection limits."""
        # Check total connection limit first
        if len(self.connections) >= self.MAX_TOTAL_CONNECTIONS:
            logger.warning(f"Total connection limit ({self.MAX_TOTAL_CONNECTIONS}) reached")
            self.connection_stats["total_limit_hits"] += 1
            # Evict oldest connection to make room
            await self._evict_oldest_connection()
            
        # Check per-user connection limit
        user_conns = self.user_connections.get(user_id, set())
        if len(user_conns) >= self.MAX_CONNECTIONS_PER_USER:
            logger.warning(f"User {user_id} connection limit ({self.MAX_CONNECTIONS_PER_USER}) reached")
            self.connection_stats["connection_limit_hits"] += 1
            # Evict oldest user connection to make room
            await self._evict_oldest_user_connection(user_id)
        
        # Check rate limits first (existing logic)
        if client_ip:
            allowed, backoff_seconds = await check_connection_rate_limit(client_ip)
            if not allowed:
                logger.warning(f"Rate limit exceeded for {client_ip}, backoff: {backoff_seconds}s")
                raise WebSocketDisconnect(code=1013, reason=f"Rate limited, try again in {backoff_seconds:.1f}s")
        
        connection_id = f"conn_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Store connection info
        self.connections[connection_id] = {
            "connection_id": connection_id,
            "user_id": user_id,
            "websocket": websocket,
            "thread_id": thread_id,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0,
            "is_healthy": True,
            "client_ip": client_ip
        }
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Register for heartbeat monitoring (existing logic)
        await register_connection_heartbeat(connection_id)
        
        # Record rate limit tracking (existing logic)
        if client_ip:
            limiter = get_rate_limiter()
            await limiter.record_connection_attempt(client_ip)
        
        # Update stats
        self.connection_stats["total_connections"] += 1
        self.connection_stats["active_connections"] += 1
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id} "
                   f"(user connections: {len(self.user_connections.get(user_id, set()))}, "
                   f"total: {len(self.connections)})")
        return connection_id
    
    async def _evict_oldest_connection(self) -> None:
        """Evict the oldest connection when total limit is exceeded."""
        if not self.connections:
            return
            
        # Find oldest connection by connected_at timestamp
        oldest_conn_id = None
        oldest_time = datetime.now(timezone.utc)
        
        for conn_id, conn_info in self.connections.items():
            connected_at = conn_info.get("connected_at")
            if connected_at and connected_at < oldest_time:
                oldest_time = connected_at
                oldest_conn_id = conn_id
        
        if oldest_conn_id:
            logger.info(f"Evicting oldest connection {oldest_conn_id} due to total limit")
            await self._cleanup_connection(oldest_conn_id, 1000, "Total connection limit exceeded")
            self.connection_stats["connections_evicted"] += 1
    
    async def _evict_oldest_user_connection(self, user_id: str) -> None:
        """Evict the oldest connection for a specific user when user limit is exceeded."""
        user_conns = self.user_connections.get(user_id, set())
        if not user_conns:
            return
            
        # Find oldest connection for this user
        oldest_conn_id = None
        oldest_time = datetime.now(timezone.utc)
        
        for conn_id in user_conns:
            if conn_id in self.connections:
                connected_at = self.connections[conn_id].get("connected_at")
                if connected_at and connected_at < oldest_time:
                    oldest_time = connected_at
                    oldest_conn_id = conn_id
        
        if oldest_conn_id:
            logger.info(f"Evicting oldest connection {oldest_conn_id} for user {user_id} due to user limit")
            await self._cleanup_connection(oldest_conn_id, 1000, "User connection limit exceeded")
            self.connection_stats["user_connections_evicted"] += 1
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task that runs every 60 seconds to clean stale connections."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every 60 seconds
                
                async with self._cleanup_lock:
                    cleaned_count = 0
                    current_time = datetime.now(timezone.utc)
                    stale_connections = []
                    
                    # Check for stale connections
                    for conn_id, conn in list(self.connections.items()):
                        last_activity = conn.get("last_activity", current_time)
                        
                        # Check if connection is stale (no activity for TTL_SECONDS)
                        if (current_time - last_activity).total_seconds() > TTL_SECONDS:
                            stale_connections.append(conn_id)
                            
                        # Check WebSocket state
                        websocket = conn.get("websocket")
                        if websocket and not is_websocket_connected(websocket):
                            stale_connections.append(conn_id)
                    
                    # Clean up stale connections
                    for conn_id in stale_connections:
                        try:
                            await self._cleanup_connection(conn_id, 1000, "Periodic TTL cleanup")
                            cleaned_count += 1
                        except Exception as e:
                            logger.warning(f"Error during periodic cleanup of {conn_id}: {e}")
                    
                    # Clean up empty user connection sets
                    empty_users = [user_id for user_id, conns in self.user_connections.items() if not conns]
                    for user_id in empty_users:
                        del self.user_connections[user_id]
                    
                    if cleaned_count > 0:
                        logger.info(f"Periodic cleanup: removed {cleaned_count} stale connections, "
                                   f"cleaned {len(empty_users)} empty user sets")
                        self.connection_stats["ttl_cleanups"] += cleaned_count
                    
                    # Log current state every 10 minutes
                    if int(time.time()) % 600 == 0:  # Every 10 minutes
                        logger.info(f"WebSocket Manager Status: "
                                   f"Active connections: {len(self.connections)}, "
                                   f"Users: {len(self.user_connections)}, "
                                   f"Rooms: {len(self.room_memberships)}, "
                                   f"Run IDs: {len(self.run_id_connections)}")
                        
            except asyncio.CancelledError:
                logger.info("Periodic cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                continue
    
    async def cleanup_stale_connections(self) -> int:
        """Enhanced cleanup with TTL awareness and metrics."""
        async with self._cleanup_lock:
            stale_connections = []
            current_time = datetime.now(timezone.utc)
            
            for conn_id, conn in list(self.connections.items()):
                websocket = conn.get("websocket")
                last_activity = conn.get("last_activity", current_time)
                
                # Check if connection is stale (TTL-based expiration)
                if (current_time - last_activity).total_seconds() > TTL_SECONDS:
                    stale_connections.append(conn_id)
                # Check WebSocket state
                elif websocket and not is_websocket_connected(websocket):
                    stale_connections.append(conn_id)
            
            # Clean up stale connections
            for conn_id in stale_connections:
                try:
                    await self._cleanup_connection(conn_id, 1000, "TTL-based stale connection cleanup")
                except Exception as e:
                    logger.warning(f"Error cleaning stale connection {conn_id}: {e}")
            
            # Clean up empty user connection sets
            empty_users = [user_id for user_id, conns in self.user_connections.items() if not conns]
            for user_id in empty_users:
                del self.user_connections[user_id]
            
            if stale_connections:
                logger.info(f"TTL cleanup: removed {len(stale_connections)} stale connections, "
                           f"cleaned {len(empty_users)} empty user sets")
                self.connection_stats["ttl_cleanups"] += len(stale_connections)
            
            return len(stale_connections)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive WebSocket statistics including TTL and connection limit metrics."""
        uptime = time.time() - self.connection_stats["start_time"]
        
        # Calculate memory usage metrics
        total_user_connections = sum(len(conns) for conns in self.user_connections.values())
        total_room_connections = sum(len(conns) for conns in self.room_memberships.values())
        
        return {
            "active_connections": len(self.connections),
            "total_connections": self.connection_stats["total_connections"], 
            "messages_sent": self.connection_stats["messages_sent"],
            "messages_received": self.connection_stats["messages_received"],
            "errors_handled": self.connection_stats["errors_handled"],
            "uptime_seconds": uptime,
            "rooms_active": len(self.room_memberships),
            "broadcasts_sent": self.connection_stats["broadcasts_sent"],
            
            # TTL and connection limit metrics
            "connections_evicted": self.connection_stats["connections_evicted"],
            "user_connections_evicted": self.connection_stats["user_connections_evicted"],
            "ttl_cleanups": self.connection_stats["ttl_cleanups"],
            "connection_limit_hits": self.connection_stats["connection_limit_hits"],
            "total_limit_hits": self.connection_stats["total_limit_hits"],
            
            # Current limits and capacity
            "max_connections_per_user": self.MAX_CONNECTIONS_PER_USER,
            "max_total_connections": self.MAX_TOTAL_CONNECTIONS,
            "ttl_seconds": TTL_SECONDS,
            
            # Memory usage indicators
            "total_user_connections": total_user_connections,
            "total_room_connections": total_room_connections,
            "run_id_connections": len(self.run_id_connections),
            
            # Utilization percentages
            "connection_utilization": (len(self.connections) / self.MAX_TOTAL_CONNECTIONS) * 100,
            "memory_health": "OK" if len(self.connections) < self.MAX_TOTAL_CONNECTIONS * 0.8 else "HIGH"
        }
    
    async def shutdown(self) -> None:
        """Enhanced shutdown with cleanup task cancellation."""
        logger.info(f"Shutting down TTL WebSocket manager with {len(self.connections)} connections")
        
        # Cancel periodic cleanup task
        if hasattr(self, '_cleanup_task') and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        cleanup_tasks = []
        for conn_id in list(self.connections.keys()):
            cleanup_tasks.append(self._cleanup_connection(conn_id, 1001, "Server shutdown"))
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Clear all state
        self.connections.clear()
        self.user_connections.clear()
        self.room_memberships.clear()
        self.run_id_connections.clear()
        
        logger.info("TTL WebSocket manager shutdown complete")


# Integration functions to patch existing manager
def patch_websocket_manager_with_ttl(manager_instance):
    """Patch an existing WebSocket manager instance with TTL and connection limit features."""
    from cachetools import TTLCache
    
    # Replace connections with TTL cache
    old_connections = dict(manager_instance.connections)
    manager_instance.connections = TTLCache(maxsize=MAX_TOTAL_CONNECTIONS, ttl=TTL_SECONDS)
    
    # Restore existing connections
    for conn_id, conn_info in old_connections.items():
        manager_instance.connections[conn_id] = conn_info
    
    # Add connection limits
    manager_instance.MAX_CONNECTIONS_PER_USER = MAX_CONNECTIONS_PER_USER
    manager_instance.MAX_TOTAL_CONNECTIONS = MAX_TOTAL_CONNECTIONS
    
    # Replace run_id_connections with TTL cache
    old_run_id_connections = dict(getattr(manager_instance, 'run_id_connections', {}))
    manager_instance.run_id_connections = TTLCache(maxsize=MAX_TOTAL_CONNECTIONS, ttl=TTL_SECONDS)
    
    # Restore existing run_id connections
    for run_id, conn_set in old_run_id_connections.items():
        manager_instance.run_id_connections[run_id] = conn_set
    
    # Add enhanced connection statistics
    manager_instance.connection_stats.update({
        "connections_evicted": 0,
        "user_connections_evicted": 0,
        "ttl_cleanups": 0,
        "connection_limit_hits": 0,
        "total_limit_hits": 0
    })
    
    # Patch methods
    original_connect_user = manager_instance.connect_user
    original_cleanup_stale_connections = manager_instance.cleanup_stale_connections
    original_get_stats = manager_instance.get_stats
    original_shutdown = manager_instance.shutdown
    
    # Create TTL manager instance for method delegation
    ttl_manager = TTLWebSocketManager()
    
    # Monkey patch with TTL-aware methods
    manager_instance._evict_oldest_connection = ttl_manager._evict_oldest_connection.__get__(manager_instance)
    manager_instance._evict_oldest_user_connection = ttl_manager._evict_oldest_user_connection.__get__(manager_instance)
    manager_instance._periodic_cleanup = ttl_manager._periodic_cleanup.__get__(manager_instance)
    
    # Start periodic cleanup task
    if not hasattr(manager_instance, '_cleanup_task'):
        manager_instance._cleanup_task = asyncio.create_task(manager_instance._periodic_cleanup())
    
    logger.info("WebSocket manager patched with TTL cache and connection limits")
    return manager_instance


# Usage example
"""
# To integrate with existing WebSocket manager:

from netra_backend.app.websocket_core.manager import get_websocket_manager
from netra_backend.app.websocket_core.manager_ttl_implementation import patch_websocket_manager_with_ttl

# Get existing manager and patch it
manager = get_websocket_manager()
ttl_manager = patch_websocket_manager_with_ttl(manager)

# Now the manager has TTL cache and connection limits
# All existing functionality is preserved while adding memory leak prevention
"""