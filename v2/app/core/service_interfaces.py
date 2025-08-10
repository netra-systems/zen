"""Standardized service interfaces for consistent service layer patterns."""

import abc
import asyncio
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union, Protocol
from datetime import datetime
from contextlib import asynccontextmanager

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .exceptions import ServiceError, RecordNotFoundError, ValidationError
from .error_context import ErrorContext


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


class BaseServiceMixin:
    """Mixin providing common service functionality."""
    
    def __init__(self):
        self._initialized = False
        self._metrics = ServiceMetrics()
        self._background_tasks: set = set()
        
    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized
    
    @property
    def metrics(self) -> ServiceMetrics:
        """Get service metrics."""
        return self._metrics
    
    def _update_metrics(self, success: bool, response_time: float):
        """Update service metrics."""
        self._metrics.requests_total += 1
        if success:
            self._metrics.requests_successful += 1
        else:
            self._metrics.requests_failed += 1
        
        # Update average response time
        if self._metrics.requests_total == 1:
            self._metrics.average_response_time = response_time
        else:
            self._metrics.average_response_time = (
                (self._metrics.average_response_time * (self._metrics.requests_total - 1) + response_time)
                / self._metrics.requests_total
            )
        
        self._metrics.last_request_timestamp = datetime.utcnow()
    
    def _create_background_task(self, coro):
        """Create and track a background task."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task
    
    async def _cancel_background_tasks(self):
        """Cancel all background tasks."""
        if self._background_tasks:
            for task in list(self._background_tasks):
                task.cancel()
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()


class BaseService(BaseServiceMixin):
    """Base service implementation with common patterns."""
    
    def __init__(self, service_name: str):
        super().__init__()
        self._service_name = service_name
        
    @property
    def service_name(self) -> str:
        """Return the service name."""
        return self._service_name
    
    async def initialize(self) -> None:
        """Initialize the service."""
        if self._initialized:
            return
        
        try:
            await self._initialize_impl()
            self._initialized = True
        except Exception as e:
            raise ServiceError(
                service_name=self._service_name,
                message=f"Failed to initialize service: {e}",
                context=ErrorContext.get_all_context()
            )
    
    async def _initialize_impl(self) -> None:
        """Service-specific initialization logic."""
        pass
    
    async def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        try:
            await self._cancel_background_tasks()
            await self._shutdown_impl()
            self._initialized = False
        except Exception as e:
            raise ServiceError(
                service_name=self._service_name,
                message=f"Failed to shutdown service: {e}",
                context=ErrorContext.get_all_context()
            )
    
    async def _shutdown_impl(self) -> None:
        """Service-specific shutdown logic."""
        pass
    
    async def health_check(self) -> ServiceHealth:
        """Perform health check and return status."""
        try:
            # Basic health check - override in subclasses for specific checks
            dependencies = await self._check_dependencies()
            
            status = "healthy"
            for dep_name, dep_status in dependencies.items():
                if dep_status != "healthy":
                    status = "degraded"
                    break
            
            return ServiceHealth(
                service_name=self._service_name,
                status=status,
                timestamp=datetime.utcnow(),
                dependencies=dependencies,
                metrics=self._metrics.dict()
            )
        except Exception as e:
            return ServiceHealth(
                service_name=self._service_name,
                status="unhealthy",
                timestamp=datetime.utcnow(),
                dependencies={},
                metrics={"error": str(e)}
            )
    
    async def _check_dependencies(self) -> Dict[str, str]:
        """Check service dependencies - override in subclasses."""
        return {}


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
                service_name=self.service_name,
                message="Database session factory not configured"
            )
        
        async with self._session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise ServiceError(
                    service_name=self.service_name,
                    message=f"Database operation failed: {e}",
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
            entity_data = data.dict() if hasattr(data, 'dict') else data
            
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
                    resource=self._model_class.__name__,
                    identifier=entity_id
                )
            
            # Update fields
            update_data = data.dict(exclude_unset=True) if hasattr(data, 'dict') else data
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


class AsyncTaskService(BaseService, AsyncServiceInterface):
    """Base service for services that run background tasks."""
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self._background_running = False
    
    async def start_background_tasks(self) -> None:
        """Start background tasks."""
        if self._background_running:
            return
        
        self._background_running = True
        await self._start_background_tasks_impl()
    
    async def _start_background_tasks_impl(self) -> None:
        """Implementation-specific background task startup."""
        pass
    
    async def stop_background_tasks(self) -> None:
        """Stop background tasks."""
        if not self._background_running:
            return
        
        self._background_running = False
        await self._stop_background_tasks_impl()
        await self._cancel_background_tasks()
    
    async def _stop_background_tasks_impl(self) -> None:
        """Implementation-specific background task shutdown."""
        pass
    
    async def _shutdown_impl(self) -> None:
        """Shutdown implementation."""
        await self.stop_background_tasks()


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
                    timestamp=datetime.utcnow(),
                    dependencies={},
                    metrics={"error": str(e)}
                )
        return health_results


# Global service registry
service_registry = ServiceRegistry()