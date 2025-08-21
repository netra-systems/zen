"""Tests for ResilientHTTPClient initialization and configuration."""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from aiohttp import ClientTimeout

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.services.external_api_client import ResilientHTTPClient

# Add project root to path


class TestResilientHTTPClientInit:
    """Test ResilientHTTPClient initialization and configuration."""
    
    @pytest.fixture
    def client(self):
        """Create a ResilientHTTPClient for testing."""
        return ResilientHTTPClient(
            base_url="https://api.example.com",
            default_headers={"User-Agent": "test-client"},
            timeout=ClientTimeout(total=5.0)
        )
    
    def test_client_initialization(self, client):
        """Test client initialization."""
        self._verify_client_properties(client)
        self._verify_client_state(client)
    
    def _verify_client_properties(self, client):
        """Verify client properties are set correctly."""
        assert client.base_url == "https://api.example.com"
        assert client.default_headers == {"User-Agent": "test-client"}
        assert client.timeout.total == 5.0
    
    def _verify_client_state(self, client):
        """Verify client internal state."""
        assert client._circuits == {}
        assert client._session is None
    
    def test_client_initialization_defaults(self):
        """Test client initialization with defaults."""
        client = ResilientHTTPClient()
        self._verify_default_properties(client)
    
    def _verify_default_properties(self, client):
        """Verify default client properties."""
        assert client.base_url is None
        assert client.default_headers == {}
        assert client.timeout.total == 10.0
    
    @pytest.mark.parametrize("service_name,mapped_service,expected_config", [
        ("google_api", "oauth_service", "google_api"),
        ("openai_api", "gpt_service", "openai_api"), 
        ("anthropic_api", "claude_service", "anthropic_api"),
        ("health_check", "ping_service", "fast_api"),
    ])
    def test_select_config_by_service(self, client, service_name, mapped_service, expected_config):
        """Test config selection for different service types."""
        # Test direct service name mapping
        config = client._select_config(service_name)
        assert config.name == expected_config
        
        # Test mapped service name mapping
        config = client._select_config(mapped_service)
        assert config.name == expected_config
    
    def test_select_config_generic(self, client):
        """Test config selection for generic APIs."""
        config = client._select_config("random_api")
        assert config.name == "external_api"