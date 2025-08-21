"""Enhanced base service classes using the new service interfaces."""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID
from datetime import datetime, UTC

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from netra_backend.app.db.base import Base
from netra_backend.app.core.service_interfaces import (
    BaseService,
    CRUDService,
    DatabaseService,
    ServiceHealth
)
from netra_backend.app.core.exceptions_database import RecordNotFoundError
from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.app.core.error_context import AsyncErrorContext as ErrorContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Legacy CRUD base class - DEPRECATED
    
    This class is deprecated. Use the new service interfaces from app.core.service_interfaces
    or EnhancedCRUDService for new implementations.
    
    TODO: Migrate app.services.user_service to use EnhancedCRUDService
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        **Parameters**
        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        
        DEPRECATED: Use EnhancedCRUDService or proper service interfaces instead.
        """
        import warnings
        warnings.warn(
            "CRUDBase is deprecated. Use EnhancedCRUDService or proper service interfaces.",
            DeprecationWarning,
            stacklevel=2
        )
        self.model = model

    async def get(self, db: AsyncSession, id: Union[int, str, UUID]) -> Optional[ModelType]:
        result = await db.execute(select(self.model).filter(self.model.id == id))
        return result.scalars().first()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        obj = await self.get(db, id=id)
        if obj:
            db.delete(obj)
            await db.commit()
        return obj


class EnhancedCRUDService(CRUDService[ModelType, Any, CreateSchemaType, UpdateSchemaType, ModelType]):
    """Enhanced CRUD service using the new service interface patterns."""
    
    def __init__(self, service_name: str, model_class: Type[ModelType]):
        super().__init__(service_name, model_class, model_class)
    
    async def _check_dependencies(self) -> Dict[str, str]:
        """Check database connectivity."""
        try:
            # Test database connection
            async with self.get_db_session() as session:
                await session.execute(select(1))
            return {"database": "healthy"}
        except Exception as e:
            logger.error(f"Database health check failed: {e}", exc_info=True)
            return {"database": "unhealthy"}
    
    def _to_response_schema(self, entity: ModelType) -> ModelType:
        """Convert entity to response schema (identity for SQLAlchemy models)."""
        return entity


class ServiceHealthChecker:
    """Utility class for checking service health."""
    
    @staticmethod
    async def check_service_health(service: BaseService) -> ServiceHealth:
        """Check the health of a service with error handling."""
        try:
            return await service.health_check()
        except Exception as e:
            logger.error(f"Service health check failed for {service.service_name}: {e}", exc_info=True)
            return ServiceHealth(
                service_name=service.service_name,
                status="unhealthy",
                timestamp=datetime.now(UTC),
                dependencies={},
                metrics={"error": str(e)}
            )
    
    @staticmethod
    async def check_multiple_services(services: List[BaseService]) -> Dict[str, ServiceHealth]:
        """Check health of multiple services concurrently."""
        import asyncio
        
        tasks = [
            ServiceHealthChecker.check_service_health(service)
            for service in services
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_status = {}
        for service, result in zip(services, results):
            if isinstance(result, Exception):
                logger.error(f"Service health check failed for {service.service_name}: {result}")
                health_status[service.service_name] = ServiceHealth(
                    service_name=service.service_name,
                    status="unhealthy",
                    timestamp=datetime.now(UTC),
                    dependencies={},
                    metrics={"error": str(result)}
                )
            else:
                health_status[service.service_name] = result
        
        return health_status


class ServiceMixin:
    """Mixin providing common service functionality for existing services."""
    
    def __init__(self, service_name: str):
        self._service_name = service_name
        self._initialized = False
        
    @property
    def service_name(self) -> str:
        return self._service_name
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    async def initialize_service(self):
        """Initialize the service."""
        if not self._initialized:
            try:
                if hasattr(self, '_initialize_impl'):
                    await self._initialize_impl()
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize service {self._service_name}: {e}", exc_info=True)
                raise ServiceError(
                    service_name=self._service_name,
                    message=f"Failed to initialize {self._service_name}: {e}",
                    context=ErrorContext.get_all_context()
                )
    
    async def shutdown_service(self):
        """Shutdown the service."""
        if self._initialized:
            try:
                if hasattr(self, '_shutdown_impl'):
                    await self._shutdown_impl()
                self._initialized = False
            except Exception as e:
                logger.error(f"Failed to shutdown service {self._service_name}: {e}", exc_info=True)
                raise ServiceError(
                    service_name=self._service_name,
                    message=f"Failed to shutdown {self._service_name}: {e}",
                    context=ErrorContext.get_all_context()
                )