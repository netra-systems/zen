"""
Offline Integration Tests Package

This package contains integration tests that can run without external services
like Redis, PostgreSQL, or Docker containers. These tests focus on validating
integration between internal components using mocks and simulations.

Test Categories:
- Configuration Integration: Environment management, config loading, validation
- API Routing Integration: FastAPI routing, middleware, request processing  
- Service Initialization: Startup sequences, dependency injection, lifecycle
- Agent Factory Integration: Agent creation, registry, execution

Business Value:
- Enables immediate testing progress without infrastructure dependencies
- Validates core integration logic without external service complexities
- Provides fast feedback loop for integration testing during development
- Ensures integration patterns work correctly before adding real service complexity
"""

__version__ = "1.0.0"
__all__ = [
    "test_configuration_integration_offline",
    "test_api_routing_integration_offline", 
    "test_service_initialization_offline",
    "test_agent_factory_integration_offline"
]