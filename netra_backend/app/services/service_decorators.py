"""Dependency injection decorators.

Provides decorators for automatic service injection.
Follows 450-line limit with 25-line function limit.
"""

import asyncio
from typing import Type, Callable, TypeVar
from netra_backend.app.services.service_locator_core import ServiceLocator

T = TypeVar("T")


def _get_injected_services(service_locator: ServiceLocator, service_types: tuple) -> list:
    """Get list of service instances for injection."""
    return [service_locator.get(service_type) for service_type in service_types]


def _create_sync_wrapper(service_locator: ServiceLocator, func: Callable, service_types: tuple) -> Callable:
    """Create wrapper for synchronous functions."""
    def wrapper(*args, **kwargs):
        services = _get_injected_services(service_locator, service_types)
        return func(*services, *args, **kwargs)
    return wrapper


def _create_async_wrapper(service_locator: ServiceLocator, func: Callable, service_types: tuple) -> Callable:
    """Create wrapper for asynchronous functions."""
    async def async_wrapper(*args, **kwargs):
        services = _get_injected_services(service_locator, service_types)
        return await func(*services, *args, **kwargs)
    return async_wrapper


def _select_wrapper(service_locator: ServiceLocator, func: Callable, service_types: tuple) -> Callable:
    """Select appropriate wrapper based on function type."""
    if asyncio.iscoroutinefunction(func):
        return _create_async_wrapper(service_locator, func, service_types)
    return _create_sync_wrapper(service_locator, func, service_types)


def create_inject_decorator(service_locator: ServiceLocator) -> Callable:
    """Create an inject decorator bound to a specific service locator."""
    def inject(*service_types: Type) -> Callable:
        """Decorator to inject services into a function or method."""
        def decorator(func: Callable) -> Callable:
            return _select_wrapper(service_locator, func, service_types)
        return decorator
    return inject


def inject_method(*service_types: Type) -> Callable:
    """Decorator to inject services into a method using global service locator."""
    def decorator(func: Callable) -> Callable:
        def wrapper(self, *args, **kwargs):
            # Get global service locator from the instance or create one
            service_locator = getattr(self, '_service_locator', ServiceLocator())
            services = _get_injected_services(service_locator, service_types)
            return func(self, *services, *args, **kwargs)
        return wrapper
    return decorator


def inject_async_method(*service_types: Type) -> Callable:
    """Decorator to inject services into an async method using global service locator."""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(self, *args, **kwargs):
            # Get global service locator from the instance or create one
            service_locator = getattr(self, '_service_locator', ServiceLocator())
            services = _get_injected_services(service_locator, service_types)
            return await func(self, *services, *args, **kwargs)
        return async_wrapper
    return decorator


def auto_inject(service_locator: ServiceLocator, service_type: Type[T]) -> Callable:
    """Decorator to automatically inject a single service type."""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                service = service_locator.get(service_type)
                return await func(service, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                service = service_locator.get(service_type)
                return func(service, *args, **kwargs)
            return sync_wrapper
    return decorator


def inject(*service_types: Type) -> Callable:
    """Global inject decorator using default service locator."""
    def decorator(func: Callable) -> Callable:
        service_locator = ServiceLocator()
        return _select_wrapper(service_locator, func, service_types)
    return decorator