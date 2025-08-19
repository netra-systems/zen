"""Real WebSocket Client for E2E Testing

Professional WebSocket client with reconnection, message handling, and comprehensive error handling.
NO MOCKING - actual WebSocket connections for true integration validation.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Reliable real-time communication testing
- Value Impact: Prevents WebSocket issues that affect user experience  
- Revenue Impact: Ensures real-time features work for paying customers
"""

import asyncio
import json
import ssl
from typing import Dict, Any, Optional, Union
import websockets
from websockets.exceptions import ConnectionClosedError
from .real_client_types import ConnectionMetrics, ClientConfig, ConnectionState


class RealWebSocketClient:
    """Real WebSocket client with reconnection and message handling"""
    
    def __init__(self, ws_url: str, config: Optional[ClientConfig] = None):
        """Initialize WebSocket client"""
        self.ws_url = ws_url
        self.config = config or ClientConfig()
        self.metrics = ConnectionMetrics()
        self.state = ConnectionState.DISCONNECTED
        self._websocket = None
        self._message_queue: asyncio.Queue = asyncio.Queue()
    
    async def connect(self, headers: Optional[Dict[str, str]] = None) -> bool:
        """Connect to WebSocket with retry logic"""
        self.state = ConnectionState.CONNECTING
        
        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = asyncio.get_event_loop().time()
                self._websocket = await self._establish_connection(headers)
                connection_time = asyncio.get_event_loop().time() - start_time
                self.metrics.connection_time = connection_time
                self.state = ConnectionState.CONNECTED
                return True
            except Exception as e:
                if attempt == self.config.max_retries:
                    self._handle_connection_error(str(e))
                    return False
                delay = self.config.get_retry_delay(attempt)
                await asyncio.sleep(delay)
        return False
    
    async def _establish_connection(self, headers: Optional[Dict[str, str]]):
        """Establish WebSocket connection"""
        extra_headers = headers or {}
        ssl_context = self.config.create_ssl_context()
        
        return await websockets.connect(
            self.ws_url,
            extra_headers=extra_headers,
            ssl=ssl_context,
            ping_timeout=self.config.timeout
        )
    
    async def send(self, message: Union[Dict[str, Any], str]) -> bool:
        """Send message through WebSocket"""
        if not self._websocket or self.state != ConnectionState.CONNECTED:
            return False
        
        try:
            message_str = self._prepare_message(message)
            await self._websocket.send(message_str)
            self.metrics.requests_sent += 1
            return True
        except (ConnectionClosedError, Exception) as e:
            self._handle_send_error(str(e))
            return False
    
    def _prepare_message(self, message: Union[Dict[str, Any], str]) -> str:
        """Prepare message for sending"""
        return json.dumps(message) if isinstance(message, dict) else message
    
    async def receive(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Receive message from WebSocket"""
        if not self._websocket:
            return None
        
        try:
            timeout_value = timeout or self.config.timeout
            message = await asyncio.wait_for(
                self._websocket.recv(), timeout=timeout_value
            )
            self.metrics.responses_received += 1
            return json.loads(message)
        except (asyncio.TimeoutError, ConnectionClosedError) as e:
            self._handle_receive_error(str(e))
            return None
    
    async def send_and_wait(self, message: Union[Dict[str, Any], str],
                           timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Send message and wait for response"""
        success = await self.send(message)
        if not success:
            return None
        return await self.receive(timeout)
    
    def _handle_connection_error(self, error: str) -> None:
        """Handle connection error"""
        self.state = ConnectionState.FAILED
        self.metrics.last_error = error
        self.metrics.retry_count += 1
    
    def _handle_send_error(self, error: str) -> None:
        """Handle send error"""
        self.metrics.last_error = error
        self.state = ConnectionState.FAILED
    
    def _handle_receive_error(self, error: str) -> None:
        """Handle receive error"""
        self.metrics.last_error = error
        if isinstance(error, str) and "closed" in error.lower():
            self.state = ConnectionState.DISCONNECTED
    
    async def close(self) -> None:
        """Close WebSocket connection"""
        if self._websocket:
            await self._websocket.close()
            self.state = ConnectionState.DISCONNECTED