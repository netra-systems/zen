"""Connection message handling operations."""

import time
from datetime import datetime, timezone
from typing import Optional

from app.logging_config import central_logger
from app.core.json_utils import prepare_websocket_message

logger = central_logger.get_logger(__name__)


class ConnectionMessageHandler:
    """Handles message sending and receiving for connections."""
    
    def __init__(self, connection_manager, message_handler, message_router, 
                 reliability, connection_timeouts, connection_timeout):
        """Initialize message handler."""
        self.connection_manager = connection_manager
        self.message_handler = message_handler
        self.message_router = message_router
        self.reliability = reliability
        self.connection_timeouts = connection_timeouts
        self.connection_timeout = connection_timeout
    
    async def handle_message(self, connection_id: str, raw_message: str) -> bool:
        """Handle incoming message from connection."""
        conn_info = self._validate_connection(connection_id)
        if not conn_info:
            return False
        
        self._update_connection_activity(conn_info)
        success = await self._process_message(raw_message, conn_info)
        
        if success:
            self._handle_success(connection_id)
        
        return success
    
    def _validate_connection(self, connection_id: str):
        """Validate connection exists and return connection info."""
        conn_info = self.connection_manager.get_connection_by_id(connection_id)
        if not conn_info:
            logger.warning(f"Received message from unknown connection: {connection_id}")
        return conn_info
    
    def _update_connection_activity(self, conn_info) -> None:
        """Update connection's last activity timestamp."""
        conn_info.last_activity = datetime.now(timezone.utc)
    
    async def _process_message(self, raw_message: str, conn_info) -> bool:
        """Process message through reliable handler."""
        return await self.message_handler.handle_message(
            raw_message,
            conn_info,
            self.message_router.route_message
        )
    
    def _handle_success(self, connection_id: str) -> None:
        """Handle successful message processing by updating timeout."""
        self.connection_timeouts[connection_id] = time.time() + self.connection_timeout
    
    async def send_message(self, connection_id: str, message: dict) -> bool:
        """Send message to connection with reliability protection."""
        try:
            return await self.reliability.execute_safely(
                lambda: self._execute_message_send(connection_id, message),
                "send_message",
                fallback=lambda: self._handle_send_failure(connection_id),
                timeout=5.0
            )
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            return False
    
    async def _execute_message_send(self, connection_id: str, message: dict) -> bool:
        """Execute the message sending process."""
        conn_info = self._validate_connection_for_send(connection_id)
        await self._send_prepared_message(conn_info, message)
        return True
    
    def _validate_connection_for_send(self, connection_id: str):
        """Validate connection exists and is alive for sending."""
        conn_info = self.connection_manager.get_connection_by_id(connection_id)
        if not conn_info:
            raise ValueError(f"Connection {connection_id} not found")
        if not self.connection_manager.is_connection_alive(conn_info):
            raise ConnectionError(f"Connection {connection_id} is not alive")
        return conn_info
    
    async def _send_prepared_message(self, conn_info, message: dict) -> None:
        """Send prepared message to connection."""
        prepared_message = prepare_websocket_message(message)
        await conn_info.websocket.send_json(prepared_message)
    
    async def _handle_send_failure(self, connection_id: str) -> bool:
        """Handle message send failure by removing connection."""
        logger.warning(f"Failed to send message to connection {connection_id}")
        # Note: This would need access to lifecycle manager to remove connection
        return False
    
    async def broadcast_message(self, message: dict, user_filter: Optional[str] = None, 
                               send_message_callback=None) -> int:
        """Broadcast message to multiple connections."""
        sent_count = 0
        connections = self.connection_manager.get_all_connections()
        
        for conn_info in connections:
            # Apply user filter if specified
            if user_filter and conn_info.user_id != user_filter:
                continue
            
            if send_message_callback:
                success = await send_message_callback(conn_info.connection_id, message)
            else:
                success = await self.send_message(conn_info.connection_id, message)
            
            if success:
                sent_count += 1
        
        return sent_count
    
    def register_message_handler(self, message_type: str, handler):
        """Register a message handler for a specific type."""
        self.message_router.register_handler(message_type, handler)
    
    def register_fallback_handler(self, handler):
        """Register a fallback message handler."""
        self.message_router.register_fallback_handler(handler)