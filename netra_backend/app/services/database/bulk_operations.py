"""Bulk Operations Module

Handles bulk database operations for repositories.
"""

from typing import TypeVar, Generic, Type, List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.services.database.repository_errors import RepositoryErrorHandler
from netra_backend.app.services.database.session_manager import SessionManager
import uuid

logger = central_logger.get_logger(__name__)

T = TypeVar('T')


class BulkOperations(Generic[T]):
    """Handles bulk database operations"""
    
    def __init__(self, model: Type[T]):
        self.model = model
        self.error_handler = RepositoryErrorHandler(model.__name__)
        self.session_manager = SessionManager(model.__name__)
    
    async def execute_bulk_create_with_error_handling(self, session: AsyncSession, data: List[Dict[str, Any]]) -> List[T]:
        """Execute bulk create operation with comprehensive error handling."""
        try:
            return await self._create_bulk_entities(session, data)
        except IntegrityError as e:
            raise self.error_handler.handle_bulk_integrity_error(e, data)
        except SQLAlchemyError as e:
            raise self.error_handler.handle_bulk_sqlalchemy_error(e, data)
        except Exception as e:
            raise self.error_handler.handle_bulk_unexpected_error(e, data)

    async def bulk_create(self, data: List[Dict[str, Any]], db: Optional[AsyncSession] = None, session: Optional[AsyncSession] = None) -> List[T]:
        """Create multiple entities in bulk"""
        validated_session = self.session_manager.validate_session(db, session)
        return await self.execute_bulk_create_with_error_handling(validated_session, data)
    
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
    
    async def get_many(self, ids: List[str], db: Optional[AsyncSession] = None, session: Optional[AsyncSession] = None) -> List[T]:
        """Get multiple entities by their IDs"""
        validated_session = self.session_manager.validate_session(db, session)
        
        try:
            return await self._execute_get_many_query(validated_session, ids)
        except SQLAlchemyError as e:
            raise self.error_handler.handle_get_many_error(e, ids)
    
    async def _execute_get_many_query(self, session: AsyncSession, ids: List[str]) -> List[T]:
        """Execute query to get multiple entities."""
        result = await session.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        return list(result.scalars().all())