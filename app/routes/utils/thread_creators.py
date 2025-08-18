"""Thread creation utilities."""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.database.thread_repository import ThreadRepository
from app.routes.utils.thread_builders import build_thread_response
import time
import uuid


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


async def create_thread_repositories():
    """Create thread and message repositories."""
    from app.services.database.thread_repository import ThreadRepository
    from app.services.database.message_repository import MessageRepository
    return ThreadRepository(), MessageRepository()


async def get_user_threads(db: AsyncSession, user_id: int):
    """Get all threads for user."""
    thread_repo = ThreadRepository()
    return await thread_repo.find_by_user(db, user_id)