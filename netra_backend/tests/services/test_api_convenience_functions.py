"""Tests for convenience functions for common APIs."""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import patch, AsyncMock

# Add project root to path

from netra_backend.app.services.external_api_client import call_google_api, call_openai_api

# Add project root to path


class TestConvenienceFunctions:
    """Test convenience functions for common APIs."""
    async def test_call_google_api_get(self):
        """Test calling Google API with GET method."""
        with patch('app.services.external_api_client.get_http_client') as mock_context:
            mock_client = self._setup_mock_client_get()
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await call_google_api("/test", "GET", {"Auth": "token"}, params={"q": "test"})
            self._verify_google_get_call(result, mock_client)
    
    def _setup_mock_client_get(self):
        """Setup mock client for GET request."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {"success": True}
        return mock_client
    
    def _verify_google_get_call(self, result, mock_client):
        """Verify Google API GET call."""
        assert result == {"success": True}
        mock_client.get.assert_called_once_with(
            "/test", "google_api", headers={"Auth": "token"}, params={"q": "test"}
        )
    async def test_call_google_api_post(self):
        """Test calling Google API with POST method."""
        with patch('app.services.external_api_client.get_http_client') as mock_context:
            mock_client = self._setup_mock_client_post()
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await call_google_api("/test", "POST", {"Auth": "token"}, json_data={"data": "value"})
            self._verify_google_post_call(result, mock_client)
    
    def _setup_mock_client_post(self):
        """Setup mock client for POST request."""
        mock_client = AsyncMock()
        mock_client.post.return_value = {"success": True}
        return mock_client
    
    def _verify_google_post_call(self, result, mock_client):
        """Verify Google API POST call."""
        assert result == {"success": True}
        mock_client.post.assert_called_once_with(
            "/test", "google_api", headers={"Auth": "token"}, json_data={"data": "value"}
        )
    async def test_call_google_api_other_method(self):
        """Test calling Google API with other HTTP method."""
        with patch('app.services.external_api_client.get_http_client') as mock_context:
            mock_client = self._setup_mock_client_request()
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await call_google_api("/test", "PUT", {"Auth": "token"}, data={"data": "value"})
            self._verify_google_put_call(result, mock_client)
    
    def _setup_mock_client_request(self):
        """Setup mock client for _request method."""
        mock_client = AsyncMock()
        mock_client._request.return_value = {"success": True}
        return mock_client
    
    def _verify_google_put_call(self, result, mock_client):
        """Verify Google API PUT call."""
        assert result == {"success": True}
        mock_client._request.assert_called_once_with(
            "PUT", "/test", "google_api", headers={"Auth": "token"}, data={"data": "value"}
        )
    async def test_call_openai_api_post(self):
        """Test calling OpenAI API with POST method."""
        with patch('app.services.external_api_client.get_http_client') as mock_context:
            mock_client = self._setup_mock_client_post()
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await call_openai_api("/test", "POST", {"Auth": "Bearer token"}, json_data={"prompt": "test"})
            self._verify_openai_post_call(result, mock_client)
    
    def _verify_openai_post_call(self, result, mock_client):
        """Verify OpenAI API POST call."""
        assert result == {"success": True}
        mock_client.post.assert_called_once_with(
            "/test", "openai_api", headers={"Auth": "Bearer token"}, json_data={"prompt": "test"}
        )
    async def test_call_openai_api_get(self):
        """Test calling OpenAI API with GET method."""
        with patch('app.services.external_api_client.get_http_client') as mock_context:
            mock_client = self._setup_mock_client_get()
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await call_openai_api("/models", "GET", {"Auth": "Bearer token"})
            self._verify_openai_get_call(result, mock_client)
    
    def _verify_openai_get_call(self, result, mock_client):
        """Verify OpenAI API GET call."""
        assert result == {"success": True}
        mock_client.get.assert_called_once_with(
            "/models", "openai_api", headers={"Auth": "Bearer token"}
        )
    async def test_call_openai_api_other_method(self):
        """Test calling OpenAI API with other HTTP method."""
        with patch('app.services.external_api_client.get_http_client') as mock_context:
            mock_client = self._setup_mock_client_request()
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await call_openai_api("/test", "DELETE", {"Auth": "Bearer token"})
            self._verify_openai_delete_call(result, mock_client)
    
    def _verify_openai_delete_call(self, result, mock_client):
        """Verify OpenAI API DELETE call."""
        assert result == {"success": True}
        mock_client._request.assert_called_once_with(
            "DELETE", "/test", "openai_api", headers={"Auth": "Bearer token"}
        )