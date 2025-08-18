"""Service Locator Pattern for Dependency Injection - Modular Facade

This module provides backward compatibility while using the new modular architecture.
All functionality has been split into focused modules ≤300 lines with functions ≤8 lines.
"""

# Import all modular components for backward compatibility
from typing import Type, TypeVar
from .service_locator_core import (
    ServiceLocator, ServiceNotFoundError, CircularDependencyError
)
from .service_interfaces import (
    IAgentService, IThreadService, IMessageHandlerService,
    IMCPService, IWebSocketService, IMCPClientService
)
from .service_registration import register_core_services
from .service_decorators import inject

T = TypeVar("T")

# Global service locator instance
service_locator = ServiceLocator()


def get_service(service_type: Type[T]) -> T:
    """Convenience function to get a service."""
    return service_locator.get(service_type)


def register_services() -> None:
    """Register all core services with proper dependency injection."""
    register_core_services(service_locator)


# Re-export all classes and functions for backward compatibility
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