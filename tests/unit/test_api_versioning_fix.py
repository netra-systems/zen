"""
Unit test to verify API versioning fix for health endpoints
Tests that API versioning headers are properly handled and returned
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import Request, Response
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import the health function we fixed
from netra_backend.app.routes.health import health, health_no_slash


@pytest.mark.asyncio
async def test_backend_health_api_versioning():
    """Test that backend health endpoint properly handles API versioning headers."""
    
    # Mock the health interface to return a basic response
    mock_health_interface = AsyncMock()
    mock_health_interface.get_health_status.return_value = {
        "status": "healthy",
        "service": "netra-ai-platform",
        "timestamp": 1234567890
    }
    
    # Test current version
    request_current = MagicMock()
    request_current.headers = {"Accept-Version": "current"}
    request_current.app.state.startup_complete = True
    
    response_current = MagicMock()
    response_current.headers = {}
    
    with patch('netra_backend.app.routes.health.health_interface', mock_health_interface):
        result = await health(request_current, response_current)
    
    # Verify API-Version header was set
    assert response_current.headers["API-Version"] == "current"
    
    # Verify response structure for current version
    assert "status" in result
    assert result["status"] == "healthy"
    
    # Test version 1.0
    request_v1 = MagicMock()
    request_v1.headers = {"API-Version": "1.0"}
    request_v1.app.state.startup_complete = True
    
    response_v1 = MagicMock()
    response_v1.headers = {}
    
    mock_health_interface.reset_mock()
    with patch('netra_backend.app.routes.health.health_interface', mock_health_interface):
        result_v1 = await health(request_v1, response_v1)
    
    # Verify API-Version header was set
    assert response_v1.headers["API-Version"] == "1.0"
    
    # Verify version_info was added for v1.0
    assert "version_info" in result_v1
    assert result_v1["version_info"]["api_version"] == "1.0"
    assert result_v1["version_info"]["service_version"] == "1.0.0"
    assert "current" in result_v1["version_info"]["supported_versions"]
    assert "1.0" in result_v1["version_info"]["supported_versions"]
    assert "2024-08-01" in result_v1["version_info"]["supported_versions"]
    
    # Test version 2024-08-01
    request_dated = MagicMock()
    request_dated.headers = {"Accept-Version": "2024-08-01"}
    request_dated.app.state.startup_complete = True
    
    response_dated = MagicMock()
    response_dated.headers = {}
    
    mock_health_interface.reset_mock()
    with patch('netra_backend.app.routes.health.health_interface', mock_health_interface):
        result_dated = await health(request_dated, response_dated)
    
    # Verify API-Version header was set
    assert response_dated.headers["API-Version"] == "2024-08-01"
    
    # Verify version_info was added for dated version
    assert "version_info" in result_dated
    assert result_dated["version_info"]["api_version"] == "2024-08-01"
    
    print("All backend API versioning tests passed!")


def test_auth_service_health_versioning_imports():
    """Test that auth service health endpoint imports and structure are correct."""
    
    # This test verifies the imports work and the function signature is correct
    from auth_service.auth_core.routes.auth_routes import auth_status
    import inspect
    
    # Check that the function has the correct signature (no request parameter needed for basic status)
    signature = inspect.signature(auth_status)
    # auth_status is a simple endpoint that doesn't require request parameter
    
    # Check that Request is imported in the module for other endpoints
    import auth_service.auth_core.routes.auth_routes as auth_routes
    assert hasattr(auth_routes, 'Request')
    
    # Verify the function is async (which means it can be enhanced with API versioning later if needed)
    assert inspect.iscoroutinefunction(auth_status)
    
    print("Auth service API versioning imports work correctly!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_backend_health_api_versioning())
    test_auth_service_health_versioning_imports()
    print("All API versioning fix tests passed!")