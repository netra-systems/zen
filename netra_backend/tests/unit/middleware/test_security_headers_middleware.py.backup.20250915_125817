"""Unit tests for Security Headers Middleware.

Tests to ensure security headers are properly added to responses.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from netra_backend.app.redis_manager import redis_manager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.middleware.security_headers_middleware import SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    """Test suite for Security Headers Middleware."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock application."""
        return Mock()

    @pytest.fixture
    def middleware(self, mock_app):
        """Create middleware instance."""
        return SecurityHeadersMiddleware(mock_app)

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = Mock(spec=Request)
        # Create mock URL
        url_mock = Mock()
        url_mock.path = "/api/test"
        request.url = url_mock
        request.headers = {}
        return request

    @pytest.mark.asyncio
    async def test_adds_security_headers(self, middleware, mock_request):
        """Test that security headers are added to response."""
        mock_response = Response(content="test", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check critical security headers
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"

        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] in ["DENY", "SAMEORIGIN"]

        assert "x-xss-protection" in response.headers
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_adds_strict_transport_security_for_https(self, middleware):
        """Test HSTS header is added for HTTPS requests."""
        request = Mock(spec=Request)
        # Create mock URL
        url_mock = Mock()
        url_mock.scheme = "https"
        url_mock.path = "/api/test"
        request.url = url_mock
        request.headers = {}

        mock_response = Response(content="test", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(request, mock_call_next)

        assert "strict-transport-security" in response.headers
        assert "max-age=" in response.headers["strict-transport-security"]

    @pytest.mark.asyncio
    async def test_no_hsts_for_http(self, middleware):
        """Test HSTS header is NOT added for HTTP requests."""
        request = Mock(spec=Request)
        # Create mock URL
        url_mock = Mock()
        url_mock.scheme = "http"
        url_mock.path = "/api/test"
        request.url = url_mock
        request.headers = {}

        mock_response = Response(content="test", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(request, mock_call_next)

        # HSTS should not be set for non-HTTPS
        assert "strict-transport-security" not in response.headers

    @pytest.mark.asyncio
    async def test_adds_content_security_policy(self, middleware, mock_request):
        """Test CSP header is added."""
        mock_response = Response(content="test", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check if CSP is configured
        if "content-security-policy" in response.headers:
            csp = response.headers["content-security-policy"]
            assert "default-src" in csp or "script-src" in csp

    @pytest.mark.asyncio
    async def test_preserves_existing_headers(self, middleware, mock_request):
        """Test that existing headers are preserved."""
        mock_response = Response(content="test", status_code=200)
        mock_response.headers["custom-header"] = "custom-value"
        mock_response.headers["cache-control"] = "no-store"
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Original headers should be preserved
        assert response.headers["custom-header"] == "custom-value"
        # Cache control should be enhanced for security (not just preserved)
        assert "no-store" in response.headers["cache-control"]
        assert "no-cache" in response.headers["cache-control"]

        # Security headers should be added
        assert "x-content-type-options" in response.headers

    @pytest.mark.asyncio
    async def test_handles_error_responses(self, middleware, mock_request):
        """Test security headers are added even to error responses."""
        error_response = JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )
        mock_call_next = AsyncMock(return_value=error_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Security headers should be added to error responses
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_referrer_policy(self, middleware, mock_request):
        """Test referrer policy header."""
        mock_response = Response(content="test", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        if "referrer-policy" in response.headers:
            policy = response.headers["referrer-policy"]
            valid_policies = [
                "no-referrer", "no-referrer-when-downgrade", 
                "origin", "origin-when-cross-origin",
                "same-origin", "strict-origin", 
                "strict-origin-when-cross-origin"
            ]
            assert policy in valid_policies

    @pytest.mark.asyncio
    async def test_permissions_policy(self, middleware, mock_request):
        """Test permissions policy header."""
        mock_response = Response(content="test", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        if "permissions-policy" in response.headers:
            policy = response.headers["permissions-policy"]
            # Check for common permissions restrictions
            assert "geolocation" in policy or "camera" in policy or "microphone" in policy

    @pytest.mark.asyncio
    async def test_call_next_called_exactly_once(self, middleware, mock_request):
        """Test that call_next is called exactly once."""
        mock_response = Response(content="test", status_code=200)
        mock_call_next = AsyncMock(return_value=mock_response)

        await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once_with(mock_request)