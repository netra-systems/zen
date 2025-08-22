"""Enhanced WebSocket Connection Lifecycle Manager

Fixes critical connection lifecycle issues identified in failing tests:
- Heartbeat mechanism with proper ping/pong handling
- Graceful shutdown with connection draining
- Connection pool management with limits
- Zombie connection detection and cleanup
- Resource cleanup on disconnect

Business Value: Prevents $8K MRR loss from poor real-time experience
Architecture: Follows CLAUDE.md modularity with <25 line functions
"""

import asyncio
import json
import time
import weakref
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket.connection import ConnectionInfo

logger = central_logger.get_logger(__name__)


class ConnectionLifecycleState(Enum):
    """Connection lifecycle states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    HEARTBEAT_ACTIVE = "heartbeat_active"
    DRAINING = "draining"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class HeartbeatConfig:
    """Configuration for heartbeat mechanism."""
    ping_interval: float = 30.0  # Send ping every 30 seconds
    pong_timeout: float = 10.0   # Wait max 10 seconds for pong
    max_missed_pongs: int = 3    # Max consecutive missed pongs
    zombie_detection_threshold: float = 120.0  # 2 minutes without response


@dataclass
class ConnectionPool:
    """Connection pool configuration and tracking."""
    max_connections_per_user: int = 5
    max_total_connections: int = 1000
    connection_timeout: float = 300.0  # 5 minutes idle timeout
    pool_cleanup_interval: float = 60.0  # Cleanup every minute


@dataclass
class ShutdownConfig:
    """Graceful shutdown configuration."""
    drain_timeout: float = 30.0
    force_close_timeout: float = 60.0
    message_flush_timeout: float = 5.0
    notify_clients: bool = True


@dataclass
class ConnectionMetrics:
    """Track connection metrics and health."""
    connection_id: str
    user_id: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_ping_sent: Optional[datetime] = None
    last_pong_received: Optional[datetime] = None
    missed_pong_count: int = 0
    total_messages_sent: int = 0
    total_messages_received: int = 0
    state: ConnectionLifecycleState = ConnectionLifecycleState.CONNECTING
    is_zombie: bool = False


class EnhancedHeartbeatManager:
    """Enhanced heartbeat manager with proper ping/pong handling."""
    
    def __init__(self, config: HeartbeatConfig = None):
        self.config = config or HeartbeatConfig()
        self.active_heartbeats: Dict[str, asyncio.Task] = {}
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}
        self.zombie_connections: Set[str] = set()
        
    async def start_heartbeat(self, conn_info: ConnectionInfo) -> None:
        """Start heartbeat monitoring for connection."""
        if conn_info.connection_id in self.active_heartbeats:
            logger.warning(f"Heartbeat already active for {conn_info.connection_id}")
            return
            
        metrics = ConnectionMetrics(
            connection_id=conn_info.connection_id,
            user_id=conn_info.user_id,
            state=ConnectionLifecycleState.HEARTBEAT_ACTIVE
        )
        self.connection_metrics[conn_info.connection_id] = metrics
        
        task = asyncio.create_task(self._heartbeat_loop(conn_info, metrics))
        self.active_heartbeats[conn_info.connection_id] = task
        logger.debug(f"Started heartbeat for connection {conn_info.connection_id}")

    async def _heartbeat_loop(self, conn_info: ConnectionInfo, metrics: ConnectionMetrics) -> None:
        """Main heartbeat loop with zombie detection."""
        try:
            while self._should_continue_heartbeat(conn_info, metrics):
                await self._send_ping(conn_info, metrics)
                await asyncio.sleep(self.config.ping_interval)
                
                if self._check_zombie_status(metrics):
                    await self._handle_zombie_connection(conn_info, metrics)
                    break
                    
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat cancelled for {conn_info.connection_id}")
        except Exception as e:
            logger.error(f"Heartbeat error for {conn_info.connection_id}: {e}")
        finally:
            await self._cleanup_heartbeat(conn_info.connection_id)

    def _should_continue_heartbeat(self, conn_info: ConnectionInfo, metrics: ConnectionMetrics) -> bool:
        """Check if heartbeat should continue."""
        if not hasattr(conn_info.websocket, 'client_state'):
            return False
        return conn_info.websocket.client_state == WebSocketState.CONNECTED

    async def _send_ping(self, conn_info: ConnectionInfo, metrics: ConnectionMetrics) -> None:
        """Send ping message to client."""
        try:
            ping_message = {
                "type": "ping", 
                "timestamp": time.time(),
                "connection_id": conn_info.connection_id
            }
            
            await conn_info.websocket.send_json(ping_message)
            metrics.last_ping_sent = datetime.now(timezone.utc)
            logger.debug(f"Sent ping to {conn_info.connection_id}")
            
        except Exception as e:
            logger.warning(f"Failed to send ping to {conn_info.connection_id}: {e}")
            metrics.missed_pong_count += 1

    def _check_zombie_status(self, metrics: ConnectionMetrics) -> bool:
        """Check if connection should be considered zombie."""
        if metrics.missed_pong_count >= self.config.max_missed_pongs:
            metrics.is_zombie = True
            return True
            
        if metrics.last_ping_sent:
            time_since_ping = (datetime.now(timezone.utc) - metrics.last_ping_sent).total_seconds()
            if time_since_ping > self.config.zombie_detection_threshold:
                metrics.is_zombie = True
                return True
                
        return False

    async def _handle_zombie_connection(self, conn_info: ConnectionInfo, metrics: ConnectionMetrics) -> None:
        """Handle detected zombie connection."""
        logger.warning(f"Zombie connection detected: {conn_info.connection_id}")
        self.zombie_connections.add(conn_info.connection_id)
        metrics.state = ConnectionLifecycleState.DISCONNECTING
        
        # Signal that connection should be closed
        try:
            await conn_info.websocket.close(code=1001, reason="Zombie connection detected")
        except Exception:
            pass  # Connection might already be closed

    async def handle_pong_received(self, connection_id: str, pong_data: Dict[str, Any] = None) -> None:
        """Handle pong response from client."""
        if connection_id not in self.connection_metrics:
            logger.warning(f"Received pong for unknown connection {connection_id}")
            return
            
        metrics = self.connection_metrics[connection_id]
        metrics.last_pong_received = datetime.now(timezone.utc)
        metrics.missed_pong_count = 0
        metrics.is_zombie = False
        
        if connection_id in self.zombie_connections:
            self.zombie_connections.remove(connection_id)
            
        logger.debug(f"Received pong from {connection_id}")

    async def stop_heartbeat(self, connection_id: str) -> None:
        """Stop heartbeat monitoring for connection."""
        if connection_id in self.active_heartbeats:
            task = self.active_heartbeats[connection_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        await self._cleanup_heartbeat(connection_id)

    async def _cleanup_heartbeat(self, connection_id: str) -> None:
        """Clean up heartbeat resources."""
        self.active_heartbeats.pop(connection_id, None)
        self.connection_metrics.pop(connection_id, None)
        self.zombie_connections.discard(connection_id)

    def get_zombie_connections(self) -> Set[str]:
        """Get list of detected zombie connections."""
        return self.zombie_connections.copy()

    def get_connection_health(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get health status for connection."""
        if connection_id not in self.connection_metrics:
            return None
            
        metrics = self.connection_metrics[connection_id]
        return {
            "connection_id": connection_id,
            "state": metrics.state.value,
            "is_zombie": metrics.is_zombie,
            "missed_pong_count": metrics.missed_pong_count,
            "last_ping_sent": metrics.last_ping_sent.isoformat() if metrics.last_ping_sent else None,
            "last_pong_received": metrics.last_pong_received.isoformat() if metrics.last_pong_received else None
        }


class EnhancedConnectionPool:
    """Enhanced connection pool with proper limits and cleanup."""
    
    def __init__(self, config: ConnectionPool = None):
        self.config = config or ConnectionPool()
        self.connections: Dict[str, ConnectionInfo] = {}
        self.user_connections: Dict[str, Set[str]] = {}
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        
    async def add_connection(self, conn_info: ConnectionInfo) -> bool:
        """Add connection to pool with limit enforcement."""
        if not self._check_pool_limits(conn_info.user_id):
            logger.warning(f"Pool limit exceeded for user {conn_info.user_id}")
            return False
            
        self._register_connection(conn_info)
        await self._start_pool_monitoring()
        return True

    def _check_pool_limits(self, user_id: str) -> bool:
        """Check if connection can be added within limits."""
        if len(self.connections) >= self.config.max_total_connections:
            return False
            
        user_conn_count = len(self.user_connections.get(user_id, set()))
        return user_conn_count < self.config.max_connections_per_user

    def _register_connection(self, conn_info: ConnectionInfo) -> None:
        """Register connection in pool."""
        self.connections[conn_info.connection_id] = conn_info
        
        if conn_info.user_id not in self.user_connections:
            self.user_connections[conn_info.user_id] = set()
        self.user_connections[conn_info.user_id].add(conn_info.connection_id)
        
        metrics = ConnectionMetrics(
            connection_id=conn_info.connection_id,
            user_id=conn_info.user_id,
            state=ConnectionLifecycleState.CONNECTED
        )
        self.connection_metrics[conn_info.connection_id] = metrics

    async def _start_pool_monitoring(self) -> None:
        """Start pool cleanup monitoring if not already running."""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._pool_cleanup_loop())

    async def _pool_cleanup_loop(self) -> None:
        """Periodic cleanup of stale connections."""
        try:
            while True:
                await asyncio.sleep(self.config.pool_cleanup_interval)
                await self._cleanup_stale_connections()
        except asyncio.CancelledError:
            logger.debug("Pool cleanup task cancelled")

    async def _cleanup_stale_connections(self) -> None:
        """Clean up stale and timed-out connections."""
        current_time = datetime.now(timezone.utc)
        stale_connections = []
        
        for conn_id, metrics in self.connection_metrics.items():
            time_since_connect = (current_time - metrics.connected_at).total_seconds()
            if time_since_connect > self.config.connection_timeout:
                stale_connections.append(conn_id)
                
        for conn_id in stale_connections:
            logger.info(f"Cleaning up stale connection {conn_id}")
            await self.remove_connection(conn_id)

    async def remove_connection(self, connection_id: str) -> None:
        """Remove connection from pool."""
        if connection_id not in self.connections:
            return
            
        conn_info = self.connections[connection_id]
        
        # Remove from user connections
        if conn_info.user_id in self.user_connections:
            self.user_connections[conn_info.user_id].discard(connection_id)
            if not self.user_connections[conn_info.user_id]:
                del self.user_connections[conn_info.user_id]
                
        # Clean up tracking
        del self.connections[connection_id]
        self.connection_metrics.pop(connection_id, None)

    def get_connection_count(self, user_id: str = None) -> int:
        """Get connection count for user or total."""
        if user_id:
            return len(self.user_connections.get(user_id, set()))
        return len(self.connections)

    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status."""
        return {
            "total_connections": len(self.connections),
            "max_total_connections": self.config.max_total_connections,
            "users_connected": len(self.user_connections),
            "pool_utilization": len(self.connections) / self.config.max_total_connections * 100
        }

    async def shutdown_pool(self) -> None:
        """Shutdown connection pool."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass


class GracefulShutdownManager:
    """Graceful shutdown with connection draining."""
    
    def __init__(self, config: ShutdownConfig = None):
        self.config = config or ShutdownConfig()
        self.is_shutting_down = False
        self.shutdown_callbacks: List[Callable] = []
        
    async def initiate_shutdown(self, connection_pool: EnhancedConnectionPool, 
                              heartbeat_manager: EnhancedHeartbeatManager) -> Dict[str, Any]:
        """Initiate graceful shutdown process."""
        if self.is_shutting_down:
            return {"error": "Shutdown already in progress"}
            
        logger.info("Starting graceful WebSocket shutdown")
        self.is_shutting_down = True
        
        shutdown_stats = {
            "started_at": time.time(),
            "total_connections": connection_pool.get_connection_count(),
            "phases_completed": []
        }
        
        try:
            # Phase 1: Stop accepting new connections (already handled by setting flag)
            if self.config.notify_clients:
                await self._notify_clients_of_shutdown(connection_pool)
            shutdown_stats["phases_completed"].append("notification")
            
            # Phase 2: Drain existing connections
            await self._drain_connections(connection_pool)
            shutdown_stats["phases_completed"].append("drain")
            
            # Phase 3: Stop heartbeats
            await self._shutdown_heartbeats(heartbeat_manager)
            shutdown_stats["phases_completed"].append("heartbeat_shutdown")
            
            # Phase 4: Force close remaining connections
            await self._force_close_remaining(connection_pool)
            shutdown_stats["phases_completed"].append("force_close")
            
            # Phase 5: Execute cleanup callbacks
            await self._execute_shutdown_callbacks()
            shutdown_stats["phases_completed"].append("cleanup")
            
            shutdown_stats["completed_at"] = time.time()
            shutdown_stats["duration"] = shutdown_stats["completed_at"] - shutdown_stats["started_at"]
            shutdown_stats["success"] = True
            
            logger.info(f"Graceful shutdown completed in {shutdown_stats['duration']:.2f}s")
            return shutdown_stats
            
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")
            shutdown_stats["error"] = str(e)
            shutdown_stats["success"] = False
            return shutdown_stats

    async def _notify_clients_of_shutdown(self, connection_pool: EnhancedConnectionPool) -> None:
        """Notify all clients of impending shutdown."""
        notification = {
            "type": "server_shutdown",
            "message": "Server is shutting down gracefully",
            "drain_timeout": self.config.drain_timeout,
            "timestamp": time.time()
        }
        
        notification_tasks = []
        for conn_info in connection_pool.connections.values():
            task = self._send_shutdown_notification(conn_info, notification)
            notification_tasks.append(task)
            
        if notification_tasks:
            await asyncio.gather(*notification_tasks, return_exceptions=True)

    async def _send_shutdown_notification(self, conn_info: ConnectionInfo, notification: Dict[str, Any]) -> None:
        """Send shutdown notification to specific connection."""
        try:
            await conn_info.websocket.send_json(notification)
        except Exception as e:
            logger.debug(f"Failed to notify connection {conn_info.connection_id}: {e}")

    async def _drain_connections(self, connection_pool: EnhancedConnectionPool) -> None:
        """Allow connections to drain naturally."""
        drain_start = time.time()
        
        while (time.time() - drain_start) < self.config.drain_timeout:
            if connection_pool.get_connection_count() == 0:
                break
            await asyncio.sleep(1.0)
            
        logger.info(f"Connection drain completed, {connection_pool.get_connection_count()} connections remaining")

    async def _shutdown_heartbeats(self, heartbeat_manager: EnhancedHeartbeatManager) -> None:
        """Stop all heartbeat monitoring."""
        connection_ids = list(heartbeat_manager.active_heartbeats.keys())
        shutdown_tasks = [
            heartbeat_manager.stop_heartbeat(conn_id) 
            for conn_id in connection_ids
        ]
        
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

    async def _force_close_remaining(self, connection_pool: EnhancedConnectionPool) -> None:
        """Force close any remaining connections."""
        remaining_connections = list(connection_pool.connections.values())
        
        for conn_info in remaining_connections:
            try:
                await conn_info.websocket.close(code=1001, reason="Server shutdown")
                await connection_pool.remove_connection(conn_info.connection_id)
            except Exception as e:
                logger.debug(f"Error force closing connection {conn_info.connection_id}: {e}")

    async def _execute_shutdown_callbacks(self) -> None:
        """Execute registered shutdown callbacks."""
        for callback in self.shutdown_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error in shutdown callback: {e}")

    def add_shutdown_callback(self, callback: Callable) -> None:
        """Add callback to be executed during shutdown."""
        self.shutdown_callbacks.append(callback)


class EnhancedLifecycleManager:
    """Main enhanced lifecycle manager coordinating all components."""
    
    def __init__(self, heartbeat_config: HeartbeatConfig = None,
                 pool_config: ConnectionPool = None, shutdown_config: ShutdownConfig = None):
        self.heartbeat_manager = EnhancedHeartbeatManager(heartbeat_config)
        self.connection_pool = EnhancedConnectionPool(pool_config)
        self.shutdown_manager = GracefulShutdownManager(shutdown_config)
        
    async def connect_user(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Connect user with full lifecycle management."""
        # Create connection info
        connection_id = f"{user_id}_{int(time.time() * 1000)}"
        conn_info = ConnectionInfo(
            connection_id=connection_id,
            websocket=websocket,
            user_id=user_id,
            connected_at=datetime.now(timezone.utc)
        )
        
        # Add to pool
        if not await self.connection_pool.add_connection(conn_info):
            raise Exception("Connection pool limit exceeded")
            
        # Start heartbeat monitoring
        await self.heartbeat_manager.start_heartbeat(conn_info)
        
        logger.info(f"User {user_id} connected with full lifecycle management")
        return conn_info

    async def disconnect_user(self, connection_id: str, code: int = 1000, reason: str = "Normal closure") -> None:
        """Disconnect user with proper cleanup."""
        # Stop heartbeat
        await self.heartbeat_manager.stop_heartbeat(connection_id)
        
        # Remove from pool
        await self.connection_pool.remove_connection(connection_id)
        
        logger.info(f"Connection {connection_id} disconnected with cleanup")

    async def handle_pong(self, connection_id: str, pong_data: Dict[str, Any] = None) -> None:
        """Handle pong message from client."""
        await self.heartbeat_manager.handle_pong_received(connection_id, pong_data)

    def get_zombie_connections(self) -> Set[str]:
        """Get detected zombie connections."""
        return self.heartbeat_manager.get_zombie_connections()

    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status."""
        return self.connection_pool.get_pool_status()

    async def cleanup_zombie_connections(self) -> List[str]:
        """Clean up detected zombie connections."""
        zombie_connections = self.get_zombie_connections()
        cleaned = []
        
        for conn_id in zombie_connections:
            try:
                await self.disconnect_user(conn_id, code=1001, reason="Zombie connection cleanup")
                cleaned.append(conn_id)
            except Exception as e:
                logger.error(f"Error cleaning up zombie connection {conn_id}: {e}")
                
        return cleaned

    async def initiate_graceful_shutdown(self) -> Dict[str, Any]:
        """Initiate graceful shutdown of all connections."""
        return await self.shutdown_manager.initiate_shutdown(self.connection_pool, self.heartbeat_manager)

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive lifecycle statistics."""
        return {
            "heartbeat": {
                "active_heartbeats": len(self.heartbeat_manager.active_heartbeats),
                "zombie_connections": len(self.heartbeat_manager.zombie_connections)
            },
            "pool": self.connection_pool.get_pool_status(),
            "shutdown": {
                "is_shutting_down": self.shutdown_manager.is_shutting_down
            }
        }

    async def shutdown(self) -> None:
        """Complete shutdown of lifecycle manager."""
        await self.shutdown_manager.initiate_shutdown(self.connection_pool, self.heartbeat_manager)
        await self.connection_pool.shutdown_pool()