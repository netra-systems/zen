"""Refactored WebSocket Message Handler

Uses message queue system for better scalability and error handling.
"""

import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from netra_backend.app.dependencies import get_user_execution_context


from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.postgres import get_async_db
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.unit_of_work import get_unit_of_work
from netra_backend.app.services.websocket.message_queue import (
    MessagePriority,
    QueuedMessage,
    message_queue,
)
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)

class BaseMessageHandler(ABC):
    """Abstract base class for message handlers"""
    
    @abstractmethod
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle the message"""
        pass
    
    @abstractmethod
    def get_message_type(self) -> str:
        """Get the message type this handler processes"""
        pass

class StartAgentHandler(BaseMessageHandler):
    """Handler for start_agent messages"""
    
    def __init__(self, supervisor, db_session_factory):
        self.supervisor = supervisor
        self.db_session_factory = db_session_factory
    
    def get_message_type(self) -> str:
        return "start_agent"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle start_agent message"""
        try:
            await self._process_start_agent_request(user_id, payload)
        except Exception as e:
            await self._handle_agent_error(user_id, e)
    
    async def _process_start_agent_request(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Process start agent request workflow."""
        user_request = self._extract_user_request(payload)
        thread_id, run_id = await self._setup_thread_and_run(user_id, user_request)
        if not thread_id or not run_id:
            return
        response = await self._execute_agent_workflow(user_request, thread_id, user_id, run_id)
        await self._finalize_agent_response(user_id, thread_id, run_id, response)

    def _extract_user_request(self, payload: Dict[str, Any]) -> str:
        """Extract user request from payload"""
        request_data = payload.get("request", {})
        return request_data.get("query", "") or request_data.get("user_request", "")
    
    async def _setup_thread_and_run(self, user_id: str, user_request: str) -> tuple[str, str]:
        """Setup thread and run for agent processing"""
        async with get_unit_of_work() as uow:
            thread = await uow.threads.get_or_create_for_user(uow.session, user_id)
            if not thread:
                # Use session-based context for error handling
                context = get_user_execution_context(user_id=user_id)
                manager = await create_websocket_manager(context)
                await manager.send_error(user_id, "Failed to create or retrieve thread")
                return None, None
            return await self._create_message_and_run(uow, thread, user_request, user_id)
    
    async def _create_message_and_run(self, uow, thread, user_request: str, user_id: str) -> tuple[str, str]:
        """Create user message and run in database"""
        await uow.messages.create_message(
            uow.session, thread_id=thread.id, role="user",
            content=user_request, metadata={"user_id": user_id}
        )
        run = await self._create_agent_run(uow, thread)
        return thread.id, run.id
    
    async def _create_agent_run(self, uow, thread):
        """Create run for agent execution"""
        return await uow.runs.create_run(
            uow.session, thread_id=thread.id, assistant_id="netra-assistant",
            model=LLMModel.GEMINI_2_5_FLASH.value, instructions="You are Netra AI Workload Optimization Assistant"
        )
    
    async def _execute_agent_workflow(self, user_request: str, thread_id: str, user_id: str, run_id: str):
        """Execute agent workflow without holding database session"""
        self._configure_supervisor(thread_id, user_id)
        return await self.supervisor.run(user_request, thread_id, user_id, run_id)
    
    def _configure_supervisor(self, thread_id: str, user_id: str) -> None:
        """Configure supervisor properties"""
        self.supervisor.thread_id = thread_id
        self.supervisor.user_id = user_id
        self.supervisor.db_session = None
    
    async def _finalize_agent_response(self, user_id: str, thread_id: str, run_id: str, response) -> None:
        """Finalize agent response and send completion"""
        await self._save_assistant_response(thread_id, run_id, response)
        await self._send_agent_completion(user_id, response)
    
    async def _save_assistant_response(self, thread_id: str, run_id: str, response) -> None:
        """Save assistant response to database"""
        async with get_unit_of_work() as uow:
            if response:
                await self._create_assistant_message(uow, thread_id, run_id, response)
            await uow.runs.update_status(uow.session, run_id, "completed")
    
    async def _create_assistant_message(self, uow, thread_id: str, run_id: str, response) -> None:
        """Create assistant message in database."""
        content = json.dumps(response) if isinstance(response, dict) else str(response)
        await uow.messages.create_message(
            uow.session, thread_id=thread_id, role="assistant",
            content=content, assistant_id="netra-assistant", run_id=run_id
        )
    
    async def _send_agent_completion(self, user_id: str, response) -> None:
        """Send agent completion message to user"""
        # Use session-based context to maintain conversation continuity
        context = get_user_execution_context(user_id=user_id)
        manager = await create_websocket_manager(context)
        await manager.send_to_user(user_id, {
            "type": "agent_completed",
            "payload": response
        })
    
    async def _handle_agent_error(self, user_id: str, error: Exception) -> None:
        """Handle agent processing errors"""
        logger.error(f"Error handling start_agent for user {user_id}: {error}")
        # Use session-based context for error handling
        context = get_user_execution_context(user_id=user_id)
        manager = await create_websocket_manager(context)
        await manager.send_error(user_id, f"Failed to start agent: {str(error)}")

class UserMessageHandler(BaseMessageHandler):
    """Handler for user_message messages"""
    
    def __init__(self, supervisor, db_session_factory):
        self.supervisor = supervisor
        self.db_session_factory = db_session_factory
    
    def get_message_type(self) -> str:
        return "user_message"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle user_message"""
        try:
            await self._process_user_message_request(user_id, payload)
        except Exception as e:
            await self._handle_user_message_error(user_id, e)
    
    async def _process_user_message_request(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Process user message request workflow."""
        text, references = self._extract_message_data(payload)
        logger.info(f"Processing user message from {user_id}: {text[:100]}...")
        thread_id, run_id = await self._setup_user_message_thread(user_id, text, references)
        if not thread_id or not run_id:
            return
        await self._execute_user_message_workflow(user_id, text, thread_id, run_id)

    async def _execute_user_message_workflow(self, user_id: str, text: str, thread_id: str, run_id: str) -> None:
        """Execute user message workflow and finalize response."""
        response = await self._process_user_message_workflow(text, thread_id, user_id, run_id)
        await self._finalize_user_message_response(user_id, thread_id, run_id, response)

    def _extract_message_data(self, payload: Dict[str, Any]) -> tuple[str, list]:
        """Extract message data from payload"""
        text = payload.get("text", "")
        references = payload.get("references", [])
        return text, references
    
    async def _setup_user_message_thread(self, user_id: str, text: str, references: list) -> tuple[str, str]:
        """Setup thread and run for user message processing"""
        async with get_unit_of_work() as uow:
            thread = await uow.threads.get_or_create_for_user(uow.session, user_id)
            if not thread:
                # Use session-based context for error handling
                context = get_user_execution_context(user_id=user_id)
                manager = await create_websocket_manager(context)
                await manager.send_error(user_id, "Failed to create or retrieve thread")
                return None, None
            return await self._create_user_message_and_run(uow, thread, text, references)
    
    async def _create_user_message_and_run(self, uow, thread, text: str, references: list) -> tuple[str, str]:
        """Create user message and run in database"""
        metadata = {"references": references} if references else None
        await uow.messages.create_message(
            uow.session, thread.id, role="user", content=text, metadata=metadata
        )
        run = await self._create_user_message_run(uow, thread)
        return thread.id, run.id
    
    async def _create_user_message_run(self, uow, thread):
        """Create run for user message processing"""
        return await uow.runs.create_run(
            uow.session, thread_id=thread.id, assistant_id="netra-assistant",
            model=LLMModel.GEMINI_2_5_FLASH.value, instructions="You are Netra AI Workload Optimization Assistant"
        )
    
    async def _process_user_message_workflow(self, text: str, thread_id: str, user_id: str, run_id: str):
        """Process user message workflow without holding database session"""
        self._configure_message_supervisor(thread_id, user_id)
        return await self.supervisor.run(text, thread_id, user_id, run_id)
    
    def _configure_message_supervisor(self, thread_id: str, user_id: str) -> None:
        """Configure supervisor for message processing"""
        self.supervisor.thread_id = thread_id
        self.supervisor.user_id = user_id
        self.supervisor.db_session = None
    
    async def _finalize_user_message_response(self, user_id: str, thread_id: str, run_id: str, response) -> None:
        """Finalize user message response and send completion"""
        await self._save_user_message_response(thread_id, run_id, response)
        await self._send_user_message_completion(user_id, response)
    
    async def _save_user_message_response(self, thread_id: str, run_id: str, response) -> None:
        """Save user message response to database"""
        async with get_unit_of_work() as uow:
            if response:
                await uow.messages.create_message(
                    uow.session, thread_id, role="assistant", content=str(response),
                    metadata={"type": "agent_response"}, assistant_id="netra-assistant", run_id=run_id
                )
            await uow.runs.update_status(uow.session, run_id, "completed")
    
    async def _send_user_message_completion(self, user_id: str, response) -> None:
        """Send user message completion to user"""
        # Use session-based context to maintain conversation continuity
        context = get_user_execution_context(user_id=user_id)
        manager = await create_websocket_manager(context)
        await manager.send_to_user(user_id, {
            "type": "agent_completed",
            "payload": response
        })
    
    async def _handle_user_message_error(self, user_id: str, error: Exception) -> None:
        """Handle user message processing errors"""
        logger.error(f"Error processing user message: {error}")
        # Use session-based context for error handling
        context = get_user_execution_context(user_id=user_id)
        manager = await create_websocket_manager(context)
        await manager.send_to_user(user_id, {
            "type": "error", "payload": {"error": str(error)}
        })

class ThreadHistoryHandler(BaseMessageHandler):
    """Handler for get_thread_history messages"""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
    
    def get_message_type(self) -> str:
        return "get_thread_history"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle get_thread_history message"""
        try:
            async with get_unit_of_work() as uow:
                await self._process_thread_history_request(uow, user_id, payload)
        except Exception as e:
            logger.error(f"Error retrieving thread history: {e}")
            # Use session-based context for error handling
            context = get_user_execution_context(user_id=user_id)
            manager = await create_websocket_manager(context)
            await manager.send_error(user_id, "Failed to retrieve thread history")

    async def _process_thread_history_request(self, uow, user_id: str, payload: Dict[str, Any]) -> None:
        """Process thread history request with database operations."""
        thread = await uow.threads.get_or_create_for_user(uow.session, user_id)
        if not thread:
            # Use session-based context for error handling
            context = get_user_execution_context(user_id=user_id)
            manager = await create_websocket_manager(context)
            await manager.send_error(user_id, "Failed to retrieve thread")
            return
        messages = await self._get_thread_messages(uow, thread.id, payload)
        history = await self._build_message_history(messages)
        await self._send_thread_history_response(user_id, thread.id, history)

    async def _get_thread_messages(self, uow, thread_id: str, payload: Dict[str, Any]):
        """Get messages for thread with limit."""
        return await uow.messages.get_thread_messages(
            uow.session, thread_id, limit=payload.get("limit", 50)
        )

    async def _build_message_history(self, messages) -> list:
        """Build formatted message history from database messages."""
        history = []
        for msg in messages:
            content = msg.content[0]["text"]["value"] if msg.content else ""
            history.append(self._format_message_entry(msg, content))
        return history

    def _format_message_entry(self, msg, content: str) -> Dict[str, Any]:
        """Format single message entry for history."""
        return {
            "role": msg.role, "content": content,
            "created_at": msg.created_at, "id": msg.id
        }

    async def _send_thread_history_response(self, user_id: str, thread_id: str, history: list) -> None:
        """Send formatted thread history response."""
        # Use session-based context with existing thread_id to maintain continuity
        context = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        manager = await create_websocket_manager(context)
        await manager.send_to_user(user_id, {
            "type": "thread_history",
            "payload": {"thread_id": thread_id, "messages": history}
        })

class StopAgentHandler(BaseMessageHandler):
    """Handler for stop_agent messages"""
    
    def __init__(self, supervisor):
        self.supervisor = supervisor
    
    def get_message_type(self) -> str:
        return "stop_agent"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle stop_agent message"""
        logger.info(f"Stopping agent for user {user_id}")
        
        # Use session-based context to maintain conversation continuity
        context = get_user_execution_context(user_id=user_id)
        manager = await create_websocket_manager(context)
        await manager.send_to_user(
            user_id,
            {
                "type": "agent_stopped",
                "payload": {"status": "stopped"}
            }
        )

class MessageHandlerService:
    """Service for managing WebSocket message handlers"""
    
    def __init__(self, supervisor, db_session_factory):
        self.supervisor = supervisor
        self.db_session_factory = db_session_factory
        self.handlers: Dict[str, BaseMessageHandler] = {}
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Setup all message handlers"""
        handlers = self._create_handler_instances()
        self._register_all_handlers(handlers)
    
    def _create_handler_instances(self) -> list:
        """Create instances of all message handlers"""
        return [
            StartAgentHandler(self.supervisor, self.db_session_factory),
            UserMessageHandler(self.supervisor, self.db_session_factory),
            ThreadHistoryHandler(self.db_session_factory),
            StopAgentHandler(self.supervisor)
        ]
    
    def _register_all_handlers(self, handlers: list) -> None:
        """Register all handlers with the service"""
        for handler in handlers:
            self.register_handler(handler)
    
    def register_handler(self, handler: BaseMessageHandler) -> None:
        """Register a message handler"""
        message_type = handler.get_message_type()
        self.handlers[message_type] = handler
        message_queue.register_handler(message_type, handler.handle)
        logger.info(f"Registered handler for message type: {message_type}")
    
    async def handle_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """Queue a message for processing with validation"""
        try:
            await self._validate_and_process_message(user_id, message)
        except Exception as e:
            await self._handle_processing_error(user_id, e)

    async def _validate_and_process_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """Validate message format and queue for processing."""
        if not await self._validate_message_format(user_id, message):
            return
        message_type = await self._extract_message_type(user_id, message)
        if not message_type:
            return
        await self._sanitize_and_queue_message(user_id, message, message_type)
    
    async def _validate_message_format(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Validate incoming message format"""
        # Use session-based context for validation
        context = get_user_execution_context(user_id=user_id)
        manager = await create_websocket_manager(context)
        if not manager.validate_message(message):
            await manager.send_error(user_id, "Invalid message format")
            return False
        return True
    
    async def _extract_message_type(self, user_id: str, message: Dict[str, Any]) -> Optional[str]:
        """Extract and validate message type"""
        message_type = message.get("type")
        # Use session-based context for message type validation
        context = get_user_execution_context(user_id=user_id)
        manager = await create_websocket_manager(context)
        if not message_type:
            await manager.send_error(user_id, "Message type not specified")
            return None
        if message_type not in self.handlers:
            await manager.send_error(user_id, f"Unknown message type: {message_type}")
            return None
        return message_type
    
    async def _sanitize_and_queue_message(self, user_id: str, message: Dict[str, Any], message_type: str) -> None:
        """Sanitize message and add to processing queue"""
        # Use session-based context for message sanitization and queuing
        context = get_user_execution_context(user_id=user_id)
        manager = await create_websocket_manager(context)
        sanitized_message = manager.sanitize_message(message)
        priority = self._determine_priority(message_type)
        queued_message = self._create_queued_message(user_id, sanitized_message, message_type, priority)
        success = await message_queue.enqueue(queued_message)
        if not success:
            await manager.send_error(user_id, "Failed to queue message")
    
    def _create_queued_message(self, user_id: str, message: Dict[str, Any], message_type: str, priority: MessagePriority) -> QueuedMessage:
        """Create queued message object"""
        return QueuedMessage(
            user_id=user_id,
            type=message_type,
            payload=message.get("payload", {}),
            priority=priority
        )
    
    async def _handle_processing_error(self, user_id: str, error: Exception) -> None:
        """Handle message processing errors"""
        logger.error(f"Error handling message: {error}")
        # Use session-based context for error handling
        context = get_user_execution_context(user_id=user_id)
        manager = await create_websocket_manager(context)
        await manager.send_error(user_id, "Internal server error")
    
    def _determine_priority(self, message_type: str) -> MessagePriority:
        """Determine message priority based on type"""
        priority_map = self._get_priority_mapping()
        return priority_map.get(message_type, MessagePriority.NORMAL)
    
    def _get_priority_mapping(self) -> dict:
        """Get message type to priority mapping"""
        return {
            "stop_agent": MessagePriority.CRITICAL,
            "start_agent": MessagePriority.HIGH,
            "user_message": MessagePriority.NORMAL,
            "get_thread_history": MessagePriority.LOW
        }
    
    async def start_processing(self, worker_count: int = 3) -> None:
        """Start message queue processing"""
        await message_queue.process_queue(worker_count)
    
    async def stop_processing(self) -> None:
        """Stop message queue processing"""
        await message_queue.stop_processing()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get message processing statistics"""
        return await message_queue.get_queue_stats()


# MessageRouter import removed to prevent circular import
# Tests should import MessageRouter directly from message_router module