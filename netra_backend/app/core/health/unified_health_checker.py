"""
Unified Health Check Utilities - Cross-Service Health Management

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate health check duplication across all services
- Value Impact: Consistent health check behavior, standardized endpoints and timeouts
- Strategic Impact: Unified monitoring, reduced operational overhead, consistent SLA reporting

This module provides unified health checking that can be used across:
- auth_service (service health and readiness)
- netra_backend (API and agent health)
- dev_launcher (service orchestration and monitoring)

Key functionality:
- Standardized health check patterns with configurable timeouts
- Unified health/readiness endpoint format
- Consistent error handling and retry logic
- Cross-service compatible interface
- Support for both HTTP and direct function call checks

Replaces 6+ duplicate health check implementations with a single unified utility.
Each function  <= 25 lines, class  <= 250 lines total.
"""

import asyncio
import json
import logging
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone

from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    READY = "ready"
    NOT_READY = "not_ready"
    UNKNOWN = "unknown"


class HealthCheckType(Enum):
    """Types of health checks."""
    LIVENESS = "liveness"  # Is the service alive?
    READINESS = "readiness"  # Is the service ready to serve traffic?
    STARTUP = "startup"  # Has the service finished starting up?


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""
    timeout_seconds: float = 5.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    endpoint_path: str = "/health"
    readiness_path: str = "/health/ready"
    startup_path: str = "/health/startup"
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    user_agent: str = "UnifiedHealthChecker/1.0"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    status: HealthStatus
    response_time_ms: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    status_code: Optional[int] = None


class UnifiedHealthChecker:
    """
    Unified health checker for all services.
    
    Provides consistent health checking patterns with standardized timeouts,
    retries, and response formats across all services.
    """
    
    def __init__(self, service_name: str = "unknown", config: Optional[HealthCheckConfig] = None):
        self.service_name = service_name
        self.config = config or HealthCheckConfig()
        self.env = IsolatedEnvironment()
        self._load_config_from_env()
    
    def _parse_timeout_value(self, value: str) -> float:
        """Parse timeout value that may include units like '10s', '5.0', etc.
        
        Args:
            value: Timeout value string (e.g., '10s', '5.0', '30')
            
        Returns:
            float: Timeout in seconds
        """
        if not value:
            return self.config.timeout_seconds
            
        # Handle values with 's' suffix (seconds)
        if value.endswith('s'):
            try:
                return float(value[:-1])
            except ValueError:
                logger.warning(f"Invalid timeout format '{value}', using default {self.config.timeout_seconds}s")
                return self.config.timeout_seconds
        
        # Handle plain numeric values
        try:
            return float(value)
        except ValueError:
            logger.warning(f"Invalid timeout format '{value}', using default {self.config.timeout_seconds}s")
            return self.config.timeout_seconds
    
    def _load_config_from_env(self) -> None:
        """Load health check configuration from environment."""
        # Override config with environment variables if present
        timeout_value = self.env.get("HEALTH_CHECK_TIMEOUT", str(self.config.timeout_seconds))
        self.config.timeout_seconds = self._parse_timeout_value(timeout_value)
        
        self.config.max_retries = int(self.env.get("HEALTH_CHECK_RETRIES", str(self.config.max_retries)))
        
        retry_delay_value = self.env.get("HEALTH_CHECK_RETRY_DELAY", str(self.config.retry_delay_seconds))
        self.config.retry_delay_seconds = self._parse_timeout_value(retry_delay_value)
        
        # Allow custom health endpoints
        self.config.endpoint_path = self.env.get("HEALTH_ENDPOINT_PATH", self.config.endpoint_path)
        self.config.readiness_path = self.env.get("READINESS_ENDPOINT_PATH", self.config.readiness_path)
        self.config.startup_path = self.env.get("STARTUP_ENDPOINT_PATH", self.config.startup_path)
    
    def check_service_health(self, host: str = "localhost", port: int = 8080) -> HealthCheckResult:
        """
        Check service health via HTTP endpoint.
        
        Args:
            host: Service host (default: localhost)
            port: Service port (default: 8080)
        
        Returns:
            HealthCheckResult with status and timing information
        """
        return self._perform_http_check(host, port, self.config.endpoint_path, HealthCheckType.LIVENESS)
    
    def check_service_readiness(self, host: str = "localhost", port: int = 8080) -> HealthCheckResult:
        """
        Check service readiness via HTTP endpoint.
        
        Args:
            host: Service host (default: localhost)
            port: Service port (default: 8080)
        
        Returns:
            HealthCheckResult with readiness status
        """
        return self._perform_http_check(host, port, self.config.readiness_path, HealthCheckType.READINESS)
    
    def check_service_startup(self, host: str = "localhost", port: int = 8080) -> HealthCheckResult:
        """
        Check service startup completion via HTTP endpoint.
        
        Args:
            host: Service host (default: localhost) 
            port: Service port (default: 8080)
        
        Returns:
            HealthCheckResult with startup status
        """
        return self._perform_http_check(host, port, self.config.startup_path, HealthCheckType.STARTUP)
    
    def _perform_http_check(self, host: str, port: int, path: str, check_type: HealthCheckType) -> HealthCheckResult:
        """Perform HTTP health check with retries."""
        url = f"http://{host}:{port}{path}"
        
        for attempt in range(self.config.max_retries):
            start_time = time.time()
            
            try:
                # Create request with timeout and user agent
                request = urllib.request.Request(url)
                request.add_header('User-Agent', self.config.user_agent)
                request.add_header('Accept', 'application/json')
                
                with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    # Check status code
                    if response.status not in self.config.expected_status_codes:
                        return self._create_error_result(
                            f"Unexpected status code: {response.status}",
                            response_time_ms,
                            status_code=response.status
                        )
                    
                    # Parse response body
                    try:
                        response_data = json.loads(response.read())
                        return self._parse_health_response(response_data, response_time_ms, check_type)
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        return self._create_error_result(
                            f"Invalid JSON response: {e}",
                            response_time_ms,
                            status_code=response.status
                        )
                        
            except urllib.error.HTTPError as e:
                response_time_ms = (time.time() - start_time) * 1000
                if attempt == self.config.max_retries - 1:  # Last attempt
                    return self._create_error_result(
                        f"HTTP {e.code}: {e.reason}",
                        response_time_ms,
                        status_code=e.code
                    )
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                response_time_ms = (time.time() - start_time) * 1000
                if attempt == self.config.max_retries - 1:  # Last attempt
                    return self._create_error_result(
                        f"Connection error: {e}",
                        response_time_ms
                    )
            
            # Wait before retry (except on last attempt)
            if attempt < self.config.max_retries - 1:
                time.sleep(self.config.retry_delay_seconds)
        
        # Should not reach here, but just in case
        return self._create_error_result("Max retries exceeded", 0)
    
    def _parse_health_response(self, response_data: Dict, response_time_ms: float, check_type: HealthCheckType) -> HealthCheckResult:
        """Parse health check response data."""
        # Standard response format: {"status": "healthy/ready/etc", ...}
        status_value = response_data.get("status", "unknown").lower()
        
        # Map response status to enum
        if check_type == HealthCheckType.LIVENESS:
            if status_value == "healthy":
                status = HealthStatus.HEALTHY
            elif status_value in ["unhealthy", "degraded"]:
                status = HealthStatus.UNHEALTHY
            else:
                status = HealthStatus.UNKNOWN
        elif check_type == HealthCheckType.READINESS:
            if status_value == "ready":
                status = HealthStatus.READY
            elif status_value in ["not_ready", "starting"]:
                status = HealthStatus.NOT_READY
            else:
                status = HealthStatus.UNKNOWN
        else:  # STARTUP
            if status_value in ["ready", "started"]:
                status = HealthStatus.READY
            elif status_value in ["starting", "initializing"]:
                status = HealthStatus.NOT_READY
            else:
                status = HealthStatus.UNKNOWN
        
        return HealthCheckResult(
            status=status,
            response_time_ms=response_time_ms,
            timestamp=datetime.now(timezone.utc),
            details=response_data,
            status_code=200
        )
    
    def _create_error_result(self, error_message: str, response_time_ms: float, status_code: Optional[int] = None) -> HealthCheckResult:
        """Create error result for failed health checks."""
        return HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            response_time_ms=response_time_ms,
            timestamp=datetime.now(timezone.utc),
            error=error_message,
            status_code=status_code
        )
    
    def check_multiple_services(self, services: Dict[str, Tuple[str, int]]) -> Dict[str, HealthCheckResult]:
        """
        Check health of multiple services.
        
        Args:
            services: Dict of {service_name: (host, port)}
        
        Returns:
            Dict of {service_name: HealthCheckResult}
        """
        results = {}
        for service_name, (host, port) in services.items():
            logger.debug(f"Checking health of {service_name} at {host}:{port}")
            results[service_name] = self.check_service_health(host, port)
        return results
    
    async def check_service_health_async(self, host: str = "localhost", port: int = 8080) -> HealthCheckResult:
        """Async version of health check (runs in thread pool)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.check_service_health, host, port)
    
    async def check_service_readiness_async(self, host: str = "localhost", port: int = 8080) -> HealthCheckResult:
        """Async version of readiness check."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.check_service_readiness, host, port)
    
    def create_health_response(self, is_healthy: bool, details: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create standardized health response format.
        
        Args:
            is_healthy: Whether the service is healthy
            details: Additional details to include
        
        Returns:
            Standardized health response dict
        """
        response = {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "version": self.env.get("SERVICE_VERSION", "unknown")
        }
        
        if details:
            response.update(details)
        
        return response
    
    def create_readiness_response(self, is_ready: bool, details: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create standardized readiness response format.
        
        Args:
            is_ready: Whether the service is ready
            details: Additional details to include
        
        Returns:
            Standardized readiness response dict
        """
        response = {
            "status": "ready" if is_ready else "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "version": self.env.get("SERVICE_VERSION", "unknown")
        }
        
        if details:
            response.update(details)
        
        return response


# Convenience functions for backward compatibility
def check_health_simple(host: str = "localhost", port: int = 8080, timeout: float = 5.0) -> bool:
    """Simple health check that returns boolean (backward compatibility)."""
    checker = UnifiedHealthChecker()
    checker.config.timeout_seconds = timeout
    result = checker.check_service_health(host, port)
    return result.status == HealthStatus.HEALTHY


def check_readiness_simple(host: str = "localhost", port: int = 8080, timeout: float = 5.0) -> bool:
    """Simple readiness check that returns boolean (backward compatibility)."""
    checker = UnifiedHealthChecker()
    checker.config.timeout_seconds = timeout
    result = checker.check_service_readiness(host, port)
    return result.status == HealthStatus.READY


# Global instances for common service patterns
auth_health_checker = UnifiedHealthChecker("auth_service")
backend_health_checker = UnifiedHealthChecker("netra_backend")
launcher_health_checker = UnifiedHealthChecker("dev_launcher")