"""Unit tests for Error Recovery Middleware.

Tests to ensure the middleware correctly handles errors and recovers gracefully.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from test_framework.database.test_database_manager import TestDatabaseManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.middleware.error_recovery_middleware import ErrorRecoveryMiddleware


class TestErrorRecoveryMiddleware:
    """Test suite for Error Recovery Middleware."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock application."""
        return Mock()

    @pytest.fixture
    def middleware(self, mock_app):
        """Create middleware instance."""
        return ErrorRecoveryMiddleware(mock_app)

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = Mock(spec=Request)
        # Create mock URL
        url_mock = Mock()
        url_mock.path = "/api/test"
        request.url = url_mock
        request.method = "GET"
        request.headers = {}
        return request

    @pytest.mark.asyncio
    async def test_successful_request_passthrough(self, middleware, mock_request):
        """Test that successful requests pass through unchanged."""
        mock_response = Response(content="success", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert response.body == b"success"
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_handles_generic_exception(self, middleware, mock_request):
        """Test handling of generic exceptions in development environment."""
        mock_call_next = AsyncMock(side_effect=Exception("Generic error"))

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 500
        assert isinstance(response, JSONResponse)
        # In development environment, error details should be included for debugging
        response_body = response.body.decode() if hasattr(response.body, 'decode') else str(response.body)
        assert "Generic error" in response_body

    @pytest.mark.asyncio
    async def test_handles_value_error(self, middleware, mock_request):
        """Test handling of ValueError with appropriate status code."""
        mock_call_next = AsyncMock(side_effect=ValueError("Invalid value"))

        response = await middleware.dispatch(mock_request, mock_call_next)

        # ValueError typically indicates bad request
        assert response.status_code in [400, 500]
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self, middleware, mock_request):
        """Test handling of timeout errors."""
        mock_call_next = AsyncMock(side_effect=TimeoutError("Request timeout"))

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code in [408, 500]  # Request Timeout or Internal Server Error
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_preserves_error_response_status(self, middleware, mock_request):
        """Test that error responses with specific status codes are preserved."""
        error_response = JSONResponse(
            status_code=403,
            content={"error": "Forbidden"}
        )
        mock_call_next = AsyncMock(return_value=error_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 403
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_logs_errors(self, middleware, mock_request):
        """Test that errors are properly logged."""
        with patch('netra_backend.app.middleware.error_recovery_middleware.logger') as mock_logger:
            mock_call_next = AsyncMock(side_effect=Exception("Test error"))

            response = await middleware.dispatch(mock_request, mock_call_next)

            # Verify error was logged
            assert mock_logger.error.called
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_recovery_for_database_error(self, middleware, mock_request):
        """Test recovery from database errors."""
        from sqlalchemy.exc import OperationalError
        mock_call_next = AsyncMock(
            side_effect=OperationalError("Database connection lost", None, None)
        )

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 503  # Service Unavailable
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_no_error_details_in_production(self, middleware, mock_request):
        """Test that error details are not exposed in production."""
        # Mock production environment
        with patch.dict('os.environ', {'ENVIRONMENT': 'production'}):
            mock_call_next = AsyncMock(side_effect=Exception("Sensitive error details"))

            response = await middleware.dispatch(mock_request, mock_call_next)

            # Error details should not be in response
            response_body = response.body.decode() if hasattr(response.body, 'decode') else str(response.body)
            assert "Sensitive error details" not in response_body
            assert response.status_code == 500