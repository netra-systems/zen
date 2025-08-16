"""WebSocket connection manager with recovery capabilities.

Manages individual WebSocket connections with automatic reconnection,
message reliability, and state preservation.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

from app.logging_config import central_logger
from .websocket_recovery_types import (
    ConnectionState,
    ReconnectionReason,
    ConnectionMetrics,
    MessageState,
    ReconnectionConfig
)

logger = central_logger.get_logger(__name__)


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
        self._initialize_state()
        self._initialize_event_handlers()
        self._initialize_heartbeat_config()
    
    def _initialize_state(self) -> None:
        """Initialize connection state variables."""
        self.state = ConnectionState.DISCONNECTED
        self.websocket: Optional[Any] = None
        self.last_error: Optional[Exception] = None
        self.reconnect_attempts = 0
        self.last_reconnect_time: Optional[datetime] = None
        self.reconnect_task: Optional[asyncio.Task] = None
    
    def _initialize_message_state(self) -> None:
        """Initialize message state management."""
        self.pending_messages: List[MessageState] = []
        self.sent_messages: Dict[str, MessageState] = {}
        self.received_messages: Set[str] = set()
        self.metrics = ConnectionMetrics(
            connection_id=self.connection_id,
            connect_time=datetime.now()
        )
    
    def _initialize_event_handlers(self) -> None:
        """Initialize event handler callbacks."""
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self.on_message: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
    
    def _initialize_heartbeat_config(self) -> None:
        """Initialize heartbeat monitoring configuration."""
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
        return await self._attempt_connection()
    
    async def _attempt_connection(self) -> bool:
        """Attempt WebSocket connection establishment."""
        try:
            import websockets
            self.websocket = await asyncio.wait_for(
                websockets.connect(self.url),
                timeout=self.config.timeout_seconds
            )
            return await self._handle_successful_connection()
        except Exception as e:
            return await self._handle_connection_failure(e)
    
    async def _handle_successful_connection(self) -> bool:
        """Handle successful WebSocket connection."""
        self.state = ConnectionState.CONNECTED
        self.metrics.connect_time = datetime.now()
        self.reconnect_attempts = 0
        self.last_error = None
        await self._setup_connection_handlers()
        await self._restore_pending_messages()
        await self._notify_connection_success()
        logger.info(f"WebSocket connected: {self.connection_id}")
        return True
    
    async def _setup_connection_handlers(self) -> None:
        """Setup message handling and heartbeat."""
        asyncio.create_task(self._message_handler())
        await self._start_heartbeat()
    
    async def _notify_connection_success(self) -> None:
        """Notify external handlers of successful connection."""
        if self.on_connect:
            await self.on_connect(self.connection_id)
    
    async def _handle_connection_failure(self, error: Exception) -> bool:
        """Handle connection failure."""
        self.state = ConnectionState.FAILED
        self.last_error = error
        self.metrics.error_count += 1
        logger.error(f"WebSocket connection failed: {self.connection_id}: {error}")
        await self._notify_connection_error(error)
        return False
    
    async def _notify_connection_error(self, error: Exception) -> None:
        """Notify external handlers of connection error."""
        if self.on_error:
            await self.on_error(self.connection_id, error)
    
    async def disconnect(self, reason: str = "manual") -> None:
        """Gracefully disconnect WebSocket."""
        if self.state == ConnectionState.DISCONNECTED:
            return
        logger.info(f"Disconnecting WebSocket: {self.connection_id} ({reason})")
        self.state = ConnectionState.CLOSING
        await self._cleanup_connection()
        await self._finalize_disconnection(reason)
    
    async def _cleanup_connection(self) -> None:
        """Cleanup connection resources."""
        await self._stop_heartbeat()
        if self.reconnect_task:
            self.reconnect_task.cancel()
        if self.websocket:
            await self._close_websocket_safely()
    
    async def _close_websocket_safely(self) -> None:
        """Close WebSocket connection safely."""
        try:
            await self.websocket.close()
        except Exception as e:
            logger.warning(f"Error closing WebSocket: {e}")
    
    async def _finalize_disconnection(self, reason: str) -> None:
        """Finalize disconnection process."""
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
        message_state = self._create_message_state(message, message_id, require_ack)
        return await self._process_message_send(message_state)
    
    def _create_message_state(self, message: Dict[str, Any], message_id: str, require_ack: bool) -> MessageState:
        """Create message state object."""
        return MessageState(
            message_id=message_id,
            content=message,
            timestamp=datetime.now(),
            ack_required=require_ack
        )
    
    async def _process_message_send(self, message_state: MessageState) -> bool:
        """Process message sending with queuing if needed."""
        if self.state != ConnectionState.CONNECTED:
            return self._queue_pending_message(message_state)
        return await self._send_message_now(message_state)
    
    def _queue_pending_message(self, message_state: MessageState) -> bool:
        """Queue message for later sending."""
        if len(self.pending_messages) < self.config.max_pending_messages:
            self.pending_messages.append(message_state)
            logger.debug(f"Message queued: {message_state.message_id}")
            return False
        else:
            logger.warning(f"Pending message queue full, dropping: {message_state.message_id}")
            return False
    
    async def _send_message_now(self, message_state: MessageState) -> bool:
        """Send message immediately."""
        if not self.websocket or self.state != ConnectionState.CONNECTED:
            return False
        try:
            return await self._execute_message_send(message_state)
        except Exception as e:
            return await self._handle_send_failure(message_state, e)
    
    async def _execute_message_send(self, message_state: MessageState) -> bool:
        """Execute the actual message send."""
        message_json = json.dumps(message_state.content)
        await self.websocket.send(message_json)
        self.metrics.message_count += 1
        if message_state.ack_required:
            self.sent_messages[message_state.message_id] = message_state
        logger.debug(f"Message sent: {message_state.message_id}")
        return True
    
    async def _handle_send_failure(self, message_state: MessageState, error: Exception) -> bool:
        """Handle message send failure."""
        logger.error(f"Failed to send message {message_state.message_id}: {error}")
        self.pending_messages.append(message_state)
        await self._handle_connection_error(error)
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
        if message_type == 'ack' and message_id:
            await self._handle_acknowledgment(message_id)
            return
        if message_type == 'pong':
            self._handle_pong()
            return
        await self._handle_regular_message(message, message_id)
    
    async def _handle_regular_message(self, message: Dict[str, Any], message_id: str) -> None:
        """Handle regular incoming message."""
        if self._is_duplicate_message(message_id):
            return
        self._record_received_message(message_id)
        if message.get('ack_required'):
            await self._send_acknowledgment(message_id)
        if self.on_message:
            await self.on_message(self.connection_id, message)
    
    def _is_duplicate_message(self, message_id: str) -> bool:
        """Check if message is duplicate."""
        if message_id and message_id in self.received_messages:
            logger.debug(f"Duplicate message ignored: {message_id}")
            return True
        return False
    
    def _record_received_message(self, message_id: str) -> None:
        """Record received message ID."""
        if message_id:
            self.received_messages.add(message_id)
            if len(self.received_messages) > 10000:
                recent_messages = list(self.received_messages)[-5000:]
                self.received_messages = set(recent_messages)
    
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
            await self._initiate_reconnection()
    
    async def _initiate_reconnection(self) -> None:
        """Initiate reconnection if within limits."""
        if self.reconnect_attempts < self.config.max_attempts:
            await self._start_reconnection(ReconnectionReason.CONNECTION_LOST)
        else:
            logger.error(f"Max reconnection attempts reached: {self.connection_id}")
            self.state = ConnectionState.FAILED
    
    async def _start_reconnection(self, reason: ReconnectionReason) -> None:
        """Start reconnection process."""
        if self.reconnect_task and not self.reconnect_task.done():
            return
        self.state = ConnectionState.RECONNECTING
        self.reconnect_task = asyncio.create_task(
            self._reconnection_loop(reason)
        )
    
    async def _reconnection_loop(self, reason: ReconnectionReason) -> None:
        """Reconnection loop with exponential backoff."""
        logger.info(f"Starting reconnection: {self.connection_id} ({reason.value})")
        while self._should_continue_reconnecting():
            delay = self._calculate_reconnection_delay()
            logger.info(
                f"Reconnection attempt {self.reconnect_attempts + 1} "
                f"in {delay:.1f}s: {self.connection_id}"
            )
            await asyncio.sleep(delay)
            await self._execute_reconnection_attempt()
            if self.state == ConnectionState.CONNECTED:
                logger.info(f"Reconnection successful: {self.connection_id}")
                return
        logger.error(f"Reconnection failed after {self.reconnect_attempts} attempts: {self.connection_id}")
        self.state = ConnectionState.FAILED
    
    def _should_continue_reconnecting(self) -> bool:
        """Check if reconnection should continue."""
        return (
            self.reconnect_attempts < self.config.max_attempts and
            self.state == ConnectionState.RECONNECTING
        )
    
    def _calculate_reconnection_delay(self) -> float:
        """Calculate delay for next reconnection attempt."""
        delay = min(
            self.config.initial_delay * (
                self.config.backoff_multiplier ** self.reconnect_attempts
            ),
            self.config.max_delay
        )
        if self.config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        return delay
    
    async def _execute_reconnection_attempt(self) -> None:
        """Execute a single reconnection attempt."""
        self.reconnect_attempts += 1
        self.last_reconnect_time = datetime.now()
        self.metrics.reconnect_count += 1
        await self.connect()
    
    async def _restore_pending_messages(self) -> None:
        """Restore pending messages after reconnection."""
        if not self.config.preserve_pending_messages:
            self.pending_messages.clear()
            return
        await self._cleanup_old_pending_messages()
        await self._resend_pending_messages()
    
    async def _cleanup_old_pending_messages(self) -> None:
        """Clean old pending messages based on retention policy."""
        cutoff_time = datetime.now() - timedelta(hours=self.config.message_retention_hours)
        self.pending_messages = [
            msg for msg in self.pending_messages
            if msg.timestamp > cutoff_time
        ]
    
    async def _resend_pending_messages(self) -> None:
        """Resend all pending messages."""
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
                await self._send_heartbeat_ping()
                await self._check_heartbeat_response()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await self._handle_connection_error(e)
                break
    
    async def _send_heartbeat_ping(self) -> None:
        """Send heartbeat ping."""
        ping_message = {
            'type': 'ping',
            'timestamp': datetime.now().isoformat()
        }
        self.metrics.last_ping = datetime.now()
        await self.websocket.send(json.dumps(ping_message))
        await asyncio.sleep(5.0)
    
    async def _check_heartbeat_response(self) -> None:
        """Check heartbeat response and handle timeouts."""
        if self.metrics.last_pong and self.metrics.last_ping:
            if self.metrics.last_pong < self.metrics.last_ping:
                self.missed_heartbeats += 1
            else:
                self.missed_heartbeats = 0
                latency = (self.metrics.last_pong - self.metrics.last_ping).total_seconds() * 1000
                self.metrics.latency_ms = latency
        if self.missed_heartbeats >= self.max_missed_heartbeats:
            logger.warning(f"Heartbeat timeout: {self.connection_id}")
            await self._handle_connection_error(Exception("Heartbeat timeout"))
    
    def _handle_pong(self) -> None:
        """Handle pong response."""
        self.metrics.last_pong = datetime.now()
        self.missed_heartbeats = 0
    
    def _generate_message_id(self) -> str:
        """Generate unique message ID."""
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