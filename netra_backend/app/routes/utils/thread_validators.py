"""Thread validation utilities."""
from typing import Any
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.services.database.thread_repository import ThreadRepository


def validate_thread_exists(thread) -> None:
    """Validate thread exists."""
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")


def validate_thread_access(thread, user_id: int) -> None:
    """Validate user has access to thread."""
    if thread.metadata_.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")


async def get_thread_with_validation(db: AsyncSession, thread_id: str, user_id: int):
    """Get thread with validation."""
    thread_repo = ThreadRepository()
    thread = await thread_repo.get_by_id(db, thread_id)
    validate_thread_exists(thread)
    validate_thread_access(thread, user_id)
    return thread


async def archive_thread_safely(db: AsyncSession, thread_id: str) -> bool:
    """Archive thread with error handling."""
    thread_repo = ThreadRepository()
    success = await thread_repo.archive_thread(db, thread_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to archive thread")
    return success