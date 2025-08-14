from typing import Dict, Optional, List, TYPE_CHECKING, TypedDict, Union, Any
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect
from app.logging_config import central_logger
from app.db.models_postgres import Thread, Run

if TYPE_CHECKING:
    from app.agents.supervisor import SupervisorAgent
from app.services.thread_service import ThreadService
from app.schemas.websocket_types import (
    UserMessagePayload,
    CreateThreadPayload,
    SwitchThreadPayload,
    DeleteThreadPayload,
    ThreadHistoryResponse,
    AgentCompletedPayload,
    AgentStoppedPayload,
    AgentResponseData
)
from app.ws_manager import manager
from app.services.message_handler_utils import handle_thread_history as _handle_thread_history
from app.services.message_handler_utils import handle_stop_agent as _handle_stop_agent
from app.services.message_handler_base import MessageHandlerBase
from app.services.message_processing import (
    process_user_message as _process_user_message,
    execute_and_persist as _execute_and_persist,
    persist_response as _persist_response,
    save_assistant_message as _save_assistant_message,
    mark_run_completed as _mark_run_completed,
    send_response_safely as _send_response_safely,
    handle_disconnect as _handle_disconnect,
    handle_processing_error as _handle_processing_error,
    is_connection_error as _is_connection_error,
    send_error_safely as _send_error_safely
)
import json

logger = central_logger.get_logger(__name__)

class StartAgentPayloadTyped(TypedDict):
    """Strongly typed payload for start_agent messages"""
    user_request: str
    thread_id: Optional[str]
    context: Optional[Dict[str, Union[str, int, float, bool]]]
    settings: Optional[Dict[str, Union[str, int, float, bool]]]

class MessageHandlerService:
    """Handles different types of WebSocket messages following conventions"""
    
    def __init__(self, supervisor: 'SupervisorAgent', thread_service: ThreadService):
        self.supervisor = supervisor
        self.thread_service = thread_service
    
    async def handle_start_agent(
        self,
        user_id: str,
        payload: StartAgentPayloadTyped,
        db_session: AsyncSession
    ) -> None:
        """Handle start_agent message type"""
        user_request = self._extract_user_request(payload)
        thread = await self._get_or_validate_thread(user_id, payload, db_session)
        if not thread:
            return
        await self._process_agent_request(user_id, user_request, thread, db_session)
    
    def _extract_user_request(self, payload: StartAgentPayloadTyped) -> str:
        """Extract user request from payload"""
        return MessageHandlerBase.extract_user_request(payload)
    
    async def _get_or_validate_thread(
        self, user_id: str, payload: StartAgentPayloadTyped, db_session: AsyncSession
    ) -> Optional[Thread]:
        """Get or validate thread for user"""
        thread_id = payload.get("thread_id", None)
        if thread_id:
            thread = await self._validate_thread_access(user_id, thread_id, db_session)
            if thread:
                return thread
        return await self._get_or_create_thread(user_id, db_session)
    
    async def _validate_thread_access(
        self, user_id: str, thread_id: str, db_session: AsyncSession
    ) -> Optional[Thread]:
        """Validate user has access to thread"""
        return await MessageHandlerBase.validate_thread_access(
            self.thread_service, user_id, thread_id, db_session
        )
    
    async def _get_or_create_thread(
        self, user_id: str, db_session: AsyncSession
    ) -> Optional[Thread]:
        """Get or create thread for user"""
        return await MessageHandlerBase.get_or_create_thread(
            self.thread_service, user_id, db_session
        )
    
    async def _process_agent_request(
        self, user_id: str, user_request: str, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Process the agent request"""
        await self._create_user_message(thread, user_request, user_id, db_session)
        run = await self._create_run(thread, db_session)
        self._configure_supervisor(user_id, thread, db_session)
        response = await self._execute_supervisor(user_request, thread, user_id, run)
        await self._save_response(thread, response, run, db_session)
        await self._complete_run(run, db_session)
        await self._send_completion(user_id, response)
    
    async def _create_user_message(
        self, thread: Thread, content: str, user_id: str, db_session: AsyncSession
    ) -> None:
        """Create user message in thread"""
        await MessageHandlerBase.create_user_message(
            self.thread_service, thread, content, user_id, db_session
        )
    
    async def _create_run(
        self, thread: Thread, db_session: AsyncSession
    ) -> Run:
        """Create run for thread"""
        return await MessageHandlerBase.create_run(
            self.thread_service, thread, db_session
        )
    
    def _configure_supervisor(self, user_id: str, thread: Thread, db_session: AsyncSession) -> None:
        """Configure supervisor with context"""
        MessageHandlerBase.configure_supervisor(
            self.supervisor, user_id, thread, db_session
        )
    
    async def _execute_supervisor(
        self, user_request: str, thread: Thread, user_id: str, run: Run
    ) -> Any:
        """Execute supervisor run"""
        return await self.supervisor.run(user_request, thread.id, user_id, run.id)
    
    async def _save_response(
        self, thread: Thread, response: Any, run: Run, db_session: AsyncSession
    ) -> None:
        """Save assistant response if present"""
        await MessageHandlerBase.save_response(
            self.thread_service, thread, response, run, db_session
        )
    
    async def _complete_run(self, run: Run, db_session: AsyncSession) -> None:
        """Mark run as completed"""
        await MessageHandlerBase.complete_run(
            self.thread_service, run, db_session
        )
    
    async def _send_completion(self, user_id: str, response: Any) -> None:
        """Send completion message to user"""
        await MessageHandlerBase.send_completion(user_id, response)
    
    async def handle_user_message(
        self,
        user_id: str,
        payload: UserMessagePayload,
        db_session: Optional[AsyncSession]
    ) -> None:
        """Handle user_message type"""
        text, references, thread_id = self._extract_message_data(payload)
        logger.info(f"Received user message from {user_id}: {text}, thread_id: {thread_id}")
        thread, run = await self._setup_thread_and_run(user_id, text, references, thread_id, db_session)
        await self._process_user_message(user_id, text, thread, run, db_session)
    
    def _extract_message_data(self, payload: UserMessagePayload) -> tuple:
        """Extract message data from payload"""
        text = payload.get("text", "")
        references = payload.get("references", [])
        thread_id = payload.get("thread_id", None)
        return text, references, thread_id
    
    async def _setup_thread_and_run(
        self, user_id: str, text: str, references: list, 
        thread_id: Optional[str], db_session: Optional[AsyncSession]
    ) -> tuple:
        """Setup thread and run for message processing"""
        if not db_session:
            return None, None
        try:
            thread = await self._get_validated_thread(user_id, thread_id, db_session)
            if not thread:
                return None, None
            return await self._initialize_conversation(thread, text, references, user_id, db_session)
        except Exception as e:
            logger.error(f"Error setting up thread/run: {e}")
            return None, None
    
    async def _get_validated_thread(
        self, user_id: str, thread_id: Optional[str], db_session: AsyncSession
    ) -> Optional[Thread]:
        """Get and validate thread for user"""
        if thread_id:
            thread = await self._validate_existing_thread(user_id, thread_id, db_session)
            if thread:
                return thread
        return await self._create_new_thread(user_id, db_session)
    
    async def _validate_existing_thread(
        self, user_id: str, thread_id: str, db_session: AsyncSession
    ) -> Optional[Thread]:
        """Validate existing thread ownership"""
        thread = await self.thread_service.get_thread(thread_id, db_session)
        if thread and thread.metadata_.get("user_id") != user_id:
            await manager.send_error(user_id, "Access denied to thread")
            return None
        return thread
    
    async def _create_new_thread(
        self, user_id: str, db_session: AsyncSession
    ) -> Optional[Thread]:
        """Create new thread for user"""
        thread = await self.thread_service.get_or_create_thread(user_id, db_session)
        if not thread:
            logger.warning(f"Could not get/create thread for user {user_id}")
        return thread
    
    async def _initialize_conversation(
        self, thread: Thread, text: str, references: List[str],
        user_id: str, db_session: AsyncSession
    ) -> tuple[Thread, Run]:
        """Initialize conversation with message and run"""
        await self._save_user_message(thread, text, references, db_session)
        run = await self._create_conversation_run(thread, db_session)
        self._setup_supervisor(thread, user_id, db_session)
        return thread, run
    
    async def _save_user_message(
        self, thread: Thread, text: str, references: List[str], db_session: AsyncSession
    ) -> None:
        """Save user message to thread"""
        metadata: Optional[Dict[str, List[str]]] = {"references": references} if references else None
        await self.thread_service.create_message(
            thread.id, role="user", content=text, metadata=metadata, db=db_session
        )
    
    async def _create_conversation_run(
        self, thread: Thread, db_session: AsyncSession
    ) -> Run:
        """Create run for conversation"""
        return await self.thread_service.create_run(
            thread.id, assistant_id="netra-assistant", model="gpt-4",
            instructions="You are Netra AI Workload Optimization Assistant", db=db_session
        )
    
    def _setup_supervisor(self, thread: Thread, user_id: str, db_session: AsyncSession) -> None:
        """Setup supervisor context"""
        self.supervisor.thread_id = thread.id
        self.supervisor.user_id = user_id
        self.supervisor.db_session = db_session
    
    async def _process_user_message(
        self, user_id: str, text: str, thread: Optional[Thread],
        run: Optional[Run], db_session: Optional[AsyncSession]
    ) -> None:
        """Process user message and send response"""
        await _process_user_message(
            self.supervisor, user_id, text, thread, run, db_session, self.thread_service
        )
    
    
    async def handle_thread_history(
        self,
        user_id: str,
        db_session: Optional[AsyncSession]
    ) -> None:
        """Handle get_thread_history message type"""
        await _handle_thread_history(self.thread_service, user_id, db_session)
    
    async def handle_stop_agent(self, user_id: str) -> None:
        """Handle stop_agent message type"""
        await _handle_stop_agent(user_id)