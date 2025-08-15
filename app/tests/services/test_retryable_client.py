"""Tests for RetryableHTTPClient functionality."""

import pytest
from unittest.mock import patch
from app.services.external_api_client import RetryableHTTPClient, ResilientHTTPClient


class TestRetryableHTTPClient:
    """Test RetryableHTTPClient functionality."""
    
    @pytest.fixture
    def retryable_client(self):
        """Create a RetryableHTTPClient for testing."""
        return RetryableHTTPClient(base_url="https://api.example.com")
    
    def test_retryable_client_inheritance(self, retryable_client):
        """Test RetryableHTTPClient inherits from ResilientHTTPClient."""
        assert isinstance(retryable_client, ResilientHTTPClient)
    
    @pytest.mark.asyncio
    async def test_get_with_retry(self, retryable_client):
        """Test GET with retry functionality."""
        with patch.object(retryable_client, 'get', return_value={"success": True}) as mock_get:
            result = await retryable_client.get_with_retry("/test", "test_api")
            
            self._verify_get_with_retry(result, mock_get)
    
    def _verify_get_with_retry(self, result, mock_get):
        """Verify GET with retry execution."""
        assert result == {"success": True}
        mock_get.assert_called_once_with("/test", "test_api")
    
    @pytest.mark.asyncio
    async def test_post_with_retry(self, retryable_client):
        """Test POST with retry functionality."""
        with patch.object(retryable_client, 'post', return_value={"success": True}) as mock_post:
            result = await retryable_client.post_with_retry(
                "/test", "test_api", json_data={"data": "value"}
            )
            
            self._verify_post_with_retry(result, mock_post)
    
    def _verify_post_with_retry(self, result, mock_post):
        """Verify POST with retry execution."""
        assert result == {"success": True}
        mock_post.assert_called_once_with("/test", "test_api", json_data={"data": "value"})