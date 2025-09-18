from shared.isolated_environment import get_env
"""
env = get_env()
Centralized Service Endpoints Configuration for E2E Tests

Provides consistent service endpoint configuration that works with both
Docker Compose and local development environments.

BVJ:
- Segment: Platform/Internal  
- Business Goal: Ensure reliable test execution
- Value Impact: Prevents port mismatch test failures
- Strategic Impact: Enables consistent cross-environment testing
"""

from dataclasses import dataclass
from typing import Optional
from shared.isolated_environment import get_env

# Import dynamic port manager for environment-aware configuration
try:
    from tests.e2e.dynamic_port_manager import get_port_manager
except ImportError:
    get_port_manager = None


@dataclass
class ServiceEndpoints:
    """Centralized service endpoint configuration."""
    
    auth_service_url: str = "http://localhost:8081"  # Docker default
    backend_service_url: str = "http://localhost:8000" 
    frontend_service_url: str = "http://localhost:3000"
    websocket_url: str = "ws://localhost:8000/ws"
    redis_url: str = "redis://localhost:6379"
    postgres_url: str = "postgresql://postgres:netra@localhost:5432/netra_test"
    clickhouse_url: str = "clickhouse://localhost:8123/netra_test"


def get_service_endpoints(environment: str = "local") -> ServiceEndpoints:
    """
    Get service endpoints configuration for the specified environment.
    
    Args:
        environment: Target environment (local, docker, ci, staging)
        
    Returns:
        ServiceEndpoints: Configured endpoints for the environment
    """
    # Try to use dynamic port manager first
    if get_port_manager:
        try:
            port_mgr = get_port_manager()
            urls = port_mgr.get_service_urls()
            return ServiceEndpoints(
                auth_service_url=urls["auth"],
                backend_service_url=urls["backend"], 
                frontend_service_url=urls["frontend"],
                websocket_url=urls["websocket"],
                redis_url=urls["redis"],
                postgres_url=urls["postgres"],
                clickhouse_url=urls["clickhouse"]
            )
        except Exception:
            # Fall back to environment-based configuration
            pass
    
    # Environment-based configuration
    if environment.lower() in ["docker", "compose"]:
        return ServiceEndpoints(
            auth_service_url="http://localhost:8081",  # Docker auth port
            backend_service_url="http://localhost:8000",
            frontend_service_url="http://localhost:3000",
            websocket_url="ws://localhost:8000/ws"
        )
    elif environment.lower() in ["staging", "prod"]:
        return ServiceEndpoints(
            auth_service_url="https://auth.netra-apex.com",
            backend_service_url="https://staging.netra-apex.com", 
            frontend_service_url="https://staging.netra-apex.com",
            websocket_url="wss://staging.netra-apex.com/ws"
        )
    else:  # local development
        return ServiceEndpoints(
            auth_service_url=get_env().get("AUTH_SERVICE_URL", "http://localhost:8081"),
            backend_service_url=get_env().get("BACKEND_SERVICE_URL", "http://localhost:8000"),
            frontend_service_url=get_env().get("FRONTEND_SERVICE_URL", "http://localhost:3000"),
            websocket_url=get_env().get("WEBSOCKET_URL", "ws://localhost:8000/ws")
        )


def get_auth_service_url() -> str:
    """Get the auth service URL for the current environment."""
    return get_service_endpoints().auth_service_url


def get_backend_service_url() -> str:
    """Get the backend service URL for the current environment.""" 
    return get_service_endpoints().backend_service_url


def get_websocket_url() -> str:
    """Get the WebSocket URL for the current environment."""
    return get_service_endpoints().websocket_url


# Convenience instance for backward compatibility
DEFAULT_ENDPOINTS = get_service_endpoints()
