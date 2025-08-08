import asyncio
import json
import logging
from typing import Dict, Any, List

from fastapi import WebSocket, WebSocketDisconnect

from app.schemas import WebSocketMessage, WebSocketError

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id in self.active_connections:
            logger.warning(f"User {user_id} already has an active WebSocket connection. Closing the old one.")
            await self.active_connections[user_id].close(code=1000, reason="New connection established")
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connection established for user {user_id}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket connection closed for user {user_id}")

    async def send_to_client(self, user_id: str, message: WebSocketMessage):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message.dict())
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}", exc_info=True)
        else:
            logger.warning(f"Attempted to send message to disconnected user: {user_id}")

    async def broadcast(self, message: WebSocketMessage):
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message.dict())
            except Exception as e:
                logger.error(f"Failed to broadcast message to user {user_id}: {e}", exc_info=True)

    async def send_error(self, user_id: str, error_message: str):
        error_payload = WebSocketError(message=error_message)
        await self.send_to_client(user_id, WebSocketMessage(type="error", payload=error_payload))


manager = WebSocketManager()