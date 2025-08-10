"""Base Repository Pattern Implementation

Provides abstract base class for all repositories with common CRUD operations.
"""

from typing import TypeVar, Generic, Optional, List, Dict, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.logging_config import central_logger
import uuid
from abc import ABC, abstractmethod

logger = central_logger.get_logger(__name__)

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    """Abstract base repository with common database operations"""
    
    def __init__(self, model: Type[T]):
        self.model = model
    
    async def create(self, db: AsyncSession, **kwargs) -> Optional[T]:
        """Create a new entity"""
        try:
            if 'id' not in kwargs and hasattr(self.model, 'id'):
                kwargs['id'] = str(uuid.uuid4())
            
            entity = self.model(**kwargs)
            db.add(entity)
            await db.commit()
            await db.refresh(entity)
            logger.info(f"Created {self.model.__name__} with id: {kwargs.get('id')}")
            return entity
            
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            return None
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error creating {self.model.__name__}: {e}")
            return None
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error creating {self.model.__name__}: {e}")
            return None
    
    async def get_by_id(self, db: AsyncSession, entity_id: str) -> Optional[T]:
        """Get entity by ID"""
        try:
            result = await db.execute(
                select(self.model).where(self.model.id == entity_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching {self.model.__name__} by id {entity_id}: {e}")
            return None
    
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
            return []
    
    async def update(self, db: AsyncSession, entity_id: str, **kwargs) -> Optional[T]:
        """Update an entity"""
        try:
            entity = await self.get_by_id(db, entity_id)
            if not entity:
                return None
            
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            
            await db.commit()
            await db.refresh(entity)
            logger.info(f"Updated {self.model.__name__} with id: {entity_id}")
            return entity
            
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Error updating {self.model.__name__} {entity_id}: {e}")
            return None
    
    async def delete(self, db: AsyncSession, entity_id: str) -> bool:
        """Delete an entity"""
        try:
            entity = await self.get_by_id(db, entity_id)
            if not entity:
                return False
            
            await db.delete(entity)
            await db.commit()
            logger.info(f"Deleted {self.model.__name__} with id: {entity_id}")
            return True
            
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Error deleting {self.model.__name__} {entity_id}: {e}")
            return False
    
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
            return 0
    
    async def exists(self, db: AsyncSession, entity_id: str) -> bool:
        """Check if entity exists"""
        try:
            query = select(func.count()).select_from(self.model).where(self.model.id == entity_id)
            result = await db.execute(query)
            return result.scalar() > 0
        except SQLAlchemyError as e:
            logger.error(f"Error checking existence of {self.model.__name__} {entity_id}: {e}")
            return False
    
    @abstractmethod
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[T]:
        """Find entities by user - must be implemented by subclasses"""
        pass