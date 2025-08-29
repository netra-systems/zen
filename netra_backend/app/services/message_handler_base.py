"""Base message handler methods extracted for modularity"""

import json
from typing import Any, Dict, Optional
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import Run, Thread
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core import get_websocket_manager
manager = get_websocket_manager()

logger = central_logger.get_logger(__name__)

class MessageHandlerBase:
    """Base methods for message handling"""
    
    @staticmethod
    def extract_user_request(payload: Dict[str, Any]) -> str:
        """Extract user request from payload - supports multiple field names for consistency"""
        # First check for direct content/text fields (same as user_message)
        if "content" in payload:
            return payload["content"]
        if "text" in payload:
            return payload["text"]
        # Then check for user_request directly
        if "user_request" in payload:
            return payload["user_request"]
        # Finally check nested request structure (legacy)
        request_data = payload.get("request", {})
        return request_data.get("query", "") or request_data.get("user_request", "")
    
    @staticmethod
    async def validate_thread_access(
        thread_service, user_id: str, thread_id: str, db_session: AsyncSession
    ) -> Optional[Thread]:
        """Validate user has access to thread"""
        thread = await thread_service.get_thread(thread_id, db_session)
        if thread and thread.metadata_.get("user_id") != user_id:
            await manager.send_error(user_id, "Access denied to thread")
            return None
        return thread
    
    @staticmethod
    async def get_or_create_thread(
        thread_service, user_id: str, db_session: AsyncSession
    ) -> Optional[Thread]:
        """Get or create thread for user"""
        thread = await thread_service.get_or_create_thread(user_id, db_session)
        if not thread:
            await manager.send_error(user_id, "Failed to create or retrieve thread")
        return thread
    
    @staticmethod
    async def create_user_message(
        thread_service, thread: Thread, content: str, 
        user_id: str, db_session: AsyncSession, metadata: Dict = None
    ) -> None:
        """Create user message in thread"""
        if metadata is None:
            metadata = {"user_id": user_id}
        await thread_service.create_message(
            thread.id, role="user", content=content,
            metadata=metadata, db=db_session
        )
    
    @staticmethod
    async def create_run(
        thread_service, thread: Thread, db_session: AsyncSession
    ) -> Run:
        """Create run for thread"""
        return await thread_service.create_run(
            thread.id, assistant_id="netra-assistant", model=LLMModel.GEMINI_2_5_FLASH.value,
            instructions="You are Netra AI Workload Optimization Assistant",
            db=db_session
        )
    
    @staticmethod
    def configure_supervisor(supervisor, user_id: str, thread: Thread, db_session: AsyncSession) -> None:
        """Configure supervisor with context"""
        supervisor.thread_id = thread.id
        supervisor.user_id = user_id
        # CRITICAL FIX: Do not assign db_session to supervisor to prevent concurrent access
        # The session is managed by the websocket handler and closed after processing
        supervisor.db_session = None
    
    @staticmethod
    async def save_response(
        thread_service, thread: Thread, response: Any, 
        run: Run, db_session: AsyncSession
    ) -> None:
        """Save assistant response if present"""
        if not response:
            return
        content = json.dumps(response) if isinstance(response, dict) else str(response)
        await thread_service.create_message(
            thread.id, role="assistant", content=content,
            assistant_id="netra-assistant", run_id=run.id, db=db_session
        )
    
    @staticmethod
    async def complete_run(thread_service, run: Run, db_session: AsyncSession) -> None:
        """Mark run as completed"""
        await thread_service.update_run_status(
            run.id, status="completed", db=db_session
        )
    
    @staticmethod
    async def send_completion(user_id: str, response: Any) -> None:
        """Send completion message to user"""
        await manager.send_message(
            user_id, {"type": "agent_completed", "payload": response}
        )
    
    @staticmethod
    def convert_response_to_dict(response: Any) -> Any:
        """Convert response to dictionary if needed"""
        if hasattr(response, 'model_dump'):
            return response.model_dump()
        elif hasattr(response, 'dict'):
            return response.dict()
        elif hasattr(response, '__dict__'):
            return response.__dict__
        return response