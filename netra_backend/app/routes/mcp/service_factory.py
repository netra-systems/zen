"""
MCP Service Factory

Factory for creating and managing MCP service instances.
Handles dependency injection and service lifecycle.
"""

from typing import Optional
from fastapi import Depends
from netra_backend.app.dependencies import get_agent_service, get_thread_service, get_corpus_service, get_security_service
from netra_backend.app.services.mcp_service import MCPService
from netra_backend.app.services.synthetic_data_service import SyntheticDataService
from netra_backend.app.services.supply_catalog_service import SupplyCatalogService
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.corpus_service import CorpusService
from netra_backend.app.services.security_service import SecurityService
from netra_backend.app.logging_config import CentralLogger

logger = CentralLogger()

# Global MCP service instance (initialized on first request)
_mcp_service: Optional[MCPService] = None


async def get_mcp_service(
    agent_service: AgentService = Depends(get_agent_service),
    thread_service: ThreadService = Depends(get_thread_service),
    corpus_service: CorpusService = Depends(get_corpus_service),
    security_service: SecurityService = Depends(get_security_service)
) -> MCPService:
    """Get or create MCP service instance"""
    return await _get_or_create_service(agent_service, thread_service, corpus_service, security_service)


def _log_service_initialization() -> None:
    """Log MCP service initialization"""
    logger.info("MCP service initialized with FastMCP 2")


def _create_additional_services() -> tuple:
    """Create additional service dependencies."""
    synthetic_data_service = SyntheticDataService()
    supply_catalog_service = SupplyCatalogService()
    return synthetic_data_service, supply_catalog_service


def _create_mcp_service(
    agent_service: AgentService,
    thread_service: ThreadService, 
    corpus_service: CorpusService,
    security_service: SecurityService
) -> MCPService:
    """Create MCP service with dependencies"""
    return _build_mcp_service_instance(agent_service, thread_service, corpus_service, security_service)


def _build_service_params(
    agent_service, thread_service, corpus_service,
    synthetic_data_service, security_service, supply_catalog_service
) -> dict:
    """Build MCP service parameters dictionary"""
    core_services = _build_core_service_params(agent_service, thread_service, corpus_service)
    extra_services = _build_extra_service_params(synthetic_data_service, security_service, supply_catalog_service)
    return {**core_services, **extra_services}


def _build_core_service_params(agent_service, thread_service, corpus_service) -> dict:
    """Build core service parameters"""
    return {
        "agent_service": agent_service,
        "thread_service": thread_service,
        "corpus_service": corpus_service
    }


def _build_extra_service_params(synthetic_data_service, security_service, supply_catalog_service) -> dict:
    """Build extra service parameters"""
    return {
        "synthetic_data_service": synthetic_data_service,
        "security_service": security_service,
        "supply_catalog_service": supply_catalog_service
    }


async def _get_or_create_service(
    agent_service: AgentService, thread_service: ThreadService,
    corpus_service: CorpusService, security_service: SecurityService
) -> MCPService:
    """Get or create service instance"""
    return await _create_service_if_needed(agent_service, thread_service, corpus_service, security_service)


def _build_mcp_service_instance(
    agent_service: AgentService, thread_service: ThreadService,
    corpus_service: CorpusService, security_service: SecurityService
) -> MCPService:
    """Build MCP service instance with all dependencies"""
    additional_services = _create_additional_services()
    service_params = _create_service_params(agent_service, thread_service, corpus_service, security_service, additional_services)
    return MCPService(**service_params)


async def _create_service_if_needed(agent_service, thread_service, corpus_service, security_service) -> MCPService:
    """Create service if needed"""
    global _mcp_service
    if _mcp_service is None:
        _mcp_service = _create_mcp_service(agent_service, thread_service, corpus_service, security_service)
        _log_service_initialization()
    return _mcp_service


def _create_service_params(agent_service, thread_service, corpus_service, security_service, additional_services) -> dict:
    """Create service parameters"""
    synthetic_data_service, supply_catalog_service = additional_services
    return _build_service_params(
        agent_service, thread_service, corpus_service, 
        synthetic_data_service, security_service, supply_catalog_service
    )


async def create_mcp_service_for_websocket() -> MCPService:
    """Create MCP service instance for WebSocket endpoints without FastAPI Depends."""
    from netra_backend.app.dependencies import get_agent_service, get_thread_service, get_corpus_service, get_security_service
    
    # Manually create service dependencies for WebSocket
    agent_service = get_agent_service()
    thread_service = get_thread_service()
    corpus_service = get_corpus_service()
    security_service = get_security_service()
    
    return await _get_or_create_service(agent_service, thread_service, corpus_service, security_service)