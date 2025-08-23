"""
WebSocket Development Utilities

Development utilities for WebSocket testing and debugging.
"""

import asyncio
import websockets
from typing import Dict, Any

class WebSocketDevUtility:
    """Development utility for WebSocket operations."""
    
    def __init__(self, url: str = "ws://localhost:8000"):
        self.url = url
        self.connection = None
    
    async def connect(self) -> bool:
        """Connect to WebSocket."""
        try:
            self.connection = await websockets.connect(self.url)
            return True
        except Exception:
            return False
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message via WebSocket."""
        if not self.connection:
            return False
        try:
            await self.connection.send(str(message))
            return True
        except Exception:
            return False
    
    async def close(self):
        """Close connection."""
        if self.connection:
            await self.connection.close()
