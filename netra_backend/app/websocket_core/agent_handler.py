"""
Agent Message Handler for WebSocket Communication

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Agent Integration
- Value Impact: Connects WebSocket infrastructure to agent execution
- Strategic Impact: Enables real-time AI agent communication

Integrates the WebSocket message router with the agent execution engine.
Handles "start_agent" and "user_message" message types with proper database session management.
"""

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.dependencies import get_db_dependency
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.websocket_core.handlers import BaseMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage

logger = central_logger.get_logger(__name__)


class AgentMessageHandler(BaseMessageHandler):
    """Handler for agent-related WebSocket messages."""
    
    def __init__(self, message_handler_service: MessageHandlerService):
        """Initialize with message handler service dependency."""
        super().__init__([
            MessageType.START_AGENT,
            MessageType.USER_MESSAGE
        ])
        self.message_handler_service = message_handler_service
        self.processing_stats = {
            "messages_processed": 0,
            "start_agent_requests": 0,
            "user_messages": 0,
            "errors": 0,
            "last_processed_time": None
        }
    
    async def handle_message(self, user_id: str, websocket: WebSocket,
                           message: WebSocketMessage) -> bool:
        """Handle agent-related WebSocket messages with database session."""
        try:
            # Get database session for this message handling
            db_session = await self._get_database_session()
            if not db_session:
                logger.error(f"Failed to get database session for user {user_id}")
                return False
            
            try:
                # Route message to appropriate handler
                success = await self._route_agent_message(
                    user_id, message, db_session
                )
                
                if success:
                    self._update_processing_stats(message.type)
                else:
                    self.processing_stats["errors"] += 1
                
                return success
                
            finally:
                # Ensure database session is properly closed
                await db_session.close()
                
        except Exception as e:
            self.processing_stats["errors"] += 1
            logger.error(f"Error handling agent message from {user_id}: {e}", exc_info=True)
            return False
    
    async def _get_database_session(self) -> Optional[AsyncSession]:
        """Get database session using dependency injection pattern."""
        try:
            # Use the same dependency that FastAPI routes use
            async for session in get_db_dependency():
                return session
        except Exception as e:
            logger.error(f"Failed to get database session: {e}")
            return None
    
    async def _route_agent_message(self, user_id: str, message: WebSocketMessage,
                                 db_session: AsyncSession) -> bool:
        """Route message to appropriate message handler service method."""
        try:
            if message.type == MessageType.START_AGENT:
                return await self._handle_start_agent(user_id, message, db_session)
            elif message.type == MessageType.USER_MESSAGE:
                return await self._handle_user_message(user_id, message, db_session)
            else:
                logger.warning(f"Unsupported message type: {message.type}")
                return False
                
        except Exception as e:
            logger.error(f"Error routing agent message: {e}", exc_info=True)
            return False
    
    async def _handle_start_agent(self, user_id: str, message: WebSocketMessage,
                                db_session: AsyncSession) -> bool:
        """Handle start_agent message type."""
        try:
            payload = message.payload
            
            # Validate required payload fields
            if not payload.get("user_request"):
                logger.warning(f"Missing user_request in start_agent payload for {user_id}")
                return False
            
            # Call message handler service
            await self.message_handler_service.handle_start_agent(
                user_id=user_id,
                payload=payload,
                db_session=db_session
            )
            
            logger.info(f"Successfully processed start_agent for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling start_agent for {user_id}: {e}", exc_info=True)
            return False
    
    async def _handle_user_message(self, user_id: str, message: WebSocketMessage,
                                 db_session: AsyncSession) -> bool:
        """Handle user_message message type."""
        try:
            payload = message.payload
            
            # Validate payload has content
            content = payload.get("content") or payload.get("text", "")
            if not content or not content.strip():
                logger.warning(f"Empty user message from {user_id}")
                return False
            
            # Call message handler service
            await self.message_handler_service.handle_user_message(
                user_id=user_id,
                payload=payload,
                db_session=db_session
            )
            
            logger.info(f"Successfully processed user_message for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling user_message for {user_id}: {e}", exc_info=True)
            return False
    
    def _update_processing_stats(self, message_type: MessageType) -> None:
        """Update processing statistics."""
        import time
        
        self.processing_stats["messages_processed"] += 1
        self.processing_stats["last_processed_time"] = time.time()
        
        if message_type == MessageType.START_AGENT:
            self.processing_stats["start_agent_requests"] += 1
        elif message_type == MessageType.USER_MESSAGE:
            self.processing_stats["user_messages"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return self.processing_stats.copy()