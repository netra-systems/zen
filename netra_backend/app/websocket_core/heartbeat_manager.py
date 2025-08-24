"""
WebSocket Heartbeat Manager

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Development Velocity
- Value Impact: Ensures WebSocket connections remain alive and detects stale connections
- Strategic Impact: Prevents connection leaks and improves system resource management

Implements WebSocket heartbeat management with timeout detection and client alive tracking.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class HeartbeatConfig:
    """Configuration for heartbeat management."""
    heartbeat_interval_seconds: int = 30
    heartbeat_timeout_seconds: int = 60
    max_missed_heartbeats: int = 3
    cleanup_interval_seconds: int = 60
    ping_payload_size_limit: int = 125  # WebSocket control frame limit


@dataclass
class ConnectionHeartbeat:
    """Heartbeat state for a connection."""
    connection_id: str
    last_ping_sent: Optional[float] = None
    last_pong_received: Optional[float] = None
    missed_heartbeats: int = 0
    is_alive: bool = True
    last_activity: float = None
    
    def __post_init__(self):
        if self.last_activity is None:
            self.last_activity = time.time()


class WebSocketHeartbeatManager:
    """Manages WebSocket heartbeats with timeout detection."""
    
    def __init__(self, config: Optional[HeartbeatConfig] = None):
        """Initialize heartbeat manager."""
        self.config = config or HeartbeatConfig()
        self.connection_heartbeats: Dict[str, ConnectionHeartbeat] = {}
        self.active_pings: Dict[str, float] = {}  # connection_id -> ping_timestamp
        
        # Tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Statistics
        self.stats = {
            'pings_sent': 0,
            'pongs_received': 0,
            'timeouts_detected': 0,
            'connections_dropped': 0,
            'avg_ping_time': 0.0
        }
        
    async def start(self) -> None:
        """Start heartbeat monitoring tasks."""
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
        logger.info("WebSocket heartbeat manager started")
    
    async def stop(self) -> None:
        """Stop heartbeat monitoring."""
        self._shutdown = True
        
        for task in [self._heartbeat_task, self._cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("WebSocket heartbeat manager stopped")
    
    async def register_connection(self, connection_id: str) -> None:
        """Register a new connection for heartbeat monitoring."""
        self.connection_heartbeats[connection_id] = ConnectionHeartbeat(connection_id)
        logger.debug(f"Registered connection {connection_id} for heartbeat monitoring")
    
    async def unregister_connection(self, connection_id: str) -> None:
        """Unregister connection from heartbeat monitoring."""
        if connection_id in self.connection_heartbeats:
            del self.connection_heartbeats[connection_id]
        
        if connection_id in self.active_pings:
            del self.active_pings[connection_id]
            
        logger.debug(f"Unregistered connection {connection_id} from heartbeat monitoring")
    
    async def record_activity(self, connection_id: str) -> None:
        """Record activity for a connection (resets timeout)."""
        if connection_id in self.connection_heartbeats:
            heartbeat = self.connection_heartbeats[connection_id]
            heartbeat.last_activity = time.time()
            heartbeat.missed_heartbeats = 0
            heartbeat.is_alive = True
    
    async def record_pong(self, connection_id: str, ping_timestamp: Optional[float] = None) -> None:
        """Record pong response from client."""
        current_time = time.time()
        
        if connection_id in self.connection_heartbeats:
            heartbeat = self.connection_heartbeats[connection_id]
            heartbeat.last_pong_received = current_time
            heartbeat.missed_heartbeats = 0
            heartbeat.is_alive = True
            heartbeat.last_activity = current_time
            
            # Calculate ping time if we have the original ping timestamp
            if ping_timestamp and connection_id in self.active_pings:
                ping_time = current_time - ping_timestamp
                self._update_avg_ping_time(ping_time)
                del self.active_pings[connection_id]
            
            self.stats['pongs_received'] += 1
            logger.debug(f"Received pong from {connection_id}")
    
    async def send_ping(self, connection_id: str, websocket, payload: bytes = b'') -> bool:
        """
        Send ping to specific connection.
        
        Args:
            connection_id: Connection identifier
            websocket: WebSocket instance
            payload: Optional payload (max 125 bytes)
            
        Returns:
            True if ping was sent successfully
        """
        if len(payload) > self.config.ping_payload_size_limit:
            logger.warning(f"Ping payload too large: {len(payload)} bytes")
            return False
            
        try:
            current_time = time.time()
            
            # Update heartbeat state
            if connection_id in self.connection_heartbeats:
                heartbeat = self.connection_heartbeats[connection_id]
                heartbeat.last_ping_sent = current_time
            
            # Send ping
            await websocket.ping(payload)
            
            # Track active ping
            self.active_pings[connection_id] = current_time
            self.stats['pings_sent'] += 1
            
            logger.debug(f"Sent ping to {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send ping to {connection_id}: {e}")
            await self._mark_connection_dead(connection_id)
            return False
    
    async def check_connection_health(self, connection_id: str) -> bool:
        """Check if connection is healthy based on heartbeat status."""
        if connection_id not in self.connection_heartbeats:
            return False
            
        heartbeat = self.connection_heartbeats[connection_id]
        current_time = time.time()
        
        # Check if we've exceeded timeout
        if heartbeat.last_activity:
            time_since_activity = current_time - heartbeat.last_activity
            if time_since_activity > self.config.heartbeat_timeout_seconds:
                await self._mark_connection_dead(connection_id)
                return False
        
        # Check missed heartbeats
        if heartbeat.missed_heartbeats >= self.config.max_missed_heartbeats:
            await self._mark_connection_dead(connection_id)
            return False
        
        return heartbeat.is_alive
    
    def get_connection_status(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status for a connection."""
        if connection_id not in self.connection_heartbeats:
            return None
            
        heartbeat = self.connection_heartbeats[connection_id]
        current_time = time.time()
        
        return {
            'connection_id': connection_id,
            'is_alive': heartbeat.is_alive,
            'missed_heartbeats': heartbeat.missed_heartbeats,
            'last_activity': heartbeat.last_activity,
            'seconds_since_activity': current_time - heartbeat.last_activity if heartbeat.last_activity else None,
            'last_ping_sent': heartbeat.last_ping_sent,
            'last_pong_received': heartbeat.last_pong_received,
            'has_pending_ping': connection_id in self.active_pings
        }
    
    async def _heartbeat_loop(self) -> None:
        """Main heartbeat monitoring loop."""
        while not self._shutdown:
            try:
                await self._process_heartbeats()
                await asyncio.sleep(self.config.heartbeat_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def _process_heartbeats(self) -> None:
        """Process heartbeats for all connections."""
        current_time = time.time()
        
        for connection_id, heartbeat in list(self.connection_heartbeats.items()):
            await self._process_single_heartbeat(connection_id, heartbeat, current_time)
    
    async def _process_single_heartbeat(self, connection_id: str, heartbeat: ConnectionHeartbeat, current_time: float) -> None:
        """Process heartbeat for a single connection."""
        # Check if connection has been inactive too long
        if heartbeat.last_activity:
            time_since_activity = current_time - heartbeat.last_activity
            
            if time_since_activity > self.config.heartbeat_timeout_seconds:
                logger.warning(f"Connection {connection_id} timeout: {time_since_activity:.1f}s since last activity")
                await self._mark_connection_dead(connection_id)
                return
        
        # Check for missed pongs
        if heartbeat.last_ping_sent and connection_id in self.active_pings:
            ping_age = current_time - heartbeat.last_ping_sent
            
            if ping_age > self.config.heartbeat_timeout_seconds:
                heartbeat.missed_heartbeats += 1
                logger.warning(f"Missed pong from {connection_id}: {heartbeat.missed_heartbeats}/{self.config.max_missed_heartbeats}")
                
                # Remove from active pings
                del self.active_pings[connection_id]
                
                if heartbeat.missed_heartbeats >= self.config.max_missed_heartbeats:
                    await self._mark_connection_dead(connection_id)
    
    async def _cleanup_loop(self) -> None:
        """Cleanup stale data periodically."""
        while not self._shutdown:
            try:
                await self._cleanup_stale_data()
                await asyncio.sleep(self.config.cleanup_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat cleanup: {e}")
    
    async def _cleanup_stale_data(self) -> None:
        """Clean up stale heartbeat data."""
        current_time = time.time()
        cleanup_threshold = self.config.heartbeat_timeout_seconds * 2
        
        # Clean up dead connections
        dead_connections = [
            conn_id for conn_id, heartbeat in self.connection_heartbeats.items()
            if not heartbeat.is_alive and 
            (current_time - heartbeat.last_activity > cleanup_threshold if heartbeat.last_activity else True)
        ]
        
        for conn_id in dead_connections:
            await self.unregister_connection(conn_id)
        
        # Clean up old active pings
        old_pings = [
            conn_id for conn_id, ping_time in self.active_pings.items()
            if current_time - ping_time > cleanup_threshold
        ]
        
        for conn_id in old_pings:
            del self.active_pings[conn_id]
        
        if dead_connections or old_pings:
            logger.debug(f"Cleaned up {len(dead_connections)} dead connections, {len(old_pings)} old pings")
    
    async def _mark_connection_dead(self, connection_id: str) -> None:
        """Mark connection as dead."""
        if connection_id in self.connection_heartbeats:
            self.connection_heartbeats[connection_id].is_alive = False
            self.stats['timeouts_detected'] += 1
            logger.warning(f"Marked connection {connection_id} as dead")
    
    def _update_avg_ping_time(self, ping_time: float) -> None:
        """Update average ping time statistics."""
        if self.stats['avg_ping_time'] == 0.0:
            self.stats['avg_ping_time'] = ping_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.stats['avg_ping_time'] = (alpha * ping_time) + ((1 - alpha) * self.stats['avg_ping_time'])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get heartbeat manager statistics."""
        return {
            'active_connections': len([h for h in self.connection_heartbeats.values() if h.is_alive]),
            'total_connections': len(self.connection_heartbeats),
            'pending_pings': len(self.active_pings),
            **self.stats
        }
    
    def get_all_connection_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all connections."""
        return {
            conn_id: self.get_connection_status(conn_id)
            for conn_id in self.connection_heartbeats.keys()
        }


# Global heartbeat manager instance
_heartbeat_manager: Optional[WebSocketHeartbeatManager] = None


def get_heartbeat_manager(config: Optional[HeartbeatConfig] = None) -> WebSocketHeartbeatManager:
    """Get global heartbeat manager instance."""
    global _heartbeat_manager
    if _heartbeat_manager is None:
        _heartbeat_manager = WebSocketHeartbeatManager(config)
    return _heartbeat_manager


async def register_connection_heartbeat(connection_id: str) -> None:
    """Convenience function to register connection for heartbeat monitoring."""
    manager = get_heartbeat_manager()
    await manager.register_connection(connection_id)


async def unregister_connection_heartbeat(connection_id: str) -> None:
    """Convenience function to unregister connection from heartbeat monitoring."""
    manager = get_heartbeat_manager()
    await manager.unregister_connection(connection_id)


async def check_connection_heartbeat(connection_id: str) -> bool:
    """Convenience function to check connection health."""
    manager = get_heartbeat_manager()
    return await manager.check_connection_health(connection_id)