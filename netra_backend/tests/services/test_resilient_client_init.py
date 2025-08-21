"""Tests for ResilientHTTPClient initialization and configuration."""

import pytest
from aiohttp import ClientTimeout
from netra_backend.app.services.external_api_client import ResilientHTTPClient


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
    
    def test_select_config_google(self, client):
        """Test config selection for Google APIs."""
        config = client._select_config("google_api")
        assert config.name == "google_api"
        
        config = client._select_config("oauth_service")
        assert config.name == "google_api"
    
    def test_select_config_openai(self, client):
        """Test config selection for OpenAI APIs."""
        config = client._select_config("openai_api")
        assert config.name == "openai_api"
        
        config = client._select_config("gpt_service")
        assert config.name == "openai_api"
    
    def test_select_config_anthropic(self, client):
        """Test config selection for Anthropic APIs."""
        config = client._select_config("anthropic_api")
        assert config.name == "anthropic_api"
        
        config = client._select_config("claude_service")
        assert config.name == "anthropic_api"
    
    def test_select_config_health(self, client):
        """Test config selection for health APIs."""
        config = client._select_config("health_check")
        assert config.name == "fast_api"
        
        config = client._select_config("ping_service")
        assert config.name == "fast_api"
    
    def test_select_config_generic(self, client):
        """Test config selection for generic APIs."""
        config = client._select_config("random_api")
        assert config.name == "external_api"