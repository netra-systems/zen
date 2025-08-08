import asyncio
import json
import logging
import uuid
from typing import Dict, Any, List

from fastapi import WebSocket, WebSocketDisconnect

from app.schemas import WebSocketMessage, WebSocketError
from app.redis_manager import redis_manager

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.server_id = uuid.uuid4().hex
        self.redis = None
        self.pubsub = None
        self.pubsub_task = None

    async def _initialize(self):
        if self.redis is None:
            self.redis = await redis_manager.get_client()
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(f"ws:{self.server_id}")
            self.pubsub_task = asyncio.create_task(self._pubsub_listener())

    async def _pubsub_listener(self):
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                user_id = data["user_id"]
                message_to_send = data["message"]
                if user_id in self.active_connections:
                    try:
                        await self.active_connections[user_id].send_json(message_to_send)
                    except Exception as e:
                        logger.error(f"Failed to send message to user {user_id}: {e}", exc_info=True)

    async def connect(self, websocket: WebSocket, user_id: str):
        await self._initialize()
        await websocket.accept()
        self.active_connections[user_id] = websocket
        await self.redis.set(f"ws_user:{user_id}", self.server_id)
        logger.info(f"WebSocket connection established for user {user_id} on server {self.server_id}")

    async def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            await self.redis.delete(f"ws_user:{user_id}")
            logger.info(f"WebSocket connection closed for user {user_id}")

    async def send_to_client(self, user_id: str, message: dict):
        await self._initialize()
        server_id = await self.redis.get(f"ws_user:{user_id}")
        if server_id:
            await self.redis.publish(f"ws:{server_id}", json.dumps({"user_id": user_id, "message": message}))
        else:
            logger.warning(f"Attempted to send message to disconnected user: {user_id}")

    async def broadcast(self, message: dict):
        await self._initialize()
        # This will be inefficient with many servers, but it's a start.
        # A better approach would be to use a shared list of all server_ids.
        all_users = await self.redis.keys("ws_user:*")
        for user_key in all_users:
            user_id = user_key.split(":")[1]
            await self.send_to_client(user_id, message)

    async def send_error(self, user_id: str, error_message: str):
        error_payload = WebSocketError(message=error_message)
        await self.send_to_client(user_id, WebSocketMessage(type="error", payload=error_payload).dict())

    async def shutdown(self):
        if self.pubsub_task:
            self.pubsub_task.cancel()
        if self.pubsub:
            await self.pubsub.close()


manager = WebSocketManager()