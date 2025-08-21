"""Tests for HTTPError custom exception."""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import pytest

# Add project root to path
from netra_backend.app.services.external_api_client import HTTPError

# Add project root to path


class TestHTTPError:
    """Test HTTPError custom exception."""
    
    def test_http_error_creation(self):
        """Test HTTPError creation with all parameters."""
        response_data = {"error": "Bad Request", "code": 400}
        error = HTTPError(400, "Request failed", response_data)
        self._verify_error_properties(error, 400, "Request failed", response_data)
    
    def _verify_error_properties(self, error, status_code, message, response_data):
        """Verify error object properties."""
        assert error.status_code == status_code
        assert str(error) == message
        assert error.response_data == response_data
    
    def test_http_error_without_response_data(self):
        """Test HTTPError creation without response data."""
        error = HTTPError(404, "Not found")
        self._verify_error_properties(error, 404, "Not found", {})
    
    def test_http_error_inheritance(self):
        """Test HTTPError inherits from Exception."""
        error = HTTPError(500, "Server error")
        assert isinstance(error, Exception)