"""Base CRUD Operations Module

Core CRUD operations for database repositories.
"""

from typing import TypeVar, Generic, Optional, List, Dict, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.logging_config import central_logger
from app.core.exceptions import RecordNotFoundError, NetraException
from app.services.database.repository_errors import RepositoryErrorHandler
from app.services.database.session_manager import SessionManager
from app.services.database.bulk_operations import BulkOperations
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, UTC

logger = central_logger.get_logger(__name__)

T = TypeVar('T')


class BaseCRUD(Generic[T], ABC):
    """Base CRUD operations for repositories"""
    
    def __init__(self, model: Type[T]):
        self.model = model
        self.error_handler = RepositoryErrorHandler(model.__name__)
        self.session_manager = SessionManager(model.__name__)
        self.bulk_ops = BulkOperations[T](model)
        self._session: Optional[AsyncSession] = None
    
    async def _execute_create_with_error_handling(self, session: AsyncSession, kwargs: Dict[str, Any]) -> T:
        """Execute create operation with comprehensive error handling."""
        try:
            return await self._create_entity(session, kwargs)
        except IntegrityError as e:
            raise self.error_handler.handle_integrity_error(e, kwargs)
        except SQLAlchemyError as e:
            raise self.error_handler.handle_sqlalchemy_error(e, kwargs)
        except Exception as e:
            raise self.error_handler.handle_unexpected_error(e, kwargs)

    async def create(self, db: Optional[AsyncSession] = None, **kwargs) -> T:
        """Create a new entity"""
        session = self.session_manager.validate_session(db, self._session)
        return await self._execute_create_with_error_handling(session, kwargs)
    
    async def _create_entity(self, session: AsyncSession, kwargs: Dict[str, Any]) -> T:
        """Create and persist entity to database."""
        if 'id' not in kwargs and hasattr(self.model, 'id'):
            kwargs['id'] = str(uuid.uuid4())
        
        entity = self.model(**kwargs)
        session.add(entity)
        await session.flush()  # Flush to get the ID but don't commit
        logger.info(f"Created {self.model.__name__} with id: {kwargs.get('id')}")
        return entity
    
    async def get_by_id(self, db: Optional[AsyncSession], entity_id: str) -> Optional[T]:
        """Get entity by ID"""
        session = self.session_manager.validate_session_with_id(db, entity_id, self._session)
        
        try:
            return await self._execute_get_by_id_query(session, entity_id)
        except SQLAlchemyError as e:
            raise self.error_handler.handle_get_by_id_error(e, entity_id)
    
    async def _execute_get_by_id_query(self, session: AsyncSession, entity_id: str) -> Optional[T]:
        """Execute get by ID query."""
        result = await session.execute(
            select(self.model).where(self.model.id == entity_id)
        )
        return result.scalar_one_or_none()
    
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
            raise self.error_handler.handle_get_all_error(e, filters)
    
    def _build_filtered_query(self, filters: Optional[Dict[str, Any]]):
        """Build query with optional filters."""
        query = select(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        return query
    
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
            raise self.error_handler.handle_update_error(e, entity_id, kwargs)
    
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
    
    async def delete(self, db: AsyncSession, entity_id: str) -> bool:
        """Delete an entity"""
        try:
            entity = await self._get_entity_for_delete(db, entity_id)
            await self._execute_delete(db, entity, entity_id)
            return True
        except NetraException:
            raise
        except SQLAlchemyError as e:
            raise self.error_handler.handle_delete_error(e, entity_id)
    
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
    
    async def count(self, db: AsyncSession, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filtering"""
        try:
            query = self._build_count_query(filters)
            result = await db.execute(query)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            raise self.error_handler.handle_count_error(e, filters)
    
    def _build_count_query(self, filters: Optional[Dict[str, Any]]):
        """Build count query with optional filters."""
        query = select(func.count()).select_from(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        return query
    
    async def exists(self, db: AsyncSession, entity_id: str) -> bool:
        """Check if entity exists"""
        try:
            query = select(func.count()).select_from(self.model).where(self.model.id == entity_id)
            result = await db.execute(query)
            return result.scalar() > 0
        except SQLAlchemyError as e:
            raise self.error_handler.handle_exists_error(e, entity_id)
    
    async def soft_delete(self, entity_id: str, db: Optional[AsyncSession] = None) -> bool:
        """Soft delete an entity (if model supports it)"""
        session = self.session_manager.validate_session_with_id(db, entity_id, self._session)
        
        try:
            entity = await self._get_entity_for_soft_delete(session, entity_id)
            return await self._execute_soft_delete(session, entity, entity_id)
        except NetraException:
            raise
        except SQLAlchemyError as e:
            raise self.error_handler.handle_soft_delete_error(e, entity_id)
    
    async def _get_entity_for_soft_delete(self, session: AsyncSession, entity_id: str) -> T:
        """Get entity for soft delete operation."""
        entity = await self.get_by_id(session, entity_id)
        if not entity:
            raise RecordNotFoundError(self.model.__name__, entity_id)
        return entity
    
    async def _execute_soft_delete(self, session: AsyncSession, entity: T, entity_id: str) -> bool:
        """Execute soft delete operation."""
        if not hasattr(entity, 'deleted_at'):
            raise self.error_handler.create_soft_delete_not_supported_error(entity_id)
        
        setattr(entity, 'deleted_at', datetime.now(UTC))
        await session.flush()  # Flush changes but don't commit
        logger.info(f"Soft deleted {self.model.__name__} with id: {entity_id}")
        return True
    
    # Delegate bulk operations to the bulk operations module
    async def bulk_create(self, data: List[Dict[str, Any]], db: Optional[AsyncSession] = None) -> List[T]:
        """Create multiple entities in bulk"""
        return await self.bulk_ops.bulk_create(data, db, self._session)
    
    async def get_many(self, ids: List[str], db: Optional[AsyncSession] = None) -> List[T]:
        """Get multiple entities by their IDs"""
        return await self.bulk_ops.get_many(ids, db, self._session)
    
    @abstractmethod
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[T]:
        """Find entities by user - must be implemented by subclasses"""
        pass