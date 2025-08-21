"""Reference Repository Implementation

Handles all reference-related database operations.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from netra_backend.app.services.database.base_repository import BaseRepository
from netra_backend.app.db.models_postgres import Reference
from netra_backend.app.logging_config import central_logger
import time
import json

logger = central_logger.get_logger(__name__)

class ReferenceRepository(BaseRepository[Reference]):
    """Repository for Reference entities"""
    
    def __init__(self):
        super().__init__(Reference)
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[Reference]:
        """Find references associated with a user"""
        try:
            result = await db.execute(
                select(Reference).where(
                    Reference.metadata_.op('->>')('user_id') == user_id
                ).order_by(desc(Reference.created_at))
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error finding references for user {user_id}: {e}")
            return []
    
    async def create_reference(self,
                             db: AsyncSession,
                             reference_id: str,
                             reference_type: str,
                             content: str,
                             metadata: Optional[Dict[str, Any]] = None) -> Optional[Reference]:
        """Create a new reference"""
        return await self.create(
            db,
            id=reference_id,
            type=reference_type,
            content=content,
            created_at=int(time.time()),
            metadata=metadata or {}
        )
    
    async def find_by_type(self,
                         db: AsyncSession,
                         reference_type: str,
                         limit: int = 50) -> List[Reference]:
        """Find references by type"""
        try:
            result = await db.execute(
                select(Reference).where(
                    Reference.type == reference_type
                ).order_by(desc(Reference.created_at)).limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error finding references of type {reference_type}: {e}")
            return []
    
    async def find_by_metadata(self,
                              db: AsyncSession,
                              metadata_filters: Dict[str, Any],
                              limit: int = 50) -> List[Reference]:
        """Find references by metadata attributes"""
        try:
            query = select(Reference)
            
            for key, value in metadata_filters.items():
                if isinstance(value, str):
                    query = query.where(
                        Reference.metadata.op('->>')( key) == value
                    )
                else:
                    query = query.where(
                        Reference.metadata.op('->')( key) == json.dumps(value)
                    )
            
            query = query.order_by(desc(Reference.created_at)).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error finding references by metadata: {e}")
            return []
    
    async def search_content(self,
                           db: AsyncSession,
                           search_term: str,
                           limit: int = 50) -> List[Reference]:
        """Search references by content"""
        try:
            result = await db.execute(
                select(Reference).where(
                    Reference.content.ilike(f"%{search_term}%")
                ).order_by(desc(Reference.created_at)).limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error searching references: {e}")
            return []
    
    async def cleanup_old_references(self,
                                   db: AsyncSession,
                                   days_old: int = 30) -> int:
        """Delete references older than specified days"""
        try:
            cutoff_timestamp = int(time.time()) - (days_old * 86400)
            
            result = await db.execute(
                select(Reference).where(
                    Reference.created_at < cutoff_timestamp
                )
            )
            old_references = result.scalars().all()
            
            deleted_count = 0
            for ref in old_references:
                await db.delete(ref)
                deleted_count += 1
            
            await db.commit()
            logger.info(f"Deleted {deleted_count} old references")
            return deleted_count
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error cleaning up old references: {e}")
            return 0