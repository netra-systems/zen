"""Standardized service interfaces for consistent service layer patterns.

This module serves as the main entry point for all service interfaces, importing
and re-exporting from the focused modular structure.
"""

# Import from service layer interfaces
# Import from agent interfaces
from netra_backend.app.core.interfaces_agent import AsyncTaskService
# Import health status enum
from netra_backend.app.services.circuit_breaker.service_health_monitor import ServiceHealthStatus

# Import from base interfaces
from netra_backend.app.core.interfaces_base import BaseService, BaseServiceMixin

# Import from repository pattern interfaces
from netra_backend.app.core.interfaces_repository import (
    CRUDService,
    DatabaseService,
    ServiceRegistry,
)
from netra_backend.app.core.interfaces_service import (
    ID,
    AsyncServiceInterface,
    BaseServiceInterface,
    CreateSchema,
    CRUDServiceInterface,
    ResponseSchema,
    ServiceHealth,
    ServiceMetrics,
    T,
    UpdateSchema,
)

# Import from WebSocket interfaces
from netra_backend.app.core.interfaces_websocket import (
    WebSocketManagerInterface,
    WebSocketServiceInterface,
)

# Re-export all interfaces for backwards compatibility
__all__ = [
    # Service layer interfaces
    'ServiceHealth',
    'ServiceHealthStatus',
    'ServiceMetrics',
    'BaseServiceInterface',
    'CRUDServiceInterface',
    'AsyncServiceInterface',
    'T', 'ID', 'CreateSchema', 'UpdateSchema', 'ResponseSchema',
    
    # Repository pattern interfaces
    'BaseServiceMixin',
    'BaseService',
    'DatabaseService',
    'CRUDService',
    'ServiceRegistry',
    
    # Agent interfaces
    'AsyncTaskService',
    
    # WebSocket interfaces
    'WebSocketServiceInterface',
    'WebSocketManagerInterface',
    
    # Global registry instance
    'service_registry'
]


# Global service registry instance
service_registry = ServiceRegistry()