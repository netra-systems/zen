"""Tests for ResilientHTTPClient URL building and header merging."""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.services.external_api_client import ResilientHTTPClient

# Add project root to path


class TestResilientHTTPClientUrlHeaders:
    """Test ResilientHTTPClient URL building and header merging."""
    
    @pytest.fixture
    def client(self):
        """Create a ResilientHTTPClient for testing."""
        return ResilientHTTPClient(
            base_url="https://api.example.com",
            default_headers={"User-Agent": "test-client"}
        )
    
    def test_build_url_with_base_url(self, client):
        """Test URL building with base URL."""
        url = client._build_url("/endpoint")
        assert url == "https://api.example.com/endpoint"
        
        url = client._build_url("endpoint")
        assert url == "https://api.example.com/endpoint"
    
    def test_build_url_absolute_url(self, client):
        """Test URL building with absolute URL."""
        absolute_url = "https://other.api.com/endpoint"
        url = client._build_url(absolute_url)
        assert url == absolute_url
    
    def test_build_url_no_base_url(self):
        """Test URL building without base URL."""
        client = ResilientHTTPClient()
        url = client._build_url("/endpoint")
        assert url == "/endpoint"
    
    def test_merge_headers(self, client):
        """Test header merging."""
        request_headers = {"Authorization": "Bearer token", "Content-Type": "application/json"}
        merged = client._merge_headers(request_headers)
        
        expected = self._create_expected_headers()
        assert merged == expected
    
    def _create_expected_headers(self):
        """Create expected merged headers."""
        return {
            "User-Agent": "test-client",
            "Authorization": "Bearer token",
            "Content-Type": "application/json"
        }
    
    def test_merge_headers_none(self, client):
        """Test header merging with None headers."""
        merged = client._merge_headers(None)
        assert merged == {"User-Agent": "test-client"}
    
    def test_merge_headers_override(self, client):
        """Test header merging with override."""
        request_headers = {"User-Agent": "override-agent"}
        merged = client._merge_headers(request_headers)
        assert merged == {"User-Agent": "override-agent"}