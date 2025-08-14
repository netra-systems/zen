"""Circuit breaker-enabled external API client for reliable service integrations.

This module provides HTTP clients with circuit breaker protection,
retry logic, and comprehensive error handling for external API calls.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, Union, List
from urllib.parse import urljoin
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError

from app.core.circuit_breaker import (
    CircuitBreaker, CircuitConfig, CircuitBreakerOpenError, circuit_registry
)
from app.core.async_retry_logic import with_retry
from app.logging_config import central_logger

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
        self.base_url = base_url
        self.default_headers = default_headers or {}
        self.timeout = timeout or ClientTimeout(total=10.0)
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
            self._circuits[api_name] = await circuit_registry.get_circuit(
                f"http_{api_name}", config
            )
        return self._circuits[api_name]
    
    def _select_config(self, api_name: str) -> CircuitConfig:
        """Select circuit config based on API name."""
        api_lower = api_name.lower()
        
        if "google" in api_lower or "oauth" in api_lower:
            return ExternalAPIConfig.GOOGLE_API_CONFIG
        elif "openai" in api_lower or "gpt" in api_lower:
            return ExternalAPIConfig.OPENAI_API_CONFIG
        elif "anthropic" in api_lower or "claude" in api_lower:
            return ExternalAPIConfig.ANTHROPIC_API_CONFIG
        elif "health" in api_lower or "ping" in api_lower:
            return ExternalAPIConfig.FAST_API_CONFIG
        else:
            return ExternalAPIConfig.GENERIC_API_CONFIG
    
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
        return await self._request("POST", url, api_name, 
                                 data=data, json_data=json_data, headers=headers)
    
    async def put(self, 
                  url: str, 
                  api_name: str = "generic",
                  data: Optional[Union[Dict[str, Any], str]] = None,
                  json_data: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Perform PUT request with circuit breaker protection."""
        return await self._request("PUT", url, api_name, 
                                 data=data, json_data=json_data, headers=headers)
    
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
        
        async def _make_request() -> Dict[str, Any]:
            session = await self._get_session()
            full_url = self._build_url(url)
            request_headers = self._merge_headers(headers)
            
            async with session.request(
                method=method,
                url=full_url,
                params=params,
                data=data,
                json=json_data,
                headers=request_headers
            ) as response:
                return await self._process_response(response, api_name)
        
        try:
            return await circuit.call(_make_request)
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
            error_data = await self._extract_error_data(response)
            raise HTTPError(
                status_code=response.status,
                message=f"{api_name} API error: {response.status}",
                response_data=error_data
            )
        
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
        """Provide fallback response when circuit is open."""
        return {
            "error": "service_unavailable",
            "message": f"{api_name} API temporarily unavailable",
            "method": method,
            "url": url,
            "fallback": True
        }
    
    async def health_check(self, api_name: str = "generic") -> Dict[str, Any]:
        """Health check for external API."""
        try:
            circuit = await self._get_circuit(api_name)
            circuit_status = circuit.get_status()
            
            # Test basic connectivity if base_url is set
            connectivity_status = await self._test_connectivity()
            
            return {
                "api_name": api_name,
                "circuit": circuit_status,
                "connectivity": connectivity_status,
                "overall_health": self._assess_health(circuit_status, connectivity_status)
            }
        except Exception as e:
            logger.error(f"Health check failed for {api_name}: {e}")
            return {
                "api_name": api_name,
                "error": str(e),
                "overall_health": "unhealthy"
            }
    
    async def _test_connectivity(self) -> Dict[str, Any]:
        """Test basic connectivity to base URL."""
        if not self.base_url:
            return {"status": "skipped", "reason": "no_base_url"}
        
        try:
            session = await self._get_session()
            async with session.get(self.base_url, timeout=ClientTimeout(total=3.0)) as response:
                return {
                    "status": "healthy",
                    "response_code": response.status
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def _assess_health(self, circuit_status: Dict[str, Any], connectivity_status: Dict[str, Any]) -> str:
        """Assess overall API health."""
        if circuit_status.get("health") == "unhealthy":
            return "unhealthy"
        elif connectivity_status.get("status") == "unhealthy":
            return "degraded"
        elif circuit_status.get("health") == "recovering":
            return "recovering"
        else:
            return "healthy"
    
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
            client_class = RetryableHTTPClient if with_retry else ResilientHTTPClient
            self._clients[name] = client_class(
                base_url=base_url,
                default_headers=headers
            )
        return self._clients[name]
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Health check for all HTTP clients."""
        return {
            name: await client.health_check(name)
            for name, client in self._clients.items()
        }
    
    async def close_all(self) -> None:
        """Close all HTTP clients."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()


# Global HTTP client manager
http_client_manager = HTTPClientManager()


@asynccontextmanager
async def get_http_client(name: str = "default", 
                         base_url: Optional[str] = None,
                         headers: Optional[Dict[str, str]] = None,
                         with_retry: bool = False):
    """Context manager for getting HTTP client with cleanup."""
    client = http_client_manager.get_client(name, base_url, headers, with_retry)
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
        if method.upper() == "GET":
            return await client.get(endpoint, "google_api", headers=headers, **kwargs)
        elif method.upper() == "POST":
            return await client.post(endpoint, "google_api", headers=headers, **kwargs)
        else:
            return await client._request(method, endpoint, "google_api", headers=headers, **kwargs)


async def call_openai_api(endpoint: str,
                         method: str = "POST",
                         headers: Optional[Dict[str, str]] = None,
                         **kwargs) -> Dict[str, Any]:
    """Call OpenAI API with circuit breaker protection."""
    async with get_http_client("openai", "https://api.openai.com") as client:
        if method.upper() == "POST":
            return await client.post(endpoint, "openai_api", headers=headers, **kwargs)
        elif method.upper() == "GET":
            return await client.get(endpoint, "openai_api", headers=headers, **kwargs)
        else:
            return await client._request(method, endpoint, "openai_api", headers=headers, **kwargs)