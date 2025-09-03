import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypedDict, Union
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect
from fastapi import WebSocket

from netra_backend.app.db.models_postgres import Message, Run, Thread
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.service_interfaces import IMessageHandlerService

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    from netra_backend.app.websocket_core import WebSocketManager
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
from netra_backend.app.websocket_core import get_websocket_manager
manager = get_websocket_manager()

logger = central_logger.get_logger(__name__)

class StartAgentPayloadTyped(TypedDict):
    """Strongly typed payload for start_agent messages"""
    user_request: str
    thread_id: Optional[str]
    context: Optional[Dict[str, Union[str, int, float, bool]]]
    settings: Optional[Dict[str, Union[str, int, float, bool]]]

class MessageHandlerService(IMessageHandlerService):
    """Handles different types of WebSocket messages following conventions"""
    
    def __init__(self, supervisor: 'SupervisorAgent', thread_service: ThreadService, websocket_manager: Optional['WebSocketManager'] = None):
        self.supervisor = supervisor
        self.thread_service = thread_service
        self.websocket_manager = websocket_manager
    
    async def handle_start_agent(
        self,
        user_id: str,
        payload: StartAgentPayloadTyped,
        db_session: AsyncSession,
        websocket: Optional['WebSocket'] = None
    ) -> None:
        """Handle start_agent message type"""
        user_request = self._extract_user_request(payload)
        thread = await self._get_or_validate_thread(user_id, payload, db_session)
        if not thread:
            return
        
        # CRITICAL FIX: Ensure thread association before agent processing
        if thread and self.websocket_manager and websocket:
            connection_id = self.websocket_manager.get_connection_id_by_websocket(websocket)
            if connection_id:
                success = self.websocket_manager.update_connection_thread(connection_id, thread.id)
                if success:
                    logger.info(f"✅ Thread association set for start_agent: connection={connection_id}, thread={thread.id}")
                    await asyncio.sleep(0.01)  # Small delay to ensure propagation
        
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
        logger.info(f"🎯 Starting agent request processing for user={user_id}, thread={thread.id}")
        logger.info(f"📊 db_session status at start: {type(db_session)}, is None: {db_session is None}")
        
        # CRITICAL FIX: Ensure thread association is established before processing
        # This prevents WebSocket emission failures during agent execution
        if self.websocket_manager:
            # Force thread association update and verify it worked
            success = self.websocket_manager.update_connection_thread(user_id, thread.id)
            if success:
                logger.info(f"✅ Thread association confirmed for user={user_id}, thread={thread.id}")
                # Small delay to ensure association propagates through all internal structures
                await asyncio.sleep(0.01)
            else:
                logger.warning(f"⚠️ No WebSocket connections found for user={user_id} - agent events may not be delivered")
                # Continue anyway - agent can still execute without WebSocket events
        
        await self._create_user_message(thread, user_request, user_id, db_session)
        run = await self._create_run(thread, db_session)
        
        logger.info(f"📝 Configuring supervisor for user={user_id}")
        self._configure_supervisor(user_id, thread, db_session)
        
        logger.info(f"🚀 Executing supervisor for run={run.id}")
        response = await self._execute_supervisor(user_request, thread, user_id, run, db_session)
        
        logger.info(f"💾 Saving response for run={run.id}")
        await self._save_response(thread, response, run, db_session)
        await self._complete_run(run, db_session)
        await self._send_completion(user_id, response)
        
        logger.info(f"✅ Agent request processing completed for user={user_id}, thread={thread.id}")
    
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
        
        # CRITICAL: Ensure supervisor has WebSocket manager for real-time events
        if self.websocket_manager and hasattr(self.supervisor, 'agent_registry'):
            logger.info(f"Setting WebSocket manager on supervisor for user {user_id}")
            self.supervisor.agent_registry.set_websocket_manager(self.websocket_manager)
        elif self.websocket_manager is None:
            logger.warning(f"WebSocket manager not available for user {user_id} - events disabled")
        else:
            logger.warning(f"Supervisor missing agent_registry - WebSocket events may not work for user {user_id}")
    
    async def _execute_supervisor(
        self, user_request: str, thread: Thread, user_id: str, run: Run, db_session: AsyncSession
    ) -> Any:
        """Execute supervisor run"""
        # CRITICAL: Register run-thread mapping for WebSocket routing
        # This ensures all agent events reach the correct user
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            bridge = await get_agent_websocket_bridge()
            
            # Register the mapping BEFORE execution
            success = await bridge.register_run_thread_mapping(
                run_id=run.id,
                thread_id=thread.id,
                metadata={
                    "user_id": user_id,
                    "user_request": user_request[:100] if user_request else "",
                    "timestamp": run.created_at
                }
            )
            
            if success:
                logger.info(f"✅ Registered run-thread mapping: run_id={run.id} → thread_id={thread.id}")
            else:
                logger.warning(f"⚠️ Failed to register run-thread mapping for run_id={run.id}")
                
            # CRITICAL: Set WebSocket bridge on SupervisorAgent for real-time events
            # This enables emit_thinking, emit_progress, and other WebSocket events
            if hasattr(self.supervisor, 'set_websocket_bridge'):
                self.supervisor.set_websocket_bridge(bridge, run.id)
                logger.info(f"✅ Set WebSocket bridge on SupervisorAgent for run_id={run.id}")
            else:
                logger.warning(f"⚠️ SupervisorAgent doesn't have set_websocket_bridge method")
                
        except Exception as e:
            logger.error(f"🚨 Error registering run-thread mapping: {e}")
            # Continue execution even if registration fails
        
        # Create UserExecutionContext for the new pattern
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
        
        # CRITICAL DEBUG: Log the db_session status
        logger.info(f"🔍 DEBUG: db_session type: {type(db_session)}, is None: {db_session is None}")
        if db_session is None:
            logger.error(f"🚨 CRITICAL: db_session is None! This will cause UserExecutionContext validation to fail")
            logger.error(f"🚨 Stack trace for debugging:")
            import traceback
            logger.error(traceback.format_stack())
        
        # Create context with proper metadata using the passed db_session
        logger.info(f"📝 Creating UserExecutionContext with: user_id={user_id}, thread_id={thread.id}, run_id={run.id}, db_session={type(db_session)}")
        
        try:
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread.id,
                run_id=run.id,
                db_session=db_session,
                metadata={
                    "user_request": user_request,
                    "timestamp": run.created_at
                }
            )
            logger.info(f"✅ Successfully created UserExecutionContext for user={user_id}, thread={thread.id}, run={run.id}")
        except Exception as e:
            logger.error(f"🚨 Failed to create UserExecutionContext: {e}")
            logger.error(f"🚨 Parameters were: user_id={user_id}, thread_id={thread.id}, run_id={run.id}, db_session={type(db_session)}")
            raise
        
        # Execute the supervisor with the new UserExecutionContext pattern
        try:
            logger.info(f"🚀 Attempting to execute SupervisorAgent.execute() with context for run_id={run.id}")
            
            # Double-check the supervisor has execute method
            if not hasattr(self.supervisor, 'execute'):
                logger.error(f"🚨 CRITICAL: SupervisorAgent does not have 'execute' method!")
                logger.error(f"🚨 Available methods: {[m for m in dir(self.supervisor) if not m.startswith('_')]}")
                raise AttributeError("SupervisorAgent missing execute method")
            
            result = await self.supervisor.execute(context, stream_updates=True)
            logger.info(f"✅ SupervisorAgent executed successfully for run_id={run.id}")
            logger.info(f"📊 Result type: {type(result)}, has content: {result is not None}")
            return result
        except AttributeError as e:
            logger.error(f"🚨 AttributeError in SupervisorAgent execution for run_id={run.id}: {e}")
            logger.error(f"🚨 This likely means the supervisor is missing a required method")
            logger.error(f"🚨 Supervisor type: {type(self.supervisor)}")
            raise
        except ValueError as e:
            logger.error(f"🚨 ValueError in SupervisorAgent execution for run_id={run.id}: {e}")
            logger.error(f"🚨 This likely means UserExecutionContext validation failed")
            logger.error(f"🚨 Context details: user_id={context.user_id}, thread_id={context.thread_id}, run_id={context.run_id}")
            raise
        except Exception as e:
            logger.error(f"❌ SupervisorAgent execution failed for run_id={run.id}: {e}", exc_info=True)
            logger.error(f"❌ Exception type: {type(e).__name__}")
            raise
    
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
        db_session: Optional[AsyncSession],
        websocket: Optional[WebSocket] = None
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
        
        # CRITICAL FIX: Ensure thread association before processing
        if thread and thread_id and self.websocket_manager and websocket:
            # Get connection_id from the websocket instance
            connection_id = self.websocket_manager.get_connection_id_by_websocket(websocket)
            if connection_id:
                # Update thread association BEFORE any agent processing
                success = self.websocket_manager.update_connection_thread(connection_id, thread_id)
                if success:
                    logger.info(f"✅ Thread association confirmed for connection={connection_id}, user={user_id}, thread={thread_id}")
                    await asyncio.sleep(0.01)  # Small delay to ensure propagation
                else:
                    logger.warning(f"⚠️ Failed to update thread for connection={connection_id}")
            else:
                logger.warning(f"⚠️ No connection found for websocket of user={user_id}")
        
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
        thread = await self.thread_service.get_thread(thread_id, user_id=user_id, db=db_session)
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
            thread.id, assistant_id="netra-assistant", model=LLMModel.GEMINI_2_5_FLASH.value,
            instructions="You are Netra AI Workload Optimization Assistant", db=db_session
        )
    
    def _setup_supervisor(self, thread: Thread, user_id: str, db_session: AsyncSession) -> None:
        """Setup supervisor context"""
        self.supervisor.thread_id = thread.id
        self.supervisor.user_id = user_id
        self.supervisor.db_session = db_session
        
        # CRITICAL: Ensure supervisor has WebSocket manager for real-time events
        if self.websocket_manager and hasattr(self.supervisor, 'agent_registry'):
            logger.info(f"Setting WebSocket manager on supervisor for user {user_id}")
            self.supervisor.agent_registry.set_websocket_manager(self.websocket_manager)
        elif self.websocket_manager is None:
            logger.warning(f"WebSocket manager not available for user {user_id} - events disabled")
        else:
            logger.warning(f"Supervisor missing agent_registry - WebSocket events may not work for user {user_id}")
    
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
        db_session: Optional[AsyncSession],
        websocket: Optional[WebSocket] = None
    ) -> None:
        """Handle switch_thread message type - join room AND load thread data"""
        thread_id = payload.get("thread_id")
        if not thread_id:
            await manager.send_error(user_id, "Thread ID required")
            return
        
        # Validate thread access and load data if database session available
        if db_session:
            thread = await self._validate_existing_thread(user_id, thread_id, db_session)
            if not thread:
                # Error already sent by _validate_existing_thread
                return
            
            # Load thread messages
            try:
                messages = await self.thread_service.get_thread_messages(thread_id, db=db_session)
                
                # Send thread data to client
                thread_data = {
                    "type": "thread_data",
                    "payload": {
                        "thread_id": thread_id,
                        "messages": [self._format_message_for_client(msg) for msg in messages],
                        "metadata": thread.metadata_
                    }
                }
                await manager.send_message(user_id, thread_data)
                logger.info(f"Sent {len(messages)} messages to user {user_id} for thread {thread_id}")
            except Exception as e:
                logger.error(f"Error loading thread messages: {e}")
                # Continue with thread switch even if message loading fails
        
        # Execute room switch
        await self._execute_thread_switch(user_id, thread_id)
        
        # Update WebSocket connection thread association if available
        if self.websocket_manager and websocket:
            connection_id = self.websocket_manager.get_connection_id_by_websocket(websocket)
            if connection_id:
                success = self.websocket_manager.update_connection_thread(connection_id, thread_id)
                if success:
                    logger.info(f"✅ Thread association updated for connection={connection_id}, thread={thread_id}")
    
    async def _execute_thread_switch(self, user_id: str, thread_id: str) -> None:
        """Execute the thread switch operation"""
        # Leave all current rooms and join new thread room
        await manager.broadcasting.leave_all_rooms(user_id)
        await manager.broadcasting.join_room(user_id, thread_id)
        logger.info(f"User {user_id} switched to thread {thread_id}")
    
    def _format_message_for_client(self, message: Message) -> Dict[str, Any]:
        """Format database message for client consumption"""
        # Extract content from the structured format
        content_value = ""
        if message.content and isinstance(message.content, list) and len(message.content) > 0:
            first_content = message.content[0]
            if isinstance(first_content, dict) and "text" in first_content:
                text_obj = first_content["text"]
                if isinstance(text_obj, dict) and "value" in text_obj:
                    content_value = text_obj["value"]
        
        return {
            "id": str(message.id),
            "role": message.role,
            "content": content_value,
            "timestamp": message.created_at if hasattr(message, 'created_at') else None,
            "metadata": message.metadata_ if hasattr(message, 'metadata_') else {}
        }

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