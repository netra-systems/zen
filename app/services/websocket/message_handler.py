"""Refactored WebSocket Message Handler

Uses message queue system for better scalability and error handling.
"""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.logging_config import central_logger
from app.services.database.unit_of_work import get_unit_of_work
from app.db.postgres import get_async_db
from app.services.websocket.message_queue import message_queue, QueuedMessage, MessagePriority
from app.ws_manager import manager
from abc import ABC, abstractmethod
import json

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
            request_data = payload.get("request", {})
            user_request = request_data.get("query", "") or request_data.get("user_request", "")
            
            # Create short-lived database session for initial setup
            thread_id = None
            run_id = None
            
            async with get_unit_of_work() as uow:
                thread = await uow.threads.get_or_create_for_user(uow.session, user_id)
                if not thread:
                    await manager.send_error(user_id, "Failed to create or retrieve thread")
                    return
                
                message = await uow.messages.create_message(
                    uow.session,
                    thread_id=thread.id,
                    role="user",
                    content=user_request,
                    metadata={"user_id": user_id}
                )
                
                run = await uow.runs.create_run(
                    uow.session,
                    thread_id=thread.id,
                    assistant_id="netra-assistant",
                    model="gpt-4",
                    instructions="You are Netra AI Workload Optimization Assistant"
                )
                
                thread_id = thread.id
                run_id = run.id
            
            # Set supervisor properties without holding database session
            self.supervisor.thread_id = thread_id
            self.supervisor.user_id = user_id
            self.supervisor.db_session = None  # Don't hold long-lived session
            
            # Run supervisor without holding database connection
            response = await self.supervisor.run(user_request, run_id, stream_updates=True)
            
            # Create new session for final message storage
            async with get_unit_of_work() as uow:
                if response:
                    await uow.messages.create_message(
                        uow.session,
                        thread_id=thread_id,
                        role="assistant",
                        content=json.dumps(response) if isinstance(response, dict) else str(response),
                        assistant_id="netra-assistant",
                        run_id=run_id
                    )
                
                await uow.runs.update_status(uow.session, run_id, "completed")
                
            await manager.send_message(
                user_id,
                {
                    "type": "agent_completed",
                    "payload": response
                }
            )
        except Exception as e:
            logger.error(f"Error handling start_agent for user {user_id}: {e}")
            await manager.send_error(user_id, f"Failed to start agent: {str(e)}")

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
            text = payload.get("text", "")
            references = payload.get("references", [])
            
            logger.info(f"Processing user message from {user_id}: {text[:100]}...")
            
            # Create short-lived database session for initial setup
            thread_id = None
            run_id = None
            
            async with get_unit_of_work() as uow:
                thread = await uow.threads.get_or_create_for_user(uow.session, user_id)
                
                if not thread:
                    await manager.send_error(user_id, "Failed to create or retrieve thread")
                    return
                
                await uow.messages.create_message(
                    uow.session,
                    thread.id,
                    role="user",
                    content=text,
                    metadata={"references": references} if references else None
                )
                
                run = await uow.runs.create_run(
                    uow.session,
                    thread_id=thread.id,
                    assistant_id="netra-assistant",
                    model="gpt-4",
                    instructions="You are Netra AI Workload Optimization Assistant"
                )
                
                thread_id = thread.id
                run_id = run.id
            
            # Set supervisor properties without holding database session
            self.supervisor.thread_id = thread_id
            self.supervisor.user_id = user_id
            self.supervisor.db_session = None  # Don't hold long-lived session
            
            # Run supervisor without holding database connection
            response = await self.supervisor.run(text, run_id, stream_updates=True)
            
            # Create new session for final message storage
            async with get_unit_of_work() as uow:
                if response:
                    await uow.messages.create_message(
                        uow.session,
                        thread_id,
                        role="assistant",
                        content=str(response),
                        metadata={"type": "agent_response"},
                        assistant_id="netra-assistant",
                        run_id=run_id
                    )
                
                await uow.runs.update_status(uow.session, run_id, "completed")
                
            await manager.send_message(
                user_id,
                {
                    "type": "agent_completed",
                    "payload": response
                }
            )
                
        except Exception as e:
            logger.error(f"Error processing user message: {e}")
            await manager.send_message(
                user_id,
                {
                    "type": "error",
                    "payload": {"error": str(e)}
                }
            )

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
                thread = await uow.threads.get_or_create_for_user(uow.session, user_id)
                if not thread:
                    await manager.send_error(user_id, "Failed to retrieve thread")
                    return
                
                messages = await uow.messages.get_thread_messages(
                    uow.session, 
                    thread.id,
                    limit=payload.get("limit", 50)
                )
                
                history = []
                for msg in messages:
                    content = msg.content[0]["text"]["value"] if msg.content else ""
                    history.append({
                        "role": msg.role,
                        "content": content,
                        "created_at": msg.created_at,
                        "id": msg.id
                    })
                
                await manager.send_message(
                    user_id,
                    {
                        "type": "thread_history",
                        "payload": {
                            "thread_id": thread.id,
                            "messages": history
                        }
                    }
                )
        except Exception as e:
            logger.error(f"Error retrieving thread history: {e}")
            await manager.send_error(user_id, "Failed to retrieve thread history")

class StopAgentHandler(BaseMessageHandler):
    """Handler for stop_agent messages"""
    
    def __init__(self, supervisor):
        self.supervisor = supervisor
    
    def get_message_type(self) -> str:
        return "stop_agent"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle stop_agent message"""
        logger.info(f"Stopping agent for user {user_id}")
        
        await manager.send_message(
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
        handlers = [
            StartAgentHandler(self.supervisor, self.db_session_factory),
            UserMessageHandler(self.supervisor, self.db_session_factory),
            ThreadHistoryHandler(self.db_session_factory),
            StopAgentHandler(self.supervisor)
        ]
        
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
            # Validate message first using manager's validation
            if not manager.validate_message(message):
                await manager.send_error(user_id, "Invalid message format")
                return
            
            message_type = message.get("type")
            if not message_type:
                await manager.send_error(user_id, "Message type not specified")
                return
            
            if message_type not in self.handlers:
                await manager.send_error(user_id, f"Unknown message type: {message_type}")
                return
            
            # Sanitize message
            message = manager.sanitize_message(message)
            
            priority = self._determine_priority(message_type)
            
            queued_message = QueuedMessage(
                user_id=user_id,
                type=message_type,
                payload=message.get("payload", {}),
                priority=priority
            )
            
            success = await message_queue.enqueue(queued_message)
            
            if not success:
                await manager.send_error(user_id, "Failed to queue message")
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await manager.send_error(user_id, "Internal server error")
    
    def _determine_priority(self, message_type: str) -> MessagePriority:
        """Determine message priority based on type"""
        priority_map = {
            "stop_agent": MessagePriority.CRITICAL,
            "start_agent": MessagePriority.HIGH,
            "user_message": MessagePriority.NORMAL,
            "get_thread_history": MessagePriority.LOW
        }
        return priority_map.get(message_type, MessagePriority.NORMAL)
    
    async def start_processing(self, worker_count: int = 3) -> None:
        """Start message queue processing"""
        await message_queue.process_queue(worker_count)
    
    async def stop_processing(self) -> None:
        """Stop message queue processing"""
        await message_queue.stop_processing()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get message processing statistics"""
        return await message_queue.get_queue_stats()