"""
Service Dependency Decorators for E2E Tests

Provides decorators to specify exactly which services are needed for each E2E test,
allowing for more granular test execution and better resource management.

Usage:
    @requires_services(["auth", "backend"], docker=False)
    @requires_live_services(["database", "redis"])
    @pytest.mark.e2e
    def test_auth_flow():
        pass
"""

import functools
import logging
import os
from enum import Enum
from typing import List, Optional, Set, Dict, Any, Callable
from dataclasses import dataclass

import pytest

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Available service types in the Netra Apex platform."""
    AUTH = "auth"
    BACKEND = "backend" 
    FRONTEND = "frontend"
    DATABASE = "database"
    REDIS = "redis"
    WEBSOCKET = "websocket"
    LLM = "llm"
    CLICKHOUSE = "clickhouse"


class ExecutionMode(Enum):
    """How services should be executed."""
    DOCKER = "docker"          # Services must run in Docker containers
    LOCAL = "local"            # Services can run as individual processes
    EITHER = "either"          # Can run in either mode
    MOCK = "mock"             # Can use mocked services (not recommended for E2E)


@dataclass
class ServiceRequirement:
    """Specification for a required service."""
    service: ServiceType
    mode: ExecutionMode = ExecutionMode.EITHER
    version: Optional[str] = None
    health_check: bool = True
    timeout: int = 30


@dataclass 
class TestServiceConfig:
    """Configuration for test service dependencies."""
    required_services: List[ServiceRequirement]
    optional_services: List[ServiceRequirement] 
    execution_mode: ExecutionMode
    setup_timeout: int = 60
    teardown_timeout: int = 30


class ServiceDependencyChecker:
    """Checks if required services are available and healthy."""
    
    def __init__(self):
        self.health_checks = {
            ServiceType.AUTH: self._check_auth_service,
            ServiceType.BACKEND: self._check_backend_service,
            ServiceType.DATABASE: self._check_database_service,
            ServiceType.REDIS: self._check_redis_service,
            ServiceType.WEBSOCKET: self._check_websocket_service,
            ServiceType.LLM: self._check_llm_service,
            ServiceType.CLICKHOUSE: self._check_clickhouse_service,
        }
    
    def check_services(self, requirements: List[ServiceRequirement]) -> Dict[ServiceType, bool]:
        """Check availability of required services."""
        results = {}
        
        for req in requirements:
            if req.health_check:
                try:
                    is_healthy = self.health_checks.get(req.service, self._default_check)(req)
                    results[req.service] = is_healthy
                    
                    if not is_healthy:
                        logger.warning(f"Service {req.service.value} is not healthy")
                except Exception as e:
                    logger.error(f"Health check failed for {req.service.value}: {e}")
                    results[req.service] = False
            else:
                results[req.service] = True  # Skip health check
                
        return results
    
    def _check_auth_service(self, req: ServiceRequirement) -> bool:
        """Check auth service health."""
        # Implementation would check auth service endpoint
        return True  # Placeholder
    
    def _check_backend_service(self, req: ServiceRequirement) -> bool:
        """Check backend service health."""
        # Implementation would check backend health endpoint
        return True  # Placeholder
    
    def _check_database_service(self, req: ServiceRequirement) -> bool:
        """Check database connectivity."""
        # Implementation would test database connection
        return True  # Placeholder
    
    def _check_redis_service(self, req: ServiceRequirement) -> bool:
        """Check Redis connectivity."""
        # Implementation would test Redis connection
        return True  # Placeholder
    
    def _check_websocket_service(self, req: ServiceRequirement) -> bool:
        """Check WebSocket service."""
        # Implementation would test WebSocket connection
        return True  # Placeholder
    
    def _check_llm_service(self, req: ServiceRequirement) -> bool:
        """Check LLM service availability."""
        # Implementation would check LLM endpoint
        return True  # Placeholder
    
    def _check_clickhouse_service(self, req: ServiceRequirement) -> bool:
        """Check ClickHouse service."""
        # Implementation would test ClickHouse connection
        return True  # Placeholder
    
    def _default_check(self, req: ServiceRequirement) -> bool:
        """Default health check for unknown services."""
        logger.warning(f"No health check implemented for {req.service.value}")
        return True


def requires_services(
    services: List[str], 
    mode: str = "either",
    docker: Optional[bool] = None,
    timeout: int = 30,
    skip_if_unavailable: bool = True
) -> Callable:
    """
    Decorator to specify required services for a test.
    
    Args:
        services: List of service names (e.g., ["auth", "backend"])
        mode: Execution mode - "docker", "local", "either", "mock"  
        docker: Legacy parameter for backward compatibility
        timeout: Timeout for service health checks
        skip_if_unavailable: Skip test if services are unavailable
        
    Example:
        @requires_services(["auth", "backend"], mode="local")
        @requires_services(["database", "redis"], mode="docker")
        def test_auth_flow():
            pass
    """
    
    # Handle legacy docker parameter
    if docker is not None:
        mode = "docker" if docker else "local"
    
    # Convert string services to ServiceRequirement objects
    requirements = []
    for service_name in services:
        try:
            service_type = ServiceType(service_name.lower())
            execution_mode = ExecutionMode(mode.lower())
            req = ServiceRequirement(
                service=service_type,
                mode=execution_mode,
                timeout=timeout
            )
            requirements.append(req)
        except ValueError as e:
            logger.error(f"Invalid service or mode: {e}")
            raise
    
    def decorator(func):
        # Add service requirements as metadata
        func._service_requirements = requirements
        func._service_mode = ExecutionMode(mode.lower())
        func._skip_if_unavailable = skip_if_unavailable
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check service availability before running test
            if skip_if_unavailable:
                checker = ServiceDependencyChecker()
                health_results = checker.check_services(requirements)
                
                failed_services = [
                    req.service.value for req, healthy in 
                    zip(requirements, health_results.values()) 
                    if not healthy
                ]
                
                if failed_services:
                    pytest.skip(f"Required services unavailable: {failed_services}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def requires_live_services(services: List[str], timeout: int = 30) -> Callable:
    """
    Decorator for tests that require live (not mocked) services.
    
    This is a shorthand for @requires_services with mode="either" and 
    health_check=True, emphasizing that real services are required.
    """
    return requires_services(services, mode="either", timeout=timeout)


def requires_docker_services(services: List[str], timeout: int = 60) -> Callable:
    """
    Decorator for tests that specifically require Docker-based services.
    
    Use this for tests that need the full Docker Compose environment.
    """
    return requires_services(services, mode="docker", timeout=timeout)


def requires_local_services(services: List[str], timeout: int = 30) -> Callable:
    """
    Decorator for tests that can use local service processes.
    
    Use this for faster tests that don't need full Docker isolation.
    """
    return requires_services(services, mode="local", timeout=timeout)


def get_test_service_requirements(test_func) -> Optional[List[ServiceRequirement]]:
    """Extract service requirements from a test function."""
    return getattr(test_func, '_service_requirements', None)


def get_test_execution_mode(test_func) -> Optional[ExecutionMode]:
    """Extract execution mode from a test function."""
    return getattr(test_func, '_service_mode', None)


def should_skip_if_unavailable(test_func) -> bool:
    """Check if test should be skipped when services are unavailable."""
    return getattr(test_func, '_skip_if_unavailable', True)


class ServiceDependencyFilter:
    """Filter tests based on available services."""
    
    def __init__(self, available_services: Set[str], execution_mode: str = "either"):
        self.available_services = {ServiceType(s.lower()) for s in available_services}
        self.execution_mode = ExecutionMode(execution_mode.lower())
        self.checker = ServiceDependencyChecker()
    
    def should_run_test(self, test_func) -> bool:
        """Determine if a test should run based on service availability."""
        requirements = get_test_service_requirements(test_func)
        if not requirements:
            return True  # No requirements, can run
        
        test_mode = get_test_execution_mode(test_func)
        
        # Check mode compatibility
        if test_mode != ExecutionMode.EITHER and test_mode != self.execution_mode:
            return False
        
        # Check service availability
        health_results = self.checker.check_services(requirements)
        required_available = all(health_results.values())
        
        if not required_available and should_skip_if_unavailable(test_func):
            return False
            
        return True


# Pytest plugin integration
def pytest_configure(config):
    """Register custom markers for service dependencies."""
    config.addinivalue_line(
        "markers", 
        "requires_auth: Test requires Auth service"
    )
    config.addinivalue_line(
        "markers", 
        "requires_backend: Test requires Backend service" 
    )
    config.addinivalue_line(
        "markers",
        "requires_database: Test requires Database service"
    )
    config.addinivalue_line(
        "markers",
        "requires_redis: Test requires Redis service"
    )
    config.addinivalue_line(
        "markers",
        "requires_docker: Test requires Docker environment"
    )
    config.addinivalue_line(
        "markers",
        "requires_live: Test requires live (non-mocked) services"
    )


def pytest_collection_modifyitems(config, items):
    """Filter tests based on service availability if configured."""
    available_services_str = config.getoption("--available-services", None)
    execution_mode = config.getoption("--execution-mode", "either")
    
    if available_services_str:
        available_services = set(available_services_str.split(","))
        service_filter = ServiceDependencyFilter(available_services, execution_mode)
        
        filtered_items = []
        for item in items:
            if service_filter.should_run_test(item.function):
                filtered_items.append(item)
            else:
                logger.info(f"Skipping {item.name} - service requirements not met")
        
        items[:] = filtered_items


def pytest_addoption(parser):
    """Add command line options for service dependency filtering."""
    parser.addoption(
        "--available-services",
        action="store",
        default=None,
        help="Comma-separated list of available services"
    )
    parser.addoption(
        "--execution-mode", 
        action="store",
        default="either",
        choices=["docker", "local", "either"],
        help="Service execution mode"
    )