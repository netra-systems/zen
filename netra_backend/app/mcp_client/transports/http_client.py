"""
HTTP transport client for MCP with Server-Sent Events support.
Handles JSON-RPC over HTTP with authentication and retry logic.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, Optional
from urllib.parse import urljoin

import httpx

from netra_backend.app.db.base import (
    MCPConnectionError,
    MCPProtocolError,
    MCPTimeoutError,
    MCPTransport,
)

logger = logging.getLogger(__name__)


class HttpTransport(MCPTransport):
    """
    HTTP transport for MCP with SSE support.
    Handles JSON-RPC over HTTP with authentication and retries.
    """
    
    def __init__(
        self,
        base_url: str,
        auth_type: Optional[str] = None,
        auth_token: Optional[str] = None,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30000,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> None:
        """Initialize HTTP transport with authentication."""
        super().__init__(timeout)
        self._initialize_transport_config(base_url, auth_type, auth_token, api_key, headers, max_retries, retry_delay)

    def _initialize_transport_config(
        self, base_url: str, auth_type: Optional[str], auth_token: Optional[str], 
        api_key: Optional[str], headers: Optional[Dict[str, str]], 
        max_retries: int, retry_delay: float
    ) -> None:
        """Initialize all transport configuration parameters."""
        self._init_config(base_url, auth_type, auth_token, api_key)
        self._init_options(headers, max_retries, retry_delay)
        self._init_runtime_state()

    def _init_config(self, base_url: str, auth_type: Optional[str], auth_token: Optional[str], api_key: Optional[str]) -> None:
        """Initialize authentication configuration."""
        self.base_url = base_url.rstrip('/')
        self.auth_type = auth_type
        self.auth_token = auth_token
        self.api_key = api_key

    def _init_options(self, headers: Optional[Dict[str, str]], max_retries: int, retry_delay: float) -> None:
        """Initialize connection options."""
        self.headers = headers or {}
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _init_runtime_state(self) -> None:
        """Initialize runtime state variables."""
        self.client: Optional[httpx.AsyncClient] = None
        self._sse_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Establish HTTP client and test connectivity."""
        if self._connected:
            return
        await self._establish_connection()

    async def _establish_connection(self) -> None:
        """Establish the HTTP connection."""
        try:
            await self._perform_connection_setup()
        except Exception as e:
            await self._cleanup()
            raise MCPConnectionError(f"Failed to connect: {e}")

    async def _perform_connection_setup(self) -> None:
        """Perform HTTP connection setup steps."""
        await self._create_client()
        await self._test_connection()
        self._connected = True
        logger.info(f"HTTP transport connected: {self.base_url}")

    async def _create_client(self) -> None:
        """Create httpx client with proper configuration."""
        auth_headers = await self._build_auth_headers()
        all_headers = self._merge_headers(auth_headers)
        self.client = self._build_http_client(all_headers)

    def _merge_headers(self, auth_headers: Dict[str, str]) -> Dict[str, str]:
        """Merge authentication headers with base headers."""
        return {**self.headers, **auth_headers}

    def _build_http_client(self, headers: Dict[str, str]) -> httpx.AsyncClient:
        """Build httpx client with configuration and timeout protection."""
        # CRITICAL FIX: Ensure timeout never exceeds 30 seconds
        timeout_seconds = min(self.timeout / 1000, 30.0)
        return httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,  # 10 second connection timeout
                read=timeout_seconds,  # Read timeout (max 30s)
                write=10.0,  # 10 second write timeout
                pool=5.0   # 5 second pool timeout
            ),
            headers=headers,
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=10,  # Limit concurrent connections
                max_keepalive_connections=5
            )
        )

    async def _build_auth_headers(self) -> Dict[str, str]:
        """Build authentication headers based on auth type."""
        auth_map = self._get_auth_header_builders()
        for auth_check, header_builder in auth_map:
            if auth_check():
                return header_builder()
        return {}

    def _get_auth_header_builders(self) -> List[Tuple[callable, callable]]:
        """Get list of auth checkers and header builders."""
        return [
            (lambda: self.auth_type == "bearer" and self.auth_token, 
             lambda: {"Authorization": f"Bearer {self.auth_token}"}),
            (lambda: self.auth_type == "api_key" and self.api_key, 
             lambda: {"X-API-Key": self.api_key}),
            (lambda: self.api_key and not self.auth_type, 
             lambda: {"Authorization": f"ApiKey {self.api_key}"})
        ]

    async def _test_connection(self) -> None:
        """Test connection with health check endpoint."""
        self._validate_client()
        health_url = urljoin(self.base_url, "/health")
        response = await self.client.get(health_url)
        self._validate_health_response(response)

    def _validate_client(self) -> None:
        """Validate that client is initialized."""
        if not self.client:
            raise MCPConnectionError("Client not initialized")

    def _validate_health_response(self, response: httpx.Response) -> None:
        """Validate health check response."""
        if response.status_code not in (200, 404):
            raise MCPConnectionError(f"Health check failed: {response.status_code}")

    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send JSON-RPC request over HTTP POST."""
        self._validate_connection()
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        request_id = UnifiedIdGenerator.generate_base_id("mcp_http_req")
        request_data = await self._build_request_data(request_id, method, params)
        return await self._execute_with_retries(request_data)

    def _validate_connection(self) -> None:
        """Validate connection state."""
        if not self._connected or not self.client:
            raise MCPConnectionError("Not connected")

    async def _execute_with_retries(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute request with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._send_http_request(request_data)
                return await self._process_http_response(response)
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                if attempt == self.max_retries:
                    raise MCPConnectionError(f"Request failed after {self.max_retries} retries: {e}")
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

    async def _build_request_data(self, request_id: str, method: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build JSON-RPC 2.0 request data."""
        request_obj = self._create_base_request(request_id, method)
        if params is not None:
            request_obj["params"] = params
        return request_obj

    def _create_base_request(self, request_id: str, method: str) -> Dict[str, Any]:
        """Create base request object."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }

    async def _send_http_request(self, request_data: Dict[str, Any]) -> httpx.Response:
        """Send HTTP request to MCP endpoint."""
        self._validate_client_available()
        url = urljoin(self.base_url, "/mcp")
        response = await self.client.post(url, json=request_data)
        response.raise_for_status()
        return response

    def _validate_client_available(self) -> None:
        """Validate client is available for requests."""
        if not self.client:
            raise MCPConnectionError("Client not available")

    async def _process_http_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Process HTTP response and validate JSON-RPC format."""
        try:
            data = response.json()
            return await self._validate_response(data)
        except json.JSONDecodeError as e:
            raise MCPProtocolError(f"Invalid JSON response: {e}")

    async def _validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON-RPC response format."""
        self._check_response_error(response)
        self._check_response_result(response)
        return response

    def _check_response_error(self, response: Dict[str, Any]) -> None:
        """Check for errors in response."""
        if 'error' in response:
            error_info = response['error']
            raise MCPProtocolError(f"RPC Error: {error_info}")

    def _check_response_result(self, response: Dict[str, Any]) -> None:
        """Check for result in response."""
        if 'result' not in response:
            raise MCPProtocolError("Invalid response: missing result")

    async def start_sse_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Start Server-Sent Events stream for real-time updates."""
        self._validate_connection()
        sse_url = urljoin(self.base_url, "/mcp/events")
        async with self.client.stream("GET", sse_url) as response:
            response.raise_for_status()
            async for event_data in self._process_sse_lines(response):
                yield event_data

    async def _process_sse_lines(self, response: httpx.Response) -> AsyncGenerator[Dict[str, Any], None]:
        """Process SSE lines and yield event data."""
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                event_data = self._parse_sse_line(line)
                if event_data:
                    yield event_data

    def _parse_sse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse SSE data line into event object."""
        data_str = line[6:]  # Remove "data: " prefix
        try:
            return json.loads(data_str)
        except json.JSONDecodeError:
            logger.warning(f"Invalid SSE data: {data_str}")
            return None

    async def _handle_sse_event(self, event_data: Dict[str, Any]) -> None:
        """Handle incoming SSE event."""
        event_type = event_data.get('type')
        if event_type == 'notification':
            await self._process_notification(event_data.get('data', {}))
        elif event_type == 'error':
            logger.error(f"SSE error: {event_data.get('error')}")

    async def _process_notification(self, notification: Dict[str, Any]) -> None:
        """Process server notification from SSE."""
        method = notification.get('method')
        params = notification.get('params')
        logger.info(f"Received notification: {method}")

    async def disconnect(self) -> None:
        """Close HTTP client and cleanup resources."""
        if not self._connected:
            return
            
        self._connected = False
        await self._cleanup()
        logger.info("HTTP transport disconnected")

    async def _cleanup(self) -> None:
        """Clean up HTTP client and SSE task."""
        await self._stop_sse_task()
        await self._close_client()

    async def _stop_sse_task(self) -> None:
        """Stop SSE background task."""
        if self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass

    async def _close_client(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def refresh_auth_token(self, new_token: str) -> None:
        """Refresh authentication token for ongoing requests."""
        self.auth_token = new_token
        if self.client and self.auth_type == "bearer":
            self.client.headers["Authorization"] = f"Bearer {new_token}"

    def get_connection_info(self) -> Dict[str, Any]:
        """Get current connection information."""
        return {
            "base_url": self.base_url,
            "connected": self._connected,
            "auth_type": self.auth_type,
            "has_client": self.client is not None
        }


class HttpTransportError(MCPConnectionError):
    """HTTP transport specific error."""
    pass


class HttpAuthenticationError(HttpTransportError):
    """HTTP authentication specific error."""
    pass