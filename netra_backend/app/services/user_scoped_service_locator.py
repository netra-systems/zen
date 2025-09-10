"""
User-Scoped ServiceLocator Factory - Complete User Isolation for Service Dependencies

Business Value Justification (BVJ):
- Segment: Platform/Core Infrastructure  
- Business Goal: $500K+ ARR Protection through Service Component Isolation
- Value Impact: Prevents singleton-based service sharing that causes user session bleeding
- Strategic Impact: Enables secure multi-user service dependency injection with guaranteed isolation

This module provides the foundational factory pattern to replace the ServiceLocator singleton
with per-user instances, preventing cross-user service contamination that blocks business value delivery.

CRITICAL BUSINESS CONTEXT:
- Each user execution must get completely isolated service instances
- Shared service instances between users cause data leakage and security breaches  
- Factory patterns ensure each user gets fresh, isolated service component instances
- This factory enables ServiceLocator isolation critical for agent and tool execution

SINGLETON VIOLATION RESOLUTION:
This factory directly addresses the ServiceLocator singleton violations identified in:
- ServiceNotFoundError cross-user contamination
- Shared service registry causing session bleeding  
- Circular dependency detection failures in multi-user scenarios
- Service instance sharing blocking proper request isolation

ARCHITECTURE COMPLIANCE:
@compliance CLAUDE.md - Factory patterns for user-scoped components (Section 2.1)
@compliance SPEC/core.xml - Single Source of Truth service management  
@compliance SPEC/type_safety.xml - Strongly typed service locator interfaces

Migration Phase: Phase 1 - Foundation Implementation (Parallel to Singleton)
GitHub Issue: https://github.com/netra-systems/netra-apex/issues/232
"""

import threading
import weakref
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.user_execution_context import UserExecutionContext
from netra_backend.app.services.service_locator_core import (
    ServiceNotFoundError,
    CircularDependencyError
)
from netra_backend.app.services.service_interfaces import (
    IAgentService,
    IMCPClientService,
    IMCPService,
    IMessageHandlerService,
    IThreadService,
    IWebSocketService,
)

logger = central_logger.get_logger(__name__)
T = TypeVar("T")


@dataclass
class UserServiceRegistry:
    """
    Per-user service registry with complete isolation.
    
    This registry maintains all services for a single user execution context,
    ensuring complete isolation from other users' service instances.
    """
    user_context: UserExecutionContext
    services: Dict[Type, Any] = field(default_factory=dict)
    factories: Dict[Type, Callable] = field(default_factory=dict)
    singletons: Dict[Type, Any] = field(default_factory=dict)
    initializing: Set[Type] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = field(default=0)
    
    def __post_init__(self):
        """Initialize registry with user context validation."""
        if not isinstance(self.user_context, UserExecutionContext):
            raise ValueError("UserServiceRegistry requires valid UserExecutionContext")
        
        logger.debug(
            f"UserServiceRegistry created for user {self.user_context.user_id[:8]}... "
            f"(request: {self.user_context.request_id[:8]}...)"
        )
    
    def get_isolation_key(self) -> str:
        """Get unique isolation key for this user registry."""
        return self.user_context.get_scoped_key("service_registry")
    
    def is_expired(self, max_age_seconds: int = 3600) -> bool:
        """Check if registry has exceeded maximum age."""
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > max_age_seconds


class UserScopedServiceLocator:
    """
    User-scoped service locator providing complete isolation between user executions.
    
    This class replaces the singleton ServiceLocator pattern with per-user instances,
    ensuring that each user's service dependencies are completely isolated from other
    users, preventing session bleeding and data contamination.
    
    Key Features:
    - Complete user isolation through UserExecutionContext
    - Per-user service registries with independent lifecycles
    - Dependency injection with circular dependency detection
    - Memory management with automatic cleanup
    - Thread-safe operations with user-scoped locking
    - Business value protection through isolation guarantees
    """
    
    def __init__(self, user_context: UserExecutionContext):
        """
        Initialize user-scoped service locator.
        
        Args:
            user_context: UserExecutionContext for complete isolation
            
        Raises:
            ValueError: If user_context is invalid
        """
        if not isinstance(user_context, UserExecutionContext):
            raise ValueError("UserScopedServiceLocator requires valid UserExecutionContext")
        
        self.user_context = user_context
        self.registry = UserServiceRegistry(user_context)
        self._lock = threading.RLock()  # Reentrant lock for user operations
        
        # Track component lifecycle for cleanup
        self._cleanup_callbacks: list = []
        
        logger.info(
            f"UserScopedServiceLocator initialized for user {user_context.user_id[:8]}... "
            f"(isolation_key: {self.registry.get_isolation_key()})"
        )
    
    def _validate_service_registration(self, 
                                     service_type: Type[T], 
                                     implementation: Optional[T], 
                                     factory: Optional[Callable[[], T]]) -> None:
        """Validate service registration parameters."""
        if not service_type:
            raise ValueError("service_type cannot be None")
        
        if implementation and factory:
            raise ValueError("Cannot provide both implementation and factory")
        
        if not implementation and not factory:
            raise ValueError("Must provide either implementation or factory")
        
        # Validate implementation type
        if implementation and not isinstance(implementation, service_type):
            raise ValueError(
                f"Implementation must be instance of {service_type.__name__}, "
                f"got {type(implementation).__name__}"
            )
    
    def register(self,
                service_type: Type[T],
                implementation: Optional[T] = None,
                factory: Optional[Callable[[], T]] = None,
                singleton: bool = True) -> None:
        """
        Register a service implementation or factory for this user.
        
        Args:
            service_type: Service interface type
            implementation: Service implementation instance
            factory: Factory function to create service
            singleton: Whether to cache the instance (per-user singleton)
            
        Raises:
            ValueError: If registration parameters are invalid
        """
        with self._lock:
            self._validate_service_registration(service_type, implementation, factory)
            
            if implementation:
                self.registry.services[service_type] = implementation
                if singleton:
                    self.registry.singletons[service_type] = implementation
            else:
                self.registry.factories[service_type] = factory
            
            logger.debug(
                f"Service registered for user {self.user_context.user_id[:8]}...: "
                f"{service_type.__name__} (singleton: {singleton})"
            )
    
    def _check_circular_dependency(self, service_type: Type[T]) -> None:
        """Check for circular dependencies in user-scoped context."""
        if service_type in self.registry.initializing:
            raise CircularDependencyError(
                f"Circular dependency detected for {service_type.__name__} "
                f"in user context {self.user_context.user_id[:8]}..."
            )
    
    def _get_cached_service(self, service_type: Type[T]) -> Optional[T]:
        """Get cached service instance if available."""
        # Check direct services first
        if service_type in self.registry.services:
            return self.registry.services[service_type]
        
        # Check user-scoped singletons
        if service_type in self.registry.singletons:
            return self.registry.singletons[service_type]
        
        return None
    
    def _execute_factory_with_tracking(self, service_type: Type[T]) -> T:
        """Execute factory with circular dependency tracking."""
        self.registry.initializing.add(service_type)
        try:
            factory = self.registry.factories[service_type]
            
            # Pass user context to factory if it accepts it
            try:
                # Check factory signature to see if it accepts user_context
                import inspect
                sig = inspect.signature(factory)
                if 'user_context' in sig.parameters:
                    instance = factory(user_context=self.user_context)
                else:
                    instance = factory()
            except TypeError:
                # Fallback to no-args factory
                instance = factory()
            
            # Cache instance as user-scoped singleton
            self._cache_factory_instance(service_type, instance)
            
            logger.debug(
                f"Factory-created service for user {self.user_context.user_id[:8]}...: "
                f"{service_type.__name__}"
            )
            
            return instance
            
        finally:
            self.registry.initializing.discard(service_type)
    
    def _cache_factory_instance(self, service_type: Type[T], instance: T) -> None:
        """Cache factory-created instance as user-scoped singleton."""
        if service_type not in self.registry.services:
            self.registry.singletons[service_type] = instance
    
    def _create_from_factory(self, service_type: Type[T]) -> Optional[T]:
        """Create service instance from factory if available."""
        if service_type not in self.registry.factories:
            return None
        
        return self._execute_factory_with_tracking(service_type)
    
    def get(self, service_type: Type[T]) -> T:
        """
        Get a service instance for this user.
        
        Args:
            service_type: Service interface type
            
        Returns:
            Service instance isolated to this user
            
        Raises:
            ServiceNotFoundError: If service is not registered for this user
            CircularDependencyError: If circular dependency is detected
        """
        with self._lock:
            self._check_circular_dependency(service_type)
            self.registry.access_count += 1
            
            # Try cached instances first
            cached = self._get_cached_service(service_type)
            if cached is not None:
                return cached
            
            # Try factory creation
            factory_instance = self._create_from_factory(service_type)
            if factory_instance is not None:
                return factory_instance
            
            # Service not found for this user
            raise ServiceNotFoundError(
                f"Service {service_type.__name__} is not registered for user "
                f"{self.user_context.user_id[:8]}... "
                f"(isolation_key: {self.registry.get_isolation_key()})"
            )
    
    def get_optional(self, service_type: Type[T]) -> Optional[T]:
        """
        Get a service instance if available, None otherwise.
        
        Args:
            service_type: Service interface type
            
        Returns:
            Service instance or None if not available
        """
        try:
            return self.get(service_type)
        except ServiceNotFoundError:
            return None
    
    def is_registered(self, service_type: Type) -> bool:
        """
        Check if a service is registered for this user.
        
        Args:
            service_type: Service interface type
            
        Returns:
            True if service is registered
        """
        with self._lock:
            return (
                service_type in self.registry.services or
                service_type in self.registry.factories
            )
    
    def clear(self) -> None:
        """Clear all registered services for this user."""
        with self._lock:
            # Execute cleanup callbacks before clearing
            for cleanup_fn in self._cleanup_callbacks:
                try:
                    cleanup_fn()
                except Exception as e:
                    logger.warning(f"Cleanup callback failed: {e}")
            
            self.registry.services.clear()
            self.registry.factories.clear()
            self.registry.singletons.clear()
            self.registry.initializing.clear()
            self._cleanup_callbacks.clear()
            
            logger.debug(
                f"Cleared all services for user {self.user_context.user_id[:8]}..."
            )
    
    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a cleanup callback for this user's services.
        
        Args:
            callback: Function to call during cleanup
        """
        self._cleanup_callbacks.append(callback)
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get statistics about this user's service registry.
        
        Returns:
            Dictionary with registry statistics
        """
        with self._lock:
            return {
                "user_id_prefix": self.user_context.user_id[:8] + "...",
                "isolation_key": self.registry.get_isolation_key(),
                "services_count": len(self.registry.services),
                "factories_count": len(self.registry.factories),
                "singletons_count": len(self.registry.singletons),
                "access_count": self.registry.access_count,
                "created_at": self.registry.created_at.isoformat(),
                "age_seconds": (datetime.now(timezone.utc) - self.registry.created_at).total_seconds(),
                "is_expired": self.registry.is_expired(),
                "initializing_count": len(self.registry.initializing)
            }


class ServiceLocatorFactory:
    """
    Factory for creating user-scoped ServiceLocator instances.
    
    This factory manages the lifecycle of UserScopedServiceLocator instances,
    providing automatic cleanup and memory management to prevent resource leaks.
    """
    
    def __init__(self):
        """Initialize factory with user registry tracking."""
        self._user_locators: Dict[str, weakref.ReferenceType] = {}
        self._lock = threading.RLock()
        
        logger.info("ServiceLocatorFactory initialized")
    
    def create_for_user(self, user_context: UserExecutionContext) -> UserScopedServiceLocator:
        """
        Create or get user-scoped service locator.
        
        Args:
            user_context: UserExecutionContext for isolation
            
        Returns:
            UserScopedServiceLocator for the user
        """
        with self._lock:
            isolation_key = user_context.get_scoped_key("service_locator")
            
            # Check if we already have a locator for this user context
            if isolation_key in self._user_locators:
                existing_ref = self._user_locators[isolation_key]
                existing_locator = existing_ref()
                
                if existing_locator is not None:
                    logger.debug(
                        f"Reusing existing ServiceLocator for user {user_context.user_id[:8]}..."
                    )
                    return existing_locator
                else:
                    # Clean up dead reference
                    del self._user_locators[isolation_key]
            
            # Create new user-scoped locator
            locator = UserScopedServiceLocator(user_context)
            
            # Register core services for this user
            self._register_core_services(locator)
            
            # Store weak reference for cleanup tracking
            self._user_locators[isolation_key] = weakref.ref(locator)
            
            logger.info(
                f"Created new UserScopedServiceLocator for user {user_context.user_id[:8]}... "
                f"(total active: {len(self._user_locators)})"
            )
            
            return locator
    
    def _register_core_services(self, locator: UserScopedServiceLocator) -> None:
        """
        Register core services for user-scoped locator.
        
        Args:
            locator: UserScopedServiceLocator to configure
        """
        try:
            # Import core service implementations
            from netra_backend.app.services.service_registration import register_core_services
            
            # Convert to singleton ServiceLocator interface for registration
            singleton_adapter = ServiceLocatorSingletonAdapter(locator)
            register_core_services(singleton_adapter)
            
            logger.debug(
                f"Core services registered for user {locator.user_context.user_id[:8]}..."
            )
            
        except Exception as e:
            logger.error(f"Failed to register core services: {e}")
            # Continue without core services - they can be registered individually
    
    def cleanup_expired_locators(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up expired user locators.
        
        Args:
            max_age_seconds: Maximum age before cleanup
            
        Returns:
            Number of locators cleaned up
        """
        with self._lock:
            expired_keys = []
            
            for isolation_key, locator_ref in self._user_locators.items():
                locator = locator_ref()
                
                if locator is None:
                    # Dead reference
                    expired_keys.append(isolation_key)
                elif locator.registry.is_expired(max_age_seconds):
                    # Expired locator
                    locator.clear()
                    expired_keys.append(isolation_key)
            
            # Clean up expired references
            for key in expired_keys:
                del self._user_locators[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired service locators")
            
            return len(expired_keys)
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """
        Get factory statistics.
        
        Returns:
            Dictionary with factory statistics
        """
        with self._lock:
            active_count = 0
            total_services = 0
            
            for locator_ref in self._user_locators.values():
                locator = locator_ref()
                if locator is not None:
                    active_count += 1
                    stats = locator.get_registry_stats()
                    total_services += stats["services_count"]
            
            return {
                "active_locators": active_count,
                "total_tracked": len(self._user_locators),
                "total_services": total_services,
                "dead_references": len(self._user_locators) - active_count
            }


class ServiceLocatorSingletonAdapter:
    """
    Adapter to make UserScopedServiceLocator compatible with singleton interface.
    
    This adapter allows existing service registration code to work with the new
    user-scoped locator during the migration period.
    """
    
    def __init__(self, user_scoped_locator: UserScopedServiceLocator):
        """Initialize adapter with user-scoped locator."""
        self.user_scoped_locator = user_scoped_locator
    
    def register(self, service_type: Type[T], implementation: Optional[T] = None,
                factory: Optional[Callable[[], T]] = None, singleton: bool = True) -> None:
        """Register service using user-scoped locator."""
        return self.user_scoped_locator.register(service_type, implementation, factory, singleton)
    
    def get(self, service_type: Type[T]) -> T:
        """Get service using user-scoped locator."""
        return self.user_scoped_locator.get(service_type)
    
    def get_optional(self, service_type: Type[T]) -> Optional[T]:
        """Get optional service using user-scoped locator."""
        return self.user_scoped_locator.get_optional(service_type)
    
    def is_registered(self, service_type: Type) -> bool:
        """Check registration using user-scoped locator."""
        return self.user_scoped_locator.is_registered(service_type)
    
    def clear(self) -> None:
        """Clear services using user-scoped locator."""
        return self.user_scoped_locator.clear()


# Global factory instance for creating user-scoped locators
_factory_instance: Optional[ServiceLocatorFactory] = None
_factory_lock = threading.RLock()


def get_service_locator_factory() -> ServiceLocatorFactory:
    """
    Get the global ServiceLocatorFactory instance.
    
    Returns:
        ServiceLocatorFactory instance
    """
    global _factory_instance
    
    with _factory_lock:
        if _factory_instance is None:
            _factory_instance = ServiceLocatorFactory()
        
        return _factory_instance


def create_user_service_locator(user_context: UserExecutionContext) -> UserScopedServiceLocator:
    """
    Create user-scoped service locator for the given context.
    
    Args:
        user_context: UserExecutionContext for isolation
        
    Returns:
        UserScopedServiceLocator instance
    """
    factory = get_service_locator_factory()
    return factory.create_for_user(user_context)


def get_user_service(service_type: Type[T], user_context: UserExecutionContext) -> T:
    """
    Convenience function to get a service for a specific user.
    
    Args:
        service_type: Service interface type
        user_context: UserExecutionContext for isolation
        
    Returns:
        Service instance isolated to the user
    """
    locator = create_user_service_locator(user_context)
    return locator.get(service_type)


# Backward Compatibility Bridge
def get_service_with_context(service_type: Type[T], 
                            user_context: Optional[UserExecutionContext] = None) -> T:
    """
    Backward compatibility function that routes to appropriate locator.
    
    If user_context is provided, uses user-scoped locator.
    Otherwise, falls back to singleton locator for backward compatibility.
    
    Args:
        service_type: Service interface type
        user_context: Optional UserExecutionContext for user-scoped access
        
    Returns:
        Service instance
    """
    if user_context is not None:
        return get_user_service(service_type, user_context)
    else:
        # Fallback to singleton for backward compatibility
        from netra_backend.app.services.service_locator import get_service
        logger.warning(
            f"Using singleton ServiceLocator for {service_type.__name__} - "
            "consider migrating to user-scoped access"
        )
        return get_service(service_type)


# SSOT Exports
__all__ = [
    # Core classes
    "UserScopedServiceLocator",
    "ServiceLocatorFactory", 
    "UserServiceRegistry",
    "ServiceLocatorSingletonAdapter",
    
    # Factory functions
    "get_service_locator_factory",
    "create_user_service_locator",
    "get_user_service",
    
    # Compatibility functions
    "get_service_with_context"
]