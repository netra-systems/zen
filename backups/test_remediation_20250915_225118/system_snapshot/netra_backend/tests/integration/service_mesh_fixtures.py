"""
Service Mesh Test Fixtures: Fixtures for service mesh integration testing.

This module provides fixtures and utilities for testing service mesh
functionality including service discovery, routing, and load balancing.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure (supports all tiers)
- Business Goal: 99.9% service mesh reliability, zero routing failures
- Value Impact: Reliable service communication enables microservice architecture
- Revenue Impact: Prevents service mesh failures that could cause $100K+ outages
"""

import pytest
from typing import Any, Dict, List, Optional, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock, patch
from contextlib import asynccontextmanager

from netra_backend.app.services.mesh.service_discovery import ServiceDiscovery as ServiceRegistry
from netra_backend.app.services.mesh.service_mesh import ServiceMesh


class MockService:
    """Mock service for service mesh testing."""
    
    def __init__(self, service_id: str, service_name: str, host: str, port: int):
        self.service_id = service_id
        self.service_name = service_name
        self.host = host
        self.port = port
        self.healthy = True
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert service to dictionary representation."""
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "host": self.host,
            "port": self.port,
            "healthy": self.healthy,
            "metadata": self.metadata
        }


class MockServiceRegistry:
    """Mock service registry for testing."""
    
    def __init__(self):
        self.services: Dict[str, List[MockService]] = {}
        self._health_checks: Dict[str, bool] = {}
    
    async def register_service(self, service: MockService) -> bool:
        """Register a service in the mock registry."""
        if service.service_name not in self.services:
            self.services[service.service_name] = []
        
        # Remove existing service with same ID
        self.services[service.service_name] = [
            s for s in self.services[service.service_name]
            if s.service_id != service.service_id
        ]
        
        self.services[service.service_name].append(service)
        self._health_checks[service.service_id] = service.healthy
        return True
    
    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service from the mock registry."""
        for service_name, service_list in self.services.items():
            self.services[service_name] = [
                s for s in service_list if s.service_id != service_id
            ]
        
        self._health_checks.pop(service_id, None)
        return True
    
    async def discover_services(self, service_name: str) -> List[Dict[str, Any]]:
        """Discover services by name."""
        services = self.services.get(service_name, [])
        return [s.to_dict() for s in services if s.healthy]
    
    async def health_check(self, service_id: str) -> bool:
        """Check health of a specific service."""
        return self._health_checks.get(service_id, False)
    
    async def update_service_health(self, service_id: str, healthy: bool) -> None:
        """Update service health status."""
        self._health_checks[service_id] = healthy
        
        # Update service object health
        for service_list in self.services.values():
            for service in service_list:
                if service.service_id == service_id:
                    service.healthy = healthy
    
    def get_all_services(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all registered services."""
        return {
            name: [s.to_dict() for s in services]
            for name, services in self.services.items()
        }


class MockCircuitBreaker:
    """Mock circuit breaker for testing."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = None
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            # Check if we should try half-open
            import time
            if (self.last_failure_time and 
                time.time() - self.last_failure_time > self.recovery_timeout):
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs) if callable(func) else func
            
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            
            return result
        
        except Exception as e:
            self.failure_count += 1
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                import time
                self.last_failure_time = time.time()
            
            raise e
    
    def get_state(self) -> str:
        """Get current circuit breaker state."""
        return self.state
    
    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = None


class MockLoadBalancer:
    """Mock load balancer for testing."""
    
    def __init__(self, strategy: str = "round_robin"):
        self.strategy = strategy
        self.current_index = 0
        self.service_weights: Dict[str, int] = {}
    
    async def select_service(self, services: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select a service based on load balancing strategy."""
        if not services:
            return None
        
        if self.strategy == "round_robin":
            service = services[self.current_index % len(services)]
            self.current_index += 1
            return service
        
        elif self.strategy == "random":
            import random
            return random.choice(services)
        
        elif self.strategy == "weighted":
            # Simple weighted selection
            total_weight = sum(self.service_weights.get(s["service_id"], 1) for s in services)
            import random
            random_weight = random.randint(1, total_weight)
            
            current_weight = 0
            for service in services:
                weight = self.service_weights.get(service["service_id"], 1)
                current_weight += weight
                if current_weight >= random_weight:
                    return service
        
        return services[0]  # Fallback
    
    def set_service_weight(self, service_id: str, weight: int) -> None:
        """Set weight for a service in weighted load balancing."""
        self.service_weights[service_id] = weight


# Pytest fixtures
@pytest.fixture
def mock_service_registry():
    """Provide a mock service registry."""
    return MockServiceRegistry()


@pytest.fixture
def mock_circuit_breaker():
    """Provide a mock circuit breaker."""
    return MockCircuitBreaker()


@pytest.fixture
def mock_load_balancer():
    """Provide a mock load balancer."""
    return MockLoadBalancer()


@pytest.fixture
def sample_services():
    """Provide sample services for testing."""
    return [
        MockService("auth-1", "auth-service", "localhost", 8001),
        MockService("auth-2", "auth-service", "localhost", 8002),
        MockService("api-1", "api-gateway", "localhost", 8080),
        MockService("api-2", "api-gateway", "localhost", 8081),
        MockService("db-1", "database", "localhost", 5432)
    ]


@pytest.fixture
async def populated_service_registry(mock_service_registry, sample_services):
    """Provide a service registry populated with sample services."""
    for service in sample_services:
        await mock_service_registry.register_service(service)
    yield mock_service_registry


@pytest.fixture
def service_mesh_config():
    """Provide service mesh configuration for testing."""
    return {
        "discovery": {
            "enabled": True,
            "heartbeat_interval": 30,
            "health_check_timeout": 10
        },
        "circuit_breaker": {
            "enabled": True,
            "failure_threshold": 5,
            "recovery_timeout": 60
        },
        "load_balancer": {
            "strategy": "round_robin",
            "health_check_enabled": True
        },
        "retry": {
            "max_attempts": 3,
            "backoff_factor": 2,
            "max_delay": 30
        }
    }


@asynccontextmanager
async def service_mesh_test_context():
    """Async context manager for service mesh testing."""
    with patch('netra_backend.app.services.mesh.service_discovery.ServiceRegistry') as mock_registry_class:
        with patch('netra_backend.app.services.mesh.service_mesh.ServiceMesh') as mock_mesh_class:
            # Create mock instances
            mock_registry = MockServiceRegistry()
            mock_mesh = MagicMock()
            
            # Setup mock classes to return our instances
            mock_registry_class.return_value = mock_registry
            mock_mesh_class.return_value = mock_mesh
            
            # Setup mock mesh methods
            mock_mesh.register_service = AsyncMock()
            mock_mesh.discover_service = AsyncMock()
            mock_mesh.call_service = AsyncMock()
            mock_mesh.health_check = AsyncMock()
            
            yield {
                "registry": mock_registry,
                "mesh": mock_mesh,
                "registry_class": mock_registry_class,
                "mesh_class": mock_mesh_class
            }


class ServiceMeshTestScenarios:
    """Predefined service mesh test scenarios."""
    
    @staticmethod
    def service_registration_and_discovery():
        """Scenario: Service registers and is discovered by other services."""
        return {
            "scenario": "service_registration_and_discovery",
            "services": [
                MockService("user-service-1", "user-service", "10.0.0.1", 8080),
                MockService("auth-service-1", "auth-service", "10.0.0.2", 8080)
            ],
            "expected_flow": [
                "register_user_service",
                "register_auth_service", 
                "discover_user_service_from_auth",
                "verify_service_metadata"
            ]
        }
    
    @staticmethod
    def service_failure_and_circuit_breaker():
        """Scenario: Service fails and circuit breaker activates."""
        return {
            "scenario": "service_failure_and_circuit_breaker",
            "services": [
                MockService("flaky-service-1", "flaky-service", "10.0.0.3", 8080)
            ],
            "failure_config": {
                "failure_threshold": 3,
                "recovery_timeout": 10
            },
            "expected_flow": [
                "register_flaky_service",
                "simulate_service_failures",
                "circuit_breaker_opens",
                "calls_rejected",
                "recovery_timeout_expires",
                "circuit_breaker_half_opens",
                "service_recovery_detected",
                "circuit_breaker_closes"
            ]
        }
    
    @staticmethod
    def load_balancing_across_instances():
        """Scenario: Load balancing requests across multiple service instances."""
        return {
            "scenario": "load_balancing_across_instances", 
            "services": [
                MockService("api-1", "api-service", "10.0.0.10", 8080),
                MockService("api-2", "api-service", "10.0.0.11", 8080),
                MockService("api-3", "api-service", "10.0.0.12", 8080)
            ],
            "load_balancer_config": {
                "strategy": "round_robin"
            },
            "expected_flow": [
                "register_multiple_api_instances",
                "discover_api_services",
                "distribute_requests_round_robin",
                "verify_even_distribution"
            ]
        }
    
    @staticmethod
    def service_health_monitoring():
        """Scenario: Continuous health monitoring and unhealthy service removal."""
        return {
            "scenario": "service_health_monitoring",
            "services": [
                MockService("healthy-service", "test-service", "10.0.0.20", 8080),
                MockService("unhealthy-service", "test-service", "10.0.0.21", 8080)
            ],
            "health_config": {
                "check_interval": 5,
                "failure_threshold": 2
            },
            "expected_flow": [
                "register_healthy_and_unhealthy_services",
                "start_health_monitoring",
                "detect_unhealthy_service", 
                "remove_unhealthy_from_discovery",
                "continue_routing_to_healthy_service"
            ]
        }


# Utility functions for service mesh testing
def create_test_service_mesh_setup():
    """Create a complete service mesh test setup."""
    registry = MockServiceRegistry()
    circuit_breaker = MockCircuitBreaker()
    load_balancer = MockLoadBalancer()
    
    return {
        "registry": registry,
        "circuit_breaker": circuit_breaker,
        "load_balancer": load_balancer
    }


async def simulate_service_failure(registry: MockServiceRegistry, service_id: str, duration: int = 10):
    """Simulate service failure for testing."""
    await registry.update_service_health(service_id, False)
    
    import asyncio
    await asyncio.sleep(duration)
    
    await registry.update_service_health(service_id, True)


def assert_service_mesh_state(mesh_state: Dict[str, Any], expected_state: Dict[str, Any]):
    """Assert that service mesh state matches expectations."""
    for key, expected_value in expected_state.items():
        actual_value = mesh_state.get(key)
        assert actual_value == expected_value, f"Expected {key}={expected_value}, got {actual_value}"


# Export key components
__all__ = [
    "MockService",
    "MockServiceRegistry", 
    "MockCircuitBreaker",
    "MockLoadBalancer",
    "service_mesh_test_context",
    "ServiceMeshTestScenarios",
    "create_test_service_mesh_setup",
    "simulate_service_failure",
    "assert_service_mesh_state"
]