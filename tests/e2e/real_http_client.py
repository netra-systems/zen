"""Real HTTP Client for E2E Testing

Professional HTTP client with connection pooling, retry logic, and comprehensive error handling.
NO MOCKING - actual network calls for true integration validation.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Reliable HTTP API testing for customer-facing features
- Value Impact: Prevents API bugs that affect user experience
- Revenue Impact: Protects customer conversion and retention
"""

import asyncio
from typing import Any, Dict, Optional

import httpx

from tests.e2e.real_client_types import ClientConfig
from tests.e2e.websocket_dev_utilities import ConnectionMetrics


class RealHTTPClient:
    """Real HTTP client with connection pooling and retry logic"""
    
    def __init__(self, base_url: str, config: Optional[ClientConfig] = None):
        """Initialize HTTP client with configuration"""
        self.base_url = base_url.rstrip('/')
        self.config = config or ClientConfig()
        self.metrics = ConnectionMetrics()
        self._client = self._create_client()
    
    def _create_client(self) -> httpx.AsyncClient:
        """Create configured HTTP client"""
        limits = httpx.Limits(max_connections=self.config.pool_size)
        timeout = httpx.Timeout(self.config.timeout)
        return httpx.AsyncClient(
            limits=limits, timeout=timeout, verify=self.config.verify_ssl
        )
    
    def _get_auth_headers(self, token: Optional[str]) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    async def get(self, path: str, token: Optional[str] = None) -> Dict[str, Any]:
        """Execute GET request with retry logic"""
        url = f"{self.base_url}{path}"
        headers = self._get_auth_headers(token)
        return await self._execute_request("GET", url, headers=headers)
    
    async def post(self, path: str, data: Dict[str, Any], 
                   token: Optional[str] = None) -> Dict[str, Any]:
        """Execute POST request with retry logic"""
        url = f"{self.base_url}{path}"
        headers = self._get_auth_headers(token)
        return await self._execute_request("POST", url, headers=headers, json=data)
    
    async def put(self, path: str, data: Dict[str, Any],
                  token: Optional[str] = None) -> Dict[str, Any]:
        """Execute PUT request with retry logic"""
        url = f"{self.base_url}{path}"
        headers = self._get_auth_headers(token)
        return await self._execute_request("PUT", url, headers=headers, json=data)
    
    async def delete(self, path: str, token: Optional[str] = None) -> Dict[str, Any]:
        """Execute DELETE request with retry logic"""
        url = f"{self.base_url}{path}"
        headers = self._get_auth_headers(token)
        return await self._execute_request("DELETE", url, headers=headers)
    
    async def _execute_request(self, method: str, url: str, 
                             **kwargs) -> Dict[str, Any]:
        """Execute HTTP request with retry logic"""
        for attempt in range(self.config.max_retries + 1):
            try:
                self.metrics.requests_sent += 1
                response = await self._client.request(method, url, **kwargs)
                return await self._process_response(response)
            except Exception as e:
                if attempt == self.config.max_retries:
                    self._record_error(str(e))
                    raise
                delay = self.config.get_retry_delay(attempt)
                await asyncio.sleep(delay)
    
    async def _process_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Process HTTP response"""
        self.metrics.responses_received += 1
        response.raise_for_status()
        return response.json()
    
    def _record_error(self, error: str) -> None:
        """Record error in metrics"""
        self.metrics.last_error = error
        self.metrics.retry_count += 1
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self._client.aclose()
