"""Thread title generation utilities."""
import time
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.llm.llm_manager import LLMManager
# WebSocket manager accessed via factory pattern for security
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.message_repository import MessageRepository

logger = central_logger.get_logger(__name__)


async def get_first_user_message_safely(db: AsyncSession, thread_id: str):
    """Get first user message with error handling."""
    message_repo = MessageRepository()
    messages = await message_repo.find_by_thread(db, thread_id, limit=5)
    first_user_message = next((msg for msg in messages if msg.role == "user"), None)
    if not first_user_message:
        raise HTTPException(status_code=400, detail="No user message found to generate title from")
    return first_user_message


def build_title_generation_prompt(content: str) -> str:
    """Build prompt for title generation."""
    return f"""Generate a concise 3-5 word title for a conversation that starts with this message:
        
        "{content[:500]}"
        
        Return ONLY the title, no explanation or quotes."""


def clean_generated_title(generated_title: str) -> str:
    """Clean and format generated title."""
    return generated_title.strip().strip('"').strip("'")[:50]


def get_fallback_title() -> str:
    """Get fallback title when LLM fails."""
    return f"Chat {int(time.time())}"


async def _call_llm_for_title(content: str) -> str:
    """Call LLM to generate title."""
    llm_manager = LLMManager()
    prompt = build_title_generation_prompt(content)
    generated_title = await llm_manager.ask_llm(prompt, "triage")
    return clean_generated_title(generated_title)

async def generate_title_with_llm(content: str) -> str:
    """Generate title using LLM with fallback."""
    try:
        return await _call_llm_for_title(content)
    except Exception as llm_error:
        logger.warning(f"LLM title generation failed: {llm_error}")
        return get_fallback_title()


async def update_thread_with_title(db: AsyncSession, thread, title: str) -> None:
    """Update thread with generated title."""
    if not thread.metadata_:
        thread.metadata_ = {}
    thread.metadata_["title"] = title
    thread.metadata_["auto_renamed"] = True
    thread.metadata_["updated_at"] = int(time.time())
    await db.commit()


async def send_thread_rename_notification(user_id: str, thread_id: str, title: str, user_context=None) -> None:
    """Send WebSocket notification for thread rename.
    
    Args:
        user_id: User identifier
        thread_id: Thread identifier
        title: New title
        user_context: Optional user execution context for WebSocket notifications
    """
    event = {
        "type": "thread_renamed", "thread_id": thread_id,
        "new_title": title, "timestamp": int(time.time())
    }
    
    if user_context:
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            websocket_manager = create_websocket_manager(user_context)
            await websocket_manager.send_to_user(str(user_id), event)
        except Exception as e:
            logger.error(f"Failed to send thread rename notification: {e}")
    else:
        logger.debug(f"Thread renamed without WebSocket notification (no user context): {thread_id} -> {title}")


async def create_final_thread_response(db: AsyncSession, thread, title: str):
    """Create final ThreadResponse with message count."""
    from netra_backend.app.routes.utils.thread_builders import build_thread_response
    from netra_backend.app.services.database.message_repository import MessageRepository
    message_repo = MessageRepository()
    message_count = await message_repo.count_by_thread(db, thread.id)
    return await build_thread_response(thread, message_count, title)