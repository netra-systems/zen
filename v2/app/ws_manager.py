
import asyncio
import json
import logging
from typing import Dict, Any, List

from fastapi import WebSocket, WebSocketDisconnect

from app.schemas import WebSocketMessage

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id in self.active_connections:
            await self.active_connections[user_id].close(code=1000, reason="New connection established")
            logger.warning(f"Closing existing WebSocket connection for user {user_id} to establish a new one.")
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_to_client(self, user_id: str, message: WebSocketMessage):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message.dict())
        else:
            logger.warning(f"Attempted to send message to disconnected user: {user_id}")

    async def broadcast(self, message: WebSocketMessage):
        for connection in self.active_connections.values():
            await connection.send_json(message.dict())

    async def send_error(self, user_id: str, error_message: str):
        from app.schemas import WebSocketError

        await self.send_to_client(user_id, WebSocketMessage(type="error", payload=WebSocketError(message=error_message)))


manager = WebSocketManager()
