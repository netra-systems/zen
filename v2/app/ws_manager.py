from app.logging_config import central_logger
from fastapi import WebSocket
from typing import List, Dict, Any
import time

logger = central_logger.get_logger(__name__)

class WebSocketManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
            cls._instance.active_connections: Dict[str, List[WebSocket]] = {}
        return cls._instance

    async def connect(self, user_id: str, websocket: WebSocket):
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_message(self, user_id: str, message: Dict[str, Any]):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to {user_id}: {e}")
                    # Remove disconnected connections
                    self.active_connections[user_id].remove(connection)
                    if not self.active_connections[user_id]:
                        del self.active_connections[user_id]

    async def send_error(self, user_id: str, error_message: str, sub_agent_name: str = "System"):
        """Send an error message to a specific user"""
        await self.send_message(
            user_id,
            {
                "type": "error",
                "payload": {"error": error_message, "sub_agent_name": sub_agent_name},
                "displayed_to_user": True
            }
        )
    
    async def send_agent_log(self, user_id: str, log_level: str, message: str, sub_agent_name: str = None):
        """Send agent log messages for real-time monitoring"""
        await self.send_message(
            user_id,
            {
                "type": "agent_log",
                "payload": {
                    "level": log_level,
                    "message": message,
                    "sub_agent_name": sub_agent_name,
                    "timestamp": time.time()
                },
                "displayed_to_user": True
            }
        )
    
    async def send_tool_call(self, user_id: str, tool_name: str, tool_args: Dict[str, Any], sub_agent_name: str = None):
        """Send tool call updates"""
        await self.send_message(
            user_id,
            {
                "type": "tool_call",
                "payload": {
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "sub_agent_name": sub_agent_name,
                    "timestamp": time.time()
                },
                "displayed_to_user": True
            }
        )
    
    async def send_tool_result(self, user_id: str, tool_name: str, result: Any, sub_agent_name: str = None):
        """Send tool result updates"""
        await self.send_message(
            user_id,
            {
                "type": "tool_result",
                "payload": {
                    "tool_name": tool_name,
                    "result": result,
                    "sub_agent_name": sub_agent_name,
                    "timestamp": time.time()
                },
                "displayed_to_user": True
            }
        )

    async def broadcast(self, message: Dict[str, Any]):
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {user_id}: {e}")

    async def shutdown(self):
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.close(code=1001)
        self.active_connections.clear()
        logger.info("All WebSocket connections closed.")

manager = WebSocketManager()