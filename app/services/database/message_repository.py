"""Message Repository Implementation

Handles all message-related database operations.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from app.services.database.base_repository import BaseRepository
from app.db.models_postgres import Message
from app.logging_config import central_logger
import time
import uuid

logger = central_logger.get_logger(__name__)

class MessageRepository(BaseRepository[Message]):
    """Repository for Message entities"""
    
    def __init__(self):
        super().__init__(Message)
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[Message]:
        """Find messages by user through thread relationship"""
        from app.db.models_postgres import Thread
        
        try:
            result = await db.execute(
                select(Message).join(Thread, Message.thread_id == Thread.id).where(
                    Thread.metadata_.op('->>')('user_id') == user_id
                ).order_by(desc(Message.created_at))
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error finding messages for user {user_id}: {e}")
            return []
    
    async def create_message(self, 
                           db: AsyncSession,
                           thread_id: str,
                           role: str,
                           content: str,
                           assistant_id: Optional[str] = None,
                           run_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> Optional[Message]:
        """Create a new message with proper structure"""
        return await self.create(
            db,
            id=f"msg_{uuid.uuid4()}",
            object="thread.message",
            created_at=int(time.time()),
            thread_id=thread_id,
            role=role,
            content=[{"type": "text", "text": {"value": content}}],
            assistant_id=assistant_id,
            run_id=run_id,
            file_ids=[],
            metadata_=metadata or {}
        )
    
    async def get_thread_messages(self,
                                 db: AsyncSession,
                                 thread_id: str,
                                 limit: int = 50,
                                 before_timestamp: Optional[int] = None) -> List[Message]:
        """Get messages for a thread with pagination"""
        try:
            query = select(Message).where(Message.thread_id == thread_id)
            
            if before_timestamp:
                query = query.where(Message.created_at < before_timestamp)
            
            query = query.order_by(desc(Message.created_at)).limit(limit)
            result = await db.execute(query)
            messages = list(result.scalars().all())
            return list(reversed(messages))
        except Exception as e:
            logger.error(f"Error getting messages for thread {thread_id}: {e}")
            return []
    
    async def get_run_messages(self,
                              db: AsyncSession,
                              run_id: str) -> List[Message]:
        """Get all messages associated with a specific run"""
        try:
            result = await db.execute(
                select(Message).where(Message.run_id == run_id).order_by(Message.created_at)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting messages for run {run_id}: {e}")
            return []
    
    async def update_message_content(self,
                                    db: AsyncSession,
                                    message_id: str,
                                    new_content: str) -> Optional[Message]:
        """Update message content"""
        message = await self.get_by_id(db, message_id)
        if not message:
            return None
        
        message.content = [{"type": "text", "text": {"value": new_content}}]
        
        try:
            await db.commit()
            await db.refresh(message)
            return message
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating message {message_id}: {e}")
            return None
    
    async def count_by_thread(self, db: AsyncSession, thread_id: str) -> int:
        """Count messages in a thread"""
        try:
            result = await db.execute(
                select(func.count(Message.id)).where(Message.thread_id == thread_id)
            )
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting messages for thread {thread_id}: {e}")
            return 0
    
    async def find_by_thread(self, 
                            db: AsyncSession, 
                            thread_id: str,
                            limit: int = 50,
                            offset: int = 0) -> List[Message]:
        """Find messages by thread with pagination"""
        try:
            result = await db.execute(
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(Message.created_at)
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error finding messages for thread {thread_id}: {e}")
            return []