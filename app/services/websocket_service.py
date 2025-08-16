"""WebSocket Service Implementation

Provides WebSocket functionality through the IWebSocketService interface.
"""

from typing import Dict, Any, List, Optional
from app.services.service_locator import IWebSocketService
from app.ws_manager import manager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketService(IWebSocketService):
    """WebSocket service implementation using the existing ws_manager."""
    
    def __init__(self):
        self.manager = manager
    
    async def send_message(self, user_id: str, message: Dict[str, Any]):
        """Send a message to a specific user via WebSocket."""
        try:
            await self.manager.send_message(user_id, message)
            logger.debug(f"Sent message to user {user_id}: {message.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            raise
    
    async def broadcast(self, message: Dict[str, Any], exclude_user_ids: list = None):
        """Broadcast a message to all connected users, optionally excluding some."""
        try:
            if exclude_user_ids:
                # Use the broadcasting manager to send to specific users
                connected_users = list(self.manager.active_connections.keys())
                target_users = [uid for uid in connected_users if uid not in exclude_user_ids]
                for user_id in target_users:
                    await self.manager.send_message(user_id, message)
            else:
                # Broadcast to all connected users
                await self.manager.broadcast_message(message)
            logger.debug(f"Broadcasted message: {message.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to broadcast message: {e}")
            raise