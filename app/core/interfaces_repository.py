"""Repository pattern interfaces and implementations."""

from typing import Any, Dict, Generic, List, Optional
from datetime import datetime, UTC
from contextlib import asynccontextmanager

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .exceptions import ServiceError, RecordNotFoundError
from app.schemas.shared_types import ErrorContext
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
        self._validate_session_factory()
        
        async with self._session_factory() as session:
            try:
                yield session
            except Exception as e:
                await self._handle_session_error(session, e)
            finally:
                await session.close()
    
    def _validate_session_factory(self):
        """Validate session factory is configured."""
        if not self._session_factory:
            raise ServiceError(
                message=f"Database session factory not configured for {self.service_name}"
            )
    
    async def _handle_session_error(self, session: AsyncSession, error: Exception):
        """Handle database session error."""
        await session.rollback()
        raise ServiceError(
            message=f"Database operation failed for {self.service_name}: {error}",
            context=ErrorContext.get_all_context()
        )


class CRUDService(DatabaseService, Generic[T, ID, CreateSchema, UpdateSchema, ResponseSchema]):
    """Base CRUD service implementation."""
    
    def __init__(self, service_name: str, model_class: type, response_schema: type):
        super().__init__(service_name)
        self._model_class = model_class
        self._response_schema = response_schema
    
    async def create(self, data: CreateSchema, **context) -> ResponseSchema:
        """Create a new entity."""
        async with self.get_db_session() as session:
            entity_data = self._extract_entity_data(data)
            entity = await self._create_and_persist_entity(session, entity_data)
            return self._to_response_schema(entity)
    
    def _extract_entity_data(self, data: CreateSchema) -> dict:
        """Extract entity data from schema."""
        return data.model_dump() if hasattr(data, 'model_dump') else data
    
    async def _create_and_persist_entity(self, session: AsyncSession, entity_data: dict):
        """Create and persist entity to database."""
        entity = self._model_class(**entity_data)
        session.add(entity)
        await session.commit()
        await session.refresh(entity)
        return entity
    
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
            query = self._build_query(session, filters)
            entities = await self._execute_paginated_query(query, skip, limit)
            return [self._to_response_schema(entity) for entity in entities]
    
    def _build_query(self, session: AsyncSession, filters: Optional[Dict[str, Any]]):
        """Build database query with optional filters."""
        query = session.query(self._model_class)
        if filters:
            query = self._apply_filters(query, filters)
        return query
    
    async def _execute_paginated_query(self, query, skip: int, limit: int):
        """Execute query with pagination."""
        return await query.offset(skip).limit(limit).all()
    
    async def update(self, entity_id: ID, data: UpdateSchema, **context) -> ResponseSchema:
        """Update an existing entity."""
        async with self.get_db_session() as session:
            entity = await self._get_entity_or_raise(session, entity_id)
            self._update_entity_fields(entity, data)
            await session.commit()
            await session.refresh(entity)
            return self._to_response_schema(entity)
    
    async def _get_entity_or_raise(self, session: AsyncSession, entity_id: ID):
        """Get entity or raise RecordNotFoundError."""
        entity = await session.get(self._model_class, entity_id)
        if not entity:
            raise RecordNotFoundError(self._model_class.__name__, entity_id)
        return entity
    
    def _update_entity_fields(self, entity, data: UpdateSchema):
        """Update entity fields from data."""
        update_data = data.model_dump(exclude_unset=True) if hasattr(data, 'model_dump') else data
        for field, value in update_data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)
    
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
            entity_dict = self._extract_entity_dict(entity)
            return self._response_schema(**entity_dict)
        return self._response_schema.from_orm(entity)
    
    def _extract_entity_dict(self, entity) -> dict:
        """Extract entity attributes as dictionary."""
        return {
            column.name: getattr(entity, column.name)
            for column in entity.__table__.columns
        }
    
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
            health_results[name] = await self._check_service_health(name, service)
        return health_results
    
    async def _check_service_health(self, name: str, service: BaseServiceInterface) -> ServiceHealth:
        """Check health of individual service."""
        try:
            return await service.health_check()
        except Exception as e:
            return self._create_unhealthy_service_health(name, e)
    
    def _create_unhealthy_service_health(self, name: str, error: Exception) -> ServiceHealth:
        """Create unhealthy service health response."""
        return ServiceHealth(
            service_name=name,
            status="unhealthy",
            timestamp=datetime.now(UTC),
            dependencies={},
            metrics={"error": str(error)}
        )