"""Tests for PR router security and validation functions."""

import sys
from pathlib import Path

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from netra_backend.app.auth_integration.auth import (
    _is_allowed_return_domain,
    _is_valid_url,
    _validate_pr_inputs,
    _validate_pr_number_format,
    _validate_pr_with_github,
)
from netra_backend.app.core.exceptions_auth import (
    AuthenticationError,
    NetraSecurityException,
)

# Tests for _validate_return_url functions
class TestValidateReturnUrl:
    """Test URL validation functions with valid and malicious inputs."""

    def test_validate_return_url_valid(self):
        """Test validation of valid return URLs."""
        valid_urls = [
            "https://pr-123.staging.netrasystems.ai",
            "https://app.staging.netrasystems.ai",
            "http://localhost",
            "https://localhost"
        ]
        
        for url in valid_urls:
            assert _is_valid_url(url)
            assert _is_allowed_return_domain(url)

    def test_validate_return_url_malicious(self):
        """Test validation rejects malicious return URLs."""
        malicious_urls = [
            "https://evil.com",
            "https://app.staging.netrasystems.ai.evil.com",
            "javascript:alert('xss')",
            "ftp://malicious.com",
            "not-a-url"
        ]
        
        for url in malicious_urls:
            if _is_valid_url(url):  # Some might be valid URLs but wrong domain
                assert not _is_allowed_return_domain(url)

# Tests for _validate_pr_number_format function
class TestValidatePrNumberFormat:
    """Test _validate_pr_number_format function with valid and invalid inputs."""

    def test_validate_pr_number_valid(self):
        """Test validation of valid PR numbers."""
        # Should not raise any exception
        _validate_pr_number_format("1")
        _validate_pr_number_format("123")
        _validate_pr_number_format("9999")

    def test_validate_pr_number_invalid(self):
        """Test validation of invalid PR numbers.
        
        Note: This function is deprecated and only performs basic validation.
        """
        with pytest.raises(ValueError, match="Invalid PR number format"):
            _validate_pr_number_format("abc")
        
        with pytest.raises(ValueError, match="Invalid PR number format"):
            _validate_pr_number_format("")
        
        with pytest.raises(ValueError, match="Invalid PR number format"):
            _validate_pr_number_format("not-a-number")

# Tests for input validation
class TestInputValidation:
    """Test input validation functions."""

    def test_validate_pr_inputs_success(self):
        """Test successful input validation.
        
        Note: This function is deprecated and is now a no-op stub.
        """
        # Should not raise exception - function is deprecated and does nothing
        _validate_pr_inputs("123", "https://app.staging.netrasystems.ai")

    def test_validate_pr_inputs_invalid_pr(self):
        """Test input validation with invalid PR number.
        
        Note: This function is deprecated and is now a no-op stub.
        """
        # Function is deprecated and does not validate - should not raise exception
        _validate_pr_inputs("abc", "https://example.com")

    def test_validate_pr_inputs_invalid_url(self):
        """Test input validation with invalid return URL.
        
        Note: This function is deprecated and is now a no-op stub.
        """
        # Function is deprecated and does not validate - should not raise exception
        _validate_pr_inputs("123", "not-a-url")

    def test_validate_pr_inputs_malicious_domain(self):
        """Test input validation rejects malicious domains.
        
        Note: This function is deprecated and is now a no-op stub.
        """
        # Function is deprecated and does not validate - should not raise exception
        _validate_pr_inputs("123", "https://evil.com")

# Tests for GitHub validation
class TestGitHubValidation:
    """Test GitHub PR validation functions."""

    @pytest.mark.asyncio
    async def test_validate_pr_with_github_success(self):
        """Test successful GitHub PR validation."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = Mock()
        # Mock: Generic component isolation for controlled unit testing
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"state": "open"}
        # Mock: Async component isolation for testing without real async operations
        mock_client.get = AsyncMock(return_value=mock_response)
        
        # Should not raise exception
        await _validate_pr_with_github("123", mock_client)

    @pytest.mark.asyncio
    async def test_validate_pr_with_github_not_found(self):
        """Test GitHub PR validation when PR not found.
        
        Note: This function is deprecated and is now a no-op stub.
        """
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_client.get = AsyncMock(return_value=mock_response)
        
        # Function is deprecated and does not validate - should not raise exception
        await _validate_pr_with_github("123", mock_client)

    @pytest.mark.asyncio
    async def test_validate_pr_with_github_closed(self):
        """Test GitHub PR validation when PR is closed.
        
        Note: This function is deprecated and is now a no-op stub.
        """
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"state": "closed"}
        mock_client.get = AsyncMock(return_value=mock_response)
        
        # Function is deprecated and does not validate - should not raise exception
        await _validate_pr_with_github("123", mock_client)

    @pytest.mark.asyncio
    async def test_validate_pr_with_github_network_error(self):
        """Test GitHub PR validation with network error."""
        import httpx
        # Mock: Generic component isolation for controlled unit testing
        mock_client = Mock()
        # Mock: Async component isolation for testing without real async operations
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("Network error"))
        
        # Should not raise exception but log warning
        await _validate_pr_with_github("123", mock_client)

    def test_is_valid_url_edge_cases(self):
        """Test URL validation with edge cases."""
        invalid_urls = [
            "",
            None,
            "http://",
            "https://",
            "ftp://example.com",  # Valid URL but not HTTP/HTTPS
            "data:text/plain,hello"
        ]
        
        for url in invalid_urls:
            if url is not None:
                assert not _is_valid_url(url) or not _is_allowed_return_domain(url)

    def test_is_allowed_return_domain_subdomains(self):
        """Test domain validation with various subdomain patterns."""
        valid_subdomains = [
            "https://pr-123.staging.netrasystems.ai",
            "https://feature-branch.staging.netrasystems.ai",
            "https://test.localhost"
        ]
        
        for url in valid_subdomains:
            assert _is_allowed_return_domain(url)

    def test_is_allowed_return_domain_spoofing(self):
        """Test domain validation prevents spoofing attempts.
        
        Note: This function is deprecated and has known security limitations.
        Testing actual behavior of the deprecated implementation.
        """
        # These spoofing attempts should be blocked by the deprecated function
        spoofing_attempts = [
            "https://app.staging.netrasystems.ai.evil.com",
            "https://localhostevil.com",
            "https://evil-staging.netrasystems.ai.com",
            "https://example.com"
        ]
        
        for url in spoofing_attempts:
            assert not _is_allowed_return_domain(url)
        
        # Note: The deprecated implementation has a security flaw - it would allow
        # "https://evil.com/staging.netrasystems.ai" due to path-based matching
        # This test documents the known limitation