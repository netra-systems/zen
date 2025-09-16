"""Docker Circuit Breaker - Test Framework Docker Integration Protection

This module provides circuit breaker functionality specifically for Docker operations
in the test framework, preventing cascading failures when Docker services are
unavailable or degraded.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure Stability
- Business Goal: Prevent test suite failures due to Docker infrastructure issues
- Value Impact: Fast failure detection, improved developer experience
- Revenue Impact: Protects development velocity by preventing hanging tests

Key Features:
- Docker service health monitoring with circuit breaker patterns
- Container startup failure protection
- Service unavailability detection
- Integration with existing test framework infrastructure
"""

import asyncio
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# Import from the existing circuit breaker system
from netra_backend.app.core.circuit_breaker import (
    CircuitState,
    CircuitConfig,
    CircuitBreakerOpenError,
    CircuitOpenException,
)

logger = logging.getLogger(__name__)


class DockerServiceStatus(Enum):
    """Docker service status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    STARTING = "starting"
    FAILED = "failed"


@dataclass
class DockerCircuitConfig:
    """Docker-specific circuit breaker configuration."""
    service_name: str
    failure_threshold: int = 3
    recovery_timeout: float = 60.0
    health_check_timeout: float = 30.0
    max_startup_time: float = 120.0
    enable_fast_fail: bool = True


@dataclass
class DockerServiceHealth:
    """Docker service health information."""
    service_name: str
    status: DockerServiceStatus
    container_id: Optional[str] = None
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    error_message: Optional[str] = None
    startup_time: Optional[float] = None


class DockerCircuitBreaker:
    """Circuit breaker for Docker service operations."""

    def __init__(self, config: DockerCircuitConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None

    def is_call_allowed(self) -> bool:
        """Check if calls to the Docker service are allowed."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def record_success(self) -> None:
        """Record a successful Docker operation."""
        self.failure_count = 0
        self.last_success_time = time.time()
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed Docker operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Docker circuit breaker OPEN for {self.config.service_name} "
                f"after {self.failure_count} failures"
            )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout


class DockerCircuitBreakerManager:
    """Manager for multiple Docker service circuit breakers."""

    def __init__(self):
        self._circuit_breakers: Dict[str, DockerCircuitBreaker] = {}
        self._service_health: Dict[str, DockerServiceHealth] = {}

    def get_circuit_breaker(self, service_name: str, config: Optional[DockerCircuitConfig] = None) -> DockerCircuitBreaker:
        """Get or create a circuit breaker for a Docker service."""
        if service_name not in self._circuit_breakers:
            if not config:
                config = DockerCircuitConfig(service_name=service_name)
            self._circuit_breakers[service_name] = DockerCircuitBreaker(config)
        return self._circuit_breakers[service_name]

    def update_service_health(self, service_name: str, health: DockerServiceHealth) -> None:
        """Update health information for a Docker service."""
        self._service_health[service_name] = health

        # Update circuit breaker based on health
        circuit_breaker = self.get_circuit_breaker(service_name)
        if health.status == DockerServiceStatus.HEALTHY:
            circuit_breaker.record_success()
        elif health.status in (DockerServiceStatus.FAILED, DockerServiceStatus.UNAVAILABLE):
            circuit_breaker.record_failure()

    def is_service_available(self, service_name: str) -> bool:
        """Check if a Docker service is available for operations."""
        circuit_breaker = self.get_circuit_breaker(service_name)
        return circuit_breaker.is_call_allowed()

    def get_service_status(self, service_name: str) -> Optional[DockerServiceHealth]:
        """Get current health status for a Docker service."""
        return self._service_health.get(service_name)

    @contextmanager
    def docker_operation(self, service_name: str):
        """Context manager for Docker operations with circuit breaker protection."""
        circuit_breaker = self.get_circuit_breaker(service_name)

        if not circuit_breaker.is_call_allowed():
            raise CircuitOpenException(f"Docker service {service_name} circuit is OPEN")

        try:
            yield
            circuit_breaker.record_success()
        except Exception as e:
            circuit_breaker.record_failure()
            logger.error(f"Docker operation failed for {service_name}: {e}")
            raise


# Global instance for easy access
_docker_circuit_manager = DockerCircuitBreakerManager()


def get_docker_circuit_manager() -> DockerCircuitBreakerManager:
    """Get the global Docker circuit breaker manager."""
    return _docker_circuit_manager


def docker_circuit_breaker(service_name: str, config: Optional[DockerCircuitConfig] = None):
    """Decorator for Docker operations with circuit breaker protection."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            manager = get_docker_circuit_manager()
            with manager.docker_operation(service_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Export public API
__all__ = [
    'DockerServiceStatus',
    'DockerCircuitConfig',
    'DockerServiceHealth',
    'DockerCircuitBreaker',
    'DockerCircuitBreakerManager',
    'get_docker_circuit_manager',
    'docker_circuit_breaker',
    'CircuitOpenException',  # Re-export for convenience
]