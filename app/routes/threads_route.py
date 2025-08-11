"""Thread Management Routes

Handles thread CRUD operations and thread history.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.postgres import get_async_db as get_db
from app.services.database.thread_repository import ThreadRepository
from app.services.database.message_repository import MessageRepository
from app.logging_config import central_logger
from app.auth.auth_dependencies import get_current_active_user
from pydantic import BaseModel
import time
import uuid

logger = central_logger.get_logger(__name__)

router = APIRouter(
    prefix="/api/threads",
    tags=["threads"],
    redirect_slashes=False  # Disable automatic trailing slash redirects
)

class ThreadCreate(BaseModel):
    title: Optional[str] = None
    metadata: Optional[dict] = None

class ThreadUpdate(BaseModel):
    title: Optional[str] = None
    metadata: Optional[dict] = None

class ThreadResponse(BaseModel):
    id: str
    object: str = "thread"
    title: Optional[str] = None
    created_at: int
    updated_at: Optional[int] = None
    metadata: Optional[dict] = None
    message_count: int = 0

@router.get("/", response_model=List[ThreadResponse])
async def list_threads(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0)
):
    """List all threads for the current user"""
    try:
        thread_repo = ThreadRepository()
        message_repo = MessageRepository()
        
        # Get all threads for user
        threads = await thread_repo.find_by_user(db, current_user.id)
        
        # Convert to response model with message counts
        response_threads = []
        for thread in threads[offset:offset+limit]:
            message_count = await message_repo.count_by_thread(db, thread.id)
            
            response_threads.append(ThreadResponse(
                id=thread.id,
                object=thread.object,
                title=thread.metadata_.get("title") if thread.metadata_ else None,
                created_at=thread.created_at,
                updated_at=thread.metadata_.get("updated_at") if thread.metadata_ else None,
                metadata=thread.metadata_,
                message_count=message_count
            ))
        
        return response_threads
        
    except Exception as e:
        logger.error(f"Error listing threads: {e}")
        raise HTTPException(status_code=500, detail="Failed to list threads")

@router.post("/", response_model=ThreadResponse)
async def create_thread(
    thread_data: ThreadCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new thread"""
    try:
        thread_repo = ThreadRepository()
        
        # Generate thread ID
        thread_id = f"thread_{uuid.uuid4().hex[:16]}"
        
        # Prepare metadata
        metadata = thread_data.metadata or {}
        metadata["user_id"] = current_user.id
        if thread_data.title:
            metadata["title"] = thread_data.title
        metadata["status"] = "active"
        
        # Create thread
        thread = await thread_repo.create(
            db,
            id=thread_id,
            object="thread",
            created_at=int(time.time()),
            metadata_=metadata
        )
        
        await db.commit()
        
        return ThreadResponse(
            id=thread.id,
            object=thread.object,
            title=metadata.get("title"),
            created_at=thread.created_at,
            metadata=thread.metadata_,
            message_count=0
        )
        
    except Exception as e:
        logger.error(f"Error creating thread: {e}")
        raise HTTPException(status_code=500, detail="Failed to create thread")

@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get a specific thread"""
    try:
        thread_repo = ThreadRepository()
        message_repo = MessageRepository()
        
        thread = await thread_repo.get_by_id(db, thread_id)
        
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Verify user owns thread
        if thread.metadata_.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        message_count = await message_repo.count_by_thread(db, thread_id)
        
        return ThreadResponse(
            id=thread.id,
            object=thread.object,
            title=thread.metadata_.get("title"),
            created_at=thread.created_at,
            updated_at=thread.metadata_.get("updated_at"),
            metadata=thread.metadata_,
            message_count=message_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get thread")

@router.put("/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: str,
    thread_update: ThreadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Update a thread"""
    try:
        thread_repo = ThreadRepository()
        message_repo = MessageRepository()
        
        thread = await thread_repo.get_by_id(db, thread_id)
        
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Verify user owns thread
        if thread.metadata_.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update metadata
        if not thread.metadata_:
            thread.metadata_ = {}
        
        if thread_update.title is not None:
            thread.metadata_["title"] = thread_update.title
        
        if thread_update.metadata:
            thread.metadata_.update(thread_update.metadata)
        
        thread.metadata_["updated_at"] = int(time.time())
        
        await db.commit()
        
        message_count = await message_repo.count_by_thread(db, thread_id)
        
        return ThreadResponse(
            id=thread.id,
            object=thread.object,
            title=thread.metadata_.get("title"),
            created_at=thread.created_at,
            updated_at=thread.metadata_.get("updated_at"),
            metadata=thread.metadata_,
            message_count=message_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update thread")

@router.delete("/{thread_id}")
async def delete_thread(
    thread_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Delete (archive) a thread"""
    try:
        thread_repo = ThreadRepository()
        
        thread = await thread_repo.get_by_id(db, thread_id)
        
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Verify user owns thread
        if thread.metadata_.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Archive instead of delete
        success = await thread_repo.archive_thread(db, thread_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to archive thread")
        
        return {"message": "Thread archived successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete thread")

@router.get("/{thread_id}/messages")
async def get_thread_messages(
    thread_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """Get messages for a specific thread"""
    try:
        thread_repo = ThreadRepository()
        message_repo = MessageRepository()
        
        thread = await thread_repo.get_by_id(db, thread_id)
        
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Verify user owns thread
        if thread.metadata_.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get messages
        messages = await message_repo.find_by_thread(
            db, 
            thread_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "thread_id": thread_id,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at,
                    "metadata": msg.metadata_
                }
                for msg in messages
            ],
            "total": await message_repo.count_by_thread(db, thread_id),
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get thread messages")