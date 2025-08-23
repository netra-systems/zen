"""Integration test scenarios combining multiple components."""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

from unittest.mock import MagicMock, patch

import pytest

from netra_backend.app.services.external_api_client import (
    HTTPError,
    ResilientHTTPClient,
)

class TestIntegrationScenarios:
    """Integration test scenarios combining multiple components."""
    async def test_full_request_flow_success(self):
        """Test complete request flow from client creation to response."""
        client = ResilientHTTPClient(base_url="https://api.test.com")
        expected_result = {"result": "success"}
        
        with patch.object(client, '_request', return_value=expected_result) as mock_request:
            result = await client.get("/endpoint", "test_api")
            
            assert result == expected_result
            mock_request.assert_called_once_with("GET", "/endpoint", "test_api", params=None, headers=None)
    
    async def test_error_handling_chain(self):
        """Test error handling through the entire chain."""
        client = ResilientHTTPClient(base_url="https://api.test.com")
        
        # Mock _request to raise HTTPError as if it came from the circuit breaker
        with patch.object(client, '_request', side_effect=HTTPError(500, "test_api API error: 500", {"error": "Internal Server Error"})) as mock_request:
            with pytest.raises(HTTPError) as exc_info:
                await client.get("/endpoint", "test_api")
            
            # Verify the error has correct properties
            assert exc_info.value.status_code == 500
            assert exc_info.value.response_data == {"error": "Internal Server Error"}
            mock_request.assert_called_once_with("GET", "/endpoint", "test_api", params=None, headers=None)
    
