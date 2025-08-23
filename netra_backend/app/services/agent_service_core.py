"""Core agent service implementation.

Provides the main AgentService class with core functionality
for agent interactions and WebSocket message handling.
"""

import json
from typing import Any, AsyncGenerator, Dict, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect

from netra_backend.app import schemas
from netra_backend.app.agents.supervisor_consolidated import (
    SupervisorAgent as Supervisor,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.service_interfaces import IAgentService
from netra_backend.app.services.streaming_service import (
    TextStreamProcessor,
    get_streaming_service,
)
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.websocket_core import get_websocket_manager
manager = get_websocket_manager()

logger = central_logger.get_logger(__name__)


class AgentService(IAgentService):
    """Service for managing agent interactions following conventions"""
    
    def __init__(self, supervisor: Supervisor) -> None:
        self.supervisor = supervisor
        self.thread_service = ThreadService()
        self.message_handler = MessageHandlerService(supervisor, self.thread_service)

    async def run(self, request_model: schemas.RequestModel, run_id: str, stream_updates: bool = False) -> Any:
        """Starts the agent. The supervisor will stream logs back to the websocket if requested."""
        user_request = request_model.user_request if hasattr(request_model, 'user_request') else str(request_model.model_dump())
        thread_id = getattr(request_model, 'id', run_id)
        user_id = getattr(request_model, 'user_id', 'default_user')
        return await self.supervisor.run(user_request, thread_id, user_id, run_id)

    async def start_agent(self, request_model, run_id: str, stream_updates: bool = False):
        """Start an agent with the given request model and run ID."""
        return await self.run(request_model, run_id, stream_updates)

    async def stop_agent(self, user_id: str) -> bool:
        """Stop an agent for the given user."""
        try:
            await manager.send_message(user_id, {"type": "agent_stopped"})
            return True
        except Exception as e:
            logger.error(f"Failed to stop agent for user {user_id}: {e}")
            return False

    async def get_agent_status(self, user_id: str) -> Dict[str, Any]:
        """Get the status of an agent for the given user."""
        return {
            "user_id": user_id,
            "status": "active",
            "supervisor_available": self.supervisor is not None
        }

    async def handle_websocket_message(
        self, 
        user_id: str, 
        message: Union[str, Dict[str, Any]], 
        db_session: Optional[AsyncSession] = None
    ) -> None:
        """Handles a message from the WebSocket."""
        logger.info(f"[AGENT SERVICE] Processing WebSocket message for user {user_id}: {type(message)}")
        await self._handle_message_with_error_handling(user_id, message, db_session)
        logger.info(f"[AGENT SERVICE] Completed WebSocket message processing for user {user_id}")
    
    async def _handle_message_with_error_handling(
        self, user_id: str, message: Union[str, Dict[str, Any]], 
        db_session: Optional[AsyncSession]
    ) -> None:
        """Handle message with comprehensive error handling."""
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
        
        # Validate message type is present
        if not message_type:
            await manager.send_error(user_id, "Message type is required")
            return
            
        payload = data.get("payload", {})
        await self._route_message_by_type(user_id, message_type, payload, db_session)
    
    async def _route_message_by_type(self, user_id: str, message_type: str, payload: Dict[str, Any], 
                                    db_session: Optional[AsyncSession]) -> None:
        """Route message to appropriate handler based on type."""
        if await self._handle_standard_message_types(user_id, message_type, payload, db_session):
            return
        await self._route_thread_messages(user_id, message_type, payload, db_session)
    
    async def _handle_standard_message_types(
        self, user_id: str, message_type: str, payload: Dict[str, Any], 
        db_session: Optional[AsyncSession]
    ) -> bool:
        """Handle standard message types, return True if handled."""
        if message_type == "start_agent":
            logger.info(f"Processing start_agent for user {user_id}")
            await self.message_handler.handle_start_agent(user_id, payload, db_session)
        elif message_type == "user_message":
            logger.info(f"Processing user_message for user {user_id}, payload keys: {list(payload.keys())}")
            await self.message_handler.handle_user_message(user_id, payload, db_session)
        elif message_type == "example_message":
            logger.info(f"Processing example_message for user {user_id}")
            await self.message_handler.handle_example_message(user_id, payload, db_session)
        elif message_type == "get_thread_history":
            await self.message_handler.handle_thread_history(user_id, db_session)
        elif message_type == "stop_agent":
            await self.message_handler.handle_stop_agent(user_id)
        elif message_type == "get_conversation_history":
            await self.message_handler.handle_get_conversation_history(user_id, payload, db_session)
        elif message_type == "get_agent_context":
            await self.message_handler.handle_get_agent_context(user_id, payload, db_session)
        else:
            return False
        return True
    
    async def _route_thread_messages(self, user_id: str, message_type: str, payload: Dict[str, Any], 
                                    db_session: Optional[AsyncSession]) -> None:
        """Route thread-related messages."""
        if await self._handle_thread_message_types(user_id, message_type, payload, db_session):
            return
        logger.warning(f"Received unhandled message type '{message_type}' for user_id: {user_id}")
        # Send error to user for unknown message type
        await manager.send_error(user_id, f"Unknown message type: {message_type}")
    
    async def _handle_thread_message_types(
        self, user_id: str, message_type: str, payload: Dict[str, Any], 
        db_session: Optional[AsyncSession]
    ) -> bool:
        """Handle thread message types, return True if handled."""
        if message_type == "create_thread":
            await self.message_handler.handle_create_thread(user_id, payload, db_session)
        elif message_type == "switch_thread":
            await self.message_handler.handle_switch_thread(user_id, payload, db_session)
        elif message_type == "delete_thread":
            await self.message_handler.handle_delete_thread(user_id, payload, db_session)
        elif message_type == "list_threads":
            await self.message_handler.handle_list_threads(user_id, db_session)
        else:
            return False
        return True
    
    async def _handle_json_decode_error(self, user_id: str, e: json.JSONDecodeError) -> None:
        """Handle JSON decode error with user notification."""
        logger.error(f"Invalid JSON in websocket message from user {user_id}: {e}")
        try:
            await manager.send_error(user_id, "Invalid JSON message format")
        except (WebSocketDisconnect, Exception):
            logger.warning(f"Could not send error to disconnected user {user_id}")
    
    def _handle_websocket_disconnect(self, user_id: str) -> None:
        """Handle WebSocket disconnection."""
        logger.info(f"WebSocket disconnected for user {user_id} during message handling")
    
    async def _handle_general_exception(self, user_id: str, e: Exception) -> None:
        """Handle general exception with error reporting."""
        logger.error(f"Error in handle_websocket_message for user_id: {user_id}: {e}", exc_info=True)
        
        # Provide more specific error messages based on exception type
        error_message = "Internal server error"
        if isinstance(e, (TypeError, AttributeError)):
            error_message = "Invalid message format or structure"
        elif isinstance(e, KeyError):
            error_message = f"Missing required field: {str(e)}"
        elif isinstance(e, ValueError):
            error_message = f"Invalid value: {str(e)}"
            
        try:
            await manager.send_error(user_id, error_message)
        except (WebSocketDisconnect, Exception):
            logger.warning(f"Could not send error to disconnected user {user_id}")
    
    def _parse_message(self, message: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Parse incoming message to dictionary"""
        if isinstance(message, str):
            data = json.loads(message)
            if isinstance(data, str):
                data = json.loads(data)
            return data
        return message
    
    async def process_message(self, message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a message and return a structured response."""
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
        """Generate true streaming response for a message."""
        logger.info(f"Starting stream for message: {message[:100]}...")
        streaming_service = get_streaming_service()
        processor = self._create_response_processor(message, thread_id)
        async for chunk in streaming_service.create_stream(processor, None):
            yield chunk.to_dict()
    
    def _create_response_processor(self, message: str, thread_id: Optional[str]):
        """Create response processor for streaming."""
        from netra_backend.app.services.agent_service_streaming import AgentResponseProcessor
        return AgentResponseProcessor(self.supervisor, message, thread_id)