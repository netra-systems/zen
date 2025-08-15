# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:47:22.001085+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to core agent service
# Git: v6 | 2c55fb99 | dirty (21 uncommitted)
# Change: Feature | Scope: Component | Risk: High
# Session: bd3301c3-f917-4d5e-aa08-3dc63f6b54e2 | Seq: 1
# Review: Pending | Score: 85
# ================================
import json
from typing import Union, Dict, Any, Optional, AsyncGenerator
from starlette.websockets import WebSocketDisconnect
from app.logging_config import central_logger
from fastapi import Depends
from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app import schemas
from app.schemas.registry import (
    WebSocketMessageIn,
    MessageTypeLiteral
)
from app.ws_manager import manager
from app.llm.llm_manager import LLMManager
from app.db.postgres import get_async_db
from app.dependencies import get_llm_manager
from app.services.thread_service import ThreadService
from app.services.message_handlers import MessageHandlerService
from app.services.streaming_service import (
    StreamingService,
    TextStreamProcessor,
    get_streaming_service
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = central_logger.get_logger(__name__)

class AgentService:
    """Service for managing agent interactions following conventions"""
    
    def __init__(self, supervisor: Supervisor) -> None:
        self.supervisor = supervisor
        self.thread_service = ThreadService()
        self.message_handler = MessageHandlerService(supervisor, self.thread_service)

    async def run(self, request_model: schemas.RequestModel, run_id: str, stream_updates: bool = False) -> Any:
        """
        Starts the agent. The supervisor will stream logs back to the websocket if requested.
        """
        # Extract user_request from the request model
        user_request = request_model.user_request if hasattr(request_model, 'user_request') else str(request_model.model_dump())
        # Use default values for thread_id and user_id when not available in request_model
        thread_id = getattr(request_model, 'id', run_id)
        user_id = getattr(request_model, 'user_id', 'default_user')
        return await self.supervisor.run(user_request, thread_id, user_id, run_id)

    async def handle_websocket_message(
        self, 
        user_id: str, 
        message: Union[str, Dict[str, Any]], 
        db_session: Optional[AsyncSession] = None
    ) -> None:
        """
        Handles a message from the WebSocket.
        """
        logger.info(f"handle_websocket_message called for user_id: {user_id}")
        try:
            await self._process_websocket_message(user_id, message, db_session)
        except json.JSONDecodeError as e:
            await self._handle_json_decode_error(user_id, e)
        except WebSocketDisconnect:
            self._handle_websocket_disconnect(user_id)
        except Exception as e:
            await self._handle_general_exception(user_id, e)
    
    async def _process_websocket_message(self, user_id: str, message: Union[str, Dict[str, Any]], 
                                        db_session: Optional[AsyncSession]) -> None:
        """Process parsed websocket message."""
        data = self._parse_message(message)
        message_type = data.get("type")
        payload = data.get("payload", {})
        await self._route_message_by_type(user_id, message_type, payload, db_session)
    
    async def _route_message_by_type(self, user_id: str, message_type: str, payload: Dict[str, Any], 
                                    db_session: Optional[AsyncSession]) -> None:
        """Route message to appropriate handler based on type."""
        if message_type == "start_agent":
            await self.message_handler.handle_start_agent(user_id, payload, db_session)
        elif message_type == "user_message":
            await self.message_handler.handle_user_message(user_id, payload, db_session)
        elif message_type == "get_thread_history":
            await self.message_handler.handle_thread_history(user_id, db_session)
        elif message_type == "stop_agent":
            await self.message_handler.handle_stop_agent(user_id)
        else:
            await self._route_thread_messages(user_id, message_type, payload, db_session)
    
    async def _route_thread_messages(self, user_id: str, message_type: str, payload: Dict[str, Any], 
                                    db_session: Optional[AsyncSession]) -> None:
        """Route thread-related messages."""
        if message_type == "create_thread":
            await self.message_handler.handle_create_thread(user_id, payload, db_session)
        elif message_type == "switch_thread":
            await self.message_handler.handle_switch_thread(user_id, payload, db_session)
        elif message_type == "delete_thread":
            await self.message_handler.handle_delete_thread(user_id, payload, db_session)
        elif message_type == "list_threads":
            await self.message_handler.handle_list_threads(user_id, db_session)
        else:
            logger.warning(f"Received unhandled message type '{message_type}' for user_id: {user_id}")
    
    async def _handle_json_decode_error(self, user_id: str, e: json.JSONDecodeError) -> None:
        """Handle JSON decode error with user notification."""
        logger.error(f"Invalid JSON in websocket message from user {user_id}: {e}")
        try:
            await manager.send_error(user_id, "Invalid message format")
        except (WebSocketDisconnect, Exception):
            logger.warning(f"Could not send error to disconnected user {user_id}")
    
    def _handle_websocket_disconnect(self, user_id: str) -> None:
        """Handle WebSocket disconnection."""
        logger.info(f"WebSocket disconnected for user {user_id} during message handling")
    
    async def _handle_general_exception(self, user_id: str, e: Exception) -> None:
        """Handle general exception with error reporting."""
        logger.error(f"Error in handle_websocket_message for user_id: {user_id}: {e}", exc_info=True)
        try:
            await manager.send_error(user_id, "Internal server error")
        except (WebSocketDisconnect, Exception):
            logger.warning(f"Could not send error to disconnected user {user_id}")
    
    def _parse_message(self, message: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Parse incoming message to dictionary"""
        if isinstance(message, str):
            data = json.loads(message)
            # Handle double-encoded JSON
            if isinstance(data, str):
                data = json.loads(data)
            return data
        return message
    
    async def process_message(self, message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a message and return a structured response.
        """
        logger.info(f"Processing message: {message[:100]}...")
        try:
            return await self._execute_message_processing(message, thread_id)
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return self._create_error_response(str(e))
    
    async def _execute_message_processing(self, message: str, thread_id: Optional[str]) -> Dict[str, Any]:
        """Execute message processing through supervisor."""
        request_model = self._create_request_model(message, thread_id)
        result = await self._run_supervisor(message, thread_id)
        return self._create_success_response(str(result))
    
    def _create_request_model(self, message: str, thread_id: Optional[str]) -> schemas.RequestModel:
        """Create request model for message processing."""
        return schemas.RequestModel(
            query=message,
            id=thread_id or "default",
            user_request=message
        )
    
    async def _run_supervisor(self, message: str, thread_id: Optional[str]):
        """Run message through supervisor agent."""
        return await self.supervisor.run(
            message, 
            thread_id or "default",
            "default_user",
            thread_id or "default"
        )
    
    def _create_success_response(self, result: str) -> Dict[str, Any]:
        """Create successful response structure."""
        return {
            "response": result,
            "agent": "supervisor",
            "status": "success"
        }
    
    def _create_error_response(self, error: str) -> Dict[str, Any]:
        """Create error response structure."""
        return {
            "response": f"Error processing message: {error}",
            "agent": "supervisor", 
            "status": "error"
        }
    
    async def generate_stream(self, message: str, thread_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate true streaming response for a message.
        Returns structured chunks with metadata.
        """
        logger.info(f"Starting stream for message: {message[:100]}...")
        streaming_service = get_streaming_service()
        processor = self._create_response_processor(message, thread_id)
        async for chunk in streaming_service.create_stream(processor, None):
            yield chunk.to_dict()
    
    def _create_response_processor(self, message: str, thread_id: Optional[str]):
        """Create response processor for streaming."""
        class AgentResponseProcessor:
            def __init__(self, supervisor, message, thread_id):
                self.supervisor = supervisor
                self.message = message
                self.thread_id = thread_id
            
            async def process(self, _):
                async for chunk in self._generate_response_chunks():
                    yield chunk
            
            async def _generate_response_chunks(self):
                """Generate response chunks from supervisor."""
                result = await self._run_supervisor_for_stream()
                content = self._extract_content(result)
                text_processor = TextStreamProcessor(chunk_size=5)
                async for chunk in text_processor.process(content):
                    yield chunk
            
            async def _run_supervisor_for_stream(self):
                """Run supervisor for streaming response."""
                return await self.supervisor.run(
                    self.message,
                    self.thread_id or "default",
                    "default_user",
                    self.thread_id or "default"
                )
            
            def _extract_content(self, result) -> str:
                """Extract content from supervisor result."""
                if hasattr(result, 'response'):
                    return str(result.response)
                return str(result)
        
        return AgentResponseProcessor(self.supervisor, message, thread_id)

def get_agent_service(
    db_session: AsyncSession = Depends(get_async_db), 
    llm_manager: LLMManager = Depends(get_llm_manager)
) -> AgentService:
    supervisor = _create_supervisor_agent(db_session, llm_manager)
    return AgentService(supervisor)

def _create_supervisor_agent(db_session: AsyncSession, llm_manager: LLMManager):
    """Create configured supervisor agent."""
    from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
    from app.agents.tool_dispatcher import ToolDispatcher
    tool_dispatcher = ToolDispatcher(db_session)
    return Supervisor(db_session, llm_manager, manager, tool_dispatcher)

# Module-level functions for backward compatibility with tests
async def process_message(message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
    """Module-level wrapper for AgentService.process_message for test compatibility"""
    from app.db.postgres import get_async_db
    from app.dependencies import get_llm_manager
    
    async with get_async_db() as db:
        return await _execute_module_process_message(db, message, thread_id)

async def _execute_module_process_message(db, message: str, thread_id: Optional[str]) -> Dict[str, Any]:
    """Execute module-level message processing."""
    llm_manager = get_llm_manager()
    agent_service = get_agent_service(db, llm_manager)
    return await agent_service.process_message(message, thread_id)

async def generate_stream(message: str, thread_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
    """Module-level wrapper for AgentService.generate_stream for test compatibility"""
    from app.db.postgres import get_async_db
    from app.config import settings
    
    async with get_async_db() as db:
        async for chunk in _execute_module_generate_stream(db, message, thread_id):
            yield chunk

async def _execute_module_generate_stream(db, message: str, thread_id: Optional[str]) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute module-level stream generation."""
    llm_manager = LLMManager(settings)
    agent_service = get_agent_service(db, llm_manager)
    async for chunk in agent_service.generate_stream(message, thread_id):
        yield chunk
