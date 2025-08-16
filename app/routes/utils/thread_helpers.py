"""Thread route specific utilities."""

from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.database.thread_repository import ThreadRepository
from app.services.database.message_repository import MessageRepository
from app.logging_config import central_logger
from app.llm.llm_manager import LLMManager
from app.ws_manager import ws_manager
import time
import uuid

logger = central_logger.get_logger(__name__)

async def create_thread_repositories():
    """Create thread and message repositories."""
    return ThreadRepository(), MessageRepository()

async def get_user_threads(db: AsyncSession, user_id: int):
    """Get all threads for user."""
    thread_repo = ThreadRepository()
    return await thread_repo.find_by_user(db, user_id)

async def build_thread_response(thread, message_count: int, title: Optional[str] = None):
    """Build ThreadResponse object."""
    from app.routes.threads_route import ThreadResponse
    return ThreadResponse(
        id=thread.id,
        object=thread.object,
        title=title or thread.metadata_.get("title"),
        created_at=thread.created_at,
        updated_at=thread.metadata_.get("updated_at"),
        metadata=thread.metadata_,
        message_count=message_count
    )

async def convert_threads_to_responses(db: AsyncSession, threads: List, offset: int, limit: int):
    """Convert threads to response objects with message counts."""
    message_repo = MessageRepository()
    response_threads = []
    for thread in threads[offset:offset+limit]:
        message_count = await message_repo.count_by_thread(db, thread.id)
        response = await build_thread_response(thread, message_count)
        response_threads.append(response)
    return response_threads

def generate_thread_id() -> str:
    """Generate unique thread ID."""
    return f"thread_{uuid.uuid4().hex[:16]}"

def prepare_thread_metadata(thread_data, user_id: int) -> Dict[str, Any]:
    """Prepare thread metadata."""
    metadata = thread_data.metadata or {}
    metadata["user_id"] = user_id
    if thread_data.title:
        metadata["title"] = thread_data.title
    metadata["status"] = "active"
    return metadata

async def create_thread_record(db: AsyncSession, thread_id: str, metadata: Dict):
    """Create thread record in database."""
    thread_repo = ThreadRepository()
    return await thread_repo.create(
        db, id=thread_id, object="thread",
        created_at=int(time.time()), metadata_=metadata
    )

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

async def update_thread_metadata_fields(thread, thread_update):
    """Update thread metadata fields."""
    if not thread.metadata_:
        thread.metadata_ = {}
    if thread_update.title is not None:
        thread.metadata_["title"] = thread_update.title
    if thread_update.metadata:
        thread.metadata_.update(thread_update.metadata)
    thread.metadata_["updated_at"] = int(time.time())

async def archive_thread_safely(db: AsyncSession, thread_id: str) -> bool:
    """Archive thread with error handling."""
    thread_repo = ThreadRepository()
    success = await thread_repo.archive_thread(db, thread_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to archive thread")
    return success

async def build_thread_messages_response(db: AsyncSession, thread_id: str, limit: int, offset: int):
    """Build thread messages response."""
    message_repo = MessageRepository()
    messages = await message_repo.find_by_thread(db, thread_id, limit=limit, offset=offset)
    total = await message_repo.count_by_thread(db, thread_id)
    
    return {
        "thread_id": thread_id,
        "messages": [
            {
                "id": msg.id, "role": msg.role, "content": msg.content,
                "created_at": msg.created_at, "metadata": msg.metadata_
            }
            for msg in messages
        ],
        "total": total, "limit": limit, "offset": offset
    }

async def get_first_user_message_safely(db: AsyncSession, thread_id: str):
    """Get first user message with error handling."""
    message_repo = MessageRepository()
    messages = await message_repo.find_by_thread(db, thread_id, limit=5)
    first_user_message = next((msg for msg in messages if msg.role == "user"), None)
    if not first_user_message:
        raise HTTPException(status_code=400, detail="No user message found to generate title from")
    return first_user_message

async def generate_title_with_llm(content: str) -> str:
    """Generate title using LLM with fallback."""
    try:
        llm_manager = LLMManager()
        prompt = f"""Generate a concise 3-5 word title for a conversation that starts with this message:
        
        "{content[:500]}"
        
        Return ONLY the title, no explanation or quotes."""
        generated_title = await llm_manager.ask_llm(prompt, "triage")
        return generated_title.strip().strip('"').strip("'")[:50]
    except Exception as llm_error:
        logger.warning(f"LLM title generation failed: {llm_error}")
        return f"Chat {int(time.time())}"

async def update_thread_with_title(db: AsyncSession, thread, title: str) -> None:
    """Update thread with generated title."""
    if not thread.metadata_:
        thread.metadata_ = {}
    thread.metadata_["title"] = title
    thread.metadata_["auto_renamed"] = True
    thread.metadata_["updated_at"] = int(time.time())
    await db.commit()

async def send_thread_rename_notification(user_id: int, thread_id: str, title: str) -> None:
    """Send WebSocket notification for thread rename."""
    event = {
        "type": "thread_renamed", "thread_id": thread_id,
        "new_title": title, "timestamp": int(time.time())
    }
    await ws_manager.send_to_user(str(user_id), event)

async def create_final_thread_response(db: AsyncSession, thread, title: str):
    """Create final ThreadResponse with message count."""
    message_repo = MessageRepository()
    message_count = await message_repo.count_by_thread(db, thread.id)
    return await build_thread_response(thread, message_count, title)

# Route handler helpers
async def handle_list_threads_request(db: AsyncSession, user_id: int, offset: int, limit: int):
    """Handle list threads request logic."""
    threads = await get_user_threads(db, user_id)
    return await convert_threads_to_responses(db, threads, offset, limit)

async def handle_create_thread_request(db: AsyncSession, thread_data, user_id: int):
    """Handle create thread request logic."""
    thread_id = generate_thread_id()
    metadata = prepare_thread_metadata(thread_data, user_id)
    thread = await create_thread_record(db, thread_id, metadata)
    if not thread:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Failed to create thread in database")
    return await build_thread_response(thread, 0, metadata.get("title"))

async def handle_get_thread_request(db: AsyncSession, thread_id: str, user_id: int):
    """Handle get thread request logic."""
    thread = await get_thread_with_validation(db, thread_id, user_id)
    message_count = await MessageRepository().count_by_thread(db, thread_id)
    return await build_thread_response(thread, message_count)

async def handle_update_thread_request(db: AsyncSession, thread_id: str, thread_update, user_id: int):
    """Handle update thread request logic."""
    thread = await get_thread_with_validation(db, thread_id, user_id)
    await update_thread_metadata_fields(thread, thread_update)
    await db.commit()
    message_count = await MessageRepository().count_by_thread(db, thread_id)
    return await build_thread_response(thread, message_count)

async def handle_delete_thread_request(db: AsyncSession, thread_id: str, user_id: int):
    """Handle delete thread request logic."""
    await get_thread_with_validation(db, thread_id, user_id)
    await archive_thread_safely(db, thread_id)
    return {"message": "Thread archived successfully"}

async def handle_get_messages_request(db: AsyncSession, thread_id: str, user_id: int, limit: int, offset: int):
    """Handle get thread messages request logic."""
    await get_thread_with_validation(db, thread_id, user_id)
    return await build_thread_messages_response(db, thread_id, limit, offset)

async def handle_auto_rename_request(db: AsyncSession, thread_id: str, user_id: int):
    """Handle auto rename thread request logic."""
    thread = await get_thread_with_validation(db, thread_id, user_id)
    first_message = await get_first_user_message_safely(db, thread_id)
    title = await generate_title_with_llm(first_message.content)
    await update_thread_with_title(db, thread, title)
    await send_thread_rename_notification(user_id, thread_id, title)
    return await create_final_thread_response(db, thread, title)

# Error handling wrapper
async def handle_route_with_error_logging(handler_func, error_context: str):
    """Handle route with standardized error logging."""
    try:
        return await handler_func()
    except HTTPException:
        raise
    except Exception as e:
        from app.logging_config import central_logger
        logger = central_logger.get_logger(__name__)
        logger.error(f"Error {error_context}: {e}", exc_info=True if "creating" in error_context else False)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to {error_context.lower()}")