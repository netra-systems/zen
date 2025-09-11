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
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.dependencies import (
    get_request_scoped_db_session,
    get_user_execution_context
)
from shared.id_generation import UnifiedIdGenerator
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.websocket_core.handlers import BaseMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor
import uuid

logger = central_logger.get_logger(__name__)


class AgentMessageHandler(BaseMessageHandler):
    """Handler for agent-related WebSocket messages."""
    
    def __init__(self, message_handler_service: MessageHandlerService, websocket: Optional[WebSocket] = None):
        """Initialize with message handler service dependency and websocket."""
        super().__init__([
            MessageType.START_AGENT,
            MessageType.USER_MESSAGE,
            MessageType.CHAT
        ])
        self.message_handler_service = message_handler_service
        self.websocket = websocket
        self.processing_stats = {
            "messages_processed": 0,
            "start_agent_requests": 0,
            "user_messages": 0,
            "chat_messages": 0,
            "errors": 0,
            "last_processed_time": None
        }
    
    async def handle_message(self, user_id: str, websocket: WebSocket,
                           message: WebSocketMessage) -> bool:
        """Handle agent-related WebSocket messages with clean WebSocket pattern.
        
        CRITICAL: This uses WebSocketContext and websocket-scoped supervisor
        for complete multi-user isolation without mock Request objects.
        
        Uses the V3 clean pattern exclusively - V2 legacy patterns have been removed.
        """
        logger.debug(f"Using clean WebSocket pattern (v3) for user {user_id}")
        return await self._handle_message_v3_clean(user_id, websocket, message)

    async def _handle_message_v3_clean(self, user_id: str, websocket: WebSocket,
                                     message: WebSocketMessage) -> bool:
        """Handle WebSocket messages using clean WebSocketContext pattern.
        
        This is the NEW clean pattern that eliminates mock Request objects
        and uses honest WebSocket-specific abstractions.
        """
        processing_start = time.time()
        message_type = message.type if hasattr(message, 'type') else 'unknown'
        
        # CRITICAL: Log agent message processing start with Golden Path context
        agent_processing_context = {
            "user_id": user_id[:8] + "..." if user_id else "unknown",
            "message_type": str(message_type),
            "processing_pattern": "v3_clean_websocket",
            "thread_id": message.payload.get("thread_id") or getattr(message, 'thread_id', None),
            "run_id": message.payload.get("run_id"),
            "has_user_request": bool(message.payload.get("user_request")),
            "payload_size": len(str(message.payload)) if message.payload else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "golden_path_stage": "agent_message_processing_start"
        }
        
        logger.info(f"🤖 GOLDEN PATH AGENT PROCESSING: Starting v3 clean processing for {message_type} from user {user_id[:8] if user_id else 'unknown'}...")
        logger.info(f"🔍 AGENT PROCESSING CONTEXT: {json.dumps(agent_processing_context, indent=2)}")
        
        try:
            # Extract identifiers from message - use existing IDs for session continuity
            thread_id = message.payload.get("thread_id") or message.thread_id
            run_id = message.payload.get("run_id")
            
            # CRITICAL FIX: Use get_user_execution_context with existing IDs for session continuity
            # Pass None for missing IDs - let the session manager handle continuity
            context = get_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,  # None if not provided - maintains session continuity
                run_id=run_id  # None if not provided - allows session reuse
            )
            ws_manager = await create_websocket_manager(context)
            connection_id = None
            
            if thread_id and ws_manager:
                connection_id = ws_manager.get_connection_id_by_websocket(websocket)
                if connection_id:
                    ws_manager.update_connection_thread(connection_id, thread_id)
                    logger.debug(f"✅ THREAD ASSOCIATION: Updated connection {connection_id} → thread {thread_id}")
                else:
                    # Generate connection ID if not found using SSOT
                    connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
                    logger.warning(f"⚠️ FALLBACK CONNECTION ID: Generated {connection_id} for user {user_id[:8]}...")

            # Create clean WebSocketContext (no mock objects!)
            # Use actual context thread_id from get_user_execution_context for session continuity
            websocket_context = WebSocketContext.create_for_user(
                websocket=websocket,
                user_id=user_id,
                thread_id=context.thread_id,  # Use thread_id from execution context for session continuity
                run_id=context.run_id,  # Use run_id from execution context for session continuity
                connection_id=connection_id
            )
            
            # CRITICAL: Log WebSocket context creation success
            context_creation_details = {
                "user_id": user_id[:8] + "..." if user_id else "unknown",
                "websocket_context_id": getattr(websocket_context, 'connection_id', 'unknown'),
                "execution_context_thread_id": context.thread_id,
                "execution_context_run_id": context.run_id,
                "websocket_manager_created": ws_manager is not None,
                "connection_id": connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "golden_path_stage": "websocket_context_ready"
            }
            
            logger.info(f"🔧 GOLDEN PATH CONTEXT: WebSocket context created for user {user_id[:8] if user_id else 'unknown'}...")
            logger.debug(f"🔍 CONTEXT CREATION: {json.dumps(context_creation_details, indent=2)}")
            
            # Get database session using async generator pattern
            async for db_session in get_request_scoped_db_session():
                try:
                    # Get app_state from WebSocket connection for bridge access
                    app_state = None
                    if hasattr(websocket, 'scope') and 'app' in websocket.scope:
                        app_state = websocket.scope['app'].state
                    
                    # Create WebSocket-scoped supervisor (NO MOCK REQUEST!)
                    supervisor = await get_websocket_scoped_supervisor(
                        context=websocket_context,
                        db_session=db_session,
                        app_state=app_state  # Pass app_state for bridge access
                    )
                    
                    # Create message handler with WebSocket-scoped supervisor
                    from netra_backend.app.services.thread_service import ThreadService
                    thread_service = ThreadService()
                    message_handler = MessageHandlerService(
                        supervisor=supervisor,
                        thread_service=thread_service
                    )
                    
                    # Route message using clean v3 pattern
                    success = await self._route_agent_message_v3(
                        websocket_context, message, db_session, message_handler, websocket
                    )
                    
                    if success:
                        # CRITICAL: Log successful agent processing with event delivery expectations
                        processing_duration = time.time() - processing_start
                        
                        success_context = {
                            "user_id": user_id[:8] + "..." if user_id else "unknown",
                            "message_type": str(message_type),
                            "processing_pattern": "v3_clean_websocket",
                            "processing_duration_ms": round(processing_duration * 1000, 2),
                            "thread_id": context.thread_id,
                            "run_id": context.run_id,
                            "websocket_context_id": getattr(websocket_context, 'connection_id', 'unknown'),
                            "expected_websocket_events": [
                                "agent_started", "agent_thinking", "tool_executing", 
                                "tool_completed", "agent_completed"
                            ],
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "golden_path_milestone": "Agent processing completed successfully - expecting WebSocket events"
                        }
                        
                        self._update_processing_stats(message.type)
                        logger.info(f"✅ GOLDEN PATH AGENT SUCCESS: Processed {message_type} for user {user_id[:8] if user_id else 'unknown'}... in {processing_duration*1000:.2f}ms")
                        logger.info(f"🔍 AGENT SUCCESS CONTEXT: {json.dumps(success_context, indent=2)}")
                        logger.info(f"📡 EXPECTED EVENTS: User should receive agent_started → agent_thinking → tool_executing → tool_completed → agent_completed")
                    else:
                        # CRITICAL: Log agent processing failure with detailed context
                        processing_duration = time.time() - processing_start
                        
                        failure_context = {
                            "user_id": user_id[:8] + "..." if user_id else "unknown",
                            "message_type": str(message_type),
                            "processing_pattern": "v3_clean_websocket",
                            "processing_duration_ms": round(processing_duration * 1000, 2),
                            "thread_id": context.thread_id,
                            "run_id": context.run_id,
                            "websocket_context_id": getattr(websocket_context, 'connection_id', 'unknown'),
                            "failed_stage": "agent_message_processing",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "golden_path_impact": "CRITICAL - Agent processing failed, no WebSocket events will be sent"
                        }
                        
                        self.processing_stats["errors"] += 1
                        logger.critical(f"🚨 GOLDEN PATH AGENT FAILURE: Failed to process {message_type} for user {user_id[:8] if user_id else 'unknown'}... after {processing_duration*1000:.2f}ms")
                        logger.critical(f"🔍 AGENT FAILURE CONTEXT: {json.dumps(failure_context, indent=2)}")
                        logger.error(f"❌ NO WEBSOCKET EVENTS: User will not receive agent_started/agent_thinking/tool_executing/tool_completed/agent_completed events")
                    
                    return success
                    
                except Exception as e:
                    self.processing_stats["errors"] += 1
                    logger.error(f"Error in v3 clean pattern for user {user_id}: {e}", exc_info=True)
                    return False
                # Session automatically closed when exiting async with block
                
        except Exception as e:
            self.processing_stats["errors"] += 1
            logger.error(f"Error in v3 clean WebSocket handling for user {user_id}: {e}", exc_info=True)
            return False

    
    
    
    
    async def _route_agent_message_v3(self, websocket_context: WebSocketContext, 
                                    message: WebSocketMessage, db_session: AsyncSession, 
                                    message_handler: MessageHandlerService, websocket: WebSocket) -> bool:
        """Route message using v3 clean WebSocket pattern.
        
        This is the NEW clean method that uses WebSocketContext instead of mock Request objects.
        It provides the same isolation guarantees as v2 but with honest abstractions.
        """
        try:
            # Update WebSocket context activity
            websocket_context.update_activity()
            
            # Validate context is ready for message processing
            websocket_context.validate_for_message_processing()
            
            # All message types use the same clean v3 handler for consistency
            if message.type in [MessageType.START_AGENT, MessageType.USER_MESSAGE, MessageType.CHAT]:
                return await self._handle_message_v3(
                    websocket_context, message, db_session, message_handler, websocket
                )
            else:
                logger.warning(f"Unsupported message type in v3 clean pattern: {message.type}")
                return False
                
        except Exception as e:
            logger.error(f"Error routing v3 clean agent message: {e}", exc_info=True)
            return False

    
    async def _handle_message_v3(self, websocket_context: WebSocketContext, 
                               message: WebSocketMessage, db_session: AsyncSession, 
                               message_handler: MessageHandlerService, websocket: WebSocket) -> bool:
        """Handle ALL message types using v3 clean WebSocket pattern.
        
        This unified handler uses WebSocketContext instead of mock Request objects
        while maintaining the same isolation guarantees as v2.
        """
        try:
            payload = message.payload
            
            # Extract the user request based on message type
            if message.type == MessageType.START_AGENT:
                user_request = payload.get("user_request")
                if not user_request:
                    logger.warning(f"Missing user_request in start_agent payload for {websocket_context.user_id}")
                    return False
            elif message.type in [MessageType.USER_MESSAGE, MessageType.CHAT]:
                user_request = payload.get("message") or payload.get("content") or payload.get("text")
                if not user_request:
                    logger.warning(f"Missing message content in payload for {websocket_context.user_id}")
                    return False
            else:
                logger.warning(f"Unsupported message type in v3 clean handler: {message.type}")
                return False
            
            # Process using clean v3 isolated message handler
            if message.type == MessageType.START_AGENT:
                await message_handler.handle_start_agent(
                    user_id=websocket_context.user_id,
                    payload=payload,
                    db_session=db_session,
                    websocket=websocket
                )
            else:
                await message_handler.handle_user_message(
                    user_id=websocket_context.user_id,
                    payload=payload,
                    db_session=db_session,
                    websocket=websocket
                )
            
            logger.info(f"✅ Successfully processed {message.type} for {websocket_context.user_id} with v3 clean pattern")
            return True
            
        except Exception as e:
            error_msg = f"Error handling {message.type} for {websocket_context.user_id} with v3 clean: {e}"
            logger.error(error_msg, exc_info=True)
            
            # Send error to user via WebSocket if possible
            try:
                # FIX: Use execution context from WebSocketContext for error handling consistency
                # Don't generate new IDs - use existing context for session continuity
                context = get_user_execution_context(
                    user_id=websocket_context.user_id,
                    thread_id=websocket_context.thread_id,  # Use existing thread_id from context
                    run_id=websocket_context.run_id  # Use existing run_id from context
                )
                manager = await create_websocket_manager(context)
                await manager.send_error(
                    websocket_context.user_id, 
                    f"Failed to process {message.type}. Please try again."
                )
            except:
                pass  # Best effort to notify user
            
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
        elif message_type == MessageType.CHAT:
            self.processing_stats["chat_messages"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return self.processing_stats.copy()


# COMPATIBILITY ALIAS: Export AgentMessageHandler as AgentHandler for backward compatibility
AgentHandler = AgentMessageHandler