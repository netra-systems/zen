"""Service Container for Dependency Injection

Manages service lifecycle and dependencies.
"""

from typing import Dict, Any, Type, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import inspect
from app.logging_config import central_logger

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
        if not implementation and not factory:
            implementation = service_type
        
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            lifetime=lifetime
        )
        
        if implementation:
            descriptor.dependencies = self._extract_dependencies(implementation)
        
        self._services[service_type] = descriptor
        logger.info(f"Registered service: {service_type.__name__} with lifetime {lifetime.value}")
    
    def resolve(self, service_type: Type) -> Any:
        """Resolve a service instance"""
        if service_type not in self._services:
            raise ValueError(f"Service {service_type.__name__} not registered")
        
        descriptor = self._services[service_type]
        
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if not descriptor.instance:
                descriptor.instance = self._create_instance(descriptor)
            return descriptor.instance
        
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            if service_type not in self._scoped_instances:
                self._scoped_instances[service_type] = self._create_instance(descriptor)
            return self._scoped_instances[service_type]
        
        else:  # TRANSIENT
            return self._create_instance(descriptor)
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a service instance"""
        if descriptor.factory:
            return descriptor.factory()
        
        if descriptor.implementation:
            dependencies = {}
            for param_name, param_type in descriptor.dependencies.items():
                if param_type in self._services:
                    dependencies[param_name] = self.resolve(param_type)
            
            return descriptor.implementation(**dependencies)
        
        raise ValueError(f"Cannot create instance for {descriptor.service_type.__name__}")
    
    def _extract_dependencies(self, implementation: Type) -> Dict[str, Type]:
        """Extract constructor dependencies"""
        dependencies = {}
        
        if hasattr(implementation, "__init__"):
            sig = inspect.signature(implementation.__init__)
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