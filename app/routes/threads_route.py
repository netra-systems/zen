"""Thread Management Routes

Handles thread CRUD operations and thread history.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.dependencies import DbDep
from app.logging_config import central_logger
from app.auth.auth_dependencies import get_current_active_user
from app.routes.utils.thread_helpers import (
    get_user_threads, convert_threads_to_responses, generate_thread_id,
    prepare_thread_metadata, create_thread_record, build_thread_response,
    get_thread_with_validation, update_thread_metadata_fields, archive_thread_safely,
    build_thread_messages_response, get_first_user_message_safely, generate_title_with_llm,
    update_thread_with_title, send_thread_rename_notification, create_final_thread_response
)
from pydantic import BaseModel
import time

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
    db: DbDep, current_user = Depends(get_current_active_user),
    limit: int = Query(20, le=100), offset: int = Query(0, ge=0)
):
    """List all threads for the current user"""
    try:
        threads = await get_user_threads(db, current_user.id)
        return await convert_threads_to_responses(db, threads, offset, limit)
    except Exception as e:
        logger.error(f"Error listing threads: {e}")
        raise HTTPException(status_code=500, detail="Failed to list threads")

@router.post("/", response_model=ThreadResponse)
async def create_thread(
    thread_data: ThreadCreate, db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Create a new thread"""
    try:
        thread_id = generate_thread_id()
        metadata = prepare_thread_metadata(thread_data, current_user.id)
        thread = await create_thread_record(db, thread_id, metadata)
        if not thread:
            raise HTTPException(status_code=500, detail="Failed to create thread in database")
        return await build_thread_response(thread, 0, metadata.get("title"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating thread: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create thread")

@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str, db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Get a specific thread"""
    try:
        thread = await get_thread_with_validation(db, thread_id, current_user.id)
        from app.services.database.message_repository import MessageRepository
        message_count = await MessageRepository().count_by_thread(db, thread_id)
        return await build_thread_response(thread, message_count)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get thread")

@router.put("/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: str, thread_update: ThreadUpdate, db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Update a thread"""
    try:
        thread = await get_thread_with_validation(db, thread_id, current_user.id)
        await update_thread_metadata_fields(thread, thread_update)
        await db.commit()
        from app.services.database.message_repository import MessageRepository
        message_count = await MessageRepository().count_by_thread(db, thread_id)
        return await build_thread_response(thread, message_count)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update thread")

@router.delete("/{thread_id}")
async def delete_thread(
    thread_id: str, db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Delete (archive) a thread"""
    try:
        await get_thread_with_validation(db, thread_id, current_user.id)
        await archive_thread_safely(db, thread_id)
        return {"message": "Thread archived successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete thread")

@router.get("/{thread_id}/messages")
async def get_thread_messages(
    thread_id: str, db: DbDep, current_user = Depends(get_current_active_user),
    limit: int = Query(50, le=100), offset: int = Query(0, ge=0)
):
    """Get messages for a specific thread"""
    try:
        await get_thread_with_validation(db, thread_id, current_user.id)
        return await build_thread_messages_response(db, thread_id, limit, offset)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get thread messages")

@router.post("/{thread_id}/auto-rename")
async def auto_rename_thread(
    thread_id: str, db: DbDep,
    current_user = Depends(get_current_active_user)
):
    """Automatically generate a title for thread based on first message"""
    try:
        thread = await get_thread_with_validation(db, thread_id, current_user.id)
        first_message = await get_first_user_message_safely(db, thread_id)
        title = await generate_title_with_llm(first_message.content)
        await update_thread_with_title(db, thread, title)
        await send_thread_rename_notification(current_user.id, thread_id, title)
        return await create_final_thread_response(db, thread, title)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error auto-renaming thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to auto-rename thread")