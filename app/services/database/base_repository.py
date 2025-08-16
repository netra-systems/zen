"""Base Repository Pattern Implementation

Provides abstract base class for all repositories with common CRUD operations.
"""

from typing import TypeVar, Generic, Optional, List, Dict, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.logging_config import central_logger
from app.core.exceptions import (
    DatabaseError, RecordNotFoundError, ConstraintViolationError,
    NetraException, ErrorCode, ErrorSeverity
)
import uuid
from abc import ABC, abstractmethod

logger = central_logger.get_logger(__name__)

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    """Abstract base repository with common database operations"""
    
    def __init__(self, model: Type[T]):
        self.model = model
        self._session: Optional[AsyncSession] = None
    
    async def _execute_create_with_error_handling(self, session: AsyncSession, kwargs: Dict[str, Any]) -> T:
        """Execute create operation with comprehensive error handling."""
        try:
            return await self._create_entity(session, kwargs)
        except IntegrityError as e:
            raise self._handle_integrity_error(e, kwargs)
        except SQLAlchemyError as e:
            raise self._handle_sqlalchemy_error(e, kwargs)
        except Exception as e:
            raise self._handle_unexpected_error(e, kwargs)

    async def create(self, db: Optional[AsyncSession] = None, **kwargs) -> T:
        """Create a new entity"""
        session = self._validate_session(db)
        return await self._execute_create_with_error_handling(session, kwargs)
    
    def _validate_session(self, db: Optional[AsyncSession]) -> AsyncSession:
        """Validate and return database session."""
        session = db or self._session
        if not session:
            raise DatabaseError(
                message="No database session available",
                context={"repository": self.model.__name__}
            )
        return session
    
    async def _create_entity(self, session: AsyncSession, kwargs: Dict[str, Any]) -> T:
        """Create and persist entity to database."""
        if 'id' not in kwargs and hasattr(self.model, 'id'):
            kwargs['id'] = str(uuid.uuid4())
        
        entity = self.model(**kwargs)
        session.add(entity)
        await session.flush()  # Flush to get the ID but don't commit
        logger.info(f"Created {self.model.__name__} with id: {kwargs.get('id')}")
        return entity
    
    def _handle_integrity_error(self, e: IntegrityError, kwargs: Dict[str, Any]) -> ConstraintViolationError:
        """Handle integrity constraint violations."""
        logger.error(f"Integrity constraint violation creating {self.model.__name__}: {e}")
        return ConstraintViolationError(
            constraint=str(e.orig) if hasattr(e, 'orig') else "unknown",
            context={"repository": self.model.__name__, "data": kwargs}
        )
    
    def _handle_sqlalchemy_error(self, e: SQLAlchemyError, kwargs: Dict[str, Any]) -> DatabaseError:
        """Handle SQLAlchemy database errors."""
        logger.error(f"Database error creating {self.model.__name__}: {e}")
        return DatabaseError(
            message=f"Failed to create {self.model.__name__}",
            context={"repository": self.model.__name__, "data": kwargs, "error": str(e)}
        )
    
    def _handle_unexpected_error(self, e: Exception, kwargs: Dict[str, Any]) -> DatabaseError:
        """Handle unexpected errors during creation."""
        logger.error(f"Unexpected error creating {self.model.__name__}: {e}")
        return DatabaseError(
            message=f"Unexpected error creating {self.model.__name__}",
            context={"repository": self.model.__name__, "data": kwargs, "error": str(e)}
        )
    
    async def get_by_id(self, db: Optional[AsyncSession], entity_id: str) -> Optional[T]:
        """Get entity by ID"""
        session = self._validate_session_with_id(db, entity_id)
        
        try:
            return await self._execute_get_by_id_query(session, entity_id)
        except SQLAlchemyError as e:
            raise self._handle_get_by_id_error(e, entity_id)
    
    def _validate_session_with_id(self, db: Optional[AsyncSession], entity_id: str) -> AsyncSession:
        """Validate session for get by ID operation."""
        session = db or self._session
        if not session:
            raise DatabaseError(
                message="No database session available",
                context={"repository": self.model.__name__, "entity_id": entity_id}
            )
        return session
    
    async def _execute_get_by_id_query(self, session: AsyncSession, entity_id: str) -> Optional[T]:
        """Execute get by ID query."""
        result = await session.execute(
            select(self.model).where(self.model.id == entity_id)
        )
        return result.scalar_one_or_none()
    
    def _handle_get_by_id_error(self, e: SQLAlchemyError, entity_id: str) -> DatabaseError:
        """Handle get by ID query errors."""
        logger.error(f"Error fetching {self.model.__name__} by id {entity_id}: {e}")
        return DatabaseError(
            message=f"Failed to fetch {self.model.__name__} by ID",
            context={"repository": self.model.__name__, "entity_id": entity_id, "error": str(e)}
        )
    
    async def get(self, db: Optional[AsyncSession], entity_id: str) -> Optional[T]:
        """Alias for get_by_id for backward compatibility"""
        return await self.get_by_id(db, entity_id)
    
    async def _execute_get_all_query(self, db: AsyncSession, filters: Optional[Dict[str, Any]], 
                                     limit: int, offset: int) -> List[T]:
        """Execute get all query with filters and pagination."""
        query = self._build_filtered_query(filters)
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_all(self, db: AsyncSession, 
                      filters: Optional[Dict[str, Any]] = None,
                      limit: int = 100, 
                      offset: int = 0) -> List[T]:
        """Get all entities with optional filtering"""
        try:
            return await self._execute_get_all_query(db, filters, limit, offset)
        except SQLAlchemyError as e:
            raise self._handle_get_all_error(e, filters)
    
    def _build_filtered_query(self, filters: Optional[Dict[str, Any]]):
        """Build query with optional filters."""
        query = select(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        return query
    
    def _handle_get_all_error(self, e: SQLAlchemyError, filters: Optional[Dict[str, Any]]) -> DatabaseError:
        """Handle get all query errors."""
        logger.error(f"Error fetching {self.model.__name__} list: {e}")
        return DatabaseError(
            message=f"Failed to fetch {self.model.__name__} list",
            context={"repository": self.model.__name__, "filters": filters, "error": str(e)}
        )
    
    async def _execute_update_operation(self, db: AsyncSession, entity_id: str, kwargs: Dict[str, Any]) -> T:
        """Execute the core update operation."""
        entity = await self._get_entity_for_update(db, entity_id)
        self._apply_updates(entity, kwargs)
        await db.flush()  # Flush changes but don't commit
        logger.info(f"Updated {self.model.__name__} with id: {entity_id}")
        return entity

    async def update(self, db: AsyncSession, entity_id: str, **kwargs) -> Optional[T]:
        """Update an entity"""
        try:
            return await self._execute_update_operation(db, entity_id, kwargs)
        except NetraException:
            raise
        except SQLAlchemyError as e:
            raise self._handle_update_error(e, entity_id, kwargs)
    
    async def _get_entity_for_update(self, db: AsyncSession, entity_id: str) -> T:
        """Get entity for update operation."""
        entity = await self.get_by_id(db, entity_id)
        if not entity:
            raise RecordNotFoundError(self.model.__name__, entity_id)
        return entity
    
    def _apply_updates(self, entity: T, kwargs: Dict[str, Any]) -> None:
        """Apply update values to entity."""
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
    
    def _handle_update_error(self, e: SQLAlchemyError, entity_id: str, kwargs: Dict[str, Any]) -> DatabaseError:
        """Handle update operation errors."""
        logger.error(f"Error updating {self.model.__name__} {entity_id}: {e}")
        return DatabaseError(
            message=f"Failed to update {self.model.__name__}",
            context={"repository": self.model.__name__, "entity_id": entity_id, "data": kwargs, "error": str(e)}
        )
    
    async def delete(self, db: AsyncSession, entity_id: str) -> bool:
        """Delete an entity"""
        try:
            entity = await self._get_entity_for_delete(db, entity_id)
            await self._execute_delete(db, entity, entity_id)
            return True
        except NetraException:
            raise
        except SQLAlchemyError as e:
            raise self._handle_delete_error(e, entity_id)
    
    async def _get_entity_for_delete(self, db: AsyncSession, entity_id: str) -> T:
        """Get entity for delete operation."""
        entity = await self.get_by_id(db, entity_id)
        if not entity:
            raise RecordNotFoundError(self.model.__name__, entity_id)
        return entity
    
    async def _execute_delete(self, db: AsyncSession, entity: T, entity_id: str) -> None:
        """Execute delete operation."""
        await db.delete(entity)
        await db.flush()  # Flush changes but don't commit
        logger.info(f"Deleted {self.model.__name__} with id: {entity_id}")
    
    def _handle_delete_error(self, e: SQLAlchemyError, entity_id: str) -> DatabaseError:
        """Handle delete operation errors."""
        logger.error(f"Error deleting {self.model.__name__} {entity_id}: {e}")
        return DatabaseError(
            message=f"Failed to delete {self.model.__name__}",
            context={"repository": self.model.__name__, "entity_id": entity_id, "error": str(e)}
        )
    
    async def count(self, db: AsyncSession, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filtering"""
        try:
            query = self._build_count_query(filters)
            result = await db.execute(query)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            raise self._handle_count_error(e, filters)
    
    def _build_count_query(self, filters: Optional[Dict[str, Any]]):
        """Build count query with optional filters."""
        query = select(func.count()).select_from(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        return query
    
    def _handle_count_error(self, e: SQLAlchemyError, filters: Optional[Dict[str, Any]]) -> DatabaseError:
        """Handle count operation errors."""
        logger.error(f"Error counting {self.model.__name__}: {e}")
        return DatabaseError(
            message=f"Failed to count {self.model.__name__}",
            context={"repository": self.model.__name__, "filters": filters, "error": str(e)}
        )
    
    async def exists(self, db: AsyncSession, entity_id: str) -> bool:
        """Check if entity exists"""
        try:
            query = select(func.count()).select_from(self.model).where(self.model.id == entity_id)
            result = await db.execute(query)
            return result.scalar() > 0
        except SQLAlchemyError as e:
            raise self._handle_exists_error(e, entity_id)
    
    def _handle_exists_error(self, e: SQLAlchemyError, entity_id: str) -> DatabaseError:
        """Handle exists operation errors."""
        logger.error(f"Error checking existence of {self.model.__name__} {entity_id}: {e}")
        return DatabaseError(
            message=f"Failed to check existence of {self.model.__name__}",
            context={"repository": self.model.__name__, "entity_id": entity_id, "error": str(e)}
        )
    
    async def _execute_bulk_create_with_error_handling(self, session: AsyncSession, data: List[Dict[str, Any]]) -> List[T]:
        """Execute bulk create operation with comprehensive error handling."""
        try:
            return await self._create_bulk_entities(session, data)
        except IntegrityError as e:
            raise self._handle_bulk_integrity_error(e, data)
        except SQLAlchemyError as e:
            raise self._handle_bulk_sqlalchemy_error(e, data)
        except Exception as e:
            raise self._handle_bulk_unexpected_error(e, data)

    async def bulk_create(self, data: List[Dict[str, Any]], db: Optional[AsyncSession] = None) -> List[T]:
        """Create multiple entities in bulk"""
        session = self._validate_session(db)
        return await self._execute_bulk_create_with_error_handling(session, data)
    
    def _create_entity_instances(self, session: AsyncSession, data: List[Dict[str, Any]]) -> List[T]:
        """Create entity instances and add to session."""
        entities = []
        for item in data:
            if 'id' not in item and hasattr(self.model, 'id'):
                item['id'] = str(uuid.uuid4())
            entity = self.model(**item)
            session.add(entity)
            entities.append(entity)
        return entities

    async def _create_bulk_entities(self, session: AsyncSession, data: List[Dict[str, Any]]) -> List[T]:
        """Create and persist multiple entities."""
        entities = self._create_entity_instances(session, data)
        await session.flush()  # Flush to get IDs but don't commit
        logger.info(f"Bulk created {len(entities)} {self.model.__name__} entities")
        return entities
    
    def _handle_bulk_integrity_error(self, e: IntegrityError, data: List[Dict[str, Any]]) -> ConstraintViolationError:
        """Handle bulk create integrity errors."""
        logger.error(f"Integrity constraint violation bulk creating {self.model.__name__}: {e}")
        return ConstraintViolationError(
            constraint=str(e.orig) if hasattr(e, 'orig') else "unknown",
            context={"repository": self.model.__name__, "data_count": len(data)}
        )
    
    def _handle_bulk_sqlalchemy_error(self, e: SQLAlchemyError, data: List[Dict[str, Any]]) -> DatabaseError:
        """Handle bulk create SQLAlchemy errors."""
        logger.error(f"Database error bulk creating {self.model.__name__}: {e}")
        return DatabaseError(
            message=f"Failed to bulk create {self.model.__name__}",
            context={"repository": self.model.__name__, "data_count": len(data), "error": str(e)}
        )
    
    def _handle_bulk_unexpected_error(self, e: Exception, data: List[Dict[str, Any]]) -> DatabaseError:
        """Handle bulk create unexpected errors."""
        logger.error(f"Unexpected error bulk creating {self.model.__name__}: {e}")
        return DatabaseError(
            message=f"Unexpected error bulk creating {self.model.__name__}",
            context={"repository": self.model.__name__, "data_count": len(data), "error": str(e)}
        )
    
    async def get_many(self, ids: List[str], db: Optional[AsyncSession] = None) -> List[T]:
        """Get multiple entities by their IDs"""
        session = self._validate_session(db)
        
        try:
            return await self._execute_get_many_query(session, ids)
        except SQLAlchemyError as e:
            raise self._handle_get_many_error(e, ids)
    
    async def _execute_get_many_query(self, session: AsyncSession, ids: List[str]) -> List[T]:
        """Execute query to get multiple entities."""
        result = await session.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        return list(result.scalars().all())
    
    def _handle_get_many_error(self, e: SQLAlchemyError, ids: List[str]) -> DatabaseError:
        """Handle get many operation errors."""
        logger.error(f"Error fetching multiple {self.model.__name__}: {e}")
        return DatabaseError(
            message=f"Failed to fetch multiple {self.model.__name__}",
            context={"repository": self.model.__name__, "ids": ids, "error": str(e)}
        )
    
    async def soft_delete(self, entity_id: str, db: Optional[AsyncSession] = None) -> bool:
        """Soft delete an entity (if model supports it)"""
        session = self._validate_session_with_id(db, entity_id)
        
        try:
            entity = await self._get_entity_for_soft_delete(session, entity_id)
            return await self._execute_soft_delete(session, entity, entity_id)
        except NetraException:
            raise
        except SQLAlchemyError as e:
            raise self._handle_soft_delete_error(e, entity_id)
    
    async def _get_entity_for_soft_delete(self, session: AsyncSession, entity_id: str) -> T:
        """Get entity for soft delete operation."""
        entity = await self.get_by_id(session, entity_id)
        if not entity:
            raise RecordNotFoundError(self.model.__name__, entity_id)
        return entity
    
    async def _execute_soft_delete(self, session: AsyncSession, entity: T, entity_id: str) -> bool:
        """Execute soft delete operation."""
        if not hasattr(entity, 'deleted_at'):
            raise self._create_soft_delete_not_supported_error(entity_id)
        
        from datetime import datetime, UTC
        setattr(entity, 'deleted_at', datetime.now(UTC))
        await session.flush()  # Flush changes but don't commit
        logger.info(f"Soft deleted {self.model.__name__} with id: {entity_id}")
        return True
    
    def _create_soft_delete_not_supported_error(self, entity_id: str) -> DatabaseError:
        """Create error for unsupported soft delete."""
        logger.warning(f"{self.model.__name__} does not support soft delete")
        return DatabaseError(
            message=f"{self.model.__name__} does not support soft delete",
            context={"repository": self.model.__name__, "entity_id": entity_id}
        )
    
    def _handle_soft_delete_error(self, e: SQLAlchemyError, entity_id: str) -> DatabaseError:
        """Handle soft delete operation errors."""
        logger.error(f"Error soft deleting {self.model.__name__} {entity_id}: {e}")
        return DatabaseError(
            message=f"Failed to soft delete {self.model.__name__}",
            context={"repository": self.model.__name__, "entity_id": entity_id, "error": str(e)}
        )
    
    @abstractmethod
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[T]:
        """Find entities by user - must be implemented by subclasses"""
        pass