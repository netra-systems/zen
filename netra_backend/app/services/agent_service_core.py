"""Core agent service implementation.

Provides the main AgentService class with core functionality
for agent interactions and WebSocket message handling.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect

from netra_backend.app import schemas
from netra_backend.app.agents.supervisor_consolidated import (
    SupervisorAgent as Supervisor,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.service_interfaces import IAgentService
from netra_backend.app.services.streaming_service import (
    TextStreamProcessor,
    get_streaming_service,
)
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.websocket_core import create_websocket_manager
from shared.id_generation import UnifiedIdGenerator
from netra_backend.app.dependencies import get_user_session_context

logger = central_logger.get_logger(__name__)


class AgentService(IAgentService):
    """Service for managing agent interactions following conventions"""
    
    def __init__(self, supervisor: Supervisor) -> None:
        """Initialize AgentService with clean bridge-based integration."""
        self.supervisor = supervisor
        self.thread_service = ThreadService()
        
        # Bridge-based WebSocket integration (SSOT)
        self._bridge = None
        self._bridge_initialized = False
        
        # Initialize message handler (bridge will provide WebSocket manager)
        self.message_handler = MessageHandlerService(supervisor, self.thread_service)
        
        # Bridge integration will be initialized on first use (event loop safe)
        # No longer call asyncio.create_task during __init__ as no event loop exists yet

    async def _initialize_bridge_integration(self) -> None:
        """Initialize WebSocket-Agent integration through bridge (SSOT for integration)."""
        try:
            # Create non-singleton bridge instance (SECURITY CRITICAL: prevents cross-user leakage)
            self._bridge = AgentWebSocketBridge()
            
            # Ensure complete integration with all components
            registry = getattr(self.supervisor, 'registry', None)
            result = await self._bridge.ensure_integration(
                supervisor=self.supervisor,
                registry=registry
            )
            
            if result.success:
                self._bridge_initialized = True
                
                # Update message handler with bridge-managed WebSocket manager
                await self._configure_message_handler_websocket()
                
                logger.info(f"Bridge integration complete in {result.duration_ms:.1f}ms")
            else:
                logger.error(f"Bridge integration failed: {result.error}")
                
        except Exception as e:
            logger.error(f"Failed to initialize bridge integration: {e}")
    
    async def _configure_message_handler_websocket(self) -> None:
        """Configure message handler with bridge-managed WebSocket manager."""
        try:
            if self._bridge and self._bridge._websocket_manager:
                # Update message handler with WebSocket manager from bridge
                self.message_handler._websocket_manager = self._bridge._websocket_manager
                logger.debug("Message handler configured with bridge-managed WebSocket manager")
        except Exception as e:
            logger.error(f"Failed to configure message handler WebSocket: {e}")
    
    async def _ensure_bridge_ready(self) -> bool:
        """Ensure bridge is ready for use, with idempotent retry and recovery."""
        # First check: if not initialized at all, initialize now (safe with event loop)
        if not self._bridge_initialized or not self._bridge:
            logger.debug("Bridge not initialized, initializing now")
            await self._initialize_bridge_integration()
        
        # Quick path: already initialized and healthy
        if self._bridge_initialized and self._bridge:
            try:
                status = await self._bridge.get_status()
                if status["state"] == "active":
                    return True
                # Bridge exists but not active - fall through to recovery
                logger.debug("Bridge exists but not active, attempting recovery")
            except Exception:
                # Bridge status check failed - fall through to full recovery
                logger.debug("Bridge status check failed, attempting full recovery")
        
        # Full recovery path: re-initialize everything idempotently
        return await self._recover_bridge_integration()
    
    async def _recover_bridge_integration(self) -> bool:
        """Idempotent bridge integration recovery."""
        try:
            # Create new bridge instance (SECURITY CRITICAL: prevents cross-user leakage)
            self._bridge = AgentWebSocketBridge()
            
            # Ensure integration with all components (idempotent)
            registry = getattr(self.supervisor, 'registry', None)
            result = await self._bridge.ensure_integration(
                supervisor=self.supervisor,
                registry=registry,
                force_reinit=True  # Force re-initialization for recovery
            )
            
            if result.success:
                self._bridge_initialized = True
                
                # Ensure message handler is properly configured (idempotent)
                await self._configure_message_handler_websocket()
                
                logger.info(f"Bridge recovery successful in {result.duration_ms:.1f}ms")
                return True
            else:
                logger.error(f"Bridge recovery failed: {result.error}")
                self._bridge_initialized = False
                return False
                
        except Exception as e:
            logger.error(f"Bridge recovery exception: {e}")
            self._bridge_initialized = False
            return False
    
    async def ensure_service_ready(self) -> bool:
        """Idempotent method to ensure entire service is ready for operations."""
        try:
            # Ensure bridge is ready
            bridge_ready = await self._ensure_bridge_ready()
            
            # Ensure message handler has WebSocket manager (idempotent)
            if bridge_ready:
                await self._configure_message_handler_websocket()
            
            # Basic service components check
            service_ready = (
                self.supervisor is not None and
                self.thread_service is not None and
                self.message_handler is not None
            )
            
            ready_status = bridge_ready and service_ready
            
            if ready_status:
                logger.debug("AgentService fully ready for operations")
            else:
                logger.warning(f"AgentService partial readiness: bridge={bridge_ready}, service={service_ready}")
                
            return ready_status
            
        except Exception as e:
            logger.error(f"Service readiness check failed: {e}")
            return False

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
            # Use bridge-managed WebSocket manager if available
            if await self._ensure_bridge_ready():
                status = await self._bridge.get_status()
                if status["dependencies"]["websocket_manager_available"]:
                    # Use session-based context to maintain conversation continuity  
                    user_context = await get_user_session_context(user_id=user_id)
                    websocket_manager = create_websocket_manager(user_context)
                    await websocket_manager.send_to_user(user_id, {"type": "agent_stopped"})
                    return True
            
            # Fallback to direct manager access (preserve existing behavior)
            # Use SSOT for fallback context creation
            # Use session-based context for fallback scenario
            fallback_context = await get_user_session_context(user_id=user_id)
            websocket_manager = create_websocket_manager(fallback_context)
            await websocket_manager.send_to_user(user_id, {"type": "agent_stopped"})
            return True
        except Exception as e:
            logger.error(f"Failed to stop agent for user {user_id}: {e}")
            return False

    async def get_agent_status(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive agent service status for a user."""
        # Base agent status
        status = {
            "user_id": user_id,
            "status": "active",
            "supervisor_available": self.supervisor is not None,
            "thread_service_available": self.thread_service is not None,
            "message_handler_available": self.message_handler is not None
        }
        
        # Add comprehensive integration status
        service_ready = await self.ensure_service_ready()
        if service_ready and self._bridge:
            bridge_status = await self._bridge.get_status()
            status.update({
                "service_ready": True,
                "bridge_integrated": True,
                "websocket_integration": bridge_status["state"],
                "websocket_healthy": bridge_status["health"]["websocket_manager_healthy"],
                "registry_healthy": bridge_status["health"]["registry_healthy"]
            })
        else:
            status.update({
                "service_ready": service_ready,
                "bridge_integrated": False,
                "websocket_integration": "unavailable",
                "websocket_healthy": False,
                "registry_healthy": False
            })
        
        return status
    
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive service status including bridge metrics."""
        base_status = {
            "service": "AgentService",
            "supervisor": {
                "available": self.supervisor is not None,
                "registry_available": hasattr(self.supervisor, 'registry') and self.supervisor.registry is not None
            },
            "thread_service": {
                "available": self.thread_service is not None
            },
            "message_handler": {
                "available": self.message_handler is not None
            }
        }
        
        # Add bridge status if available
        if self._bridge:
            try:
                bridge_status = await self._bridge.get_status()
                base_status["bridge"] = bridge_status
            except Exception as e:
                base_status["bridge"] = {"error": str(e), "available": False}
        else:
            base_status["bridge"] = {"available": False, "initialized": self._bridge_initialized}
        
        return base_status

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
        # Extract context data early for use in error handlers
        context_data = None
        try:
            # Attempt to parse message to extract context data for error handling
            parsed_data = self._parse_message(message)
            payload = parsed_data.get("payload", {})
            context_data = {
                "thread_id": payload.get("thread_id"),
                "run_id": payload.get("run_id"),
                "request_id": payload.get("request_id")
            }
        except Exception:
            # If parsing fails, we'll handle it in the JSON decode error handler
            pass
        
        try:
            await self._process_websocket_message(user_id, message, db_session)
        except json.JSONDecodeError as e:
            await self._handle_json_decode_error(user_id, e, context_data)
        except WebSocketDisconnect:
            self._handle_websocket_disconnect(user_id)
        except Exception as e:
            await self._handle_general_exception(user_id, e, context_data)
    
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
        # Send error to user for unknown message type (through bridge-managed WebSocket)
        try:
            # Use session-based context for error handling with available payload context
            # Extract thread_id from payload if available
            thread_id = payload.get("thread_id") if payload else None
            error_context = await get_user_session_context(user_id=user_id, thread_id=thread_id)
            websocket_manager = create_websocket_manager(error_context)
            await websocket_manager.send_error(user_id, f"Unknown message type: {message_type}")
        except Exception as e:
            logger.error(f"Failed to send unknown message type error to {user_id}: {e}")
    
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
    
    async def _handle_json_decode_error(self, user_id: str, e: json.JSONDecodeError, context_data: Optional[Dict[str, Any]] = None) -> None:
        """Handle JSON decode error with user notification (WebSocket boundary)."""
        logger.error(f"Invalid JSON in websocket message from user {user_id}: {e}")
        try:
            # Use bridge-managed WebSocket communication (preserve boundary)
            # Use session-based context with all available context data
            if context_data and any(context_data.values()):
                # Use SSOT method with all known context data
                json_error_context = await get_user_session_context(
                    user_id=user_id,
                    thread_id=context_data.get("thread_id"),
                    run_id=context_data.get("run_id")
                )
            else:
                # Fallback to session-based context for JSON error handling
                json_error_context = await get_user_session_context(user_id=user_id)
            websocket_manager = create_websocket_manager(json_error_context)
            await websocket_manager.send_error(user_id, "Invalid JSON message format")
        except (WebSocketDisconnect, Exception):
            logger.warning(f"Could not send error to disconnected user {user_id}")
    
    def _handle_websocket_disconnect(self, user_id: str) -> None:
        """Handle WebSocket disconnection (WebSocket boundary)."""
        logger.info(f"WebSocket disconnected for user {user_id} during message handling")
    
    async def _handle_general_exception(self, user_id: str, e: Exception, context_data: Optional[Dict[str, Any]] = None) -> None:
        """Handle general exception with error reporting (Agent boundary + WebSocket communication)."""
        logger.error(f"Error in handle_websocket_message for user_id: {user_id}: {e}", exc_info=True)
        
        # Agent concern: Determine appropriate error message based on exception type
        error_message = "Internal server error"
        if isinstance(e, (TypeError, AttributeError)):
            error_message = "Invalid message format or structure"
        elif isinstance(e, KeyError):
            error_message = f"Missing required field: {str(e)}"
        elif isinstance(e, ValueError):
            error_message = f"Invalid value: {str(e)}"
            
        # WebSocket concern: Send error through WebSocket channel
        try:
            # Use session-based context with all available context data
            if context_data and any(context_data.values()):
                # Use SSOT method with all known context data
                exception_context = await get_user_session_context(
                    user_id=user_id,
                    thread_id=context_data.get("thread_id"),
                    run_id=context_data.get("run_id")
                )
            else:
                # Fallback to session-based context for exception handling
                exception_context = await get_user_session_context(user_id=user_id)
            websocket_manager = create_websocket_manager(exception_context)
            await websocket_manager.send_error(user_id, error_message)
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
    
    async def execute_agent(
        self, 
        agent_type: str, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """Execute an agent task using the AgentWebSocketBridge.
        
        This method uses the bridge for WebSocket-Agent coordination,
        ensuring proper event delivery and lifecycle management.
        """
        logger.info(f"Executing {agent_type} agent for user {user_id}")
        
        try:
            # Ensure service is fully ready for execution (idempotent)
            if not await self.ensure_service_ready():
                logger.warning("Service not fully ready, executing without WebSocket coordination")
                return await self._execute_agent_fallback(agent_type, message, context, user_id)
            
            # Get orchestrator through bridge
            status = await self._bridge.get_status()
            if not status["dependencies"]["orchestrator_available"]:
                logger.warning("Orchestrator not available, using fallback execution")
                return await self._execute_agent_fallback(agent_type, message, context, user_id)
            
            # Get orchestrator from bridge's internal state (cleaner access)
            orchestrator = self._bridge._orchestrator
            
            # Create execution context with deduplication
            exec_context, notifier = await orchestrator.create_execution_context(
                agent_type=agent_type,
                user_id=user_id,
                message=message,
                context=context
            )
            
            # Send thinking event
            await notifier.send_agent_thinking(
                exec_context, 
                f"Processing {agent_type} request"
            )
            
            # Execute through supervisor
            full_message = f"[Agent Type: {agent_type}] {message}"
            if context:
                full_message += f" (Context: {context})"
                
            result = await self.supervisor.run(
                full_message, 
                exec_context.thread_id,
                user_id,
                exec_context.run_id
            )
            
            # Complete execution with proper cleanup
            await orchestrator.complete_execution(exec_context, result)
            
            return {
                "response": str(result),
                "agent": agent_type,
                "status": "success",
                "user_id": user_id,
                "websocket_events_sent": True,
                "bridge_coordinated": True
            }
            
        except Exception as e:
            logger.error(f"Error executing {agent_type} agent: {e}", exc_info=True)
            
            # Ensure completion event is sent even on error (best effort)
            if 'exec_context' in locals() and 'orchestrator' in locals():
                try:
                    await orchestrator.complete_execution(exec_context, None)
                except Exception:
                    pass  # Best effort cleanup
            
            return {
                "response": f"Error executing {agent_type} agent: {str(e)}",
                "agent": agent_type,
                "status": "error",
                "user_id": user_id,
                "error": str(e)
            }
    
    async def _execute_agent_fallback(
        self, 
        agent_type: str, 
        message: str, 
        context: Optional[Dict[str, Any]], 
        user_id: str
    ) -> Dict[str, Any]:
        """Fallback execution without WebSocket coordination."""
        try:
            full_message = f"[Agent Type: {agent_type}] {message}"
            if context:
                full_message += f" (Context: {context})"
                
            result = await self.supervisor.run(
                full_message, 
                f"thread_{user_id}",
                user_id,
                f"run_{agent_type}_{user_id}"
            )
            
            return {
                "response": str(result),
                "agent": agent_type,
                "status": "success",
                "user_id": user_id,
                "websocket_events_sent": False,
                "bridge_coordinated": False,
                "fallback_execution": True
            }
            
        except Exception as e:
            logger.error(f"Fallback execution failed for {agent_type}: {e}")
            return {
                "response": f"Error in fallback execution: {str(e)}",
                "agent": agent_type,
                "status": "error",
                "user_id": user_id,
                "error": str(e),
                "fallback_execution": True
            }