"""
Test for CORS middleware async context manager bug fix.

Tests that the middleware properly handles both normal callable 
and async context manager wrapped call_next parameters.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from netra_backend.app.middleware.cors_fix_middleware import CORSFixMiddleware


class _AsyncGeneratorContextManager:
    """Mock the specific _AsyncGeneratorContextManager that causes the error."""
    
    def __init__(self, call_next):
        self.call_next = call_next
        
    async def __aenter__(self):
        return self.call_next
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_cors_middleware_handles_normal_callable():
    """Test that middleware works with normal callable call_next."""
    # Create mock app and request
    app = MagicMock()
    middleware = CORSFixMiddleware(app, environment="development")
    
    # Create mock request with origin
    request = MagicMock(spec=Request)
    request.headers = {"origin": "http://localhost:3000"}
    request.url.path = "/api/test"
    
    # Create mock call_next that returns a response
    expected_response = Response(content="test", status_code=200)
    call_next = AsyncMock(return_value=expected_response)
    
    # Call dispatch
    response = await middleware.dispatch(request, call_next)
    
    # Verify call_next was called with request
    call_next.assert_called_once_with(request)
    
    # Verify response has CORS headers
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cors_middleware_handles_context_manager_wrapped_callable():
    """Test that middleware handles call_next wrapped in async context manager."""
    # Create mock app and request
    app = MagicMock()
    middleware = CORSFixMiddleware(app, environment="development")
    
    # Create mock request with origin
    request = MagicMock(spec=Request)
    request.headers = {"origin": "http://localhost:3000"}
    request.url.path = "/api/test"
    
    # Create mock call_next wrapped in context manager
    expected_response = Response(content="test", status_code=200)
    actual_call_next = AsyncMock(return_value=expected_response)
    call_next_context_manager = _AsyncGeneratorContextManager(actual_call_next)
    
    # Call dispatch with context manager
    response = await middleware.dispatch(request, call_next_context_manager)
    
    # Verify the actual call_next was called with request
    actual_call_next.assert_called_once_with(request)
    
    # Verify response has CORS headers
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cors_middleware_handles_error_with_context_manager():
    """Test error handling when call_next is wrapped in context manager."""
    # Create mock app and request
    app = MagicMock()
    middleware = CORSFixMiddleware(app, environment="development")
    
    # Create mock request with origin
    request = MagicMock(spec=Request)
    request.headers = {"origin": "http://localhost:3000"}
    request.url.path = "/api/test"
    
    # Create mock call_next that raises an error
    actual_call_next = AsyncMock(side_effect=Exception("Test error"))
    call_next_context_manager = _AsyncGeneratorContextManager(actual_call_next)
    
    # Call dispatch with context manager that will error
    response = await middleware.dispatch(request, call_next_context_manager)
    
    # Verify error response is created with CORS headers
    assert response.status_code == 500
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    
    # Verify it's a JSON error response
    assert isinstance(response, JSONResponse)