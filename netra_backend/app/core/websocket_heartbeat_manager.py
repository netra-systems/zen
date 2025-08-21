"""WebSocket heartbeat monitoring and health management.

Provides heartbeat functionality to monitor connection health
and detect connection issues through ping/pong mechanism.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, Callable

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_recovery_types import ConnectionMetrics

logger = central_logger.get_logger(__name__)


class WebSocketHeartbeatManager:
    """Manages WebSocket heartbeat monitoring and health checks."""
    
    def __init__(self, connection_id: str, metrics: ConnectionMetrics):
        """Initialize heartbeat manager."""
        self.connection_id = connection_id
        self.metrics = metrics
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.heartbeat_interval = 30.0
        self.missed_heartbeats = 0
        self.max_missed_heartbeats = 3
        self.on_heartbeat_timeout: Optional[Callable] = None
    
    async def start_heartbeat(self, websocket, connection_state_checker: Callable) -> None:
        """Start heartbeat monitoring."""
        if self.heartbeat_task:
            return
        self.heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(websocket, connection_state_checker)
        )
    
    async def stop_heartbeat(self) -> None:
        """Stop heartbeat monitoring."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None
    
    async def _heartbeat_loop(self, websocket, connection_state_checker: Callable) -> None:
        """Heartbeat monitoring loop."""
        while connection_state_checker():
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if not connection_state_checker():
                    break
                await self._send_heartbeat_ping(websocket)
                await self._check_heartbeat_response()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                if self.on_heartbeat_timeout:
                    await self.on_heartbeat_timeout(e)
                break
    
    async def _send_heartbeat_ping(self, websocket) -> None:
        """Send heartbeat ping."""
        ping_message = {
            'type': 'ping',
            'timestamp': datetime.now().isoformat()
        }
        self.metrics.last_ping = datetime.now()
        await websocket.send(json.dumps(ping_message))
        await asyncio.sleep(5.0)
    
    async def _check_heartbeat_response(self) -> None:
        """Check heartbeat response and handle timeouts."""
        if self.metrics.last_pong and self.metrics.last_ping:
            if self.metrics.last_pong < self.metrics.last_ping:
                self.missed_heartbeats += 1
            else:
                self.missed_heartbeats = 0
                self._calculate_latency()
        await self._check_missed_heartbeats()
    
    def _calculate_latency(self) -> None:
        """Calculate connection latency from ping/pong."""
        if self.metrics.last_pong and self.metrics.last_ping:
            latency = (self.metrics.last_pong - self.metrics.last_ping).total_seconds() * 1000
            self.metrics.latency_ms = latency
    
    async def _check_missed_heartbeats(self) -> None:
        """Check for missed heartbeats and trigger timeout."""
        if self.missed_heartbeats >= self.max_missed_heartbeats:
            logger.warning(f"Heartbeat timeout: {self.connection_id}")
            if self.on_heartbeat_timeout:
                await self.on_heartbeat_timeout(Exception("Heartbeat timeout"))
    
    def handle_pong(self) -> None:
        """Handle pong response."""
        self.metrics.last_pong = datetime.now()
        self.missed_heartbeats = 0
    
    def get_missed_heartbeats(self) -> int:
        """Get count of missed heartbeats."""
        return self.missed_heartbeats