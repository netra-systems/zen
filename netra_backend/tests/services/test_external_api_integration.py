"""Integration test scenarios combining multiple components."""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import patch, MagicMock

# Add project root to path

from netra_backend.app.services.external_api_client import ResilientHTTPClient, HTTPError
from netra_backend.tests.services.external_api_client_utils import (

# Add project root to path
    create_success_response_mock,
    create_async_context_manager,
    setup_circuit_and_session_mocks,
    configure_request_flow_mocks
)


class TestIntegrationScenarios:
    """Integration test scenarios combining multiple components."""
    async def test_full_request_flow_success(self):
        """Test complete request flow from client creation to response."""
        mock_response = create_success_response_mock()
        mock_circuit, mock_session = setup_circuit_and_session_mocks(mock_response)
        
        with patch('app.services.external_api_client.CircuitBreaker') as mock_cb_class, \
             patch('app.services.external_api_client.circuit_registry') as mock_registry, \
             patch('app.services.external_api_client.ClientSession') as mock_session_class:
            
            configure_request_flow_mocks(mock_cb_class, mock_registry, mock_session_class, mock_circuit, mock_session)
            result = await self._execute_full_request_flow()
            assert result == {"result": "success"}
    
    async def _execute_full_request_flow(self):
        """Execute the full request flow test."""
        client = ResilientHTTPClient(base_url="https://api.test.com")
        return await client.get("/endpoint", "test_api")
    async def test_error_handling_chain(self):
        """Test error handling through the entire chain."""
        mock_response = self._create_error_response_mock()
        mock_circuit, mock_session = setup_circuit_and_session_mocks(mock_response)
        
        with patch('app.services.external_api_client.CircuitBreaker') as mock_cb_class, \
             patch('app.services.external_api_client.circuit_registry') as mock_registry, \
             patch('app.services.external_api_client.ClientSession') as mock_session_class:
            
            configure_request_flow_mocks(mock_cb_class, mock_registry, mock_session_class, mock_circuit, mock_session)
            await self._verify_error_handling_chain()
    
    def _create_error_response_mock(self):
        """Create mock response for error requests."""
        from unittest.mock import AsyncMock
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.json = AsyncMock(return_value={"error": "Internal Server Error"})
        return mock_response
    
    async def _verify_error_handling_chain(self):
        """Verify error handling chain behavior."""
        client = ResilientHTTPClient(base_url="https://api.test.com")
        
        with pytest.raises(HTTPError) as exc_info:
            await client.get("/endpoint", "test_api")
        
        self._verify_error_properties(exc_info)
    
    def _verify_error_properties(self, exc_info):
        """Verify error properties."""
        assert exc_info.value.status_code == 500
        assert exc_info.value.response_data == {"error": "Internal Server Error"}