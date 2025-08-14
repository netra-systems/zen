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
from app.schemas.websocket_types import (
    WebSocketMessageIn,
    MessageTypeLiteral
)
from app.ws_manager import manager
from app.llm.llm_manager import LLMManager
from app.db.postgres import get_async_db
from app.dependencies import get_llm_manager
from app.services.thread_service import ThreadService
from app.services.message_handlers import MessageHandlerService
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
            data = self._parse_message(message)
            message_type = data.get("type")
            payload = data.get("payload", {})
            
            if message_type == "start_agent":
                await self.message_handler.handle_start_agent(user_id, payload, db_session)
            
            elif message_type == "user_message":
                await self.message_handler.handle_user_message(user_id, payload, db_session)
            
            elif message_type == "get_thread_history":
                await self.message_handler.handle_thread_history(user_id, db_session)
            
            elif message_type == "stop_agent":
                await self.message_handler.handle_stop_agent(user_id)
            
            elif message_type == "create_thread":
                await self.message_handler.handle_create_thread(user_id, payload, db_session)
            
            elif message_type == "switch_thread":
                await self.message_handler.handle_switch_thread(user_id, payload, db_session)
            
            elif message_type == "delete_thread":
                await self.message_handler.handle_delete_thread(user_id, payload, db_session)
            
            elif message_type == "list_threads":
                await self.message_handler.handle_list_threads(user_id, db_session)
            
            else:
                logger.warning(f"Received unhandled message type '{message_type}' for user_id: {user_id}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in websocket message from user {user_id}: {e}")
            try:
                await manager.send_error(user_id, "Invalid message format")
            except (WebSocketDisconnect, Exception):
                logger.warning(f"Could not send error to disconnected user {user_id}")
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id} during message handling")
            # Don't try to send messages to disconnected WebSocket
        except Exception as e:
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
            # Create a request model for processing
            request_model = schemas.RequestModel(
                query=message,
                id=thread_id or "default",
                user_request=message
            )
            
            # Process through supervisor
            result = await self.supervisor.run(
                message, 
                thread_id or "default",
                "default_user",
                thread_id or "default"
            )
            
            return {
                "response": str(result),
                "agent": "supervisor",
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                "response": f"Error processing message: {str(e)}",
                "agent": "supervisor", 
                "status": "error"
            }
    
    async def generate_stream(self, message: str) -> AsyncGenerator[str, None]:
        """
        Generate streaming response for a message.
        """
        logger.info(f"Starting stream for message: {message[:100]}...")
        try:
            # For now, simulate streaming by yielding parts of response
            response = await self.process_message(message)
            
            # Split response into chunks for streaming
            text = response.get("response", "")
            chunk_size = max(1, len(text) // 10)  # 10 chunks
            
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i + chunk_size]
                yield chunk
                
        except Exception as e:
            logger.error(f"Error in generate_stream: {e}", exc_info=True)
            yield f"Error: {str(e)}"

def get_agent_service(
    db_session: AsyncSession = Depends(get_async_db), 
    llm_manager: LLMManager = Depends(get_llm_manager)
) -> AgentService:
    from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
    from app.agents.tool_dispatcher import ToolDispatcher
    tool_dispatcher = ToolDispatcher(db_session)
    supervisor = Supervisor(db_session, llm_manager, manager, tool_dispatcher)
    return AgentService(supervisor)

# Module-level functions for backward compatibility with tests
async def process_message(message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
    """Module-level wrapper for AgentService.process_message for test compatibility"""
    from app.db.postgres import get_async_db
    from app.dependencies import get_llm_manager
    
    # Create dependencies
    async for db in get_async_db():
        llm_manager = get_llm_manager()
        agent_service = get_agent_service(db, llm_manager)
        result = await agent_service.process_message(message, thread_id)
        return result

async def generate_stream(message: str) -> AsyncGenerator[str, None]:
    """Module-level wrapper for AgentService.generate_stream for test compatibility"""
    from app.db.postgres import get_async_db
    from app.dependencies import get_llm_manager
    
    # Create dependencies
    async for db in get_async_db():
        llm_manager = get_llm_manager()
        agent_service = get_agent_service(db, llm_manager)
        async for chunk in agent_service.generate_stream(message):
            yield chunk
        break
