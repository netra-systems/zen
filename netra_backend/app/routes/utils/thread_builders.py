"""Thread response builders."""
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.services.database.message_repository import MessageRepository


def extract_thread_title(thread, title: Optional[str]) -> Optional[str]:
    """Extract thread title from parameters or metadata with NULL safety."""
    if title:
        return title
    if hasattr(thread, 'metadata_') and thread.metadata_:
        return thread.metadata_.get("title")
    return None


def extract_thread_updated_at(thread) -> Optional[int]:
    """Extract thread updated_at timestamp with NULL safety."""
    if hasattr(thread, 'metadata_') and thread.metadata_:
        return thread.metadata_.get("updated_at")
    return None


def _create_thread_response_fields(thread, message_count: int, title: Optional[str]) -> Dict:
    """Create thread response field dictionary with NULL safety."""
    # Ensure metadata is never None in response
    metadata = thread.metadata_ if hasattr(thread, 'metadata_') and thread.metadata_ else {}
    
    return {
        "id": thread.id, 
        "object": thread.object,
        "title": extract_thread_title(thread, title), 
        "created_at": thread.created_at,
        "updated_at": extract_thread_updated_at(thread), 
        "metadata": metadata,
        "message_count": message_count
    }

async def build_thread_response(thread, message_count: int, title: Optional[str] = None):
    """Build ThreadResponse object."""
    from netra_backend.app.routes.threads_route import ThreadResponse
    fields = _create_thread_response_fields(thread, message_count, title)
    return ThreadResponse(**fields)


async def _process_single_thread(db: AsyncSession, message_repo: MessageRepository, thread):
    """Process single thread for response."""
    message_count = await message_repo.count_by_thread(db, thread.id)
    return await build_thread_response(thread, message_count)

async def convert_threads_to_responses(db: AsyncSession, threads: List, offset: int, limit: int):
    """Convert threads to response objects with message counts."""
    message_repo = MessageRepository()
    response_threads = []
    for thread in threads[offset:offset+limit]:
        response = await _process_single_thread(db, message_repo, thread)
        response_threads.append(response)
    return response_threads


def format_single_message(msg) -> Dict[str, Any]:
    """Format single message for response with NULL safety."""
    # Ensure metadata is never None in response
    metadata = msg.metadata_ if hasattr(msg, 'metadata_') and msg.metadata_ else {}
    
    return {
        "id": msg.id, 
        "role": msg.role, 
        "content": msg.content,
        "created_at": msg.created_at, 
        "metadata": metadata
    }


def format_messages_list(messages) -> List[Dict[str, Any]]:
    """Format messages list for response."""
    return [format_single_message(msg) for msg in messages]


def build_messages_metadata(thread_id: str, total: int, limit: int, offset: int) -> Dict[str, Any]:
    """Build messages response metadata."""
    return {
        "thread_id": thread_id,
        "total": total,
        "limit": limit,
        "offset": offset
    }


async def build_thread_messages_response(db: AsyncSession, thread_id: str, limit: int, offset: int):
    """Build thread messages response."""
    message_repo = MessageRepository()
    messages = await message_repo.find_by_thread(db, thread_id, limit=limit, offset=offset)
    total = await message_repo.count_by_thread(db, thread_id)
    formatted_messages = format_messages_list(messages)
    metadata = build_messages_metadata(thread_id, total, limit, offset)
    return {"messages": formatted_messages, **metadata}