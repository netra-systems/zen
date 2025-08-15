"""Comprehensive unit tests for ExternalAPIClient."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any
from aiohttp import ClientTimeout, ClientSession, ClientError, ClientResponse
from aiohttp.web_exceptions import HTTPError as AIOHTTPError

# Import the components we're testing
from app.services.external_api_client import (
    ExternalAPIConfig,
    HTTPError,
    ResilientHTTPClient,
    RetryableHTTPClient,
    HTTPClientManager,
    get_http_client,
    call_google_api,
    call_openai_api,
    http_client_manager
)


class TestExternalAPIConfig:
    """Test ExternalAPIConfig configurations."""
    
    def test_google_api_config(self):
        """Test Google API configuration."""
        config = ExternalAPIConfig.GOOGLE_API_CONFIG
        assert config.name == "google_api"
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.timeout_seconds == 10.0
    
    def test_openai_api_config(self):
        """Test OpenAI API configuration."""
        config = ExternalAPIConfig.OPENAI_API_CONFIG
        assert config.name == "openai_api"
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 20.0
        assert config.timeout_seconds == 15.0
    
    def test_anthropic_api_config(self):
        """Test Anthropic API configuration."""
        config = ExternalAPIConfig.ANTHROPIC_API_CONFIG
        assert config.name == "anthropic_api"
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 20.0
        assert config.timeout_seconds == 15.0
    
    def test_generic_api_config(self):
        """Test generic API configuration."""
        config = ExternalAPIConfig.GENERIC_API_CONFIG
        assert config.name == "external_api"
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.timeout_seconds == 10.0
    
    def test_fast_api_config(self):
        """Test fast API configuration."""
        config = ExternalAPIConfig.FAST_API_CONFIG
        assert config.name == "fast_api"
        assert config.failure_threshold == 2
        assert config.recovery_timeout == 10.0
        assert config.timeout_seconds == 3.0


class TestHTTPError:
    """Test HTTPError custom exception."""
    
    def test_http_error_creation(self):
        """Test HTTPError creation with all parameters."""
        response_data = {"error": "Bad Request", "code": 400}
        error = HTTPError(400, "Request failed", response_data)
        
        assert error.status_code == 400
        assert str(error) == "Request failed"
        assert error.response_data == response_data
    
    def test_http_error_without_response_data(self):
        """Test HTTPError creation without response data."""
        error = HTTPError(404, "Not found")
        
        assert error.status_code == 404
        assert str(error) == "Not found"
        assert error.response_data == {}
    
    def test_http_error_inheritance(self):
        """Test HTTPError inherits from Exception."""
        error = HTTPError(500, "Server error")
        assert isinstance(error, Exception)


class TestResilientHTTPClient:
    """Test ResilientHTTPClient functionality."""
    
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
        assert client.base_url == "https://api.example.com"
        assert client.default_headers == {"User-Agent": "test-client"}
        assert client.timeout.total == 5.0
        assert client._circuits == {}
        assert client._session is None
    
    def test_client_initialization_defaults(self):
        """Test client initialization with defaults."""
        client = ResilientHTTPClient()
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
    
    def test_build_url_with_base_url(self, client):
        """Test URL building with base URL."""
        url = client._build_url("/endpoint")
        assert url == "https://api.example.com/endpoint"
        
        url = client._build_url("endpoint")
        assert url == "https://api.example.com/endpoint"
    
    def test_build_url_absolute_url(self, client):
        """Test URL building with absolute URL."""
        absolute_url = "https://other.api.com/endpoint"
        url = client._build_url(absolute_url)
        assert url == absolute_url
    
    def test_build_url_no_base_url(self):
        """Test URL building without base URL."""
        client = ResilientHTTPClient()
        url = client._build_url("/endpoint")
        assert url == "/endpoint"
    
    def test_merge_headers(self, client):
        """Test header merging."""
        request_headers = {"Authorization": "Bearer token", "Content-Type": "application/json"}
        merged = client._merge_headers(request_headers)
        
        expected = {
            "User-Agent": "test-client",
            "Authorization": "Bearer token",
            "Content-Type": "application/json"
        }
        assert merged == expected
    
    def test_merge_headers_none(self, client):
        """Test header merging with None headers."""
        merged = client._merge_headers(None)
        assert merged == {"User-Agent": "test-client"}
    
    def test_merge_headers_override(self, client):
        """Test header merging with override."""
        request_headers = {"User-Agent": "override-agent"}
        merged = client._merge_headers(request_headers)
        assert merged == {"User-Agent": "override-agent"}
    
    @pytest.mark.asyncio
    async def test_get_session_new(self, client):
        """Test getting new session."""
        with patch('app.services.external_api_client.ClientSession') as mock_session_class:
            mock_session = Mock()
            mock_session.closed = False
            mock_session_class.return_value = mock_session
            
            session = await client._get_session()
            
            assert session == mock_session
            mock_session_class.assert_called_once_with(
                timeout=client.timeout,
                headers=client.default_headers
            )
    
    @pytest.mark.asyncio
    async def test_get_session_reuse(self, client):
        """Test reusing existing session."""
        mock_session = Mock()
        mock_session.closed = False
        client._session = mock_session
        
        session = await client._get_session()
        assert session == mock_session
    
    @pytest.mark.asyncio
    async def test_get_session_closed_recreate(self, client):
        """Test recreating closed session."""
        old_session = Mock()
        old_session.closed = True
        client._session = old_session
        
        with patch('app.services.external_api_client.ClientSession') as mock_session_class:
            new_session = Mock()
            new_session.closed = False
            mock_session_class.return_value = new_session
            
            session = await client._get_session()
            assert session == new_session
    
    @pytest.mark.asyncio
    async def test_get_circuit_new(self, client):
        """Test getting new circuit breaker."""
        with patch('app.services.external_api_client.circuit_registry') as mock_registry:
            mock_circuit = Mock()
            mock_registry.get_circuit = AsyncMock(return_value=mock_circuit)
            
            circuit = await client._get_circuit("test_api")
            
            assert circuit == mock_circuit
            assert client._circuits["test_api"] == mock_circuit
            mock_registry.get_circuit.assert_called_once_with(
                "http_test_api", client._select_config("test_api")
            )
    
    @pytest.mark.asyncio
    async def test_get_circuit_existing(self, client):
        """Test getting existing circuit breaker."""
        mock_circuit = Mock()
        client._circuits["test_api"] = mock_circuit
        
        circuit = await client._get_circuit("test_api")
        assert circuit == mock_circuit
    
    def test_get_fallback_response(self, client):
        """Test fallback response generation."""
        response = client._get_fallback_response("GET", "/test", "test_api")
        
        expected = {
            "error": "service_unavailable",
            "message": "test_api API temporarily unavailable",
            "method": "GET",
            "url": "/test",
            "fallback": True
        }
        assert response == expected
    
    @pytest.mark.asyncio
    async def test_extract_error_data_json(self, client):
        """Test extracting JSON error data."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"error": "Bad Request"})
        
        error_data = await client._extract_error_data(mock_response)
        assert error_data == {"error": "Bad Request"}
    
    @pytest.mark.asyncio
    async def test_extract_error_data_text(self, client):
        """Test extracting text error data when JSON fails."""
        mock_response = AsyncMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text.return_value = "Error message"
        mock_response.status = 400
        
        error_data = await client._extract_error_data(mock_response)
        assert error_data == {"error": "Error message", "status": 400}
    
    @pytest.mark.asyncio
    async def test_process_response_success_json(self, client):
        """Test processing successful JSON response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "success"})
        
        result = await client._process_response(mock_response, "test_api")
        assert result == {"data": "success"}
    
    @pytest.mark.asyncio
    async def test_process_response_success_text(self, client):
        """Test processing successful text response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text.return_value = "Plain text response"
        
        result = await client._process_response(mock_response, "test_api")
        assert result == {"text": "Plain text response", "status": 200}
    
    @pytest.mark.asyncio
    async def test_process_response_error(self, client):
        """Test processing error response."""
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={"error": "Bad Request"})
        
        with pytest.raises(HTTPError) as exc_info:
            await client._process_response(mock_response, "test_api")
        
        assert exc_info.value.status_code == 400
        assert "test_api API error: 400" in str(exc_info.value)
        assert exc_info.value.response_data == {"error": "Bad Request"}
    
    @pytest.mark.asyncio
    async def test_request_success(self, client):
        """Test successful request execution."""
        mock_circuit = AsyncMock()
        mock_circuit.call.return_value = {"success": True}
        
        with patch.object(client, '_get_circuit', return_value=mock_circuit):
            result = await client._request("GET", "/test", "test_api")
            assert result == {"success": True}
            mock_circuit.call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_request_circuit_open(self, client):
        """Test request when circuit is open."""
        from app.core.circuit_breaker import CircuitBreakerOpenError
        
        mock_circuit = AsyncMock()
        mock_circuit.call.side_effect = CircuitBreakerOpenError("Circuit open")
        
        with patch.object(client, '_get_circuit', return_value=mock_circuit), \
             patch('app.services.external_api_client.logger') as mock_logger:
            
            result = await client._request("GET", "/test", "test_api")
            
            expected = {
                "error": "service_unavailable",
                "message": "test_api API temporarily unavailable",
                "method": "GET",
                "url": "/test",
                "fallback": True
            }
            assert result == expected
            mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_method(self, client):
        """Test GET method."""
        with patch.object(client, '_request', return_value={"success": True}) as mock_request:
            result = await client.get("/test", "test_api", params={"key": "value"}, headers={"Auth": "token"})
            
            assert result == {"success": True}
            mock_request.assert_called_once_with(
                "GET", "/test", "test_api", params={"key": "value"}, headers={"Auth": "token"}
            )
    
    @pytest.mark.asyncio
    async def test_post_method(self, client):
        """Test POST method."""
        with patch.object(client, '_request', return_value={"success": True}) as mock_request:
            result = await client.post(
                "/test", "test_api", 
                data="raw_data", 
                json_data={"json": "data"}, 
                headers={"Auth": "token"}
            )
            
            assert result == {"success": True}
            mock_request.assert_called_once_with(
                "POST", "/test", "test_api", 
                data="raw_data", 
                json_data={"json": "data"}, 
                headers={"Auth": "token"}
            )
    
    @pytest.mark.asyncio
    async def test_put_method(self, client):
        """Test PUT method."""
        with patch.object(client, '_request', return_value={"success": True}) as mock_request:
            result = await client.put(
                "/test", "test_api", 
                data={"form": "data"}, 
                headers={"Auth": "token"}
            )
            
            assert result == {"success": True}
            mock_request.assert_called_once_with(
                "PUT", "/test", "test_api", 
                data={"form": "data"}, 
                json_data=None, 
                headers={"Auth": "token"}
            )
    
    @pytest.mark.asyncio
    async def test_delete_method(self, client):
        """Test DELETE method."""
        with patch.object(client, '_request', return_value={"success": True}) as mock_request:
            result = await client.delete("/test", "test_api", headers={"Auth": "token"})
            
            assert result == {"success": True}
            mock_request.assert_called_once_with(
                "DELETE", "/test", "test_api", headers={"Auth": "token"}
            )
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
        mock_circuit = Mock()
        mock_circuit.get_status.return_value = {"health": "healthy", "state": "closed"}
        
        with patch.object(client, '_get_circuit', return_value=mock_circuit), \
             patch.object(client, '_test_connectivity', return_value={"status": "healthy"}):
            
            result = await client.health_check("test_api")
            
            assert result["api_name"] == "test_api"
            assert result["circuit"]["health"] == "healthy"
            assert result["connectivity"]["status"] == "healthy"
            assert result["overall_health"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_error(self, client):
        """Test health check with error."""
        with patch.object(client, '_get_circuit', side_effect=Exception("Circuit error")), \
             patch('app.services.external_api_client.logger') as mock_logger:
            
            result = await client.health_check("test_api")
            
            assert result["api_name"] == "test_api"
            assert result["error"] == "Circuit error"
            assert result["overall_health"] == "unhealthy"
            mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_connectivity_no_base_url(self):
        """Test connectivity test without base URL."""
        client = ResilientHTTPClient()
        result = await client._test_connectivity()
        
        assert result == {"status": "skipped", "reason": "no_base_url"}
    
    @pytest.mark.asyncio
    async def test_test_connectivity_success(self, client):
        """Test successful connectivity test."""
        # Create a proper async context manager class
        class MockResponse:
            def __init__(self, status):
                self.status = status
        
        class MockAsyncContextManager:
            def __init__(self, response):
                self.response = response
            
            async def __aenter__(self):
                return self.response
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        mock_session = Mock()
        mock_response = MockResponse(200)
        mock_session.get.return_value = MockAsyncContextManager(mock_response)
        
        async def mock_get_session():
            return mock_session
        
        with patch.object(client, '_get_session', side_effect=mock_get_session):
            result = await client._test_connectivity()
            
            assert result["status"] == "healthy"
            assert result["response_code"] == 200
    
    @pytest.mark.asyncio
    async def test_test_connectivity_failure(self, client):
        """Test failed connectivity test."""
        mock_session = Mock()
        mock_session.get.side_effect = Exception("Connection failed")
        
        async def mock_get_session():
            return mock_session
        
        with patch.object(client, '_get_session', side_effect=mock_get_session):
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
    
    @pytest.mark.asyncio
    async def test_close_session(self, client):
        """Test closing HTTP session."""
        mock_session = Mock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        client._session = mock_session
        
        await client.close()
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_no_session(self, client):
        """Test closing when no session exists."""
        await client.close()  # Should not raise exception
    
    @pytest.mark.asyncio
    async def test_close_already_closed_session(self, client):
        """Test closing already closed session."""
        mock_session = Mock()
        mock_session.closed = True
        mock_session.close = AsyncMock()
        client._session = mock_session
        
        await client.close()
        mock_session.close.assert_not_called()


class TestRetryableHTTPClient:
    """Test RetryableHTTPClient functionality."""
    
    @pytest.fixture
    def retryable_client(self):
        """Create a RetryableHTTPClient for testing."""
        return RetryableHTTPClient(base_url="https://api.example.com")
    
    def test_retryable_client_inheritance(self, retryable_client):
        """Test RetryableHTTPClient inherits from ResilientHTTPClient."""
        assert isinstance(retryable_client, ResilientHTTPClient)
    
    @pytest.mark.asyncio
    async def test_get_with_retry(self, retryable_client):
        """Test GET with retry functionality."""
        with patch.object(retryable_client, 'get', return_value={"success": True}) as mock_get:
            result = await retryable_client.get_with_retry("/test", "test_api")
            
            assert result == {"success": True}
            mock_get.assert_called_once_with("/test", "test_api")
    
    @pytest.mark.asyncio
    async def test_post_with_retry(self, retryable_client):
        """Test POST with retry functionality."""
        with patch.object(retryable_client, 'post', return_value={"success": True}) as mock_post:
            result = await retryable_client.post_with_retry(
                "/test", "test_api", json_data={"data": "value"}
            )
            
            assert result == {"success": True}
            mock_post.assert_called_once_with("/test", "test_api", json_data={"data": "value"})


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
        
        assert isinstance(client, ResilientHTTPClient)
        assert not isinstance(client, RetryableHTTPClient)
        assert client.base_url == "https://api.test.com"
        assert client.default_headers == {"Auth": "token"}
        assert "test" in manager._clients
    
    def test_get_client_new_retryable(self, manager):
        """Test getting new retryable client."""
        client = manager.get_client("test", "https://api.test.com", {"Auth": "token"}, with_retry=True)
        
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
    
    @pytest.mark.asyncio
    async def test_health_check_all_empty(self, manager):
        """Test health check with no clients."""
        result = await manager.health_check_all()
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_health_check_all_with_clients(self, manager):
        """Test health check with multiple clients."""
        # Create mock clients
        mock_client1 = AsyncMock()
        mock_client1.health_check.return_value = {"status": "healthy"}
        mock_client2 = AsyncMock()
        mock_client2.health_check.return_value = {"status": "degraded"}
        
        manager._clients = {
            "client1": mock_client1,
            "client2": mock_client2
        }
        
        result = await manager.health_check_all()
        
        assert result["client1"] == {"status": "healthy"}
        assert result["client2"] == {"status": "degraded"}
        mock_client1.health_check.assert_called_once_with("client1")
        mock_client2.health_check.assert_called_once_with("client2")
    
    @pytest.mark.asyncio
    async def test_close_all_empty(self, manager):
        """Test closing all clients when none exist."""
        await manager.close_all()
        assert manager._clients == {}
    
    @pytest.mark.asyncio
    async def test_close_all_with_clients(self, manager):
        """Test closing all clients."""
        # Create mock clients
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        
        manager._clients = {
            "client1": mock_client1,
            "client2": mock_client2
        }
        
        await manager.close_all()
        
        mock_client1.close.assert_called_once()
        mock_client2.close.assert_called_once()
        assert manager._clients == {}


class TestGetHTTPClient:
    """Test get_http_client context manager."""
    
    @pytest.mark.asyncio
    async def test_get_http_client_context_manager(self):
        """Test get_http_client context manager."""
        with patch('app.services.external_api_client.http_client_manager') as mock_manager:
            mock_client = Mock()
            mock_manager.get_client.return_value = mock_client
            
            async with get_http_client("test", "https://api.test.com", {"Auth": "token"}, True) as client:
                assert client == mock_client
            
            mock_manager.get_client.assert_called_once_with(
                "test", "https://api.test.com", {"Auth": "token"}, True
            )


class TestConvenienceFunctions:
    """Test convenience functions for common APIs."""
    
    @pytest.mark.asyncio
    async def test_call_google_api_get(self):
        """Test calling Google API with GET method."""
        with patch('app.services.external_api_client.get_http_client') as mock_context:
            mock_client = AsyncMock()
            mock_client.get.return_value = {"success": True}
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await call_google_api("/test", "GET", {"Auth": "token"}, params={"q": "test"})
            
            assert result == {"success": True}
            mock_client.get.assert_called_once_with(
                "/test", "google_api", headers={"Auth": "token"}, params={"q": "test"}
            )
    
    @pytest.mark.asyncio
    async def test_call_google_api_post(self):
        """Test calling Google API with POST method."""
        with patch('app.services.external_api_client.get_http_client') as mock_context:
            mock_client = AsyncMock()
            mock_client.post.return_value = {"success": True}
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await call_google_api("/test", "POST", {"Auth": "token"}, json_data={"data": "value"})
            
            assert result == {"success": True}
            mock_client.post.assert_called_once_with(
                "/test", "google_api", headers={"Auth": "token"}, json_data={"data": "value"}
            )
    
    @pytest.mark.asyncio
    async def test_call_google_api_other_method(self):
        """Test calling Google API with other HTTP method."""
        with patch('app.services.external_api_client.get_http_client') as mock_context:
            mock_client = AsyncMock()
            mock_client._request.return_value = {"success": True}
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await call_google_api("/test", "PUT", {"Auth": "token"}, data={"data": "value"})
            
            assert result == {"success": True}
            mock_client._request.assert_called_once_with(
                "PUT", "/test", "google_api", headers={"Auth": "token"}, data={"data": "value"}
            )
    
    @pytest.mark.asyncio
    async def test_call_openai_api_post(self):
        """Test calling OpenAI API with POST method."""
        with patch('app.services.external_api_client.get_http_client') as mock_context:
            mock_client = AsyncMock()
            mock_client.post.return_value = {"success": True}
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await call_openai_api("/test", "POST", {"Auth": "Bearer token"}, json_data={"prompt": "test"})
            
            assert result == {"success": True}
            mock_client.post.assert_called_once_with(
                "/test", "openai_api", headers={"Auth": "Bearer token"}, json_data={"prompt": "test"}
            )
    
    @pytest.mark.asyncio
    async def test_call_openai_api_get(self):
        """Test calling OpenAI API with GET method."""
        with patch('app.services.external_api_client.get_http_client') as mock_context:
            mock_client = AsyncMock()
            mock_client.get.return_value = {"success": True}
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await call_openai_api("/models", "GET", {"Auth": "Bearer token"})
            
            assert result == {"success": True}
            mock_client.get.assert_called_once_with(
                "/models", "openai_api", headers={"Auth": "Bearer token"}
            )
    
    @pytest.mark.asyncio
    async def test_call_openai_api_other_method(self):
        """Test calling OpenAI API with other HTTP method."""
        with patch('app.services.external_api_client.get_http_client') as mock_context:
            mock_client = AsyncMock()
            mock_client._request.return_value = {"success": True}
            mock_context.return_value.__aenter__.return_value = mock_client
            
            result = await call_openai_api("/test", "DELETE", {"Auth": "Bearer token"})
            
            assert result == {"success": True}
            mock_client._request.assert_called_once_with(
                "DELETE", "/test", "openai_api", headers={"Auth": "Bearer token"}
            )


class TestGlobalClientManager:
    """Test global http_client_manager instance."""
    
    def test_global_manager_exists(self):
        """Test global manager instance exists."""
        assert http_client_manager is not None
        assert isinstance(http_client_manager, HTTPClientManager)
    
    def test_global_manager_singleton_behavior(self):
        """Test that importing returns the same instance."""
        from app.services.external_api_client import http_client_manager as imported_manager
        assert imported_manager is http_client_manager


class TestIntegrationScenarios:
    """Integration test scenarios combining multiple components."""
    
    @pytest.mark.asyncio
    async def test_full_request_flow_success(self):
        """Test complete request flow from client creation to response."""
        # This would be more of an integration test, but we can test the flow with mocks
        
        mock_circuit = AsyncMock()
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        
        # Setup mocks
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"result": "success"})
        # Create a proper async context manager mock
        from unittest.mock import MagicMock
        
        class MockAsyncContextManager:
            async def __aenter__(self):
                return mock_response
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        # Make session.request return the async context manager
        mock_session.request = MagicMock(return_value=MockAsyncContextManager())
        async def mock_circuit_call(func):
            return await func()
        mock_circuit.call = AsyncMock(side_effect=mock_circuit_call)
        
        with patch('app.services.external_api_client.CircuitBreaker') as mock_cb_class, \
             patch('app.services.external_api_client.circuit_registry') as mock_registry, \
             patch('app.services.external_api_client.ClientSession') as mock_session_class:
            
            mock_cb_class.return_value = mock_circuit
            mock_registry.get_circuit = AsyncMock(return_value=mock_circuit)
            mock_session_class.return_value = mock_session
            
            client = ResilientHTTPClient(base_url="https://api.test.com")
            result = await client.get("/endpoint", "test_api")
            
            assert result == {"result": "success"}
    
    @pytest.mark.asyncio
    async def test_error_handling_chain(self):
        """Test error handling through the entire chain."""
        mock_circuit = AsyncMock()
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        
        # Setup error response
        mock_response.status = 500
        mock_response.json = AsyncMock(return_value={"error": "Internal Server Error"})
        # Create a proper async context manager mock for error case
        from unittest.mock import MagicMock
        
        class MockAsyncContextManagerError:
            async def __aenter__(self):
                return mock_response
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        # Make session.request return the async context manager
        mock_session.request = MagicMock(return_value=MockAsyncContextManagerError())
        async def mock_circuit_call_error(func):
            return await func()
        mock_circuit.call = AsyncMock(side_effect=mock_circuit_call_error)
        
        with patch('app.services.external_api_client.CircuitBreaker') as mock_cb_class, \
             patch('app.services.external_api_client.circuit_registry') as mock_registry, \
             patch('app.services.external_api_client.ClientSession') as mock_session_class:
            
            mock_cb_class.return_value = mock_circuit
            mock_registry.get_circuit = AsyncMock(return_value=mock_circuit)
            mock_session_class.return_value = mock_session
            
            client = ResilientHTTPClient(base_url="https://api.test.com")
            
            with pytest.raises(HTTPError) as exc_info:
                await client.get("/endpoint", "test_api")
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.response_data == {"error": "Internal Server Error"}