"""Test client for WebSocket connections with typed methods."""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


class WebSocketTestClient:
    """Typed client for testing WebSocket connections."""
    
    def __init__(self, url: str):
        """Initialize WebSocket test client.
        
        Args:
            url: WebSocket URL with auth token (e.g., ws://localhost:8000/ws?token=...)
        """
        self.url = url
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._received_messages: List[Dict[str, Any]] = []
        self._message_queue: asyncio.Queue = asyncio.Queue()
        
    async def connect(self, timeout: float = 10.0) -> bool:
        """Connect to the WebSocket server.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connected successfully
        """
        try:
            self._websocket = await asyncio.wait_for(
                websockets.connect(self.url),
                timeout=timeout
            )
            
            # Start background task to receive messages
            self._receive_task = asyncio.create_task(self._receive_messages())
            
            logger.info(f"Connected to WebSocket: {self.url}")
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"WebSocket connection timeout: {self.url}")
            return False
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
            
    async def _receive_messages(self) -> None:
        """Background task to receive messages."""
        if not self._websocket:
            return
            
        try:
            async for message in self._websocket:
                try:
                    data = json.loads(message)
                    self._received_messages.append(data)
                    await self._message_queue.put(data)
                    logger.debug(f"Received message: {data}")
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON message: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            
    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message through the WebSocket.
        
        Args:
            message: Message to send as dictionary
        """
        if not self._websocket:
            raise RuntimeError("WebSocket not connected")
            
        await self._websocket.send(json.dumps(message))
        logger.debug(f"Sent message: {message}")
        
    async def send_chat(self, text: str, thread_id: Optional[str] = None) -> None:
        """Send a chat message.
        
        Args:
            text: Chat message text
            thread_id: Optional thread ID
        """
        message = {
            "type": "chat",
            "message": text
        }
        if thread_id:
            message["thread_id"] = thread_id
            
        await self.send(message)
        
    async def send_ping(self) -> None:
        """Send a ping message."""
        await self.send({"type": "ping"})
        
    async def receive(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Receive a message from the queue.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Received message or None if timeout
        """
        try:
            message = await asyncio.wait_for(
                self._message_queue.get(),
                timeout=timeout
            )
            return message
        except asyncio.TimeoutError:
            return None
            
    async def receive_until(self, message_type: str, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Receive messages until a specific type is received.
        
        Args:
            message_type: Type of message to wait for
            timeout: Maximum time to wait
            
        Returns:
            The message of the specified type or None if timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            message = await self.receive(timeout=1.0)
            if message and message.get("type") == message_type:
                return message
                
        return None
        
    async def wait_for_message(self, predicate, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Wait for a message matching a predicate.
        
        Args:
            predicate: Function that returns True for matching messages
            timeout: Maximum time to wait
            
        Returns:
            The first message matching the predicate or None if timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            message = await self.receive(timeout=1.0)
            if message and predicate(message):
                return message
                
        return None
        
    def get_all_received_messages(self) -> List[Dict[str, Any]]:
        """Get all messages received since connection.
        
        Returns:
            List of all received messages
        """
        return self._received_messages.copy()
        
    def clear_received_messages(self) -> None:
        """Clear the received messages buffer."""
        self._received_messages.clear()
        
    async def disconnect(self) -> None:
        """Disconnect from the WebSocket server."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
                
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
            
        logger.info("Disconnected from WebSocket")
        
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected.
        
        Returns:
            True if connected
        """
        return self._websocket is not None and not self._websocket.closed
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()