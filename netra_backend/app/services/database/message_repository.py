"""Message Repository Implementation

Handles all message-related database operations.
"""

import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import Message
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.base_repository import BaseRepository

logger = central_logger.get_logger(__name__)

class MessageRepository(BaseRepository[Message]):
    """Repository for Message entities"""
    
    def __init__(self):
        super().__init__(Message)
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[Message]:
        """Find messages by user through thread relationship"""
        from netra_backend.app.db.models_postgres import Thread
        
        try:
            result = await db.execute(
                select(Message).join(Thread, Message.thread_id == Thread.id).where(
                    Thread.metadata_.op('->>')('user_id') == user_id
                ).order_by(desc(Message.created_at))
            )
            scalars = result.scalars()
            if hasattr(scalars, '__await__'):
                scalars = await scalars
            scalars_result = scalars.all()
            if hasattr(scalars_result, '__await__'):
                scalars_result = await scalars_result
            return list(scalars_result)
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
            db=db,
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
    
    async def get_by_thread(self, 
                           db: AsyncSession, 
                           thread_id: str,
                           limit: int = 50) -> List[Message]:
        """Get messages by thread - alias for find_by_thread for consistency"""
        return await self.get_thread_messages(db, thread_id, limit)    
    async def get_messages_paginated(self,
                                   db: AsyncSession,
                                   thread_id: str,
                                   limit: int = 20,
                                   offset: int = 0) -> List[Message]:
        """Get paginated messages for a thread"""
        try:
            query = select(Message).where(Message.thread_id == thread_id)
            query = query.order_by(Message.created_at).limit(limit).offset(offset)
            result = await db.execute(query)
            scalars = result.scalars()
            if hasattr(scalars, '__await__'):
                scalars = await scalars
            scalars_result = scalars.all()
            if hasattr(scalars_result, '__await__'):
                scalars_result = await scalars_result
            return list(scalars_result)
        except Exception as e:
            logger.error(f"Error getting paginated messages for thread {thread_id}: {e}")
            return []
    
    async def search_messages(self,
                            db: AsyncSession,
                            query: str,
                            thread_id: Optional[str] = None) -> List[Message]:
        """Search messages by content"""
        try:
            # Extract text content from JSON structure for search
            stmt = select(Message)
            
            if thread_id:
                stmt = stmt.where(Message.thread_id == thread_id)
            
            # For now, return all messages since content is in JSON format
            # In a real implementation, we'd use JSON operators to search content
            result = await db.execute(stmt.order_by(Message.created_at))
            scalars = result.scalars()
            if hasattr(scalars, '__await__'):
                scalars = await scalars
            scalars_result = scalars.all()
            if hasattr(scalars_result, '__await__'):
                scalars_result = await scalars_result
            messages = list(scalars_result)
            
            # Simple text search in content
            filtered = []
            for msg in messages:
                if msg.content:
                    # Handle different content formats for flexibility
                    if isinstance(msg.content, str):
                        # Simple string content
                        if query.lower() in msg.content.lower():
                            filtered.append(msg)
                    elif isinstance(msg.content, list):
                        # OpenAI format: list of content objects
                        for content_item in msg.content:
                            if isinstance(content_item, dict) and 'text' in content_item:
                                text_content = content_item.get('text', {}).get('value', '')
                                if query.lower() in text_content.lower():
                                    filtered.append(msg)
                                    break
            
            return filtered
        except Exception as e:
            logger.error(f"Error searching messages with query '{query}': {e}")
            return []
    
    async def get_messages_by_date_range(self,
                                       db: AsyncSession,
                                       thread_id: str,
                                       start_date,
                                       end_date) -> List[Message]:
        """Get messages by date range"""
        try:
            # Convert datetime to timestamp if needed
            start_ts = int(start_date.timestamp()) if hasattr(start_date, 'timestamp') else start_date
            end_ts = int(end_date.timestamp()) if hasattr(end_date, 'timestamp') else end_date
            
            query = select(Message).where(
                and_(
                    Message.thread_id == thread_id,
                    Message.created_at >= start_ts,
                    Message.created_at <= end_ts
                )
            ).order_by(Message.created_at)
            
            result = await db.execute(query)
            scalars = result.scalars()
            if hasattr(scalars, '__await__'):
                scalars = await scalars
            scalars_result = scalars.all()
            if hasattr(scalars_result, '__await__'):
                scalars_result = await scalars_result
            return list(scalars_result)
        except Exception as e:
            logger.error(f"Error getting messages by date range for thread {thread_id}: {e}")
            return []
