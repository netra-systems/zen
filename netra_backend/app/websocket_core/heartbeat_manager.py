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
    heartbeat_timeout_seconds: int = 90  # CRITICAL FIX: Increased from 60 to handle staging latency
    max_missed_heartbeats: int = 2       # CRITICAL FIX: Reduced from 3 for faster detection
    cleanup_interval_seconds: int = 120  # CRITICAL FIX: Increased cleanup interval for staging
    ping_payload_size_limit: int = 125   # WebSocket control frame limit
    
    @classmethod
    def for_environment(cls, environment: str = "development") -> "HeartbeatConfig":
        """Create environment-specific heartbeat configuration."""
        if environment == "staging":
            return cls(
                heartbeat_interval_seconds=30,
                heartbeat_timeout_seconds=90,   # Longer timeout for GCP staging
                max_missed_heartbeats=2,        # Faster detection
                cleanup_interval_seconds=120,   # Less aggressive cleanup
                ping_payload_size_limit=125
            )
        elif environment == "production":
            return cls(
                heartbeat_interval_seconds=25,
                heartbeat_timeout_seconds=75,   # Conservative production timeout
                max_missed_heartbeats=2,        # Quick detection
                cleanup_interval_seconds=180,   # Conservative cleanup
                ping_payload_size_limit=125
            )
        else:  # development/testing
            return cls(
                heartbeat_interval_seconds=45,
                heartbeat_timeout_seconds=60,   # Standard dev timeout
                max_missed_heartbeats=3,        # More permissive for dev
                cleanup_interval_seconds=60,    # Standard cleanup
                ping_payload_size_limit=125
            )


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
        """Initialize heartbeat manager with thread-safe collections."""
        self.config = config or HeartbeatConfig()
        self.connection_heartbeats: Dict[str, ConnectionHeartbeat] = {}
        self.active_pings: Dict[str, float] = {}  # connection_id -> ping_timestamp
        
        # ROBUSTNESS: Add locks for thread safety
        self._heartbeat_lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        
        # Tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Statistics with more comprehensive tracking
        self.stats = {
            'pings_sent': 0,
            'pongs_received': 0,
            'timeouts_detected': 0,
            'connections_dropped': 0,
            'avg_ping_time': 0.0,
            'total_connections_registered': 0,
            'resurrection_count': 0,
            'cleanup_runs': 0
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
        """Register a new connection for heartbeat monitoring with duplicate handling."""
        # ROBUSTNESS: Handle duplicate registrations gracefully
        if connection_id in self.connection_heartbeats:
            logger.warning(f"Connection {connection_id} already registered, resetting heartbeat state")
            # Clean up any stale state
            if connection_id in self.active_pings:
                del self.active_pings[connection_id]
        
        self.connection_heartbeats[connection_id] = ConnectionHeartbeat(connection_id)
        logger.debug(f"Registered connection {connection_id} for heartbeat monitoring")
    
    async def unregister_connection(self, connection_id: str) -> None:
        """Unregister connection with comprehensive cleanup."""
        # ROBUSTNESS: Track if connection was actually registered
        was_registered = False
        
        if connection_id in self.connection_heartbeats:
            # ROBUSTNESS: Log final state before removal for debugging
            final_state = self.get_connection_status(connection_id)
            if final_state:
                logger.debug(f"Unregistering {connection_id} - final state: alive={final_state['is_alive']}, missed={final_state['missed_heartbeats']}")
            
            del self.connection_heartbeats[connection_id]
            was_registered = True
        
        if connection_id in self.active_pings:
            del self.active_pings[connection_id]
            was_registered = True
        
        if was_registered:
            logger.debug(f"Unregistered connection {connection_id} from heartbeat monitoring")
        else:
            logger.debug(f"Attempted to unregister unknown connection {connection_id}")
    
    async def record_activity(self, connection_id: str) -> None:
        """Record activity for a connection with validation."""
        if connection_id in self.connection_heartbeats:
            heartbeat = self.connection_heartbeats[connection_id]
            current_time = time.time()
            
            # ROBUSTNESS: Track activity frequency for debugging
            if heartbeat.last_activity:
                time_since_last = current_time - heartbeat.last_activity
                if time_since_last < 0.1:  # Less than 100ms
                    logger.debug(f"Rapid activity for {connection_id}: {time_since_last*1000:.1f}ms since last")
            
            heartbeat.last_activity = current_time
            heartbeat.missed_heartbeats = 0
            
            # ROBUSTNESS: Resurrect dead connections if activity detected
            if not heartbeat.is_alive:
                logger.info(f"Resurrecting connection {connection_id} due to activity")
                heartbeat.is_alive = True
                async with self._stats_lock:
                    self.stats['connections_dropped'] = max(0, self.stats['connections_dropped'] - 1)
                    self.stats['resurrection_count'] += 1
        else:
            logger.debug(f"Activity recorded for unregistered connection {connection_id}")
    
    async def record_pong(self, connection_id: str, ping_timestamp: Optional[float] = None) -> None:
        """Record pong response from client with enhanced validation."""
        current_time = time.time()
        
        # ROBUSTNESS: Validate connection exists
        if connection_id not in self.connection_heartbeats:
            logger.warning(f"Received pong for unregistered connection: {connection_id}")
            return
        
        heartbeat = self.connection_heartbeats[connection_id]
        heartbeat.last_pong_received = current_time
        heartbeat.missed_heartbeats = 0
        heartbeat.is_alive = True
        heartbeat.last_activity = current_time
        
        # Calculate ping time if we have the original ping timestamp
        if ping_timestamp and connection_id in self.active_pings:
            ping_time = current_time - ping_timestamp
            
            # ROBUSTNESS: Validate ping time is reasonable (< 30 seconds)
            if ping_time > 30:
                logger.warning(f"Abnormally high ping time for {connection_id}: {ping_time:.1f}s")
            elif ping_time < 0:
                logger.error(f"Negative ping time for {connection_id}: {ping_time:.1f}s")
            else:
                self._update_avg_ping_time(ping_time)
            
            del self.active_pings[connection_id]
        elif connection_id in self.active_pings:
            # No timestamp provided, but we have an active ping
            del self.active_pings[connection_id]
        
        self.stats['pongs_received'] += 1
        logger.debug(f"Received pong from {connection_id}")
    
    async def send_ping(self, connection_id: str, websocket, payload: bytes = b'') -> bool:
        """
        Send ping to specific connection with enhanced error handling.
        
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
        
        # ROBUSTNESS: Validate connection exists before attempting ping
        if connection_id not in self.connection_heartbeats:
            logger.warning(f"Attempting to ping unregistered connection: {connection_id}")
            return False
            
        try:
            current_time = time.time()
            
            # ROBUSTNESS: Check if previous ping is still pending (possible network issue)
            if connection_id in self.active_pings:
                ping_age = current_time - self.active_pings[connection_id]
                if ping_age < self.config.heartbeat_interval_seconds:
                    logger.debug(f"Skipping ping for {connection_id} - previous ping still pending ({ping_age:.1f}s old)")
                    return True  # Not an error, just skip this ping
            
            # Update heartbeat state
            heartbeat = self.connection_heartbeats[connection_id]
            heartbeat.last_ping_sent = current_time
            
            # ROBUSTNESS: Add timeout to ping operation
            ping_timeout = min(5.0, self.config.heartbeat_interval_seconds / 2)
            await asyncio.wait_for(websocket.ping(payload), timeout=ping_timeout)
            
            # Track active ping
            self.active_pings[connection_id] = current_time
            self.stats['pings_sent'] += 1
            
            logger.debug(f"Sent ping to {connection_id}")
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"Ping timeout for {connection_id}")
            # Don't immediately mark as dead - could be temporary network issue
            if connection_id in self.connection_heartbeats:
                self.connection_heartbeats[connection_id].missed_heartbeats += 1
            return False
        except Exception as e:
            logger.error(f"Failed to send ping to {connection_id}: {e}")
            await self._mark_connection_dead(connection_id)
            return False
    
    async def check_connection_health(self, connection_id: str) -> bool:
        """Check if connection is healthy with comprehensive validation."""
        if connection_id not in self.connection_heartbeats:
            logger.debug(f"Connection {connection_id} not found in heartbeat registry")
            return False
            
        heartbeat = self.connection_heartbeats[connection_id]
        current_time = time.time()
        
        # ROBUSTNESS: Multiple health checks with priority
        health_checks = []
        
        # Check if explicitly marked as dead
        if not heartbeat.is_alive:
            health_checks.append((False, "Connection marked as dead"))
        
        # Check if we've exceeded timeout
        if heartbeat.last_activity:
            time_since_activity = current_time - heartbeat.last_activity
            if time_since_activity > self.config.heartbeat_timeout_seconds:
                health_checks.append((False, f"Activity timeout: {time_since_activity:.1f}s"))
            elif time_since_activity > self.config.heartbeat_timeout_seconds * 0.8:
                health_checks.append((True, f"Warning: Approaching timeout: {time_since_activity:.1f}s"))
        else:
            # No activity recorded yet - check connection age
            health_checks.append((True, "No activity recorded yet"))
        
        # Check missed heartbeats
        if heartbeat.missed_heartbeats >= self.config.max_missed_heartbeats:
            health_checks.append((False, f"Too many missed heartbeats: {heartbeat.missed_heartbeats}"))
        elif heartbeat.missed_heartbeats > 0:
            health_checks.append((True, f"Warning: {heartbeat.missed_heartbeats} missed heartbeats"))
        
        # Check for stale pending pings
        if connection_id in self.active_pings:
            ping_age = current_time - self.active_pings[connection_id]
            if ping_age > self.config.heartbeat_timeout_seconds:
                health_checks.append((False, f"Stale pending ping: {ping_age:.1f}s old"))
        
        # Process health checks
        is_healthy = True
        for healthy, reason in health_checks:
            if not healthy and "Warning" not in reason:
                logger.debug(f"Connection {connection_id} unhealthy: {reason}")
                await self._mark_connection_dead(connection_id)
                return False
            elif "Warning" in reason:
                logger.debug(f"Connection {connection_id}: {reason}")
        
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
        """Process heartbeat with enhanced error handling and logging."""
        try:
            # ROBUSTNESS: Skip already dead connections unless recently resurrected
            if not heartbeat.is_alive:
                time_since_death = current_time - heartbeat.last_activity if heartbeat.last_activity else float('inf')
                if time_since_death > self.config.cleanup_interval_seconds:
                    return  # Skip processing long-dead connections
            
            # Check if connection has been inactive too long
            if heartbeat.last_activity:
                time_since_activity = current_time - heartbeat.last_activity
                
                # ROBUSTNESS: Progressive warning levels
                if time_since_activity > self.config.heartbeat_timeout_seconds:
                    logger.warning(f"Connection {connection_id} timeout: {time_since_activity:.1f}s since last activity")
                    await self._mark_connection_dead(connection_id)
                    return
                elif time_since_activity > self.config.heartbeat_timeout_seconds * 0.8:
                    logger.debug(f"Connection {connection_id} approaching timeout: {time_since_activity:.1f}s")
            else:
                # ROBUSTNESS: Initialize activity for new connections
                heartbeat.last_activity = current_time
            
            # Check for missed pongs
            if heartbeat.last_ping_sent and connection_id in self.active_pings:
                ping_age = current_time - heartbeat.last_ping_sent
                
                # ROBUSTNESS: Consider network latency before marking as missed
                adjusted_timeout = self.config.heartbeat_timeout_seconds * 1.2  # 20% grace period
                
                if ping_age > adjusted_timeout:
                    heartbeat.missed_heartbeats += 1
                    logger.warning(f"Missed pong from {connection_id}: {heartbeat.missed_heartbeats}/{self.config.max_missed_heartbeats} (ping age: {ping_age:.1f}s)")
                    
                    # Remove from active pings
                    del self.active_pings[connection_id]
                    
                    if heartbeat.missed_heartbeats >= self.config.max_missed_heartbeats:
                        await self._mark_connection_dead(connection_id)
                elif ping_age > self.config.heartbeat_timeout_seconds:
                    logger.debug(f"Ping for {connection_id} in grace period: {ping_age:.1f}s")
                    
        except Exception as e:
            logger.error(f"Error processing heartbeat for {connection_id}: {e}", exc_info=True)
            # ROBUSTNESS: Don't let one bad connection break the whole loop
    
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
        """Clean up stale heartbeat data with comprehensive validation."""
        try:
            current_time = time.time()
            cleanup_threshold = self.config.heartbeat_timeout_seconds * 2
            
            # ROBUSTNESS: Track cleanup metrics
            cleanup_stats = {
                'dead_connections': 0,
                'orphaned_pings': 0,
                'resurrected': 0
            }
            
            # Clean up dead connections
            dead_connections = []
            for conn_id, heartbeat in list(self.connection_heartbeats.items()):
                if not heartbeat.is_alive:
                    time_since_death = current_time - heartbeat.last_activity if heartbeat.last_activity else cleanup_threshold + 1
                    
                    if time_since_death > cleanup_threshold:
                        dead_connections.append(conn_id)
                    elif time_since_death < 0:
                        # ROBUSTNESS: Handle clock skew
                        logger.warning(f"Clock skew detected for {conn_id}: negative time since death")
                        heartbeat.last_activity = current_time
            
            for conn_id in dead_connections:
                await self.unregister_connection(conn_id)
                cleanup_stats['dead_connections'] += 1
            
            # Clean up orphaned active pings (pings without corresponding heartbeat entries)
            orphaned_pings = []
            old_pings = []
            
            for conn_id, ping_time in list(self.active_pings.items()):
                if conn_id not in self.connection_heartbeats:
                    # ROBUSTNESS: Orphaned ping - no corresponding connection
                    orphaned_pings.append(conn_id)
                elif current_time - ping_time > cleanup_threshold:
                    old_pings.append(conn_id)
                elif current_time - ping_time < 0:
                    # ROBUSTNESS: Handle clock skew
                    logger.warning(f"Clock skew detected for ping {conn_id}: negative age")
                    self.active_pings[conn_id] = current_time
            
            for conn_id in orphaned_pings + old_pings:
                del self.active_pings[conn_id]
                if conn_id in orphaned_pings:
                    cleanup_stats['orphaned_pings'] += 1
            
            # ROBUSTNESS: Log cleanup summary if anything was cleaned
            if any(cleanup_stats.values()):
                logger.info(f"Heartbeat cleanup: removed {cleanup_stats['dead_connections']} dead connections, "
                          f"{cleanup_stats['orphaned_pings']} orphaned pings, {len(old_pings)} old pings")
                
        except Exception as e:
            logger.error(f"Error during heartbeat cleanup: {e}", exc_info=True)
            # ROBUSTNESS: Don't let cleanup errors break the service
    
    async def _mark_connection_dead(self, connection_id: str) -> None:
        """Mark connection as dead with comprehensive cleanup."""
        if connection_id in self.connection_heartbeats:
            heartbeat = self.connection_heartbeats[connection_id]
            
            # ROBUSTNESS: Only mark dead once to prevent duplicate stats
            if heartbeat.is_alive:
                heartbeat.is_alive = False
                heartbeat.last_activity = time.time()  # Record when it died
                async with self._stats_lock:
                    self.stats['timeouts_detected'] += 1
                    self.stats['connections_dropped'] += 1
                
                # Clean up any pending pings
                if connection_id in self.active_pings:
                    del self.active_pings[connection_id]
                
                logger.warning(f"Marked connection {connection_id} as dead - missed: {heartbeat.missed_heartbeats}, last_activity: {heartbeat.last_activity}")
            else:
                logger.debug(f"Connection {connection_id} already marked as dead")
    
    def _update_avg_ping_time(self, ping_time: float) -> None:
        """Update average ping time statistics with bounds checking."""
        # ROBUSTNESS: Validate ping time
        if ping_time <= 0 or ping_time > 30:
            logger.debug(f"Ignoring invalid ping time: {ping_time}")
            return
        
        if self.stats['avg_ping_time'] == 0.0:
            self.stats['avg_ping_time'] = ping_time
        else:
            # Exponential moving average with outlier dampening
            alpha = 0.1
            
            # ROBUSTNESS: Dampen effect of outliers
            if ping_time > self.stats['avg_ping_time'] * 5:
                alpha = 0.02  # Reduce weight of outliers
            
            self.stats['avg_ping_time'] = (alpha * ping_time) + ((1 - alpha) * self.stats['avg_ping_time'])
            
            # ROBUSTNESS: Keep track of min/max for debugging
            if 'min_ping_time' not in self.stats:
                self.stats['min_ping_time'] = ping_time
                self.stats['max_ping_time'] = ping_time
            else:
                self.stats['min_ping_time'] = min(self.stats['min_ping_time'], ping_time)
                self.stats['max_ping_time'] = max(self.stats['max_ping_time'], ping_time)
    
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
    """Get global heartbeat manager instance with environment-aware configuration."""
    global _heartbeat_manager
    if _heartbeat_manager is None:
        # CRITICAL FIX: Use environment-specific configuration if none provided
        if config is None:
            from shared.isolated_environment import get_env
            env = get_env()
            environment = env.get("ENVIRONMENT", "development").lower()
            config = HeartbeatConfig.for_environment(environment)
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