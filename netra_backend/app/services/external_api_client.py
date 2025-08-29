"""Circuit breaker-enabled external API client for reliable service integrations.

This module provides HTTP clients with circuit breaker protection,
retry logic, and comprehensive error handling for external API calls.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientError, ClientSession, ClientTimeout

from netra_backend.app.core.async_retry_logic import with_retry
from netra_backend.app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitConfig,
    circuit_registry,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExternalAPIConfig:
    """Configuration for external API circuit breakers."""
    
    # Google APIs (OAuth, Gemini, etc.)
    GOOGLE_API_CONFIG = CircuitConfig(
        name="google_api",
        failure_threshold=3,
        recovery_timeout=30.0,
        timeout_seconds=10.0
    )
    
    # OpenAI API
    OPENAI_API_CONFIG = CircuitConfig(
        name="openai_api",
        failure_threshold=5,
        recovery_timeout=20.0,
        timeout_seconds=15.0
    )
    
    # Anthropic API
    ANTHROPIC_API_CONFIG = CircuitConfig(
        name="anthropic_api",
        failure_threshold=5,
        recovery_timeout=20.0,
        timeout_seconds=15.0
    )
    
    # Generic external API
    GENERIC_API_CONFIG = CircuitConfig(
        name="external_api",
        failure_threshold=3,
        recovery_timeout=30.0,
        timeout_seconds=10.0
    )
    
    # Fast APIs (health checks, etc.)
    FAST_API_CONFIG = CircuitConfig(
        name="fast_api",
        failure_threshold=2,
        recovery_timeout=10.0,
        timeout_seconds=3.0
    )


class HTTPError(Exception):
    """Custom HTTP error with status code."""
    
    def __init__(self, status_code: int, message: str, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class ResilientHTTPClient:
    """HTTP client with circuit breaker protection."""
    
    def __init__(self, 
                 base_url: Optional[str] = None,
                 default_headers: Optional[Dict[str, str]] = None,
                 timeout: Optional[ClientTimeout] = None):
        self._init_config(base_url, default_headers, timeout)
        self._init_internal_state()
    
    def _init_config(self, base_url: Optional[str], default_headers: Optional[Dict[str, str]], 
                     timeout: Optional[ClientTimeout]) -> None:
        """Initialize client configuration."""
        self.base_url = base_url
        self.default_headers = default_headers or {}
        self.timeout = timeout or ClientTimeout(total=10.0)
    
    def _init_internal_state(self) -> None:
        """Initialize internal state variables."""
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._session: Optional[ClientSession] = None
    
    async def _get_session(self) -> ClientSession:
        """Get or create HTTP session."""
        if not self._session or self._session.closed:
            self._session = ClientSession(
                timeout=self.timeout,
                headers=self.default_headers
            )
        return self._session
    
    async def _get_circuit(self, api_name: str) -> CircuitBreaker:
        """Get circuit breaker for API."""
        if api_name not in self._circuits:
            config = self._select_config(api_name)
            self._circuits[api_name] = circuit_registry.get_breaker(
                f"http_{api_name}", config
            )
        return self._circuits[api_name]
    
    def _select_config(self, api_name: str) -> CircuitConfig:
        """Select circuit config based on API name."""
        api_lower = api_name.lower()
        return self._get_config_by_type(api_lower)
    
    def _get_config_by_type(self, api_lower: str) -> CircuitConfig:
        """Get config based on API type matching."""
        config_mapping = self._get_api_config_mapping()
        for api_type, config in config_mapping.items():
            if self._matches_api_type(api_lower, api_type):
                return config
        return ExternalAPIConfig.GENERIC_API_CONFIG

    def _get_api_config_mapping(self) -> Dict[str, CircuitConfig]:
        """Get API type to config mapping"""
        return {
            "google": ExternalAPIConfig.GOOGLE_API_CONFIG,
            "openai": ExternalAPIConfig.OPENAI_API_CONFIG,
            "anthropic": ExternalAPIConfig.ANTHROPIC_API_CONFIG,
            "fast": ExternalAPIConfig.FAST_API_CONFIG
        }

    def _matches_api_type(self, api_lower: str, api_type: str) -> bool:
        """Check if API matches the given type"""
        type_checkers = self._get_type_checkers()
        checker = type_checkers.get(api_type)
        return checker(api_lower) if checker else False
    
    def _get_type_checkers(self) -> Dict[str, callable]:
        """Get mapping of API types to checker functions."""
        return {
            "google": self._is_google_api,
            "openai": self._is_openai_api,
            "anthropic": self._is_anthropic_api,
            "fast": self._is_fast_api
        }
    
    def _is_google_api(self, api_lower: str) -> bool:
        """Check if API is Google-based."""
        return "google" in api_lower or "oauth" in api_lower
    
    def _is_openai_api(self, api_lower: str) -> bool:
        """Check if API is OpenAI-based."""
        return "openai" in api_lower or "gpt" in api_lower
    
    def _is_anthropic_api(self, api_lower: str) -> bool:
        """Check if API is Anthropic-based."""
        return "anthropic" in api_lower or "claude" in api_lower
    
    def _is_fast_api(self, api_lower: str) -> bool:
        """Check if API is fast/health API."""
        return "health" in api_lower or "ping" in api_lower
    
    async def get(self, 
                  url: str, 
                  api_name: str = "generic",
                  params: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Perform GET request with circuit breaker protection."""
        return await self._request("GET", url, api_name, params=params, headers=headers)
    
    async def post(self, 
                   url: str, 
                   api_name: str = "generic",
                   data: Optional[Union[Dict[str, Any], str]] = None,
                   json_data: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Perform POST request with circuit breaker protection."""
        return await self._request_with_body("POST", url, api_name, data, json_data, headers)
    
    async def _request_with_body(self, method: str, url: str, api_name: str,
                                data: Optional[Union[Dict[str, Any], str]], 
                                json_data: Optional[Dict[str, Any]], 
                                headers: Optional[Dict[str, str]]) -> Dict[str, Any]:
        """Execute request with body data."""
        return await self._request(method, url, api_name, 
                                 data=data, json_data=json_data, headers=headers)
    
    async def put(self, 
                  url: str, 
                  api_name: str = "generic",
                  data: Optional[Union[Dict[str, Any], str]] = None,
                  json_data: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Perform PUT request with circuit breaker protection."""
        return await self._request_with_body("PUT", url, api_name, data, json_data, headers)
    
    async def delete(self, 
                     url: str, 
                     api_name: str = "generic",
                     headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Perform DELETE request with circuit breaker protection."""
        return await self._request("DELETE", url, api_name, headers=headers)
    
    async def _request(self, 
                      method: str, 
                      url: str, 
                      api_name: str,
                      params: Optional[Dict[str, Any]] = None,
                      data: Optional[Union[Dict[str, Any], str]] = None,
                      json_data: Optional[Dict[str, Any]] = None,
                      headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Execute HTTP request with circuit breaker protection."""
        circuit = await self._get_circuit(api_name)
        request_func = self._create_request_function(method, url, api_name, params, data, json_data, headers)
        return await self._execute_with_circuit(circuit, request_func, method, url, api_name)
    
    def _create_request_function(self, method: str, url: str, api_name: str, 
                                params: Optional[Dict[str, Any]], data: Optional[Union[Dict[str, Any], str]], 
                                json_data: Optional[Dict[str, Any]], headers: Optional[Dict[str, str]]):
        """Create request function for circuit execution."""
        async def _make_request() -> Dict[str, Any]:
            return await self._prepare_and_execute_request(method, url, api_name, params, data, json_data, headers)
        return _make_request
    
    async def _prepare_and_execute_request(self, method: str, url: str, api_name: str,
                                          params: Optional[Dict[str, Any]], 
                                          data: Optional[Union[Dict[str, Any], str]], 
                                          json_data: Optional[Dict[str, Any]], 
                                          headers: Optional[Dict[str, str]]) -> Dict[str, Any]:
        """Prepare request parameters and execute HTTP request."""
        session = await self._get_session()
        full_url = self._build_url(url)
        request_headers = self._merge_headers(headers)
        return await self._execute_http_request(session, method, full_url, params, data, json_data, request_headers, api_name)
    
    async def _execute_http_request(self, session, method: str, full_url: str, 
                                   params, data, json_data, request_headers, api_name: str) -> Dict[str, Any]:
        """Execute HTTP request with session."""
        async with session.request(
            method=method, url=full_url, params=params, 
            data=data, json=json_data, headers=request_headers
        ) as response:
            return await self._process_response(response, api_name)
    
    async def _execute_with_circuit(self, circuit, request_func, method: str, url: str, api_name: str) -> Dict[str, Any]:
        """Execute request with circuit breaker handling."""
        try:
            return await circuit.call(request_func)
        except CircuitBreakerOpenError:
            logger.warning(f"HTTP request blocked - circuit open: {api_name}")
            return self._get_fallback_response(method, url, api_name)
    
    def _build_url(self, url: str) -> str:
        """Build full URL from base URL and endpoint."""
        if self.base_url and not url.startswith(('http://', 'https://')):
            return urljoin(self.base_url, url)
        return url
    
    def _merge_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Merge default and request headers."""
        merged = self.default_headers.copy()
        if headers:
            merged.update(headers)
        return merged
    
    async def _process_response(self, response: aiohttp.ClientResponse, api_name: str) -> Dict[str, Any]:
        """Process HTTP response and handle errors."""
        if response.status >= 400:
            await self._handle_error_response(response, api_name)
        return await self._extract_response_data(response)
    
    async def _handle_error_response(self, response: aiohttp.ClientResponse, api_name: str) -> None:
        """Handle error response by raising appropriate exception."""
        error_data = await self._extract_error_data(response)
        raise HTTPError(
            status_code=response.status,
            message=f"{api_name} API error: {response.status}",
            response_data=error_data
        )
    
    async def _extract_response_data(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Extract response data as JSON or text."""
        try:
            return await response.json()
        except json.JSONDecodeError:
            text_content = await response.text()
            return {"text": text_content, "status": response.status}
    
    async def _extract_error_data(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Extract error data from response."""
        try:
            return await response.json()
        except json.JSONDecodeError:
            return {"error": await response.text(), "status": response.status}
    
    def _get_fallback_response(self, method: str, url: str, api_name: str) -> Dict[str, Any]:
        """Raise exception instead of providing fallback response when circuit is open."""
        logger.error(f"External API circuit breaker is open for {api_name}")
        raise HTTPError(503, f"External API {api_name} temporarily unavailable - circuit breaker open")
    
    async def health_check(self, api_name: str = "generic") -> Dict[str, Any]:
        """Health check for external API."""
        try:
            return await self._perform_health_check(api_name)
        except Exception as e:
            logger.error(f"Health check failed for {api_name}: {e}")
            return self._create_unhealthy_status(api_name, str(e))
    
    async def _perform_health_check(self, api_name: str) -> Dict[str, Any]:
        """Perform health check operations."""
        circuit = await self._get_circuit(api_name)
        circuit_status = circuit.get_status()
        connectivity_status = await self._test_connectivity()
        return self._build_health_status(api_name, circuit_status, connectivity_status)
    
    def _build_health_status(self, api_name: str, circuit_status: Dict[str, Any], 
                            connectivity_status: Dict[str, Any]) -> Dict[str, Any]:
        """Build complete health status response."""
        overall_health = self._assess_health(circuit_status, connectivity_status)
        return self._create_health_status_dict(api_name, circuit_status, connectivity_status, overall_health)
    
    def _create_health_status_dict(self, api_name: str, circuit_status: Dict[str, Any], 
                                  connectivity_status: Dict[str, Any], overall_health: str) -> Dict[str, Any]:
        """Create health status dictionary."""
        base_status = self._get_base_health_fields(api_name, circuit_status)
        extended_status = self._get_extended_health_fields(connectivity_status, overall_health)
        return {**base_status, **extended_status}
    
    def _get_base_health_fields(self, api_name: str, circuit_status: Dict[str, Any]) -> Dict[str, Any]:
        """Get base health status fields."""
        return {"api_name": api_name, "circuit": circuit_status}
    
    def _get_extended_health_fields(self, connectivity_status: Dict[str, Any], overall_health: str) -> Dict[str, Any]:
        """Get extended health status fields."""
        return {"connectivity": connectivity_status, "overall_health": overall_health}
    
    def _create_unhealthy_status(self, api_name: str, error: str) -> Dict[str, Any]:
        """Create unhealthy status response."""
        return {
            "api_name": api_name,
            "error": error,
            "overall_health": "unhealthy"
        }
    
    async def _test_connectivity(self) -> Dict[str, Any]:
        """Test basic connectivity to base URL."""
        if not self.base_url:
            return {"status": "skipped", "reason": "no_base_url"}
        return await self._perform_connectivity_test()
    
    async def _perform_connectivity_test(self) -> Dict[str, Any]:
        """Perform actual connectivity test."""
        try:
            session = await self._get_session()
            async with session.get(self.base_url, timeout=ClientTimeout(total=3.0)) as response:
                return self._create_healthy_connectivity_status(response.status)
        except Exception as e:
            return self._create_unhealthy_connectivity_status(str(e))
    
    def _create_healthy_connectivity_status(self, status_code: int) -> Dict[str, Any]:
        """Create healthy connectivity status."""
        return {"status": "healthy", "response_code": status_code}
    
    def _create_unhealthy_connectivity_status(self, error: str) -> Dict[str, Any]:
        """Create unhealthy connectivity status."""
        return {"status": "unhealthy", "error": error}
    
    def _assess_health(self, circuit_status: Dict[str, Any], connectivity_status: Dict[str, Any]) -> str:
        """Assess overall API health."""
        if self._is_circuit_unhealthy(circuit_status):
            return "unhealthy"
        elif self._is_connectivity_unhealthy(connectivity_status):
            return "degraded"
        elif self._is_circuit_recovering(circuit_status):
            return "recovering"
        return "healthy"
    
    def _is_circuit_unhealthy(self, circuit_status: Dict[str, Any]) -> bool:
        """Check if circuit is unhealthy."""
        return circuit_status.get("health") == "unhealthy"
    
    def _is_connectivity_unhealthy(self, connectivity_status: Dict[str, Any]) -> bool:
        """Check if connectivity is unhealthy."""
        return connectivity_status.get("status") == "unhealthy"
    
    def _is_circuit_recovering(self, circuit_status: Dict[str, Any]) -> bool:
        """Check if circuit is recovering."""
        return circuit_status.get("health") == "recovering"
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


class RetryableHTTPClient(ResilientHTTPClient):
    """HTTP client with both circuit breakers and retry logic."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    @with_retry(max_attempts=3, delay=1.0, backoff_factor=2.0)
    async def get_with_retry(self, *args, **kwargs) -> Dict[str, Any]:
        """GET request with retry logic."""
        return await self.get(*args, **kwargs)
    
    @with_retry(max_attempts=3, delay=1.0, backoff_factor=2.0)
    async def post_with_retry(self, *args, **kwargs) -> Dict[str, Any]:
        """POST request with retry logic."""
        return await self.post(*args, **kwargs)


class HTTPClientManager:
    """Manager for HTTP clients with different configurations."""
    
    def __init__(self):
        self._clients: Dict[str, ResilientHTTPClient] = {}
    
    def get_client(self, 
                   name: str,
                   base_url: Optional[str] = None,
                   headers: Optional[Dict[str, str]] = None,
                   with_retry: bool = False) -> ResilientHTTPClient:
        """Get or create HTTP client."""
        if name not in self._clients:
            self._create_new_client(name, base_url, headers, with_retry)
        return self._clients[name]
    
    def _create_new_client(self, name: str, base_url: Optional[str], 
                          headers: Optional[Dict[str, str]], with_retry: bool) -> None:
        """Create new HTTP client instance."""
        client_class = self._select_client_class(with_retry)
        self._clients[name] = client_class(
            base_url=base_url,
            default_headers=headers
        )
    
    def _select_client_class(self, with_retry: bool) -> type:
        """Select appropriate client class."""
        return RetryableHTTPClient if with_retry else ResilientHTTPClient
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Health check for all HTTP clients."""
        health_checks = {}
        for name, client in self._clients.items():
            health_checks[name] = await client.health_check(name)
        return health_checks
    
    async def close_all(self) -> None:
        """Close all HTTP clients."""
        await self._close_all_clients()
        self._clients.clear()
    
    async def _close_all_clients(self) -> None:
        """Close all client connections."""
        await self._perform_client_closures()
    
    async def _perform_client_closures(self) -> None:
        """Perform individual client closures."""
        for client in self._clients.values():
            await client.close()


# Global HTTP client manager
http_client_manager = HTTPClientManager()


@asynccontextmanager
async def get_http_client(name: str = "default", 
                         base_url: Optional[str] = None,
                         headers: Optional[Dict[str, str]] = None,
                         with_retry: bool = False):
    """Context manager for getting HTTP client with cleanup."""
    client = http_client_manager.get_client(name, base_url, headers, with_retry)
    async with _managed_client_context(client):
        yield client

@asynccontextmanager
async def _managed_client_context(client: ResilientHTTPClient):
    """Manage client context with proper cleanup."""
    try:
        yield client
    finally:
        # Cleanup handled by manager
        pass


# Convenience functions for common APIs
async def call_google_api(endpoint: str, 
                         method: str = "GET",
                         headers: Optional[Dict[str, str]] = None,
                         **kwargs) -> Dict[str, Any]:
    """Call Google API with circuit breaker protection."""
    async with get_http_client("google", "https://googleapis.com") as client:
        return await _execute_google_api_call(client, endpoint, method, headers, **kwargs)

async def _execute_google_api_call(client, endpoint: str, method: str, 
                                  headers: Optional[Dict[str, str]], **kwargs) -> Dict[str, Any]:
    """Execute Google API call with method routing."""
    method_upper = method.upper()
    return await _route_google_api_method(client, endpoint, method_upper, headers, **kwargs)

async def _route_google_api_method(client, endpoint: str, method_upper: str, 
                                  headers: Optional[Dict[str, str]], **kwargs) -> Dict[str, Any]:
    """Route Google API method to appropriate client method."""
    if method_upper == "GET":
        return await client.get(endpoint, "google_api", headers=headers, **kwargs)
    elif method_upper == "POST":
        return await client.post(endpoint, "google_api", headers=headers, **kwargs)
    return await client._request(method_upper, endpoint, "google_api", headers=headers, **kwargs)


async def call_openai_api(endpoint: str,
                         method: str = "POST",
                         headers: Optional[Dict[str, str]] = None,
                         **kwargs) -> Dict[str, Any]:
    """Call OpenAI API with circuit breaker protection."""
    async with get_http_client("openai", "https://api.openai.com") as client:
        return await _execute_openai_api_call(client, endpoint, method, headers, **kwargs)

async def _execute_openai_api_call(client, endpoint: str, method: str, 
                                  headers: Optional[Dict[str, str]], **kwargs) -> Dict[str, Any]:
    """Execute OpenAI API call with method routing."""
    method_upper = method.upper()
    if method_upper == "POST":
        return await client.post(endpoint, "openai_api", headers=headers, **kwargs)
    elif method_upper == "GET":
        return await client.get(endpoint, "openai_api", headers=headers, **kwargs)
    return await client._request(method, endpoint, "openai_api", headers=headers, **kwargs)