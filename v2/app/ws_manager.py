from typing import List, Dict
from fastapi import WebSocket
import redis.asyncio as redis
import asyncio
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self, redis_manager: redis.Redis):
        self.redis_manager = redis_manager
        self.connections: Dict[str, List[WebSocket]] = {}
        self.pubsub_client = self.redis_manager.pubsub()

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.connections:
            self.connections[user_id] = []
        self.connections[user_id].append(websocket)
        await self.pubsub_client.subscribe(f"user:{user_id}")
        asyncio.create_task(self.listen_for_messages(f"user:{user_id}"))

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.connections:
            self.connections[user_id].remove(websocket)
            if not self.connections[user_id]:
                del self.connections[user_id]
                asyncio.create_task(self.pubsub_client.unsubscribe(f"user:{user_id}"))

    async def listen_for_messages(self, channel: str):
        while True:
            try:
                message = await self.pubsub_client.get_message(ignore_subscribe_messages=True)
                if message:
                    user_id = channel.split(":")[1]
                    if user_id in self.connections:
                        for websocket in self.connections[user_id]:
                            await websocket.send_text(message['data'])
            except Exception as e:
                logger.error(f"Error listening for messages on channel {channel}: {e}")
                break

    async def send_to_client(self, user_id: str, message: 'WebSocketMessage'):
        await self.redis_manager.publish(f"user:{user_id}", message.model_dump_json())

    async def broadcast(self, message: 'WebSocketMessage'):
        await self.redis_manager.publish("broadcast", message.model_dump_json())

    async def send_error(self, user_id: str, error_message: str):
        from app.schemas import WebSocketMessage, WebSocketError
        error_payload = WebSocketError(message=error_message)
        ws_message = WebSocketMessage(type="error", payload=error_payload)
        await self.send_to_client(user_id, ws_message)

    async def shutdown(self):
        for user_id, connections in self.connections.items():
            for websocket in connections:
                await websocket.close(code=1001, reason="Server is shutting down")
        self.connections.clear()
        await self.pubsub_client.close()

# This is a placeholder for the actual manager that will be created in main.py
manager = None

def initialize_ws_manager(redis_manager: redis.Redis):
    global manager
    manager = WebSocketManager(redis_manager)
