from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.db.models_postgres import Thread, Message, Assistant, Run
from app.logging_config import central_logger
import uuid
import time
import json

logger = central_logger.get_logger(__name__)

class ThreadService:
    """Service for managing conversation threads and messages"""
    
    async def get_or_create_thread(self, db: AsyncSession, user_id: str) -> Optional[Thread]:
        """Get existing thread for user or create a new one"""
        # For simplicity, we'll use one thread per user
        # In production, you might want multiple threads per user
        thread_id = f"thread_{user_id}"
        
        try:
            result = await db.execute(
                select(Thread).where(Thread.id == thread_id)
            )
            thread = result.scalar_one_or_none()
            
            if not thread:
                thread = Thread(
                    id=thread_id,
                    object="thread",
                    created_at=int(time.time()),
                    metadata_={"user_id": user_id}
                )
                db.add(thread)
                await db.commit()
                await db.refresh(thread)
                logger.info(f"Created new thread for user {user_id}")
            
            return thread
            
        except IntegrityError as e:
            # Handle race condition where thread was created by another request
            await db.rollback()
            logger.warning(f"Thread creation race condition for user {user_id}: {e}")
            # Try to fetch the existing thread
            result = await db.execute(
                select(Thread).where(Thread.id == thread_id)
            )
            return result.scalar_one_or_none()
            
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error in get_or_create_thread for user {user_id}: {e}")
            return None
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error in get_or_create_thread for user {user_id}: {e}")
            return None
    
    async def create_message(
        self, 
        db: AsyncSession,
        thread_id: str,
        role: str,
        content: str,
        assistant_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """Create a new message in a thread"""
        try:
            message = Message(
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
            
            db.add(message)
            await db.commit()
            await db.refresh(message)
            
            logger.info(f"Created message {message.id} in thread {thread_id}")
            return message
            
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error creating message in thread {thread_id}: {e}")
            return None
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error creating message in thread {thread_id}: {e}")
            return None
    
    async def get_thread_messages(
        self,
        db: AsyncSession,
        thread_id: str,
        limit: int = 50
    ) -> List[Message]:
        """Get messages for a thread"""
        result = await db.execute(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))  # Return in chronological order
    
    async def create_run(
        self,
        db: AsyncSession,
        thread_id: str,
        assistant_id: str,
        model: str = "gpt-4",
        instructions: Optional[str] = None
    ) -> Run:
        """Create a new run for a thread"""
        run = Run(
            id=f"run_{uuid.uuid4()}",
            object="thread.run",
            created_at=int(time.time()),
            thread_id=thread_id,
            assistant_id=assistant_id,
            status="in_progress",
            model=model,
            instructions=instructions,
            tools=[],
            file_ids=[],
            metadata_={}
        )
        
        db.add(run)
        await db.commit()
        await db.refresh(run)
        
        logger.info(f"Created run {run.id} for thread {thread_id}")
        return run
    
    async def update_run_status(
        self,
        db: AsyncSession,
        run_id: str,
        status: str,
        error: Optional[Dict[str, Any]] = None
    ) -> Run:
        """Update the status of a run"""
        result = await db.execute(
            select(Run).where(Run.id == run_id)
        )
        run = result.scalar_one_or_none()
        
        if run:
            run.status = status
            if error:
                run.last_error = error
            if status == "completed":
                run.completed_at = int(time.time())
            elif status == "failed":
                run.failed_at = int(time.time())
            
            await db.commit()
            await db.refresh(run)
            logger.info(f"Updated run {run_id} status to {status}")
        
        return run