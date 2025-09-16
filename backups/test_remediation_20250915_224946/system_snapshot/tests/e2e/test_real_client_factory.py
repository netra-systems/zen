"""Test Real Client Factory Implementation

Unit tests for the real client factory to validate functionality,
error handling, and architectural compliance.

Business Value Justification (BVJ):
- Segment: All customer tiers
- Business Goal: Validate E2E testing infrastructure reliability
- Value Impact: Ensures test infrastructure supports production validation
- Revenue Impact: Prevents bugs that could impact customer experience
"""

import asyncio
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.real_client_factory import (
    RealClientFactory,
    create_real_client_factory,
)
from test_framework.http_client import (
    ClientConfig,
    create_test_config,
)
from test_framework.http_client import UnifiedHTTPClient as RealHTTPClient
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient


@pytest.mark.e2e
class RealClientFactoryTests:
    """Test suite for RealClientFactory"""
    
    @pytest.mark.e2e
    def test_factory_initialization(self):
        """Test factory initializes with default config"""
        factory = create_real_client_factory()
        assert isinstance(factory, RealClientFactory)
        assert isinstance(factory.config, ClientConfig)
    
    @pytest.mark.e2e
    def test_factory_with_custom_config(self):
        """Test factory initializes with custom config"""
        config = create_test_config(timeout=10.0, max_retries=5)
        factory = create_real_client_factory(config)
        assert factory.config.timeout == 10.0
        assert factory.config.max_retries == 5
    
    @pytest.mark.e2e
    def test_http_client_creation(self):
        """Test HTTP client creation"""
        factory = create_real_client_factory()
        client = factory.create_http_client("http://localhost:8000")
        assert isinstance(client, RealHTTPClient)
        assert client.base_url == "http://localhost:8000"
    
    @pytest.mark.e2e
    def test_websocket_client_creation(self):
        """Test WebSocket client creation"""
        factory = create_real_client_factory()
        client = factory.create_websocket_client("ws://localhost:8000/ws")
        assert isinstance(client, RealWebSocketClient)
        assert client.ws_url == "ws://localhost:8000/ws"
    
    @pytest.mark.e2e
    def test_client_reuse(self):
        """Test client reuse for same URLs"""
        factory = create_real_client_factory()
        client1 = factory.create_http_client("http://localhost:8000")
        client2 = factory.create_http_client("http://localhost:8000")
        assert client1 is client2
    
    @pytest.mark.e2e
    def test_auth_client_creation(self):
        """Test auth HTTP client with specific config"""
        factory = create_real_client_factory()
        client = factory.create_auth_http_client("http://localhost:8001")
        assert isinstance(client, RealHTTPClient)
        assert client.config.timeout == 15.0
        assert client.config.max_retries == 2
    
    @pytest.mark.e2e
    def test_backend_client_creation(self):
        """Test backend HTTP client with specific config"""
        factory = create_real_client_factory()
        client = factory.create_backend_http_client("http://localhost:8000")
        assert isinstance(client, RealHTTPClient)
        assert client.config.timeout == 60.0
        assert client.config.pool_size == 20
    
    @pytest.mark.e2e
    def test_initial_metrics(self):
        """Test initial connection metrics"""
        factory = create_real_client_factory()
        metrics = factory.get_connection_metrics()
        expected = {"http": {"requests": 0, "responses": 0}, 
                   "websocket": {"messages_sent": 0, "messages_received": 0}}
        assert metrics == expected


@pytest.mark.e2e
class RealHTTPClientTests:
    """Test suite for RealHTTPClient"""
    
    @pytest.mark.e2e
    def test_client_initialization(self):
        """Test HTTP client initialization"""
        config = create_test_config()
        client = RealHTTPClient("http://localhost:8000", config)
        assert client.base_url == "http://localhost:8000"
        assert client.config is config
    
    @pytest.mark.e2e
    def test_auth_headers_without_token(self):
        """Test auth headers without token"""
        client = RealHTTPClient("http://localhost:8000")
        headers = client._get_auth_headers(None)
        expected = {"Content-Type": "application/json"}
        assert headers == expected
    
    @pytest.mark.e2e
    def test_auth_headers_with_token(self):
        """Test auth headers with token"""
        client = RealHTTPClient("http://localhost:8000")
        headers = client._get_auth_headers("test-token")
        expected = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-token"
        }
        assert headers == expected
    
    @pytest.mark.e2e
    def test_base_url_normalization(self):
        """Test base URL trailing slash removal"""
        client = RealHTTPClient("http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"


@pytest.mark.e2e
class RealWebSocketClientTests:
    """Test suite for RealWebSocketClient"""
    
    @pytest.mark.e2e
    def test_client_initialization(self):
        """Test WebSocket client initialization"""
        config = create_test_config()
        client = RealWebSocketClient("ws://localhost:8000/ws", config)
        assert client.ws_url == "ws://localhost:8000/ws"
        assert client.config is config
    
    @pytest.mark.e2e
    def test_message_preparation(self):
        """Test message preparation for sending"""
        client = RealWebSocketClient("ws://localhost:8000/ws")
        
        # Test dict message
        dict_msg = {"type": "test", "data": "value"}
        prepared = client._prepare_message(dict_msg)
        assert prepared == '{"type": "test", "data": "value"}'
        
        # Test string message
        str_msg = "test message"
        prepared = client._prepare_message(str_msg)
        assert prepared == "test message"


@pytest.mark.e2e
class ClientConfigTests:
    """Test suite for ClientConfig"""
    
    @pytest.mark.e2e
    def test_default_config(self):
        """Test default configuration values"""
        config = ClientConfig()
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.pool_size == 10
        assert config.verify_ssl is False
    
    @pytest.mark.e2e
    def test_retry_delay_calculation(self):
        """Test retry delay with backoff"""
        config = ClientConfig(retry_delay=1.0)
        assert config.get_retry_delay(0) == 1.0
        assert config.get_retry_delay(1) == 2.0
        assert config.get_retry_delay(2) == 3.0
    
    @pytest.mark.e2e
    def test_ssl_context_creation(self):
        """Test SSL context creation"""
        config = ClientConfig(verify_ssl=False)
        ssl_context = config.create_ssl_context()
        assert ssl_context is not None
        
        config = ClientConfig(verify_ssl=True)  
        ssl_context = config.create_ssl_context()
        assert ssl_context is None


@pytest.mark.asyncio
@pytest.mark.e2e
class AsyncOperationsTests:
    """Test suite for async operations"""
    
    @pytest.mark.e2e
    async def test_factory_cleanup(self):
        """Test factory cleanup operations"""
        factory = create_real_client_factory()
        
        # Create some clients
        factory.create_http_client("http://localhost:8000")
        factory.create_websocket_client("ws://localhost:8000/ws")
        
        # Cleanup should complete without errors
        await factory.cleanup()
        
        # Verify clients are cleared
        assert len(factory._http_clients) == 0
        assert len(factory._ws_clients) == 0
