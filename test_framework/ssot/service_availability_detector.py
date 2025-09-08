"""
SSOT Service Availability Detector

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Reliable integration testing without Docker dependency
- Value Impact: Tests can run in any environment with graceful service detection
- Strategic Impact: Enables testing on developer machines, CI/CD, and production-like environments

This module provides intelligent service availability detection that:
1. Checks if services are running and reachable
2. Provides clear skip conditions for tests when services unavailable
3. Distinguishes between configuration issues vs service downtime
4. Enables mock fallbacks for offline development

CRITICAL: This replaces hard failures with intelligent service detection
"""

import asyncio
import logging
import socket
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple, Any, List
from urllib.parse import urlparse

import aiohttp
import httpx
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service availability status enumeration."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ServiceAvailabilityResult:
    """Result of service availability check."""
    status: ServiceStatus
    url: str
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    service_type: Optional[str] = None
    can_mock: bool = False


@dataclass
class ServiceEndpoints:
    """Standard service endpoints configuration."""
    backend_base: str
    auth_base: str
    websocket_base: str
    
    @property
    def backend_health(self) -> str:
        return f"{self.backend_base}/health"
    
    @property 
    def auth_health(self) -> str:
        return f"{self.auth_base}/health"
    
    @property
    def websocket_url(self) -> str:
        # Convert HTTP to WebSocket URL
        parsed = urlparse(self.backend_base)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        return f"{ws_scheme}://{parsed.netloc}/ws"


class ServiceAvailabilityDetector:
    """Centralized service availability detection for integration tests."""
    
    def __init__(self, timeout: float = 5.0):
        """Initialize detector with configurable timeout.
        
        Args:
            timeout: Connection timeout in seconds
        """
        self.timeout = timeout
        self.env = get_env()
        self._endpoints = self._build_service_endpoints()
        self._cache: Dict[str, Tuple[ServiceAvailabilityResult, float]] = {}
        self._cache_ttl = 30.0  # Cache results for 30 seconds
        
    def _build_service_endpoints(self) -> ServiceEndpoints:
        """Build service endpoints from environment configuration."""
        # Get ports from environment with fallbacks
        backend_port = self.env.get("BACKEND_PORT", "8000")
        auth_port = self.env.get("AUTH_SERVICE_PORT", "8081")
        
        # Build base URLs
        backend_base = self.env.get("BACKEND_SERVICE_URL", f"http://localhost:{backend_port}")
        auth_base = self.env.get("AUTH_SERVICE_URL", f"http://localhost:{auth_port}")
        
        # WebSocket URL is derived from backend
        parsed_backend = urlparse(backend_base)
        ws_scheme = "wss" if parsed_backend.scheme == "https" else "ws"
        websocket_base = f"{ws_scheme}://{parsed_backend.netloc}"
        
        return ServiceEndpoints(
            backend_base=backend_base,
            auth_base=auth_base,
            websocket_base=websocket_base
        )
    
    def _is_cache_valid(self, url: str) -> bool:
        """Check if cached result is still valid."""
        if url not in self._cache:
            return False
        
        _, cached_time = self._cache[url]
        return time.time() - cached_time < self._cache_ttl
    
    def _get_cached_result(self, url: str) -> Optional[ServiceAvailabilityResult]:
        """Get cached result if valid."""
        if self._is_cache_valid(url):
            result, _ = self._cache[url]
            return result
        return None
    
    def _cache_result(self, url: str, result: ServiceAvailabilityResult) -> None:
        """Cache a service availability result."""
        self._cache[url] = (result, time.time())
    
    async def check_service_async(self, url: str, service_type: str = "unknown") -> ServiceAvailabilityResult:
        """Check service availability asynchronously.
        
        Args:
            url: Service URL to check
            service_type: Type of service (for better error messages)
            
        Returns:
            ServiceAvailabilityResult with availability status
        """
        # Check cache first
        cached_result = self._get_cached_result(url)
        if cached_result:
            logger.debug(f"Using cached availability result for {url}")
            return cached_result
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url) as response:
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    result = ServiceAvailabilityResult(
                        status=ServiceStatus.AVAILABLE if response.status == 200 else ServiceStatus.ERROR,
                        url=url,
                        response_time_ms=response_time_ms,
                        status_code=response.status,
                        service_type=service_type,
                        can_mock=service_type in ["backend", "auth"]
                    )
                    
                    if response.status != 200:
                        result.error_message = f"HTTP {response.status}"
                    
                    self._cache_result(url, result)
                    logger.info(f"Service check: {service_type} at {url} -> {result.status.value} ({response_time_ms:.1f}ms)")
                    return result
                    
        except asyncio.TimeoutError:
            result = ServiceAvailabilityResult(
                status=ServiceStatus.TIMEOUT,
                url=url,
                error_message=f"Timeout after {self.timeout}s",
                service_type=service_type,
                can_mock=service_type in ["backend", "auth"]
            )
            
        except aiohttp.ClientConnectorError as e:
            result = ServiceAvailabilityResult(
                status=ServiceStatus.UNAVAILABLE,
                url=url,
                error_message=f"Connection failed: {str(e)}",
                service_type=service_type,
                can_mock=service_type in ["backend", "auth"]
            )
            
        except Exception as e:
            result = ServiceAvailabilityResult(
                status=ServiceStatus.ERROR,
                url=url,
                error_message=f"Unexpected error: {str(e)}",
                service_type=service_type,
                can_mock=service_type in ["backend", "auth"]
            )
        
        self._cache_result(url, result)
        logger.warning(f"Service check: {service_type} at {url} -> {result.status.value} ({result.error_message})")
        return result
    
    def check_service_sync(self, url: str, service_type: str = "unknown") -> ServiceAvailabilityResult:
        """Check service availability synchronously.
        
        Args:
            url: Service URL to check
            service_type: Type of service (for better error messages)
            
        Returns:
            ServiceAvailabilityResult with availability status
        """
        # Check cache first
        cached_result = self._get_cached_result(url)
        if cached_result:
            logger.debug(f"Using cached availability result for {url}")
            return cached_result
        
        start_time = time.time()
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                response_time_ms = (time.time() - start_time) * 1000
                
                result = ServiceAvailabilityResult(
                    status=ServiceStatus.AVAILABLE if response.status_code == 200 else ServiceStatus.ERROR,
                    url=url,
                    response_time_ms=response_time_ms,
                    status_code=response.status_code,
                    service_type=service_type,
                    can_mock=service_type in ["backend", "auth"]
                )
                
                if response.status_code != 200:
                    result.error_message = f"HTTP {response.status_code}"
                
                self._cache_result(url, result)
                logger.info(f"Service check: {service_type} at {url} -> {result.status.value} ({response_time_ms:.1f}ms)")
                return result
                
        except httpx.TimeoutException:
            result = ServiceAvailabilityResult(
                status=ServiceStatus.TIMEOUT,
                url=url,
                error_message=f"Timeout after {self.timeout}s",
                service_type=service_type,
                can_mock=service_type in ["backend", "auth"]
            )
            
        except httpx.ConnectError as e:
            result = ServiceAvailabilityResult(
                status=ServiceStatus.UNAVAILABLE,
                url=url,
                error_message=f"Connection failed: {str(e)}",
                service_type=service_type,
                can_mock=service_type in ["backend", "auth"]
            )
            
        except Exception as e:
            result = ServiceAvailabilityResult(
                status=ServiceStatus.ERROR,
                url=url,
                error_message=f"Unexpected error: {str(e)}",
                service_type=service_type,
                can_mock=service_type in ["backend", "auth"]
            )
        
        self._cache_result(url, result)
        logger.warning(f"Service check: {service_type} at {url} -> {result.status.value} ({result.error_message})")
        return result
    
    def check_port_open(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """Check if a specific port is open (fast socket check).
        
        Args:
            host: Host to check
            port: Port number
            timeout: Socket timeout in seconds
            
        Returns:
            True if port is open and accepting connections
        """
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.error, OSError):
            return False
    
    async def check_websocket_availability(self, ws_url: str) -> ServiceAvailabilityResult:
        """Check WebSocket endpoint availability.
        
        Args:
            ws_url: WebSocket URL to test
            
        Returns:
            ServiceAvailabilityResult for WebSocket endpoint
        """
        # Check cache first
        cached_result = self._get_cached_result(ws_url)
        if cached_result:
            logger.debug(f"Using cached WebSocket availability result for {ws_url}")
            return cached_result
        
        start_time = time.time()
        
        try:
            import websockets
            
            # Attempt WebSocket connection with timeout
            async with websockets.connect(ws_url, timeout=self.timeout) as websocket:
                response_time_ms = (time.time() - start_time) * 1000
                
                # Try to send a ping
                await websocket.ping()
                
                result = ServiceAvailabilityResult(
                    status=ServiceStatus.AVAILABLE,
                    url=ws_url,
                    response_time_ms=response_time_ms,
                    service_type="websocket",
                    can_mock=False  # WebSocket mocking is more complex
                )
                
                self._cache_result(ws_url, result)
                logger.info(f"WebSocket check: {ws_url} -> {result.status.value} ({response_time_ms:.1f}ms)")
                return result
                
        except asyncio.TimeoutError:
            result = ServiceAvailabilityResult(
                status=ServiceStatus.TIMEOUT,
                url=ws_url,
                error_message=f"WebSocket timeout after {self.timeout}s",
                service_type="websocket",
                can_mock=False
            )
            
        except Exception as e:
            result = ServiceAvailabilityResult(
                status=ServiceStatus.UNAVAILABLE,
                url=ws_url,
                error_message=f"WebSocket connection failed: {str(e)}",
                service_type="websocket", 
                can_mock=False
            )
        
        self._cache_result(ws_url, result)
        logger.warning(f"WebSocket check: {ws_url} -> {result.status.value} ({result.error_message})")
        return result
    
    async def check_all_services(self) -> Dict[str, ServiceAvailabilityResult]:
        """Check availability of all configured services.
        
        Returns:
            Dictionary mapping service names to availability results
        """
        results = {}
        
        # Check core services
        tasks = [
            ("backend", self.check_service_async(self._endpoints.backend_health, "backend")),
            ("auth", self.check_service_async(self._endpoints.auth_health, "auth")),
            ("websocket", self.check_websocket_availability(self._endpoints.websocket_url))
        ]
        
        # Run all checks concurrently
        for service_name, task in tasks:
            try:
                result = await task
                results[service_name] = result
            except Exception as e:
                logger.error(f"Failed to check {service_name} service: {e}")
                results[service_name] = ServiceAvailabilityResult(
                    status=ServiceStatus.ERROR,
                    url=f"unknown-{service_name}",
                    error_message=f"Check failed: {str(e)}",
                    service_type=service_name
                )
        
        return results
    
    def check_all_services_sync(self) -> Dict[str, ServiceAvailabilityResult]:
        """Check availability of all configured services synchronously.
        
        Returns:
            Dictionary mapping service names to availability results
        """
        results = {}
        
        # Check HTTP services
        results["backend"] = self.check_service_sync(self._endpoints.backend_health, "backend")
        results["auth"] = self.check_service_sync(self._endpoints.auth_health, "auth")
        
        # For WebSocket, we just check if the port is open
        parsed_ws = urlparse(self._endpoints.websocket_url)
        port = parsed_ws.port or (443 if parsed_ws.scheme == "wss" else 80)
        host = parsed_ws.hostname or "localhost"
        
        if self.check_port_open(host, port):
            results["websocket"] = ServiceAvailabilityResult(
                status=ServiceStatus.AVAILABLE,
                url=self._endpoints.websocket_url,
                service_type="websocket"
            )
        else:
            results["websocket"] = ServiceAvailabilityResult(
                status=ServiceStatus.UNAVAILABLE,
                url=self._endpoints.websocket_url,
                error_message=f"Port {port} not open on {host}",
                service_type="websocket"
            )
        
        return results
    
    def generate_skip_message(self, service_results: Dict[str, ServiceAvailabilityResult], 
                            required_services: List[str]) -> Optional[str]:
        """Generate pytest skip message if required services unavailable.
        
        Args:
            service_results: Results from check_all_services()
            required_services: List of service names required for test
            
        Returns:
            Skip message if services unavailable, None if all available
        """
        unavailable_services = []
        
        for service_name in required_services:
            if service_name not in service_results:
                unavailable_services.append(f"{service_name} (not checked)")
                continue
                
            result = service_results[service_name]
            if result.status not in [ServiceStatus.AVAILABLE]:
                error_detail = f" ({result.error_message})" if result.error_message else ""
                unavailable_services.append(f"{service_name}{error_detail}")
        
        if unavailable_services:
            return f"Required services unavailable: {', '.join(unavailable_services)}"
        
        return None
    
    def clear_cache(self) -> None:
        """Clear the availability check cache."""
        self._cache.clear()
        logger.debug("Service availability cache cleared")


# Global instance for easy access
_global_detector: Optional[ServiceAvailabilityDetector] = None


def get_service_detector(timeout: float = 5.0) -> ServiceAvailabilityDetector:
    """Get global service availability detector instance.
    
    Args:
        timeout: Connection timeout in seconds
        
    Returns:
        ServiceAvailabilityDetector instance
    """
    global _global_detector
    
    if _global_detector is None:
        _global_detector = ServiceAvailabilityDetector(timeout=timeout)
    
    return _global_detector


def require_services(service_names: List[str], timeout: float = 5.0) -> Dict[str, ServiceAvailabilityResult]:
    """Check required services and return results for pytest usage.
    
    This is the main function tests should use to check service availability.
    
    Args:
        service_names: List of required service names ("backend", "auth", "websocket")
        timeout: Connection timeout in seconds
        
    Returns:
        Dictionary of service availability results
        
    Usage:
        def test_backend_integration():
            services = require_services(["backend", "auth"])
            skip_msg = get_service_detector().generate_skip_message(services, ["backend", "auth"])
            if skip_msg:
                pytest.skip(skip_msg)
            
            # Test code here - services are confirmed available
    """
    detector = get_service_detector(timeout=timeout)
    return detector.check_all_services_sync()


async def require_services_async(service_names: List[str], timeout: float = 5.0) -> Dict[str, ServiceAvailabilityResult]:
    """Check required services asynchronously.
    
    Args:
        service_names: List of required service names
        timeout: Connection timeout in seconds
        
    Returns:
        Dictionary of service availability results
    """
    detector = get_service_detector(timeout=timeout)
    return await detector.check_all_services()