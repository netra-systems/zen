"""Thread Management Routes

Handles thread CRUD operations and thread history.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.dependencies import DbDep
from app.services.database.thread_repository import ThreadRepository
from app.services.database.message_repository import MessageRepository
from app.logging_config import central_logger
from app.auth.auth_dependencies import get_current_active_user
from app.llm.llm_manager import LLMManager
from app.ws_manager import ws_manager
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
    db: DbDep,
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
    db: DbDep,
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
        
        if not thread:
            raise HTTPException(status_code=500, detail="Failed to create thread in database")
        
        return ThreadResponse(
            id=thread.id,
            object=thread.object,
            title=metadata.get("title"),
            created_at=thread.created_at,
            metadata=thread.metadata_,
            message_count=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating thread: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create thread")

@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    db: DbDep,
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
    db: DbDep,
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
    db: DbDep,
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
    db: DbDep,
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

async def _validate_thread_access(db: AsyncSession, thread_id: str, current_user) -> any:
    """Validate thread exists and user has access"""
    thread_repo = ThreadRepository()
    thread = await thread_repo.get_by_id(db, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.metadata_.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return thread

async def _get_first_user_message(db: AsyncSession, thread_id: str) -> any:
    """Get first user message from thread"""
    message_repo = MessageRepository()
    messages = await message_repo.find_by_thread(db, thread_id, limit=5)
    first_user_message = next((msg for msg in messages if msg.role == "user"), None)
    if not first_user_message:
        raise HTTPException(status_code=400, detail="No user message found to generate title from")
    return first_user_message

async def _build_title_prompt(content: str) -> str:
    """Build LLM prompt for title generation"""
    return f"""Generate a concise 3-5 word title for a conversation that starts with this message:
    
    "{content[:500]}"
    
    Return ONLY the title, no explanation or quotes."""

async def _generate_title(first_message_content: str) -> str:
    """Generate title using LLM with fallback"""
    try:
        llm_manager = LLMManager()
        prompt = _build_title_prompt(first_message_content)
        generated_title = await llm_manager.ask_llm(prompt, "triage")
        return generated_title.strip().strip('"').strip("'")[:50]
    except Exception as llm_error:
        logger.warning(f"LLM title generation failed: {llm_error}")
        return f"Chat {int(time.time())}"

async def _update_thread_metadata(db: AsyncSession, thread: any, title: str) -> None:
    """Update thread metadata with new title"""
    if not thread.metadata_:
        thread.metadata_ = {}
    thread.metadata_["title"] = title
    thread.metadata_["auto_renamed"] = True
    thread.metadata_["updated_at"] = int(time.time())
    await db.commit()

async def _build_rename_event(thread_id: str, title: str) -> dict:
    """Build WebSocket event for thread rename"""
    return {
        "type": "thread_renamed",
        "thread_id": thread_id,
        "new_title": title,
        "timestamp": int(time.time())
    }

async def _send_rename_notification(user_id: str, thread_id: str, title: str) -> None:
    """Send WebSocket notification for thread rename"""
    event = _build_rename_event(thread_id, title)
    await ws_manager.send_to_user(user_id, event)

async def _get_message_count(db: AsyncSession, thread_id: str) -> int:
    """Get message count for thread"""
    message_repo = MessageRepository()
    return await message_repo.count_by_thread(db, thread_id)

async def _create_thread_response(db: AsyncSession, thread: any, title: str) -> ThreadResponse:
    """Create ThreadResponse with message count"""
    message_count = await _get_message_count(db, thread.id)
    return ThreadResponse(
        id=thread.id, object=thread.object, title=title,
        created_at=thread.created_at, updated_at=thread.metadata_.get("updated_at"),
        metadata=thread.metadata_, message_count=message_count
    )

@router.post("/{thread_id}/auto-rename")
async def auto_rename_thread(
    thread_id: str,
    db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Automatically generate a title for thread based on first message"""
    try:
        thread = await _validate_thread_access(db, thread_id, current_user)
        first_message = await _get_first_user_message(db, thread_id)
        title = await _generate_title(first_message.content)
        await _update_thread_metadata(db, thread, title)
        await _send_rename_notification(current_user.id, thread_id, title)
        return await _create_thread_response(db, thread, title)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error auto-renaming thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to auto-rename thread")

