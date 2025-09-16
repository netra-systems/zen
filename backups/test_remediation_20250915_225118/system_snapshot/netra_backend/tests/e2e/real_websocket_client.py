"""Real WebSocket Client for E2E Testing

Minimal WebSocket client implementation for integration tests.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional
import websockets
from websockets import ServerConnection
from websockets import ConnectionClosed, WebSocketException

from netra_backend.tests.e2e.real_client_types import ClientConfig, ConnectionState

logger = logging.getLogger(__name__)

class RealWebSocketClient:
    """Real WebSocket client for integration testing."""
    
    def __init__(self, config: ClientConfig):
        self.config = config
        self.connection_state = ConnectionState.DISCONNECTED
        self.websocket: Optional[websockets.ServerConnection] = None
        self.message_handler: Optional[Callable] = None
        self._closed = False
    
    async def connect(self) -> bool:
        """Connect to the WebSocket server."""
        try:
            self.connection_state = ConnectionState.CONNECTING
            
            headers = self.config.headers or {}
            if self.config.auth_token:
                headers["Authorization"] = f"Bearer {self.config.auth_token}"
            
            self.websocket = await websockets.connect(
                self.config.websocket_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.connection_state = ConnectionState.CONNECTED
            logger.info(f"Connected to WebSocket: {self.config.websocket_url}")
            return True
            
        except Exception as e:
            self.connection_state = ConnectionState.ERROR
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        self._closed = True
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.connection_state = ConnectionState.DISCONNECTED
        logger.info("Disconnected from WebSocket")
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a message to the WebSocket server."""
        if not self.websocket or self.connection_state != ConnectionState.CONNECTED:
            logger.error("Cannot send message: not connected")
            return False
        
        try:
            message_str = json.dumps(message)
            await self.websocket.send(message_str)
            logger.debug(f"Sent message: {message_str}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def receive_message(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Receive a message from the WebSocket server."""
        if not self.websocket or self.connection_state != ConnectionState.CONNECTED:
            return None
        
        try:
            message_str = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=timeout or self.config.timeout
            )
            message = json.loads(message_str)
            logger.debug(f"Received message: {message_str}")
            return message
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for message")
            return None
        except ConnectionClosed:
            self.connection_state = ConnectionState.DISCONNECTED
            logger.warning("WebSocket connection closed")
            return None
        except Exception as e:
            logger.error(f"Failed to receive message: {e}")
            return None
    
    async def listen(self, message_handler: Callable[[Dict[str, Any]], None]):
        """Listen for messages and call the handler for each message."""
        self.message_handler = message_handler
        
        while not self._closed and self.connection_state == ConnectionState.CONNECTED:
            message = await self.receive_message()
            if message and self.message_handler:
                try:
                    await self.message_handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if the client is connected."""
        return self.connection_state == ConnectionState.CONNECTED and self.websocket is not None