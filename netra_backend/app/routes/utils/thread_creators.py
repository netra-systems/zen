"""Thread creation utilities."""
import time
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.routes.utils.thread_builders import build_thread_response
from netra_backend.app.services.database.thread_repository import ThreadRepository


def generate_thread_id() -> str:
    """Generate unique thread ID using UnifiedIDManager for SSOT compliance.
    
    Uses the proper SSOT pattern: instance method with IDType enum.
    Returns properly formatted thread ID with consistent naming.
    """
    from netra_backend.app.core.unified_id_manager import get_id_manager, IDType
    
    # Use SSOT pattern: instance method with IDType for consistency
    # No prefix needed as IDType.THREAD already includes "thread" in the ID
    id_manager = get_id_manager()
    return id_manager.generate_id(IDType.THREAD)


def prepare_thread_metadata(thread_data, user_id: str) -> Dict[str, Any]:
    """Prepare thread metadata with consistent user_id formatting."""
    from netra_backend.app.logging_config import central_logger
    logger = central_logger.get_logger(__name__)
    
    metadata = thread_data.metadata or {}
    
    # Ensure user_id is always stored as a string for consistency
    normalized_user_id = str(user_id).strip()
    metadata["user_id"] = normalized_user_id
    
    logger.debug(f"Creating thread with user_id: {normalized_user_id} (original type: {type(user_id).__name__})")
    
    if thread_data.title:
        metadata["title"] = thread_data.title
    metadata["status"] = "active"
    metadata["created_at"] = int(time.time())
    
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
    from netra_backend.app.services.database.message_repository import MessageRepository
    from netra_backend.app.services.database.thread_repository import ThreadRepository
    return ThreadRepository(), MessageRepository()


async def get_user_threads(db: AsyncSession, user_id: str):
    """Get all threads for user."""
    thread_repo = ThreadRepository()
    return await thread_repo.find_by_user(db, user_id)


class ThreadCreator:
    """SSOT Thread Creator for integration testing.
    
    Provides unified thread creation interface that combines thread creation
    with initial message creation for comprehensive testing scenarios.
    """
    
    def __init__(self):
        """Initialize ThreadCreator with SSOT dependencies."""
        self.thread_repo = ThreadRepository()
        from netra_backend.app.services.database.message_repository import MessageRepository
        self.message_repo = MessageRepository()
    
    async def create_thread_with_message(self, context, message: str, title: str = None):
        """Create thread and initial message atomically.
        
        Args:
            context: UserExecutionContext with user_id and thread_id
            message: Initial message content
            title: Optional thread title
            
        Returns:
            Thread object with created thread data
        """
        from netra_backend.app.logging_config import central_logger
        from netra_backend.app.services.database.unit_of_work import get_unit_of_work
        
        logger = central_logger.get_logger(__name__)
        
        # Generate thread ID if not provided in context
        thread_id = str(context.thread_id) if context.thread_id else generate_thread_id()
        user_id = str(context.user_id)
        
        logger.debug(f"Creating thread {thread_id} with message for user {user_id}")
        
        # Prepare thread metadata
        metadata = prepare_thread_metadata(
            type('ThreadData', (), {'metadata': {}, 'title': title})(),
            user_id
        )
        
        # Create thread and message atomically using unit of work
        async with get_unit_of_work() as uow:
            # Create thread record
            thread = await create_thread_record(uow.session, thread_id, metadata)
            
            # Create initial message
            message_data = {
                "id": f"msg_{generate_thread_id()}",  # Reuse ID generator
                "object": "thread.message",
                "created_at": int(time.time()),
                "thread_id": thread_id,
                "role": "user",
                "content": [{"type": "text", "text": {"value": message}}],
                "assistant_id": None,
                "run_id": None,
                "file_ids": [],
                "metadata_": {"initial_message": True}
            }
            
            initial_message = await self.message_repo.create(uow.session, **message_data)
            
            logger.info(f"Successfully created thread {thread_id} with initial message for user {user_id}")
            
            return thread