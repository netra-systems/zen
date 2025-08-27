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
    is_websocket_connected,
    safe_websocket_send,
    safe_websocket_close,
    create_server_message,
    create_error_message,
    MessageType,
    WebSocketConfig
)

logger = central_logger.get_logger(__name__)
router = APIRouter(tags=["WebSocket"])
tracing_manager = TracingManager()

# WebSocket Configuration
WEBSOCKET_CONFIG = WebSocketConfig(
    max_connections_per_user=3,
    max_message_rate_per_minute=30,
    max_message_size_bytes=8192,
    connection_timeout_seconds=300,
    heartbeat_interval_seconds=45,
    cleanup_interval_seconds=60,
    enable_compression=False
)


@router.websocket("/ws")
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
    
    try:
        # Get service instances
        ws_manager = get_websocket_manager()
        message_router = get_message_router()
        connection_monitor = get_connection_monitor()
        
        # Initialize MessageHandlerService and AgentMessageHandler
        from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
        from netra_backend.app.services.message_handlers import MessageHandlerService
        
        # Get dependencies from app state (check if they exist first)
        supervisor = getattr(websocket.app.state, 'agent_supervisor', None)
        thread_service = getattr(websocket.app.state, 'thread_service', None)
        
        # Create MessageHandlerService and AgentMessageHandler if dependencies exist
        if supervisor is not None and thread_service is not None:
            message_handler_service = MessageHandlerService(supervisor, thread_service)
            agent_handler = AgentMessageHandler(message_handler_service)
            
            # Register agent handler with message router
            message_router.add_handler(agent_handler)
        else:
            logger.warning("WebSocket dependencies not available - running in test mode without agent handlers")
        
        # Authenticate and establish secure connection
        async with secure_websocket_context(websocket) as (auth_info, security_manager):
            user_id = auth_info.user_id
            
            # Accept WebSocket connection
            await websocket.accept()
            connection_start_time = time.time()
            logger.info(f"WebSocket connection accepted for user: {user_id} at {datetime.now(timezone.utc).isoformat()}")
            
            # Register connection with manager
            connection_id = await ws_manager.connect_user(user_id, websocket)
            
            # Register with security manager
            security_manager.register_connection(connection_id, auth_info, websocket)
            
            # Register with connection monitor
            connection_monitor.register_connection(connection_id, user_id, websocket)
            
            # Start heartbeat monitoring
            heartbeat = WebSocketHeartbeat(
                interval=WEBSOCKET_CONFIG.heartbeat_interval_seconds,
                timeout=10.0
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
            
            logger.info(f"WebSocket ready: {connection_id}")
            
            # Main message handling loop
            logger.info(f"Starting message handling loop for connection: {connection_id}")
            await _handle_websocket_messages(
                websocket, user_id, connection_id, ws_manager, 
                message_router, connection_monitor, security_manager, heartbeat
            )
            logger.info(f"Message handling loop ended for connection: {connection_id}")
            
    except HTTPException as e:
        logger.error(f"WebSocket authentication failed: {e.detail}")
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await safe_websocket_close(websocket, code=e.status_code, reason=e.detail[:50])
    
    except WebSocketDisconnect as e:
        logger.info(f"WebSocket disconnected: {connection_id} ({e.code}: {e.reason})")
    
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
            except Exception:
                pass  # Best effort to send error message
            
            await safe_websocket_close(websocket, code=1011, reason="Internal error")
    
    finally:
        # Cleanup resources
        if heartbeat:
            await heartbeat.stop()
        
        if connection_id:
            ws_manager = get_websocket_manager()
            connection_monitor = get_connection_monitor()
            security_manager = get_connection_security_manager()
            
            # Disconnect from manager
            await ws_manager.disconnect_user(user_id, websocket, 1000, "Normal closure")
            
            # Unregister from monitoring
            connection_monitor.unregister_connection(connection_id)
            security_manager.unregister_connection(connection_id)
            
            logger.info(f"WebSocket cleanup completed: {connection_id}")


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
    
    try:
        while is_websocket_connected(websocket):
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
                success = await message_router.route_message(user_id, websocket, message_data)
                
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
                logger.info(f"WebSocket disconnect: {disconnect_info}")
                break
                
            except Exception as e:
                error_count += 1
                connection_monitor.update_activity(connection_id, "error")
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


# Configuration and Health Endpoints

async def get_websocket_service_discovery():
    """Get WebSocket service discovery configuration for tests."""
    ws_manager = get_websocket_manager()
    stats = ws_manager.get_stats()
    
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
    stats = ws_manager.get_stats()
    
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
async def websocket_health_check():
    """WebSocket service health check with resilient error handling."""
    errors = []
    metrics = {}
    
    # Try to get WebSocket manager stats (most basic requirement)
    try:
        ws_manager = get_websocket_manager()
        ws_stats = ws_manager.get_stats()
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
        logger.info("Test WebSocket connection accepted (no auth)")
        
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
        
        logger.info(f"Test WebSocket ready: {connection_id}")
        
        # Simple message handling loop
        while True:
            try:
                # Receive message with timeout
                raw_message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                logger.info(f"Test WebSocket received: {raw_message}")
                
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
        logger.info(f"Test WebSocket disconnected: {connection_id} ({e.code}: {e.reason})")
    
    except Exception as e:
        logger.error(f"Test WebSocket error: {e}", exc_info=True)
        if websocket.application_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close(code=1011, reason="Internal error")
            except:
                pass
    
    finally:
        if connection_id:
            logger.info(f"Test WebSocket cleanup completed: {connection_id}")


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
        "websocket_manager": ws_manager.get_stats(),
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