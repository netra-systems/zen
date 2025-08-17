"""Base Repository Pattern Implementation

Provides common CRUD operations for all entity repositories.
"""

from typing import Optional, List, Dict, Any, TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError

from app.logging_config import central_logger
from app.core.exceptions_db import NetraException

logger = central_logger.get_logger(__name__)

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository providing common CRUD operations."""
    
    def __init__(self, model_class: type, session: AsyncSession):
        self.model_class = model_class
        self.session = session
    
    async def create(self, **kwargs) -> T:
        """Create new entity."""
        try:
            entity = self.model_class(**kwargs)
            self.session.add(entity)
            await self.session.flush()
            return entity
        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise NetraException(f"Failed to create {self.model_class.__name__}")
    
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        try:
            result = await self.session.execute(
                select(self.model_class).where(self.model_class.id == entity_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model_class.__name__} by ID: {e}")
            return None
    
    async def get_by_field(self, field_name: str, value: Any) -> Optional[T]:
        """Get entity by specific field."""
        try:
            field = getattr(self.model_class, field_name)
            result = await self.session.execute(
                select(self.model_class).where(field == value)
            )
            return result.scalar_one_or_none()
        except (SQLAlchemyError, AttributeError) as e:
            logger.error(f"Error getting {self.model_class.__name__} by {field_name}: {e}")
            return None
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """List all entities with pagination."""
        try:
            result = await self.session.execute(
                select(self.model_class).limit(limit).offset(offset)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error listing {self.model_class.__name__}: {e}")
            return []
    
    async def update_by_id(self, entity_id: str, **kwargs) -> bool:
        """Update entity by ID."""
        try:
            result = await self.session.execute(
                update(self.model_class)
                .where(self.model_class.id == entity_id)
                .values(**kwargs)
            )
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model_class.__name__}: {e}")
            return False
    
    async def delete_by_id(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        try:
            result = await self.session.execute(
                delete(self.model_class).where(self.model_class.id == entity_id)
            )
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model_class.__name__}: {e}")
            return False
    
    async def count(self) -> int:
        """Count total entities."""
        try:
            result = await self.session.execute(
                select(self.model_class.id)
            )
            return len(list(result.scalars().all()))
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model_class.__name__}: {e}")
            return 0