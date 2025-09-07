# Shim module for test utilities
from test_framework.utils import *
from test_framework.http_client import *
from typing import Dict, Any, Optional
import asyncio
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment


class MockHTTPClient:
    """Mock HTTP client for testing."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_headers: Dict[str, str] = {}
        self.request_history: list = []
        self.mock_responses: Dict[str, Dict[str, Any]] = {}
        
    async def get(self, path: str, headers: Dict[str, str] = None, **kwargs):
        """Mock GET request."""
        return await self._make_request("GET", path, headers, **kwargs)
    
    async def post(self, path: str, json: Dict[str, Any] = None, 
                   headers: Dict[str, str] = None, **kwargs):
        """Mock POST request."""
        return await self._make_request("POST", path, headers, json=json, **kwargs)
    
    async def put(self, path: str, json: Dict[str, Any] = None,
                  headers: Dict[str, str] = None, **kwargs):
        """Mock PUT request."""
        return await self._make_request("PUT", path, headers, json=json, **kwargs)
    
    async def delete(self, path: str, headers: Dict[str, str] = None, **kwargs):
        """Mock DELETE request."""
        return await self._make_request("DELETE", path, headers, **kwargs)
    
    async def _make_request(self, method: str, path: str, headers: Dict[str, str] = None, **kwargs):
        """Make a mock HTTP request."""
        combined_headers = {**self.session_headers}
        if headers:
            combined_headers.update(headers)
        
        request_data = {
            "method": method,
            "url": f"{self.base_url}{path}",
            "headers": combined_headers,
            "kwargs": kwargs
        }
        self.request_history.append(request_data)
        
        # Check for mock response
        mock_key = f"{method}:{path}"
        if mock_key in self.mock_responses:
            response_data = self.mock_responses[mock_key]
            return MockResponse(
                status_code=response_data.get("status_code", 200),
                json_data=response_data.get("json", {}),
                headers=response_data.get("headers", {})
            )
        
        # Default successful response
        return MockResponse(200, {"status": "success", "method": method, "path": path})
    
    def set_mock_response(self, method: str, path: str, status_code: int = 200,
                         json_data: Dict[str, Any] = None, headers: Dict[str, str] = None):
        """Set a mock response for a specific endpoint."""
        mock_key = f"{method}:{path}"
        self.mock_responses[mock_key] = {
            "status_code": status_code,
            "json": json_data or {},
            "headers": headers or {}
        }
    
    def set_session_header(self, key: str, value: str):
        """Set a session header."""
        self.session_headers[key] = value


class MockResponse:
    """Mock HTTP response."""
    
    def __init__(self, status_code: int = 200, json_data: Dict[str, Any] = None,
                 headers: Dict[str, str] = None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {}
        
    async def json(self):
        """Get JSON response data."""
        return self._json_data
    
    def json_sync(self):
        """Get JSON response data synchronously."""
        return self._json_data
    
    @property
    def ok(self):
        """Check if response is successful."""
        return 200 <= self.status_code < 300


# Create base_client as an alias for MockHTTPClient
base_client = MockHTTPClient


def create_test_client(base_url: str = "http://localhost:8000") -> MockHTTPClient:
    """Create a test HTTP client."""
    return MockHTTPClient(base_url)


def create_authenticated_client(token: str, base_url: str = "http://localhost:8000") -> MockHTTPClient:
    """Create an authenticated test client."""
    client = MockHTTPClient(base_url)
    client.set_session_header("Authorization", f"Bearer {token}")
    return client


async def setup_test_client_with_auth() -> MockHTTPClient:
    """Set up a test client with authentication."""
    client = create_test_client()
    
    # Mock successful authentication response
    client.set_mock_response("POST", "/auth/login", 200, {
        "access_token": "mock_token_123",
        "token_type": "bearer",
        "expires_in": 3600
    })
    
    # Perform mock login
    response = await client.post("/auth/login", json={
        "username": "test_user",
        "password": "test_password"
    })
    
    if response.ok:
        token_data = await response.json()
        client.set_session_header("Authorization", f"Bearer {token_data['access_token']}")
    
    return client
