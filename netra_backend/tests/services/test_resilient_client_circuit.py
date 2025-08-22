"""Tests for ResilientHTTPClient circuit breaker management."""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add project root to path
from netra_backend.app.services.external_api_client import ResilientHTTPClient
from netra_backend.tests.services.external_api_client_utils import (
    verify_new_circuit_creation,
)

# Add project root to path


class TestResilientHTTPClientCircuit:
    """Test ResilientHTTPClient circuit breaker management."""
    
    @pytest.fixture
    def client(self):
        """Create a ResilientHTTPClient for testing."""
        return ResilientHTTPClient(base_url="https://api.example.com")
    async def test_get_circuit_new(self, client):
        """Test getting new circuit breaker."""
        with patch('app.services.external_api_client.circuit_registry') as mock_registry:
            mock_circuit = Mock()
            mock_registry.get_breaker = Mock(return_value=mock_circuit)
            
            circuit = await client._get_circuit("test_api")
            verify_new_circuit_creation(circuit, mock_circuit, client, mock_registry)
    async def test_get_circuit_existing(self, client):
        """Test getting existing circuit breaker."""
        mock_circuit = Mock()
        client._circuits["test_api"] = mock_circuit
        
        circuit = await client._get_circuit("test_api")
        assert circuit == mock_circuit
    
    def test_get_fallback_response(self, client):
        """Test fallback response generation."""
        response = client._get_fallback_response("GET", "/test", "test_api")
        expected = self._create_expected_fallback()
        assert response == expected
    
    def _create_expected_fallback(self):
        """Create expected fallback response."""
        return {
            "error": "service_unavailable",
            "message": "test_api API temporarily unavailable",
            "method": "GET",
            "url": "/test",
            "fallback": True
        }
    async def test_request_success(self, client):
        """Test successful request execution."""
        mock_circuit = AsyncMock()
        mock_circuit.call.return_value = {"success": True}
        
        with patch.object(client, '_get_circuit', return_value=mock_circuit):
            result = await client._request("GET", "/test", "test_api")
            assert result == {"success": True}
            mock_circuit.call.assert_called_once()
    async def test_request_circuit_open(self, client):
        """Test request when circuit is open."""
        from netra_backend.app.core.circuit_breaker import CircuitBreakerOpenError
        
        mock_circuit = self._setup_open_circuit_mock()
        
        with patch.object(client, '_get_circuit', return_value=mock_circuit), \
             patch('app.services.external_api_client.logger') as mock_logger:
            result = await client._request("GET", "/test", "test_api")
            self._verify_circuit_open_result(result, mock_logger)
    
    def _setup_open_circuit_mock(self):
        """Setup mock circuit that is open."""
        from netra_backend.app.core.circuit_breaker import CircuitBreakerOpenError
        mock_circuit = AsyncMock()
        mock_circuit.call.side_effect = CircuitBreakerOpenError("Circuit open")
        return mock_circuit
    
    def _verify_circuit_open_result(self, result, mock_logger):
        """Verify circuit open behavior."""
        from netra_backend.tests.services.external_api_client_utils import (
            verify_circuit_open_behavior,
        )
        verify_circuit_open_behavior(result, mock_logger)