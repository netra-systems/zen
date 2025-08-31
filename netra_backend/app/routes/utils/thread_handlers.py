"""Thread route handlers."""
import time

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
    """Handle get thread request logic."""
    thread = await get_thread_with_validation(db, thread_id, user_id)
    message_count = await MessageRepository().count_by_thread(db, thread_id)
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
    """Update thread metadata fields."""
    _initialize_thread_metadata(thread)
    _update_title_field(thread, thread_update)
    if thread_update.metadata:
        thread.metadata_.update(thread_update.metadata)
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
    """Handle get thread messages request logic."""
    await get_thread_with_validation(db, thread_id, user_id)
    return await build_thread_messages_response(db, thread_id, limit, offset)


async def handle_auto_rename_request(db: AsyncSession, thread_id: str, user_id: str):
    """Handle auto rename thread request logic."""
    thread = await get_thread_with_validation(db, thread_id, user_id)
    first_message = await get_first_user_message_safely(db, thread_id)
    title = await generate_title_with_llm(first_message.content)
    await update_thread_with_title(db, thread, title)
    await send_thread_rename_notification(user_id, thread_id, title)
    return await create_final_thread_response(db, thread, title)