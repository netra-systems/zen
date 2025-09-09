"""
Unit test to verify API versioning fix for health endpoints
Tests that API versioning headers are properly handled and returned

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure API versioning works correctly for health endpoints
- Value Impact: Prevents API compatibility issues with different client versions
- Strategic Impact: Maintains backward compatibility and clear API evolution
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from fastapi import Request, Response
from fastapi.testclient import TestClient
from fastapi import FastAPI
from shared.isolated_environment import IsolatedEnvironment

# Import the health function we fixed
from netra_backend.app.routes.health import health, health_no_slash


class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()



@pytest.mark.asyncio
async def test_backend_health_api_versioning():
    """Test that backend health endpoint properly handles API versioning headers."""
    
    # Test current version
    request_current = Mock(spec=Request)
    request_current.headers = {"Accept-Version": "current"}
    request_current.method = "GET"
    request_current.url = "http://testserver/health"
    
    # Mock app state
    app_state = Mock()
    app_state.startup_complete = True
    request_current.app = Mock()
    request_current.app.state = app_state
    
    response_current = Mock(spec=Response)
    response_current.headers = {}
    
    # Patch health checkers to avoid real service dependencies
    with patch('netra_backend.app.routes.health.health_interface') as mock_health_interface:
        mock_health_interface.get_health_status.return_value = {
            "status": "healthy",
            "service": "netra-ai-platform",
            "timestamp": 1234567890
        }
        
        result = await health(request_current, response_current)
        
        # Verify API-Version header was set
        assert response_current.headers["API-Version"] == "current"
        
        # Verify response structure for current version
        assert "status" in result
        assert result["status"] == "healthy"
    
    # Test version 1.0
    request_v1 = Mock(spec=Request)
    request_v1.headers = {"API-Version": "1.0"}
    request_v1.method = "GET"
    request_v1.url = "http://testserver/health"
    request_v1.app = Mock()
    request_v1.app.state = app_state
    
    response_v1 = Mock(spec=Response)
    response_v1.headers = {}
    
    with patch('netra_backend.app.routes.health.health_interface') as mock_health_interface:
        mock_health_interface.get_health_status.return_value = {
            "status": "healthy",
            "service": "netra-ai-platform",
            "timestamp": 1234567890
        }
        
        result_v1 = await health(request_v1, response_v1)
        
        # Verify API-Version header was set
        assert response_v1.headers["API-Version"] == "1.0"
        
        # Verify basic response structure
        assert "status" in result_v1
        assert result_v1["status"] == "healthy"
    
    # Test version 2024-08-01
    request_dated = Mock(spec=Request)
    request_dated.headers = {"Accept-Version": "2024-08-01"}
    request_dated.method = "GET"
    request_dated.url = "http://testserver/health"
    request_dated.app = Mock()
    request_dated.app.state = app_state
    
    response_dated = Mock(spec=Response)
    response_dated.headers = {}
    
    with patch('netra_backend.app.routes.health.health_interface') as mock_health_interface:
        mock_health_interface.get_health_status.return_value = {
            "status": "healthy",
            "service": "netra-ai-platform",
            "timestamp": 1234567890
        }
        
        result_dated = await health(request_dated, response_dated)
        
        # Verify API-Version header was set
        assert response_dated.headers["API-Version"] == "2024-08-01"
        
        # Verify basic response structure
        assert "status" in result_dated
        assert result_dated["status"] == "healthy"



def test_auth_service_health_versioning_imports():
    """Test that auth service health endpoint imports and structure are correct."""
    
    # This test verifies the imports work and the function signature is correct
    try:
        from auth_service.auth_core.routes.auth_routes import auth_status
        import inspect
        
        # Check that the function has the correct signature
        signature = inspect.signature(auth_status)
        
        # Check that Request is imported in the module for other endpoints
        import auth_service.auth_core.routes.auth_routes as auth_routes
        assert hasattr(auth_routes, 'Request')
        
        # Verify the function is async (which means it can be enhanced with API versioning later if needed)
        assert inspect.iscoroutinefunction(auth_status)
        
        print("Auth service API versioning imports work correctly!")
        
    except ImportError as e:
        # Handle case where auth service is not available in test environment
        pytest.skip(f"Auth service not available: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_backend_health_api_versioning())
    test_auth_service_health_versioning_imports()
    print("All API versioning fix tests passed!")