"""Real Client Types for E2E Testing

Provides client types and interfaces for E2E tests.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import httpx
import websockets
from unittest.mock import MagicMock


@dataclass
class TestClient:
    """HTTP test client for E2E tests."""
    
    base_url: str
    headers: Dict[str, str] = None
    cookies: Dict[str, str] = None
    timeout: float = 30.0
    
    def __post_init__(self):
        self.headers = self.headers or {}
        self.cookies = self.cookies or {}
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            cookies=self.cookies,
            timeout=self.timeout
        )
    
    async def get(self, path: str, **kwargs) -> httpx.Response:
        """Make GET request."""
        return await self._client.get(path, **kwargs)
    
    async def post(self, path: str, **kwargs) -> httpx.Response:
        """Make POST request."""
        return await self._client.post(path, **kwargs)
    
    async def put(self, path: str, **kwargs) -> httpx.Response:
        """Make PUT request."""
        return await self._client.put(path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """Make DELETE request."""
        return await self._client.delete(path, **kwargs)
    
    async def close(self):
        """Close the client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


@dataclass
class WebSocketClient:
    """WebSocket test client for E2E tests."""
    
    url: str
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        self.headers = self.headers or {}
        self._websocket = None
        self._connected = False
    
    async def connect(self):
        """Connect to WebSocket."""
        self._websocket = await websockets.connect(
            self.url,
            extra_headers=self.headers
        )
        self._connected = True
        return self
    
    async def send(self, message: str):
        """Send message."""
        if not self._connected:
            raise RuntimeError("WebSocket not connected")
        await self._websocket.send(message)
    
    async def receive(self) -> str:
        """Receive message."""
        if not self._connected:
            raise RuntimeError("WebSocket not connected")
        return await self._websocket.recv()
    
    async def close(self):
        """Close connection."""
        if self._websocket:
            await self._websocket.close()
            self._connected = False
    
    async def __aenter__(self):
        return await self.connect()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class MockClient:
    """Mock client for testing without real services."""
    
    def __init__(self):
        self.requests = []
        self.responses = []
        self.mock = MagicMock()
    
    async def get(self, *args, **kwargs):
        self.requests.append(("GET", args, kwargs))
        return self.mock.get(*args, **kwargs)
    
    async def post(self, *args, **kwargs):
        self.requests.append(("POST", args, kwargs))
        return self.mock.post(*args, **kwargs)
    
    async def close(self):
        pass