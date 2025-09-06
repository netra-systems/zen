"""
Base class for staging environment tests.
Provides common functionality for all staging E2E tests.
"""

import asyncio
import pytest
import httpx
import websockets
import json
from typing import Optional, Dict, Any
from tests.e2e.staging_test_config import get_staging_config, is_staging_available


class StagingTestBase:
    """Base class for staging environment tests"""
    
    @classmethod
    def setup_class(cls):
        """Setup for test class"""
        cls.config = get_staging_config()
        cls.client = None
        cls.websocket = None
        
        # Skip all tests if staging is not available
        if not is_staging_available():
            pytest.skip("Staging environment is not available")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup after test class"""
        if cls.client:
            asyncio.run(cls.client.aclose())
        if cls.websocket:
            asyncio.run(cls.websocket.close())
    
    async def get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP client for API calls"""
        if not self.client:
            self.client = httpx.AsyncClient(
                base_url=self.config.backend_url,
                timeout=self.config.timeout,
                headers=self.config.get_headers()
            )
        return self.client
    
    async def get_websocket_connection(self) -> websockets.WebSocketClientProtocol:
        """Get WebSocket connection"""
        if not self.websocket:
            headers = self.config.get_websocket_headers()
            try:
                self.websocket = await websockets.connect(
                    self.config.websocket_url,
                    extra_headers=headers if headers else None
                )
            except Exception as e:
                if self.config.skip_websocket_auth:
                    pytest.skip(f"WebSocket requires authentication: {e}")
                raise
        return self.websocket
    
    async def call_api(
        self,
        endpoint: str,
        method: str = "GET",
        json_data: Optional[Dict[str, Any]] = None,
        include_auth: bool = False
    ) -> httpx.Response:
        """Call API endpoint"""
        client = await self.get_http_client()
        
        headers = self.config.get_headers(include_auth)
        
        if method == "GET":
            response = await client.get(endpoint, headers=headers)
        elif method == "POST":
            response = await client.post(endpoint, json=json_data, headers=headers)
        elif method == "PUT":
            response = await client.put(endpoint, json=json_data, headers=headers)
        elif method == "DELETE":
            response = await client.delete(endpoint, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return response
    
    async def send_websocket_message(self, message: Dict[str, Any]) -> Optional[str]:
        """Send WebSocket message and wait for response"""
        ws = await self.get_websocket_connection()
        
        await ws.send(json.dumps(message))
        
        try:
            response = await asyncio.wait_for(ws.recv(), timeout=self.config.timeout)
            return response
        except asyncio.TimeoutError:
            return None
    
    async def verify_health(self):
        """Verify backend health"""
        response = await self.call_api("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        return True
    
    async def verify_api_health(self):
        """Verify API health"""
        response = await self.call_api("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        return True
    
    def assert_websocket_event(self, event: str, event_type: str):
        """Assert WebSocket event structure"""
        try:
            data = json.loads(event)
            assert "type" in data, f"Missing 'type' field in event: {data}"
            assert data["type"] == event_type, f"Expected type '{event_type}', got '{data['type']}'"
            return data
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON in WebSocket event: {event}")
    
    async def wait_for_websocket_event(
        self,
        event_type: str,
        timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Wait for specific WebSocket event type"""
        ws = await self.get_websocket_connection()
        timeout = timeout or self.config.timeout
        
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=1)
                data = json.loads(response)
                if data.get("type") == event_type:
                    return data
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError:
                continue
        
        return None


# Decorator to mark tests as staging tests
def staging_test(func):
    """Decorator to mark and configure staging tests"""
    @pytest.mark.staging
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not is_staging_available(),
        reason="Staging environment is not available"
    )
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper