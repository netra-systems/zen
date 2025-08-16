"""
WebSocket transport client for MCP with full-duplex communication.
Handles JSON-RPC over WebSocket with automatic reconnection and heartbeat.
"""

import asyncio
import json
import uuid
import logging
from typing import Dict, Any, Optional, Callable
import websockets
from websockets.exceptions import ConnectionClosed, InvalidMessage
import ssl
from urllib.parse import urlparse

from .base import MCPTransport, MCPConnectionError, MCPTimeoutError, MCPProtocolError

logger = logging.getLogger(__name__)


class WebSocketTransport(MCPTransport):
    """
    WebSocket transport for MCP with full-duplex communication.
    Handles automatic reconnection, heartbeat, and message routing.
    """
    
    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30000,
        ping_interval: int = 30,
        ping_timeout: int = 10,
        max_reconnect_attempts: int = 5,
        reconnect_delay: float = 2.0
    ) -> None:
        """Initialize WebSocket transport with configuration."""
        super().__init__(timeout)
        self.url = url
        self.headers = headers or {}
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._receiver_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0

    async def connect(self) -> None:
        """Establish WebSocket connection with retry logic."""
        if self._connected:
            return
            
        for attempt in range(self.max_reconnect_attempts):
            try:
                await self._establish_connection()
                await self._start_background_tasks()
                self._connected = True
                self._reconnect_attempts = 0
                logger.info(f"WebSocket transport connected: {self.url}")
                return
            except Exception as e:
                self._reconnect_attempts = attempt + 1
                if attempt < self.max_reconnect_attempts - 1:
                    await asyncio.sleep(self.reconnect_delay * (2 ** attempt))
                    logger.warning(f"Connection attempt {attempt + 1} failed, retrying...")
                else:
                    raise MCPConnectionError(f"Failed to connect after {self.max_reconnect_attempts} attempts: {e}")

    async def _establish_connection(self) -> None:
        """Establish the WebSocket connection."""
        ssl_context = await self._create_ssl_context()
        
        self.websocket = await websockets.connect(
            self.url,
            extra_headers=self.headers,
            ssl=ssl_context,
            ping_interval=self.ping_interval,
            ping_timeout=self.ping_timeout,
            close_timeout=10
        )

    async def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for secure WebSocket connections."""
        parsed_url = urlparse(self.url)
        if parsed_url.scheme == "wss":
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            return ssl_context
        return None

    async def _start_background_tasks(self) -> None:
        """Start receiver and heartbeat background tasks."""
        self._receiver_task = asyncio.create_task(self._message_receiver_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _message_receiver_loop(self) -> None:
        """Continuously receive and process WebSocket messages."""
        try:
            while self._connected and self.websocket:
                message = await self.websocket.recv()
                await self._handle_incoming_message(message)
        except ConnectionClosed:
            logger.warning("WebSocket connection closed by server")
            await self._handle_disconnect()
        except Exception as e:
            logger.error(f"Message receiver error: {e}")
            await self._handle_disconnect()

    async def _handle_incoming_message(self, message: str) -> None:
        """Process incoming WebSocket message."""
        try:
            data = json.loads(message)
            await self._route_message(data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")

    async def _route_message(self, data: Dict[str, Any]) -> None:
        """Route message to appropriate handler."""
        if 'id' in data and data['id'] in self._pending_requests:
            await self._handle_response(data)
        elif 'method' in data:
            await self._handle_notification(data)
        else:
            logger.warning(f"Unhandled message: {data}")

    async def _handle_response(self, data: Dict[str, Any]) -> None:
        """Handle JSON-RPC response message."""
        request_id = data['id']
        future = self._pending_requests.pop(request_id, None)
        if future and not future.cancelled():
            future.set_result(data)

    async def _handle_notification(self, data: Dict[str, Any]) -> None:
        """Handle JSON-RPC notification message."""
        method = data.get('method')
        if method in self._message_handlers:
            handler = self._message_handlers[method]
            await handler(data.get('params', {}))

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to maintain connection."""
        try:
            while self._connected and self.websocket:
                await asyncio.sleep(self.ping_interval)
                if self.websocket and not self.websocket.closed:
                    await self.websocket.ping()
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send JSON-RPC request over WebSocket."""
        if not self._connected or not self.websocket:
            raise MCPConnectionError("Not connected")
            
        request_id = str(uuid.uuid4())
        request_data = await self._build_request(request_id, method, params)
        
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            await self.websocket.send(json.dumps(request_data))
            response = await asyncio.wait_for(future, timeout=self.timeout / 1000)
            return await self._validate_response(response)
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise MCPTimeoutError(f"Request timeout: {method}")
        except ConnectionClosed:
            self._pending_requests.pop(request_id, None)
            raise MCPConnectionError("WebSocket connection closed")

    async def _build_request(self, request_id: str, method: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build JSON-RPC 2.0 request."""
        request_obj = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }
        if params is not None:
            request_obj["params"] = params
        return request_obj

    async def _validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON-RPC response format."""
        if 'error' in response:
            error_info = response['error']
            raise MCPProtocolError(f"RPC Error: {error_info}")
            
        if 'result' not in response:
            raise MCPProtocolError("Invalid response: missing result")
            
        return response

    def register_notification_handler(self, method: str, handler: Callable) -> None:
        """Register handler for server notifications."""
        self._message_handlers[method] = handler

    def unregister_notification_handler(self, method: str) -> None:
        """Unregister notification handler."""
        self._message_handlers.pop(method, None)

    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send JSON-RPC notification (no response expected)."""
        if not self._connected or not self.websocket:
            raise MCPConnectionError("Not connected")
            
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params is not None:
            notification["params"] = params
            
        await self.websocket.send(json.dumps(notification))

    async def disconnect(self) -> None:
        """Close WebSocket connection and cleanup."""
        if not self._connected:
            return
            
        self._connected = False
        await self._cleanup()
        logger.info("WebSocket transport disconnected")

    async def _cleanup(self) -> None:
        """Clean up all resources and tasks."""
        await self._stop_background_tasks()
        await self._close_websocket()
        self._cancel_pending_requests()

    async def _stop_background_tasks(self) -> None:
        """Stop all background tasks."""
        for task in [self._receiver_task, self._heartbeat_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def _close_websocket(self) -> None:
        """Close WebSocket connection."""
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        self.websocket = None

    def _cancel_pending_requests(self) -> None:
        """Cancel all pending requests."""
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

    async def _handle_disconnect(self) -> None:
        """Handle unexpected disconnection and attempt reconnection."""
        if self._connected:
            self._connected = False
            self._cancel_pending_requests()
            logger.warning("WebSocket disconnected unexpectedly")
            
            if self._reconnect_attempts < self.max_reconnect_attempts:
                await self._attempt_reconnection()

    async def _attempt_reconnection(self) -> None:
        """Attempt to reconnect after unexpected disconnection."""
        try:
            await asyncio.sleep(self.reconnect_delay)
            await self.connect()
            logger.info("WebSocket reconnected successfully")
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")


class WebSocketTransportError(MCPConnectionError):
    """WebSocket transport specific error."""
    pass