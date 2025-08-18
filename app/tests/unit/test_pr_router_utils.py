"""Tests for PR router utility functions.

Note: This file has been updated to test the current PR router implementation.
Previous tests for OAuth and CSRF utilities have been moved to test_pr_router_state.py
or removed as the functionality no longer exists in the current implementation.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from app.auth.pr_router import (
    build_pr_redirect_url,
    handle_pr_routing_error,
    get_pr_environment_status,
    extract_pr_number_from_request,
    extract_pr_from_host,
    route_pr_authentication,
    PR_STATE_TTL
)
from app.core.exceptions_auth import AuthenticationError


class TestBuildPrRedirectUrl:
    """Test build_pr_redirect_url function."""

    def test_build_pr_redirect_url_default_path(self):
        """Test building PR redirect URL with default path."""
        result = build_pr_redirect_url("123")
        expected = "https://pr-123.staging.netrasystems.ai/"
        assert result == expected

    def test_build_pr_redirect_url_custom_path(self):
        """Test building PR redirect URL with custom path."""
        result = build_pr_redirect_url("456", "/dashboard")
        expected = "https://pr-456.staging.netrasystems.ai/dashboard"
        assert result == expected

    def test_build_pr_redirect_url_with_query(self):
        """Test building PR redirect URL with query parameters."""
        result = build_pr_redirect_url("789", "/app?param=value")
        expected = "https://pr-789.staging.netrasystems.ai/app?param=value"
        assert result == expected


class TestHandlePrRoutingError:
    """Test handle_pr_routing_error function."""

    @patch('app.auth.pr_router.logger')
    def test_handle_pr_routing_error_basic(self, mock_logger):
        """Test handling basic PR routing error."""
        error = Exception("Test error")
        result = handle_pr_routing_error(error, "123")
        
        assert isinstance(result, HTTPException)
        assert result.status_code == 400
        assert "Invalid PR environment configuration: 123" in result.detail
        mock_logger.error.assert_called_once()

    @patch('app.auth.pr_router.logger')
    def test_handle_pr_routing_error_auth_error(self, mock_logger):
        """Test handling authentication error."""
        error = AuthenticationError("Auth failed")
        result = handle_pr_routing_error(error, "456")
        
        assert isinstance(result, HTTPException)
        assert result.status_code == 400
        mock_logger.error.assert_called_once()
        # Check that the error message contains the expected parts
        call_args = mock_logger.error.call_args[0][0]
        assert "PR routing error for PR 456:" in call_args
        assert "Auth failed" in call_args


class TestGetPrEnvironmentStatus:
    """Test get_pr_environment_status function."""

    def test_get_pr_environment_status_basic(self):
        """Test getting PR environment status."""
        status = get_pr_environment_status("123")
        
        assert status["pr_number"] == "123"
        assert status["status"] == "active"
        assert "auth_domain" in status
        assert "frontend_domain" in status
        assert "api_domain" in status
        assert "last_updated" in status

    def test_get_pr_environment_status_domains(self):
        """Test PR environment status contains correct domains."""
        status = get_pr_environment_status("456")
        
        assert "auth-pr-456" in status["auth_domain"]
        assert "pr-456.staging.netrasystems.ai" in status["frontend_domain"]
        assert "pr-456-api.staging.netrasystems.ai" in status["api_domain"]


class TestExtractPrNumber:
    """Test PR number extraction functions."""

    def test_extract_pr_from_host_frontend(self):
        """Test extracting PR number from frontend host."""
        result = extract_pr_from_host("pr-123.staging.netrasystems.ai")
        assert result == "123"

    def test_extract_pr_from_host_api(self):
        """Test extracting PR number from API host."""
        result = extract_pr_from_host("pr-456-api.staging.netrasystems.ai")
        assert result == "456"

    def test_extract_pr_from_host_invalid(self):
        """Test extracting PR number from invalid host."""
        result = extract_pr_from_host("invalid.example.com")
        assert result is None

    def test_extract_pr_from_host_wrong_domain(self):
        """Test extracting PR number from wrong domain."""
        result = extract_pr_from_host("pr-123.wrongdomain.com")
        assert result is None

    def test_extract_pr_number_from_request_header(self):
        """Test extracting PR number from request header."""
        headers = {"X-PR-Number": "789"}
        result = extract_pr_number_from_request(headers)
        assert result == "789"

    def test_extract_pr_number_from_request_host(self):
        """Test extracting PR number from host header."""
        headers = {"host": "pr-123.staging.netrasystems.ai"}
        result = extract_pr_number_from_request(headers)
        assert result == "123"

    def test_extract_pr_number_from_request_invalid_header(self):
        """Test extracting PR number with invalid header value."""
        headers = {"X-PR-Number": "invalid"}
        result = extract_pr_number_from_request(headers)
        assert result is None

    def test_extract_pr_number_from_request_no_match(self):
        """Test extracting PR number when no match found."""
        headers = {"host": "invalid.example.com"}
        result = extract_pr_number_from_request(headers)
        assert result is None


class TestRoutePrAuthentication:
    """Test route_pr_authentication function."""

    def test_route_pr_authentication_login(self):
        """Test routing PR authentication for login flow."""
        redirect_url, config = route_pr_authentication("123", "login")
        
        assert "auth-pr-123" in redirect_url
        assert "/auth/login" in redirect_url
        assert config["pr_number"] == "123"
        assert config["environment"] == "pr"

    def test_route_pr_authentication_login_with_return_url(self):
        """Test routing PR authentication for login with return URL."""
        return_url = "https://example.com"
        redirect_url, config = route_pr_authentication("123", "login", return_url)
        
        assert "auth-pr-123" in redirect_url
        assert "/auth/login" in redirect_url
        assert f"return_url={return_url}" in redirect_url
        assert "pr=123" in redirect_url

    def test_route_pr_authentication_callback(self):
        """Test routing PR authentication for callback flow."""
        redirect_url, config = route_pr_authentication("456", "callback")
        
        assert "pr-456.staging.netrasystems.ai" in redirect_url
        assert "/auth/callback" in redirect_url
        assert config["pr_number"] == "456"

    def test_route_pr_authentication_default(self):
        """Test routing PR authentication for default flow."""
        redirect_url, config = route_pr_authentication("789", "default")
        
        assert redirect_url == "https://pr-789.staging.netrasystems.ai"
        assert config["pr_number"] == "789"


class TestPrStateTtl:
    """Test PR state TTL constant."""

    def test_pr_state_ttl_value(self):
        """Test PR state TTL has expected value."""
        assert PR_STATE_TTL == 300
        assert isinstance(PR_STATE_TTL, int)

    def test_pr_state_ttl_reasonable(self):
        """Test PR state TTL is reasonable (between 1 minute and 1 hour)."""
        assert 60 <= PR_STATE_TTL <= 3600  # Between 1 minute and 1 hour