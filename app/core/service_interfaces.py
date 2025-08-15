"""Standardized service interfaces for consistent service layer patterns.

This module serves as the main entry point for all service interfaces, importing
and re-exporting from the focused modular structure.
"""

# Import from service layer interfaces
from .interfaces_service import (
    ServiceHealth,
    ServiceMetrics,
    BaseServiceInterface,
    CRUDServiceInterface,
    AsyncServiceInterface,
    T, ID, CreateSchema, UpdateSchema, ResponseSchema
)

# Import from base interfaces
from .interfaces_base import (
    BaseServiceMixin,
    BaseService
)

# Import from repository pattern interfaces
from .interfaces_repository import (
    DatabaseService,
    CRUDService,
    ServiceRegistry
)

# Import from agent interfaces
from .interfaces_agent import (
    AsyncTaskService
)

# Import from WebSocket interfaces
from .interfaces_websocket import (
    WebSocketServiceInterface,
    WebSocketManagerInterface
)


# Re-export all interfaces for backwards compatibility
__all__ = [
    # Service layer interfaces
    'ServiceHealth',
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