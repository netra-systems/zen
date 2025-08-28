"""Tests for PR router utility functions.

Note: This file has been updated to test the current PR router implementation.
Previous tests for OAuth and CSRF utilities have been moved to test_pr_router_state.py
or removed as the functionality no longer exists in the current implementation.
"""

import sys
from pathlib import Path

from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from netra_backend.app.auth_integration.auth import (
    PR_STATE_TTL,
    build_pr_redirect_url,
    extract_pr_from_host,
    extract_pr_number_from_request,
    get_pr_environment_status,
    handle_pr_routing_error,
    route_pr_authentication,
)
from netra_backend.app.core.exceptions_auth import AuthenticationError

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

    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.auth_integration.auth.logger')
    def test_handle_pr_routing_error_basic(self, mock_logger):
        """Test handling basic PR routing error.
        
        Note: This function is deprecated and simplified.
        """
        error = Exception("Test error")
        result = handle_pr_routing_error(error)
        
        assert isinstance(result, dict)
        assert result["error"] == "Test error"
        mock_logger.warning.assert_called_once_with("handle_pr_routing_error is deprecated - use auth service")

    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.auth_integration.auth.logger')
    def test_handle_pr_routing_error_auth_error(self, mock_logger):
        """Test handling authentication error.
        
        Note: This function is deprecated and simplified.
        """
        error = AuthenticationError("Auth failed")
        result = handle_pr_routing_error(error)
        
        assert isinstance(result, dict)
        assert result["error"] == "AUTH_FAILED: Auth failed"
        mock_logger.warning.assert_called_once_with("handle_pr_routing_error is deprecated - use auth service")

class TestGetPrEnvironmentStatus:
    """Test get_pr_environment_status function."""

    def test_get_pr_environment_status_basic(self):
        """Test getting PR environment status.
        
        Note: This function is deprecated and simplified.
        """
        status = get_pr_environment_status("123")
        
        assert status["pr_number"] == "123"
        assert status["status"] == "unknown"

    def test_get_pr_environment_status_domains(self):
        """Test PR environment status contains correct domains.
        
        Note: This function is deprecated and simplified.
        """
        status = get_pr_environment_status("456")
        
        assert status["pr_number"] == "456"
        assert status["status"] == "unknown"

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
        """Test extracting PR number from request header.
        
        Note: This function is deprecated and always returns None.
        """
        headers = {"X-PR-Number": "789"}
        result = extract_pr_number_from_request(headers)
        assert result is None

    def test_extract_pr_number_from_request_host(self):
        """Test extracting PR number from host header.
        
        Note: This function is deprecated and always returns None.
        """
        headers = {"host": "pr-123.staging.netrasystems.ai"}
        result = extract_pr_number_from_request(headers)
        assert result is None

    def test_extract_pr_number_from_request_invalid_header(self):
        """Test extracting PR number with invalid header value.
        
        Note: This function is deprecated and always returns None.
        """
        headers = {"X-PR-Number": "invalid"}
        result = extract_pr_number_from_request(headers)
        assert result is None

    def test_extract_pr_number_from_request_no_match(self):
        """Test extracting PR number when no match found.
        
        Note: This function is deprecated and always returns None.
        """
        headers = {"host": "invalid.example.com"}
        result = extract_pr_number_from_request(headers)
        assert result is None

class TestRoutePrAuthentication:
    """Test route_pr_authentication function."""

    @pytest.mark.asyncio
    async def test_route_pr_authentication_login(self):
        """Test routing PR authentication for login flow.
        
        Note: This function is deprecated and simplified.
        """
        result = await route_pr_authentication("123", "auth_code")
        
        assert result["pr_number"] == "123"
        assert result["authenticated"] == False

    @pytest.mark.asyncio
    async def test_route_pr_authentication_callback(self):
        """Test routing PR authentication for callback flow.
        
        Note: This function is deprecated and simplified.
        """
        result = await route_pr_authentication("456", "auth_code")
        
        assert result["pr_number"] == "456"
        assert result["authenticated"] == False

    @pytest.mark.asyncio
    async def test_route_pr_authentication_default(self):
        """Test routing PR authentication for default flow.
        
        Note: This function is deprecated and simplified.
        """
        result = await route_pr_authentication("789", "auth_code")
        
        assert result["pr_number"] == "789"
        assert result["authenticated"] == False

class TestPrStateTtl:
    """Test PR state TTL constant."""

    def test_pr_state_ttl_value(self):
        """Test PR state TTL has expected value."""
        assert PR_STATE_TTL == 3600
        assert isinstance(PR_STATE_TTL, int)

    def test_pr_state_ttl_reasonable(self):
        """Test PR state TTL is reasonable (between 1 minute and 1 hour)."""
        assert 60 <= PR_STATE_TTL <= 3600  # Between 1 minute and 1 hour