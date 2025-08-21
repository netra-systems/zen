"""Tests for ResilientHTTPClient response processing."""

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

from netra_backend.app.services.external_api_client import ResilientHTTPClient, HTTPError
from netra_backend.tests.services.external_api_client_utils import (

# Add project root to path
    create_text_error_response_mock,
    create_text_success_response_mock,
    verify_error_response_processing
)


class TestResilientHTTPClientResponse:
    """Test ResilientHTTPClient response processing."""
    
    @pytest.fixture
    def client(self):
        """Create a ResilientHTTPClient for testing."""
        return ResilientHTTPClient(base_url="https://api.example.com")
    async def test_extract_error_data_json(self, client):
        """Test extracting JSON error data."""
        from unittest.mock import AsyncMock
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"error": "Bad Request"})
        
        error_data = await client._extract_error_data(mock_response)
        assert error_data == {"error": "Bad Request"}
    async def test_extract_error_data_text(self, client):
        """Test extracting text error data when JSON fails."""
        mock_response = create_text_error_response_mock()
        error_data = await client._extract_error_data(mock_response)
        assert error_data == {"error": "Error message", "status": 400}
    async def test_process_response_success_json(self, client):
        """Test processing successful JSON response."""
        from unittest.mock import AsyncMock
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "success"})
        
        result = await client._process_response(mock_response, "test_api")
        assert result == {"data": "success"}
    async def test_process_response_success_text(self, client):
        """Test processing successful text response."""
        mock_response = create_text_success_response_mock()
        result = await client._process_response(mock_response, "test_api")
        assert result == {"text": "Plain text response", "status": 200}
    async def test_process_response_error(self, client):
        """Test processing error response."""
        mock_response = self._create_error_response_mock()
        
        with pytest.raises(HTTPError) as exc_info:
            await client._process_response(mock_response, "test_api")
        
        verify_error_response_processing(exc_info)
    
    def _create_error_response_mock(self):
        """Create mock response for error processing test."""
        from unittest.mock import AsyncMock
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={"error": "Bad Request"})
        return mock_response