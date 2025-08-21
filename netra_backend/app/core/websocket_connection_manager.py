"""WebSocket connection manager with recovery capabilities.

Manages individual WebSocket connections with automatic reconnection,
message reliability, and state preservation.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from app.logging_config import central_logger
from netra_backend.app.websocket_recovery_types import (
    ConnectionState,
    ReconnectionReason,
    ConnectionMetrics,
    ReconnectionConfig
)
from netra_backend.app.websocket_message_handler import WebSocketMessageHandler
from netra_backend.app.websocket_heartbeat_manager import WebSocketHeartbeatManager
from netra_backend.app.websocket_reconnection_handler import WebSocketReconnectionHandler, WebSocketMessageRestorer

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
        self._init_basic_properties(connection_id, url, config)
        self._initialize_state()
        self._initialize_components()
        self._setup_event_handlers()
    
    def _init_basic_properties(self, connection_id: str, url: str, config: Optional[ReconnectionConfig]) -> None:
        """Initialize basic connection properties."""
        self.connection_id = connection_id
        self.url = url
        self.config = config or ReconnectionConfig()
    
    def _initialize_state(self) -> None:
        """Initialize connection state variables."""
        self.state = ConnectionState.DISCONNECTED
        self.websocket: Optional[Any] = None
        self.last_error: Optional[Exception] = None
        self.metrics = ConnectionMetrics(
            connection_id=self.connection_id,
            connect_time=datetime.now()
        )
    
    def _initialize_components(self) -> None:
        """Initialize helper components."""
        self.message_handler = WebSocketMessageHandler()
        self.heartbeat_manager = WebSocketHeartbeatManager(self.connection_id, self.metrics)
        self.reconnection_handler = WebSocketReconnectionHandler(self.connection_id, self.config)
        self.message_restorer = WebSocketMessageRestorer(self.config)
    
    def _setup_event_handlers(self) -> None:
        """Setup event handlers for components."""
        self._setup_internal_handlers()
        self._setup_external_handlers()
    
    def _setup_internal_handlers(self) -> None:
        """Setup internal component event handlers."""
        self.heartbeat_manager.on_heartbeat_timeout = self._handle_connection_error
        self.reconnection_handler.on_reconnect_success = self._on_reconnection_success
        self.reconnection_handler.on_reconnect_failure = self._on_reconnection_failure
    
    def _setup_external_handlers(self) -> None:
        """Setup external event handler placeholders."""
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self.on_message: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
    
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
            await self._establish_websocket_connection()
            return await self._handle_successful_connection()
        except Exception as e:
            return await self._handle_connection_failure(e)
    
    async def _establish_websocket_connection(self) -> None:
        """Establish WebSocket connection with timeout."""
        import websockets
        self.websocket = await asyncio.wait_for(
            websockets.connect(self.url),
            timeout=self.config.timeout_seconds
        )
    
    async def _handle_successful_connection(self) -> bool:
        """Handle successful WebSocket connection."""
        self._update_connection_state()
        await self._setup_connection()
        await self._notify_connection_success()
        logger.info(f"WebSocket connected: {self.connection_id}")
        return True
    
    def _update_connection_state(self) -> None:
        """Update connection state after successful connection."""
        self.state = ConnectionState.CONNECTED
        self.metrics.connect_time = datetime.now()
        self.reconnection_handler.reset_attempts()
        self.last_error = None
    
    async def _setup_connection(self) -> None:
        """Setup connection handlers and restore state."""
        asyncio.create_task(self._message_handler_loop())
        await self.heartbeat_manager.start_heartbeat(self.websocket, self._is_connected)
        await self.message_restorer.restore_pending_messages(
            self.message_handler.pending_messages, self._send_message_now
        )
    
    def _is_connected(self) -> bool:
        """Check if connection is in connected state."""
        return self.state == ConnectionState.CONNECTED
    
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
        if self.on_error:
            await self.on_error(self.connection_id, error)
        return False
    
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
        await self.heartbeat_manager.stop_heartbeat()
        self.reconnection_handler.cancel_reconnection()
        await self._close_websocket_safely()
    
    async def _close_websocket_safely(self) -> None:
        """Close WebSocket connection safely."""
        if self.websocket:
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
        message_id = message.get('id') or self.message_handler.generate_message_id()
        message['id'] = message_id
        message_state = self.message_handler.create_message_state(message, message_id, require_ack)
        return await self._process_message_send(message_state)
    
    async def _process_message_send(self, message_state) -> bool:
        """Process message sending with queuing if needed."""
        if self.state != ConnectionState.CONNECTED:
            return self.message_handler.queue_pending_message(message_state, self.config.max_pending_messages)
        return await self._send_message_now(message_state)
    
    async def _send_message_now(self, message_state) -> bool:
        """Send message immediately."""
        if not self.websocket or self.state != ConnectionState.CONNECTED:
            return False
        try:
            await self.message_handler.execute_message_send(self.websocket, message_state)
            self.metrics.message_count += 1
            return True
        except Exception as e:
            logger.error(f"Failed to send message {message_state.message_id}: {e}")
            self.message_handler.pending_messages.append(message_state)
            await self._handle_connection_error(e)
            return False
    
    async def _message_handler_loop(self) -> None:
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
        message_type = message.get('type')
        message_id = message.get('id')
        if message_type == 'pong':
            self.heartbeat_manager.handle_pong()
            return
        if message.get('ack_required'):
            await self.message_handler.send_acknowledgment(self.websocket, message_id)
        await self.message_handler.process_received_message(message, self.connection_id)
        self.message_handler.on_message = self.on_message
    
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
        if self.reconnection_handler.is_within_limits():
            self.state = ConnectionState.RECONNECTING
            await self.reconnection_handler.start_reconnection(
                ReconnectionReason.CONNECTION_LOST, self.connect
            )
        else:
            logger.error(f"Max reconnection attempts reached: {self.connection_id}")
            self.state = ConnectionState.FAILED
    
    async def _on_reconnection_success(self) -> None:
        """Handle successful reconnection."""
        self.metrics.reconnect_count += 1
    
    async def _on_reconnection_failure(self) -> None:
        """Handle failed reconnection."""
        self.state = ConnectionState.FAILED
    
    def get_status(self) -> Dict[str, Any]:
        """Get connection status."""
        return {
            'connection_id': self.connection_id,
            'state': self.state.value,
            'reconnect_attempts': self.reconnection_handler.get_attempts(),
            'pending_messages': self.message_handler.get_pending_count(),
            'sent_unacked': self.message_handler.get_unacked_count(),
            'metrics': {
                'message_count': self.metrics.message_count,
                'error_count': self.metrics.error_count,
                'reconnect_count': self.metrics.reconnect_count,
                'latency_ms': self.metrics.latency_ms,
                'missed_heartbeats': self.heartbeat_manager.get_missed_heartbeats()
            },
            'last_error': str(self.last_error) if self.last_error else None
        }