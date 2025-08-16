"""Service Locator Pattern for Dependency Injection.

This module provides a centralized service locator to break circular dependencies
and enable proper dependency injection throughout the application.
"""

from typing import Dict, Type, Any, Optional, TypeVar, Generic, Callable, List
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
            if service_type not in self._services:
                self._singletons[service_type] = instance
            return instance
        finally:
            self._initializing.discard(service_type)
    
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


class IMCPClientService(ABC):
    """Interface for MCP Client service."""
    
    @abstractmethod
    async def register_server(self, server_config: Dict[str, Any]) -> bool:
        """Register an external MCP server."""
        pass
    
    @abstractmethod
    async def connect_to_server(self, server_name: str) -> Dict[str, Any]:
        """Connect to a specific MCP server."""
        pass
    
    @abstractmethod
    async def list_servers(self) -> List[Dict[str, Any]]:
        """List all registered MCP servers."""
        pass
    
    @abstractmethod
    async def discover_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Discover tools from an MCP server."""
        pass
    
    @abstractmethod
    async def execute_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on an MCP server."""
        pass
    
    @abstractmethod
    async def get_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """Get resources from an MCP server."""
        pass
    
    @abstractmethod
    async def fetch_resource(self, server_name: str, uri: str) -> Dict[str, Any]:
        """Fetch a specific resource from an MCP server."""
        pass
    
    @abstractmethod
    async def clear_cache(self, server_name: Optional[str] = None):
        """Clear MCP client cache."""
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

def _create_core_services() -> dict:
    """Create core service instances."""
    from app.services.thread_service import ThreadService
    from app.services.corpus_service import CorpusService
    return {
        'agent_service': _create_agent_service(),
        'thread_service': ThreadService(),
        'corpus_service': CorpusService()
    }

def _create_data_services() -> dict:
    """Create data service instances."""
    from app.services.synthetic_data_service import SyntheticDataService
    from app.services.security_service import SecurityService
    from app.services.supply_catalog_service import SupplyCatalogService
    return {
        'synthetic_data_service': SyntheticDataService(),
        'security_service': SecurityService(),
        'supply_catalog_service': SupplyCatalogService()
    }

def _create_mcp_dependencies() -> dict:
    """Create MCP service dependencies."""
    core_services = _create_core_services()
    data_services = _create_data_services()
    return {**core_services, **data_services}

def _create_mcp_service():
    """Create MCPService with proper dependencies."""
    from app.services.mcp_service import MCPService
    dependencies = _create_mcp_dependencies()
    return MCPService(**dependencies)

def _create_mcp_client_service():
    """Create MCPClientService with proper dependencies."""
    from app.services.mcp_client_service import MCPClientService
    return MCPClientService()

def _register_agent_services() -> None:
    """Register agent and message handler services."""
    service_locator.register(
        IAgentService,
        factory=lambda: _create_agent_service(),
        singleton=True
    )
    service_locator.register(
        IMessageHandlerService,
        factory=lambda: _create_message_handler_service(),
        singleton=True
    )

def _register_thread_service() -> None:
    """Register thread service."""
    from app.services.thread_service import ThreadService
    service_locator.register(
        IThreadService,
        factory=lambda: ThreadService(),
        singleton=True
    )

def _register_websocket_service() -> None:
    """Register WebSocket service."""
    from app.services.websocket_service import WebSocketService
    service_locator.register(
        IWebSocketService,
        factory=lambda: WebSocketService(),
        singleton=True
    )

def _register_communication_services() -> None:
    """Register communication and thread services."""
    _register_thread_service()
    _register_websocket_service()

def _register_client_services() -> None:
    """Register MCP client services."""
    service_locator.register(
        IMCPClientService,
        factory=lambda: _create_mcp_client_service(),
        singleton=True
    )

def register_core_services() -> None:
    """Register all core services with proper dependency injection."""
    _register_agent_services()
    _register_communication_services()
    _register_client_services()
    # Note: MCPService registration disabled due to complex repository dependencies
    logger.info("Core services registered successfully")


def get_service(service_type: Type[T]) -> T:
    """Convenience function to get a service."""
    return service_locator.get(service_type)


# ============================================================================
# DECORATORS
# ============================================================================

def _get_injected_services(service_types: tuple) -> list:
    """Get list of service instances for injection."""
    return [service_locator.get(st) for st in service_types]

def _create_sync_wrapper(func: Callable, service_types: tuple) -> Callable:
    """Create wrapper for synchronous functions."""
    def wrapper(*args, **kwargs):
        services = _get_injected_services(service_types)
        return func(*services, *args, **kwargs)
    return wrapper

def _create_async_wrapper(func: Callable, service_types: tuple) -> Callable:
    """Create wrapper for asynchronous functions."""
    async def async_wrapper(*args, **kwargs):
        services = _get_injected_services(service_types)
        return await func(*services, *args, **kwargs)
    return async_wrapper

def _select_wrapper(func: Callable, service_types: tuple) -> Callable:
    """Select appropriate wrapper based on function type."""
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return _create_async_wrapper(func, service_types)
    return _create_sync_wrapper(func, service_types)

def inject(*service_types: Type) -> Callable:
    """Decorator to inject services into a function or method."""
    def decorator(func: Callable) -> Callable:
        return _select_wrapper(func, service_types)
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
    "IMCPClientService",
    "register_core_services",
    "get_service",
    "inject",
]