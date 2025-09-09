"""Thread route handlers."""
import time

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.routes.utils.thread_builders import (
    build_thread_messages_response,
    build_thread_response,
    convert_threads_to_responses,
)
from netra_backend.app.routes.utils.thread_creators import (
    create_thread_record,
    generate_thread_id,
    get_user_threads,
    prepare_thread_metadata,
)
from netra_backend.app.routes.utils.thread_title_generator import (
    create_final_thread_response,
    generate_title_with_llm,
    get_first_user_message_safely,
    send_thread_rename_notification,
    update_thread_with_title,
)
from netra_backend.app.routes.utils.thread_validators import (
    archive_thread_safely,
    get_thread_with_validation,
)
from netra_backend.app.services.database.message_repository import MessageRepository


async def handle_list_threads_request(db: AsyncSession, user_id: str, offset: int, limit: int):
    """Handle list threads request logic."""
    threads = await get_user_threads(db, user_id)
    return await convert_threads_to_responses(db, threads, offset, limit)


def _validate_thread_creation(thread) -> None:
    """Validate thread creation result."""
    if not thread:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Failed to create thread in database")

async def handle_create_thread_request(db: AsyncSession, thread_data, user_id: str):
    """Handle create thread request logic."""
    thread_id = generate_thread_id()
    metadata = prepare_thread_metadata(thread_data, user_id)
    thread = await create_thread_record(db, thread_id, metadata)
    _validate_thread_creation(thread)
    return await build_thread_response(thread, 0, metadata.get("title"))


async def handle_get_thread_request(db: AsyncSession, thread_id: str, user_id: str):
    """Handle get thread request logic with enhanced logging."""
    from netra_backend.app.logging_config import central_logger
    logger = central_logger.get_logger(__name__)
    
    logger.info(f"Getting thread {thread_id} for user {user_id}")
    thread = await get_thread_with_validation(db, thread_id, user_id)
    
    logger.debug(f"Thread {thread_id} metadata: {thread.metadata_ if hasattr(thread, 'metadata_') else 'No metadata'}")
    
    message_count = await MessageRepository().count_by_thread(db, thread_id)
    logger.debug(f"Thread {thread_id} has {message_count} messages")
    
    return await build_thread_response(thread, message_count)


def _initialize_thread_metadata(thread) -> None:
    """Initialize thread metadata if needed."""
    if not thread.metadata_:
        thread.metadata_ = {}

def _update_title_field(thread, thread_update) -> None:
    """Update title field if provided."""
    if thread_update.title is not None:
        thread.metadata_["title"] = thread_update.title

async def update_thread_metadata_fields(thread, thread_update):
    """Update thread metadata fields while preserving user_id consistency."""
    from netra_backend.app.logging_config import central_logger
    logger = central_logger.get_logger(__name__)
    
    _initialize_thread_metadata(thread)
    
    # Preserve the original user_id to prevent accidental changes
    original_user_id = thread.metadata_.get("user_id")
    
    _update_title_field(thread, thread_update)
    if thread_update.metadata:
        # Prevent user_id from being changed via metadata update
        update_data = thread_update.metadata.copy()
        if "user_id" in update_data:
            logger.warning(f"Attempt to change user_id in thread {thread.id} blocked")
            del update_data["user_id"]
        thread.metadata_.update(update_data)
    
    # Ensure user_id remains unchanged and properly formatted
    if original_user_id:
        thread.metadata_["user_id"] = str(original_user_id).strip()
    
    thread.metadata_["updated_at"] = int(time.time())


async def handle_update_thread_request(db: AsyncSession, thread_id: str, thread_update, user_id: str):
    """Handle update thread request logic."""
    thread = await get_thread_with_validation(db, thread_id, user_id)
    await update_thread_metadata_fields(thread, thread_update)
    await db.commit()
    message_count = await MessageRepository().count_by_thread(db, thread_id)
    return await build_thread_response(thread, message_count)


async def handle_delete_thread_request(db: AsyncSession, thread_id: str, user_id: str):
    """Handle delete thread request logic."""
    await get_thread_with_validation(db, thread_id, user_id)
    await archive_thread_safely(db, thread_id)
    return {"message": "Thread archived successfully"}


async def handle_get_messages_request(db: AsyncSession, thread_id: str, user_id: str, limit: int, offset: int):
    """Handle get thread messages request logic with enhanced logging."""
    from netra_backend.app.logging_config import central_logger
    logger = central_logger.get_logger(__name__)
    
    logger.info(f"Getting messages for thread {thread_id}, user {user_id}, limit {limit}, offset {offset}")
    
    thread = await get_thread_with_validation(db, thread_id, user_id)
    logger.debug(f"Thread validation passed for {thread_id}")
    
    response = await build_thread_messages_response(db, thread_id, limit, offset)
    logger.debug(f"Returning {len(response.get('messages', []))} messages for thread {thread_id}")
    
    return response


async def handle_auto_rename_request(db: AsyncSession, thread_id: str, user_id: str):
    """Handle auto rename thread request logic."""
    thread = await get_thread_with_validation(db, thread_id, user_id)
    first_message = await get_first_user_message_safely(db, thread_id)
    title = await generate_title_with_llm(first_message.content)
    await update_thread_with_title(db, thread, title)
    await send_thread_rename_notification(user_id, thread_id, title)
    return await create_final_thread_response(db, thread, title)


async def handle_send_message_request(db: AsyncSession, thread_id: str, request, user_id: str):
    """Handle send message to thread request logic."""
    import time
    from uuid import uuid4
    from netra_backend.app.logging_config import central_logger
    from netra_backend.app.services.database.message_repository import MessageRepository
    
    logger = central_logger.get_logger(__name__)
    logger.info(f"Sending message to thread {thread_id} for user {user_id}")
    
    # Validate thread exists and user has access
    thread = await get_thread_with_validation(db, thread_id, user_id)
    logger.debug(f"Thread validation passed for {thread_id}")
    
    # Create message record
    message_id = str(uuid4())
    created_at = int(time.time())
    
    # Prepare message data
    message_data = {
        'id': message_id,
        'thread_id': thread_id,
        'role': 'user',  # Messages sent via this endpoint are user messages
        'content': request.message,
        'created_at': created_at,
        'metadata_': request.metadata or {}
    }
    
    try:
        # Save message to database
        message_repo = MessageRepository()
        await message_repo.create(db, **message_data)
        await db.commit()
        
        logger.info(f"Successfully created message {message_id} in thread {thread_id}")
        
        # Return response matching the expected schema
        return {
            'id': message_id,
            'thread_id': thread_id,
            'content': request.message,
            'role': 'user',
            'created_at': created_at
        }
        
    except Exception as e:
        logger.error(f"Failed to save message to thread {thread_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}"
        )