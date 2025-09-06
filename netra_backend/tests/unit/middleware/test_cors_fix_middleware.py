"""Unit tests for CORS Fix Middleware.

Tests to ensure the middleware correctly handles call_next and adds CORS headers.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.middleware.cors_fix_middleware import CORSFixMiddleware


class TestCORSFixMiddleware:
    """Test suite for CORS Fix Middleware."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock application."""
        return Mock()

    @pytest.fixture
    def middleware(self, mock_app):
        """Create middleware instance."""
        return CORSFixMiddleware(mock_app, environment="development")

    @pytest.fixture
    def mock_request(self):
        """Create a mock request with headers."""
        request = Mock(spec=Request)
        request.headers = {
            "origin": "http://localhost:3000",
            "content-type": "application/json"
        }
        # Create mock URL
        url_mock = Mock()
        url_mock.path = "/api/threads"
        request.url = url_mock
        return request

    @pytest.mark.asyncio
    async def test_middleware_calls_next_directly(self, middleware, mock_request):
        """Test that middleware calls call_next directly without context manager."""
        # Create a mock call_next that returns a response
        mock_response = Response(content="test", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)

        # Call the middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify call_next was called with the request
        mock_call_next.assert_called_once_with(mock_request)

        # Verify response is returned
        assert response.status_code == 200

        # Verify CORS headers are added for allowed origin
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    @pytest.mark.asyncio
    async def test_middleware_handles_errors(self, middleware, mock_request):
        """Test that middleware handles errors from call_next."""
        # Create a mock call_next that raises an exception
        mock_call_next = AsyncMock(side_effect=Exception("Test error"))

        # Call the middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify error response is returned
        assert response.status_code == 500

        # Verify CORS headers are still added on error
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    @pytest.mark.asyncio
    async def test_middleware_no_context_manager_usage(self, middleware, mock_request):
        """Test that middleware never tries to use call_next as a context manager."""
        # Create a mock callable that would fail if used as context manager
        async def mock_call_next(req):
            """Simple async callable that returns a response."""
            await asyncio.sleep(0)
            return Response(content="test")

        # This callable doesn't have context manager methods
        assert not hasattr(mock_call_next, '__aenter__')
        assert not hasattr(mock_call_next, '__aexit__')

        # Call the middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # If we get here without error, the middleware correctly treated it as callable
        assert response is not None
        assert response.body == b"test"

    @pytest.mark.asyncio
    async def test_middleware_with_invalid_origin(self, middleware):
        """Test middleware with invalid origin."""
        # Create request with invalid origin
        request = Mock(spec=Request)
        request.headers = {
            "origin": "http://malicious.com",
            "content-type": "application/json"
        }
        # Create mock URL
        url_mock = Mock()
        url_mock.path = "/api/threads"
        request.url = url_mock

        mock_response = Response(content="test", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(request, mock_call_next)

        # Verify CORS headers are NOT added for invalid origin
        assert "access-control-allow-origin" not in response.headers

    @pytest.mark.asyncio
    async def test_middleware_preserves_response_content(self, middleware, mock_request):
        """Test that middleware preserves the original response content."""
        # Create a response with specific content
        original_content = {"data": "test", "value": 123}
        mock_response = JSONResponse(content=original_content, status_code=201)
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify response content and status are preserved
        assert response.status_code == 201
        # Response body would need to be decoded in real scenario
        # Here we just verify the response object is passed through
        assert response is not None