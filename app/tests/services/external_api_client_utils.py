"""Shared test utilities for ExternalAPIClient tests."""

import json
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any
from aiohttp import ClientResponse


def create_mock_session(closed: bool = False) -> Mock:
    """Create mock session with specified closed state."""
    mock_session = Mock()
    mock_session.closed = closed
    return mock_session


def create_healthy_circuit_mock() -> Mock:
    """Create mock circuit for healthy state."""
    mock_circuit = Mock()
    mock_circuit.get_status.return_value = {"health": "healthy", "state": "closed"}
    return mock_circuit


def create_success_response_mock() -> AsyncMock:
    """Create mock response for successful requests."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"result": "success"})
    return mock_response


def create_error_response_mock(status: int = 400, error_data: Dict[str, Any] = None) -> AsyncMock:
    """Create mock response for error requests."""
    if error_data is None:
        error_data = {"error": "Bad Request"}
    
    mock_response = AsyncMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=error_data)
    return mock_response


def create_text_error_response_mock() -> AsyncMock:
    """Create mock response for text error extraction."""
    mock_response = AsyncMock()
    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
    mock_response.text.return_value = "Error message"
    mock_response.status = 400
    return mock_response


def create_text_success_response_mock() -> AsyncMock:
    """Create mock response for successful text processing."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
    mock_response.text.return_value = "Plain text response"
    return mock_response


class MockAsyncContextManager:
    """Mock async context manager for HTTP responses."""
    
    def __init__(self, response: AsyncMock):
        """Initialize with response object."""
        self.response = response
    
    async def __aenter__(self):
        """Enter async context."""
        return self.response
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        return None


def create_async_context_manager(response: AsyncMock) -> MockAsyncContextManager:
    """Create async context manager for mock response."""
    return MockAsyncContextManager(response)


def create_expected_fallback_response() -> Dict[str, Any]:
    """Create expected fallback response for circuit open test."""
    return {
        "error": "service_unavailable",
        "message": "test_api API temporarily unavailable",
        "method": "GET",
        "url": "/test",
        "fallback": True
    }


def verify_new_session_creation(session, mock_session, mock_session_class, client):
    """Verify new session creation behavior."""
    assert session == mock_session
    mock_session_class.assert_called_once_with(
        timeout=client.timeout,
        headers=client.default_headers
    )


def verify_new_circuit_creation(circuit, mock_circuit, client, mock_registry):
    """Verify new circuit breaker creation."""
    assert circuit == mock_circuit
    assert client._circuits["test_api"] == mock_circuit
    mock_registry.get_circuit.assert_called_once_with(
        "http_test_api", client._select_config("test_api")
    )


def verify_error_response_processing(exc_info):
    """Verify error response processing behavior."""
    assert exc_info.value.status_code == 400
    assert "test_api API error: 400" in str(exc_info.value)
    assert exc_info.value.response_data == {"error": "Bad Request"}


def verify_circuit_open_behavior(result, mock_logger):
    """Verify circuit open behavior."""
    expected = create_expected_fallback_response()
    assert result == expected
    mock_logger.warning.assert_called_once()


def verify_successful_health_check(result):
    """Verify successful health check results."""
    assert result["api_name"] == "test_api"
    assert result["circuit"]["health"] == "healthy"
    assert result["connectivity"]["status"] == "healthy"
    assert result["overall_health"] == "healthy"


def verify_error_health_check(result, mock_logger):
    """Verify error health check results."""
    assert result["api_name"] == "test_api"
    assert result["error"] == "Circuit error"
    assert result["overall_health"] == "unhealthy"
    mock_logger.error.assert_called_once()


def setup_circuit_and_session_mocks(mock_response):
    """Setup circuit breaker and session mocks."""
    mock_circuit = AsyncMock()
    mock_session = AsyncMock()
    
    async def mock_circuit_call(func):
        return await func()
    mock_circuit.call = AsyncMock(side_effect=mock_circuit_call)
    
    from unittest.mock import MagicMock
    mock_session.request = MagicMock(return_value=create_async_context_manager(mock_response))
    return mock_circuit, mock_session


def configure_request_flow_mocks(mock_cb_class, mock_registry, mock_session_class, mock_circuit, mock_session):
    """Configure mocks for request flow test."""
    mock_cb_class.return_value = mock_circuit
    mock_registry.get_circuit = AsyncMock(return_value=mock_circuit)
    mock_session_class.return_value = mock_session