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
    handle_list_threads_request, handle_create_thread_request, handle_get_thread_request,
    handle_update_thread_request, handle_delete_thread_request, handle_get_messages_request,
    handle_auto_rename_request
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
        return await handle_list_threads_request(db, current_user.id, offset, limit)
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
        return await handle_create_thread_request(db, thread_data, current_user.id)
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
        return await handle_get_thread_request(db, thread_id, current_user.id)
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
        return await handle_update_thread_request(db, thread_id, thread_update, current_user.id)
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
        return await handle_delete_thread_request(db, thread_id, current_user.id)
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
        return await handle_get_messages_request(db, thread_id, current_user.id, limit, offset)
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
        return await handle_auto_rename_request(db, thread_id, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error auto-renaming thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to auto-rename thread")