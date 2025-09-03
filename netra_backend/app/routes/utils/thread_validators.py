"""Thread validation utilities."""
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.services.database.thread_repository import ThreadRepository


def validate_thread_exists(thread) -> None:
    """Validate thread exists."""
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")


def validate_thread_access(thread, user_id: str) -> None:
    """Validate user has access to thread."""
    from netra_backend.app.logging_config import central_logger
    logger = central_logger.get_logger(__name__)
    
    # Handle various metadata structures
    if not hasattr(thread, 'metadata_') or thread.metadata_ is None:
        logger.error(f"Thread {thread.id if hasattr(thread, 'id') else 'unknown'} has no metadata")
        raise HTTPException(status_code=500, detail="Thread metadata is missing")
    
    # Get thread user_id from metadata, handling different possible locations and types
    thread_user_id = thread.metadata_.get("user_id")
    
    # Handle None case
    if thread_user_id is None:
        logger.error(f"Thread {thread.id if hasattr(thread, 'id') else 'unknown'} has no user_id in metadata")
        raise HTTPException(status_code=500, detail="Thread has no associated user")
    
    # Normalize both IDs to strings for comparison, handling various types
    try:
        # Handle UUID objects, integers, and strings
        normalized_thread_user = str(thread_user_id).strip()
        normalized_current_user = str(user_id).strip()
        
        # Log the comparison for debugging
        logger.debug(f"Access check - Thread user: {normalized_thread_user} (type: {type(thread_user_id).__name__}), "
                    f"Current user: {normalized_current_user} (type: {type(user_id).__name__})")
        
        if normalized_thread_user != normalized_current_user:
            logger.warning(f"Access denied - Thread user {normalized_thread_user} != Current user {normalized_current_user}")
            raise HTTPException(status_code=403, detail="Access denied")
            
    except HTTPException:
        # Re-raise HTTPException as-is (403 Access denied)
        raise
    except Exception as e:
        logger.error(f"Error validating thread access: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to validate thread access")


async def get_thread_with_validation(db: AsyncSession, thread_id: str, user_id: str):
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