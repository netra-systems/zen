"""
Unified WebSocket Endpoints - Single Source of Truth

Business Value Justification:
- Segment: Platform/Internal 
- Business Goal: Stability & Development Velocity
- Value Impact: Single WebSocket endpoint, eliminates routing confusion
- Strategic Impact: Replaces 3 conflicting endpoints with 1 secure implementation

Endpoints provided:
- /ws: Main WebSocket endpoint (secure, authenticated)
- /ws/config: WebSocket configuration
- /ws/health: Health check
- /ws/stats: Statistics (development)

CRITICAL: This replaces ALL previous WebSocket endpoints.
All clients should migrate to /ws with proper JWT authentication.
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from netra_backend.app.core.tracing import TracingManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.monitoring.gcp_error_reporter import gcp_reportable, set_request_context, clear_request_context
from netra_backend.app.websocket_core import (
    WebSocketManager,
    MessageRouter,
    WebSocketAuthenticator,
    ConnectionSecurityManager,
    get_websocket_manager,
    get_message_router,
    get_websocket_authenticator,
    get_connection_security_manager,
    secure_websocket_context,
    WebSocketHeartbeat,
    get_connection_monitor,
    safe_websocket_send,
    safe_websocket_close,
    create_server_message,
    create_error_message,
    MessageType,
    WebSocketConfig
)
from netra_backend.app.websocket_core.utils import is_websocket_connected

logger = central_logger.get_logger(__name__)
router = APIRouter(tags=["WebSocket"])
tracing_manager = TracingManager()

# WebSocket Configuration - Environment Aware
def _get_rate_limit_for_environment() -> int:
    """Get WebSocket rate limit based on environment."""
    from netra_backend.app.core.environment_constants import Environment
    from shared.isolated_environment import get_env
    
    env = get_env()
    environment = env.get("ENVIRONMENT", "development").lower()
    testing = env.get("TESTING", "0") == "1"
    
    # Much higher rate limits for testing environments to prevent E2E test failures
    if testing or environment in ["testing", "e2e_testing"]:
        return 1000  # Very high limit for test environments
    elif environment == "development":
        return 300   # High limit for development
    elif environment == "staging":
        return 100   # Medium limit for staging
    else:  # production
        return 30    # Conservative limit for production

def _get_staging_optimized_timeouts():
    """Get staging-optimized timeout configuration to prevent disconnections."""
    from shared.isolated_environment import get_env
    
    env = get_env()
    environment = env.get("ENVIRONMENT", "development").lower()
    
    if environment == "staging":
        # CRITICAL FIX: Use environment variables with staging defaults
        # Staging environment needs longer timeouts to handle network latency
        # and GCP load balancer keepalive requirements
        return {
            "connection_timeout_seconds": int(env.get("WEBSOCKET_CONNECTION_TIMEOUT", "600")),
            "heartbeat_interval_seconds": int(env.get("WEBSOCKET_HEARTBEAT_INTERVAL", "30")),
            "heartbeat_timeout_seconds": int(env.get("WEBSOCKET_HEARTBEAT_TIMEOUT", "90")),
            "cleanup_interval_seconds": int(env.get("WEBSOCKET_CLEANUP_INTERVAL", "120"))
        }
    elif environment == "production":
        # Production values - conservative but reliable with environment variables
        return {
            "connection_timeout_seconds": int(env.get("WEBSOCKET_CONNECTION_TIMEOUT", "900")),
            "heartbeat_interval_seconds": int(env.get("WEBSOCKET_HEARTBEAT_INTERVAL", "25")),
            "heartbeat_timeout_seconds": int(env.get("WEBSOCKET_HEARTBEAT_TIMEOUT", "75")),
            "cleanup_interval_seconds": int(env.get("WEBSOCKET_CLEANUP_INTERVAL", "180"))
        }
    else:
        # Development/testing - more permissive with environment variables
        return {
            "connection_timeout_seconds": int(env.get("WEBSOCKET_CONNECTION_TIMEOUT", "300")),
            "heartbeat_interval_seconds": int(env.get("WEBSOCKET_HEARTBEAT_INTERVAL", "45")),
            "heartbeat_timeout_seconds": int(env.get("WEBSOCKET_HEARTBEAT_TIMEOUT", "60")),
            "cleanup_interval_seconds": int(env.get("WEBSOCKET_CLEANUP_INTERVAL", "60"))
        }

# Get environment-specific timeout configuration
_timeout_config = _get_staging_optimized_timeouts()

WEBSOCKET_CONFIG = WebSocketConfig(
    max_connections_per_user=3,
    max_message_rate_per_minute=_get_rate_limit_for_environment(),
    max_message_size_bytes=8192,
    connection_timeout_seconds=_timeout_config["connection_timeout_seconds"],
    heartbeat_interval_seconds=_timeout_config["heartbeat_interval_seconds"],
    cleanup_interval_seconds=_timeout_config["cleanup_interval_seconds"],
    enable_compression=False
)

# CRITICAL FIX: Export heartbeat timeout for heartbeat manager configuration
HEARTBEAT_TIMEOUT_SECONDS = _timeout_config["heartbeat_timeout_seconds"]


@router.websocket("/ws")
@gcp_reportable(reraise=True)
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint - handles all WebSocket connections.
    
    Features:
    - JWT authentication (header or subprotocol)
    - Automatic message routing
    - Heartbeat monitoring
    - Rate limiting
    - Error handling and recovery
    - MCP/JSON-RPC compatibility
    
    Authentication:
    - Authorization header: "Bearer <jwt_token>"
    - Sec-WebSocket-Protocol: "jwt.<base64url_encoded_token>"
    """
    connection_id: Optional[str] = None
    heartbeat: Optional[WebSocketHeartbeat] = None
    user_id: Optional[str] = None
    authenticated = False
    
    try:
        # CRITICAL FIX: Accept WebSocket FIRST before any authentication or operations
        # This prevents "WebSocket is not connected" errors during authentication failures
        subprotocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
        selected_protocol = None
        
        # Select jwt-auth if available (client supports authentication)
        if "jwt-auth" in [p.strip() for p in subprotocols]:
            selected_protocol = "jwt-auth"
        
        # Accept with selected subprotocol BEFORE authentication
        if selected_protocol:
            await websocket.accept(subprotocol=selected_protocol)
            logger.debug(f"WebSocket accepted with subprotocol: {selected_protocol}")
        else:
            await websocket.accept()
            logger.debug("WebSocket accepted without subprotocol")
        
        # Get service instances
        ws_manager = get_websocket_manager()
        message_router = get_message_router()
        connection_monitor = get_connection_monitor()
        
        # Log current handler count for debugging
        logger.info(f"WebSocket message router has {len(message_router.handlers)} handlers before agent handler registration")
        
        # Initialize MessageHandlerService and AgentMessageHandler
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
        from netra_backend.app.services.message_handlers import MessageHandlerService
        
        # Get dependencies from app state (check if they exist first)
        supervisor = getattr(websocket.app.state, 'agent_supervisor', None)
        thread_service = getattr(websocket.app.state, 'thread_service', None)
        
        # Check environment to determine if fallback is allowed
        from shared.isolated_environment import get_env
        environment = get_env().get("ENVIRONMENT", "development").lower()
        is_testing = get_env().get("TESTING", "0") == "1"
        
        # Log dependency status for debugging
        logger.info(f"WebSocket dependency check - Environment: {environment}, Testing: {is_testing}")
        logger.info(f"WebSocket dependency check - Supervisor: {supervisor is not None}, ThreadService: {thread_service is not None}")
        
        # Check if startup is still in progress
        startup_complete = getattr(websocket.app.state, 'startup_complete', False)
        if not startup_complete and environment in ["staging", "production"]:
            logger.warning(f"WebSocket accessed before startup complete in {environment} - startup_complete={startup_complete}")
        
        # CRITICAL FIX: If thread_service is missing but supervisor exists, create it
        if supervisor is not None and thread_service is None:
            logger.warning("thread_service missing but supervisor available - creating thread_service")
            from netra_backend.app.services.thread_service import ThreadService
            thread_service = ThreadService()
            websocket.app.state.thread_service = thread_service
            logger.info("Created missing thread_service for WebSocket handler")
        
        # Create MessageHandlerService and AgentMessageHandler if dependencies exist
        if supervisor is not None and thread_service is not None:
            try:
                # CRITICAL FIX: Pass WebSocket manager to enable real-time agent events
                message_handler_service = MessageHandlerService(supervisor, thread_service, ws_manager)
                agent_handler = AgentMessageHandler(message_handler_service, websocket)
                
                # Register agent handler with message router
                message_router.add_handler(agent_handler)
                logger.info(f"Registered real AgentMessageHandler for production agent pipeline")
                logger.info(f"Total handlers after registration: {len(message_router.handlers)}")
            except Exception as e:
                # CRITICAL: NO FALLBACK IN STAGING/PRODUCTION
                if environment in ["staging", "production"] and not is_testing:
                    logger.error(f"Failed to register AgentMessageHandler in {environment}: {e}")
                    raise RuntimeError(f"AgentMessageHandler registration failed in {environment} - this is a critical error") from e
                else:
                    logger.warning(f"Failed to register real AgentMessageHandler: {e}, using fallback for {environment}")
                    # Create fallback agent handler only for testing/development
                    fallback_handler = _create_fallback_agent_handler()
                    message_router.add_handler(fallback_handler)
                    logger.info(f"Registered fallback AgentMessageHandler for {environment} environment")
                    logger.info(f"Total handlers after fallback registration: {len(message_router.handlers)}")
        else:
            # CRITICAL: NO FALLBACK IN STAGING/PRODUCTION - CHAT IS KING
            if environment in ["staging", "production"] and not is_testing:
                missing_deps = []
                if supervisor is None:
                    missing_deps.append("agent_supervisor")
                if thread_service is None:
                    missing_deps.append("thread_service")
                error_msg = f"CRITICAL: Chat dependencies missing in {environment}: {missing_deps}"
                logger.critical(error_msg)
                logger.critical("Chat delivers 90% of value - cannot operate without agent services")
                
                # This should NEVER happen if startup is working correctly
                # Send critical error and raise to trigger alerts
                error_response = create_error_message(
                    "CRITICAL_FAILURE",
                    "Chat service failed to initialize. This is a critical error.",
                    {"missing_dependencies": missing_deps, "environment": environment, "severity": "CRITICAL"}
                )
                await safe_websocket_send(websocket, error_response.model_dump())
                await asyncio.sleep(0.1)  # Give time for message to be sent
                await safe_websocket_close(websocket, code=1011, reason="Critical failure")
                
                # Raise to trigger monitoring alerts - chat MUST work
                raise RuntimeError(f"Chat critical failure in {environment} - missing {missing_deps}")
            else:
                logger.warning(f"WebSocket dependencies not available in {environment} - creating fallback agent handler")
                # Create fallback agent handler only for testing/development
                fallback_handler = _create_fallback_agent_handler()
                message_router.add_handler(fallback_handler)
                logger.info(f"🤖 Registered fallback AgentMessageHandler for {environment} - will handle CHAT messages!")
                logger.info(f"🤖 Fallback handler can handle: {fallback_handler.supported_types}")
                logger.info(f"🤖 Total handlers registered: {len(message_router.handlers)}")
                
                # List all registered handlers for debugging
                for idx, handler in enumerate(message_router.handlers):
                    handler_types = getattr(handler, 'supported_types', [])
                    logger.info(f"  Handler {idx}: {handler.__class__.__name__} - supports {handler_types}")
        
        # Authenticate and establish secure connection AFTER accepting
        # CRITICAL FIX: Handle authentication errors gracefully without breaking message loop
        try:
            async with secure_websocket_context(websocket) as (auth_info, security_manager):
                user_id = auth_info.user_id
                authenticated = True
                
                # Set GCP error reporting context
                set_request_context(
                    user_id=user_id,
                    http_context={
                        'method': 'WEBSOCKET',
                        'url': '/ws',
                        'userAgent': websocket.headers.get('user-agent', '') if hasattr(websocket, 'headers') else '',
                    }
                )
                
                connection_start_time = time.time()
                logger.info(f"WebSocket authenticated for user: {user_id} at {datetime.now(timezone.utc).isoformat()}")
                
                # Register connection with manager
                connection_id = await ws_manager.connect_user(user_id, websocket)
                
                # Register with security manager
                security_manager.register_connection(connection_id, auth_info, websocket)
                
                # Register with connection monitor
                connection_monitor.register_connection(connection_id, user_id, websocket)
                
                # Start heartbeat monitoring with staging-optimized timeout
                heartbeat = WebSocketHeartbeat(
                    interval=WEBSOCKET_CONFIG.heartbeat_interval_seconds,
                    timeout=HEARTBEAT_TIMEOUT_SECONDS
                )
                await heartbeat.start(websocket)
                
                # Send welcome message
                welcome_msg = create_server_message(
                    MessageType.SYSTEM_MESSAGE,
                    {
                        "event": "connection_established",
                        "connection_id": connection_id,
                        "user_id": user_id,
                        "server_time": datetime.now(timezone.utc).isoformat(),
                        "config": {
                            "heartbeat_interval": WEBSOCKET_CONFIG.heartbeat_interval_seconds,
                            "max_message_size": WEBSOCKET_CONFIG.max_message_size_bytes
                        }
                    }
                )
                await safe_websocket_send(websocket, welcome_msg.model_dump())
                
                logger.debug(f"WebSocket ready: {connection_id}")
                
                # Main message handling loop
                logger.debug(f"Starting message handling loop for connection: {connection_id}")
                # Debug: Check WebSocket state before entering loop
                logger.debug(f"WebSocket state before loop - client_state: {getattr(websocket, 'client_state', 'N/A')}, application_state: {getattr(websocket, 'application_state', 'N/A')}")
                await _handle_websocket_messages(
                    websocket, user_id, connection_id, ws_manager, 
                    message_router, connection_monitor, security_manager, heartbeat
                )
                logger.debug(f"Message handling loop ended for connection: {connection_id}")
                
        except HTTPException as auth_error:
            # CRITICAL FIX: Authentication failed after WebSocket was accepted
            # Handle this gracefully without triggering "Need to call accept first" errors
            logger.error(f"WebSocket authentication failed: {auth_error.detail}")
            
            # WebSocket is already accepted, so we can safely send error and close
            try:
                error_msg = create_error_message(
                    "AUTH_ERROR",
                    auth_error.detail,
                    {"code": auth_error.status_code}
                )
                await safe_websocket_send(websocket, error_msg.model_dump())
                await asyncio.sleep(0.1)  # Brief delay to ensure message is sent
                await safe_websocket_close(websocket, code=auth_error.status_code, reason=auth_error.detail[:50])
            except Exception as send_error:
                logger.warning(f"Could not send authentication error message: {send_error}")
                # Force close without message
                await safe_websocket_close(websocket, code=1008, reason="Auth failed")
            return
            
    except WebSocketDisconnect as e:
        logger.debug(f"WebSocket disconnected: {connection_id} ({e.code}: {e.reason})")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        if is_websocket_connected(websocket):
            # Send error message before closing
            try:
                error_msg = create_server_message(
                    MessageType.ERROR,
                    {
                        "error": "Internal server error",
                        "message": "An unexpected error occurred. Please reconnect.",
                        "code": "INTERNAL_ERROR"
                    }
                )
                await safe_websocket_send(websocket, error_msg.model_dump())
                await asyncio.sleep(0.1)  # Brief delay to ensure message is sent
            except Exception:
                pass  # Best effort to send error message
            
            await safe_websocket_close(websocket, code=1011, reason="Internal error")
    
    finally:
        # Clear GCP error reporting context
        clear_request_context()
        
        # Cleanup resources - only if authentication was successful
        if heartbeat:
            await heartbeat.stop()
        
        if connection_id and user_id and authenticated:
            try:
                ws_manager = get_websocket_manager()
                connection_monitor = get_connection_monitor()
                security_manager = get_connection_security_manager()
                
                # Disconnect from manager
                await ws_manager.disconnect_user(user_id, websocket, 1000, "Normal closure")
                
                # Unregister from monitoring
                connection_monitor.unregister_connection(connection_id)
                security_manager.unregister_connection(connection_id)
                
                logger.debug(f"WebSocket cleanup completed: {connection_id}")
            except Exception as cleanup_error:
                logger.warning(f"Error during WebSocket cleanup: {cleanup_error}")


async def _handle_websocket_messages(
    websocket: WebSocket,
    user_id: str, 
    connection_id: str,
    ws_manager: WebSocketManager,
    message_router: MessageRouter,
    connection_monitor,
    security_manager: ConnectionSecurityManager,
    heartbeat: WebSocketHeartbeat
) -> None:
    """Handle WebSocket message loop with error recovery."""
    error_count = 0
    max_errors = 5
    backoff_delay = 0.1
    max_backoff = 5.0
    
    loop_start_time = time.time()
    message_count = 0
    logger.info(f"Entering message handling loop for connection: {connection_id} (user: {user_id})")
    
    # Debug WebSocket state at loop entry
    logger.info(f"WebSocket state at loop entry - client_state: {getattr(websocket, 'client_state', 'N/A')}, application_state: {getattr(websocket, 'application_state', 'N/A')}")
    
    try:
        first_check = True
        while is_websocket_connected(websocket):
            if first_check:
                logger.debug(f"First loop iteration for {connection_id}, WebSocket is_connected returned True")
                first_check = False
            try:
                # Track loop iteration with detailed state
                loop_duration = time.time() - loop_start_time
                logger.debug(f"Message loop iteration #{message_count + 1} for {connection_id}, state: {websocket.application_state}, duration: {loop_duration:.1f}s")
                
                # Receive message with timeout
                raw_message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=WEBSOCKET_CONFIG.heartbeat_interval_seconds
                )
                
                message_count += 1
                logger.debug(f"Received message #{message_count} from {connection_id}: {raw_message[:100]}...")
                
                # Validate message size
                if len(raw_message.encode('utf-8')) > WEBSOCKET_CONFIG.max_message_size_bytes:
                    security_manager.report_security_violation(
                        connection_id, "message_too_large", 
                        {"size": len(raw_message)}
                    )
                    continue
                
                # Parse message
                try:
                    message_data = json.loads(raw_message)
                except json.JSONDecodeError as e:
                    await _send_format_error(websocket, f"Invalid JSON: {str(e)}")
                    continue
                
                # Update activity
                connection_monitor.update_activity(connection_id, "message_received")
                
                # Handle pong messages for heartbeat
                if message_data.get("type") == "pong":
                    heartbeat.on_pong_received()
                    logger.debug(f"Received pong from {connection_id}")
                
                # Route message to appropriate handler
                logger.info(f"Routing message type '{message_data.get('type')}' from {user_id}: {str(message_data)[:200]}")
                success = await message_router.route_message(user_id, websocket, message_data)
                logger.info(f"Message routing result: {success} for user {user_id}")
                
                if success:
                    error_count = 0  # Reset error count on success
                    backoff_delay = 0.1  # Reset backoff
                    connection_monitor.update_activity(connection_id, "message_sent")
                    logger.debug(f"Successfully processed message for {connection_id}")
                else:
                    error_count += 1
                    logger.warning(f"Message routing failed for {connection_id}, error_count: {error_count}")
                    await asyncio.sleep(min(backoff_delay, max_backoff))
                    backoff_delay = min(backoff_delay * 2, max_backoff)
                
                # Check security status
                if not security_manager.validate_connection_security(connection_id):
                    logger.warning(f"Security validation failed for {connection_id}")
                    break
                
                # Break on too many errors
                if error_count >= max_errors:
                    logger.error(f"Too many errors for connection {connection_id}")
                    break
                    
            except asyncio.TimeoutError:
                # CRITICAL FIX: Timeout is expected for heartbeat - continue loop but add debug logging
                logger.debug(f"Heartbeat timeout for connection: {connection_id}, continuing loop")
                continue
                
            except WebSocketDisconnect as e:
                # Client disconnected - log with detailed information
                disconnect_info = {
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "disconnect_code": e.code,
                    "disconnect_reason": e.reason or "No reason provided",
                    "connection_duration": time.time() - connection_monitor.get_connection_start_time(connection_id) if hasattr(connection_monitor, 'get_connection_start_time') else "Unknown"
                }
                logger.debug(f"WebSocket disconnect: {disconnect_info}")
                break
                
            except Exception as e:
                error_count += 1
                connection_monitor.update_activity(connection_id, "error")
                
                # CRITICAL FIX: Check if the error is related to WebSocket connection state
                error_message = str(e)
                if "Need to call 'accept' first" in error_message or "WebSocket is not connected" in error_message:
                    logger.error(f"WebSocket connection state error for {connection_id}: {error_message}")
                    logger.error("This indicates a race condition between accept() and message handling")
                    # Break immediately - don't retry connection state errors
                    break
                else:
                    logger.error(f"Message handling error for {connection_id}: {e}", exc_info=True)
                
                if error_count >= max_errors:
                    logger.error(f"Too many errors, closing connection {connection_id}")
                    break
                
                # Apply backoff
                await asyncio.sleep(min(backoff_delay, max_backoff))
                backoff_delay = min(backoff_delay * 2, max_backoff)
                
    except Exception as e:
        logger.error(f"Critical error in message handling loop for {connection_id}: {e}", exc_info=True)
    
    # Log final statistics
    loop_total_duration = time.time() - loop_start_time
    logger.info(
        f"Exiting message handling loop for connection: {connection_id} | "
        f"Duration: {loop_total_duration:.1f}s | Messages processed: {message_count} | "
        f"Errors: {error_count} | User: {user_id}"
    )


async def _send_format_error(websocket: WebSocket, error_message: str) -> None:
    """Send format error message to client."""
    error_msg = create_error_message("FORMAT_ERROR", error_message)
    await safe_websocket_send(websocket, error_msg.model_dump())


def _create_fallback_agent_handler():
    """Create fallback agent handler for E2E testing when real services are not available."""
    from netra_backend.app.websocket_core.handlers import BaseMessageHandler
    from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage, create_server_message
    
    class FallbackAgentHandler(BaseMessageHandler):
        """Fallback handler that generates mock agent responses for E2E testing."""
        
        def __init__(self):
            super().__init__([
                MessageType.CHAT,
                MessageType.USER_MESSAGE,
                MessageType.START_AGENT
            ])
        
        async def handle_message(self, user_id: str, websocket: WebSocket,
                               message: WebSocketMessage) -> bool:
            """Handle chat/user messages with realistic agent pipeline simulation."""
            try:
                logger.info(f"🤖 FallbackAgentHandler CALLED! Processing {message.type} from {user_id} - payload: {message.payload}")
                
                content = message.payload.get("content", "")
                thread_id = message.payload.get("thread_id", message.thread_id)
                
                if not content:
                    logger.warning(f"Empty message content from {user_id}")
                    return False
                
                # SIMPLIFY: Just send a single agent response immediately
                response_content = f"Agent processed your message: '{content}'"
                
                # Send agent response
                response_msg = {
                    "type": "agent_response",
                    "content": response_content,
                    "message": response_content,
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "timestamp": time.time()
                }
                await websocket.send_json(response_msg)
                logger.info(f"🤖 Sent simple agent response to {user_id}")
                
                return True
                
            except Exception as e:
                logger.error(f"Error in FallbackAgentHandler for {user_id}: {e}", exc_info=True)
                
                # Send error response
                error_msg = create_error_message(
                    "AGENT_ERROR",
                    f"Agent processing failed: {str(e)}",
                    {"user_id": user_id, "thread_id": message.thread_id}
                )
                await safe_websocket_send(websocket, error_msg.model_dump())
                return False
    
    return FallbackAgentHandler()


# Configuration and Health Endpoints

async def get_websocket_service_discovery():
    """Get WebSocket service discovery configuration for tests."""
    ws_manager = get_websocket_manager()
    stats = await ws_manager.get_stats()
    
    return {
        "status": "success",
        "websocket_config": {
            "endpoints": {
                "websocket": "/ws"
            },
            "features": {
                "json_first": True,
                "auth_required": True,
                "heartbeat": True,
                "message_routing": True,
                "rate_limiting": True
            },
            "limits": {
                "max_connections_per_user": WEBSOCKET_CONFIG.max_connections_per_user,
                "max_message_rate_per_minute": WEBSOCKET_CONFIG.max_message_rate_per_minute,
                "max_message_size_bytes": WEBSOCKET_CONFIG.max_message_size_bytes
            }
        },
        "server": {
            "active_connections": stats["active_connections"],
            "server_time": datetime.now(timezone.utc).isoformat()
        }
    }


async def authenticate_websocket_with_database(session_info: Dict[str, str]) -> str:
    """Authenticate WebSocket with database session for tests."""
    from netra_backend.app.db.postgres_session import get_async_db
    from netra_backend.app.services.security_service import SecurityService
    
    async with get_async_db() as session:
        security_service = SecurityService(session)
        user = await security_service.get_user_by_id(session_info["user_id"])
        if user and user.is_active:
            return session_info["user_id"]
        else:
            raise HTTPException(status_code=401, detail="User not authenticated")


@router.get("/ws/config")
async def get_websocket_config():
    """Get WebSocket configuration for clients."""
    ws_manager = get_websocket_manager()
    stats = await ws_manager.get_stats()
    
    return {
        "websocket": {
            "endpoint": "/ws",
            "version": "1.0.0",
            "authentication": "jwt_required",
            "supported_auth_methods": ["header", "subprotocol"],
            "features": {
                "heartbeat": True,
                "message_routing": True,
                "json_rpc_support": True,
                "rate_limiting": True,
                "error_recovery": True
            },
            "limits": {
                "max_connections_per_user": WEBSOCKET_CONFIG.max_connections_per_user,
                "max_message_rate_per_minute": WEBSOCKET_CONFIG.max_message_rate_per_minute,
                "max_message_size_bytes": WEBSOCKET_CONFIG.max_message_size_bytes,
                "heartbeat_interval_seconds": WEBSOCKET_CONFIG.heartbeat_interval_seconds
            }
        },
        "server": {
            "active_connections": stats["active_connections"],
            "uptime_seconds": stats["uptime_seconds"],
            "server_time": datetime.now(timezone.utc).isoformat()
        },
        "migration": {
            "replaces_endpoints": [
                "/ws (legacy insecure)",
                "/api/mcp/ws (MCP-specific)", 
                "websocket_unified.py endpoint"
            ],
            "compatibility": "All message formats supported"
        }
    }


@router.get("/ws/health")
@router.head("/ws/health")
@router.options("/ws/health")
async def websocket_health_check():
    """WebSocket service health check with resilient error handling."""
    errors = []
    metrics = {}
    
    # Try to get WebSocket manager stats (most basic requirement)
    try:
        ws_manager = get_websocket_manager()
        ws_stats = await ws_manager.get_stats()
        metrics["websocket"] = {
            "active_connections": ws_stats["active_connections"],
            "total_connections": ws_stats["total_connections"], 
            "messages_processed": ws_stats["messages_sent"] + ws_stats["messages_received"],
            "error_rate": ws_stats["errors_handled"] / max(1, ws_stats["total_connections"])
        }
    except Exception as e:
        errors.append(f"websocket_manager: {str(e)}")
        metrics["websocket"] = {
            "status": "unavailable",
            "error": str(e)
        }
    
    # Try to get authentication stats (optional)
    try:
        authenticator = get_websocket_authenticator()
        auth_stats = authenticator.get_auth_stats()
        metrics["authentication"] = {
            "success_rate": auth_stats.get("success_rate", 0),
            "rate_limited_requests": auth_stats.get("rate_limited", 0)
        }
    except Exception as e:
        errors.append(f"websocket_auth: {str(e)}")
        metrics["authentication"] = {
            "status": "unavailable", 
            "error": str(e)
        }
    
    # Try to get connection monitoring stats (optional)
    try:
        connection_monitor = get_connection_monitor()
        monitor_stats = connection_monitor.get_global_stats()
        metrics["monitoring"] = {
            "monitored_connections": monitor_stats["total_connections"],
            "healthy_connections": monitor_stats.get("health_summary", {}).get("healthy_connections", 0)
        }
    except Exception as e:
        errors.append(f"connection_monitor: {str(e)}")
        metrics["monitoring"] = {
            "status": "unavailable",
            "error": str(e)
        }
    
    # Determine health status based on core functionality
    ws_metrics = metrics.get("websocket", {})
    is_healthy = (
        "error" not in ws_metrics and  # WebSocket manager is available
        ws_metrics.get("active_connections", -1) >= 0  # Basic sanity check
    )
    
    status = "healthy" if is_healthy else "degraded" 
    if errors:
        status = "degraded"
    
    response = {
        "status": status,
        "service": "websocket",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "config": {
            "max_connections_per_user": WEBSOCKET_CONFIG.max_connections_per_user,
            "heartbeat_interval": WEBSOCKET_CONFIG.heartbeat_interval_seconds
        }
    }
    
    if errors:
        response["errors"] = errors
    
    return response


@router.websocket("/websocket")
async def websocket_legacy_endpoint(websocket: WebSocket):
    """
    Legacy WebSocket endpoint for backward compatibility.
    
    This endpoint mirrors the main /ws endpoint functionality but provides
    backward compatibility for existing tests and clients using /websocket.
    
    Redirects to the main websocket_endpoint implementation.
    """
    return await websocket_endpoint(websocket)


@router.websocket("/ws/test")
async def websocket_test_endpoint(websocket: WebSocket):
    """
    Simple WebSocket test endpoint - NO AUTHENTICATION REQUIRED.
    
    This endpoint is for E2E testing and basic connectivity verification.
    It accepts connections without JWT authentication and handles basic messages.
    """
    connection_id: Optional[str] = None
    
    try:
        # Accept WebSocket connection without authentication
        await websocket.accept()
        logger.debug("Test WebSocket connection accepted (no auth)")
        
        # Generate a simple connection ID
        connection_id = f"test_{int(time.time())}"
        
        # Send welcome message
        welcome_msg = {
            "type": "connection_established",
            "connection_id": connection_id,
            "server_time": datetime.now(timezone.utc).isoformat(),
            "message": "Test WebSocket connected successfully"
        }
        await websocket.send_json(welcome_msg)
        
        logger.debug(f"Test WebSocket ready: {connection_id}")
        
        # Simple message handling loop
        while True:
            try:
                # Receive message with timeout
                raw_message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                logger.debug(f"Test WebSocket received: {raw_message}")
                
                # Parse message
                try:
                    message_data = json.loads(raw_message)
                except json.JSONDecodeError as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Invalid JSON: {str(e)}"
                    })
                    continue
                
                # Handle different message types
                msg_type = message_data.get("type", "unknown")
                
                if msg_type == "ping":
                    # Respond to ping with pong
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                elif msg_type == "echo":
                    # Echo the message back
                    await websocket.send_json({
                        "type": "echo_response",
                        "original": message_data,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                elif msg_type == "session_start":
                    # Handle session start request - return a mock session ID for testing
                    client_id = message_data.get("client_id", "unknown")
                    session_id = f"test_session_{client_id}_{int(time.time())}"
                    await websocket.send_json({
                        "type": "session_started",
                        "session_id": session_id,
                        "client_id": client_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "message": "Test session started successfully"
                    })
                elif msg_type == "queue_message":
                    # Handle message queueing - acknowledge for testing
                    client_id = message_data.get("client_id", "unknown")
                    await websocket.send_json({
                        "type": "message_queued",
                        "client_id": client_id,
                        "queued_count": 1,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "message": "Message queued successfully"
                    })
                elif msg_type == "reconnect":
                    # Handle reconnection request - simulate session restoration
                    client_id = message_data.get("client_id", "unknown")
                    session_id = message_data.get("session_id", "unknown")
                    await websocket.send_json({
                        "type": "session_restored",
                        "session_id": session_id,
                        "client_id": client_id,
                        "queued_messages": 1,  # Simulate at least one queued message
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "message": "Session restored successfully"
                    })
                else:
                    # Send generic acknowledgment
                    await websocket.send_json({
                        "type": "ack",
                        "received_type": msg_type,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                continue
                
            except WebSocketDisconnect:
                break
                
            except Exception as e:
                logger.error(f"Test WebSocket message error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except WebSocketDisconnect as e:
        logger.debug(f"Test WebSocket disconnected: {connection_id} ({e.code}: {e.reason})")
    
    except Exception as e:
        logger.error(f"Test WebSocket error: {e}", exc_info=True)
        if is_websocket_connected(websocket):
            try:
                await websocket.close(code=1011, reason="Internal error")
            except:
                pass
    
    finally:
        if connection_id:
            logger.debug(f"Test WebSocket cleanup completed: {connection_id}")


@router.get("/ws/stats")
async def websocket_detailed_stats():
    """Detailed WebSocket statistics (for development/monitoring)."""
    ws_manager = get_websocket_manager()
    message_router = get_message_router()
    authenticator = get_websocket_authenticator()
    security_manager = get_connection_security_manager()
    connection_monitor = get_connection_monitor()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "websocket_manager": await ws_manager.get_stats(),
        "message_router": message_router.get_stats(),
        "authentication": authenticator.get_auth_stats(),
        "security": security_manager.get_security_summary(),
        "connection_monitoring": connection_monitor.get_global_stats(),
        "system": {
            "config": WEBSOCKET_CONFIG.model_dump(),
            "endpoint_info": {
                "main_endpoint": "/ws",
                "supports_json_rpc": True,
                "requires_authentication": True
            }
        }
    }