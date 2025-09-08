"""
Auth Service Integration Test Helpers

This module provides utilities for integration tests to handle auth service availability
gracefully, preventing cascading failures when services are not available.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Reliability
- Value Impact: Enables reliable integration testing without Docker dependencies
- Strategic Impact: Reduces false test failures and improves developer productivity
"""

import asyncio
import logging
import httpx
from typing import Optional, Dict, Any, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AuthServiceStatus:
    """Status of auth service for integration tests."""
    available: bool
    url: str
    health_status: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    last_check_time: Optional[float] = None


class AuthServiceIntegrationHelper:
    """Helper class for auth service integration test management."""
    
    def __init__(self, auth_service_url: str = "http://localhost:8081"):
        """Initialize helper with auth service URL.
        
        Args:
            auth_service_url: URL of the auth service to check
        """
        self.auth_service_url = auth_service_url
        self._status_cache: Optional[AuthServiceStatus] = None
        self._cache_duration = 10  # Cache status for 10 seconds
        
    async def check_auth_service_availability(self, timeout: float = 2.0) -> AuthServiceStatus:
        """Check if auth service is available and healthy.
        
        Args:
            timeout: Timeout for health check request
            
        Returns:
            AuthServiceStatus with availability information
        """
        import time
        
        # Check cache first
        if (self._status_cache and 
            self._status_cache.last_check_time and 
            time.time() - self._status_cache.last_check_time < self._cache_duration):
            logger.debug(f"Using cached auth service status: {self._status_cache.available}")
            return self._status_cache
        
        logger.info(f"Checking auth service availability at {self.auth_service_url}")
        
        try:
            async with httpx.AsyncClient() as client:
                # Try health endpoint first
                try:
                    response = await client.get(
                        f"{self.auth_service_url}/health",
                        timeout=timeout
                    )
                    
                    if response.status_code == 200:
                        health_data = response.json()
                        status = AuthServiceStatus(
                            available=True,
                            url=self.auth_service_url,
                            health_status=health_data,
                            last_check_time=time.time()
                        )
                        logger.info(f"Auth service is healthy: {health_data}")
                    else:
                        # Service responded but not healthy
                        status = AuthServiceStatus(
                            available=False,
                            url=self.auth_service_url,
                            error_message=f"Health check returned {response.status_code}: {response.text}",
                            last_check_time=time.time()
                        )
                        logger.warning(f"Auth service health check failed: {response.status_code}")
                        
                except httpx.RequestError:
                    # Health endpoint failed, try basic connectivity
                    try:
                        response = await client.get(
                            self.auth_service_url,
                            timeout=timeout
                        )
                        # Any response means service is at least running
                        status = AuthServiceStatus(
                            available=True,
                            url=self.auth_service_url,
                            error_message=f"Health endpoint unavailable but service running (status: {response.status_code})",
                            last_check_time=time.time()
                        )
                        logger.info(f"Auth service is running but health endpoint unavailable")
                    except httpx.RequestError as e:
                        # Complete connection failure
                        status = AuthServiceStatus(
                            available=False,
                            url=self.auth_service_url,
                            error_message=f"Connection failed: {str(e)}",
                            last_check_time=time.time()
                        )
                        logger.warning(f"Auth service connection failed: {e}")
                        
        except Exception as e:
            # Unexpected error
            status = AuthServiceStatus(
                available=False,
                url=self.auth_service_url,
                error_message=f"Unexpected error: {str(e)}",
                last_check_time=time.time()
            )
            logger.error(f"Unexpected error checking auth service: {e}")
        
        # Cache the result
        self._status_cache = status
        return status
    
    async def wait_for_auth_service(self, max_wait_time: float = 30.0, check_interval: float = 2.0) -> bool:
        """Wait for auth service to become available.
        
        Args:
            max_wait_time: Maximum time to wait in seconds
            check_interval: Time between checks in seconds
            
        Returns:
            True if service became available, False if timed out
        """
        import time
        
        start_time = time.time()
        logger.info(f"Waiting for auth service to become available (max {max_wait_time}s)")
        
        while time.time() - start_time < max_wait_time:
            status = await self.check_auth_service_availability()
            if status.available:
                elapsed = time.time() - start_time
                logger.info(f"Auth service became available after {elapsed:.1f}s")
                return True
            
            logger.debug(f"Auth service not yet available: {status.error_message}")
            await asyncio.sleep(check_interval)
        
        elapsed = time.time() - start_time
        logger.warning(f"Auth service did not become available within {elapsed:.1f}s")
        return False
    
    @asynccontextmanager
    async def auth_service_context(self, require_available: bool = False):
        """Context manager for auth service integration tests.
        
        Args:
            require_available: If True, will skip/fail if auth service not available
            
        Yields:
            AuthServiceStatus: Current status of auth service
            
        Raises:
            pytest.skip: If require_available=True and service unavailable
        """
        status = await self.check_auth_service_availability()
        
        if require_available and not status.available:
            import pytest
            pytest.skip(f"Auth service not available: {status.error_message}")
        
        logger.info(f"Auth service integration test context - available: {status.available}")
        
        try:
            yield status
        finally:
            # Cleanup if needed
            pass
    
    def get_integration_test_recommendations(self, status: AuthServiceStatus) -> Dict[str, Any]:
        """Get recommendations for integration test configuration based on auth service status.
        
        Args:
            status: Current auth service status
            
        Returns:
            Dictionary with test configuration recommendations
        """
        if status.available:
            return {
                "run_auth_tests": True,
                "use_real_auth": True,
                "expect_auth_failures": False,
                "circuit_breaker_tolerance": "normal",
                "recommended_timeout": 5.0,
                "test_categories": ["full_integration", "auth_validation", "circuit_breaker_recovery"]
            }
        else:
            return {
                "run_auth_tests": False,
                "use_real_auth": False,
                "expect_auth_failures": True,
                "circuit_breaker_tolerance": "high",
                "recommended_timeout": 2.0,
                "test_categories": ["graceful_degradation", "service_unavailable_handling"],
                "skip_reason": status.error_message,
                "alternative_approaches": [
                    "Test error handling and graceful degradation",
                    "Test circuit breaker behavior with simulated failures",
                    "Test fallback mechanisms and user notifications"
                ]
            }


# Global helper instance
_global_auth_helper: Optional[AuthServiceIntegrationHelper] = None


def get_auth_service_helper(auth_service_url: str = "http://localhost:8081") -> AuthServiceIntegrationHelper:
    """Get global auth service integration helper instance.
    
    Args:
        auth_service_url: URL of auth service to check
        
    Returns:
        AuthServiceIntegrationHelper instance
    """
    global _global_auth_helper
    if _global_auth_helper is None or _global_auth_helper.auth_service_url != auth_service_url:
        _global_auth_helper = AuthServiceIntegrationHelper(auth_service_url)
    return _global_auth_helper


async def check_auth_service_quick(auth_service_url: str = "http://localhost:8081") -> bool:
    """Quick check if auth service is available.
    
    Args:
        auth_service_url: URL of auth service to check
        
    Returns:
        True if available, False otherwise
    """
    helper = get_auth_service_helper(auth_service_url)
    status = await helper.check_auth_service_availability(timeout=1.0)
    return status.available


# Pytest integration decorators and fixtures
def pytest_auth_service_required(auth_service_url: str = "http://localhost:8081"):
    """Decorator to skip test if auth service is not available.
    
    Args:
        auth_service_url: URL of auth service to check
        
    Usage:
        @pytest_auth_service_required()
        async def test_auth_integration():
            # This test will be skipped if auth service unavailable
            pass
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            helper = get_auth_service_helper(auth_service_url)
            async with helper.auth_service_context(require_available=True) as status:
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def pytest_auth_service_graceful(auth_service_url: str = "http://localhost:8081"):
    """Decorator to provide auth service status to test for graceful handling.
    
    Args:
        auth_service_url: URL of auth service to check
        
    Usage:
        @pytest_auth_service_graceful()
        async def test_auth_graceful(auth_status):
            if auth_status.available:
                # Test normal auth flow
            else:
                # Test error handling and graceful degradation
    """
    def decorator(func):
        import functools
        import inspect
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            helper = get_auth_service_helper(auth_service_url)
            status = await helper.check_auth_service_availability()
            
            # Check if function expects auth_status parameter
            sig = inspect.signature(func)
            if 'auth_status' in sig.parameters:
                kwargs['auth_status'] = status
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Fixture for pytest integration
def auth_service_status_fixture():
    """Pytest fixture that provides auth service status."""
    import pytest
    
    @pytest.fixture
    async def auth_service_status():
        helper = get_auth_service_helper()
        return await helper.check_auth_service_availability()
    
    return auth_service_status


def auth_service_helper_fixture():
    """Pytest fixture that provides auth service helper."""
    import pytest
    
    @pytest.fixture
    def auth_service_helper():
        return get_auth_service_helper()
    
    return auth_service_helper


__all__ = [
    'AuthServiceStatus',
    'AuthServiceIntegrationHelper',
    'get_auth_service_helper',
    'check_auth_service_quick',
    'pytest_auth_service_required',
    'pytest_auth_service_graceful',
    'auth_service_status_fixture',
    'auth_service_helper_fixture'
]