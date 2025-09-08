"""
WebSocket transport client for MCP with full-duplex communication.
Handles JSON-RPC over WebSocket with automatic reconnection and heartbeat.
"""

import asyncio
import json
import logging
import ssl
import uuid
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

import websockets
from websockets import ServerConnection
from websockets.exceptions import ConnectionClosed, InvalidMessage

from netra_backend.app.db.base import (
    MCPConnectionError,
    MCPProtocolError,
    MCPTimeoutError,
    MCPTransport,
)

logger = logging.getLogger(__name__)


class WebSocketTransport(MCPTransport):
    """
    WebSocket transport for MCP with full-duplex communication.
    Handles automatic reconnection, heartbeat, and message routing.
    """
    
    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30000, ping_interval: int = 30, ping_timeout: int = 10, max_reconnect_attempts: int = 5, reconnect_delay: float = 2.0) -> None:
        """Initialize WebSocket transport with configuration."""
        super().__init__(timeout)
        self._init_connection_params(url, headers, ping_interval, ping_timeout, max_reconnect_attempts, reconnect_delay)
        self._init_state_variables()

    def _init_connection_params(self, url: str, headers: Optional[Dict[str, str]], ping_interval: int, ping_timeout: int, max_reconnect_attempts: int, reconnect_delay: float) -> None:
        """Initialize connection parameters."""
        self.url = url
        self.headers = headers or {}
        self._init_ping_params(ping_interval, ping_timeout)
        self._init_reconnect_params(max_reconnect_attempts, reconnect_delay)

    def _init_ping_params(self, ping_interval: int, ping_timeout: int) -> None:
        """Initialize ping-related parameters."""
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout

    def _init_reconnect_params(self, max_reconnect_attempts: int, reconnect_delay: float) -> None:
        """Initialize reconnection parameters."""
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay

    def _init_state_variables(self) -> None:
        """Initialize state management variables."""
        self.websocket: Optional[websockets.ServerConnection] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._receiver_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0

    async def connect(self) -> None:
        """Establish WebSocket connection with retry logic."""
        if self._connected:
            return
        await self._connect_with_retries()

    async def _connect_with_retries(self) -> None:
        """Attempt connection with retry logic."""
        for attempt in range(self.max_reconnect_attempts):
            try:
                await self._perform_connection_steps()
                return
            except Exception as e:
                await self._handle_connection_retry(attempt, e)

    async def _perform_connection_steps(self) -> None:
        """Perform all steps needed for successful connection."""
        await self._establish_connection()
        await self._start_background_tasks()
        self._connected = True
        self._reconnect_attempts = 0
        logger.info(f"WebSocket transport connected: {self.url}")

    async def _handle_connection_retry(self, attempt: int, error: Exception) -> None:
        """Handle connection retry logic for failed attempts."""
        self._reconnect_attempts = attempt + 1
        if attempt < self.max_reconnect_attempts - 1:
            await asyncio.sleep(self.reconnect_delay * (2 ** attempt))
            logger.warning(f"Connection attempt {attempt + 1} failed, retrying...")
        else:
            raise MCPConnectionError(f"Failed to connect after {self.max_reconnect_attempts} attempts: {error}")

    async def _establish_connection(self) -> None:
        """Establish the WebSocket connection."""
        ssl_context = await self._create_ssl_context()
        connection_params = await self._build_connection_params(ssl_context)
        self.websocket = await websockets.connect(**connection_params)

    async def _build_connection_params(self, ssl_context: Optional[ssl.SSLContext]) -> Dict[str, Any]:
        """Build WebSocket connection parameters."""
        base_params = await self._get_base_connection_params(ssl_context)
        timeout_params = await self._get_timeout_params()
        return {**base_params, **timeout_params}

    async def _get_base_connection_params(self, ssl_context: Optional[ssl.SSLContext]) -> Dict[str, Any]:
        """Get base connection parameters."""
        return {
            "uri": self.url,
            "extra_headers": self.headers,
            "ssl": ssl_context
        }

    async def _get_timeout_params(self) -> Dict[str, Any]:
        """Get timeout-related parameters."""
        return {
            "ping_interval": self.ping_interval,
            "ping_timeout": self.ping_timeout,
            "close_timeout": 10
        }

    async def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for secure WebSocket connections."""
        parsed_url = urlparse(self.url)
        if parsed_url.scheme == "wss":
            return await self._build_ssl_context()
        return None

    async def _build_ssl_context(self) -> ssl.SSLContext:
        """Build and configure SSL context."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        return ssl_context

    async def _start_background_tasks(self) -> None:
        """Start receiver and heartbeat background tasks."""
        self._receiver_task = asyncio.create_task(self._message_receiver_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _message_receiver_loop(self) -> None:
        """Continuously receive and process WebSocket messages."""
        try:
            await self._receive_messages_loop()
        except ConnectionClosed:
            await self._handle_connection_closed()
        except Exception as e:
            await self._handle_receiver_error(e)

    async def _handle_connection_closed(self) -> None:
        """Handle WebSocket connection closed by server."""
        logger.warning("WebSocket connection closed by server")
        await self._handle_disconnect()

    async def _handle_receiver_error(self, error: Exception) -> None:
        """Handle message receiver errors."""
        logger.error(f"Message receiver error: {error}")
        await self._handle_disconnect()

    async def _receive_messages_loop(self) -> None:
        """Main message receiving loop."""
        while self._connected and self.websocket:
            message = await self.websocket.recv()
            await self._handle_incoming_message(message)

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
            await self._send_heartbeats_loop()
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

    async def _send_heartbeats_loop(self) -> None:
        """Main heartbeat sending loop."""
        while self._connected and self.websocket:
            await asyncio.sleep(self.ping_interval)
            if self.websocket and not self.websocket.closed:
                await self.websocket.ping()

    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send JSON-RPC request over WebSocket."""
        if not self._connected or not self.websocket:
            raise MCPConnectionError("Not connected")
            
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        request_id = UnifiedIdGenerator.generate_base_id("mcp_ws_req")
        request_data = await self._build_request(request_id, method, params)
        return await self._execute_request(request_id, request_data, method)

    async def _execute_request(self, request_id: str, request_data: Dict[str, Any], method: str) -> Dict[str, Any]:
        """Execute the request and handle response/errors."""
        future = await self._setup_request_future(request_id)
        
        try:
            return await self._send_and_wait_response(request_data, future)
        except (asyncio.TimeoutError, ConnectionClosed) as e:
            return await self._handle_request_error(request_id, method, e)

    async def _send_and_wait_response(self, request_data: Dict[str, Any], future: asyncio.Future) -> Dict[str, Any]:
        """Send request and wait for response."""
        await self.websocket.send(json.dumps(request_data))
        response = await asyncio.wait_for(future, timeout=self.timeout / 1000)
        return await self._validate_response(response)

    async def _setup_request_future(self, request_id: str) -> asyncio.Future:
        """Setup future for request tracking."""
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        return future

    async def _handle_request_error(self, request_id: str, method: str, error: Exception) -> None:
        """Handle request timeout and connection errors."""
        self._pending_requests.pop(request_id, None)
        if isinstance(error, asyncio.TimeoutError):
            raise MCPTimeoutError(f"Request timeout: {method}")
        else:
            raise MCPConnectionError("WebSocket connection closed")

    async def _build_request(self, request_id: str, method: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build JSON-RPC 2.0 request."""
        request_obj = await self._create_base_request(request_id, method)
        if params is not None:
            request_obj["params"] = params
        return request_obj

    async def _create_base_request(self, request_id: str, method: str) -> Dict[str, Any]:
        """Create base JSON-RPC request object."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }

    async def _validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON-RPC response format."""
        if 'error' in response:
            await self._handle_response_error(response['error'])
            
        if 'result' not in response:
            raise MCPProtocolError("Invalid response: missing result")
        return response

    async def _handle_response_error(self, error_info: Any) -> None:
        """Handle JSON-RPC error responses."""
        raise MCPProtocolError(f"RPC Error: {error_info}")

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
            
        notification = await self._build_notification(method, params)
        await self.websocket.send(json.dumps(notification))

    async def _build_notification(self, method: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build JSON-RPC notification object."""
        notification = await self._create_base_notification(method)
        if params is not None:
            notification["params"] = params
        return notification

    async def _create_base_notification(self, method: str) -> Dict[str, Any]:
        """Create base notification object."""
        return {
            "jsonrpc": "2.0",
            "method": method
        }

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
                await self._cancel_task_safely(task)

    async def _cancel_task_safely(self, task: asyncio.Task) -> None:
        """Cancel a task safely with exception handling."""
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
            await self._process_disconnect()
            await self._check_reconnection_needed()

    async def _process_disconnect(self) -> None:
        """Process the disconnection state changes."""
        self._connected = False
        self._cancel_pending_requests()
        logger.warning("WebSocket disconnected unexpectedly")

    async def _check_reconnection_needed(self) -> None:
        """Check if reconnection should be attempted."""
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