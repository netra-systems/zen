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
from typing import Union, Dict, Any, Optional
from starlette.websockets import WebSocketDisconnect
from app.logging_config import central_logger
from fastapi import Depends
from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app import schemas
from app.schemas.websocket_types import (
    WebSocketMessageIn,
    ParsedMessage,
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
        return await self.supervisor.run(user_request, run_id, stream_updates)

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
    
    def _parse_message(self, message: Union[str, Dict[str, Any]]) -> ParsedMessage:
        """Parse incoming message to dictionary"""
        if isinstance(message, str):
            data = json.loads(message)
            # Handle double-encoded JSON
            if isinstance(data, str):
                data = json.loads(data)
            return data
        return message

def get_agent_service(
    db_session: AsyncSession = Depends(get_async_db), 
    llm_manager: LLMManager = Depends(get_llm_manager)
) -> AgentService:
    from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
    from app.agents.tool_dispatcher import ToolDispatcher
    tool_dispatcher = ToolDispatcher(db_session)
    supervisor = Supervisor(db_session, llm_manager, manager, tool_dispatcher)
    return AgentService(supervisor)
