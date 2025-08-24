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
from starlette.websockets import WebSocketState

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
        
        # Authenticate and establish secure connection
        async with secure_websocket_context(websocket) as (auth_info, security_manager):
            user_id = auth_info.user_id
            
            # Accept WebSocket connection
            await websocket.accept()
            logger.info(f"WebSocket connection accepted for user: {user_id}")
            
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
            await _handle_websocket_messages(
                websocket, user_id, connection_id, ws_manager, 
                message_router, connection_monitor, security_manager, heartbeat
            )
            
    except HTTPException as e:
        logger.error(f"WebSocket authentication failed: {e.detail}")
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await safe_websocket_close(websocket, code=e.status_code, reason=e.detail[:50])
    
    except WebSocketDisconnect as e:
        logger.info(f"WebSocket disconnected: {connection_id} ({e.code}: {e.reason})")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        if is_websocket_connected(websocket):
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
    
    try:
        while is_websocket_connected(websocket):
            try:
                # Receive message with timeout
                raw_message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=WEBSOCKET_CONFIG.heartbeat_interval_seconds
                )
                
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
                
                # Route message to appropriate handler
                success = await message_router.route_message(user_id, websocket, message_data)
                
                if success:
                    error_count = 0  # Reset error count on success
                    backoff_delay = 0.1  # Reset backoff
                    connection_monitor.update_activity(connection_id, "message_sent")
                else:
                    error_count += 1
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
                # Timeout is expected for heartbeat - continue loop
                continue
                
            except WebSocketDisconnect:
                # Client disconnected - break loop
                break
                
            except Exception as e:
                error_count += 1
                connection_monitor.update_activity(connection_id, "error")
                logger.error(f"Message handling error for {connection_id}: {e}")
                
                if error_count >= max_errors:
                    logger.error(f"Too many errors, closing connection {connection_id}")
                    break
                
                # Apply backoff
                await asyncio.sleep(min(backoff_delay, max_backoff))
                backoff_delay = min(backoff_delay * 2, max_backoff)
                
    except Exception as e:
        logger.error(f"Critical error in message handling loop: {e}", exc_info=True)


async def _send_format_error(websocket: WebSocket, error_message: str) -> None:
    """Send format error message to client."""
    error_msg = create_error_message("FORMAT_ERROR", error_message)
    await safe_websocket_send(websocket, error_msg.model_dump())


# Configuration and Health Endpoints

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
            "active_connections": stats.active_connections,
            "uptime_seconds": stats.uptime_seconds,
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
    """WebSocket service health check."""
    ws_manager = get_websocket_manager()
    authenticator = get_websocket_authenticator()
    connection_monitor = get_connection_monitor()
    
    # Get service statistics
    ws_stats = ws_manager.get_stats()
    auth_stats = authenticator.get_auth_stats()
    monitor_stats = connection_monitor.get_global_stats()
    
    # Determine health status
    is_healthy = (
        ws_stats.active_connections >= 0 and  # Basic sanity check
        auth_stats.get("success_rate", 0) > 0.8 and  # 80%+ auth success rate
        ws_stats.errors_handled < 100  # Less than 100 total errors
    )
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "service": "websocket",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "websocket": {
                "active_connections": ws_stats.active_connections,
                "total_connections": ws_stats.total_connections,
                "messages_processed": ws_stats.messages_sent + ws_stats.messages_received,
                "error_rate": ws_stats.errors_handled / max(1, ws_stats.total_connections)
            },
            "authentication": {
                "success_rate": auth_stats.get("success_rate", 0),
                "rate_limited_requests": auth_stats.get("rate_limited", 0)
            },
            "monitoring": {
                "monitored_connections": monitor_stats["total_connections"],
                "healthy_connections": monitor_stats.get("health_summary", {}).get("healthy_connections", 0)
            }
        },
        "config": {
            "max_connections_per_user": WEBSOCKET_CONFIG.max_connections_per_user,
            "heartbeat_interval": WEBSOCKET_CONFIG.heartbeat_interval_seconds
        }
    }


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
        "websocket_manager": ws_manager.get_stats().model_dump(),
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