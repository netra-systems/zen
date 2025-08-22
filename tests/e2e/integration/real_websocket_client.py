"""Real WebSocket Client for E2E Testing

WebSocket client for real connection testing with state management,
authentication, and error handling capabilities.
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional

import websockets
from websockets.exceptions import ConnectionClosedError

from tests.e2e.real_client_types import ClientConfig, ConnectionState


class RealWebSocketClient:
    """Real WebSocket client for E2E testing."""
    
    def __init__(self, url: str, config: ClientConfig):
        """Initialize WebSocket client."""
        self.url = url
        self.config = config
        self.state = ConnectionState.DISCONNECTED
        self._websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._auth_headers: Dict[str, str] = {}
    
    async def connect(self, headers: Optional[Dict[str, str]] = None) -> bool:
        """Connect to WebSocket server."""
        try:
            if headers:
                self._auth_headers = headers
            
            # Try to establish connection - append token to URL if provided
            url = self.url
            if headers and "Authorization" in headers:
                token = headers["Authorization"].replace("Bearer ", "")
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}token={token}"
            
            self._websocket = await asyncio.wait_for(
                websockets.connect(url),
                timeout=self.config.timeout
            )
            self.state = ConnectionState.CONNECTED
            return True
            
        except (ConnectionClosedError, asyncio.TimeoutError, OSError) as e:
            self.state = ConnectionState.DISCONNECTED
            return False
        except Exception as e:
            # Handle other WebSocket errors (like 403 Forbidden)
            self.state = ConnectionState.DISCONNECTED
            return False
    
    async def send(self, message: Dict[str, Any]) -> bool:
        """Send message to WebSocket server."""
        if not self._websocket or self.state != ConnectionState.CONNECTED:
            return False
        
        try:
            await self._websocket.send(json.dumps(message))
            return True
        except (ConnectionClosedError, OSError):
            self.state = ConnectionState.DISCONNECTED
            return False
    
    async def receive(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Receive message from WebSocket server."""
        if not self._websocket or self.state != ConnectionState.CONNECTED:
            return None
        
        try:
            message_str = await asyncio.wait_for(
                self._websocket.recv(),
                timeout=timeout
            )
            return json.loads(message_str)
        except (ConnectionClosedError, asyncio.TimeoutError, json.JSONDecodeError, OSError):
            return None
    
    async def send_message(self, message: str) -> bool:
        """Send string message to WebSocket server."""
        if not self._websocket or self.state != ConnectionState.CONNECTED:
            return False
        
        try:
            await self._websocket.send(message)
            return True
        except (ConnectionClosedError, OSError):
            self.state = ConnectionState.DISCONNECTED
            return False
    
    async def close(self):
        """Close WebSocket connection."""
        if self._websocket:
            await self._websocket.close()
        self.state = ConnectionState.DISCONNECTED
        self._websocket = None
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self.state == ConnectionState.CONNECTED and self._websocket is not None
