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
    
    async def create(self, db: Optional[AsyncSession] = None, **kwargs) -> T:
        """Create a new entity"""
        session = db or self._session
        if not session:
            raise DatabaseError(
                message="No database session available",
                context={"repository": self.model.__name__}
            )
        
        try:
            if 'id' not in kwargs and hasattr(self.model, 'id'):
                kwargs['id'] = str(uuid.uuid4())
            
            entity = self.model(**kwargs)
            session.add(entity)
            # Don't commit here - let UnitOfWork handle transactions
            await session.flush()  # Flush to get the ID but don't commit
            logger.info(f"Created {self.model.__name__} with id: {kwargs.get('id')}")
            return entity
            
        except IntegrityError as e:
            logger.error(f"Integrity constraint violation creating {self.model.__name__}: {e}")
            raise ConstraintViolationError(
                constraint=str(e.orig) if hasattr(e, 'orig') else "unknown",
                context={"repository": self.model.__name__, "data": kwargs}
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error creating {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Failed to create {self.model.__name__}",
                context={"repository": self.model.__name__, "data": kwargs, "error": str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected error creating {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Unexpected error creating {self.model.__name__}",
                context={"repository": self.model.__name__, "data": kwargs, "error": str(e)}
            )
    
    async def get_by_id(self, db: Optional[AsyncSession], entity_id: str) -> Optional[T]:
        """Get entity by ID"""
        session = db or self._session
        if not session:
            raise DatabaseError(
                message="No database session available",
                context={"repository": self.model.__name__, "entity_id": entity_id}
            )
        
        try:
            result = await session.execute(
                select(self.model).where(self.model.id == entity_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching {self.model.__name__} by id {entity_id}: {e}")
            raise DatabaseError(
                message=f"Failed to fetch {self.model.__name__} by ID",
                context={"repository": self.model.__name__, "entity_id": entity_id, "error": str(e)}
            )
    
    async def get(self, db: Optional[AsyncSession], entity_id: str) -> Optional[T]:
        """Alias for get_by_id for backward compatibility"""
        return await self.get_by_id(db, entity_id)
    
    async def get_all(self, db: AsyncSession, 
                      filters: Optional[Dict[str, Any]] = None,
                      limit: int = 100, 
                      offset: int = 0) -> List[T]:
        """Get all entities with optional filtering"""
        try:
            query = select(self.model)
            
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)
            
            query = query.limit(limit).offset(offset)
            result = await db.execute(query)
            return list(result.scalars().all())
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching {self.model.__name__} list: {e}")
            raise DatabaseError(
                message=f"Failed to fetch {self.model.__name__} list",
                context={"repository": self.model.__name__, "filters": filters, "error": str(e)}
            )
    
    async def update(self, db: AsyncSession, entity_id: str, **kwargs) -> Optional[T]:
        """Update an entity"""
        try:
            entity = await self.get_by_id(db, entity_id)
            if not entity:
                raise RecordNotFoundError(self.model.__name__, entity_id)
            
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            
            # Don't commit here - let UnitOfWork handle transactions
            await db.flush()  # Flush changes but don't commit
            logger.info(f"Updated {self.model.__name__} with id: {entity_id}")
            return entity
            
        except NetraException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model.__name__} {entity_id}: {e}")
            raise DatabaseError(
                message=f"Failed to update {self.model.__name__}",
                context={"repository": self.model.__name__, "entity_id": entity_id, "data": kwargs, "error": str(e)}
            )
    
    async def delete(self, db: AsyncSession, entity_id: str) -> bool:
        """Delete an entity"""
        try:
            entity = await self.get_by_id(db, entity_id)
            if not entity:
                raise RecordNotFoundError(self.model.__name__, entity_id)
            
            await db.delete(entity)
            # Don't commit here - let UnitOfWork handle transactions
            await db.flush()  # Flush changes but don't commit
            logger.info(f"Deleted {self.model.__name__} with id: {entity_id}")
            return True
            
        except NetraException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model.__name__} {entity_id}: {e}")
            raise DatabaseError(
                message=f"Failed to delete {self.model.__name__}",
                context={"repository": self.model.__name__, "entity_id": entity_id, "error": str(e)}
            )
    
    async def count(self, db: AsyncSession, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filtering"""
        try:
            query = select(func.count()).select_from(self.model)
            
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)
            
            result = await db.execute(query)
            return result.scalar() or 0
            
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise DatabaseError(
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
            logger.error(f"Error checking existence of {self.model.__name__} {entity_id}: {e}")
            raise DatabaseError(
                message=f"Failed to check existence of {self.model.__name__}",
                context={"repository": self.model.__name__, "entity_id": entity_id, "error": str(e)}
            )
    
    async def bulk_create(self, data: List[Dict[str, Any]], db: Optional[AsyncSession] = None) -> List[T]:
        """Create multiple entities in bulk"""
        session = db or self._session
        if not session:
            raise DatabaseError(
                message="No database session available",
                context={"repository": self.model.__name__}
            )
        
        entities = []
        try:
            for item in data:
                if 'id' not in item and hasattr(self.model, 'id'):
                    item['id'] = str(uuid.uuid4())
                entity = self.model(**item)
                session.add(entity)
                entities.append(entity)
            
            # Don't commit here - let UnitOfWork handle transactions
            await session.flush()  # Flush to get IDs but don't commit
            logger.info(f"Bulk created {len(entities)} {self.model.__name__} entities")
            return entities
            
        except IntegrityError as e:
            logger.error(f"Integrity constraint violation bulk creating {self.model.__name__}: {e}")
            raise ConstraintViolationError(
                constraint=str(e.orig) if hasattr(e, 'orig') else "unknown",
                context={"repository": self.model.__name__, "data_count": len(data)}
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error bulk creating {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Failed to bulk create {self.model.__name__}",
                context={"repository": self.model.__name__, "data_count": len(data), "error": str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected error bulk creating {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Unexpected error bulk creating {self.model.__name__}",
                context={"repository": self.model.__name__, "data_count": len(data), "error": str(e)}
            )
    
    async def get_many(self, ids: List[str], db: Optional[AsyncSession] = None) -> List[T]:
        """Get multiple entities by their IDs"""
        session = db or self._session
        if not session:
            raise DatabaseError(
                message="No database session available",
                context={"repository": self.model.__name__}
            )
        
        try:
            result = await session.execute(
                select(self.model).where(self.model.id.in_(ids))
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching multiple {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Failed to fetch multiple {self.model.__name__}",
                context={"repository": self.model.__name__, "ids": ids, "error": str(e)}
            )
    
    async def soft_delete(self, entity_id: str, db: Optional[AsyncSession] = None) -> bool:
        """Soft delete an entity (if model supports it)"""
        session = db or self._session
        if not session:
            raise DatabaseError(
                message="No database session available",
                context={"repository": self.model.__name__, "entity_id": entity_id}
            )
        
        try:
            entity = await self.get_by_id(session, entity_id)
            if not entity:
                raise RecordNotFoundError(self.model.__name__, entity_id)
            
            # Check if model supports soft delete
            if hasattr(entity, 'deleted_at'):
                from datetime import datetime, UTC
                setattr(entity, 'deleted_at', datetime.now(UTC))
                # Don't commit here - let UnitOfWork handle transactions
                await session.flush()  # Flush changes but don't commit
                logger.info(f"Soft deleted {self.model.__name__} with id: {entity_id}")
                return True
            else:
                logger.warning(f"{self.model.__name__} does not support soft delete")
                raise DatabaseError(
                    message=f"{self.model.__name__} does not support soft delete",
                    context={"repository": self.model.__name__, "entity_id": entity_id}
                )
                
        except NetraException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error soft deleting {self.model.__name__} {entity_id}: {e}")
            raise DatabaseError(
                message=f"Failed to soft delete {self.model.__name__}",
                context={"repository": self.model.__name__, "entity_id": entity_id, "error": str(e)}
            )
    
    @abstractmethod
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[T]:
        """Find entities by user - must be implemented by subclasses"""
        pass