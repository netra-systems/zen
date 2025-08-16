"""Service Locator Pattern for Dependency Injection.

This module provides a centralized service locator to break circular dependencies
and enable proper dependency injection throughout the application.
"""

from typing import Dict, Type, Any, Optional, TypeVar, Generic, Callable
from functools import lru_cache
import threading
from abc import ABC, abstractmethod
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

class IAgentService(ABC):
    """Interface for agent service."""
    
    @abstractmethod
    async def start_agent(self, request_model, run_id: str, stream_updates: bool = False):
        """Start an agent with the given request model and run ID."""
        pass
    
    @abstractmethod
    async def stop_agent(self, user_id: str) -> bool:
        """Stop an agent for the given user."""
        pass
    
    @abstractmethod
    async def get_agent_status(self, user_id: str) -> Dict[str, Any]:
        """Get the status of an agent for the given user."""
        pass


class IThreadService(ABC):
    """Interface for thread service."""
    
    @abstractmethod
    async def create_thread(self, user_id: str, db=None):
        """Create a new thread for the user."""
        pass
    
    @abstractmethod
    async def get_thread(self, thread_id: str, user_id: str, db=None):
        """Get a specific thread by ID."""
        pass
    
    @abstractmethod
    async def switch_thread(self, user_id: str, thread_id: str, db=None):
        """Switch user to a different thread."""
        pass
    
    @abstractmethod
    async def delete_thread(self, thread_id: str, user_id: str, db=None):
        """Delete a thread for the user."""
        pass


class IMessageHandlerService(ABC):
    """Interface for message handler service."""
    
    @abstractmethod
    async def handle_message(self, user_id: str, message_type: str, payload: Dict[str, Any]):
        """Handle a WebSocket message with proper type and payload."""
        pass
    
    @abstractmethod
    async def process_user_message(self, user_id: str, message: str, thread_id: str = None):
        """Process a user message in a specific thread."""
        pass


class IMCPService(ABC):
    """Interface for MCP service."""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any] = None):
        """Initialize the MCP service with optional configuration."""
        pass
    
    @abstractmethod
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any], user_context: Dict[str, Any] = None):
        """Execute an MCP tool with the given parameters and user context."""
        pass


class IWebSocketService(ABC):
    """Interface for WebSocket service."""
    
    @abstractmethod
    async def send_message(self, user_id: str, message: Dict[str, Any]):
        """Send a message to a specific user via WebSocket."""
        pass
    
    @abstractmethod
    async def broadcast(self, message: Dict[str, Any], exclude_user_ids: list = None):
        """Broadcast a message to all connected users, optionally excluding some."""
        pass


# ============================================================================
# SERVICE REGISTRATION HELPERS
# ============================================================================

def _create_agent_service():
    """Create AgentService with proper dependencies."""
    from app.agents.supervisor_consolidated import SupervisorAgent
    from app.services.agent_service import AgentService
    # Create a supervisor instance with minimal dependencies for service locator
    supervisor = SupervisorAgent(None, None, None, None)  # Will be properly initialized when used
    return AgentService(supervisor)

def _create_message_handler_service():
    """Create MessageHandlerService with proper dependencies."""
    from app.agents.supervisor_consolidated import SupervisorAgent
    from app.services.message_handlers import MessageHandlerService
    from app.services.thread_service import ThreadService
    # Create dependencies
    supervisor = SupervisorAgent(None, None, None, None)  # Will be properly initialized when used
    thread_service = ThreadService()
    return MessageHandlerService(supervisor, thread_service)

def _create_mcp_service():
    """Create MCPService with proper dependencies."""
    from app.services.mcp_service import MCPService
    from app.services.agent_service import AgentService
    from app.services.thread_service import ThreadService
    from app.services.corpus_service import CorpusService
    from app.services.synthetic_data_service import SyntheticDataService
    from app.services.security_service import SecurityService
    from app.services.supply_catalog_service import SupplyCatalogService
    
    # Create minimal dependencies - these will be properly initialized when used
    agent_service = _create_agent_service()
    thread_service = ThreadService()
    corpus_service = CorpusService()
    synthetic_data_service = SyntheticDataService()
    security_service = SecurityService()
    supply_catalog_service = SupplyCatalogService()
    
    return MCPService(
        agent_service=agent_service,
        thread_service=thread_service,
        corpus_service=corpus_service,
        synthetic_data_service=synthetic_data_service,
        security_service=security_service,
        supply_catalog_service=supply_catalog_service
    )

def register_core_services():
    """Register all core services with proper dependency injection."""
    from app.services.agent_service import AgentService
    from app.services.thread_service import ThreadService
    from app.services.message_handlers import MessageHandlerService
    from app.services.mcp_service import MCPService
    from app.services.websocket_service import WebSocketService
    
    # Register services with factories to delay initialization
    service_locator.register(
        IAgentService,
        factory=lambda: _create_agent_service(),
        singleton=True
    )
    
    service_locator.register(
        IThreadService,
        factory=lambda: ThreadService(),
        singleton=True
    )
    
    service_locator.register(
        IMessageHandlerService,
        factory=lambda: _create_message_handler_service(),
        singleton=True
    )
    
    service_locator.register(
        IMCPService,
        factory=lambda: _create_mcp_service(),
        singleton=True
    )
    
    service_locator.register(
        IWebSocketService,
        factory=lambda: WebSocketService(),
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