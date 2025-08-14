"""Service Locator Pattern for Dependency Injection.

This module provides a centralized service locator to break circular dependencies
and enable proper dependency injection throughout the application.
"""

from typing import Dict, Type, Any, Optional, TypeVar, Generic, Callable
from functools import lru_cache
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
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ServiceLocator, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._services: Dict[Type, Any] = {}
            self._factories: Dict[Type, Callable] = {}
            self._singletons: Dict[Type, Any] = {}
            self._initializing: set = set()
            self._initialized = True
    
    def register(
        self,
        service_type: Type[T],
        implementation: Optional[T] = None,
        factory: Optional[Callable[[], T]] = None,
        singleton: bool = True
    ) -> None:
        """Register a service implementation or factory.
        
        Args:
            service_type: The type/interface of the service
            implementation: An instance of the service (optional)
            factory: A factory function that creates the service (optional)
            singleton: Whether to cache the service instance
        """
        if implementation and factory:
            raise ValueError("Cannot provide both implementation and factory")
        
        if implementation:
            self._services[service_type] = implementation
            if singleton:
                self._singletons[service_type] = implementation
        elif factory:
            self._factories[service_type] = factory
        else:
            raise ValueError("Must provide either implementation or factory")
        
        logger.debug(f"Registered service: {service_type.__name__}")
    
    def get(self, service_type: Type[T]) -> T:
        """Get a service instance.
        
        Args:
            service_type: The type of service to retrieve
            
        Returns:
            The service instance
            
        Raises:
            ServiceNotFoundError: If the service is not registered
            CircularDependencyError: If a circular dependency is detected
        """
        # Check for circular dependencies
        if service_type in self._initializing:
            raise CircularDependencyError(
                f"Circular dependency detected for {service_type.__name__}"
            )
        
        # Check if we have a cached instance
        if service_type in self._services:
            return self._services[service_type]
        
        # Check if we have a singleton
        if service_type in self._singletons:
            return self._singletons[service_type]
        
        # Check if we have a factory
        if service_type in self._factories:
            try:
                self._initializing.add(service_type)
                factory = self._factories[service_type]
                instance = factory()
                
                # Cache if singleton
                if service_type not in self._services:
                    self._singletons[service_type] = instance
                
                return instance
            finally:
                self._initializing.discard(service_type)
        
        raise ServiceNotFoundError(
            f"Service {service_type.__name__} is not registered"
        )
    
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
        """Register a service lazily using a decorator.
        
        Example:
            @service_locator.register_lazy(UserService)
            class UserServiceImpl(UserService):
                pass
        """
        def decorator(cls: Type[T]) -> Type[T]:
            self.register(service_type, factory=lambda: cls())
            return cls
        return decorator


# Global service locator instance
service_locator = ServiceLocator()


# ============================================================================
# SERVICE INTERFACES
# ============================================================================

class IAgentService:
    """Interface for agent service."""
    async def start_agent(self, *args, **kwargs): pass
    async def stop_agent(self, *args, **kwargs): pass
    async def get_agent_status(self, *args, **kwargs): pass


class IThreadService:
    """Interface for thread service."""
    async def create_thread(self, *args, **kwargs): pass
    async def get_thread(self, *args, **kwargs): pass
    async def switch_thread(self, *args, **kwargs): pass
    async def delete_thread(self, *args, **kwargs): pass


class IMessageHandlerService:
    """Interface for message handler service."""
    async def handle_message(self, *args, **kwargs): pass
    async def process_user_message(self, *args, **kwargs): pass


class IMCPService:
    """Interface for MCP service."""
    async def initialize(self, *args, **kwargs): pass
    async def execute_tool(self, *args, **kwargs): pass


class IWebSocketService:
    """Interface for WebSocket service."""
    async def send_message(self, *args, **kwargs): pass
    async def broadcast(self, *args, **kwargs): pass


# ============================================================================
# SERVICE REGISTRATION HELPERS
# ============================================================================

def register_core_services():
    """Register all core services with proper dependency injection."""
    from app.services.agent_service import AgentService
    from app.services.thread_service import ThreadService
    from app.services.message_handlers import MessageHandlerService
    from app.services.mcp_service import MCPService
    
    # Register services with factories to delay initialization
    service_locator.register(
        IAgentService,
        factory=lambda: AgentService(),
        singleton=True
    )
    
    service_locator.register(
        IThreadService,
        factory=lambda: ThreadService(),
        singleton=True
    )
    
    service_locator.register(
        IMessageHandlerService,
        factory=lambda: MessageHandlerService(
            agent_service=service_locator.get(IAgentService),
            thread_service=service_locator.get(IThreadService)
        ),
        singleton=True
    )
    
    service_locator.register(
        IMCPService,
        factory=lambda: MCPService(),
        singleton=True
    )
    
    logger.info("Core services registered successfully")


def get_service(service_type: Type[T]) -> T:
    """Convenience function to get a service."""
    return service_locator.get(service_type)


# ============================================================================
# DECORATORS
# ============================================================================

def inject(*service_types: Type) -> Callable:
    """Decorator to inject services into a function or method.
    
    Example:
        @inject(IAgentService, IThreadService)
        async def my_function(agent_service, thread_service, other_arg):
            # agent_service and thread_service are automatically injected
            pass
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Inject services at the beginning of args
            services = [service_locator.get(st) for st in service_types]
            return func(*services, *args, **kwargs)
        
        async def async_wrapper(*args, **kwargs):
            # Inject services at the beginning of args
            services = [service_locator.get(st) for st in service_types]
            return await func(*services, *args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


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
    "register_core_services",
    "get_service",
    "inject",
]