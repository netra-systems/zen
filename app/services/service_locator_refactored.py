"""Service Locator facade for dependency injection.

Provides backward compatibility while using modular architecture.
Follows 450-line limit with 25-line function limit.
"""

from typing import Type, TypeVar
from .service_locator_core import ServiceLocator, ServiceNotFoundError, CircularDependencyError
from .service_interfaces import (
    IAgentService, IThreadService, IMessageHandlerService,
    IMCPService, IWebSocketService, IMCPClientService
)
from .service_registration import register_core_services
from .service_decorators import create_inject_decorator

T = TypeVar("T")

# Global service locator instance
service_locator = ServiceLocator()

# Create inject decorator bound to global service locator
inject = create_inject_decorator(service_locator)


def get_service(service_type: Type[T]) -> T:
    """Convenience function to get a service."""
    return service_locator.get(service_type)


def register_services() -> None:
    """Register all core services with proper dependency injection."""
    register_core_services(service_locator)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "ServiceLocator",
    "service_locator",
    "ServiceNotFoundError",
    "CircularDependencyError",
    "IAgentService",
    "IThreadService",
    "IMessageHandlerService",
    "IMCPService",
    "IWebSocketService",
    "IMCPClientService",
    "register_core_services",
    "register_services",
    "get_service",
    "inject",
]