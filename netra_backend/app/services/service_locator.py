"""Service Locator Pattern for Dependency Injection - Modular Facade

This module provides backward compatibility while using the new modular architecture.
All functionality has been split into focused modules  <= 300 lines with functions  <= 8 lines.
"""

# Import all modular components for backward compatibility
from typing import Type, TypeVar

from netra_backend.app.services.service_decorators import inject
from netra_backend.app.services.service_interfaces import (
    IAgentService,
    IMCPClientService,
    IMCPService,
    IMessageHandlerService,
    IThreadService,
    IWebSocketService,
)
from netra_backend.app.services.service_locator_core import (
    CircularDependencyError,
    ServiceLocator,
    ServiceNotFoundError,
)
from netra_backend.app.services.service_registration import register_core_services

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