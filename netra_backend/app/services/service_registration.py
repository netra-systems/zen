"""Service registration helpers for dependency injection.

Provides functions to register services with the service locator.
Follows 450-line limit with 25-line function limit.
"""

from app.logging_config import central_logger
from netra_backend.app.service_locator_core import ServiceLocator
from netra_backend.app.service_interfaces import (
    IAgentService, IThreadService, IMessageHandlerService,
    IMCPService, IWebSocketService, IMCPClientService
)
from netra_backend.app.service_factory import (
    _create_agent_service, _create_message_handler_service,
    _create_mcp_service, _create_websocket_service, _create_mcp_client_service
)

logger = central_logger.get_logger(__name__)


def _register_agent_services(service_locator: ServiceLocator) -> None:
    """Register agent-related services."""
    service_locator.register(
        IAgentService,
        factory=_create_agent_service
    )
    logger.debug("Agent services registered")


def _register_communication_services(service_locator: ServiceLocator) -> None:
    """Register communication-related services."""
    service_locator.register(
        IMessageHandlerService,
        factory=_create_message_handler_service
    )
    
    service_locator.register(
        IWebSocketService,
        factory=_create_websocket_service
    )
    logger.debug("Communication services registered")


def _register_client_services(service_locator: ServiceLocator) -> None:
    """Register client-related services."""
    service_locator.register(
        IMCPClientService,
        factory=_create_mcp_client_service
    )
    logger.debug("Client services registered")


def _register_mcp_services(service_locator: ServiceLocator) -> None:
    """Register MCP-related services."""
    service_locator.register(
        IMCPService,
        factory=_create_mcp_service
    )
    logger.debug("MCP services registered")


def _register_thread_services(service_locator: ServiceLocator) -> None:
    """Register thread-related services."""
    from app.services.thread_service import ThreadService
    
    service_locator.register(
        IThreadService,
        factory=lambda: ThreadService()
    )
    logger.debug("Thread services registered")


def register_core_services(service_locator: ServiceLocator) -> None:
    """Register all core services with proper dependency injection."""
    _register_agent_services(service_locator)
    _register_communication_services(service_locator)
    _register_client_services(service_locator)
    _register_thread_services(service_locator)
    # Note: MCPService registration disabled due to complex repository dependencies
    logger.info("Core services registered successfully")


def register_service_batch(service_locator: ServiceLocator, services: dict) -> None:
    """Register a batch of services."""
    for service_type, service_instance in services.items():
        service_locator.register(service_type, implementation=service_instance)
    logger.debug(f"Registered {len(services)} services in batch")


def unregister_service(service_locator: ServiceLocator, service_type) -> bool:
    """Unregister a service (for testing purposes)."""
    try:
        if hasattr(service_locator, '_services'):
            service_locator._services.pop(service_type, None)
        if hasattr(service_locator, '_factories'):
            service_locator._factories.pop(service_type, None)
        if hasattr(service_locator, '_singletons'):
            service_locator._singletons.pop(service_type, None)
        return True
    except Exception as e:
        logger.error(f"Failed to unregister service {service_type}: {e}")
        return False