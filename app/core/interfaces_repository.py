"""Repository pattern interfaces and implementations."""

from typing import Any, Dict, Generic, List, Optional
from datetime import datetime, UTC
from contextlib import asynccontextmanager

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .exceptions import ServiceError, RecordNotFoundError
from .error_context import ErrorContext
from .interfaces_service import (
    BaseServiceInterface, 
    ServiceHealth,
    T, ID, CreateSchema, UpdateSchema, ResponseSchema
)
from .interfaces_base import BaseService


class DatabaseService(BaseService):
    """Base service for database operations."""
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self._session_factory = None
    
    def set_session_factory(self, session_factory):
        """Set the database session factory."""
        self._session_factory = session_factory
    
    @asynccontextmanager
    async def get_db_session(self):
        """Get a database session with proper error handling."""
        if not self._session_factory:
            raise ServiceError(
                message=f"Database session factory not configured for {self.service_name}"
            )
        
        async with self._session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise ServiceError(
                    message=f"Database operation failed for {self.service_name}: {e}",
                    context=ErrorContext.get_all_context()
                )
            finally:
                await session.close()


class CRUDService(DatabaseService, Generic[T, ID, CreateSchema, UpdateSchema, ResponseSchema]):
    """Base CRUD service implementation."""
    
    def __init__(self, service_name: str, model_class: type, response_schema: type):
        super().__init__(service_name)
        self._model_class = model_class
        self._response_schema = response_schema
    
    async def create(self, data: CreateSchema, **context) -> ResponseSchema:
        """Create a new entity."""
        async with self.get_db_session() as session:
            # Convert Pydantic model to dict for SQLAlchemy
            entity_data = data.model_dump() if hasattr(data, 'model_dump') else data
            
            # Create entity
            entity = self._model_class(**entity_data)
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            
            # Convert to response schema
            return self._to_response_schema(entity)
    
    async def get_by_id(self, entity_id: ID, **context) -> Optional[ResponseSchema]:
        """Get entity by ID."""
        async with self.get_db_session() as session:
            entity = await session.get(self._model_class, entity_id)
            if entity:
                return self._to_response_schema(entity)
            return None
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        filters: Optional[Dict[str, Any]] = None,
        **context
    ) -> List[ResponseSchema]:
        """Get multiple entities with pagination and filtering."""
        async with self.get_db_session() as session:
            query = session.query(self._model_class)
            
            # Apply filters if provided
            if filters:
                query = self._apply_filters(query, filters)
            
            # Apply pagination
            entities = await query.offset(skip).limit(limit).all()
            
            return [self._to_response_schema(entity) for entity in entities]
    
    async def update(self, entity_id: ID, data: UpdateSchema, **context) -> ResponseSchema:
        """Update an existing entity."""
        async with self.get_db_session() as session:
            entity = await session.get(self._model_class, entity_id)
            if not entity:
                raise RecordNotFoundError(
                    self._model_class.__name__,
                    entity_id
                )
            
            # Update fields
            update_data = data.model_dump(exclude_unset=True) if hasattr(data, 'model_dump') else data
            for field, value in update_data.items():
                if hasattr(entity, field):
                    setattr(entity, field, value)
            
            await session.commit()
            await session.refresh(entity)
            
            return self._to_response_schema(entity)
    
    async def delete(self, entity_id: ID, **context) -> bool:
        """Delete an entity."""
        async with self.get_db_session() as session:
            entity = await session.get(self._model_class, entity_id)
            if not entity:
                return False
            
            await session.delete(entity)
            await session.commit()
            return True
    
    async def exists(self, entity_id: ID, **context) -> bool:
        """Check if entity exists."""
        async with self.get_db_session() as session:
            entity = await session.get(self._model_class, entity_id)
            return entity is not None
    
    def _to_response_schema(self, entity) -> ResponseSchema:
        """Convert database entity to response schema."""
        if hasattr(entity, '__dict__'):
            # Convert SQLAlchemy model to dict, then to response schema
            entity_dict = {
                column.name: getattr(entity, column.name)
                for column in entity.__table__.columns
            }
            return self._response_schema(**entity_dict)
        return self._response_schema.from_orm(entity)
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to query - override in subclasses for complex filtering."""
        for field, value in filters.items():
            if hasattr(self._model_class, field):
                query = query.filter(getattr(self._model_class, field) == value)
        return query


class ServiceRegistry:
    """Registry for managing service instances."""
    
    def __init__(self):
        self._services: Dict[str, BaseServiceInterface] = {}
    
    def register(self, service: BaseServiceInterface):
        """Register a service."""
        self._services[service.service_name] = service
    
    def get_service(self, service_name: str) -> Optional[BaseServiceInterface]:
        """Get a registered service."""
        return self._services.get(service_name)
    
    def get_all_services(self) -> Dict[str, BaseServiceInterface]:
        """Get all registered services."""
        return self._services.copy()
    
    async def initialize_all(self):
        """Initialize all registered services."""
        for service in self._services.values():
            await service.initialize()
    
    async def shutdown_all(self):
        """Shutdown all registered services."""
        for service in reversed(list(self._services.values())):
            await service.shutdown()
    
    async def health_check_all(self) -> Dict[str, ServiceHealth]:
        """Perform health check on all services."""
        health_results = {}
        for name, service in self._services.items():
            try:
                health_results[name] = await service.health_check()
            except Exception as e:
                health_results[name] = ServiceHealth(
                    service_name=name,
                    status="unhealthy",
                    timestamp=datetime.now(UTC),
                    dependencies={},
                    metrics={"error": str(e)}
                )
        return health_results