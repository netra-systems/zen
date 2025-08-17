"""Core ServiceLocator implementation for dependency injection.

Provides the main ServiceLocator class and related exceptions.
Follows 300-line limit with 8-line function limit.
"""

from typing import Dict, Type, Any, Optional, TypeVar, Callable
import threading
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
T = TypeVar("T")


class ServiceNotFoundError(Exception):
    """Raised when a requested service is not registered."""
    pass


class CircularDependencyError(Exception):
    """Raised when a circular dependency is detected."""
    pass


class ServiceLocator:
    """Centralized service locator for dependency injection."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure singleton pattern with thread safety."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ServiceLocator, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize the service locator."""
        if not self._initialized:
            self._services: Dict[Type, Any] = {}
            self._factories: Dict[Type, Callable] = {}
            self._singletons: Dict[Type, Any] = {}
            self._initializing: set = set()
            self._initialized = True
    
    def _validate_registration_params(self, implementation: Optional[T], factory: Optional[Callable[[], T]]) -> None:
        """Validate registration parameters."""
        if implementation and factory:
            raise ValueError("Cannot provide both implementation and factory")
        if not implementation and not factory:
            raise ValueError("Must provide either implementation or factory")
    
    def _register_implementation(self, service_type: Type[T], implementation: T, singleton: bool) -> None:
        """Register a service implementation."""
        self._services[service_type] = implementation
        if singleton:
            self._singletons[service_type] = implementation
    
    def _register_factory(self, service_type: Type[T], factory: Callable[[], T]) -> None:
        """Register a service factory."""
        self._factories[service_type] = factory
    
    def register(
        self,
        service_type: Type[T],
        implementation: Optional[T] = None,
        factory: Optional[Callable[[], T]] = None,
        singleton: bool = True
    ) -> None:
        """Register a service implementation or factory."""
        self._validate_registration_params(implementation, factory)
        
        if implementation:
            self._register_implementation(service_type, implementation, singleton)
        else:
            self._register_factory(service_type, factory)
        
        logger.debug(f"Registered service: {service_type.__name__}")
    
    def _check_circular_dependency(self, service_type: Type[T]) -> None:
        """Check for circular dependencies."""
        if service_type in self._initializing:
            raise CircularDependencyError(
                f"Circular dependency detected for {service_type.__name__}"
            )
    
    def _get_cached_service(self, service_type: Type[T]) -> Optional[T]:
        """Get cached service instance if available."""
        if service_type in self._services:
            return self._services[service_type]
        if service_type in self._singletons:
            return self._singletons[service_type]
        return None
    
    def _execute_factory_with_tracking(self, service_type: Type[T]) -> T:
        """Execute factory with circular dependency tracking."""
        self._initializing.add(service_type)
        try:
            factory = self._factories[service_type]
            instance = factory()
            self._cache_factory_instance(service_type, instance)
            return instance
        finally:
            self._initializing.discard(service_type)
    
    def _cache_factory_instance(self, service_type: Type[T], instance: T) -> None:
        """Cache factory-created instance if not already cached."""
        if service_type not in self._services:
            self._singletons[service_type] = instance
    
    def _create_from_factory(self, service_type: Type[T]) -> Optional[T]:
        """Create service instance from factory if available."""
        if service_type not in self._factories:
            return None
        return self._execute_factory_with_tracking(service_type)
    
    def get(self, service_type: Type[T]) -> T:
        """Get a service instance."""
        self._check_circular_dependency(service_type)
        
        cached = self._get_cached_service(service_type)
        if cached is not None:
            return cached
        
        factory_instance = self._create_from_factory(service_type)
        if factory_instance is not None:
            return factory_instance
        
        raise ServiceNotFoundError(f"Service {service_type.__name__} is not registered")
    
    def get_optional(self, service_type: Type[T]) -> Optional[T]:
        """Get a service instance if available, None otherwise."""
        try:
            return self.get(service_type)
        except ServiceNotFoundError:
            return None
    
    def clear(self) -> None:
        """Clear all registered services (useful for testing)."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self._initializing.clear()
    
    def is_registered(self, service_type: Type) -> bool:
        """Check if a service is registered."""
        return (
            service_type in self._services or
            service_type in self._factories
        )
    
    def register_lazy(self, service_type: Type[T]) -> Callable[[T], None]:
        """Register a service lazily using a decorator."""
        def decorator(cls: Type[T]) -> Type[T]:
            self.register(service_type, factory=lambda: cls())
            return cls
        return decorator