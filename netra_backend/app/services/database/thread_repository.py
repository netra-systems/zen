"""Thread Repository Implementation

Handles all thread-related database operations.
"""

import time
import uuid
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import Thread
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.base_repository import BaseRepository

logger = central_logger.get_logger(__name__)

class ThreadRepository(BaseRepository[Thread]):
    """Repository for Thread entities"""
    
    def __init__(self):
        super().__init__(Thread)
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[Thread]:
        """Find all threads for a user using JSONB query.
        
        SSOT: This is the canonical way to query threads by user_id.
        No fallback queries or Python filtering - database query must work correctly.
        """
        try:
            # Ensure user_id is string format for consistent comparison
            user_id_str = str(user_id).strip()
            logger.debug(f"Finding threads for user_id: {user_id_str}")
            
            # Query using JSONB operators - this is the SSOT pattern
            result = await db.execute(
                select(Thread).where(
                    Thread.metadata_.op('->>')('user_id') == user_id_str
                ).order_by(Thread.created_at.desc())
            )
            threads = list(result.scalars().all())
            logger.info(f"Found {len(threads)} threads for user {user_id_str}")
            return threads
        except Exception as e:
            logger.error(f"Error finding threads for user {user_id}: {e}", exc_info=True)
            # Raise the error - no fallback, let caller handle it
            raise
    
    async def get_or_create_for_user(self, db: AsyncSession, user_id: str) -> Optional[Thread]:
        """Get existing thread for user or create new one
        
        First checks for existing active threads for the user.
        If none exist, creates a new thread using UnifiedIDManager for consistent ID generation.
        """
        # First check if user has any existing active threads
        existing_thread = await self.get_active_thread(db, user_id)
        if existing_thread:
            return existing_thread
        
        # Create new thread using UnifiedIDManager for SSOT compliance
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
        # UnifiedIDManager.generate_thread_id() returns unprefixed ID to prevent double prefixing
        base_id = UnifiedIDManager.generate_thread_id()
        thread_id = f"thread_{base_id}"
        
        return await self.create(
            db=db,
            id=thread_id,
            object="thread",
            created_at=int(time.time()),
            metadata_={"user_id": user_id}
        )
    
    async def get_active_thread(self, db: AsyncSession, user_id: str) -> Optional[Thread]:
        """Get the most recent active thread for a user"""
        try:
            result = await db.execute(
                select(Thread).where(
                    and_(
                        Thread.metadata_.op('->>')('user_id') == user_id,
                        Thread.metadata_.op('->>')('status') != 'archived'
                    )
                ).order_by(Thread.created_at.desc()).limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting active thread for user {user_id}: {e}")
            return None
    
    async def archive_thread(self, db: AsyncSession, thread_id: str) -> bool:
        """Archive a thread"""
        thread = await self.get_by_id(db, thread_id)
        if not thread:
            return False
        
        if not thread.metadata_:
            thread.metadata_ = {}
        
        thread.metadata_['status'] = 'archived'
        thread.metadata_['archived_at'] = int(time.time())
        
        try:
            await db.commit()
            logger.info(f"Archived thread {thread_id}")
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"Error archiving thread {thread_id}: {e}")
            return False
    
    async def get_active_threads(self, db: AsyncSession, user_id: str) -> List[Thread]:
        """Get all active (non-soft-deleted) threads for a user.
        
        SSOT: Query pattern for active threads.
        No mock workarounds - tests should use proper async mocking.
        """
        result = await db.execute(
            select(Thread).where(
                and_(
                    Thread.metadata_.op('->>')('user_id') == user_id,
                    Thread.deleted_at.is_(None)
                )
            ).order_by(Thread.created_at.desc())
        )
        return list(result.scalars().all())