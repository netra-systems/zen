"""Tests for ResilientHTTPClient HTTP methods."""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import patch

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.services.external_api_client import ResilientHTTPClient

# Add project root to path


class TestResilientHTTPClientMethods:
    """Test ResilientHTTPClient HTTP methods."""
    
    @pytest.fixture
    def client(self):
        """Create a ResilientHTTPClient for testing."""
        return ResilientHTTPClient(base_url="https://api.example.com")
    async def test_get_method(self, client):
        """Test GET method."""
        with patch.object(client, '_request', return_value={"success": True}) as mock_request:
            result = await client.get("/test", "test_api", params={"key": "value"}, headers={"Auth": "token"})
            
            self._verify_get_request(result, mock_request)
    
    def _verify_get_request(self, result, mock_request):
        """Verify GET request execution."""
        assert result == {"success": True}
        mock_request.assert_called_once_with(
            "GET", "/test", "test_api", params={"key": "value"}, headers={"Auth": "token"}
        )
    async def test_post_method(self, client):
        """Test POST method."""
        with patch.object(client, '_request', return_value={"success": True}) as mock_request:
            result = await client.post(
                "/test", "test_api", 
                data="raw_data", 
                json_data={"json": "data"}, 
                headers={"Auth": "token"}
            )
            
            self._verify_post_request(result, mock_request)
    
    def _verify_post_request(self, result, mock_request):
        """Verify POST request execution."""
        assert result == {"success": True}
        mock_request.assert_called_once_with(
            "POST", "/test", "test_api", 
            data="raw_data", 
            json_data={"json": "data"}, 
            headers={"Auth": "token"}
        )
    async def test_put_method(self, client):
        """Test PUT method."""
        with patch.object(client, '_request', return_value={"success": True}) as mock_request:
            result = await client.put(
                "/test", "test_api", 
                data={"form": "data"}, 
                headers={"Auth": "token"}
            )
            
            self._verify_put_request(result, mock_request)
    
    def _verify_put_request(self, result, mock_request):
        """Verify PUT request execution."""
        assert result == {"success": True}
        mock_request.assert_called_once_with(
            "PUT", "/test", "test_api", 
            data={"form": "data"}, 
            json_data=None, 
            headers={"Auth": "token"}
        )
    async def test_delete_method(self, client):
        """Test DELETE method."""
        with patch.object(client, '_request', return_value={"success": True}) as mock_request:
            result = await client.delete("/test", "test_api", headers={"Auth": "token"})
            
            self._verify_delete_request(result, mock_request)
    
    def _verify_delete_request(self, result, mock_request):
        """Verify DELETE request execution."""
        assert result == {"success": True}
        mock_request.assert_called_once_with(
            "DELETE", "/test", "test_api", headers={"Auth": "token"}
        )