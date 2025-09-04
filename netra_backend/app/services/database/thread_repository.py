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
        """Find all threads for a user with robust error handling"""
        try:
            # Ensure user_id is string format for consistent comparison
            user_id_str = str(user_id).strip()
            logger.debug(f"Finding threads for user_id: {user_id_str}")
            
            # Primary query using JSONB operators
            result = await db.execute(
                select(Thread).where(
                    Thread.metadata_.op('->>')('user_id') == user_id_str
                ).order_by(Thread.created_at.desc())
            )
            threads = list(result.scalars().all())
            logger.info(f"Found {len(threads)} threads for user {user_id_str}")
            return threads
            
        except Exception as e:
            logger.error(f"Primary JSONB query failed for user {user_id}: {e}", exc_info=True)
            
            # Fallback: try alternative query approach for cases where metadata might be NULL or malformed
            try:
                logger.warning(f"Attempting fallback query for user {user_id}")
                result = await db.execute(
                    select(Thread).order_by(Thread.created_at.desc())
                )
                all_threads = result.scalars().all()
                
                # Filter threads in Python as a last resort
                user_threads = []
                for thread in all_threads:
                    if thread.metadata_ and isinstance(thread.metadata_, dict):
                        thread_user_id = thread.metadata_.get('user_id')
                        if thread_user_id and str(thread_user_id).strip() == user_id_str:
                            user_threads.append(thread)
                
                logger.info(f"Fallback: Found {len(user_threads)} threads for user {user_id_str}")
                return user_threads
                
            except Exception as fallback_error:
                logger.error(f"Fallback query also failed: {fallback_error}", exc_info=True)
                # Return empty list to prevent endpoint failure, but log the issue
                logger.critical(f"Unable to retrieve threads for user {user_id} - returning empty list")
                return []
    
    async def get_or_create_for_user(self, db: AsyncSession, user_id: str) -> Optional[Thread]:
        """Get existing thread for user or create new one
        
        First checks for existing active threads for the user.
        If none exist, creates a new thread with a unique UUID-based ID.
        """
        # First check if user has any existing active threads
        existing_thread = await self.get_active_thread(db, user_id)
        if existing_thread:
            return existing_thread
        
        # Create new thread with unique ID
        thread_id = f"thread_{uuid.uuid4().hex[:16]}"
        
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
        """Get all active (non-soft-deleted) threads for a user"""
        try:
            result = await db.execute(
                select(Thread).where(
                    and_(
                        Thread.metadata_.op('->>')('user_id') == user_id,
                        Thread.deleted_at.is_(None)
                    )
                ).order_by(Thread.created_at.desc())
            )
            scalars = result.scalars()
            # Handle potential mock coroutine issues
            if hasattr(scalars, '__await__'):
                scalars = await scalars
            scalars_result = scalars.all()
            if hasattr(scalars_result, '__await__'):
                scalars_result = await scalars_result
            return list(scalars_result)
        except Exception as e:
            logger.error(f"Error getting active threads for user {user_id}: {e}")
            return []