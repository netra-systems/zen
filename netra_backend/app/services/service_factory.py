"""Service factory functions for dependency injection.

Provides factory functions to create service instances.
Follows 450-line limit with 25-line function limit.
"""

from typing import Any, Dict


def _create_agent_service():
    """Create AgentService with proper dependencies."""
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    from netra_backend.app.services.agent_service import AgentService
    
    # Create a supervisor instance with minimal dependencies for service locator
    supervisor = SupervisorAgent(None, None, None, None)  # Will be properly initialized when used
    return AgentService(supervisor)


def _create_message_handler_service():
    """Create MessageHandlerService with proper dependencies."""
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    from netra_backend.app.services.message_handlers import MessageHandlerService
    from netra_backend.app.services.thread_service import ThreadService
    
    # Create dependencies
    supervisor = SupervisorAgent(None, None, None, None)  # Will be properly initialized when used
    thread_service = ThreadService()
    return MessageHandlerService(supervisor, thread_service)


def _create_core_services() -> Dict[str, Any]:
    """Create core service instances."""
    from netra_backend.app.services.corpus_service import CorpusService
    from netra_backend.app.services.thread_service import ThreadService
    
    return {
        'agent_service': _create_agent_service(),
        'thread_service': ThreadService(),
        'corpus_service': CorpusService()
    }


def _create_data_services() -> Dict[str, Any]:
    """Create data service instances."""
    from netra_backend.app.services.security_service import SecurityService
    from netra_backend.app.services.supply_catalog_service import SupplyCatalogService
    from netra_backend.app.services.synthetic_data_service import SyntheticDataService
    
    return {
        'synthetic_data_service': SyntheticDataService(),
        'security_service': SecurityService(),
        'supply_catalog_service': SupplyCatalogService()
    }


def _create_mcp_dependencies() -> Dict[str, Any]:
    """Create MCP service dependencies."""
    core_services = _create_core_services()
    data_services = _create_data_services()
    return {**core_services, **data_services}


def _create_mcp_service():
    """Create MCPService with proper dependencies."""
    from netra_backend.app.services.mcp_service import MCPService
    
    dependencies = _create_mcp_dependencies()
    return MCPService(**dependencies)


def _create_websocket_service():
    """Create WebSocketService with proper dependencies."""
    from netra_backend.app.services.websocket_service import WebSocketService
    
    message_handler = _create_message_handler_service()
    return WebSocketService(message_handler)


def _create_mcp_client_service():
    """Create MCPClientService with proper dependencies."""
    from netra_backend.app.services.mcp_client_service import MCPClientService
    
    return MCPClientService()


def get_mcp_service():
    """Get MCP service instance for dependency injection."""
    return _create_mcp_service()


def get_service_factories() -> Dict[str, callable]:
    """Get all available service factories."""
    return {
        'agent_service': _create_agent_service,
        'message_handler_service': _create_message_handler_service,
        'mcp_service': _create_mcp_service,
        'websocket_service': _create_websocket_service,
        'mcp_client_service': _create_mcp_client_service,
        'core_services': _create_core_services,
        'data_services': _create_data_services
    }