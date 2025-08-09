import logging
from fastapi import WebSocket
from typing import List, Dict
from redis.asyncio import Redis
from app.schemas import WebSocketMessage, User

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis: Redis | None = None

    def initialize(self, redis: Redis):
        self.redis = redis

    async def connect(self, websocket: WebSocket, user: User):
        await websocket.accept()
        user_id = str(user.id)
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, user: User, websocket: WebSocket):
        user_id = str(user.id)
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: WebSocketMessage, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message.dict())

    async def broadcast(self, message: WebSocketMessage):
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.send_json(message.dict())

    async def broadcast_to_user(self, user_id: str, message: WebSocketMessage):
        if self.redis:
            await self.redis.publish(f"ws:{user_id}", message.json())

    async def send_error(self, user_id: str, error_message: str):
        error = WebSocketMessage(type="error", payload={"message": error_message})
        await self.send_personal_message(error, user_id)

    async def shutdown(self):
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.close(code=1001)
        self.active_connections.clear()
        logger.info("All WebSocket connections closed.")

manager = WebSocketManager()

def initialize_ws_manager(redis: Redis):
    manager.initialize(redis)