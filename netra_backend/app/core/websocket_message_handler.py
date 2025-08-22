"""WebSocket message handling utilities.

Provides message processing, acknowledgment handling, and message state
management for WebSocket connections.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from netra_backend.app.core.websocket_recovery_types import MessageState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketMessageHandler:
    """Handles WebSocket message processing and state management."""
    
    def __init__(self):
        """Initialize message handler."""
        self.pending_messages: List[MessageState] = []
        self.sent_messages: Dict[str, MessageState] = {}
        self.received_messages: Set[str] = set()
        self.on_message: Optional[Callable] = None
    
    def create_message_state(self, message: Dict[str, Any], message_id: str, require_ack: bool) -> MessageState:
        """Create message state object."""
        return MessageState(
            message_id=message_id,
            content=message,
            timestamp=datetime.now(),
            ack_required=require_ack
        )
    
    def queue_pending_message(self, message_state: MessageState, max_pending: int) -> bool:
        """Queue message for later sending."""
        if self._can_queue_message(max_pending):
            return self._add_to_queue(message_state)
        return self._handle_queue_full(message_state)
    
    def _can_queue_message(self, max_pending: int) -> bool:
        """Check if message can be queued."""
        return len(self.pending_messages) < max_pending
    
    def _add_to_queue(self, message_state: MessageState) -> bool:
        """Add message to pending queue."""
        self.pending_messages.append(message_state)
        logger.debug(f"Message queued: {message_state.message_id}")
        return False
    
    def _handle_queue_full(self, message_state: MessageState) -> bool:
        """Handle case when queue is full."""
        logger.warning(f"Pending message queue full, dropping: {message_state.message_id}")
        return False
    
    async def execute_message_send(self, websocket, message_state: MessageState) -> bool:
        """Execute the actual message send."""
        message_json = json.dumps(message_state.content)
        await websocket.send(message_json)
        self._track_sent_message_if_required(message_state)
        logger.debug(f"Message sent: {message_state.message_id}")
        return True
    
    def _track_sent_message_if_required(self, message_state: MessageState) -> None:
        """Track sent message if acknowledgment is required."""
        if message_state.ack_required:
            self.sent_messages[message_state.message_id] = message_state
    
    async def process_received_message(self, message: Dict[str, Any], connection_id: str) -> None:
        """Process received message."""
        message_id = message.get('id')
        message_type = message.get('type')
        
        if self._is_ack_message(message_type, message_id):
            self.handle_acknowledgment(message_id)
            return
        
        if self._is_pong_message(message_type):
            return  # Handled by heartbeat manager
        
        await self._handle_regular_message(message, message_id, connection_id)
    
    def _is_ack_message(self, message_type: str, message_id: str) -> bool:
        """Check if message is an acknowledgment."""
        return message_type == 'ack' and message_id is not None
    
    def _is_pong_message(self, message_type: str) -> bool:
        """Check if message is a pong response."""
        return message_type == 'pong'
    
    async def _handle_regular_message(self, message: Dict[str, Any], message_id: str, connection_id: str) -> None:
        """Handle regular incoming message."""
        if self._is_duplicate_message(message_id):
            return
        self._record_received_message(message_id)
        if self.on_message:
            await self.on_message(connection_id, message)
    
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
    
    def handle_acknowledgment(self, message_id: str) -> None:
        """Handle message acknowledgment."""
        if message_id in self.sent_messages:
            message_state = self.sent_messages[message_id]
            message_state.acknowledged = True
            del self.sent_messages[message_id]
            logger.debug(f"Message acknowledged: {message_id}")
    
    async def send_acknowledgment(self, websocket, message_id: str) -> None:
        """Send acknowledgment for received message."""
        ack_message = self._create_ack_message(message_id)
        await self._send_ack_message(websocket, ack_message)
    
    def _create_ack_message(self, message_id: str) -> Dict[str, Any]:
        """Create acknowledgment message."""
        return {
            'type': 'ack',
            'id': message_id,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _send_ack_message(self, websocket, ack_message: Dict[str, Any]) -> None:
        """Send acknowledgment message through websocket."""
        try:
            await websocket.send(json.dumps(ack_message))
        except Exception as e:
            logger.warning(f"Failed to send acknowledgment: {e}")
    
    def generate_message_id(self) -> str:
        """Generate unique message ID."""
        return str(uuid.uuid4())
    
    def get_pending_count(self) -> int:
        """Get count of pending messages."""
        return len(self.pending_messages)
    
    def get_unacked_count(self) -> int:
        """Get count of unacknowledged messages."""
        return len(self.sent_messages)
    
    def clear_pending_messages(self) -> None:
        """Clear all pending messages."""
        self.pending_messages.clear()
    
    def get_pending_messages_copy(self) -> List[MessageState]:
        """Get copy of pending messages."""
        return self.pending_messages.copy()