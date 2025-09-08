"""
SSOT No-Docker Mode Detection

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Enable testing without Docker dependency for development workflow
- Value Impact: Tests can run locally without Docker Compose overhead
- Strategic Impact: Faster development cycles and CI/CD flexibility

This module provides centralized detection of --no-docker mode and provides
appropriate skip conditions for integration tests that require external services.

CRITICAL: This ensures tests gracefully skip when services unavailable rather than hard-failing.
"""

import logging
import os
import pytest
from functools import wraps
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

from test_framework.ssot.service_availability_detector import (
    get_service_detector, 
    ServiceAvailabilityResult,
    ServiceStatus
)
from test_framework.ssot.database_skip_conditions import (
    get_availability_checker,
    DatabaseAvailabilityChecker
)

logger = logging.getLogger(__name__)


@dataclass
class NoDocketModeConfig:
    """Configuration for no-docker mode execution."""
    enabled: bool = False
    skip_service_dependent_tests: bool = True
    allow_mock_fallbacks: bool = True
    service_check_timeout: float = 3.0
    cache_service_checks: bool = True


class NoDockerModeDetector:
    """Centralized detector for --no-docker mode execution."""
    
    def __init__(self):
        self.config = self._detect_no_docker_mode()
        self.service_detector = get_service_detector(timeout=self.config.service_check_timeout)
        self.db_checker = get_availability_checker()
        self._service_cache: Dict[str, bool] = {}
        
    def _detect_no_docker_mode(self) -> NoDocketModeConfig:
        """Detect if running in --no-docker mode from environment or pytest config."""
        
        # Check environment variable first
        no_docker_env = os.getenv("TEST_NO_DOCKER", "").lower() in ("1", "true", "yes")
        
        # Check pytest config if available
        no_docker_pytest = False
        try:
            # This will work if called during pytest execution
            import _pytest.config
            config = _pytest.config.get_config()
            if config and hasattr(config.option, 'no_docker'):
                no_docker_pytest = getattr(config.option, 'no_docker', False)
        except (ImportError, AttributeError, RuntimeError):
            # Not in pytest context or config unavailable
            pass
        
        enabled = no_docker_env or no_docker_pytest
        
        if enabled:
            logger.info("No-Docker mode detected - tests will skip when services unavailable")
        
        return NoDocketModeConfig(
            enabled=enabled,
            skip_service_dependent_tests=True,
            allow_mock_fallbacks=True,
            service_check_timeout=3.0 if enabled else 5.0,
            cache_service_checks=enabled  # Cache more aggressively in no-docker mode
        )
    
    def is_no_docker_mode(self) -> bool:
        """Check if running in no-docker mode."""
        return self.config.enabled
    
    def should_skip_service_dependent_test(self, required_services: List[str]) -> Optional[str]:
        """
        Check if test should be skipped based on service availability.
        
        Args:
            required_services: List of required service names
            
        Returns:
            Skip message if test should be skipped, None if test can run
        """
        if not self.config.enabled:
            # Not in no-docker mode, don't skip
            return None
        
        if not required_services:
            # No service dependencies, can run
            return None
        
        # Check service availability
        unavailable_services = []
        
        for service_name in required_services:
            if service_name in ["backend", "auth", "websocket"]:
                # Check HTTP services
                if not self._check_service_available(service_name):
                    unavailable_services.append(service_name)
                    
            elif service_name in ["postgresql", "clickhouse", "redis"]:
                # Check database services
                if not self._check_database_available(service_name):
                    unavailable_services.append(service_name)
                    
            else:
                logger.warning(f"Unknown service type for availability check: {service_name}")
                unavailable_services.append(f"{service_name} (unknown)")
        
        if unavailable_services:
            return f"--no-docker mode: Required services unavailable: {', '.join(unavailable_services)}"
        
        return None
    
    def _check_service_available(self, service_name: str) -> bool:
        """Check if HTTP service is available."""
        if self.config.cache_service_checks and service_name in self._service_cache:
            return self._service_cache[service_name]
        
        try:
            if service_name == "backend":
                result = self.service_detector.check_service_sync(
                    self.service_detector._endpoints.backend_health, 
                    "backend"
                )
            elif service_name == "auth":
                result = self.service_detector.check_service_sync(
                    self.service_detector._endpoints.auth_health,
                    "auth"
                )
            elif service_name == "websocket":
                # For WebSocket, just check if port is open (simpler check)
                from urllib.parse import urlparse
                parsed = urlparse(self.service_detector._endpoints.websocket_url)
                port = parsed.port or (443 if parsed.scheme == "wss" else 80)
                host = parsed.hostname or "localhost"
                is_available = self.service_detector.check_port_open(host, port, timeout=1.0)
                
                if self.config.cache_service_checks:
                    self._service_cache[service_name] = is_available
                
                return is_available
            else:
                return False
            
            is_available = result.status == ServiceStatus.AVAILABLE
            
            if self.config.cache_service_checks:
                self._service_cache[service_name] = is_available
                
            return is_available
            
        except Exception as e:
            logger.debug(f"Service check failed for {service_name}: {e}")
            if self.config.cache_service_checks:
                self._service_cache[service_name] = False
            return False
    
    def _check_database_available(self, db_name: str) -> bool:
        """Check if database service is available."""
        cache_key = f"db_{db_name}"
        if self.config.cache_service_checks and cache_key in self._service_cache:
            return self._service_cache[cache_key]
        
        try:
            if db_name == "postgresql":
                is_available, _ = self.db_checker.check_postgresql_available()
            elif db_name == "clickhouse":
                is_available, _ = self.db_checker.check_clickhouse_available()
            elif db_name == "redis":
                is_available, _ = self.db_checker.check_redis_available()
            else:
                return False
            
            if self.config.cache_service_checks:
                self._service_cache[cache_key] = is_available
                
            return is_available
            
        except Exception as e:
            logger.debug(f"Database check failed for {db_name}: {e}")
            if self.config.cache_service_checks:
                self._service_cache[cache_key] = False
            return False
    
    def clear_cache(self) -> None:
        """Clear the service availability cache."""
        self._service_cache.clear()
        self.service_detector.clear_cache()


# Global instance
_no_docker_detector: Optional[NoDockerModeDetector] = None


def get_no_docker_detector(force_refresh: bool = False) -> NoDockerModeDetector:
    """Get the global no-docker mode detector instance."""
    global _no_docker_detector
    
    if _no_docker_detector is None or force_refresh:
        _no_docker_detector = NoDockerModeDetector()
    
    return _no_docker_detector


def skip_if_no_docker_and_services_unavailable(*required_services: str):
    """
    Decorator to skip test if running in --no-docker mode and required services unavailable.
    
    Args:
        required_services: List of required service names
        
    Usage:
        @skip_if_no_docker_and_services_unavailable("postgresql", "clickhouse")
        def test_database_integration():
            # Test that requires PostgreSQL and ClickHouse
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        @wraps(test_func)
        def wrapper(*args, **kwargs):
            detector = get_no_docker_detector()
            skip_msg = detector.should_skip_service_dependent_test(list(required_services))
            
            if skip_msg:
                pytest.skip(skip_msg)
            
            return test_func(*args, **kwargs)
        
        return wrapper
    return decorator


def skip_if_no_docker_and_services_unavailable_async(*required_services: str):
    """
    Async version of skip_if_no_docker_and_services_unavailable.
    
    Usage:
        @skip_if_no_docker_and_services_unavailable_async("backend", "auth")
        async def test_async_integration():
            # Async test that requires backend and auth services
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        @wraps(test_func)
        async def wrapper(*args, **kwargs):
            detector = get_no_docker_detector()
            skip_msg = detector.should_skip_service_dependent_test(list(required_services))
            
            if skip_msg:
                pytest.skip(skip_msg)
            
            return await test_func(*args, **kwargs)
        
        return wrapper
    return decorator


# Pytest fixture for no-docker mode detection
@pytest.fixture
def no_docker_mode():
    """Pytest fixture that provides no-docker mode information."""
    return get_no_docker_detector()


@pytest.fixture 
def require_services_in_no_docker(*required_services: str):
    """
    Pytest fixture that skips test if in no-docker mode and services unavailable.
    
    Usage:
        def test_integration(require_services_in_no_docker("postgresql", "redis")):
            # Test will skip if in --no-docker mode and services unavailable
            pass
    """
    def fixture_factory():
        detector = get_no_docker_detector()
        skip_msg = detector.should_skip_service_dependent_test(list(required_services))
        
        if skip_msg:
            pytest.skip(skip_msg)
        
        return {"no_docker_mode": detector.is_no_docker_mode(), "services_available": True}
    
    return pytest.fixture(fixture_factory)


def is_no_docker_mode() -> bool:
    """Simple function to check if running in no-docker mode."""
    return get_no_docker_detector().is_no_docker_mode()


def clear_no_docker_cache() -> None:
    """Clear all no-docker mode detection caches."""
    detector = get_no_docker_detector()
    detector.clear_cache()


# Export all utilities
__all__ = [
    'NoDockerModeDetector',
    'NoDocketModeConfig', 
    'get_no_docker_detector',
    'skip_if_no_docker_and_services_unavailable',
    'skip_if_no_docker_and_services_unavailable_async',
    'no_docker_mode',
    'require_services_in_no_docker',
    'is_no_docker_mode',
    'clear_no_docker_cache'
]