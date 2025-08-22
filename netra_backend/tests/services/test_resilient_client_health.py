"""Tests for ResilientHTTPClient health checks and connectivity."""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import Mock, patch

import pytest

# Add project root to path
from netra_backend.app.services.external_api_client import ResilientHTTPClient
from netra_backend.tests.services.external_api_client_utils import (
    # Add project root to path
    create_healthy_circuit_mock,
    verify_error_health_check,
    verify_successful_health_check,
)


class TestResilientHTTPClientHealth:
    """Test ResilientHTTPClient health checks and connectivity."""
    
    @pytest.fixture
    def client(self):
        """Create a ResilientHTTPClient for testing."""
        return ResilientHTTPClient(base_url="https://api.example.com")
    async def test_health_check_success(self, client):
        """Test successful health check."""
        mock_circuit = create_healthy_circuit_mock()
        
        with patch.object(client, '_get_circuit', return_value=mock_circuit), \
             patch.object(client, '_test_connectivity', return_value={"status": "healthy"}):
            result = await client.health_check("test_api")
            verify_successful_health_check(result)
    async def test_health_check_error(self, client):
        """Test health check with error."""
        with patch.object(client, '_get_circuit', side_effect=Exception("Circuit error")), \
             patch('app.services.external_api_client.logger') as mock_logger:
            result = await client.health_check("test_api")
            verify_error_health_check(result, mock_logger)
    async def test_test_connectivity_no_base_url(self):
        """Test connectivity test without base URL."""
        client = ResilientHTTPClient()
        result = await client._test_connectivity()
        
        assert result == {"status": "skipped", "reason": "no_base_url"}
    async def test_test_connectivity_success(self, client):
        """Test successful connectivity test."""
        mock_session = self._setup_successful_connectivity_test()
        
        with patch.object(client, '_get_session', return_value=mock_session):
            result = await client._test_connectivity()
            self._verify_connectivity_success(result)
    
    def _setup_successful_connectivity_test(self):
        """Setup mock for successful connectivity test."""
        from netra_backend.tests.services.external_api_client_utils import (
            MockAsyncContextManager,
        )
        
        class MockResponse:
            def __init__(self, status):
                self.status = status
        
        mock_session = Mock()
        mock_response = MockResponse(200)
        mock_session.get.return_value = MockAsyncContextManager(mock_response)
        return mock_session
    
    def _verify_connectivity_success(self, result):
        """Verify successful connectivity test results."""
        assert result["status"] == "healthy"
        assert result["response_code"] == 200
    async def test_test_connectivity_failure(self, client):
        """Test failed connectivity test."""
        mock_session = Mock()
        mock_session.get.side_effect = Exception("Connection failed")
        
        with patch.object(client, '_get_session', return_value=mock_session):
            result = await client._test_connectivity()
            
            assert result["status"] == "unhealthy"
            assert result["error"] == "Connection failed"
    
    def test_assess_health_unhealthy_circuit(self, client):
        """Test health assessment with unhealthy circuit."""
        circuit_status = {"health": "unhealthy"}
        connectivity_status = {"status": "healthy"}
        
        health = client._assess_health(circuit_status, connectivity_status)
        assert health == "unhealthy"
    
    def test_assess_health_unhealthy_connectivity(self, client):
        """Test health assessment with unhealthy connectivity."""
        circuit_status = {"health": "healthy"}
        connectivity_status = {"status": "unhealthy"}
        
        health = client._assess_health(circuit_status, connectivity_status)
        assert health == "degraded"
    
    def test_assess_health_recovering(self, client):
        """Test health assessment with recovering circuit."""
        circuit_status = {"health": "recovering"}
        connectivity_status = {"status": "healthy"}
        
        health = client._assess_health(circuit_status, connectivity_status)
        assert health == "recovering"
    
    def test_assess_health_healthy(self, client):
        """Test health assessment with all healthy."""
        circuit_status = {"health": "healthy"}
        connectivity_status = {"status": "healthy"}
        
        health = client._assess_health(circuit_status, connectivity_status)
        assert health == "healthy"