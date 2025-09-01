"""Service factory functions for dependency injection.

Provides factory functions to create service instances.
Follows 450-line limit with 25-line function limit.
"""

from typing import Any, Dict


def _create_agent_service():
    """Create AgentService - NOTE: Requires app context with initialized dependencies.
    
    This function should NOT be called directly. Use the application's
    initialized agent_service from app.state instead.
    """
    raise NotImplementedError(
        "Agent service cannot be created via factory - it requires initialized dependencies. "
        "Use app.state.agent_service which is created during deterministic startup with proper "
        "WebSocket bridge, LLM manager, and other critical dependencies."
    )


def _create_message_handler_service():
    """Create MessageHandlerService - NOTE: Requires app context with initialized supervisor.
    
    This function should NOT be called directly. Use the application's
    message handlers which are created during startup.
    """
    raise NotImplementedError(
        "Message handler service cannot be created via factory - it requires initialized supervisor. "
        "Message handlers are registered during deterministic startup with proper dependencies."
    )


def _create_core_services() -> Dict[str, Any]:
    """Create core service instances that don't require complex dependencies.
    
    NOTE: agent_service is excluded as it requires initialized supervisor.
    Services requiring WebSocket bridge or supervisor must be created during startup.
    """
    from netra_backend.app.services.corpus_service import CorpusService
    from netra_backend.app.services.thread_service import ThreadService
    
    return {
        # agent_service excluded - requires initialized supervisor with WebSocket bridge
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
    """Create MCP service dependencies.
    
    NOTE: This only creates services that don't require complex initialization.
    Services like agent_service must be provided from app.state.
    """
    core_services = _create_core_services()
    data_services = _create_data_services()
    return {**core_services, **data_services}


def _create_mcp_service(agent_service=None):
    """Create MCPService with dependencies.
    
    Args:
        agent_service: Optional pre-initialized agent service from app.state.
                      Required for full functionality. If not provided, raises error.
    """
    from netra_backend.app.services.mcp_service import MCPService
    
    if not agent_service:
        raise ValueError(
            "agent_service is required for MCPService initialization. "
            "It must be provided from app.state during startup."
        )
    
    dependencies = _create_mcp_dependencies()
    
    # Add agent_service (required)
    dependencies['agent_service'] = agent_service
    
    return MCPService(**dependencies)


def _create_websocket_service():
    """Create WebSocketService - NOTE: Requires initialized message handlers.
    
    WebSocket service is initialized during startup with proper dependencies.
    """
    raise NotImplementedError(
        "WebSocket service cannot be created via factory - it requires initialized message handlers. "
        "WebSocket service is created during deterministic startup."
    )


def _create_mcp_client_service():
    """Create MCPClientService with proper dependencies."""
    from netra_backend.app.services.mcp_client_service import MCPClientService
    
    return MCPClientService()


def get_mcp_service(agent_service=None):
    """Get MCP service instance for dependency injection.
    
    Args:
        agent_service: Optional pre-initialized agent service from app.state.
    
    Note: This function is primarily for manual creation. For FastAPI dependency injection,
    use the get_mcp_service in routes/mcp/service_factory.py which properly injects dependencies.
    """
    return _create_mcp_service(agent_service=agent_service)


def get_service_factories() -> Dict[str, callable]:
    """Get available service factories.
    
    NOTE: Services requiring WebSocket bridge or supervisor are excluded.
    These must be created during deterministic startup.
    """
    return {
        # agent_service excluded - requires initialized supervisor
        # message_handler_service excluded - requires initialized supervisor  
        'mcp_service': _create_mcp_service,
        # websocket_service excluded - requires initialized components
        'mcp_client_service': _create_mcp_client_service,
        'core_services': _create_core_services,
        'data_services': _create_data_services
    }