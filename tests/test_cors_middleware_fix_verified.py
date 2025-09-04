"""
Test to verify CORS middleware fix for AsyncGeneratorContextManager bug.

This test ensures that the middleware correctly handles call_next as a simple
callable without attempting to treat it as a context manager.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from netra_backend.app.middleware.cors_fix_middleware import CORSFixMiddleware


@pytest.mark.asyncio
async def test_cors_middleware_direct_call_next():
    """Test that middleware directly calls call_next without context manager handling."""
    # Create mock app and middleware
    app = MagicMock()
    middleware = CORSFixMiddleware(app, environment="development")
    
    # Create mock request with valid origin
    request = MagicMock(spec=Request)
    request.headers = {"origin": "http://localhost:3000"}
    request.url.path = "/api/test"
    
    # Create mock response
    expected_response = Response(content="test", status_code=200)
    
    # Create mock call_next that returns response
    call_next = AsyncMock(return_value=expected_response)
    
    # Execute middleware
    response = await middleware.dispatch(request, call_next)
    
    # Verify call_next was called directly with request
    call_next.assert_called_once_with(request)
    
    # Verify response is correct
    assert response.status_code == 200
    
    # Verify CORS headers were added
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


@pytest.mark.asyncio
async def test_cors_middleware_error_handling():
    """Test that middleware properly handles errors from call_next."""
    # Create mock app and middleware
    app = MagicMock()
    middleware = CORSFixMiddleware(app, environment="development")
    
    # Create mock request with valid origin
    request = MagicMock(spec=Request)
    request.headers = {"origin": "http://localhost:3000"}
    request.url.path = "/api/test"
    
    # Create mock call_next that raises an error
    error_message = "Test error from downstream"
    call_next = AsyncMock(side_effect=Exception(error_message))
    
    # Execute middleware - should handle error gracefully
    response = await middleware.dispatch(request, call_next)
    
    # Verify call_next was called
    call_next.assert_called_once_with(request)
    
    # Verify error response is created
    assert response.status_code == 500
    assert isinstance(response, JSONResponse)
    
    # Verify CORS headers are added even on error
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"


@pytest.mark.asyncio
async def test_cors_middleware_no_origin():
    """Test middleware behavior when no origin header is present."""
    # Create mock app and middleware
    app = MagicMock()
    middleware = CORSFixMiddleware(app, environment="development")
    
    # Create request without origin header
    request = MagicMock(spec=Request)
    request.headers = {}
    request.url.path = "/api/test"
    
    # Create mock response
    expected_response = Response(content="test", status_code=200)
    call_next = AsyncMock(return_value=expected_response)
    
    # Execute middleware
    response = await middleware.dispatch(request, call_next)
    
    # Verify call_next was called
    call_next.assert_called_once_with(request)
    
    # Verify response but no CORS headers added (no origin)
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.asyncio  
async def test_cors_middleware_invalid_origin():
    """Test middleware behavior with invalid origin."""
    # Create mock app and middleware
    app = MagicMock()
    middleware = CORSFixMiddleware(app, environment="development")
    
    # Create request with invalid origin
    request = MagicMock(spec=Request)
    request.headers = {"origin": "http://malicious.com"}
    request.url.path = "/api/test"
    
    # Create mock response
    expected_response = Response(content="test", status_code=200)
    call_next = AsyncMock(return_value=expected_response)
    
    # Execute middleware
    response = await middleware.dispatch(request, call_next)
    
    # Verify call_next was called
    call_next.assert_called_once_with(request)
    
    # Verify response but no CORS headers for invalid origin
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.asyncio
async def test_cors_middleware_preflight_request():
    """Test middleware handles OPTIONS preflight requests."""
    # Create mock app and middleware
    app = MagicMock()
    middleware = CORSFixMiddleware(app, environment="development")
    
    # Create OPTIONS request with origin
    request = MagicMock(spec=Request)
    request.method = "OPTIONS"
    request.headers = {
        "origin": "http://localhost:3000",
        "access-control-request-method": "POST"
    }
    request.url.path = "/api/test"
    
    # Create mock response for OPTIONS
    expected_response = Response(status_code=200)
    call_next = AsyncMock(return_value=expected_response)
    
    # Execute middleware
    response = await middleware.dispatch(request, call_next)
    
    # Verify call_next was called
    call_next.assert_called_once_with(request)
    
    # Verify CORS headers are present for preflight
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "Access-Control-Allow-Methods" in response.headers
    assert "Access-Control-Allow-Headers" in response.headers