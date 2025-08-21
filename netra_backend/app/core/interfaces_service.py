"""Service layer interfaces for consistent service patterns."""

import abc
from typing import Any, Dict, Generic, List, Optional, TypeVar, Protocol
from datetime import datetime

from pydantic import BaseModel


# Type variables for generic interfaces
T = TypeVar('T')
ID = TypeVar('ID')
CreateSchema = TypeVar('CreateSchema', bound=BaseModel)
UpdateSchema = TypeVar('UpdateSchema', bound=BaseModel)
ResponseSchema = TypeVar('ResponseSchema', bound=BaseModel)


class ServiceHealth(BaseModel):
    """Standard service health check model."""
    service_name: str
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    version: Optional[str] = None
    dependencies: Dict[str, str] = {}
    metrics: Dict[str, Any] = {}


class ServiceMetrics(BaseModel):
    """Standard service metrics model."""
    requests_total: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    average_response_time: float = 0.0
    last_request_timestamp: Optional[datetime] = None


class BaseServiceInterface(Protocol):
    """Base interface that all services should implement."""
    
    @property
    def service_name(self) -> str:
        """Return the service name."""
        ...
    
    async def health_check(self) -> ServiceHealth:
        """Perform health check and return status."""
        ...
    
    async def initialize(self) -> None:
        """Initialize the service."""
        ...
    
    async def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        ...


class CRUDServiceInterface(BaseServiceInterface, Generic[T, ID, CreateSchema, UpdateSchema, ResponseSchema]):
    """Interface for CRUD services."""
    
    async def create(self, data: CreateSchema, **context) -> ResponseSchema:
        """Create a new entity."""
        ...
    
    async def get_by_id(self, entity_id: ID, **context) -> Optional[ResponseSchema]:
        """Get entity by ID."""
        ...
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        filters: Optional[Dict[str, Any]] = None,
        **context
    ) -> List[ResponseSchema]:
        """Get multiple entities with pagination and filtering."""
        ...
    
    async def update(self, entity_id: ID, data: UpdateSchema, **context) -> ResponseSchema:
        """Update an existing entity."""
        ...
    
    async def delete(self, entity_id: ID, **context) -> bool:
        """Delete an entity."""
        ...
    
    async def exists(self, entity_id: ID, **context) -> bool:
        """Check if entity exists."""
        ...


class AsyncServiceInterface(BaseServiceInterface):
    """Interface for asynchronous services."""
    
    async def start_background_tasks(self) -> None:
        """Start background tasks."""
        ...
    
    async def stop_background_tasks(self) -> None:
        """Stop background tasks."""
        ...