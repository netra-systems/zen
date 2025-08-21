"""Service Container for Dependency Injection

Manages service lifecycle and dependencies.
"""

from typing import Dict, Any, Type, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import inspect
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class ServiceLifetime(Enum):
    """Service lifetime scopes"""
    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"

@dataclass
class ServiceDescriptor:
    """Describes a registered service"""
    service_type: Type
    implementation: Optional[Type] = None
    factory: Optional[Callable] = None
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    instance: Optional[Any] = None
    dependencies: Dict[str, Type] = field(default_factory=dict)

class ServiceContainer:
    """IoC container for dependency injection"""
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._scoped_instances: Dict[Type, Any] = {}
    
    def register(self,
                service_type: Type,
                implementation: Optional[Type] = None,
                factory: Optional[Callable] = None,
                lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> None:
        """Register a service"""
        implementation = self._resolve_implementation(implementation, factory, service_type)
        descriptor = self._create_service_descriptor(service_type, implementation, factory, lifetime)
        self._finalize_service_registration(service_type, descriptor)

    def _resolve_implementation(self, implementation: Optional[Type], factory: Optional[Callable], service_type: Type) -> Optional[Type]:
        """Resolve implementation type if not provided."""
        if not implementation and not factory:
            return service_type
        return implementation

    def _create_service_descriptor(self, service_type: Type, implementation: Optional[Type], factory: Optional[Callable], lifetime: ServiceLifetime) -> ServiceDescriptor:
        """Create service descriptor with dependencies."""
        descriptor = ServiceDescriptor(
            service_type=service_type, implementation=implementation,
            factory=factory, lifetime=lifetime
        )
        if implementation:
            descriptor.dependencies = self._extract_dependencies(implementation)
        return descriptor

    def _finalize_service_registration(self, service_type: Type, descriptor: ServiceDescriptor) -> None:
        """Complete service registration and log."""
        self._services[service_type] = descriptor
        logger.info(f"Registered service: {service_type.__name__} with lifetime {descriptor.lifetime.value}")
    
    def resolve(self, service_type: Type) -> Any:
        """Resolve a service instance"""
        if service_type not in self._services:
            raise ValueError(f"Service {service_type.__name__} not registered")
        descriptor = self._services[service_type]
        return self._resolve_by_lifetime(service_type, descriptor)

    def _resolve_by_lifetime(self, service_type: Type, descriptor: ServiceDescriptor) -> Any:
        """Resolve service instance based on lifetime strategy."""
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return self._resolve_singleton(descriptor)
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            return self._resolve_scoped(service_type, descriptor)
        else:  # TRANSIENT
            return self._create_instance(descriptor)

    def _resolve_singleton(self, descriptor: ServiceDescriptor) -> Any:
        """Resolve singleton service instance."""
        if not descriptor.instance:
            descriptor.instance = self._create_instance(descriptor)
        return descriptor.instance

    def _resolve_scoped(self, service_type: Type, descriptor: ServiceDescriptor) -> Any:
        """Resolve scoped service instance."""
        if service_type not in self._scoped_instances:
            self._scoped_instances[service_type] = self._create_instance(descriptor)
        return self._scoped_instances[service_type]
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a service instance"""
        if descriptor.factory:
            return descriptor.factory()
        if descriptor.implementation:
            dependencies = self._resolve_dependencies(descriptor.dependencies)
            return descriptor.implementation(**dependencies)
        raise ValueError(f"Cannot create instance for {descriptor.service_type.__name__}")

    def _resolve_dependencies(self, dependencies: Dict[str, Type]) -> Dict[str, Any]:
        """Resolve all dependencies for service creation."""
        resolved_deps = {}
        for param_name, param_type in dependencies.items():
            if param_type in self._services:
                resolved_deps[param_name] = self.resolve(param_type)
        return resolved_deps
    
    def _extract_dependencies(self, implementation: Type) -> Dict[str, Type]:
        """Extract constructor dependencies"""
        dependencies = {}
        if hasattr(implementation, "__init__"):
            sig = inspect.signature(implementation.__init__)
            dependencies = self._process_signature_parameters(sig)
        return dependencies

    def _process_signature_parameters(self, sig) -> Dict[str, Type]:
        """Process signature parameters to extract type annotations."""
        dependencies = {}
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            if param.annotation != inspect.Parameter.empty:
                dependencies[param_name] = param.annotation
        return dependencies
    
    def clear_scoped(self) -> None:
        """Clear scoped instances"""
        self._scoped_instances.clear()
        logger.debug("Cleared scoped service instances")
    
    def get_all(self, service_type: Type) -> list:
        """Get all implementations of a service type"""
        instances = []
        for registered_type, descriptor in self._services.items():
            if issubclass(registered_type, service_type):
                instances.append(self.resolve(registered_type))
        return instances

container = ServiceContainer()