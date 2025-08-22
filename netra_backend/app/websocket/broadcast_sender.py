"""WebSocket Broadcast Message Sender.

Handles the low-level message sending to individual connections.
"""

from typing import Any, Dict, Union

from starlette.websockets import WebSocketState

from netra_backend.app.core.json_utils import prepare_websocket_message
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket.connection import ConnectionInfo, ConnectionManager

logger = central_logger.get_logger(__name__)


class BroadcastSender:
    """Handles low-level message sending to WebSocket connections."""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    async def send_to_connection(self, conn_info: ConnectionInfo, message: Union[Dict[str, Any], Any]) -> bool:
        """Send a message to a specific connection.
        
        Args:
            conn_info: Connection to send to
            message: Message to send
            
        Returns:
            True if message was sent successfully
        """
        if not self._is_connection_ready(conn_info):
            return False
        return await self._execute_connection_send(conn_info, message)
    
    async def _execute_connection_send(self, conn_info: ConnectionInfo, message) -> bool:
        """Execute connection send with comprehensive error handling."""
        try:
            return await self._perform_message_send(conn_info, message)
        except (RuntimeError, ConnectionError) as e:
            self._handle_connection_error(conn_info, e)
            return False
        except Exception as e:
            self._handle_unexpected_error(conn_info, e)
            return False

    def _is_connection_ready(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection is ready for sending."""
        if not self._check_connection_not_closing(conn_info):
            return False
        return self._check_websocket_states(conn_info)
    
    def _check_connection_not_closing(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection is not marked as closing."""
        if conn_info.is_closing:
            logger.debug(f"Connection {conn_info.connection_id} is closing, skipping send")
            return False
        return True
    
    def _check_websocket_states(self, conn_info: ConnectionInfo) -> bool:
        """Check WebSocket client and application states."""
        ws_state = conn_info.websocket.client_state
        app_state = conn_info.websocket.application_state
        return self._validate_connection_states(conn_info, ws_state, app_state)
    
    def _validate_connection_states(self, conn_info: ConnectionInfo, ws_state, app_state) -> bool:
        """Validate WebSocket connection states."""
        if not self._check_client_state(conn_info, ws_state):
            return False
        return self._check_application_state(conn_info, app_state)
    
    def _check_client_state(self, conn_info: ConnectionInfo, ws_state) -> bool:
        """Check WebSocket client state."""
        if ws_state != WebSocketState.CONNECTED:
            logger.debug(f"Connection {conn_info.connection_id} not in CONNECTED state: {ws_state.name}")
            return False
        return True
    
    def _check_application_state(self, conn_info: ConnectionInfo, app_state) -> bool:
        """Check WebSocket application state."""
        if app_state != WebSocketState.CONNECTED:
            logger.debug(f"Connection {conn_info.connection_id} application state not connected: {app_state.name}")
            return False
        return True

    async def _perform_message_send(self, conn_info: ConnectionInfo, message: Union[Dict[str, Any], Any]) -> bool:
        """Perform actual message sending."""
        prepared_message = prepare_websocket_message(message)
        await conn_info.websocket.send_json(prepared_message)
        return True

    def _handle_connection_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
        """Handle connection-related errors."""
        error_msg = str(error)
        self._log_connection_error(conn_info, error, error_msg)
    
    def _log_connection_error(self, conn_info: ConnectionInfo, error: Exception, error_msg: str) -> None:
        """Log connection error with appropriate level."""
        if self._is_close_related_error(error_msg):
            self._log_close_error(conn_info, error, error_msg)
        else:
            logger.warning(f"Error sending to connection {conn_info.connection_id}: {error}")
    
    def _is_close_related_error(self, error_msg: str) -> bool:
        """Check if error is related to connection closing."""
        return ("Cannot call \"send\" once a close message has been sent" in error_msg or
                "Cannot call" in error_msg or "close" in error_msg.lower())
    
    def _log_close_error(self, conn_info: ConnectionInfo, error: Exception, error_msg: str) -> None:
        """Log connection close related errors."""
        if "Cannot call \"send\" once a close message has been sent" in error_msg:
            logger.debug(f"Connection {conn_info.connection_id} already closing, skipping send")
        else:
            logger.debug(f"Connection {conn_info.connection_id} closed: {error}")

    def _handle_unexpected_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
        """Handle unexpected errors during message sending."""
        logger.error(f"Unexpected error sending to connection {conn_info.connection_id}: {error}")