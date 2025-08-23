from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypedDict, Union

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect

from netra_backend.app.db.models_postgres import Run, Thread
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.service_interfaces import IMessageHandlerService

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor import SupervisorAgent
import json

from netra_backend.app.schemas.registry import (
    AgentCompletedPayload,
    AgentResponseData,
    AgentStoppedPayload,
    CreateThreadPayload,
    DeleteThreadPayload,
    SwitchThreadPayload,
    ThreadHistoryResponse,
    UserMessagePayload,
)
from netra_backend.app.services.message_handler_base import MessageHandlerBase
from netra_backend.app.services.message_handler_utils import (
    handle_stop_agent as _handle_stop_agent,
)
from netra_backend.app.services.message_handler_utils import (
    handle_thread_history as _handle_thread_history,
)
from netra_backend.app.services.message_processing import (
    execute_and_persist as _execute_and_persist,
)
from netra_backend.app.services.message_processing import (
    handle_disconnect as _handle_disconnect,
)
from netra_backend.app.services.message_processing import (
    handle_processing_error as _handle_processing_error,
)
from netra_backend.app.services.message_processing import (
    is_connection_error as _is_connection_error,
)
from netra_backend.app.services.message_processing import (
    mark_run_completed as _mark_run_completed,
)
from netra_backend.app.services.message_processing import (
    persist_response as _persist_response,
)
from netra_backend.app.services.message_processing import (
    process_user_message_with_notifications as _process_user_message,
)
from netra_backend.app.services.message_processing import (
    save_assistant_message as _save_assistant_message,
)
from netra_backend.app.services.message_processing import (
    send_error_safely as _send_error_safely,
)
from netra_backend.app.services.message_processing import (
    send_response_safely as _send_response_safely,
)
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.ws_manager import manager

logger = central_logger.get_logger(__name__)

class StartAgentPayloadTyped(TypedDict):
    """Strongly typed payload for start_agent messages"""
    user_request: str
    thread_id: Optional[str]
    context: Optional[Dict[str, Union[str, int, float, bool]]]
    settings: Optional[Dict[str, Union[str, int, float, bool]]]

class MessageHandlerService(IMessageHandlerService):
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
        
        # Don't process empty messages - prevents wasted agent resources
        if not text or not text.strip():
            logger.warning(f"Empty message from {user_id}, not starting agent")
            await manager.send_error(user_id, "Please enter a message")
            return
        
        thread, run = await self._setup_thread_and_run(user_id, text, references, thread_id, db_session)
        # Join user to thread room for WebSocket broadcasts
        if thread and thread_id:
            await manager.broadcasting.join_room(user_id, thread_id)
        await self._process_user_message(user_id, text, thread, run, db_session)
    
    def _extract_message_data(self, payload: UserMessagePayload) -> tuple:
        """Extract message data from payload - supports both 'content' and 'text' fields"""
        # Support both 'content' (from frontend) and 'text' (legacy) field names
        # Ensure text is never None
        text = payload.get("content") or payload.get("text") or ""
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
        return await self._setup_thread_with_validation(user_id, text, references, thread_id, db_session)
    
    async def _setup_thread_with_validation(
        self, user_id: str, text: str, references: list,
        thread_id: Optional[str], db_session: AsyncSession
    ) -> tuple:
        """Setup thread with validation and error handling"""
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
    
    async def handle_switch_thread(
        self,
        user_id: str,
        payload: SwitchThreadPayload,
        db_session: Optional[AsyncSession]
    ) -> None:
        """Handle switch_thread message type - join user to thread room"""
        thread_id = payload.get("thread_id")
        if not thread_id:
            await manager.send_error(user_id, "Thread ID required")
            return
        await self._execute_thread_switch(user_id, thread_id)
    
    async def _execute_thread_switch(self, user_id: str, thread_id: str) -> None:
        """Execute the thread switch operation"""
        # Leave all current rooms and join new thread room
        await manager.broadcasting.leave_all_rooms(user_id)
        await manager.broadcasting.join_room(user_id, thread_id)
        logger.info(f"User {user_id} switched to thread {thread_id}")

    # Interface implementation methods
    async def handle_message(self, user_id: str, message: Dict[str, Any]):
        """Handle a WebSocket message with proper type and payload."""
        message_type = message.get("type", "")
        payload = message.get("payload", {})
        await self._route_message(user_id, message_type, payload)
    
    async def _route_message(self, user_id: str, message_type: str, payload: Dict[str, Any]) -> None:
        """Route message to appropriate handler based on type"""
        if message_type == "start_agent":
            await self.handle_start_agent(user_id, payload, None)
        elif message_type == "user_message":
            await self.handle_user_message(user_id, payload, None)
        else:
            await self._route_other_messages(user_id, message_type, payload)
    
    async def _route_other_messages(self, user_id: str, message_type: str, payload: Dict[str, Any]) -> None:
        """Route other message types to their handlers"""
        if message_type == "get_thread_history":
            await self.handle_thread_history(user_id, None)
        elif message_type == "stop_agent":
            await self.handle_stop_agent(user_id)
        elif message_type == "switch_thread":
            await self.handle_switch_thread(user_id, payload, None)
        elif message_type == "example_message":
            await self.handle_example_message(user_id, payload, None)
        else:
            await manager.send_error(user_id, f"Unknown message type: {message_type}")

    async def process_user_message(self, user_id: str, message: str, thread_id: str = None):
        """Process a user message in a specific thread."""
        payload = {"text": message}
        if thread_id:
            payload["thread_id"] = thread_id
        await self.handle_user_message(user_id, payload, None)

    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        await manager.broadcast(message)

    async def handle_get_conversation_history(
        self, user_id: str, payload: Dict[str, Any], db_session: Optional[AsyncSession]
    ) -> None:
        """Handle get_conversation_history message type."""
        try:
            session_token = payload.get("session_token", user_id)
            logger.info(f"Getting conversation history for user {user_id}, session: {session_token}")
            
            # Get conversation history from thread service or create mock data
            history = await self._get_user_conversation_history(user_id, db_session)
            
            response = {
                "type": "conversation_history",
                "payload": {
                    "history": history,
                    "session_token": session_token
                }
            }
            
            await manager.send_message(user_id, response)
            logger.info(f"Sent conversation history to user {user_id}: {len(history)} messages")
            
        except Exception as e:
            logger.error(f"Error getting conversation history for user {user_id}: {e}", exc_info=True)
            await manager.send_error(user_id, f"Failed to get conversation history: {str(e)}")

    async def handle_get_agent_context(
        self, user_id: str, payload: Dict[str, Any], db_session: Optional[AsyncSession]
    ) -> None:
        """Handle get_agent_context message type."""
        try:
            session_token = payload.get("session_token", user_id)
            logger.info(f"Getting agent context for user {user_id}, session: {session_token}")
            
            # Get agent context from session or create mock data
            context = await self._get_user_agent_context(user_id, session_token, db_session)
            
            response = {
                "type": "agent_context",
                "payload": {
                    "context": context,
                    "session_token": session_token
                }
            }
            
            await manager.send_message(user_id, response)
            logger.info(f"Sent agent context to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error getting agent context for user {user_id}: {e}", exc_info=True)
            await manager.send_error(user_id, f"Failed to get agent context: {str(e)}")

    async def _get_user_conversation_history(
        self, user_id: str, db_session: Optional[AsyncSession]
    ) -> List[Dict[str, Any]]:
        """Get conversation history for user."""
        try:
            if db_session:
                # Try to get actual conversation history from database
                threads = await self.thread_service.get_user_threads(user_id, db_session)
                if threads:
                    # Get messages from the most recent thread
                    recent_thread = threads[0]
                    messages = await self.thread_service.get_thread_messages(recent_thread.id, db_session)
                    return [self._format_message_for_history(msg) for msg in messages]
            
            # Return empty history if no database session or no threads found
            return []
            
        except Exception as e:
            logger.warning(f"Could not get conversation history from database for user {user_id}: {e}")
            return []

    async def _get_user_agent_context(
        self, user_id: str, session_token: str, db_session: Optional[AsyncSession]
    ) -> Dict[str, Any]:
        """Get agent context for user session."""
        try:
            # Create a basic agent context
            context = {
                "session_token": session_token,
                "user_id": user_id,
                "conversation_history": await self._get_user_conversation_history(user_id, db_session),
                "agent_memory": {
                    "user_preferences": {},
                    "variables": {},
                    "workflow_state": {
                        "current_step": 0,
                        "total_steps": 1,
                        "pending_steps": []
                    }
                },
                "tool_call_history": [],
                "created_at": "2025-01-20T10:00:00Z",
                "last_activity": "2025-01-20T10:00:00Z"
            }
            
            # Try to get additional context from supervisor if available
            if hasattr(self.supervisor, 'get_agent_context'):
                supervisor_context = await self.supervisor.get_agent_context(user_id)
                if supervisor_context:
                    context.update(supervisor_context)
            
            return context
            
        except Exception as e:
            logger.warning(f"Could not get agent context for user {user_id}: {e}")
            # Return minimal context on error
            return {
                "session_token": session_token,
                "user_id": user_id,
                "conversation_history": [],
                "agent_memory": {"user_preferences": {}, "variables": {}, "workflow_state": {}},
                "tool_call_history": [],
                "error": "Context retrieval failed"
            }

    async def handle_example_message(
        self,
        user_id: str,
        payload: Dict[str, Any],
        db_session: Optional[AsyncSession]
    ) -> None:
        """Handle example_message message type."""
        try:
            logger.info(f"Processing example message for user {user_id}")
            
            # Import the example message handler with deferred import to avoid circular dependencies
            try:
                from netra_backend.app.handlers.example_message_handler import (
                    handle_example_message,
                )
            except ImportError as import_error:
                logger.error(f"Failed to import example message handler: {import_error}")
                await manager.send_error(user_id, "Example message handler not available")
                return
            
            # Add user_id to payload if not present
            if "user_id" not in payload:
                payload["user_id"] = user_id
                
            # Process the example message
            response = await handle_example_message(payload)
            
            # Send success response back to user
            success_message = {
                "type": "example_message_response",
                "payload": {
                    "status": response.status,
                    "message_id": response.message_id,
                    "result": response.result,
                    "processing_time_ms": response.processing_time_ms,
                    "business_insights": response.business_insights
                }
            }
            
            await manager.send_message(user_id, success_message)
            logger.info(f"Successfully processed example message for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing example message for user {user_id}: {e}", exc_info=True)
            await manager.send_error(user_id, f"Failed to process example message: {str(e)}")
    
    def _format_message_for_history(self, message) -> Dict[str, Any]:
        """Format a database message for conversation history."""
        return {
            "id": str(message.id),
            "role": message.role,
            "content": message.content,
            "timestamp": message.created_at.isoformat() if hasattr(message, 'created_at') else "2025-01-20T10:00:00Z"
        }