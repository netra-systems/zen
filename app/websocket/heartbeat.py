"""WebSocket heartbeat and connection health monitoring.

Manages heartbeat/ping-pong functionality to detect dead connections
and maintain connection health.
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Set
from dataclasses import dataclass, field

from app.logging_config import central_logger
from .connection import ConnectionInfo, ConnectionManager
from .error_handler import ErrorHandler, WebSocketError, ErrorSeverity

logger = central_logger.get_logger(__name__)


@dataclass
class HeartbeatConfig:
    """Configuration for heartbeat functionality."""
    interval_seconds: int = 30  # How often to send pings
    timeout_seconds: int = 60   # How long to wait for pong before considering connection dead
    max_missed_heartbeats: int = 3  # Max consecutive missed heartbeats before disconnection


class HeartbeatManager:
    """Manages WebSocket heartbeat functionality."""
    
    def __init__(self, connection_manager: ConnectionManager, error_handler: Optional[ErrorHandler] = None):
        """Initialize heartbeat manager.
        
        Args:
            connection_manager: Connection manager instance
            error_handler: Error handler for reporting issues
        """
        self.connection_manager = connection_manager
        self.error_handler = error_handler
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self.config = HeartbeatConfig()
        self.missed_heartbeats: Dict[str, int] = {}  # Track missed heartbeats per connection
        self._running = False
        self._stats = {
            "total_pings_sent": 0,
            "total_pongs_received": 0,
            "connections_timed_out": 0,
            "heartbeat_failures": 0
        }
    
    async def start_heartbeat_for_connection(self, conn_info: ConnectionInfo):
        """Start heartbeat monitoring for a connection.
        
        Args:
            conn_info: Connection to monitor
        """
        if conn_info.connection_id in self.heartbeat_tasks:
            logger.warning(f"Heartbeat already running for connection {conn_info.connection_id}")
            return
        
        task = asyncio.create_task(self._heartbeat_loop(conn_info))
        self.heartbeat_tasks[conn_info.connection_id] = task
        self.missed_heartbeats[conn_info.connection_id] = 0
        
        logger.debug(f"Started heartbeat for connection {conn_info.connection_id}")
    
    async def stop_heartbeat_for_connection(self, connection_id: str):
        """Stop heartbeat monitoring for a connection.
        
        Args:
            connection_id: Connection to stop monitoring
        """
        if connection_id not in self.heartbeat_tasks:
            return
        
        task = self.heartbeat_tasks[connection_id]
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Error stopping heartbeat for {connection_id}: {e}")
        
        del self.heartbeat_tasks[connection_id]
        if connection_id in self.missed_heartbeats:
            del self.missed_heartbeats[connection_id]
        
        logger.debug(f"Stopped heartbeat for connection {connection_id}")
    
    async def handle_pong(self, conn_info: ConnectionInfo):
        """Handle pong response from client.
        
        Args:
            conn_info: Connection that sent pong
        """
        conn_info.last_pong = datetime.now(timezone.utc)
        
        # Reset missed heartbeat counter
        if conn_info.connection_id in self.missed_heartbeats:
            self.missed_heartbeats[conn_info.connection_id] = 0
        
        self._stats["total_pongs_received"] += 1
        logger.debug(f"Received pong from connection {conn_info.connection_id}")
    
    def is_connection_alive(self, conn_info: ConnectionInfo) -> bool:
        """Check if a connection is still alive based on heartbeat.
        
        Args:
            conn_info: Connection to check
            
        Returns:
            True if connection appears to be alive
        """
        if not self.connection_manager.is_connection_alive(conn_info):
            return False
        
        # Check heartbeat timeout
        now = datetime.now(timezone.utc)
        time_since_ping = (now - conn_info.last_ping).total_seconds()
        
        if time_since_ping > self.config.timeout_seconds:
            logger.debug(f"Connection {conn_info.connection_id} heartbeat timeout ({time_since_ping:.1f}s)")
            return False
        
        # Check missed heartbeats
        missed_count = self.missed_heartbeats.get(conn_info.connection_id, 0)
        if missed_count >= self.config.max_missed_heartbeats:
            logger.debug(f"Connection {conn_info.connection_id} exceeded missed heartbeat limit ({missed_count})")
            return False
        
        return True
    
    async def _heartbeat_loop(self, conn_info: ConnectionInfo):
        """Heartbeat loop for a specific connection.
        
        Args:
            conn_info: Connection to monitor
        """
        try:
            while self.connection_manager.is_connection_alive(conn_info):
                try:
                    # Send ping
                    await self._send_ping(conn_info)
                    conn_info.last_ping = datetime.now(timezone.utc)
                    self._stats["total_pings_sent"] += 1
                    
                    # Wait for heartbeat interval
                    await asyncio.sleep(self.config.interval_seconds)
                    
                    # Check if we received a pong within the timeout period
                    await self._check_pong_response(conn_info)
                    
                    # Check if connection is still alive
                    if not self.is_connection_alive(conn_info):
                        logger.warning(f"Connection {conn_info.connection_id} failed heartbeat check")
                        break
                        
                except asyncio.CancelledError:
                    raise  # Re-raise cancellation to exit gracefully
                except Exception as e:
                    await self._handle_heartbeat_error(conn_info, e)
                    
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat cancelled for {conn_info.connection_id}")
        except Exception as e:
            logger.error(f"Heartbeat error for {conn_info.connection_id}: {e}")
            if self.error_handler:
                await self.error_handler.handle_connection_error(
                    conn_info, 
                    f"Heartbeat loop error: {e}",
                    "heartbeat_error",
                    ErrorSeverity.MEDIUM
                )
        finally:
            # Clean up
            if conn_info.connection_id in self.heartbeat_tasks:
                del self.heartbeat_tasks[conn_info.connection_id]
            if conn_info.connection_id in self.missed_heartbeats:
                del self.missed_heartbeats[conn_info.connection_id]
    
    async def _send_ping(self, conn_info: ConnectionInfo):
        """Send ping message to connection.
        
        Args:
            conn_info: Connection to ping
        """
        ping_message = {
            "type": "ping",
            "timestamp": time.time(),
            "system": True
        }
        
        try:
            if self.connection_manager.is_connection_alive(conn_info):
                await conn_info.websocket.send_json(ping_message)
            else:
                raise ConnectionError("WebSocket not in connected state")
        except Exception as e:
            logger.debug(f"Failed to send ping to {conn_info.connection_id}: {e}")
            raise
    
    async def _check_pong_response(self, conn_info: ConnectionInfo):
        """Check if we received a pong response within the timeout.
        
        Args:
            conn_info: Connection to check
        """
        now = datetime.now(timezone.utc)
        
        # If we have never received a pong, use the ping time as baseline
        last_response_time = conn_info.last_pong or conn_info.last_ping
        time_since_response = (now - last_response_time).total_seconds()
        
        if time_since_response > self.config.timeout_seconds:
            # Increment missed heartbeat counter
            missed_count = self.missed_heartbeats.get(conn_info.connection_id, 0) + 1
            self.missed_heartbeats[conn_info.connection_id] = missed_count
            
            logger.debug(f"Connection {conn_info.connection_id} missed heartbeat {missed_count}/{self.config.max_missed_heartbeats}")
            
            if missed_count >= self.config.max_missed_heartbeats:
                self._stats["connections_timed_out"] += 1
                if self.error_handler:
                    await self.error_handler.handle_connection_error(
                        conn_info,
                        f"Connection timed out after {missed_count} missed heartbeats",
                        "heartbeat_timeout",
                        ErrorSeverity.HIGH
                    )
    
    async def _handle_heartbeat_error(self, conn_info: ConnectionInfo, error: Exception):
        """Handle errors during heartbeat operations.
        
        Args:
            conn_info: Connection that had the error
            error: Error that occurred
        """
        self._stats["heartbeat_failures"] += 1
        
        if self.error_handler:
            await self.error_handler.handle_connection_error(
                conn_info,
                f"Heartbeat error: {error}",
                "heartbeat_error",
                ErrorSeverity.MEDIUM
            )
        
        # For most heartbeat errors, we should stop the heartbeat and let connection cleanup handle it
        await self.stop_heartbeat_for_connection(conn_info.connection_id)
    
    async def cleanup_dead_connections(self):
        """Check all monitored connections and clean up dead ones."""
        dead_connections = []
        
        for connection_id, task in list(self.heartbeat_tasks.items()):
            conn_info = self.connection_manager.get_connection_by_id(connection_id)
            
            if not conn_info or not self.is_connection_alive(conn_info):
                dead_connections.append(connection_id)
        
        for connection_id in dead_connections:
            await self.stop_heartbeat_for_connection(connection_id)
            logger.info(f"Cleaned up heartbeat for dead connection {connection_id}")
    
    async def shutdown_all_heartbeats(self):
        """Stop all heartbeat monitoring."""
        logger.info("Shutting down all heartbeat monitoring...")
        
        tasks_to_cancel = []
        for connection_id, task in self.heartbeat_tasks.items():
            if not task.done():
                task.cancel()
                tasks_to_cancel.append(task)
        
        # Wait for all tasks to cancel
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        
        self.heartbeat_tasks.clear()
        self.missed_heartbeats.clear()
        
        logger.info(f"Heartbeat shutdown complete. Final stats: {self.get_stats()}")
    
    def get_stats(self) -> Dict[str, any]:
        """Get heartbeat statistics.
        
        Returns:
            Dictionary with heartbeat statistics
        """
        active_heartbeats = len(self.heartbeat_tasks)
        total_missed = sum(self.missed_heartbeats.values())
        
        return {
            "active_heartbeats": active_heartbeats,
            "total_pings_sent": self._stats["total_pings_sent"],
            "total_pongs_received": self._stats["total_pongs_received"],
            "connections_timed_out": self._stats["connections_timed_out"],
            "heartbeat_failures": self._stats["heartbeat_failures"],
            "total_missed_heartbeats": total_missed,
            "config": {
                "interval_seconds": self.config.interval_seconds,
                "timeout_seconds": self.config.timeout_seconds,
                "max_missed_heartbeats": self.config.max_missed_heartbeats
            }
        }
    
    def get_connection_heartbeat_info(self, connection_id: str) -> Optional[Dict[str, any]]:
        """Get heartbeat information for a specific connection.
        
        Args:
            connection_id: Connection to get info for
            
        Returns:
            Dictionary with heartbeat info or None if not monitored
        """
        if connection_id not in self.heartbeat_tasks:
            return None
        
        conn_info = self.connection_manager.get_connection_by_id(connection_id)
        if not conn_info:
            return None
        
        missed_count = self.missed_heartbeats.get(connection_id, 0)
        is_alive = self.is_connection_alive(conn_info)
        
        return {
            "connection_id": connection_id,
            "is_alive": is_alive,
            "last_ping": conn_info.last_ping.isoformat(),
            "last_pong": conn_info.last_pong.isoformat() if conn_info.last_pong else None,
            "missed_heartbeats": missed_count,
            "max_missed_heartbeats": self.config.max_missed_heartbeats,
            "heartbeat_active": not self.heartbeat_tasks[connection_id].done()
        }