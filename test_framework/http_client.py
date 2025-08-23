"""Unified HTTP Client for E2E Testing

Professional HTTP client with connection pooling, retry logic, and comprehensive error handling.
NO MOCKING - actual network calls for true integration validation.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Reliable HTTP API testing for customer-facing features
- Value Impact: Prevents API bugs that affect user experience
- Revenue Impact: Protects customer conversion and retention

This consolidates all HTTP client functionality from E2E tests into a single, well-tested module.
"""

import asyncio
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Union
import httpx
from pathlib import Path


class ConnectionState(Enum):
    """WebSocket connection states for E2E testing.
    
    Consolidated enum covering all test scenarios across different test modules.
    This provides a single source of truth for connection state management in tests.
    """
    # Core connection states
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    CLOSING = "closing"
    CLOSED = "closed"
    
    # Advanced states for resilience testing
    STREAMING = "streaming"
    INTERRUPTED = "interrupted"
    RECOVERING = "recovering"
    
    # Backend-specific states (mapped for compatibility)
    ACTIVE = "active"


@dataclass
class ClientConfig:
    """Configuration for HTTP test client."""
    
    base_url: str = "http://localhost:8000"
    websocket_url: str = "ws://localhost:8000/websocket"
    auth_url: str = "http://localhost:8001"
    timeout: float = 30.0
    max_retries: int = 3
    pool_size: int = 100
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    use_ssl: bool = False
    verify_ssl: bool = True
    
    def get_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff."""
        return min(2 ** attempt, 30.0)


class ConnectionMetrics:
    """Track connection metrics."""
    
    def __init__(self):
        self.requests_sent = 0
        self.responses_received = 0
        self.retry_count = 0
        self.last_error = None


class UnifiedHTTPClient:
    """Unified HTTP client with connection pooling, retry logic, and consistent interface."""
    
    def __init__(self, base_url: str = "http://localhost:8000", config: Optional[ClientConfig] = None):
        """Initialize HTTP client with configuration."""
        self.base_url = base_url.rstrip('/')
        self.config = config or ClientConfig(base_url=base_url)
        self.metrics = ConnectionMetrics()
        self._client = self._create_client()
    
    def _create_client(self) -> httpx.AsyncClient:
        """Create configured HTTP client."""
        limits = httpx.Limits(max_connections=self.config.pool_size)
        timeout = httpx.Timeout(self.config.timeout)
        return httpx.AsyncClient(
            limits=limits, 
            timeout=timeout, 
            verify=self.config.verify_ssl,
            follow_redirects=True
        )
    
    def _get_auth_headers(self, token: Optional[str]) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {"Content-Type": "application/json"}
        headers.update(self.config.headers)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    async def get(self, path: str, token: Optional[str] = None, **kwargs) -> Union[httpx.Response, Dict[str, Any]]:
        """Execute GET request with retry logic."""
        url = f"{self.base_url}{path}"
        headers = self._get_auth_headers(token)
        return await self._execute_request("GET", url, headers=headers, **kwargs)
    
    async def post(self, path: str, data: Optional[Dict[str, Any]] = None, 
                   token: Optional[str] = None, **kwargs) -> Union[httpx.Response, Dict[str, Any]]:
        """Execute POST request with retry logic."""
        url = f"{self.base_url}{path}"
        headers = self._get_auth_headers(token)
        if data is not None:
            kwargs["json"] = data
        return await self._execute_request("POST", url, headers=headers, **kwargs)
    
    async def put(self, path: str, data: Optional[Dict[str, Any]] = None,
                  token: Optional[str] = None, **kwargs) -> Union[httpx.Response, Dict[str, Any]]:
        """Execute PUT request with retry logic."""
        url = f"{self.base_url}{path}"
        headers = self._get_auth_headers(token)
        if data is not None:
            kwargs["json"] = data
        return await self._execute_request("PUT", url, headers=headers, **kwargs)
    
    async def delete(self, path: str, token: Optional[str] = None, **kwargs) -> Union[httpx.Response, Dict[str, Any]]:
        """Execute DELETE request with retry logic."""
        url = f"{self.base_url}{path}"
        headers = self._get_auth_headers(token)
        return await self._execute_request("DELETE", url, headers=headers, **kwargs)
    
    async def patch(self, path: str, data: Optional[Dict[str, Any]] = None,
                   token: Optional[str] = None, **kwargs) -> Union[httpx.Response, Dict[str, Any]]:
        """Execute PATCH request with retry logic."""
        url = f"{self.base_url}{path}"
        headers = self._get_auth_headers(token)
        if data is not None:
            kwargs["json"] = data
        return await self._execute_request("PATCH", url, headers=headers, **kwargs)
    
    async def _execute_request(self, method: str, url: str, 
                             return_response: bool = False,
                             **kwargs) -> Union[httpx.Response, Dict[str, Any]]:
        """Execute HTTP request with retry logic."""
        for attempt in range(self.config.max_retries + 1):
            try:
                self.metrics.requests_sent += 1
                response = await self._client.request(method, url, **kwargs)
                
                if return_response:
                    return response
                else:
                    return await self._process_response(response)
            except Exception as e:
                if attempt == self.config.max_retries:
                    self._record_error(str(e))
                    raise
                delay = self.config.get_retry_delay(attempt)
                await asyncio.sleep(delay)
    
    async def _process_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Process HTTP response."""
        self.metrics.responses_received += 1
        response.raise_for_status()
        
        # Handle different response types
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        else:
            return {"content": response.text, "status_code": response.status_code}
    
    def _record_error(self, error: str) -> None:
        """Record error in metrics."""
        self.metrics.last_error = error
        self.metrics.retry_count += 1
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


class AuthHTTPClient(UnifiedHTTPClient):
    """Specialized HTTP client for auth service testing."""
    
    def __init__(self, auth_url: str = "http://localhost:8001", config: Optional[ClientConfig] = None):
        """Initialize auth HTTP client."""
        super().__init__(auth_url, config)
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and get token."""
        return await self.post("/auth/login", {
            "username": username,
            "password": password
        })
    
    async def register(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register new user."""
        return await self.post("/auth/register", {
            "username": username,
            "email": email,
            "password": password
        })
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate token."""
        return await self.get("/auth/validate", token=token)
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token."""
        return await self.post("/auth/refresh", {
            "refresh_token": refresh_token
        })
    
    async def logout(self, token: str) -> Dict[str, Any]:
        """Logout and invalidate token."""
        return await self.post("/auth/logout", token=token)


class BackendHTTPClient(UnifiedHTTPClient):
    """Specialized HTTP client for backend service testing."""
    
    def __init__(self, backend_url: str = "http://localhost:8000", config: Optional[ClientConfig] = None):
        """Initialize backend HTTP client."""
        super().__init__(backend_url, config)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        return await self.get("/health")
    
    async def create_thread(self, token: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new thread."""
        return await self.post("/api/threads", data, token=token)
    
    async def send_message(self, thread_id: str, message: str, token: str) -> Dict[str, Any]:
        """Send message to thread."""
        return await self.post(f"/api/threads/{thread_id}/messages", {
            "content": message
        }, token=token)
    
    async def get_threads(self, token: str) -> Dict[str, Any]:
        """Get user threads."""
        return await self.get("/api/threads", token=token)


# Factory functions for common client configurations
def create_auth_client(config: Optional[ClientConfig] = None) -> AuthHTTPClient:
    """Create auth service HTTP client."""
    if not config:
        config = ClientConfig(base_url="http://localhost:8001")
    return AuthHTTPClient(config.base_url, config)


def create_backend_client(config: Optional[ClientConfig] = None) -> BackendHTTPClient:
    """Create backend service HTTP client."""
    if not config:
        config = ClientConfig(base_url="http://localhost:8000")
    return BackendHTTPClient(config.base_url, config)


def create_unified_client(base_url: str = "http://localhost:8000", 
                         config: Optional[ClientConfig] = None) -> UnifiedHTTPClient:
    """Create unified HTTP client."""
    return UnifiedHTTPClient(base_url, config)


def create_auth_config() -> ClientConfig:
    """Create default ClientConfig for auth service."""
    return ClientConfig(
        base_url="http://localhost:8001",
        auth_url="http://localhost:8001",
        timeout=30.0,
        max_retries=3
    )


def create_backend_config() -> ClientConfig:
    """Create default ClientConfig for backend service."""
    return ClientConfig(
        base_url="http://localhost:8000",
        timeout=30.0,
        max_retries=3
    )


def create_test_config(**kwargs) -> ClientConfig:
    """Create test ClientConfig with optional overrides."""
    defaults = {
        "base_url": "http://localhost:8000",
        "timeout": 30.0,
        "max_retries": 3
    }
    defaults.update(kwargs)
    return ClientConfig(**defaults)


# Legacy compatibility - maintains backward compatibility with existing tests
class TestClient(UnifiedHTTPClient):
    """Legacy TestClient - forwards to UnifiedHTTPClient for backward compatibility."""
    pass


class RealHTTPClient(UnifiedHTTPClient):
    """Legacy RealHTTPClient - forwards to UnifiedHTTPClient for backward compatibility."""
    pass