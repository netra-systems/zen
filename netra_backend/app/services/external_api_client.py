"""External API Client Service

Handles HTTP requests to external APIs with retry logic, rate limiting, and error handling.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import aiohttp
import time

logger = logging.getLogger(__name__)


class HTTPError(Exception):
    """HTTP error exception for external API calls.
    
    Raised when HTTP requests fail or return error status codes.
    """
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}
        
    def __str__(self) -> str:
        if self.status_code:
            return f"HTTP {self.status_code}: {super().__str__()}"
        return super().__str__()


class HTTPMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class ExternalAPIConfig:
    """Configuration for external API client."""
    base_url: Optional[str] = None
    default_timeout: float = 30.0
    max_retries: int = 3
    rate_limit_per_second: float = 10.0


@dataclass
class APIRequest:
    """API request configuration."""
    url: str
    method: HTTPMethod = HTTPMethod.GET
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    json_data: Optional[Dict[str, Any]] = None
    timeout: float = 30.0


@dataclass
class APIResponse:
    """API response wrapper."""
    status_code: int
    data: Optional[Dict[str, Any]] = None
    text: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    success: bool = False
    error: Optional[str] = None


# Alias for backward compatibility
ResilientHTTPClient = None  # Will be set after class definition


class ExternalAPIClient:
    """Client for making HTTP requests to external APIs."""
    
    def __init__(self, base_url: Optional[str] = None, default_timeout: float = 30.0):
        self.base_url = base_url
        self.default_timeout = default_timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = {}  # Simple rate limiting by host
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.default_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def request(self, request: APIRequest) -> APIResponse:
        """Make HTTP request to external API."""
        try:
            url = request.url
            if self.base_url and not url.startswith('http'):
                url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
            
            session = await self._get_session()
            
            # Apply rate limiting
            await self._apply_rate_limit(url)
            
            async with session.request(
                method=request.method.value,
                url=url,
                headers=request.headers or {},
                params=request.params,
                json=request.json_data,
                timeout=aiohttp.ClientTimeout(total=request.timeout)
            ) as response:
                
                # Read response
                try:
                    response_data = await response.json()
                    response_text = None
                except Exception:
                    response_data = None
                    response_text = await response.text()
                
                api_response = APIResponse(
                    status_code=response.status,
                    data=response_data,
                    text=response_text,
                    headers=dict(response.headers),
                    success=200 <= response.status < 300
                )
                
                if not api_response.success:
                    api_response.error = f"HTTP {response.status}: {response_text or 'Unknown error'}"
                
                logger.debug(f"API request to {url}: {response.status}")
                return api_response
                
        except asyncio.TimeoutError:
            return APIResponse(
                status_code=408,
                error="Request timeout",
                success=False
            )
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return APIResponse(
                status_code=500,
                error=str(e),
                success=False
            )
    
    async def _apply_rate_limit(self, url: str):
        """Apply simple rate limiting."""
        try:
            from urllib.parse import urlparse
            host = urlparse(url).hostname or "unknown"
            
            last_request = self._rate_limiter.get(host, 0)
            current_time = time.time()
            
            # Simple rate limit: max 10 requests per second per host
            if current_time - last_request < 0.1:
                await asyncio.sleep(0.1)
            
            self._rate_limiter[host] = time.time()
            
        except Exception as e:
            logger.debug(f"Rate limiting error: {e}")
    
    async def get(self, url: str, headers: Optional[Dict[str, str]] = None, 
                  params: Optional[Dict[str, Any]] = None) -> APIResponse:
        """Make GET request."""
        request = APIRequest(
            url=url,
            method=HTTPMethod.GET,
            headers=headers,
            params=params
        )
        return await self.request(request)
    
    async def post(self, url: str, json_data: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """Make POST request."""
        request = APIRequest(
            url=url,
            method=HTTPMethod.POST,
            headers=headers,
            json_data=json_data
        )
        return await self.request(request)
    
    async def put(self, url: str, json_data: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """Make PUT request."""
        request = APIRequest(
            url=url,
            method=HTTPMethod.PUT,
            headers=headers,
            json_data=json_data
        )
        return await self.request(request)
    
    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """Make DELETE request."""
        request = APIRequest(
            url=url,
            method=HTTPMethod.DELETE,
            headers=headers
        )
        return await self.request(request)
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience functions
async def get(url: str, headers: Optional[Dict[str, str]] = None, 
              params: Optional[Dict[str, Any]] = None) -> APIResponse:
    """Make a GET request using a temporary client."""
    async with ExternalAPIClient() as client:
        return await client.get(url, headers, params)


async def post(url: str, json_data: Optional[Dict[str, Any]] = None,
               headers: Optional[Dict[str, str]] = None) -> APIResponse:
    """Make a POST request using a temporary client."""
    async with ExternalAPIClient() as client:
        return await client.post(url, json_data, headers)


# Global client instance for reuse
_global_client: Optional[ExternalAPIClient] = None


def get_global_client() -> ExternalAPIClient:
    """Get or create global HTTP client."""
    global _global_client
    if _global_client is None:
        _global_client = ExternalAPIClient()
    return _global_client


async def close_global_client():
    """Close global HTTP client."""
    global _global_client
    if _global_client:
        await _global_client.close()
        _global_client = None


# Set alias for backward compatibility
ResilientHTTPClient = ExternalAPIClient