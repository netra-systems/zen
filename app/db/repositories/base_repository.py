"""Base Repository Pattern Implementation

Provides common CRUD operations for all entity repositories.
"""

from typing import Optional, List, Dict, Any, TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError

from app.logging_config import central_logger
from app.core.exceptions_database import NetraException

logger = central_logger.get_logger(__name__)

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository providing common CRUD operations."""
    
    def __init__(self, model_class: type, session: AsyncSession):
        self.model_class = model_class
        self.session = session
    
    def _create_entity(self, **kwargs) -> T:
        """Create entity instance."""
        return self.model_class(**kwargs)
    
    async def _add_and_flush_entity(self, entity: T) -> T:
        """Add entity to session and flush."""
        self.session.add(entity)
        await self.session.flush()
        return entity
    
    def _handle_create_error(self, e: SQLAlchemyError):
        """Handle entity creation error."""
        logger.error(f"Error creating {self.model_class.__name__}: {e}")
        raise NetraException(f"Failed to create {self.model_class.__name__}")
    
    async def create(self, **kwargs) -> T:
        """Create new entity."""
        try:
            entity = self._create_entity(**kwargs)
            return await self._add_and_flush_entity(entity)
        except SQLAlchemyError as e:
            self._handle_create_error(e)
    
    def _build_id_query(self, entity_id: str):
        """Build query for entity by ID."""
        return select(self.model_class).where(self.model_class.id == entity_id)
    
    def _handle_get_error(self, e: SQLAlchemyError, context: str):
        """Handle entity retrieval error."""
        logger.error(f"Error getting {self.model_class.__name__} {context}: {e}")
        return None
    
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        try:
            query = self._build_id_query(entity_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            return self._handle_get_error(e, "by ID")
    
    def _build_field_query(self, field_name: str, value: Any):
        """Build query for entity by field."""
        field = getattr(self.model_class, field_name)
        return select(self.model_class).where(field == value)
    
    async def get_by_field(self, field_name: str, value: Any) -> Optional[T]:
        """Get entity by specific field."""
        try:
            query = self._build_field_query(field_name, value)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except (SQLAlchemyError, AttributeError) as e:
            return self._handle_get_error(e, f"by {field_name}")
    
    def _build_list_query(self, limit: int, offset: int):
        """Build query for listing entities."""
        return select(self.model_class).limit(limit).offset(offset)
    
    def _handle_list_error(self, e: SQLAlchemyError) -> List[T]:
        """Handle entity listing error."""
        logger.error(f"Error listing {self.model_class.__name__}: {e}")
        return []
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """List all entities with pagination."""
        try:
            query = self._build_list_query(limit, offset)
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            return self._handle_list_error(e)
    
    def _build_update_query(self, entity_id: str, **kwargs):
        """Build update query for entity."""
        return (update(self.model_class)
                .where(self.model_class.id == entity_id)
                .values(**kwargs))
    
    def _handle_update_error(self, e: SQLAlchemyError) -> bool:
        """Handle entity update error."""
        logger.error(f"Error updating {self.model_class.__name__}: {e}")
        return False
    
    async def update_by_id(self, entity_id: str, **kwargs) -> bool:
        """Update entity by ID."""
        try:
            query = self._build_update_query(entity_id, **kwargs)
            result = await self.session.execute(query)
            return result.rowcount > 0
        except SQLAlchemyError as e:
            return self._handle_update_error(e)
    
    def _build_delete_query(self, entity_id: str):
        """Build delete query for entity."""
        return delete(self.model_class).where(self.model_class.id == entity_id)
    
    def _handle_delete_error(self, e: SQLAlchemyError) -> bool:
        """Handle entity deletion error."""
        logger.error(f"Error deleting {self.model_class.__name__}: {e}")
        return False
    
    async def delete_by_id(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        try:
            query = self._build_delete_query(entity_id)
            result = await self.session.execute(query)
            return result.rowcount > 0
        except SQLAlchemyError as e:
            return self._handle_delete_error(e)
    
    def _build_count_query(self):
        """Build count query for entities."""
        return select(self.model_class.id)
    
    def _handle_count_error(self, e: SQLAlchemyError) -> int:
        """Handle entity count error."""
        logger.error(f"Error counting {self.model_class.__name__}: {e}")
        return 0
    
    async def count(self) -> int:
        """Count total entities."""
        try:
            query = self._build_count_query()
            result = await self.session.execute(query)
            return len(list(result.scalars().all()))
        except SQLAlchemyError as e:
            return self._handle_count_error(e)