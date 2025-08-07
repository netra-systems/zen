from fastapi import WebSocket
from typing import Dict, Any
from app.schemas import WebSocketMessage

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, run_id: str):
        await websocket.accept()
        self.active_connections[run_id] = websocket

    def disconnect(self, run_id: str):
        if run_id in self.active_connections:
            del self.active_connections[run_id]

    async def send_to_run(self, message: WebSocketMessage):
        if message.run_id in self.active_connections:
            await self.active_connections[message.run_id].send_json(message.dict())

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()
