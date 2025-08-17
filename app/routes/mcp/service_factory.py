"""
MCP Service Factory

Factory for creating and managing MCP service instances.
Handles dependency injection and service lifecycle.
"""

from typing import Optional
from fastapi import Depends
from app.dependencies import get_agent_service, get_thread_service, get_corpus_service, get_security_service
from app.services.mcp_service import MCPService
from app.services.synthetic_data_service import SyntheticDataService
from app.services.supply_catalog_service import SupplyCatalogService
from app.services.agent_service import AgentService
from app.services.thread_service import ThreadService
from app.services.corpus_service import CorpusService
from app.services.security_service import SecurityService
from app.logging_config import CentralLogger

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
    global _mcp_service
    
    if _mcp_service is None:
        _mcp_service = _create_mcp_service(
            agent_service, 
            thread_service, 
            corpus_service, 
            security_service
        )
        logger.info("MCP service initialized with FastMCP 2")
        
    return _mcp_service


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
    synthetic_data_service, supply_catalog_service = _create_additional_services()
    return MCPService(
        agent_service=agent_service,
        thread_service=thread_service,
        corpus_service=corpus_service,
        synthetic_data_service=synthetic_data_service,
        security_service=security_service,
        supply_catalog_service=supply_catalog_service
    )