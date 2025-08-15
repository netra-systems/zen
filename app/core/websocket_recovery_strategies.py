"""WebSocket connection recovery and state restoration strategies.

Provides automatic reconnection, state synchronization, and graceful handling
of WebSocket connection failures with minimal user disruption.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ConnectionState(Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    CLOSING = "closing"


class ReconnectionReason(Enum):
    """Reasons for reconnection attempts."""
    CONNECTION_LOST = "connection_lost"
    NETWORK_ERROR = "network_error"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    MANUAL = "manual"


@dataclass
class ConnectionMetrics:
    """Metrics for WebSocket connection."""
    connection_id: str
    connect_time: datetime
    disconnect_time: Optional[datetime] = None
    message_count: int = 0
    error_count: int = 0
    reconnect_count: int = 0
    last_ping: Optional[datetime] = None
    last_pong: Optional[datetime] = None
    latency_ms: float = 0.0


@dataclass
class MessageState:
    """State of a WebSocket message."""
    message_id: str
    content: Dict[str, Any]
    timestamp: datetime
    ack_required: bool = False
    acknowledged: bool = False
    retry_count: int = 0


@dataclass
class ReconnectionConfig:
    """Configuration for reconnection behavior."""
    max_attempts: int = 10
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    timeout_seconds: int = 30
    
    # State preservation
    preserve_pending_messages: bool = True
    max_pending_messages: int = 1000
    message_retention_hours: int = 24


class WebSocketConnectionManager:
    """Manages WebSocket connections with recovery capabilities."""
    
    def __init__(
        self,
        connection_id: str,
        url: str,
        config: Optional[ReconnectionConfig] = None
    ):
        """Initialize connection manager."""
        self.connection_id = connection_id
        self.url = url
        self.config = config or ReconnectionConfig()
        
        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.websocket: Optional[Any] = None
        self.last_error: Optional[Exception] = None
        
        # Reconnection tracking
        self.reconnect_attempts = 0
        self.last_reconnect_time: Optional[datetime] = None
        self.reconnect_task: Optional[asyncio.Task] = None
        
        # Message state management
        self.pending_messages: List[MessageState] = []
        self.sent_messages: Dict[str, MessageState] = {}
        self.received_messages: Set[str] = set()
        
        # Metrics
        self.metrics = ConnectionMetrics(
            connection_id=connection_id,
            connect_time=datetime.now()
        )
        
        # Event handlers
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self.on_message: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Health monitoring
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.heartbeat_interval = 30.0
        self.missed_heartbeats = 0
        self.max_missed_heartbeats = 3
    
    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            return True
        
        self.state = ConnectionState.CONNECTING
        logger.info(f"Connecting to WebSocket: {self.connection_id}")
        
        try:
            import websockets
            
            self.websocket = await asyncio.wait_for(
                websockets.connect(self.url),
                timeout=self.config.timeout_seconds
            )
            
            self.state = ConnectionState.CONNECTED
            self.metrics.connect_time = datetime.now()
            self.reconnect_attempts = 0
            self.last_error = None
            
            # Start message handling and heartbeat
            asyncio.create_task(self._message_handler())
            await self._start_heartbeat()
            
            # Restore pending messages
            await self._restore_pending_messages()
            
            if self.on_connect:
                await self.on_connect(self.connection_id)
            
            logger.info(f"WebSocket connected: {self.connection_id}")
            return True
            
        except Exception as e:
            self.state = ConnectionState.FAILED
            self.last_error = e
            self.metrics.error_count += 1
            
            logger.error(f"WebSocket connection failed: {self.connection_id}: {e}")
            
            if self.on_error:
                await self.on_error(self.connection_id, e)
            
            return False
    
    async def disconnect(self, reason: str = "manual") -> None:
        """Gracefully disconnect WebSocket."""
        if self.state == ConnectionState.DISCONNECTED:
            return
        
        logger.info(f"Disconnecting WebSocket: {self.connection_id} ({reason})")
        
        self.state = ConnectionState.CLOSING
        
        # Stop heartbeat
        await self._stop_heartbeat()
        
        # Cancel reconnection if active
        if self.reconnect_task:
            self.reconnect_task.cancel()
        
        # Close WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
        
        self.state = ConnectionState.DISCONNECTED
        self.metrics.disconnect_time = datetime.now()
        
        if self.on_disconnect:
            await self.on_disconnect(self.connection_id, reason)
    
    async def send_message(
        self,
        message: Dict[str, Any],
        require_ack: bool = False
    ) -> bool:
        """Send message with reliability guarantees."""
        message_id = message.get('id') or self._generate_message_id()
        message['id'] = message_id
        
        message_state = MessageState(
            message_id=message_id,
            content=message,
            timestamp=datetime.now(),
            ack_required=require_ack
        )
        
        # Add to pending if connection not ready
        if self.state != ConnectionState.CONNECTED:
            if len(self.pending_messages) < self.config.max_pending_messages:
                self.pending_messages.append(message_state)
                logger.debug(f"Message queued: {message_id}")
            else:
                logger.warning(f"Pending message queue full, dropping: {message_id}")
            return False
        
        return await self._send_message_now(message_state)
    
    async def _send_message_now(self, message_state: MessageState) -> bool:
        """Send message immediately."""
        if not self.websocket or self.state != ConnectionState.CONNECTED:
            return False
        
        try:
            message_json = json.dumps(message_state.content)
            await self.websocket.send(message_json)
            
            self.metrics.message_count += 1
            
            if message_state.ack_required:
                self.sent_messages[message_state.message_id] = message_state
            
            logger.debug(f"Message sent: {message_state.message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message {message_state.message_id}: {e}")
            self.pending_messages.append(message_state)
            await self._handle_connection_error(e)
            return False
    
    async def _message_handler(self) -> None:
        """Handle incoming WebSocket messages."""
        while self.state == ConnectionState.CONNECTED and self.websocket:
            try:
                message_raw = await self.websocket.recv()
                message = json.loads(message_raw)
                
                await self._process_received_message(message)
                
            except Exception as e:
                logger.error(f"Message handling error: {e}")
                await self._handle_connection_error(e)
                break
    
    async def _process_received_message(self, message: Dict[str, Any]) -> None:
        """Process received message."""
        message_id = message.get('id')
        message_type = message.get('type')
        
        # Handle acknowledgments
        if message_type == 'ack' and message_id:
            await self._handle_acknowledgment(message_id)
            return
        
        # Handle pong responses
        if message_type == 'pong':
            self._handle_pong()
            return
        
        # Prevent duplicate processing
        if message_id and message_id in self.received_messages:
            logger.debug(f"Duplicate message ignored: {message_id}")
            return
        
        if message_id:
            self.received_messages.add(message_id)
            
            # Clean old received messages
            if len(self.received_messages) > 10000:
                # Keep only recent half
                recent_messages = list(self.received_messages)[-5000:]
                self.received_messages = set(recent_messages)
        
        # Send acknowledgment if required
        if message.get('ack_required'):
            await self._send_acknowledgment(message_id)
        
        # Process message
        if self.on_message:
            await self.on_message(self.connection_id, message)
    
    async def _handle_acknowledgment(self, message_id: str) -> None:
        """Handle message acknowledgment."""
        if message_id in self.sent_messages:
            message_state = self.sent_messages[message_id]
            message_state.acknowledged = True
            del self.sent_messages[message_id]
            
            logger.debug(f"Message acknowledged: {message_id}")
    
    async def _send_acknowledgment(self, message_id: str) -> None:
        """Send acknowledgment for received message."""
        ack_message = {
            'type': 'ack',
            'id': message_id,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            await self.websocket.send(json.dumps(ack_message))
        except Exception as e:
            logger.warning(f"Failed to send acknowledgment: {e}")
    
    async def _handle_connection_error(self, error: Exception) -> None:
        """Handle connection errors and trigger recovery."""
        self.last_error = error
        self.metrics.error_count += 1
        
        if self.state == ConnectionState.CONNECTED:
            self.state = ConnectionState.DISCONNECTED
            logger.warning(f"WebSocket connection lost: {self.connection_id}: {error}")
            
            # Start reconnection
            if self.reconnect_attempts < self.config.max_attempts:
                await self._start_reconnection(ReconnectionReason.CONNECTION_LOST)
            else:
                logger.error(f"Max reconnection attempts reached: {self.connection_id}")
                self.state = ConnectionState.FAILED
    
    async def _start_reconnection(self, reason: ReconnectionReason) -> None:
        """Start reconnection process."""
        if self.reconnect_task and not self.reconnect_task.done():
            return  # Already reconnecting
        
        self.state = ConnectionState.RECONNECTING
        self.reconnect_task = asyncio.create_task(
            self._reconnection_loop(reason)
        )
    
    async def _reconnection_loop(self, reason: ReconnectionReason) -> None:
        """Reconnection loop with exponential backoff."""
        logger.info(f"Starting reconnection: {self.connection_id} ({reason.value})")
        
        while (
            self.reconnect_attempts < self.config.max_attempts and
            self.state == ConnectionState.RECONNECTING
        ):
            # Calculate delay
            delay = min(
                self.config.initial_delay * (
                    self.config.backoff_multiplier ** self.reconnect_attempts
                ),
                self.config.max_delay
            )
            
            # Add jitter
            if self.config.jitter:
                import random
                delay *= (0.5 + random.random() * 0.5)
            
            logger.info(
                f"Reconnection attempt {self.reconnect_attempts + 1} "
                f"in {delay:.1f}s: {self.connection_id}"
            )
            
            await asyncio.sleep(delay)
            
            self.reconnect_attempts += 1
            self.last_reconnect_time = datetime.now()
            self.metrics.reconnect_count += 1
            
            # Attempt reconnection
            if await self.connect():
                logger.info(f"Reconnection successful: {self.connection_id}")
                return
        
        # Max attempts reached
        logger.error(f"Reconnection failed after {self.reconnect_attempts} attempts: {self.connection_id}")
        self.state = ConnectionState.FAILED
    
    async def _restore_pending_messages(self) -> None:
        """Restore pending messages after reconnection."""
        if not self.config.preserve_pending_messages:
            self.pending_messages.clear()
            return
        
        # Clean old messages
        cutoff_time = datetime.now() - timedelta(hours=self.config.message_retention_hours)
        self.pending_messages = [
            msg for msg in self.pending_messages
            if msg.timestamp > cutoff_time
        ]
        
        # Resend pending messages
        messages_to_send = self.pending_messages.copy()
        self.pending_messages.clear()
        
        for message_state in messages_to_send:
            await self._send_message_now(message_state)
        
        logger.info(f"Restored {len(messages_to_send)} pending messages: {self.connection_id}")
    
    async def _start_heartbeat(self) -> None:
        """Start heartbeat monitoring."""
        if self.heartbeat_task:
            return
        
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def _stop_heartbeat(self) -> None:
        """Stop heartbeat monitoring."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None
    
    async def _heartbeat_loop(self) -> None:
        """Heartbeat monitoring loop."""
        while self.state == ConnectionState.CONNECTED:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                if self.state != ConnectionState.CONNECTED:
                    break
                
                # Send ping
                ping_message = {
                    'type': 'ping',
                    'timestamp': datetime.now().isoformat()
                }
                
                self.metrics.last_ping = datetime.now()
                await self.websocket.send(json.dumps(ping_message))
                
                # Wait for pong (with timeout)
                await asyncio.sleep(5.0)
                
                # Check if pong received
                if self.metrics.last_pong and self.metrics.last_ping:
                    if self.metrics.last_pong < self.metrics.last_ping:
                        self.missed_heartbeats += 1
                    else:
                        self.missed_heartbeats = 0
                        # Calculate latency
                        latency = (self.metrics.last_pong - self.metrics.last_ping).total_seconds() * 1000
                        self.metrics.latency_ms = latency
                
                # Check for missed heartbeats
                if self.missed_heartbeats >= self.max_missed_heartbeats:
                    logger.warning(f"Heartbeat timeout: {self.connection_id}")
                    await self._handle_connection_error(Exception("Heartbeat timeout"))
                    break
                    
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await self._handle_connection_error(e)
                break
    
    def _handle_pong(self) -> None:
        """Handle pong response."""
        self.metrics.last_pong = datetime.now()
        self.missed_heartbeats = 0
    
    def _generate_message_id(self) -> str:
        """Generate unique message ID."""
        import uuid
        return str(uuid.uuid4())
    
    def get_status(self) -> Dict[str, Any]:
        """Get connection status."""
        return {
            'connection_id': self.connection_id,
            'state': self.state.value,
            'reconnect_attempts': self.reconnect_attempts,
            'pending_messages': len(self.pending_messages),
            'sent_unacked': len(self.sent_messages),
            'metrics': {
                'message_count': self.metrics.message_count,
                'error_count': self.metrics.error_count,
                'reconnect_count': self.metrics.reconnect_count,
                'latency_ms': self.metrics.latency_ms,
                'missed_heartbeats': self.missed_heartbeats
            },
            'last_error': str(self.last_error) if self.last_error else None
        }


class WebSocketRecoveryManager:
    """Manager for multiple WebSocket connections with recovery."""
    
    def __init__(self):
        """Initialize recovery manager."""
        self.connections: Dict[str, WebSocketConnectionManager] = {}
        self.default_config = ReconnectionConfig()
    
    async def create_connection(
        self,
        connection_id: str,
        url: str,
        config: Optional[ReconnectionConfig] = None
    ) -> WebSocketConnectionManager:
        """Create managed WebSocket connection."""
        if connection_id in self.connections:
            await self.remove_connection(connection_id)
        
        manager = WebSocketConnectionManager(
            connection_id, url, config or self.default_config
        )
        
        self.connections[connection_id] = manager
        logger.info(f"Created WebSocket connection manager: {connection_id}")
        
        return manager
    
    async def remove_connection(self, connection_id: str) -> None:
        """Remove and cleanup connection."""
        if connection_id in self.connections:
            manager = self.connections[connection_id]
            await manager.disconnect("removed")
            del self.connections[connection_id]
            logger.info(f"Removed WebSocket connection: {connection_id}")
    
    async def recover_all_connections(self) -> Dict[str, bool]:
        """Attempt recovery for all failed connections."""
        results = {}
        
        for connection_id, manager in self.connections.items():
            if manager.state in [ConnectionState.FAILED, ConnectionState.DISCONNECTED]:
                try:
                    success = await manager.connect()
                    results[connection_id] = success
                except Exception as e:
                    logger.error(f"Recovery failed for {connection_id}: {e}")
                    results[connection_id] = False
        
        return results
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all connections."""
        return {
            connection_id: manager.get_status()
            for connection_id, manager in self.connections.items()
        }
    
    async def cleanup_all(self) -> None:
        """Cleanup all connections."""
        for connection_id in list(self.connections.keys()):
            await self.remove_connection(connection_id)


# Global WebSocket recovery manager
websocket_recovery_manager = WebSocketRecoveryManager()