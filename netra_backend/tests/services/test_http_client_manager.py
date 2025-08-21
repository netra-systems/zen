"""Tests for HTTPClientManager functionality."""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import AsyncMock

# Add project root to path

from netra_backend.app.services.external_api_client import (

# Add project root to path
    HTTPClientManager,
    ResilientHTTPClient,
    RetryableHTTPClient,
    get_http_client,
    http_client_manager
)


class TestHTTPClientManager:
    """Test HTTPClientManager functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh HTTPClientManager for testing."""
        return HTTPClientManager()
    
    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert manager._clients == {}
    
    def test_get_client_new_resilient(self, manager):
        """Test getting new resilient client."""
        client = manager.get_client("test", "https://api.test.com", {"Auth": "token"})
        self._verify_resilient_client(client, manager)
    
    def _verify_resilient_client(self, client, manager):
        """Verify resilient client properties."""
        assert isinstance(client, ResilientHTTPClient)
        assert not isinstance(client, RetryableHTTPClient)
        assert client.base_url == "https://api.test.com"
        assert client.default_headers == {"Auth": "token"}
        assert "test" in manager._clients
    
    def test_get_client_new_retryable(self, manager):
        """Test getting new retryable client."""
        client = manager.get_client("test", "https://api.test.com", {"Auth": "token"}, with_retry=True)
        self._verify_retryable_client(client, manager)
    
    def _verify_retryable_client(self, client, manager):
        """Verify retryable client properties."""
        assert isinstance(client, RetryableHTTPClient)
        assert client.base_url == "https://api.test.com"
        assert client.default_headers == {"Auth": "token"}
        assert "test" in manager._clients
    
    def test_get_client_existing(self, manager):
        """Test getting existing client."""
        # Create first client
        client1 = manager.get_client("test")
        # Get same client again
        client2 = manager.get_client("test")
        
        assert client1 is client2
        assert len(manager._clients) == 1
    async def test_health_check_all_empty(self, manager):
        """Test health check with no clients."""
        result = await manager.health_check_all()
        assert result == {}
    async def test_health_check_all_with_clients(self, manager):
        """Test health check with multiple clients."""
        mock_clients = self._setup_mock_clients(manager)
        
        result = await manager.health_check_all()
        self._verify_health_check_results(result, mock_clients)
    
    def _setup_mock_clients(self, manager):
        """Setup mock clients for health check test."""
        mock_client1 = AsyncMock()
        mock_client1.health_check.return_value = {"status": "healthy"}
        mock_client2 = AsyncMock()
        mock_client2.health_check.return_value = {"status": "degraded"}
        
        manager._clients = {
            "client1": mock_client1,
            "client2": mock_client2
        }
        return {"client1": mock_client1, "client2": mock_client2}
    
    def _verify_health_check_results(self, result, mock_clients):
        """Verify health check results."""
        assert result["client1"] == {"status": "healthy"}
        assert result["client2"] == {"status": "degraded"}
        mock_clients["client1"].health_check.assert_called_once_with("client1")
        mock_clients["client2"].health_check.assert_called_once_with("client2")
    async def test_close_all_empty(self, manager):
        """Test closing all clients when none exist."""
        await manager.close_all()
        assert manager._clients == {}
    async def test_close_all_with_clients(self, manager):
        """Test closing all clients."""
        mock_clients = self._setup_mock_clients_for_close(manager)
        
        await manager.close_all()
        self._verify_close_all_results(manager, mock_clients)
    
    def _setup_mock_clients_for_close(self, manager):
        """Setup mock clients for close test."""
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        
        manager._clients = {
            "client1": mock_client1,
            "client2": mock_client2
        }
        return {"client1": mock_client1, "client2": mock_client2}
    
    def _verify_close_all_results(self, manager, mock_clients):
        """Verify close all results."""
        mock_clients["client1"].close.assert_called_once()
        mock_clients["client2"].close.assert_called_once()
        assert manager._clients == {}


class TestGetHTTPClient:
    """Test get_http_client context manager."""
    async def test_get_http_client_context_manager(self):
        """Test get_http_client context manager."""
        from unittest.mock import patch, Mock
        with patch('app.services.external_api_client.http_client_manager') as mock_manager:
            mock_client = Mock()
            mock_manager.get_client.return_value = mock_client
            
            async with get_http_client("test", "https://api.test.com", {"Auth": "token"}, True) as client:
                assert client == mock_client
            
            self._verify_context_manager_call(mock_manager)
    
    def _verify_context_manager_call(self, mock_manager):
        """Verify context manager call."""
        mock_manager.get_client.assert_called_once_with(
            "test", "https://api.test.com", {"Auth": "token"}, True
        )


class TestGlobalClientManager:
    """Test global http_client_manager instance."""
    
    def test_global_manager_exists(self):
        """Test global manager instance exists."""
        assert http_client_manager is not None
        assert isinstance(http_client_manager, HTTPClientManager)
    
    def test_global_manager_singleton_behavior(self):
        """Test that importing returns the same instance."""
        from netra_backend.app.services.external_api_client import http_client_manager as imported_manager
        assert imported_manager is http_client_manager