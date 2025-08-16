"""Tests for PR router security and validation functions."""

import pytest
from unittest.mock import AsyncMock, Mock

from app.auth.pr_router import (
    _validate_pr_inputs,
    _validate_pr_number_format,
    _validate_pr_with_github,
    _is_valid_url,
    _is_allowed_return_domain
)
from app.core.exceptions_auth import AuthenticationError, NetraSecurityException


# Tests for _validate_return_url functions
class TestValidateReturnUrl:
    """Test URL validation functions with valid and malicious inputs."""

    def test_validate_return_url_valid(self):
        """Test validation of valid return URLs."""
        valid_urls = [
            "https://pr-123.staging.netrasystems.ai",
            "https://staging.netrasystems.ai",
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
            "https://staging.netrasystems.ai.evil.com",
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
        """Test validation of invalid PR numbers."""
        with pytest.raises(AuthenticationError, match="PR number must be numeric"):
            _validate_pr_number_format("abc")
        
        with pytest.raises(AuthenticationError, match="PR number must be between"):
            _validate_pr_number_format("0")
        
        with pytest.raises(AuthenticationError, match="PR number must be between"):
            _validate_pr_number_format("10000")


# Tests for input validation
class TestInputValidation:
    """Test input validation functions."""

    async def test_validate_pr_inputs_success(self):
        """Test successful input validation."""
        # Should not raise exception
        await _validate_pr_inputs("123", "https://staging.netrasystems.ai")

    async def test_validate_pr_inputs_invalid_pr(self):
        """Test input validation with invalid PR number."""
        with pytest.raises(AuthenticationError, match="Invalid PR number format"):
            await _validate_pr_inputs("abc", "https://example.com")

    async def test_validate_pr_inputs_invalid_url(self):
        """Test input validation with invalid return URL."""
        with pytest.raises(AuthenticationError, match="Invalid return URL"):
            await _validate_pr_inputs("123", "not-a-url")

    async def test_validate_pr_inputs_malicious_domain(self):
        """Test input validation rejects malicious domains."""
        with pytest.raises(NetraSecurityException, match="Return URL not in allowed domains"):
            await _validate_pr_inputs("123", "https://evil.com")


# Tests for GitHub validation
class TestGitHubValidation:
    """Test GitHub PR validation functions."""

    async def test_validate_pr_with_github_success(self):
        """Test successful GitHub PR validation."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"state": "open"}
        mock_client.get = AsyncMock(return_value=mock_response)
        
        # Should not raise exception
        await _validate_pr_with_github("123", mock_client)

    async def test_validate_pr_with_github_not_found(self):
        """Test GitHub PR validation when PR not found."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_client.get = AsyncMock(return_value=mock_response)
        
        with pytest.raises(AuthenticationError, match="PR #123 not found"):
            await _validate_pr_with_github("123", mock_client)

    async def test_validate_pr_with_github_closed(self):
        """Test GitHub PR validation when PR is closed."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"state": "closed"}
        mock_client.get = AsyncMock(return_value=mock_response)
        
        with pytest.raises(AuthenticationError, match="PR #123 is not open"):
            await _validate_pr_with_github("123", mock_client)

    async def test_validate_pr_with_github_network_error(self):
        """Test GitHub PR validation with network error."""
        import httpx
        mock_client = Mock()
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
        """Test domain validation prevents spoofing attempts."""
        spoofing_attempts = [
            "https://staging.netrasystems.ai.evil.com",
            "https://evil.com/staging.netrasystems.ai",
            "https://localhostevil.com",
            "https://evil-staging.netrasystems.ai.com"
        ]
        
        for url in spoofing_attempts:
            assert not _is_allowed_return_domain(url)