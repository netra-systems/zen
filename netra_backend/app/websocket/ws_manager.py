"""WebSocket Manager Module"""

from typing import Dict, Set
import asyncio
from fastapi import WebSocket


class WebSocketManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        async with self.connection_lock:
            self.active_connections[client_id] = websocket
    
    async def disconnect(self, client_id: str):
        """Remove WebSocket connection"""
        async with self.connection_lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
    
    async def send_message(self, client_id: str, message: str):
        """Send message to specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)


# Create singleton instance
ws_manager = WebSocketManager()
