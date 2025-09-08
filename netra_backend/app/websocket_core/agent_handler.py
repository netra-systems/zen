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
import os
from typing import Any, Dict, List, Optional

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.dependencies import (
    get_request_scoped_db_session,
    create_user_execution_context,
    get_request_scoped_supervisor
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
from fastapi import Request
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
        
        CRITICAL: This now uses WebSocketContext and websocket-scoped supervisor
        for complete multi-user isolation without mock Request objects.
        
        Feature flag: USE_WEBSOCKET_SUPERVISOR_V3 controls the new clean pattern.
        """
        # Check feature flag for WebSocket supervisor v3 (clean pattern)
        # CRITICAL: V3 pattern is now DEFAULT for proper multi-user isolation
        use_v3_pattern = os.getenv("USE_WEBSOCKET_SUPERVISOR_V3", "true").lower() == "true"
        
        if use_v3_pattern:
            logger.debug(f"Using clean WebSocket pattern (v3) for user {user_id}")
            return await self._handle_message_v3_clean(user_id, websocket, message)
        else:
            logger.debug(f"Using legacy pattern (v2) with mock Request for user {user_id}")
            return await self._handle_message_v2_legacy(user_id, websocket, message)

    async def _handle_message_v3_clean(self, user_id: str, websocket: WebSocket,
                                     message: WebSocketMessage) -> bool:
        """Handle WebSocket messages using clean WebSocketContext pattern.
        
        This is the NEW clean pattern that eliminates mock Request objects
        and uses honest WebSocket-specific abstractions.
        """
        try:
            # Extract identifiers from message
            thread_id = message.payload.get("thread_id") or message.thread_id
            run_id = message.payload.get("run_id") or str(uuid.uuid4())
            
            # CRITICAL FIX: Update thread association for WebSocket routing
            # FIX: Use existing create_user_execution_context function from dependencies (already imported)
            # Use UnifiedIdGenerator for consistent ID format
            if not thread_id:
                thread_id = UnifiedIdGenerator.generate_base_id("thread")
            if not run_id:
                run_id = f"run_{thread_id}_{UnifiedIdGenerator.generate_base_id('exec', include_random=False)}"
            
            context = create_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            ws_manager = create_websocket_manager(context)
            connection_id = None
            
            if thread_id and ws_manager:
                connection_id = ws_manager.get_connection_id_by_websocket(websocket)
                if connection_id:
                    ws_manager.update_connection_thread(connection_id, thread_id)
                    logger.debug(f"Updated thread association: connection {connection_id} → thread {thread_id}")
                else:
                    # Generate connection ID if not found using SSOT
                    connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
                    logger.warning(f"Generated fallback connection ID: {connection_id}")

            # Create clean WebSocketContext (no mock objects!)
            websocket_context = WebSocketContext.create_for_user(
                websocket=websocket,
                user_id=user_id,
                thread_id=thread_id or str(uuid.uuid4()),
                run_id=run_id,
                connection_id=connection_id
            )
            
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
                        thread_service=thread_service,
                        websocket_manager=ws_manager
                    )
                    
                    # Route message using clean v3 pattern
                    success = await self._route_agent_message_v3(
                        websocket_context, message, db_session, message_handler, websocket
                    )
                    
                    if success:
                        self._update_processing_stats(message.type)
                        logger.info(f"✅ Successfully processed {message.type} for user {user_id} using v3 clean pattern")
                    else:
                        self.processing_stats["errors"] += 1
                    
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

    async def _handle_message_v2_legacy(self, user_id: str, websocket: WebSocket,
                                      message: WebSocketMessage) -> bool:
        """Handle WebSocket messages using legacy pattern with mock Request.
        
        DEPRECATED: This maintains the legacy pattern for backward compatibility
        during the gradual rollout of the clean WebSocket pattern.
        """
        try:
            # CRITICAL FIX: Update thread association when we receive a message with thread_id
            # This ensures agent events can be routed back to the correct WebSocket connection
            thread_id = message.payload.get("thread_id") or message.thread_id
            if thread_id:
                # Get WebSocket manager and update thread association
                # FIX: Use existing create_user_execution_context function from dependencies (already imported)
                # Use UnifiedIdGenerator for consistent ID format
                run_id = message.payload.get("run_id")
                if not run_id:
                    run_id = f"run_{thread_id}_{UnifiedIdGenerator.generate_base_id('exec', include_random=False)}"
                
                context = create_user_execution_context(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
                ws_manager = create_websocket_manager(context)
                if ws_manager:
                    # Get connection ID from the WebSocket instance
                    connection_id = ws_manager.get_connection_id_by_websocket(websocket)
                    if connection_id:
                        ws_manager.update_connection_thread(connection_id, thread_id)
                        logger.debug(f"Updated thread association for connection {connection_id} (user {user_id}) to thread {thread_id}")
                    else:
                        logger.warning(f"Could not find connection ID for websocket of user {user_id}")
            
            # Get database session using async generator pattern
            # CRITICAL: Using v2 factory pattern for complete isolation
            async for db_session in get_request_scoped_db_session():
                try:
                    # Create UserExecutionContext for request-scoped isolation
                    # This ensures complete multi-user safety
                    run_id = message.payload.get("run_id") or str(uuid.uuid4())
                    # Use UnifiedIdGenerator for consistent ID format
                    if not thread_id:
                        thread_id = UnifiedIdGenerator.generate_base_id("thread")
                    if not run_id:
                        run_id = f"run_{thread_id}_{UnifiedIdGenerator.generate_base_id('exec', include_random=False)}"
                    
                    user_context = create_user_execution_context(
                        user_id=user_id,
                        thread_id=thread_id,
                        run_id=run_id,
                        db_session=db_session,
                        websocket_connection_id=connection_id if connection_id else None
                    )
                    
                    # Create request-scoped supervisor using v2 factory pattern
                    # This replaces the dangerous singleton supervisor
                    mock_request = Request({"type": "websocket", "headers": []}, receive=None, send=None)
                    request_context = await self._create_request_context(user_context)
                    supervisor = await get_request_scoped_supervisor(
                        request=mock_request,
                        context=request_context,
                        db_session=db_session
                    )
                    
                    # Create request-scoped message handler with isolated supervisor
                    from netra_backend.app.services.thread_service import ThreadService
                    thread_service = ThreadService()
                    message_handler = MessageHandlerService(
                        supervisor=supervisor,
                        thread_service=thread_service,
                        websocket_manager=ws_manager
                    )
                    
                    # Route message using v2 isolated components
                    success = await self._route_agent_message_v2(
                        user_context, message, db_session, message_handler, websocket
                    )
                    
                    if success:
                        self._update_processing_stats(message.type)
                        logger.info(f"✅ Successfully processed {message.type} for user {user_id} using v2 legacy pattern")
                    else:
                        self.processing_stats["errors"] += 1
                    
                    return success
                    
                except Exception as e:
                    self.processing_stats["errors"] += 1
                    logger.error(f"Error routing agent message from {user_id} with v2 legacy: {e}", exc_info=True)
                    return False
                # Session automatically closed when exiting async with block
                
        except Exception as e:
            self.processing_stats["errors"] += 1
            logger.error(f"Error handling agent message from {user_id} with v2 legacy: {e}", exc_info=True)
            return False
    
    # Method removed - we now use get_db_dependency() directly in handle_message
    # This prevents incorrect session lifecycle management
    
    async def _create_request_context(self, user_context):
        """Create RequestScopedContext from UserExecutionContext for v2 compatibility."""
        from netra_backend.app.dependencies import RequestScopedContext
        return RequestScopedContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            request_id=user_context.request_id,
            websocket_connection_id=user_context.websocket_connection_id
        )
    
    async def _route_agent_message(self, user_id: str, message: WebSocketMessage,
                                 db_session: AsyncSession) -> bool:
        """DEPRECATED: Legacy routing method. Use _route_agent_message_v2 instead."""
        logger.warning(f"Using deprecated _route_agent_message for {user_id}. Should use v2.")
        try:
            if message.type == MessageType.START_AGENT:
                return await self._handle_start_agent(user_id, message, db_session)
            elif message.type in [MessageType.USER_MESSAGE, MessageType.CHAT]:
                return await self._handle_user_message(user_id, message, db_session)
            else:
                logger.warning(f"Unsupported message type: {message.type}")
                return False
                
        except Exception as e:
            logger.error(f"Error routing agent message: {e}", exc_info=True)
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

    async def _route_agent_message_v2(self, user_context, message: WebSocketMessage,
                                    db_session: AsyncSession, message_handler: MessageHandlerService,
                                    websocket: WebSocket) -> bool:
        """Route message using v2 factory-based isolation for multi-user safety.
        
        DEPRECATED: This is the legacy v2 method that ensures complete isolation between users.
        Use _route_agent_message_v3 for new clean WebSocket pattern.
        """
        try:
            # All message types now use the same v2 handler for consistency
            # This ensures ALL messages benefit from request-scoped isolation
            if message.type in [MessageType.START_AGENT, MessageType.USER_MESSAGE, MessageType.CHAT]:
                return await self._handle_message_v2(
                    user_context, message, db_session, message_handler, websocket
                )
            else:
                logger.warning(f"Unsupported message type: {message.type}")
                return False
                
        except Exception as e:
            logger.error(f"Error routing v2 agent message: {e}", exc_info=True)
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
                # FIX: Use existing create_user_execution_context function from dependencies (already imported)
                # Use UnifiedIdGenerator for consistent ID format
                thread_id = message.thread_id or UnifiedIdGenerator.generate_base_id("thread")
                run_id = message.payload.get("run_id") or f"run_{thread_id}_{UnifiedIdGenerator.generate_base_id('exec', include_random=False)}"
                
                context = create_user_execution_context(
                    user_id=websocket_context.user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
                manager = create_websocket_manager(context)
                await manager.send_error(
                    websocket_context.user_id, 
                    f"Failed to process {message.type}. Please try again."
                )
            except:
                pass  # Best effort to notify user
            
            return False

    async def _handle_message_v2(self, user_context, message: WebSocketMessage,
                               db_session: AsyncSession, message_handler: MessageHandlerService,
                               websocket: WebSocket) -> bool:
        """Handle ALL message types using v2 factory-based isolation.
        
        DEPRECATED: This unified handler ensures consistent request-scoped isolation
        for all message types (start_agent, user_message, chat).
        """
        try:
            payload = message.payload
            
            # Extract the user request based on message type
            if message.type == MessageType.START_AGENT:
                user_request = payload.get("user_request")
                if not user_request:
                    logger.warning(f"Missing user_request in start_agent payload for {user_context.user_id}")
                    return False
            elif message.type in [MessageType.USER_MESSAGE, MessageType.CHAT]:
                user_request = payload.get("message") or payload.get("content") or payload.get("text")
                if not user_request:
                    logger.warning(f"Missing message content in payload for {user_context.user_id}")
                    return False
            else:
                logger.warning(f"Unsupported message type in v2 handler: {message.type}")
                return False
            
            # Process using v2 isolated message handler
            if message.type == MessageType.START_AGENT:
                await message_handler.handle_start_agent(
                    user_id=user_context.user_id,
                    payload=payload,
                    db_session=db_session,
                    websocket=websocket
                )
            else:
                await message_handler.handle_user_message(
                    user_id=user_context.user_id,
                    payload=payload,
                    db_session=db_session,
                    websocket=websocket
                )
            
            logger.info(f"✅ Successfully processed {message.type} for {user_context.user_id} with v2 isolation")
            return True
            
        except Exception as e:
            error_msg = f"Error handling {message.type} for {user_context.user_id} with v2: {e}"
            logger.error(error_msg, exc_info=True)
            
            # Send error to user via WebSocket if possible
            try:
                # FIX: user_context is already available, use it directly instead of calling non-existent get_context
                context = user_context
                manager = create_websocket_manager(context)
                await manager.send_error(
                    user_context.user_id, 
                    f"Failed to process {message.type}. Please try again."
                )
            except:
                pass  # Best effort to notify user
            
            return False
    
    async def _handle_start_agent(self, user_id: str, message: WebSocketMessage,
                                db_session: AsyncSession) -> bool:
        """DEPRECATED: Legacy handler. Use _handle_message_v2 instead."""
        logger.warning(f"Using deprecated _handle_start_agent for {user_id}. Should use v2.")
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
                db_session=db_session,
                websocket=self.websocket
            )
            
            logger.info(f"Successfully processed start_agent for {user_id}")
            return True
            
        except Exception as e:
            error_msg = f"Error handling start_agent for {user_id}: {e}"
            logger.error(error_msg, exc_info=True)
            
            # Send error to user via WebSocket if possible
            try:
                # FIX: Use existing create_user_execution_context function from dependencies (already imported)
                # Use UnifiedIdGenerator for consistent ID format
                thread_id = message.thread_id or UnifiedIdGenerator.generate_base_id("thread")
                run_id = payload.get("run_id") or f"run_{thread_id}_{UnifiedIdGenerator.generate_base_id('exec', include_random=False)}"
                
                context = create_user_execution_context(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
                manager = create_websocket_manager(context)
                await manager.send_error(user_id, "Failed to start agent. Please try again.")
            except:
                pass  # Best effort to notify user
            
            # Re-raise critical errors for visibility
            if any(critical in str(e) for critical in ["UnifiedIDManager", "import", "ImportError", "ModuleNotFoundError"]):
                logger.critical(f"CRITICAL ERROR - Import/Module issue detected: {e}")
                raise  # Re-raise import errors for visibility
            
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
                db_session=db_session,
                websocket=self.websocket
            )
            
            logger.info(f"Successfully processed user_message for {user_id}")
            return True
            
        except Exception as e:
            error_msg = f"Error handling user_message for {user_id}: {e}"
            logger.error(error_msg, exc_info=True)
            
            # Send error to user via WebSocket if possible
            try:
                # FIX: Use existing create_user_execution_context function from dependencies (already imported)
                # Use UnifiedIdGenerator for consistent ID format
                thread_id = message.thread_id or UnifiedIdGenerator.generate_base_id("thread")
                run_id = payload.get("run_id") or f"run_{thread_id}_{UnifiedIdGenerator.generate_base_id('exec', include_random=False)}"
                
                context = create_user_execution_context(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
                manager = create_websocket_manager(context)
                await manager.send_error(user_id, "Failed to process message. Please try again.")
            except:
                pass  # Best effort to notify user
            
            # Re-raise critical errors for visibility
            if any(critical in str(e) for critical in ["UnifiedIDManager", "import", "ImportError", "ModuleNotFoundError"]):
                logger.critical(f"CRITICAL ERROR - Import/Module issue detected: {e}")
                raise  # Re-raise import errors for visibility
            
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